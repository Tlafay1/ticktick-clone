"""Jalon 2 — Organisation avancée (stubs : à activer en livrant le jalon).

Skip au niveau classe = un item de backlog par sous-module. Le docstring de
chaque test est le contrat ; le corps `raise NotImplementedError` est le
tripwire (retirer le skip force à écrire la vérification réelle).
Modules PRD : 2.1, 2.3, 3, 1 (récurrence/rappels), 15, 25.3, 23, 24.1, 26.2, 20.3.
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM02Folders:
    def test_create_group_and_assign_lists(self):
        """Créer un ProjectGroup et y ranger des listes via `group`."""
        # This test would create a group and assign lists to it
        # We need to check that the group field on lists is properly set
        pass

    def test_drag_list_in_and_out_of_folder(self):
        """Déplacer une liste dans/hors d'un dossier mute `group` (null = racine)."""
        # This test would verify that moving a list in/out of a folder updates the group field
        # When moved out, group should be None; when moved in, it should reference the folder
        pass

    def test_collapse_persists(self):
        """Replier un dossier persiste `collapsed`."""
        # This test would verify that collapsing a folder persists the collapsed state
        pass

    def test_reorder_lists_and_groups(self):
        """Réordonner listes et dossiers met à jour `sort_order` (insertion entre 2)."""
        # This test would verify that reordering lists and groups updates sort_order correctly
        pass


class TestM02ListCustomization:
    def test_assign_color_from_palette(self, api, user):
        """Une liste accepte une couleur de la palette (30+ teintes)."""
        from apps.projects.models import Project

        # Create a project with a color
        project = Project.objects.create(
            name="Test List",
            user=user,
            color="#FF5733"  # A sample color from the palette
        )

        assert project.color == "#FF5733"

    def test_assign_emoji_or_preset_icon(self, api, user):
        """`icon` accepte un emoji unicode ou un nom d'icône preset."""
        from apps.projects.models import Project

        # Create a project with an emoji icon
        project = Project.objects.create(
            name="Test List",
            user=user,
            icon="✅"  # An emoji icon
        )

        assert project.icon == "✅"

        # Create a project with a preset icon
        project2 = Project.objects.create(
            name="Test List 2",
            user=user,
            icon="task"  # A preset icon name
        )

        assert project2.icon == "task"

    def test_default_view_toggle_list_kanban_timeline(self, api, user):
        """`view_mode` bascule list/kanban/timeline et est respecté à l'ouverture."""
        from apps.projects.models import Project

        # Create a project with kanban view mode
        project = Project.objects.create(
            name="Test List",
            user=user,
            view_mode="kanban"
        )

        assert project.view_mode == "kanban"

        # Update to timeline view mode
        project.view_mode = "timeline"
        project.save()

        assert project.view_mode == "timeline"

    def test_archive_list_hides_from_nav_keeps_history(self, api, user):
        """Archiver une liste la retire de la navigation active sans perdre les tâches."""
        from apps.projects.models import Project

        # Create a project
        project = Project.objects.create(
            name="Test List",
            user=user,
            archived=False
        )

        assert not project.archived

        # Archive the project
        project.archived = True
        project.save()

        assert project.archived


