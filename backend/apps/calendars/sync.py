"""Import des événements d'un abonnement ICS (module 4.3, lecture seule).

Les récurrences (RRULE) sont dépliées sur une fenêtre glissante
[-30 j, +365 j] avec un plafond d'occurrences par événement — suffisant pour
l'affichage calendrier, sans stocker un flux infini.
"""
import logging
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_tz

from django.utils import timezone

logger = logging.getLogger(__name__)

WINDOW_PAST_DAYS = 30
WINDOW_FUTURE_DAYS = 365
MAX_OCCURRENCES = 500


def _aware(value):
    """Normalise date/datetime ICS en datetime aware (UTC pour les naïfs)."""
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, dt_tz.utc)
    if isinstance(value, date):
        return timezone.make_aware(datetime.combine(value, time.min), dt_tz.utc)
    return None


def parse_ics(text, now=None):
    """Extrait les occurrences d'un flux ICS.

    Retourne une liste de dicts {uid, title, location, start, end, is_all_day},
    récurrences dépliées dans la fenêtre.
    """
    from dateutil.rrule import rrulestr
    from icalendar import Calendar

    now = now or timezone.now()
    window_start = now - timedelta(days=WINDOW_PAST_DAYS)
    window_end = now + timedelta(days=WINDOW_FUTURE_DAYS)

    cal = Calendar.from_ical(text)
    occurrences = []
    for component in cal.walk("VEVENT"):
        uid = str(component.get("UID", ""))[:255]
        title = str(component.get("SUMMARY", ""))[:255]
        location = str(component.get("LOCATION", ""))[:255]
        dtstart_prop = component.get("DTSTART")
        if not dtstart_prop:
            continue
        raw_start = dtstart_prop.dt
        is_all_day = not isinstance(raw_start, datetime)
        start = _aware(raw_start)
        dtend_prop = component.get("DTEND")
        end = _aware(dtend_prop.dt) if dtend_prop else None
        duration = (end - start) if end else None

        rrule_prop = component.get("RRULE")
        if rrule_prop is None:
            if window_start <= start <= window_end:
                occurrences.append({
                    "uid": uid, "title": title, "location": location,
                    "start": start, "end": end, "is_all_day": is_all_day,
                })
            continue

        # Récurrence : déplier dans la fenêtre (les datetimes naïfs de la
        # RRULE sont comparés dans le référentiel du DTSTART).
        try:
            rule = rrulestr(rrule_prop.to_ical().decode(), dtstart=start)
            count = 0
            for occ in rule.between(window_start, window_end, inc=True):
                occ = _aware(occ)
                occurrences.append({
                    "uid": uid, "title": title, "location": location,
                    "start": occ, "end": (occ + duration) if duration else None,
                    "is_all_day": is_all_day,
                })
                count += 1
                if count >= MAX_OCCURRENCES:
                    break
        except (ValueError, TypeError) as exc:
            logger.warning("RRULE ICS illisible (uid=%s) : %s", uid, exc)
    return occurrences


def refresh_subscription(subscription):
    """Télécharge et réimporte les événements d'un abonnement. Retourne le nb importé."""
    import requests

    from .models import CalendarEvent

    try:
        resp = requests.get(subscription.url, timeout=15)
        resp.raise_for_status()
        # Octets bruts : RFC 5545 impose UTF-8, mais `resp.text` retombe sur
        # latin-1 quand le serveur n'annonce pas de charset (mojibake).
        occurrences = parse_ics(resp.content)
    except Exception as exc:  # réseau/parse : on garde les anciens événements
        logger.warning("Refresh ICS échoué (%s) : %s", subscription.url[:64], exc)
        return 0

    # Remplacement atomique du contenu de l'abonnement.
    CalendarEvent.objects.filter(subscription=subscription).delete()
    seen = set()
    events = []
    for o in occurrences:
        key = (o["uid"], o["start"])
        if key in seen:
            continue
        seen.add(key)
        events.append(CalendarEvent(subscription=subscription, **o))
    CalendarEvent.objects.bulk_create(events)
    subscription.last_synced_at = timezone.now()
    subscription.save(update_fields=["last_synced_at"])
    return len(events)
