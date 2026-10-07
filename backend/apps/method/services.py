"""Logique de la méthode (modules 36 à 41), partagée par l'API et le tick minute.

Règles fixes (cf. docs/requirements/modules-36-41.md) : elles ne sont pas
configurables, c'est voulu — on ne renégocie pas ses règles sur le moment.
"""
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import UserSettings
from apps.focus.models import FocusSession
from apps.projects.models import Objective, Project
from apps.tasks.models import POSTPONE_THRESHOLD, ActivityLog, Blocker, Task
from apps.webhooks.dispatch import emit

from .models import DayLog, MethodConfig, Slot, SlotOccurrence, WeeklyReview

CONTRACT_MINUTES = 10                    # démarrer = 10 min, le reste est du bonus
START_EARLY = timedelta(minutes=60)      # on peut prendre un peu d'avance
NUDGE_AFTER = timedelta(minutes=15)      # relance « version 2 minutes »
MISSED_GRACE = timedelta(minutes=15)     # raté 15 min après la fin
AMNESTY_AFTER = timedelta(days=7)        # au-delà, le retard est amnistié en revue
REVIEW_UPCOMING = timedelta(hours=2)     # le planificateur prépare la revue
EVENT_STALE = timedelta(hours=12)        # pas de rendez-vous de revue périmé
UP_RATE, DOWN_RATE = 0.8, 0.5            # règle des 2 semaines (niveaux)
SYSTEM_ACTOR = "system"

REMEDIES = {
    Blocker.BORING: "Ennuyeuse : associe-la à un plaisir (musique, café) ou fais-la avec "
                    "quelqu'un, 10 minutes chrono.",
    Blocker.UNCLEAR: "Floue : écris la toute première action physique (un verbe, un objet). "
                     "Ton coach peut la reformuler.",
    Blocker.TOO_BIG: "Trop grosse : découpe-la en étapes de 30 minutes au plus ; seule la "
                     "première compte aujourd'hui.",
    Blocker.UNPLEASANT: "Désagréable : fais-en exprès une version ratée en 10 minutes, en "
                        "premier dans ta journée.",
    Blocker.USELESS: "Plus utile : abandonnée, sans culpabilité. Une tâche de moins.",
}


# ---- Temps local -------------------------------------------------------------

def user_tz(user):
    return UserSettings.objects.get_or_create(user=user)[0].tzinfo


def local_now(user):
    return timezone.now().astimezone(user_tz(user))


def week_start_of(day):
    return day - timedelta(days=day.weekday())