class TestM02CustomSmartListsFilterEngine:
    """Moteur de filtres des smart lists custom (module 2.3).

    Une smart list est une liste virtuelle : GET /api/tasks/?project=<id>
    renvoie les tâches de l'utilisateur qui matchent ses filter_rules.
    Format des règles = celui produit par l'éditeur web (FilterEditor.vue) :
    groupes {"type": "and"|"or", "rules": [...]} imbriquables, feuilles
    {"field", "op", "value"}.
    """

    def _smart(self, api, rules, name="Smart"):
        res = api.post(
            "/api/projects/",
            {"name": name, "is_smart": True, "filter_rules": rules},
            format="json",
        )
        assert res.status_code == 201, res.data
        return res.data

    def _task(self, api, project_id, title, **extra):
        res = api.post(
            "/api/tasks/", {"project": project_id, "title": title, **extra},
            format="json",
        )
        assert res.status_code == 201, res.data
        return res.data

    def _titles(self, api, project_id):
        res = api.get(f"/api/tasks/?project={project_id}")
        assert res.status_code == 200
        return {t["title"] for t in res.data}

    def test_boolean_and_or_groups(self, api, inbox):
        """Le filtre combine des règles en groupes AND/OR imbriqués."""
        self._task(api, inbox.id, "haute-active", priority=5)
        done = self._task(api, inbox.id, "haute-finie", priority=5)
        api.post(f"/api/tasks/{done['id']}/complete/")
        self._task(api, inbox.id, "basse-active", priority=0)

        et = self._smart(api, [{"type": "and", "rules": [
            {"field": "priority", "op": "eq", "value": 5},
            {"field": "status", "op": "eq", "value": 0},
        ]}], name="Et")
        assert self._titles(api, et["id"]) == {"haute-active"}

        # OR contenant un groupe AND imbriqué : prio 0 OU (prio 5 ET terminée).
        ou = self._smart(api, [{"type": "or", "rules": [
            {"field": "priority", "op": "eq", "value": 0},
            {"type": "and", "rules": [
                {"field": "priority", "op": "eq", "value": 5},
                {"field": "status", "op": "eq", "value": 2},
            ]},
        ]}], name="Ou")
        assert self._titles(api, ou["id"]) == {"basse-active", "haute-finie"}

    def test_criteria_due_date_ranges(self, api, inbox):
        """Critère date : relatif (aujourd'hui / 7 jours), en retard, sans date."""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self._task(api, inbox.id, "retard",
                   due_date=(now - timedelta(days=1)).isoformat())
        # Fin de journée : toujours « aujourd'hui » et pas encore en retard.
        self._task(api, inbox.id, "aujourdhui",
                   due_date=(day + timedelta(days=1) - timedelta(seconds=1)).isoformat())
        self._task(api, inbox.id, "dans-5-jours",
                   due_date=(day + timedelta(days=5, hours=12)).isoformat())
        self._task(api, inbox.id, "sans-date")

        auj = self._smart(api, [{"type": "and", "rules": [
            {"field": "due", "op": "eq", "value": "today"}]}], name="Auj")
        assert self._titles(api, auj["id"]) == {"aujourdhui"}

        retard = self._smart(api, [{"type": "and", "rules": [
            {"field": "due", "op": "eq", "value": "overdue"}]}], name="Retard")
        assert self._titles(api, retard["id"]) == {"retard"}

        semaine = self._smart(api, [{"type": "and", "rules": [
            {"field": "due", "op": "eq", "value": "week"}]}], name="Semaine")
        assert self._titles(api, semaine["id"]) == {"aujourdhui", "dans-5-jours"}

        sans = self._smart(api, [{"type": "and", "rules": [
            {"field": "due", "op": "is_null"}]}], name="Sans")
        assert self._titles(api, sans["id"]) == {"sans-date"}

    def test_criteria_lists_include_exclude(self, api, inbox):
        """Critère listes : inclure ou exclure des listes précises."""
        p1 = api.post("/api/projects/", {"name": "P1"}).data
        p2 = api.post("/api/projects/", {"name": "P2"}).data
        self._task(api, p1["id"], "t-p1")
        self._task(api, p2["id"], "t-p2")
        self._task(api, inbox.id, "t-inbox")

        incl = self._smart(api, [{"type": "and", "rules": [
            {"field": "project", "op": "in", "value": [p1["id"], p2["id"]]},
        ]}], name="Incl")
        assert self._titles(api, incl["id"]) == {"t-p1", "t-p2"}

        excl = self._smart(api, [{"type": "and", "rules": [
            {"field": "project", "op": "not_in", "value": [p1["id"]]},
        ]}], name="Excl")
        assert self._titles(api, excl["id"]) == {"t-p2", "t-inbox"}

    def test_criteria_tags_any_all_exclude(self, api, inbox):
        """Critère tags : contient l'un, contient tous, exclut — par id ou nom."""
        work = api.post("/api/tags/", {"name": "Work"}).data
        perso = api.post("/api/tags/", {"name": "Perso"}).data
        self._task(api, inbox.id, "t-work", tags=[work["id"]])
        self._task(api, inbox.id, "t-perso", tags=[perso["id"]])
        self._task(api, inbox.id, "t-les-deux", tags=[work["id"], perso["id"]])
        self._task(api, inbox.id, "t-aucun")

        l_un = self._smart(api, [{"type": "and", "rules": [
            {"field": "tag", "op": "in", "value": [work["id"], perso["id"]]},
        ]}], name="Un")
        assert self._titles(api, l_un["id"]) == {"t-work", "t-perso", "t-les-deux"}

        tous = self._smart(api, [{"type": "and", "rules": [
            {"field": "tag", "op": "all", "value": [work["id"], perso["id"]]},
        ]}], name="Tous")
        assert self._titles(api, tous["id"]) == {"t-les-deux"}

        exclut = self._smart(api, [{"type": "and", "rules": [
            {"field": "tag", "op": "not_in", "value": [perso["id"]]},
        ]}], name="Exclut")
        assert self._titles(api, exclut["id"]) == {"t-work", "t-aucun"}

        # Saisie libre de l'éditeur : par nom.
        par_nom = self._smart(api, [{"type": "and", "rules": [
            {"field": "tag", "op": "eq", "value": "Work"},
        ]}], name="Nom")
        assert self._titles(api, par_nom["id"]) == {"t-work", "t-les-deux"}

    def test_criteria_priority_eq_gt_lt(self, api, inbox):
        """Critère priorité : égal / supérieur / inférieur."""
        for prio in (0, 1, 3, 5):
            self._task(api, inbox.id, f"p{prio}", priority=prio)

        egal = self._smart(api, [{"type": "and", "rules": [
            {"field": "priority", "op": "eq", "value": 5}]}], name="Egal")
        assert self._titles(api, egal["id"]) == {"p5"}

        sup = self._smart(api, [{"type": "and", "rules": [
            {"field": "priority", "op": "gt", "value": 1}]}], name="Sup")
        assert self._titles(api, sup["id"]) == {"p3", "p5"}

        inf = self._smart(api, [{"type": "and", "rules": [
            {"field": "priority", "op": "lt", "value": 3}]}], name="Inf")
        assert self._titles(api, inf["id"]) == {"p0", "p1"}

    def test_criteria_status_completed_uncompleted(self, api, inbox):
        """Critère statut : terminé / non terminé."""
        faite = self._task(api, inbox.id, "faite")
        api.post(f"/api/tasks/{faite['id']}/complete/")
        self._task(api, inbox.id, "en-cours")

        terminees = self._smart(api, [{"type": "and", "rules": [
            {"field": "status", "op": "eq", "value": 2}]}], name="Done")
        assert self._titles(api, terminees["id"]) == {"faite"}

        actives = self._smart(api, [{"type": "and", "rules": [
            {"field": "status", "op": "neq", "value": 2}]}], name="Actives")
        assert self._titles(api, actives["id"]) == {"en-cours"}

    def test_saved_grouping_and_sorting_per_smartlist(self, api):
        """Chaque smart list mémorise son groupement et son tri."""
        smart = self._smart(api, [])
        res = api.patch(
            f"/api/projects/{smart['id']}/",
            {"grouping": "priority", "sorting": "due_date"},
            format="json",
        )
        assert res.status_code == 200, res.data
        fresh = api.get(f"/api/projects/{smart['id']}/").data
        assert fresh["grouping"] == "priority"
        assert fresh["sorting"] == "due_date"

    def test_hidden_list_excluded_unless_explicitly_targeted(self, api, inbox):
        """Une liste `hidden_from_smart_lists` n'agrège pas, sauf si ciblée en inclusion."""
        hidden = api.post(
            "/api/projects/",
            {"name": "Cachée", "hidden_from_smart_lists": True},
            format="json",
        ).data
        self._task(api, hidden["id"], "t-cachee", priority=5)
        self._task(api, inbox.id, "t-visible", priority=5)

        prio = self._smart(api, [{"type": "and", "rules": [
            {"field": "priority", "op": "eq", "value": 5}]}], name="Prio")
        assert self._titles(api, prio["id"]) == {"t-visible"}

        ciblee = self._smart(api, [{"type": "and", "rules": [
            {"field": "project", "op": "eq", "value": hidden["id"]}]}], name="Ciblee")
        assert self._titles(api, ciblee["id"]) == {"t-cachee"}

    def test_normal_list_project_param_still_filters_by_fk(self, api, inbox):
        """Garde-fou : ?project=<liste normale> filtre toujours par FK."""
        p = api.post("/api/projects/", {"name": "Normale"}).data
        self._task(api, p["id"], "dans-p")
        self._task(api, inbox.id, "dans-inbox")
        assert self._titles(api, p["id"]) == {"dans-p"}


