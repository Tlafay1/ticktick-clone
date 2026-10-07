#!/usr/bin/env python3
"""Installe une méthode d'organisation dans un compte, via l'API (clé d'API).

Usage :
    python3 scripts/installer_methode.py --url https://tasks.mondomaine.fr \\
        --cle <clé d'API> [--plan perso/plan-methode.json]

Le plan (JSON) décrit objectifs, sections, premières actions, créneaux, revue et
comptes à rebours ; il vit hors du dépôt public (perso/ est ignoré par git).
Idempotent : relancer ne crée rien en double (correspondance par nom/titre).
Aucune dépendance : bibliothèque standard seulement.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


class Api:
    def __init__(self, base, cle):
        self.base = base.rstrip("/") + "/api"
        self.entetes = {"Authorization": f"Api-Key {cle}", "Content-Type": "application/json",
                        "X-Actor": "user"}

    def appel(self, methode, chemin, corps=None):
        requete = urllib.request.Request(
            self.base + chemin, method=methode, headers=self.entetes,
            data=json.dumps(corps).encode() if corps is not None else None,
        )
        try:
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                contenu = reponse.read()
        except urllib.error.HTTPError as e:
            sys.exit(f"✗ {methode} {chemin} → {e.code} {e.read().decode()[:300]}")
        return json.loads(contenu) if contenu else None


def installer(api, plan):
    fait = []
    reglages = api.appel("GET", "/me/")["settings"]
    if plan.get("timezone") and not reglages.get("timezone"):
        api.appel("PATCH", "/me/settings/", {"timezone": plan["timezone"]})
        fait.append(f"fuseau {plan['timezone']}")

    projets = {p["name"]: p for p in api.appel("GET", "/projects/")}
    ids_des_objectifs = {}
    for objectif in plan.get("objectifs", []):
        projet = projets.get(objectif["nom"])
        if projet is None:
            projet = api.appel("POST", "/projects/", {
                "name": objectif["nom"], "color": objectif.get("couleur", ""),
                "objective": objectif.get("statut", "active"),
            })
            fait.append(f"objectif « {objectif['nom']} »")
        ids_des_objectifs[objectif["nom"]] = projet["id"]
        sections = {s["name"]: s["id"] for s in projet.get("sections", [])}
        for rang, nom in enumerate(objectif.get("sections", [])):
            if nom not in sections:
                sections[nom] = api.appel("POST", "/sections/", {
                    "project": projet["id"], "name": nom, "sort_order": (rang + 1) * 1000,
                })["id"]
        existantes = {t["title"] for t in api.appel("GET", f"/tasks/?project={projet['id']}")}
        nouvelles = 0
        for rang, tache in enumerate(objectif.get("taches", [])):
            if tache["titre"] in existantes:
                continue
            corps = {"project": projet["id"], "title": tache["titre"], "sort_order": (rang + 1) * 1000}
            if tache.get("section"):
                corps["section"] = sections[tache["section"]]
            api.appel("POST", "/tasks/", corps)
            nouvelles += 1
        if nouvelles:
            fait.append(f"{nouvelles} action(s) dans « {objectif['nom']} »")

    revue = plan.get("revue")
    config = api.appel("GET", "/method/config/")
    if revue and (config["review_weekday"], config["review_time"][:5]) != (revue["jour"], revue["heure"]):
        api.appel("PATCH", "/method/config/", {"review_weekday": revue["jour"], "review_time": revue["heure"]})
        fait.append("revue réglée")

    creneaux = {(s["weekday"], s["start_time"][:5], s["kind"]) for s in api.appel("GET", "/slots/")}
    for c in plan.get("creneaux", []):
        cle = (c["jour"], c["heure"], c.get("type", "work"))
        if cle in creneaux:
            continue
        corps = {"weekday": c["jour"], "start_time": c["heure"], "duration_minutes": c.get("duree", 25),
                 "kind": c.get("type", "work")}
        if c.get("objectif"):
            corps["project"] = ids_des_objectifs[c["objectif"]]
        api.appel("POST", "/slots/", corps)
        fait.append(f"créneau {c['heure']} (jour {c['jour']})")

    comptes = {c["title"] for c in api.appel("GET", "/countdowns/")}
    for c in plan.get("comptes_a_rebours", []):
        if c["titre"] not in comptes:
            api.appel("POST", "/countdowns/", {"title": c["titre"], "target_date": c["date"], "pinned": True})
            fait.append(f"compte à rebours « {c['titre']} »")
    return fait


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="adresse du serveur (sans /api)")
    parser.add_argument("--cle", required=True, help="clé d'API (Réglages → Clés d'API)")
    parser.add_argument("--plan", default="perso/plan-methode.json")
    args = parser.parse_args()
    with open(args.plan, encoding="utf-8") as fichier:
        plan = json.load(fichier)
    fait = installer(Api(args.url, args.cle), plan)
    print("✓ " + ("\n✓ ".join(fait) if fait else "Déjà en place : rien à faire."))


if __name__ == "__main__":
    main()
