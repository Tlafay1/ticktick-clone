"""Accès au vault Obsidian synchronisé (client headless, volume partagé).

Le backend écrit directement les fichiers markdown ; le conteneur
`obsidian-sync` (ob sync --continuous) pousse ensuite vers Obsidian Sync.
Seule la section `## <JOURNAL_HEADING>` de la daily note est la propriété de
l'outil : elle est entièrement re-rendue et remplacée à chaque écriture, le
reste de la note n'est jamais touché.
"""
import json
import os
import re
import tempfile
from pathlib import Path

from django.conf import settings


class VaultUnavailable(Exception):
    """Vault non configuré ou non monté (→ 503 côté API)."""


def _root():
    raw = settings.OBSIDIAN_VAULT_PATH
    if not raw:
        raise VaultUnavailable("OBSIDIAN_VAULT_PATH n'est pas configuré.")
    root = Path(raw)
    if not root.is_dir():
        raise VaultUnavailable(f"Vault Obsidian introuvable : {raw}")
    return root


def _daily_config(root):
    """Config du plugin natif Daily Notes (`.obsidian/daily-notes.json`).

    Les variables d'env JOURNAL_DAILY_FOLDER / JOURNAL_DAILY_FORMAT priment si
    définies (utile quand la config `.obsidian` n'est pas synchronisée).
    """
    cfg = {}
    cfg_path = root / ".obsidian" / "daily-notes.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            cfg = {}
    return {
        "folder": settings.JOURNAL_DAILY_FOLDER or cfg.get("folder", ""),
        "format": settings.JOURNAL_DAILY_FORMAT or cfg.get("format") or "YYYY-MM-DD",
        "template": cfg.get("template", ""),
    }


# Tokens moment.js usuels des formats de daily note. Les portions entre
# crochets ([...]) sont des littéraux, les autres tokens sont laissés tels quels.
_MOMENT_TOKENS = {
    "YYYY": "{:%Y}",
    "YY": "{:%y}",
    "MM": "{:%m}",
    "M": "{0.month}",
    "DD": "{:%d}",
    "D": "{0.day}",
}
_TOKEN_RE = re.compile(r"\[([^\]]*)\]|(YYYY|YY|MM|M|DD|D)")


def format_moment(date, fmt):
    """Applique un format moment.js (sous-ensemble numérique) à une date."""

    def repl(match):
        literal, token = match.groups()
        if literal is not None:
            return literal
        return _MOMENT_TOKENS[token].format(date)

    return _TOKEN_RE.sub(repl, fmt)


def note_relpath(date, cfg):
    """Chemin relatif de la daily note (le format peut contenir des `/`)."""
    name = format_moment(date, cfg["format"]) + ".md"
    return str(Path(cfg["folder"]) / name) if cfg["folder"] else name


def _new_note_content(root, cfg, date, note_path):
    """Contenu initial d'une daily note absente : template Daily Notes si
    configuré (placeholders {{title}}, {{date}}, {{date:FMT}}), sinon vide."""
    template = cfg.get("template")
    if template:
        tpl_path = root / template
        if tpl_path.suffix != ".md":
            tpl_path = tpl_path.with_suffix(".md")
        if tpl_path.is_file():
            content = tpl_path.read_text(encoding="utf-8")
            content = content.replace("{{title}}", note_path.stem)
            content = re.sub(
                r"\{\{date(?::([^}]+))?\}\}",
                lambda m: format_moment(date, m.group(1)) if m.group(1) else date.isoformat(),
                content,
            )
            return content
    return ""


_HEADING_RE_TEMPLATE = r"^##\s+{}\s*$"


def _replace_section(content, heading, section_md):
    """Remplace la section `## heading` (jusqu'au prochain titre de niveau ≤ 2)
    par `section_md` ; l'ajoute en fin de note si absente. Le reste du contenu
    est préservé à l'octet près."""
    lines = content.splitlines(keepends=True)
    start_re = re.compile(_HEADING_RE_TEMPLATE.format(re.escape(heading)))
    end_re = re.compile(r"^#{1,2}\s")
    section_md = section_md.rstrip("\n") + "\n"

    start = next((i for i, l in enumerate(lines) if start_re.match(l.rstrip("\n"))), None)
    if start is None:
        base = content
        if base and not base.endswith("\n"):
            base += "\n"
        if base.strip():
            base += "\n"
        return base + section_md
    end = next((i for i in range(start + 1, len(lines)) if end_re.match(lines[i])), len(lines))
    tail = "".join(lines[end:])
    if tail and not section_md.endswith("\n\n"):
        section_md += "\n"
    return "".join(lines[:start]) + section_md + tail


def _atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".journal-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def upsert_journal_section(date, section_md):
    """Écrit/remplace la section journal dans la daily note de `date`.

    Crée la note (depuis le template Daily Notes) si absente. Renvoie le
    chemin relatif de la note dans le vault.
    """
    root = _root()
    cfg = _daily_config(root)
    rel = note_relpath(date, cfg)
    path = root / rel
    try:
        content = (
            path.read_text(encoding="utf-8")
            if path.is_file()
            else _new_note_content(root, cfg, date, path)
        )
        _atomic_write(path, _replace_section(content, settings.JOURNAL_HEADING, section_md))
    except OSError as exc:
        raise VaultUnavailable(f"Écriture impossible dans le vault : {exc}") from exc
    return rel