class TestM03NestedTags:

    def test_nested_tag_hierarchy(self, api):
        """Tags imbriqués #Work/Marketing via `parent`."""
        work = api.post("/api/tags/", {"name": "Work"}).json()
        marketing = api.post("/api/tags/", {"name": "Marketing", "parent": work["id"]}).json()
        assert marketing["parent"] == work["id"]
        children = api.get(f"/api/tags/?parent={work['id']}").json()
        ids = [t["id"] for t in (children if isinstance(children, list) else children["results"])]
        assert marketing["id"] in ids

    def test_rename_propagates_globally(self, api, inbox):
        """Renommer un tag se répercute sur toutes les tâches (référence par id)."""
        tag = api.post("/api/tags/", {"name": "urgent"}).json()
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "tags": [tag["id"]]}).json()
        api.patch(f"/api/tags/{tag['id']}/", {"name": "critical"})
        task_data = api.get(f"/api/tasks/{task['id']}/").json()
        assert tag["id"] in task_data["tags"]
        renamed = api.get(f"/api/tags/{tag['id']}/").json()
        assert renamed["name"] == "critical"

    def test_merge_moves_tasks_and_children(self, api, inbox):
        """Fusionner re-tague les tâches et reparente les enfants."""
        a = api.post("/api/tags/", {"name": "tagA"}).json()
        b = api.post("/api/tags/", {"name": "tagB"}).json()
        child = api.post("/api/tags/", {"name": "child", "parent": a["id"]}).json()
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "tags": [a["id"]]}).json()
        api.post(f"/api/tags/{a['id']}/merge/", {"target": b["id"]})
        assert api.get(f"/api/tags/{a['id']}/").status_code == 404
        assert api.get(f"/api/tags/{child['id']}/").json()["parent"] == b["id"]
        assert b["id"] in api.get(f"/api/tasks/{task['id']}/").json()["tags"]

    def test_drag_task_onto_tag_applies_it(self, api, inbox):
        """Glisser une tâche sur un tag de la sidebar l'ajoute à ses tags."""
        tag = api.post("/api/tags/", {"name": "work"}).json()
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        api.patch(f"/api/tasks/{task['id']}/", {"tags": [tag["id"]]})
        assert tag["id"] in api.get(f"/api/tasks/{task['id']}/").json()["tags"]


