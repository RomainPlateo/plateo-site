#!/usr/bin/env python3
"""
Rapatrie en local toutes les images encore hébergées sur le CDN Webflow
(cdn.prod.website-files.com et uploads-ssl.webflow.com), les allège (format WebP, largeur max 1200 px)
et met à jour les liens dans les fichiers HTML.

À lancer depuis la racine du site, AVANT de résilier Webflow :
    python3 scripts/rapatrier-images.py

La conversion WebP utilise Pillow (pip install pillow). Sans Pillow,
les images sont simplement copiées telles quelles.
"""
import pathlib
import re
import urllib.parse
import urllib.request

try:
    from PIL import Image
except ImportError:
    Image = None
    print("Pillow absent : images copiées sans optimisation (pip install pillow).")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "img" / "webflow"
PATTERN = re.compile(r'https://(?:cdn\.prod\.website-files\.com|uploads-ssl\.webflow\.com|assets-global\.website-files\.com)/[^"\'\s)]+')
MAX_WIDTH = 1200

DEST.mkdir(parents=True, exist_ok=True)
html_files = [f for f in ROOT.rglob("*.html")
              if not {"node_modules", "data", "templates"} & set(f.relative_to(ROOT).parts)]
urls = sorted({u for f in html_files for u in PATTERN.findall(f.read_text(encoding="utf-8"))})
print(f"{len(urls)} image(s) à rapatrier")


def clean_name(url):
    raw = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    name = re.sub(r"^[0-9a-f]{24}_", "", raw)  # retire l'identifiant Webflow
    name = re.sub(r"[^\w.\-]+", "-", name).strip("-_").lower()
    return name


mapping = {}
used = set()
for url in urls:
    name = clean_name(url)
    stem, ext = name.rsplit(".", 1) if "." in name else (name, "bin")
    convert = Image is not None and ext in {"png", "jpg", "jpeg"}
    final_ext = "webp" if convert else ext
    target = DEST / f"{stem}.{final_ext}"
    i = 2
    while target in used:  # deux images différentes avec le même nom
        target = DEST / f"{stem}-{i}.{final_ext}"
        i += 1
    used.add(target)

    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if convert:
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
        print("  ✓", target.name)
    mapping[url] = target

for f in html_files:
    text = f.read_text(encoding="utf-8")
    new = text
    depth = len(f.relative_to(ROOT).parts) - 1
    for url, target in mapping.items():
        rel = pathlib.Path(*[".."] * depth, target.relative_to(ROOT))
        new = new.replace(url, rel.as_posix())
    if new != text:
        f.write_text(new, encoding="utf-8")
        print("  liens mis à jour :", f.relative_to(ROOT))

# Correspondance URL Webflow -> fichier local, utilisée par scripts/build.py
import json
mapfile = DEST / "correspondances.json"
old = json.loads(mapfile.read_text(encoding="utf-8")) if mapfile.exists() else {}
old.update({u: t.relative_to(ROOT).as_posix() for u, t in mapping.items()})
mapfile.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")

print("Terminé. Les images sont dans assets/img/webflow/")
