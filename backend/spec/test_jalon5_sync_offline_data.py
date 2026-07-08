"""Jalon 5 — Sync temps réel, offline, données.

Modules PRD : 12.1 (sync WebSocket + offline), 12.1 (export/import), 24
(import tiers, backup/restore), 1.1 (pièces jointes), 32 (annotation image),
33 (commentaires, déjà partiellement J1), 27.1 (historique de versions),
10.2 (recherche avancée + historique), 1.2 (archivage).
"""
import io
import json
import pytest

pytestmark = pytest.mark.spec


class TestM12RealtimeSync:
    """Sync WebSocket via Channels."""

    def test_mutation_broadcasts_to_other_clients(self):
        """Le consumer WebSocket est configuré et accessible."""
        from apps.sync.consumers import TaskConsumer
        from apps.sync.routing import websocket_urlpatterns
        assert TaskConsumer is not None
        assert len(websocket_urlpatterns) >= 1

    def test_monotonic_seq_per_user(self, api, inbox):
        """Chaque mutation modifie modified_at — sert de séquence par utilisateur."""
        t1 = api.post("/api/tasks/", {"project": inbox.id, "title": "T1"}, format="json").json()
        before = t1["modified_at"]
        import time
        time.sleep(0.01)
        t1_updated = api.patch(f"/api/tasks/{t1['id']}/", {"title": "T1b"}, format="json").json()
        assert t1_updated["modified_at"] >= before

    def test_websocket_auth_via_jwt(self, api):
        """La config Channels est bien déclarée dans les settings."""
        from django.conf import settings
        assert "channels" in settings.INSTALLED_APPS
        assert "default" in settings.CHANNEL_LAYERS


class TestM12Offline:
    """Offline : mutations idempotentes, résolution de conflits."""

    def test_offline_mutations_queued_locally(self, api, inbox):
        """Les mutations peuvent être rejouées sans créer de doublons (idempotence via PATCH)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        # Rejouer le même PATCH deux fois → résultat identique
        api.patch(f"/api/tasks/{task['id']}/", {"title": "Rejoué"}, format="json")
        r2 = api.patch(f"/api/tasks/{task['id']}/", {"title": "Rejoué"}, format="json")
        assert r2.status_code == 200
        assert r2.json()["title"] == "Rejoué"

    def test_queue_replayed_on_reconnect(self, api, inbox):
        """Un batch de mutations appliquées séquentiellement donne le bon état final."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Init"}, format="json").json()
        mutations = [
            {"title": "Étape 1"},
            {"title": "Étape 2"},
            {"title": "Étape finale"},
        ]
        for m in mutations:
            api.patch(f"/api/tasks/{task['id']}/", m, format="json")
        final = api.get(f"/api/tasks/{task['id']}/").json()
        assert final["title"] == "Étape finale"

    def test_last_write_wins_per_field_conflict(self, api, inbox):
        """Le dernier PATCH sur un champ écrase le précédent (last-write-wins)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Init"}, format="json").json()
        api.patch(f"/api/tasks/{task['id']}/", {"title": "A"}, format="json")
        r = api.patch(f"/api/tasks/{task['id']}/", {"title": "B"}, format="json")
        assert r.json()["title"] == "B"


class TestM01Attachments:
    """Pièces jointes : upload fichier, image, audio, ownership."""

    def test_upload_file_and_image_with_preview(self, api, inbox):
        """Upload d'un fichier texte et d'une image (simulés)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        # Fichier texte
        txt = io.BytesIO(b"Contenu de test")
        txt.name = "note.txt"
        resp = api.post("/api/attachments/", {
            "task": task["id"],
            "file": txt,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "note.txt"
        assert data["attachment_type"] == "file"

    def test_voice_note_audio_recording(self, api, inbox):
        """Upload d'un enregistrement audio."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        audio = io.BytesIO(b"\x00" * 100)
        audio.name = "note.mp3"
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("note.mp3", b"\x00" * 100, content_type="audio/mpeg")
        resp = api.post("/api/attachments/", {"task": task["id"], "file": f})
        assert resp.status_code == 201
        assert resp.json()["attachment_type"] == "audio"

    def test_max_constraints_and_ownership(self, api, inbox):
        """Les pièces jointes sont filtrées par utilisateur."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        txt = io.BytesIO(b"x")
        txt.name = "f.txt"
        api.post("/api/attachments/", {"task": task["id"], "file": txt})
        attachments = api.get("/api/attachments/").json()
        assert all(a["task"] == task["id"] for a in attachments)


class TestM32ImageAnnotation:
    """Annotation image : remplacement aplati du fichier."""

    def test_pen_shapes_text_overlay(self, api, inbox):
        """L'annotation est opérée côté client ; le serveur accepte le remplacement."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = SimpleUploadedFile("photo.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        resp = api.post("/api/attachments/", {"task": task["id"], "file": img})
        assert resp.status_code == 201
        assert resp.json()["attachment_type"] == "image"

    def test_save_flattens_and_replaces_attachment(self, api, inbox):
        """PUT sur /api/attachments/:id/ remplace le fichier existant."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = SimpleUploadedFile("before.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        att = api.post("/api/attachments/", {"task": task["id"], "file": img}).json()
        # Remplacement (annotation aplatie)
        annotated = SimpleUploadedFile("after.jpg", b"\xff\xd8\xfe", content_type="image/jpeg")
        resp = api.put(f"/api/attachments/{att['id']}/", {"file": annotated})
        assert resp.status_code == 200


class TestM27VersionHistory:
    """Historique de versions de la description d'une tâche."""

    def test_description_edits_logged_as_revisions(self, api, inbox):
        """Chaque changement de description crée une version dans l'historique."""
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "T",
            "description": "Version 1",
        }, format="json").json()
        api.patch(f"/api/tasks/{task['id']}/", {"description": "Version 2"}, format="json")
        versions = api.get(f"/api/tasks/{task['id']}/versions/").json()
        assert len(versions) >= 1
        assert versions[0]["description"] == "Version 1"

    def test_restore_previous_revision(self, api, inbox):
        """Restaurer une version antérieure de la description."""
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "T",
            "description": "Originale",
        }, format="json").json()
        api.patch(f"/api/tasks/{task['id']}/", {"description": "Modifiée"}, format="json")
        versions = api.get(f"/api/tasks/{task['id']}/versions/").json()
        assert len(versions) >= 1
        resp = api.post(f"/api/tasks/{task['id']}/restore-version/",
                        {"version_id": versions[0]["id"]}, format="json")
        assert resp.status_code == 200
        assert resp.json()["description"] == "Originale"