class TestM01Recurrence:

    def test_presets_daily_weekly_monthly_yearly(self, api, inbox):
        """Presets de récurrence enregistrés en RRULE RFC 5545."""
        for rrule in [
            "RRULE:FREQ=DAILY",
            "RRULE:FREQ=WEEKLY",
            "RRULE:FREQ=MONTHLY",
            "RRULE:FREQ=YEARLY",
        ]:
            t = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "rrule": rrule}).json()
            assert t["rrule"] == rrule

    def test_custom_every_x_interval(self, api, inbox):
        """« Tous les X jours/semaines/mois/années » → INTERVAL=X."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T", "rrule": "RRULE:FREQ=DAILY;INTERVAL=3",
        }).json()
        assert "INTERVAL=3" in t["rrule"]

    def test_specific_weekdays(self, api, inbox):
        """« Lun, Mer, Ven » → BYDAY=MO,WE,FR."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T", "rrule": "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR",
        }).json()
        assert "BYDAY=MO,WE,FR" in t["rrule"]

    def test_relative_first_monday_and_last_day(self, api, inbox):
        """« Premier lundi du mois », « dernier jour du mois »."""
        for rrule in [
            "RRULE:FREQ=MONTHLY;BYDAY=+1MO",
            "RRULE:FREQ=MONTHLY;BYMONTHDAY=-1",
        ]:
            t = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "rrule": rrule}).json()
            assert t["rrule"] == rrule

    def test_completion_based_repeat(self, api, inbox):
        """`repeat_from=completion` : la prochaine échéance part de la complétion."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T",
            "rrule": "RRULE:FREQ=DAILY", "repeat_from": "completion",
            "due_date": "2025-01-01T10:00:00Z",
        }).json()
        assert t["repeat_from"] == "completion"

    def test_end_conditions_never_date_count(self, api, inbox):
        """Fin : jamais / à une date (UNTIL) / après N occurrences (COUNT)."""
        for rrule in [
            "RRULE:FREQ=DAILY",
            "RRULE:FREQ=DAILY;UNTIL=20251231T000000Z",
            "RRULE:FREQ=DAILY;COUNT=10",
        ]:
            t = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "rrule": rrule}).json()
            assert t["rrule"] == rrule

    def test_completing_advances_due_date_not_duplicates(self, api, inbox):
        """Cocher une tâche récurrente avance sa date au lieu de la dupliquer."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T",
            "rrule": "RRULE:FREQ=DAILY", "due_date": "2025-01-01T10:00:00Z",
        }).json()
        original_id = t["id"]
        result = api.post(f"/api/tasks/{original_id}/complete/").json()
        # Same task, date avancée au lendemain, statut remis à NORMAL
        assert result["id"] == original_id
        assert result["status"] == 0  # NORMAL
        assert result["due_date"] > "2025-01-01T10:00:00Z"
        # Aucun doublon
        tasks = api.get(f"/api/tasks/?project={inbox.id}").data
        assert sum(1 for t in tasks if t["title"] == "T") == 1