def day_bounds(user, first_day, last_day):
    """[début de first_day, début du lendemain de last_day[ en instants aware."""
    tz = user_tz(user)
    start = datetime.combine(first_day, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(last_day + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return start, end


# ---- Occurrences ---------------------------------------------------------------

def _excuse_for(user, config, day):
    if config.is_paused(day):
        return SlotOccurrence.Excuse.PAUSE
    if DayLog.objects.filter(user=user, date=day, color=DayLog.Color.RED).exists():
        return SlotOccurrence.Excuse.ROUGE
    return ""


def ensure_occurrences(user, first_day, last_day):
    """Matérialise les occurrences des créneaux entre deux dates (incluses).

    Jamais d'occurrence antérieure à la création du créneau : sinon un créneau
    créé à 21 h « raterait » aussitôt celui de 20 h 30.
    """
    tz = user_tz(user)
    config = MethodConfig.for_user(user)
    for slot in Slot.objects.filter(user=user):
        day = first_day
        while day <= last_day:
            if day.weekday() == slot.weekday:
                start_at = datetime.combine(day, slot.start_time, tzinfo=tz)
                if start_at >= slot.created_at and not slot.occurrences.filter(date=day).exists():
                    excuse = _excuse_for(user, config, day)
                    try:
                        with transaction.atomic():
                            SlotOccurrence.objects.create(
                                user=user, slot=slot, date=day, start_at=start_at,
                                duration_minutes=slot.duration_minutes, kind=slot.kind,
                                status=(SlotOccurrence.Status.EXCUSED if excuse
                                        else SlotOccurrence.Status.PLANNED),
                                excuse_reason=excuse,
                            )
                    except IntegrityError:
                        pass  # créée en parallèle (tick vs requête)
            day += timedelta(days=1)


def reset_future_occurrences(slot):
    """Un créneau modifié/supprimé : ses occurrences à venir non entamées disparaissent
    (rematérialisées à la demande) ; le passé reste intact."""
    slot.occurrences.filter(
        status__in=[SlotOccurrence.Status.PLANNED, SlotOccurrence.Status.EXCUSED],
        start_at__gt=timezone.now(), started_at__isnull=True,
    ).exclude(excuse_reason=SlotOccurrence.Excuse.JOKER).delete()


def _open_tasks(qs):
    return qs.filter(
        status=Task.Status.NORMAL, proposed=False,
        trashed_at__isnull=True, archived_at__isnull=True,
    )


def _first_actionable(tasks):
    """Première tâche ouverte, en descendant dans ses sous-tâches ouvertes
    (la prochaine action concrète, pas le chapeau)."""
    task = tasks.order_by("sort_order", "id").first()
    while task is not None:
        child = _open_tasks(task.children.all()).order_by("sort_order", "id").first()
        if child is None:
            return task
        task = child
    return None


def next_action(occurrence):
    """Tâche proposée par l'occurrence (M36.3) : assignée, sinon objectif du créneau,
    sinon objectif actif le mieux classé. Jamais une proposition non validée."""
    task = occurrence.task
    if task is not None and _open_tasks(Task.objects.filter(pk=task.pk)).exists():
        return task
    slot_project = occurrence.slot.project if occurrence.slot else None
    projects = (
        [slot_project] if slot_project is not None
        else Project.objects.filter(user=occurrence.user, objective=Objective.ACTIVE,
                                    archived=False).order_by("sort_order", "id")
    )
    for project in projects:
        found = _first_actionable(_open_tasks(project.tasks.filter(parent__isnull=True)))
        if found is not None:
            return found
    return None


def serialize_occurrence(occurrence):
    from .serializers import SlotOccurrenceSerializer

    return SlotOccurrenceSerializer(occurrence).data


# ---- Démarrer, joker, raté -----------------------------------------------------

def start_occurrence(occurrence, task=None, minutes=None, actor="user"):
    """Démarrer en un geste (M36.4) : honore, fixe la tâche, lance le contrat de 10 min."""
    now = timezone.now()
    if occurrence.status not in (SlotOccurrence.Status.PLANNED, SlotOccurrence.Status.MISSED):
        raise ValidationError({"detail": "Ce créneau n'est plus à démarrer."})
    if local_now(occurrence.user).date() != occurrence.date or now < occurrence.start_at - START_EARLY:
        raise ValidationError({"detail": "Ce créneau se démarre le jour même, au plus tôt une heure avant."})
    task = task or next_action(occurrence)

    # Une session déjà en cours est rattachée au créneau plutôt que doublée.
    session = FocusSession.objects.filter(user=occurrence.user, end_at__isnull=True).first()
    created = session is None
    if created:
        session = FocusSession.objects.create(
            user=occurrence.user, task=task, start_at=now,
            planned_seconds=int(minutes or CONTRACT_MINUTES) * 60,
        )

    was_missed = occurrence.status == SlotOccurrence.Status.MISSED
    occurrence.status = SlotOccurrence.Status.HONORED
    occurrence.started_at = now
    occurrence.task = task
    occurrence.focus_session = session
    occurrence.save()
    if was_missed:
        # Rattrapé le jour même : le tampon qui l'attendait redevient libre.
        SlotOccurrence.objects.filter(recovers=occurrence).update(recovers=None)
    recovered = occurrence.recovers
    if occurrence.kind == Slot.Kind.BUFFER and recovered is not None \
            and recovered.status == SlotOccurrence.Status.MISSED:
        recovered.status = SlotOccurrence.Status.RECOVERED
        recovered.save(update_fields=["status"])

    if created:
        from apps.focus.serializers import FocusSessionSerializer

        emit(occurrence.user, "pomodoro.started", FocusSessionSerializer(session).data, actor=actor)
    emit(occurrence.user, "slot.started", serialize_occurrence(occurrence), actor=actor)
    return occurrence


def jokers_used(user, day):
    return SlotOccurrence.objects.filter(
        user=user, excuse_reason=SlotOccurrence.Excuse.JOKER,
        date__year=day.year, date__month=day.month,
    ).count()


def jokers_remaining(user, day):
    config = MethodConfig.for_user(user)
    return max(0, config.jokers_per_month - jokers_used(user, day))


def use_joker(occurrence):
    """Excuser une occurrence sans pénalité, dans la limite du quota mensuel (M36.7)."""
    if occurrence.kind != Slot.Kind.WORK or occurrence.status not in (
        SlotOccurrence.Status.PLANNED, SlotOccurrence.Status.MISSED,
    ):
        raise ValidationError({"detail": "Ce créneau ne peut pas recevoir de joker."})
    if jokers_remaining(occurrence.user, occurrence.date) <= 0:
        raise ValidationError({"detail": "Plus de joker ce mois-ci."})
    occurrence.status = SlotOccurrence.Status.EXCUSED
    occurrence.excuse_reason = SlotOccurrence.Excuse.JOKER
    occurrence.save(update_fields=["status", "excuse_reason"])
    SlotOccurrence.objects.filter(recovers=occurrence).update(recovers=None)
    return occurrence


def _assign_recovery(missed):
    """Report automatique au prochain tampon libre de la semaine (M36.6)."""
    user = missed.user
    today = local_now(user).date()
    week_end = week_start_of(missed.date) + timedelta(days=6)
    if today > week_end:
        return
    ensure_occurrences(user, today, week_end)
    buffer = SlotOccurrence.objects.filter(
        user=user, kind=Slot.Kind.BUFFER, status=SlotOccurrence.Status.PLANNED,
        start_at__gt=timezone.now(), date__lte=week_end, recovers__isnull=True,
    ).first()
    if buffer is not None:
        buffer.recovers = missed
        buffer.save(update_fields=["recovers"])


# ---- Tick minute ---------------------------------------------------------------

def _push(user, title, body, url):
    from apps.accounts.fcm import send_fcm
    from apps.accounts.push import notify_user

    # Le téléphone programme ces rendez-vous en local : FCM le saute (reminder=True).
    for push, extra in ((notify_user, {}), (send_fcm, {"reminder": True})):
        try:
            push(user, title=title, body=body, url=url, **extra)
        except Exception:  # un canal en échec ne bloque ni les autres ni le tick
            pass


def tick_user(user):
    """Transitions horaires d'un utilisateur : relances, ratés, tampons, revue."""
    now = timezone.now()
    config = MethodConfig.for_user(user)
    today = local_now(user).date()
    ensure_occurrences(user, today, today + timedelta(days=1))
    paused = config.is_paused(today)
    if paused:
        apply_excuse(user, today, SlotOccurrence.Excuse.PAUSE)

    for occ in SlotOccurrence.objects.filter(
        user=user, status=SlotOccurrence.Status.PLANNED, start_at__lte=now,
    ).select_related("slot__project"):
        if now >= occ.end_at + MISSED_GRACE:
            if occ.kind == Slot.Kind.BUFFER:
                occ.status = SlotOccurrence.Status.FREE
                occ.save(update_fields=["status"])
            else:
                occ.status = SlotOccurrence.Status.MISSED
                occ.save(update_fields=["status"])
                emit(user, "slot.missed", serialize_occurrence(occ), actor=SYSTEM_ACTOR)
                _assign_recovery(occ)
            continue
        if occ.due_sent_at is None:
            occ.due_sent_at = now
            occ.save(update_fields=["due_sent_at"])
            # Un tampon sans rattrapage est du temps libre : on ne dérange pas.
            if now < occ.start_at + NUDGE_AFTER and (
                occ.kind == Slot.Kind.WORK or occ.recovers_id is not None
            ):
                data = serialize_occurrence(occ)
                emit(user, "slot.due", data, actor=SYSTEM_ACTOR)
                action = (data.get("next_action") or {}).get("title")
                _push(user, "🎯 C'est l'heure",
                      f"{action} — 10 minutes suffisent." if action else "10 minutes suffisent.",
                      "/today")
        if occ.kind == Slot.Kind.WORK and occ.nudge_sent_at is None and now >= occ.start_at + NUDGE_AFTER:
            occ.nudge_sent_at = now
            occ.save(update_fields=["nudge_sent_at"])
            emit(user, "slot.nudge", serialize_occurrence(occ), actor=SYSTEM_ACTOR)

    if not paused:
        _tick_review(user, config, now)


def review_moment(user, config, week_start):
    return datetime.combine(
        week_start + timedelta(days=config.review_weekday), config.review_time,
        tzinfo=user_tz(user),
    )


def _tick_review(user, config, now):
    week_start = week_start_of(local_now(user).date())
    moment = review_moment(user, config, week_start)
    if not (moment - REVIEW_UPCOMING <= now < moment + EVENT_STALE):
        return
    review, _ = WeeklyReview.objects.get_or_create(user=user, week_start=week_start)
    payload = {"week_start": week_start.isoformat(), "review_at": moment.isoformat()}
    if now < moment and review.upcoming_sent_at is None:
        review.upcoming_sent_at = now
        review.save(update_fields=["upcoming_sent_at"])
        emit(user, "review.upcoming", payload, actor=SYSTEM_ACTOR)
    if now >= moment and review.due_sent_at is None and review.completed_at is None:
        review.due_sent_at = now
        review.save(update_fields=["due_sent_at"])
        emit(user, "review.due", payload, actor=SYSTEM_ACTOR)
        _push(user, "🗓️ Ta revue de la semaine", "10 minutes pour décider à froid.", "/review")


# ---- Couleur du jour & pause ---------------------------------------------------

def apply_excuse(user, day, reason):
    """Excuse les occurrences encore prévues du jour (journée rouge, pause)."""
    SlotOccurrence.objects.filter(
        user=user, date=day, status=SlotOccurrence.Status.PLANNED,
    ).update(status=SlotOccurrence.Status.EXCUSED, excuse_reason=reason)


def lift_excuse(user, day, reason):
    """Annule une excuse rouge/pause pour les occurrences pas encore passées."""
    for occ in SlotOccurrence.objects.filter(
        user=user, date=day, status=SlotOccurrence.Status.EXCUSED, excuse_reason=reason,
    ):
        if timezone.now() < occ.end_at + MISSED_GRACE:
            occ.status = SlotOccurrence.Status.PLANNED
            occ.excuse_reason = ""
            occ.save(update_fields=["status", "excuse_reason"])


def set_day_color(user, day, color, actor="user"):
    DayLog.objects.update_or_create(user=user, date=day, defaults={"color": color})
    ensure_occurrences(user, day, day)
    if color == DayLog.Color.RED:
        apply_excuse(user, day, SlotOccurrence.Excuse.ROUGE)
    else:
        lift_excuse(user, day, SlotOccurrence.Excuse.ROUGE)
    emit(user, "day.color", {"date": day.isoformat(), "color": color}, actor=actor)


def sync_pause(user, config):
    """Réaligne les occurrences à venir sur la pause (posée, prolongée ou levée)."""
    today = local_now(user).date()
    upcoming = SlotOccurrence.objects.filter(user=user, date__gte=today)
    for day in sorted(set(upcoming.values_list("date", flat=True))):
        if config.is_paused(day):
            apply_excuse(user, day, SlotOccurrence.Excuse.PAUSE)
        else:
            lift_excuse(user, day, SlotOccurrence.Excuse.PAUSE)


# ---- Tableau de bord, revue ----------------------------------------------------

def today_tasks(user):
    """Tâches d'« Aujourd'hui » (dues aujourd'hui ou en retard), hors propositions."""
    _, end = day_bounds(user, local_now(user).date(), local_now(user).date())
    return _open_tasks(Task.objects.filter(user=user)).filter(
        due_date__lt=end, project__archived=False,
    )


def week_score(user, week_start):
    """Score d'une semaine : créneaux de travail honorés (ou rattrapés) / décidés."""
    occ = SlotOccurrence.objects.filter(
        user=user, kind=Slot.Kind.WORK,
        date__gte=week_start, date__lte=week_start + timedelta(days=6),
    )
    honored = occ.filter(status__in=[SlotOccurrence.Status.HONORED,
                                     SlotOccurrence.Status.RECOVERED]).count()
    decided = honored + occ.filter(status=SlotOccurrence.Status.MISSED).count()
    return {"honored": honored, "decided": decided,
            "rate": round(honored / decided, 2) if decided else None}


def level_suggestion(user, week_start, level):
    current = week_score(user, week_start)["rate"]
    previous = week_score(user, week_start - timedelta(days=7))["rate"]
    if current is None or previous is None:
        return "keep"
    if current >= UP_RATE and previous >= UP_RATE:
        return "up"
    if current < DOWN_RATE and previous < DOWN_RATE and level > 1:
        return "down"
    return "keep"


def default_review_week(user):
    """Semaine de la dernière revue arrivée (ou sur le point de l'être)."""
    config = MethodConfig.for_user(user)
    this_week = week_start_of(local_now(user).date())
    if timezone.now() + REVIEW_UPCOMING >= review_moment(user, config, this_week):
        return this_week
    return this_week - timedelta(days=7)


def amnesty_candidates(user):
    return _open_tasks(Task.objects.filter(user=user)).filter(
        due_date__lt=timezone.now() - AMNESTY_AFTER,
    )


def review_summary(user, week_start):
    from .serializers import SlotOccurrenceSerializer

    config = MethodConfig.for_user(user)
    week_end = week_start + timedelta(days=6)
    start, end = day_bounds(user, week_start, week_end)
    review = WeeklyReview.objects.filter(user=user, week_start=week_start).first()
    completed = Task.objects.filter(
        user=user, status=Task.Status.COMPLETED, completed_at__gte=start, completed_at__lt=end,
    ).select_related("project").order_by("completed_at")
    focus_seconds = sum(FocusSession.objects.filter(
        user=user, start_at__gte=start, start_at__lt=end, end_at__isnull=False,
    ).values_list("duration_seconds", flat=True))
    colors = {c: 0 for c in DayLog.Color.values}
    for color in DayLog.objects.filter(user=user, date__gte=week_start,
                                       date__lte=week_end).values_list("color", flat=True):
        colors[color] += 1
    today = local_now(user).date()
    occurrences = SlotOccurrence.objects.filter(
        user=user, date__gte=week_start, date__lte=week_end,
    ).select_related("slot__project", "task")

    def brief(tasks):
        return [{"id": t.id, "title": t.title, "project": t.project_id} for t in tasks]

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "review_at": review_moment(user, config, week_start).isoformat(),
        "score": week_score(user, week_start),
        "occurrences": SlotOccurrenceSerializer(occurrences, many=True).data,
        "completed": brief(completed[:50]),
        "focus_minutes": focus_seconds // 60,
        "blocked": brief(_open_tasks(Task.objects.filter(user=user)).filter(
            postpone_count__gte=POSTPONE_THRESHOLD).select_related("project")),
        "amnesty": brief(amnesty_candidates(user).select_related("project")),
        "inbox_count": _open_tasks(Task.objects.filter(user=user, project__is_inbox=True)).count(),
        "proposals_count": Task.objects.filter(
            user=user, proposed=True, status=Task.Status.NORMAL, trashed_at__isnull=True,
        ).count(),
        "day_colors": colors,
        "jokers_remaining": jokers_remaining(user, today),
        "level": config.level,
        "suggestion": level_suggestion(user, week_start, config.level),
        "completed_at": review.completed_at.isoformat() if review and review.completed_at else None,
        "notes": review.notes if review else "",
    }


def complete_review(user, week_start, level=None, amnesty=True, notes="", actor="user"):
    """Valide une revue (M41.2) : amnistie, niveau, score figé. Idempotent."""
    config = MethodConfig.for_user(user)
    review, _ = WeeklyReview.objects.get_or_create(user=user, week_start=week_start)
    if review.completed_at is not None:
        return review
    if amnesty:
        for task in amnesty_candidates(user):
            # Mise à jour directe : l'amnistie n'est pas un report (M40.1).
            Task.objects.filter(pk=task.pk).update(due_date=None, start_date=None)
            ActivityLog.log(task, "amnesty", actor=actor)
    review.level_before = config.level
    if level:
        config.level = int(level)
        config.save(update_fields=["level"])
    review.level_after = config.level
    review.rate = week_score(user, week_start)["rate"]
    review.notes = notes or ""
    review.completed_at = timezone.now()
    review.save()
    emit(user, "review.completed", review_summary(user, week_start), actor=actor)
    return review


def diagnose(task, reason, actor="user"):
    """Diagnostic d'une tâche qui coince (M40.3) → remède concret."""
    if reason not in Blocker.values:
        raise ValidationError({"reason": f"Raison inconnue (attendu : {', '.join(Blocker.values)})."})
    if reason == Blocker.USELESS:
        task.set_status(Task.Status.WONT_DO, actor=actor)
    task.blocker = reason
    task.postpone_count = 0
    task.last_actor = actor
    task.save(update_fields=["blocker", "postpone_count", "last_actor"])
    ActivityLog.log(task, "diagnosed", actor=actor, reason=reason)
    return REMEDIES[reason]

