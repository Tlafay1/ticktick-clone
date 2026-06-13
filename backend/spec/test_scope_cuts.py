"""Périmètre coupé — la définition de « terminé » en creux.

Ces comportements du PRD sont DÉLIBÉRÉMENT absents. Les consigner ici garantit
qu'ils sont des décisions tracées, pas des oublis. Ils ne deviendront jamais
verts (corps `pass`, pas de tripwire). La `reason` documente pourquoi.
"""
import pytest

pytestmark = pytest.mark.spec


class TestCutMonoUser:
    """Mono-utilisateur : aucune collaboration."""
    pytestmark = pytest.mark.skip(reason="COUPÉ — mono-utilisateur (pas de collab)")

    def test_m09_list_sharing_roles_assignment(self):
        """Module 9 entier : partage de listes, rôles Owner/Member/Viewer, assignation,
        flux d'activité collaboratif, @mentions, smart list « Assigned to me »,
        filtres par assigné, DND de liste partagée (M28.1)."""

    def test_filter_criteria_assignee(self):
        """Critère de filtre « assignee » (sans objet en mono-utilisateur)."""


class TestCutOnUserRequest:
    """Coupé explicitement à la demande de l'utilisateur."""
    pytestmark = pytest.mark.skip(reason="COUPÉ — demande utilisateur")

    def test_m08_notes_module(self):
        """Module 8 entier : bascule tâche↔note, outliner, templates de notes.
        (Les descriptions markdown riches des tâches restent, elles.)"""

    def test_voice_dictation_input(self):
        """Saisie/dictée vocale (Siri/Assistant, dictée widgets & Quick Ball)."""

    def test_m29_focus_autopause_on_incoming_call(self):
        """Pause auto du focus sur appel entrant."""

    def test_no_captcha_ratelimit_email_verification(self):
        """Aucun captcha, rate-limiting ni vérification d'email — système ouvert."""


class TestCutIntegrations:
    """Intégrations externes coupées (seul l'ICS read-only est gardé, cf. J3)."""
    pytestmark = pytest.mark.skip(reason="COUPÉ — intégrations externes")

    def test_m04_oauth_google_outlook_twoway_and_caldav(self):
        """Sync bidirectionnelle Google/Outlook (OAuth) et abonnement CalDAV."""

    def test_m20_email_to_task_mailbox(self):
        """Mailbox email-to-task (todo+abc@…)."""

    def test_m19_ai_suggested_tasks(self):
        """Suggestions de tâches par IA."""

    def test_m34_notion_and_apple_health(self):
        """Sync Notion bidirectionnelle (M34.1) et intégration Apple Health (M34.2)."""


class TestCutOutOfClientScope:
    """Hors périmètre : clients web / Android / Windows uniquement."""
    pytestmark = pytest.mark.skip(reason="COUPÉ — hors périmètre client")

    def test_m20_browser_web_clipper_extension(self):
        """Extension navigateur / Web Clipper (4e type de client)."""

    def test_m27_wearables_watch_apps(self):
        """Apple Watch / Wear OS (M27.3)."""

    def test_ios_macos_linux_clients(self):
        """Clients iOS, macOS (menu bar), Linux ; Live Activities / Dynamic Island."""


class TestCutHallucinatedFeatures:
    """Absents du vrai TickTick (corrections du PRD)."""
    pytestmark = pytest.mark.skip(reason="COUPÉ — non présent dans TickTick")

    def test_m01_task_merging(self):
        """« Task Merging » (fusion de plusieurs tâches). La conversion
        tâche↔sous-tâche par drag, elle, est conservée (J2)."""

    def test_m11_desktop_sticky_notes(self):
        """Sticky notes flottantes sur le bureau Windows."""

    def test_m11_shake_to_clean(self):
        """« Shake to Clean » (secouer pour archiver)."""

    def test_per_task_email_reminders(self):
        """Rappels par email par tâche (on garde push/notif système)."""