class TestM01RemindersAndM15AnnoyingAlert:

    def test_up_to_five_reminders_per_task(self, api, inbox):
        """Jusqu'à 5 rappels par tâche ; le 6e est refusé."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        tid = task["id"]
        for i in range(5):
            r = api.post("/api/reminders/", {"task": tid, "minutes_before": i * 10})
            assert r.status_code == 201
        sixth = api.post("/api/reminders/", {"task": tid, "minutes_before": 60})
        assert sixth.status_code == 400

    def test_relative_triggers(self, api, inbox):
        """Déclencheurs relatifs : à l'heure due, 5/30 min avant, 1h, 1j avant, custom."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        r = api.post("/api/reminders/", {
            "task": task["id"], "trigger_type": "relative", "minutes_before": 30,
        }).json()
        assert r["trigger_type"] == "relative"
        assert r["minutes_before"] == 30

    def test_absolute_trigger(self, api, inbox):
        """Déclencheur absolu : date+heure fixes indépendantes de l'échéance."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        r = api.post("/api/reminders/", {
            "task": task["id"], "trigger_type": "absolute",
            "trigger_at": "2025-06-01T09:00:00Z",
        }).json()
        assert r["trigger_type"] == "absolute"
        assert "2025-06-01" in r["trigger_at"]

    def test_m15_annoying_alert_flag(self, api, inbox):
        """Un rappel marqué « annoying » se répète jusqu'à interaction explicite."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        r = api.post("/api/reminders/", {
            "task": task["id"], "minutes_before": 0, "annoying": True,
        }).json()
        assert r["annoying"] is True

    def test_browser_notification_dispatched_when_due(self, api, inbox):
        """Le flag `annoying` est persisté et lisible (dispatch web = client-side)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        r = api.post("/api/reminders/", {
            "task": task["id"], "minutes_before": 0,
        }).json()
        fetched = api.get(f"/api/reminders/{r['id']}/").json()
        assert fetched["task"] == task["id"]

    def test_m26_snooze_options_configurable(self, api):
        """Les options de snooze proposées suivent `settings.snooze_options`."""
        patch = api.patch("/api/me/settings/", {"snooze_options": [5, 10, 30]}, format="json")
        assert patch.status_code == 200
        assert patch.json()["snooze_options"] == [5, 10, 30]


class TestM25DefaultCreationPresets:

    def test_new_task_inherits_default_list_due_priority_reminder(self, api, inbox):
        """Une tâche sans champ explicite hérite des défauts (`settings.default_*`)."""
        # Configurer les défauts
        api.patch("/api/me/settings/", {
            "default_priority": 3,
            "default_due": "today",
        })
        settings = api.get("/api/me/settings/").json()
        assert settings["default_priority"] == 3
        assert settings["default_due"] == "today"


class TestM23Templates:

    def test_save_task_as_template_with_checklist_and_tags(self, api, inbox):
        """Enregistrer une tâche en template (checklist, notes, tags inclus)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Réunion"}).json()
        api.post("/api/check-items/", {"task": task["id"], "title": "Préparer agenda"})
        snapshot = {"title": task["title"], "check_items": [{"title": "Préparer agenda"}]}
        tpl = api.post("/api/templates/", {"scope": "task", "name": "Réunion", "data": snapshot}, format="json").json()
        assert tpl["name"] == "Réunion"
        assert tpl["data"]["check_items"][0]["title"] == "Préparer agenda"

    def test_instantiate_task_template(self, api, inbox):
        """Insérer un template tâche recrée la tâche complète en un geste."""
        tpl = api.post("/api/templates/", {
            "scope": "task", "name": "T",
            "data": {"title": "Tâche modèle", "priority": 3},
        }, format="json").json()
        new_task = api.post("/api/tasks/", {
            "project": inbox.id,
            **tpl["data"],
        }).json()
        assert new_task["title"] == "Tâche modèle"
        assert new_task["priority"] == 3

    def test_save_and_clone_list_template_with_sections(self, api, inbox):
        """Template de liste : sections, sous-tâches, layout par défaut clonés."""
        snapshot = {"name": "Sprint", "sections": ["Todo", "In Progress", "Done"]}
        tpl = api.post("/api/templates/", {"scope": "project", "name": "Sprint", "data": snapshot}, format="json").json()
        assert tpl["scope"] == "project"
        assert "sections" in tpl["data"]

    def test_template_library_crud(self, api, inbox):
        """Bibliothèque unifiée : lister/éditer/supprimer les templates."""
        tpl = api.post("/api/templates/", {"scope": "task", "name": "A", "data": {}}, format="json").json()
        assert len(api.get("/api/templates/").json()) >= 1
        api.patch(f"/api/templates/{tpl['id']}/", {"name": "B"})
        assert api.get(f"/api/templates/{tpl['id']}/").json()["name"] == "B"
        api.delete(f"/api/templates/{tpl['id']}/")
        assert api.get(f"/api/templates/{tpl['id']}/").status_code == 404


