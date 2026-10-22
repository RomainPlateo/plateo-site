#!/usr/bin/env python3
"""
Importe les réalisations depuis l'export CSV de Webflow (collection « Dernières réalisations »).

    python3 scripts/importer-realisations.py chemin/vers/export.csv

Écrit data/realisations.json. Ensuite : python3 scripts/build.py, puis rapatrier-images.py.
Les réglages faits à la main dans data/realisations.json (spécialité, texte, "masquer") sont conservés.
"""
import csv
import json
import pathlib
import re
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "realisations.json"

CLIENTS = {"at": "Association tutélaire", "association tutélaire": "Association tutélaire",
           "mjpmi": "MJPM indépendant", "préposé d'établissement": "Préposé d'établissement",
           "coordinateur de parcours complexe": "Coordinateur de parcours complexe",
           "c.h.r.s": "CHRS", "autre": "Autre"}

# Spécialité (section de la page « Les Spécialités ») de chaque chantier
SPECIALITE_PAR_SLUG = {
    "adaptation-de-logement": "adaptation-des-logements",
    "adaptation-dune-salle-de-bains": "adaptation-des-logements",
    "remplacement-plaque-de-cuisson-au-gaz": "adaptation-des-logements",
    "remplacement-dune-serrure": "depannages",
    "remplacement-dune-serrure-2": "depannages",
    "debouchage-dun-lavabo": "depannages",
    "remise-en-etat-avant-vente": "remise-en-etat",
    "remise-en-etat-dun-logement": "remise-en-etat",
    "mise-en-peinture-dune-chambre": "remise-en-etat",
    "mise-en-peinture-dune-chambre-2": "remise-en-etat",
    "mise-en-peinture-dune-salle-de-bains-jpg": "remise-en-etat",
    "mise-en-peinture-suite-a-un-degat-des-eaux": "remise-en-etat",
    "nettoyage-diogene": "nettoyage-et-desinsectisation",
    "debarrassage-complet-dun-logement": "nettoyage-et-desinsectisation",
    "debarrassage-dun-logement": "nettoyage-et-desinsectisation",
    "entretien-dun-jardin": "espaces-exterieurs",
    "taille-dune-haie": "espaces-exterieurs",
    "elagage-dun-cypres": "espaces-exterieurs",
    "amenagement-terrain": "espaces-exterieurs",
    "remise-en-etat-dun-caniveau": "espaces-exterieurs",
}


def date_iso(s):
    s = (s or "").strip()
    return datetime.strptime(s[4:15], "%b %d %Y").strftime("%Y-%m-%d") if s else None


def texte(html):
    t = re.sub(r"<[^>]+>", " ", html or "").replace("‍", " ")
    return re.sub(r"\s+", " ", t).strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 scripts/importer-realisations.py export.csv")
    lignes = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
    anciens = {}
    if DATA.exists():
        anciens = {r["slug"]: r for r in json.loads(DATA.read_text(encoding="utf-8"))["realisations"]}

    out = []
    for x in lignes:
        slug = (x.get("Slug") or "").strip()
        if not slug:
            continue
        if x["Archived"] != "false" or x["Draft"] != "false":
            print(f"  ignoré (brouillon ou archivé) : {slug}")
            continue
        r = anciens.get(slug, {"slug": slug})
        desc = texte(x["Project Write Up"]) or x["Project Summary"].strip()
        image = x["Image"].strip().replace("(", "%28").replace(")", "%29")
        r.setdefault("specialite", SPECIALITE_PAR_SLUG.get(slug, "tous-les-travaux-courants"))
        r.update({
            "titre": x["Project Title"].strip(),
            "client": CLIENTS.get(x["Type de client"].strip().lower(), x["Type de client"].strip() or "Autre"),
            "image": image or None,
            "date": date_iso(x["Published On"]) or date_iso(x["Created On"]),
        })
        if desc and not r.get("texte"):
            r["texte"] = desc
        out.append(r)

    out.sort(key=lambda r: r.get("date") or "", reverse=True)
    data = {"_note": "Réalisations (page /projets et fiches /projects/<slug>). Champs modifiables : "
                     "specialite (ancre de la page Les Spécialités), client, texte, masquer.",
            "realisations": out}
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {len(out)} réalisations importées dans data/realisations.json")


if __name__ == "__main__":
    main()
