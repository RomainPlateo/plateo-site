#!/usr/bin/env python3
"""
Rapatrie en local toutes les images encore hébergées sur le CDN Webflow
(cdn.prod.website-files.com, uploads-ssl.webflow.com, assets-global.website-files.com),
les allège (format WebP, largeur max 1200 px) et met à jour les liens dans les fichiers HTML.

À lancer depuis la racine du site, AVANT de résilier Webflow :
    python3 -m pip install pillow      (une seule fois)
    python3 scripts/rapatrier-images.py

Le script peut être relancé autant de fois que nécessaire : les images déjà
rapatriées sont conservées, et une image qui échoue n'arrête pas les autres.
"""
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow est nécessaire pour alléger les images.\n"
             "Installe-le avec :  python3 -m pip install pillow\n"
             "puis relance :      python3 scripts/rapatrier-images.py")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "img" / "webflow"
MAPFILE = DEST / "correspondances.json"
PATTERN = re.compile(r'https://(?:cdn\.prod\.website-files\.com|uploads-ssl\.webflow\.com|'
                     r'assets-global\.website-files\.com)/(?:[^"\'\s()<>]|\([^"\'\s()<>]*\))+')
MAX_WIDTH = 1200
CONVERTIBLES = {"png", "jpg", "jpeg"}

DEST.mkdir(parents=True, exist_ok=True)
html_files = [f for f in ROOT.rglob("*.html")
              if not {"node_modules", "data", "templates", ".git"} & set(f.relative_to(ROOT).parts)]
urls = sorted({u for f in html_files for u in PATTERN.findall(f.read_text(encoding="utf-8"))})
print(f"{len(urls)} image(s) encore sur Webflow")


def clean_name(url):
    raw = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    name = re.sub(r"^[0-9a-f]{24}_", "", raw)  # retire l'identifiant Webflow
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()  # sans accents
    name = re.sub(r"[^A-Za-z0-9.\-]+", "-", name).strip("-_.").lower()
    stem, ext = name.rsplit(".", 1) if "." in name else (name, "bin")
    return stem[:80].strip("-") or "image", ext


def telecharger(url):
    for essai in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            derniere = e
            time.sleep(2)
    raise derniere


def ancien_fichier(url, ext):
    """Fichier déjà téléchargé par une version précédente du script (non converti)."""
    raw = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    raw = re.sub(r"^[0-9a-f]{24}_", "", raw)
    nom = re.sub(r"[^\w.\-]+", "-", raw).strip("-_").lower()
    f = DEST / nom
    return f if f.exists() and f.suffix.lstrip(".") == ext else None


mapping = json.loads(MAPFILE.read_text(encoding="utf-8")) if MAPFILE.exists() else {}
pris = {v for v in mapping.values()}
echecs = []
for url in urls:
    if url in mapping and (ROOT / mapping[url]).exists():
        continue
    stem, ext = clean_name(url)
    convertir = ext in CONVERTIBLES
    final_ext = "webp" if convertir else ext
    target = DEST / f"{stem}.{final_ext}"
    i = 2
    while target.relative_to(ROOT).as_posix() in pris:
        target = DEST / f"{stem}-{i}.{final_ext}"
        i += 1
    try:
        ancien = ancien_fichier(url, ext)
        data = ancien.read_bytes() if ancien else telecharger(url)
        if convertir:
            tmp = DEST / f".tmp-{stem}.{ext}"
            tmp.write_bytes(data)
            im = Image.open(tmp)
            im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
            im.save(target, "WEBP", quality=80, method=6)
            tmp.unlink()
        else:
            target.write_bytes(data)
        if ancien and ancien != target:
            ancien.unlink()
    except Exception as e:  # noqa: BLE001
        echecs.append((url, str(e)))
        print("  ✗", url, "→", e)
        continue
    rel = target.relative_to(ROOT).as_posix()
    mapping[url] = rel
    pris.add(rel)
    print("  ✓", target.name)

# Enregistre la correspondance (utilisée par scripts/build.py) avant de toucher au HTML
MAPFILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

for f in html_files:
    text = f.read_text(encoding="utf-8")
    new = text
    depth = len(f.relative_to(ROOT).parts) - 1
    for url, rel_target in mapping.items():
        if url in new:
            new = new.replace(url, "../" * depth + rel_target)
    if new != text:
        f.write_text(new, encoding="utf-8")
        print("  liens mis à jour :", f.relative_to(ROOT))

# Fichiers bruts laissés par l'ancienne version du script et devenus inutiles
utilises = {ROOT / v for v in mapping.values()}
for f in DEST.iterdir():
    if f.suffix.lower() in {".png", ".jpg", ".jpeg"} and f not in utilises:
        f.unlink()

restants = sorted({u for f in html_files for u in PATTERN.findall(f.read_text(encoding="utf-8"))})
print()
if restants:
    print(f"⚠ {len(restants)} image(s) toujours sur Webflow (relance le script ; si ça persiste, "
          "envoie la liste à Claude) :")
    for u in restants:
        print("   ", u)
else:
    print("✓ Terminé : toutes les images sont sur le site (assets/img/webflow/).")
