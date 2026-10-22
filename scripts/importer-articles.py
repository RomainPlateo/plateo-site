#!/usr/bin/env python3
"""
Importe les articles depuis l'export CSV de Webflow (collection « Articles »).

    python3 scripts/importer-articles.py chemin/vers/export.csv

- Met à jour data/articles.json (titre, catégorie, date, résumé, image, auteur).
- Écrit le texte nettoyé de chaque article dans data/articles/<slug>.html.
Ensuite : python3 scripts/build.py, puis python3 scripts/rapatrier-images.py.

Les réglages faits à la main dans data/articles.json (ex. "masquer": true) sont conservés.
"""
import csv
import json
import pathlib
import re
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "articles.json"
BODIES = ROOT / "data" / "articles"

CATEGORIES = {"etudes de cas": "Étude de cas", "étude de cas": "Étude de cas",
              "conseils": "Conseils", "réglementation": "Réglementation", "autre": "Autre"}
AUTEURS = {"malaika-h": "Malaïka Hunt", "romain-cordier": "Romain Cordier",
           "raphael-w": "Raphaël Wieruszewski", "nathalie-p": "Nathalie P."}


def date_iso(s):
    s = (s or "").strip()
    if not s:
        return None
    return datetime.strptime(s[4:15], "%b %d %Y").strftime("%Y-%m-%d")


def categorie(c):
    c = (c or "").replace("\xa0", " ").strip()
    return CATEGORIES.get(c.lower(), "Autre")


def lien_interne(url, slugs):
    """Convertit un lien vers plateo.fr en lien relatif à jour (préfixe {{root}})."""
    chemin = re.sub(r"^https?://(www\.)?plateo\.fr", "", url) or "/"
    chemin, _, ancre = chemin.partition("#")
    chemin = chemin.split("?")[0]
    m = re.match(r"^/(?:media|blog(?:/[^/]+)?)/([^/]+)$", chemin)
    if m:
        slug = re.sub(r"[^a-z0-9-]", "", m.group(1).lower().replace("'", "").replace(":", "-"))
        slug = re.sub(r"-+", "-", slug).strip("-")
        cible = f"media/{slug}" if slug in slugs else "media/"
    elif chemin.startswith(("/blog", "/media")):
        cible = "media/"
    elif chemin.startswith("/contact"):
        cible = "contact"
    elif chemin in ("/", "/custom"):
        cible = "./"
    else:
        cible = chemin.lstrip("/")
    return "{{root}}" + cible + (f"#{ancre}" if ancre else "")


def nettoyer(html, slugs):
    h = html
    h = re.sub(r'\s(id|data-rt-[a-z-]+)="[^"]*"', "", h)
    h = re.sub(r'\sclass="w-richtext[^"]*"', ' class="article-figure"', h)
    h = re.sub(r"<figure([^>]*)>\s*<div>(.*?)</div>\s*</figure>", r"<figure\1>\2</figure>", h, flags=re.S)
    h = re.sub(r'\s(width|height|loading)="auto"', "", h)
    h = h.replace("<img ", '<img loading="lazy" ')
    h = re.sub(r"<(/?)h1\b", r"<\1h2", h)
    h = re.sub(r"<p>(\s|&nbsp;|‍|<br>)*</p>", "", h)

    def lien(m):
        attrs = m.group(1)
        href = re.search(r'href="([^"]*)"', attrs)
        if not href:
            return m.group(0)
        url = href.group(1)
        attrs = re.sub(r'\s(target|rel)="[^"]*"', "", attrs)
        if re.match(r"^(https?://(www\.)?plateo\.fr|/)", url):
            attrs = attrs.replace(f'href="{url}"', f'href="{lien_interne(url, slugs)}"')
        elif url.startswith("http"):
            attrs += ' target="_blank" rel="noopener"'
        return f"<a{attrs}>"

    h = re.sub(r"<a(\s[^>]*)>", lien, h)
    return h.strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 scripts/importer-articles.py export.csv")
    csv.field_size_limit(10**9)
    lignes = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
    data = json.loads(DATA.read_text(encoding="utf-8"))
    existants = {a["slug"]: a for a in data["articles"]}
    slugs = {x["Slug"] for x in lignes}
    BODIES.mkdir(parents=True, exist_ok=True)

    articles = []
    for x in lignes:
        slug = x["Slug"]
        publie = x["Archived"] == "false" and (x["Draft"] == "false" or slug in existants)
        if not publie:
            print(f"  ignoré (brouillon ou archivé) : {slug}")
            continue
        a = existants.get(slug, {"slug": slug})
        a.update({
            "titre": x["Blog Title"].strip(),
            "categorie": categorie(x["Categories"]),
            "date": date_iso(x["Published On"]) or date_iso(x["Created On"]),
            "maj": date_iso(x["Updated On"]),
            "resume": x["Post Summary"].strip() or None,
            "image": (x["Main Image"] or x["Thumbnail image"]).strip() or None,
            "auteur": AUTEURS.get(x["Authors"].strip(), x["Authors"].strip() or "Plateo"),
            "a_la_une": x["Featured?"] == "true",
        })
        (BODIES / f"{slug}.html").write_text(nettoyer(x["Post Body"], slugs), encoding="utf-8")
        articles.append(a)

    articles.sort(key=lambda a: a.get("date") or "", reverse=True)
    data["articles"] = articles
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {len(articles)} articles importés dans data/articles.json et data/articles/")


if __name__ == "__main__":
    main()