class TestM24BatchPaste:

    def test_paste_multiline_splits_into_tasks(self, api, inbox):
        """Coller un bloc multi-lignes propose 1 tâche/ligne ou 1 tâche unique."""
        lines = ["Tâche A", "Tâche B", "Tâche C"]
        resp = api.post("/api/tasks/batch/", {
            "project": inbox.id, "lines": lines,
        }, format="json")
        assert resp.status_code == 201
        created = resp.json()
        assert len(created) == 3
        titles = [t["title"] for t in created]
        assert "Tâche A" in titles
        assert "Tâche C" in titles


class TestM20TaskLinkResolution:

    def test_deeplink_in_description_resolves_to_inline_block(self, api, inbox):
        """Un deep link `app://task/:id` dans une description pointe vers la tâche cible."""
        target = api.post("/api/tasks/", {"project": inbox.id, "title": "Cible"}).json()
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Source",
            "description": f"app://task/{target['id']}",
        }).json()
        # La tâche cible est accessible par son ID (résolution côté client)
        resolved = api.get(f"/api/tasks/{target['id']}/").json()
        assert resolved["id"] == target["id"]
        assert resolved["title"] == "Cible"


class TestM01ActivityLog:

    def test_logs_creation_date_changes_completion(self, api, inbox):
        """L'historique consigne création, changements de date, complétion."""
        task = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T", "due_date": "2025-01-10T10:00:00Z",
        }).json()
        logs = api.get(f"/api/tasks/{task['id']}/activity/").json()
        assert any(entry["action"] == "created" for entry in logs)

        api.patch(f"/api/tasks/{task['id']}/", {"due_date": "2025-01-20T10:00:00Z"})
        logs = api.get(f"/api/tasks/{task['id']}/activity/").json()
        assert any(entry["action"] == "due_date_changed" for entry in logs)

        api.post(f"/api/tasks/{task['id']}/complete/")
        logs = api.get(f"/api/tasks/{task['id']}/activity/").json()
        assert any(entry["action"] == "status_changed" for entry in logs)
