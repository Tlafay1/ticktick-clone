"""Journal intime (API 0.3.0) : merge incrémental d'une journée racontée à un
agent, re-rendu de la section `## Journal` dans la daily note Obsidian."""
import json
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db

DATE = "2026-07-25"


@pytest.fixture
def vault(tmp_path, settings):
    settings.OBSIDIAN_VAULT_PATH = str(tmp_path)
    return tmp_path


@pytest.fixture
def captured(monkeypatch):
    calls = []
    monkeypatch.setattr("apps.webhooks.tasks.deliver_webhook.delay",
                        lambda *args: calls.append(args))
    return calls


def note(vault, name=f"{DATE}.md"):
    return (vault / name).read_text(encoding="utf-8")


# --- Merge incrémental -------------------------------------------------------

def test_journee_completee_au_fil_de_l_eau(api, vault):
    """Un moment à midi, un le soir, le ressenti global au coucher : la section
    est consolidée, pas empilée."""
    r1 = api.post("/api/journal/entries/",
                  {"date": DATE, "highlights": ["Super déjeuner avec Alex"]},
                  format="json")
    assert r1.status_code == 201
    r2 = api.post("/api/journal/entries/",
                  {"date": DATE, "lows": ["Réunion interminable"],
                   "mood": "fatigué mais content"},
                  format="json")
    assert r2.status_code == 201

    data = r2.json()
    assert len(data["moments"]) == 2
    assert data["mood"] == "fatigué mais content"

    content = note(vault)
    assert content.count("## Journal") == 1
    assert "**Ressenti général** : fatigué mais content" in content
    assert "### Moments positifs" in content
    assert "Super déjeuner avec Alex" in content
    assert "### Moments négatifs" in content
    assert "Réunion interminable" in content


def test_get_relit_l_etat_du_jour(api, vault):
    api.post("/api/journal/entries/",
             {"date": DATE, "anecdotes": ["Le chat a volé un croissant"]},
             format="json")
    r = api.get(f"/api/journal/entries/{DATE}/")
    assert r.status_code == 200
    data = r.json()
    assert data["moments"][0]["kind"] == "anecdote"
    assert "### Anecdotes" in data["rendered_markdown"]


def test_payload_vide_refuse(api, vault):
    assert api.post("/api/journal/entries/", {"date": DATE},
                    format="json").status_code == 400


def test_date_defaut_aujourdhui_dans_le_fuseau(api, vault):
    r = api.post("/api/journal/entries/",
                 {"tz": "Europe/Paris", "feelings": ["Serein"]}, format="json")
    assert r.status_code == 201
    local_today = timezone.localtime(timezone.now(), ZoneInfo("Europe/Paris")).date()
    assert r.json()["date"] == local_today.isoformat()
    # Les heures de la note sont rendues dans le fuseau de la journée.
    from apps.journal.models import JournalMoment
    moment = JournalMoment.objects.get()
    stamp = timezone.localtime(moment.noted_at, ZoneInfo("Europe/Paris")).strftime("%H:%M")
    assert f"**{stamp}** — Serein" in note(vault, f"{local_today.isoformat()}.md")


# --- Résolution de la daily note --------------------------------------------

def test_config_daily_notes_du_vault(api, vault):
    """Le chemin de la daily note vient de `.obsidian/daily-notes.json`."""
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "daily-notes.json").write_text(
        json.dumps({"folder": "Notes/Daily", "format": "DD-MM-YYYY"}))
    r = api.post("/api/journal/entries/", {"date": DATE, "highlights": ["x"]},
                 format="json")
    assert r.json()["note_path"] == "Notes/Daily/25-07-2026.md"
    assert (vault / "Notes/Daily/25-07-2026.md").is_file()


def test_fallback_env_sans_config_vault(api, vault, settings):
    settings.JOURNAL_DAILY_FOLDER = "Quotidien"
    r = api.post("/api/journal/entries/", {"date": DATE, "highlights": ["x"]},
                 format="json")
    assert r.json()["note_path"] == f"Quotidien/{DATE}.md"