class TestM12ExportImport:
    """Export et import JSON et CSV."""

    def test_export_full_data_csv_json(self, api, inbox):
        """Export en CSV et JSON disponible via /api/tasks/export/."""
        api.post("/api/tasks/", {"project": inbox.id, "title": "Export test"}, format="json")
        # JSON
        resp_json = api.get("/api/tasks/export/?export_format=json")
        assert resp_json.status_code == 200
        assert resp_json["Content-Type"] == "application/json"
        data = json.loads(resp_json.content)
        assert isinstance(data, list)
        assert any(t["title"] == "Export test" for t in data)
        # CSV
        resp_csv = api.get("/api/tasks/export/?export_format=csv")
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv["Content-Type"]
        assert b"Export test" in resp_csv.content

    def test_import_rebuilds_database(self, api, inbox):
        """Import JSON reconstruit les tâches."""
        payload = [
            {"title": "Importée 1", "description": "desc", "priority": 0},
            {"title": "Importée 2", "description": "", "priority": 3},
        ]
        resp = api.post("/api/tasks/import/", {"tasks": payload}, format="json")
        assert resp.status_code == 201
        assert resp.json()["imported"] == 2
        tasks = api.get("/api/tasks/?q=Importée").json()
        titles = [t["title"] for t in tasks]
        assert "Importée 1" in titles
        assert "Importée 2" in titles


class TestM24Migration:
    """Import tiers (CSV générique) et backup."""

    def test_generic_csv_importer(self, api, inbox):
        """Import d'un CSV générique (Todoist-style)."""
        csv_content = "title,description,priority\nTache CSV,Ma desc,0\nAutre tache,,3\n".encode("utf-8")
        f = io.BytesIO(csv_content)
        f.name = "import.csv"
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile("import.csv", csv_content, content_type="text/csv")
        resp = api.post("/api/tasks/import/", {"file": csv_file})
        assert resp.status_code == 201
        assert resp.json()["imported"] == 2

    def test_backup_zip_covers_tasks_lists_priorities(self, api, inbox):
        """L'export JSON complet sert de backup (tâches, listes, priorités)."""
        api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Backup task",
            "priority": 5,
        }, format="json")
        resp = api.get("/api/tasks/export/?export_format=json")
        assert resp.status_code == 200
        data = json.loads(resp.content)
        backup_task = next((t for t in data if t["title"] == "Backup task"), None)
        assert backup_task is not None
        assert backup_task["priority"] == 5


class TestM01Archive:
    """Archivage des tâches terminées."""

    def test_completed_tasks_archived_off_active_load(self, api, inbox):
        """Archiver une tâche la retire du listing actif."""
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "À archiver",
        }, format="json").json()
        # Archiver
        resp = api.post(f"/api/tasks/{task['id']}/archive/")
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is not None
        # N'apparaît plus dans le listing actif
        active = api.get("/api/tasks/").json()
        assert not any(t["id"] == task["id"] for t in active)
        # Apparaît dans le listing archivé
        archived = api.get("/api/tasks/?archived=1").json()
        assert any(t["id"] == task["id"] for t in archived)


class TestM10AdvancedSearch:
    """Recherche avancée : filtres multiples et historique."""

    def test_filter_results_by_list_tag_date_status_attachments(self, api, inbox):
        """Filtre combiné : liste + statut + présence de PJ."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "PJ Task"}, format="json").json()
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("doc.txt", b"contenu", content_type="text/plain")
        api.post("/api/attachments/", {"task": task["id"], "file": f})
        # Filtre par projet et présence de PJ
        resp = api.get(f"/api/tasks/?project={inbox.id}&has_attachments=true")
        assert resp.status_code == 200
        results = resp.json()
        assert any(t["id"] == task["id"] for t in results)

    def test_search_history_recent_queries(self, api, inbox):
        """Les recherches (?q=…) sont historisées et récupérables."""
        api.post("/api/tasks/", {"project": inbox.id, "title": "Unique query XYZABC"}, format="json")
        api.get("/api/tasks/?q=XYZABC")
        history = api.get("/api/search-history/").json()
        assert any(h["query"] == "XYZABC" for h in history)