def test_note_creee_depuis_le_template(api, vault):
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "daily-notes.json").write_text(
        json.dumps({"template": "Templates/Daily"}))
    (vault / "Templates").mkdir()
    (vault / "Templates" / "Daily.md").write_text(
        "# {{title}}\n\n## Tâches\n\n## Notes\n", encoding="utf-8")
    api.post("/api/journal/entries/", {"date": DATE, "highlights": ["x"]},
             format="json")
    content = note(vault)
    assert content.startswith(f"# {DATE}\n")
    assert "## Tâches" in content and "## Notes" in content
    assert "## Journal" in content


# --- Remplacement de section : le reste de la note est intouché --------------

def test_section_machine_owned_et_reste_preserve(api, vault):
    avant = f"# {DATE}\n\n## Matin\nRéveil dur.\n\n## Journal\nvieux contenu\n\n## Soir\nCiné.\n"
    (vault / f"{DATE}.md").write_text(avant, encoding="utf-8")
    api.post("/api/journal/entries/", {"date": DATE, "highlights": ["Nouveau"]},
             format="json")
    content = note(vault)
    assert content.startswith(f"# {DATE}\n\n## Matin\nRéveil dur.\n\n## Journal")
    assert "vieux contenu" not in content
    assert "Nouveau" in content
    assert content.rstrip().endswith("## Soir\nCiné.")


# --- Correction / suppression d'un moment ------------------------------------

def test_correction_et_suppression_d_un_moment(api, vault):
    r = api.post("/api/journal/entries/",
                 {"date": DATE, "lows": ["Trop de réunions", "Pluie"]},
                 format="json")
    m1, m2 = r.json()["moments"]
    api.patch(f"/api/journal/moments/{m1['id']}/",
              {"text": "Vraiment trop de réunions"}, format="json")
    assert "Vraiment trop de réunions" in note(vault)
    assert "Trop de réunions\n" not in note(vault)
    api.delete(f"/api/journal/moments/{m2['id']}/")
    assert "Pluie" not in note(vault)


def test_isolation_moments_d_un_autre_utilisateur(api, vault, user):
    from django.contrib.auth import get_user_model
    from apps.journal.models import JournalEntry, JournalMoment

    autre = get_user_model().objects.create_user(email="x@example.com", password="s")
    entry = JournalEntry.objects.create(user=autre, date=DATE)
    moment = JournalMoment.objects.create(entry=entry, kind="positif", text="privé")
    assert api.delete(f"/api/journal/moments/{moment.id}/").status_code == 404


# --- Vault indisponible -------------------------------------------------------

def test_vault_indisponible_503_et_rollback(api, settings):
    settings.OBSIDIAN_VAULT_PATH = ""
    r = api.post("/api/journal/entries/", {"date": DATE, "highlights": ["x"]},
                 format="json")
    assert r.status_code == 503
    from apps.journal.models import JournalEntry, JournalMoment
    assert not JournalEntry.objects.exists() and not JournalMoment.objects.exists()


# --- Acteur + webhooks --------------------------------------------------------

def test_actor_propage_et_webhook_emis(api, vault, user, captured):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=user, url="https://x/h", events=["journal.updated"])
    api.post("/api/journal/entries/",
             {"date": DATE, "highlights": ["Belle balade"], "mood": "apaisé"},
             format="json", HTTP_X_ACTOR="agent:konofan")
    content = note(vault)
    assert "*Tenu par agent:konofan*" in content

    env = next(e for _, e in captured if e["event"] == "journal.updated")
    assert env["actor"] == "agent:konofan"
    assert env["data"]["moments"][0]["actor"] == "agent:konofan"


def test_catalogue_expose_journal_updated(api):
    assert "journal.updated" in api.get("/api/webhooks/events/").json()["events"]
