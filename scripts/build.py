#!/usr/bin/env python3
"""
Génère les pages du site à partir des modèles et des données.

    python3 scripts/build.py

- templates/header.html et templates/footer.html : menu et pied de page communs.
  Toute modification y est reportée sur toutes les pages (accueil compris).
- data/travaux.json : contenu de la page « Les Spécialités » (les-specialites.html).
- data/accompagnement.json et data/audit.json : pages « Accompagnement Travaux » et « Audit Sécurité / Salubrité ».
- data/articles.json + data/articles/*.html : articles (page « Le média » et media/<slug>.html),
  importés depuis Webflow avec scripts/importer-articles.py.
- data/ressources.json : livres blancs et réglages du formulaire (clé Web3Forms).
- data/mentions-legales.html : texte des mentions légales (date : MAJ_MENTIONS ci-dessous).
- data/realisations.json : réalisations (page /projets et fiches projects/<slug>),
  importées avec scripts/importer-realisations.py.
- data/faq.json : FAQ commune à l'accueil et à la page « Les Spécialités ».
- Les anciennes pages services/<métier> renvoient vers les-specialites#<métier>.
- sitemap.xml est régénéré.

Aucune dépendance : Python 3 suffit.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.plateo.fr/"
TALLY = "https://tally.so/r/3y695p"
TPL = ROOT / "templates"
MAJ_MENTIONS = "2026-10-22"

# Politique de sécurité du contenu : seules ces sources peuvent être chargées par les pages.
# Si tu ajoutes un outil externe (statistiques, vidéo…), il faut l'autoriser ici.
CSP_META = """  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'sha256-/x7W7R75k8Roq0WaVRQX9blP4OufE5xbAdzklGxsgpw='; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.web3forms.com; form-action 'self' https://api.web3forms.com; base-uri 'self'; object-src 'none'; upgrade-insecure-requests">
  <meta name="referrer" content="strict-origin-when-cross-origin">
"""  # date de dernière mise à jour des mentions légales
e = lambda t: html.escape(t, quote=False)
ea = lambda t: html.escape(t, quote=True)

ICON_CHECK = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" d="M5 12.5l4.2 4.2L19 7"/></svg>'


def partial(name, root, accueil=False, actif=None):
    t = (TPL / name).read_text(encoding="utf-8")
    t = t.replace("{{root}}", root)
    t = t.replace("{{nav_accueil}}", ' aria-current="page"' if accueil else "")
    if actif and name == "header.html":  # souligne la page en cours dans le menu
        for h in (actif, actif + "/"):
            t = t.replace(f'<li><a href="{root}{h}">', f'<li><a href="{root}{h}" aria-current="page">', 1)
    return t


def sync_index():
    """Recopie le menu et le pied de page communs dans index.html."""
    p = ROOT / "index.html"
    s = p.read_text(encoding="utf-8")
    for start, end, name in [
        ("<!-- ============ EN-TÊTE ============ -->", "</header>", "header.html"),
        ("<!-- ============ PIED DE PAGE ============ -->", "</footer>", "footer.html"),
    ]:
        a = s.index(start)
        b = s.index(end, a) + len(end)
        s = s[:a] + partial(name, "", accueil=True).rstrip("\n") + s[b:]
    p.write_text(s, encoding="utf-8")


def local_images(text, root):
    """Remplace les images Webflow déjà rapatriées par leur copie locale."""
    mapfile = ROOT / "assets" / "img" / "webflow" / "correspondances.json"
    if mapfile.exists():
        for url, local in json.loads(mapfile.read_text(encoding="utf-8")).items():
            text = text.replace(url, root + local)
    return text


def head(title, description, url, root, ld):
    actif = url[len(SITE):].split("/")[0] or None
    ld_txt = json.dumps(ld, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{CSP_META}  <title>{e(title)}</title>
  <meta name="description" content="{ea(description)}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{url}">
  <meta name="theme-color" content="#14263E">

  <meta property="og:type" content="website">
  <meta property="og:locale" content="fr_FR">
  <meta property="og:site_name" content="Plateo">
  <meta property="og:title" content="{ea(title)}">
  <meta property="og:description" content="{ea(description)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}assets/img/og-plateo.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">

  <link rel="icon" type="image/png" sizes="48x48" href="{root}assets/img/favicon.png">
  <link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
  <link rel="preload" href="{root}assets/fonts/outfit-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{root}css/style.css">
  <script>document.documentElement.classList.add('js');</script>
  <script type="application/ld+json">
{ld_txt}
  </script>
</head>
<body>

<a class="skip-link" href="#contenu">Aller au contenu</a>

{partial("header.html", root, actif=actif).rstrip()}
'''


def foot(root):
    return f'''
{partial("footer.html", root).rstrip()}

<script src="{root}js/main.js" defer></script>
</body>
</html>
'''


def faq_data():
    return json.loads((ROOT / "data" / "faq.json").read_text(encoding="utf-8"))["faq"]


def faq_items_html(faq):
    return "\n".join(
        f'''        <details class="faq-item"{' open' if i == 0 else ''}>
          <summary><h3>{e(f['question'])}</h3></summary>
          <div class="faq-answer">{''.join(f'<p>{x}</p>' for x in f['reponse_html'])}</div>
        </details>''' for i, f in enumerate(faq))


def faq_ld(faq, page_url):
    texte = lambda h: html.unescape(re.sub(r"<[^>]+>", "", h))
    return {
        "@type": "FAQPage",
        "@id": page_url + "#faq",
        "inLanguage": "fr-FR",
        "mainEntity": [{"@type": "Question", "name": f["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": " ".join(texte(x) for x in f["reponse_html"])}} for f in faq],
    }


def sync_index_faq(faq):
    """Recopie la FAQ commune dans index.html (affichage + données structurées)."""
    p = ROOT / "index.html"
    s = p.read_text(encoding="utf-8")
    a = s.index('<div class="faq-list reveal">') + len('<div class="faq-list reveal">')
    b = s.index("      </div>\n    </div>\n  </section>", a)
    s = s[:a] + "\n" + faq_items_html(faq) + "\n" + s[b:]
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    data = json.loads(m.group(1))
    data["@graph"] = [n for n in data["@graph"] if n.get("@type") != "FAQPage"] + [faq_ld(faq, SITE)]
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    s = s[:m.start(1)] + "\n" + "\n".join("  " + l for l in txt.splitlines()) + "\n  " + s[m.end(1):]
    p.write_text(s, encoding="utf-8")


def page_travaux(d):
    root = ""
    p = d["page"]
    url = SITE + p["slug"]

    sommaire = "\n".join(
        f'''          <a class="toc-chip" href="#{m['slug']}"><img src="{m['picto']}" alt="" width="28" height="28">{e(m['nom'])}</a>'''
        for m in d["metiers"])

    def metier(i, m):
        prestas = "\n".join(
            f'''            <article class="presta-card">
              <span class="presta-icon">{ICON_CHECK}</span>
              <h3>{e(t)}</h3>
              <p>{e(x)}</p>
            </article>''' for t, x in m["prestations"])
        reals = ", ".join(f'<a href="{root}projects/{s}">{e(t)}</a>' for s, t in m.get("realisations", []))
        arts = "\n".join(f'<li><a href="{root}media/{s}">{e(t)}</a></li>' for s, t in m.get("articles", []))
        return f'''
  <section class="section trade-section{' section-alt' if i % 2 else ''}" id="{m['slug']}" aria-labelledby="t-{m['slug']}">
    <div class="container trade-layout">
      <div class="trade-aside reveal">
        <img class="trade-picto" src="{m['picto']}" alt="" width="96" height="96" loading="lazy">
        <p class="eyebrow">Corps d'état {i + 1:02d}</p>
        <h2 id="t-{m['slug']}">{e(m['nom'])}</h2>
        <p class="trade-intro">{e(m['intro'])}</p>
        {f'<p class="trade-examples"><strong>Exemples de chantiers :</strong> {reals}</p>' if reals else ''}
        <a href="{TALLY}" class="btn btn-primary btn-sm" target="_blank" rel="noopener">Demander un devis<span class="sr-only"> : {e(m['nom'].lower())}</span></a>
      </div>
      <div class="trade-main">
        <div class="presta-grid-2 reveal">
{prestas}
        </div>
        {f"""<div class="trade-reads reveal">
          <p class="trade-reads-title">À lire sur le média</p>
          <ul>
            {arts}
          </ul>
        </div>""" if arts else ""}
      </div>
    </div>
  </section>'''

    metiers = "".join(metier(i, m) for i, m in enumerate(d["metiers"]))

    etapes = "\n".join(
        f'''          <li class="step reveal">
            <span class="step-num">{i}</span>
            <h3>{e(t)}</h3>
            <p>{e(x)}</p>
          </li>''' for i, (t, x) in enumerate(d["etapes"], 1))

    pourquoi = "\n".join(
        f'''          <div class="why-item reveal">
            <h3>{e(t)}</h3>
            <p>{e(x)}</p>
          </div>''' for t, x in d["pourquoi"])

    faq_list = faq_data()
    faq = faq_items_html(faq_list)

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": url + "#page",
                "url": url,
                "name": p["title"],
                "description": p["description"],
                "inLanguage": "fr-FR",
                "isPartOf": {"@id": SITE + "#site"},
                "about": {"@id": SITE + "#organisation"},
            },
            {
                "@type": "ItemList",
                "name": "Corps d'état pris en charge par Plateo",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "item": {
                            "@type": "Service",
                            "@id": f"{url}#{m['slug']}",
                            "name": m["nom"],
                            "description": m["intro"],
                            "url": f"{url}#{m['slug']}",
                            "provider": {"@id": SITE + "#organisation"},
                            "hasOfferCatalog": {
                                "@type": "OfferCatalog",
                                "name": m["nom"],
                                "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": t, "description": x}} for t, x in m["prestations"]],
                            },
                        },
                    }
                    for i, m in enumerate(d["metiers"])
                ],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": "Les Spécialités", "item": url},
                ],
            },
            faq_ld(faq_list, url),
        ],
    }

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE DE PAGE ============ -->
  <section class="hero page-hero">
    <div class="container">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Les Spécialités</li>
        </ol>
      </nav>
      <div class="page-hero-text">
        <h1 class="hero-title" data-split>{e(p['h1'])}</h1>
        {''.join(f'<p class="lead hero-anim">{e(x)}</p>' for x in p['intro'])}
        <div class="btn-row hero-anim">
          <a href="{TALLY}" class="btn btn-primary" target="_blank" rel="noopener">Demander un devis</a>
          <a href="tel:+33778242775" class="btn btn-ghost">07 78 24 27 75</a>
        </div>
      </div>
      <nav class="toc hero-anim" aria-label="Nos corps d'état">
{sommaire}
      </nav>
    </div>
  </section>
{metiers}

  <!-- ============ DÉROULÉ ============ -->
  <section class="section section-dark-soft">
    <div class="container">
      <div class="section-head reveal">
        <p class="eyebrow">Le fonctionnement</p>
        <h2>De la demande à la fin du chantier</h2>
      </div>
      <ol class="steps">
{etapes}
      </ol>
    </div>
  </section>

  <!-- ============ POURQUOI PLATEO ============ -->
  <section class="section">
    <div class="container">
      <div class="section-head center reveal">
        <p class="eyebrow">Pourquoi Plateo</p>
        <h2>Par nos artisans qualifiés et sensibilisés</h2>
        <p class="section-intro">Un réseau de plus de 90 artisans partenaires, habitués à intervenir chez des personnes vulnérables.</p>
      </div>
      <div class="why-grid">
{pourquoi}
      </div>
    </div>
  </section>

  <!-- ============ FAQ ============ -->
  <section class="section section-alt" id="faq" aria-labelledby="faq-title">
    <div class="container faq-wrap">
      <div class="section-head reveal">
        <p class="eyebrow">Questions fréquentes</p>
        <h2 id="faq-title">Vos questions sur Plateo</h2>
        <p class="faq-intro">Une autre question&nbsp;? <a href="{root}contact">Contactez-nous</a>.</p>
      </div>
      <div class="faq-list reveal">
{faq}
      </div>
    </div>
  </section>

  <!-- ============ CTA ============ -->
  <section class="section">
    <div class="container">
      <div class="cta-band reveal">
        <div>
          <h2>Des travaux à prévoir chez un bénéficiaire&nbsp;?</h2>
          <p>Décrivez-nous le besoin : nous revenons vers vous rapidement pour organiser la suite.</p>
        </div>
        <div class="cta-actions">
          <a href="{TALLY}" class="btn btn-primary btn-lg" target="_blank" rel="noopener">Faire une demande</a>
          <a href="tel:+33778242775" class="btn btn-link">ou appelez le 07 78 24 27 75</a>
        </div>
      </div>
    </div>
  </section>

</main>
'''
    return head(p["title"], p["description"], url, root, ld) + body + foot(root)


LOGOS_PARTENAIRES = '''          <a href="https://www.tutelleauquotidien.fr/" target="_blank" rel="noopener"><img src="{root}assets/img/webflow/logo_taq_ld_transparent-1--min.webp" width="240" height="239" alt="Tutelle Au Quotidien" loading="lazy"></a>
          <a href="https://plateforme-athena.com/" target="_blank" rel="noopener"><img src="{root}assets/img/webflow/athena-main-logo-1-1--min.webp" width="360" height="224" alt="Athena" loading="lazy"></a>
          <a href="https://horizons.eu.com/" target="_blank" rel="noopener"><img src="{root}assets/img/webflow/logo-horizons-1--min.webp" width="240" height="240" alt="Horizons" loading="lazy"></a>'''
LOGOS_SOUTIENS = '''          <img src="{root}assets/img/webflow/plateo-live4good-logo-transp.webp" width="180" height="96" alt="Live for Good" loading="lazy">
          <img src="{root}assets/img/webflow/plateo-accm-logo-transp.webp" width="180" height="96" alt="Accélérateur M" loading="lazy">
          <img src="{root}assets/img/webflow/nouveau-logo-incoplex-sud__1_-removebg-preview.webp" width="300" height="262" alt="Incoplex" loading="lazy">'''


def page_apropos(d):
    root = ""
    url = SITE + d["slug"]

    chiffres = "\n".join(
        f'''        <div class="fact reveal"><dd>{e(v)}</dd><dt>{e(l)}</dt></div>''' for v, l in d["chiffres"])

    def bloc(i, b):
        corps = "".join(f"<p>{e(x)}</p>" for x in b.get("texte", []))
        if b.get("liste"):
            corps += '<ul class="check-list check-list-1">' + "".join(f"<li>{e(x)}</li>" for x in b["liste"]) + "</ul>"
        return f'''
  <section class="section{' section-alt' if i % 2 else ''}" id="{b['eyebrow'].lower()}">
    <div class="container story{' story-reverse' if i % 2 else ''}">
      <div class="story-media reveal"><img src="{b['image']}" alt="{ea(b['alt'])}" loading="lazy"></div>
      <div class="story-text reveal">
        <p class="eyebrow">{e(b['eyebrow'])}</p>
        <h2>{e(b['titre'])}</h2>
        {corps}
      </div>
    </div>
  </section>'''

    recit = "".join(bloc(i, b) for i, b in enumerate(d["recit"]))

    valeurs = "\n".join(
        f'''        <article class="value-card reveal">
          <span class="value-num">{i:02d}</span>
          <h3>{e(t)}</h3>
          <p>{e(x)}</p>
        </article>''' for i, (t, x) in enumerate(d["valeurs"], 1))

    equipe = "\n".join(
        f'''        <article class="team-card reveal">
          <img src="{m['photo']}" alt="Photo de {ea(m['nom'])}" width="240" height="240" loading="lazy">
          <h3>{e(m['nom'])}</h3>
          <p class="role">{e(m['role'])}</p>
          <blockquote class="team-quote">« {e(m['citation'])} »</blockquote>
          <p class="xp-title">Expériences :</p>
          <ul>
            {''.join(f'<li>{e(x)}</li>' for x in m['experiences'])}
          </ul>
        </article>''' for m in d["equipe"])

    faq = "\n".join(
        f'''        <details class="faq-item"{' open' if i == 0 else ''}>
          <summary><h3>{e(q)}</h3></summary>
          <div class="faq-answer">{''.join(f'<p>{e(x)}</p>' for x in ps)}</div>
        </details>''' for i, (q, ps) in enumerate(d["faq"]))

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "AboutPage",
                "@id": url + "#page",
                "url": url,
                "name": d["title"],
                "description": d["description"],
                "inLanguage": "fr-FR",
                "isPartOf": {"@id": SITE + "#site"},
                "about": {"@id": SITE + "#organisation"},
            },
            {
                "@type": "ProfessionalService",
                "@id": SITE + "#organisation",
                "name": "Plateo",
                "url": SITE,
                "foundingDate": "2020",
                "foundingLocation": {"@type": "Place", "name": "Marseille, France"},
                "founder": [{"@type": "Person", "name": m["nom"], "jobTitle": m["role"]} for m in d["equipe"][:2]],
                "employee": [{"@type": "Person", "name": m["nom"], "jobTitle": m["role"]} for m in d["equipe"]],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": "À propos", "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": " ".join(ps)}} for q, ps in d["faq"]],
            },
        ],
    }

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE DE PAGE ============ -->
  <section class="hero page-hero">
    <div class="container page-hero-grid">
      <div>
        <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
          <ol>
            <li><a href="{root}./">Accueil</a></li>
            <li aria-current="page">À propos</li>
          </ol>
        </nav>
        <h1 class="hero-title" data-split>{e(d['h1'])}</h1>
        {''.join(f'<p class="lead hero-anim">{e(x)}</p>' for x in d['intro'])}
        <div class="btn-row hero-anim">
          <a href="{TALLY}" class="btn btn-primary" target="_blank" rel="noopener">Commander des travaux</a>
          <a href="{root}contact" class="btn btn-ghost">Nous contacter</a>
        </div>
      </div>
      <div class="founders hero-anim">
        <img src="{d['photo_fondateurs']}" alt="Les fondateurs de Plateo, Romain Cordier et Raphaël Wieruszewski" fetchpriority="high">
      </div>
    </div>
  </section>

  <!-- ============ PLATEO EN BREF ============ -->
  <section class="section section-tight">
    <div class="container">
      <h2 class="sr-only">Plateo en bref</h2>
      <dl class="facts">
{chiffres}
      </dl>
      {f'<p class="facts-note reveal">{e(d["chiffres_note"])}</p>' if d.get("chiffres_note") else ""}
    </div>
  </section>
{recit}

  <!-- ============ VALEURS ============ -->
  <section class="section section-dark-soft">
    <div class="container">
      <div class="section-head center reveal">
        <p class="eyebrow">Valeurs</p>
        <h2>Confiance, expertise et solidarité</h2>
      </div>
      <div class="grid-3">
{valeurs}
      </div>
    </div>
  </section>

  <!-- ============ ÉQUIPE ============ -->
  <section class="section" id="equipe">
    <div class="container">
      <div class="section-head center reveal">
        <p class="eyebrow">Notre équipe</p>
        <h2>Une équipe qualifiée et complémentaire</h2>
      </div>
      <div class="grid-3">
{equipe}
      </div>

      <div class="logo-strip reveal">
        <p class="logo-strip-title">Nos partenaires</p>
        <div class="logos">
{LOGOS_PARTENAIRES.format(root=root)}
        </div>
      </div>
      <div class="logo-strip reveal">
        <p class="logo-strip-title">Ils nous accompagnent</p>
        <div class="logos">
{LOGOS_SOUTIENS.format(root=root)}
        </div>
      </div>
    </div>
  </section>

  <!-- ============ FAQ ============ -->
  <section class="section section-alt" id="faq" aria-labelledby="faq-title">
    <div class="container faq-wrap">
      <div class="section-head reveal">
        <p class="eyebrow">Questions fréquentes</p>
        <h2 id="faq-title">Qu'est-ce que Plateo peut faire pour vous&nbsp;?</h2>
        <p class="faq-intro">Une autre question&nbsp;? <a href="{root}contact">Contactez-nous</a>.</p>
      </div>
      <div class="faq-list reveal">
{faq}
      </div>
    </div>
  </section>

  <!-- ============ CTA ============ -->
  <section class="section">
    <div class="container">
      <div class="cta-band reveal">
        <div>
          <h2>Gagnez du temps&nbsp;: confiez-nous les travaux chez vos bénéficiaires</h2>
          <ul class="check-list">
            <li><a href="{root}accompagnement-travaux-plateo">Accompagnement Travaux</a></li>
            <li><a href="{root}audit-securite-salubrite">Audit Sécurité / Salubrité</a></li>
            <li><a href="{root}les-specialites#depannages">Dépannages</a></li>
            <li><a href="{root}les-specialites">Travaux sur devis</a></li>
          </ul>
        </div>
        <div class="cta-actions">
          <a href="{TALLY}" class="btn btn-primary btn-lg" target="_blank" rel="noopener">Faire une demande</a>
          <a href="tel:+33778242775" class="btn btn-link">ou appelez le 07 78 24 27 75</a>
        </div>
      </div>
    </div>
  </section>

</main>
'''
    return head(d["title"], d["description"], url, root, ld) + body + foot(root)


def blocs_html(items):
    """Paragraphes (texte ou HTML simple) ; une liste <ul> est insérée telle quelle."""
    return "".join(x if x.lstrip().startswith("<ul") else f"<p>{x}</p>" for x in items)


def texte_brut(items):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", x)) for x in items).replace("  ", " ").strip()


def niveaux_titres(corps):
    """Remet les intertitres d'un article dans l'ordre (h2, puis h3…) sans sauter de niveau."""
    precedent = 1

    def remplacer(m):
        nonlocal precedent
        niveau = max(2, min(int(m.group(1)), precedent + 1))
        precedent = niveau
        return f"<h{niveau}{m.group(2)}>{m.group(3)}</h{niveau}>"

    return re.sub(r"<h([2-6])(\b[^>]*)>(.*?)</h\1>", remplacer, corps, flags=re.S)


def couper(t, n=157):
    """Coupe un texte à n caractères maximum, sur un mot entier."""
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,;:–-") + "…"


def meta_description(resume, corps):
    """Description pour Google : 70 à 160 caractères, complétée par le début de l'article si besoin."""
    resume = re.sub(r"\s+", " ", resume).strip()
    if len(resume) >= 70:
        return couper(resume)
    debut = texte_brut([corps])
    base = (resume.rstrip(".!?…") + ". " if resume else "") + debut
    return couper(base)


def page_pilier(d, pourquoi_items):
    """Page de service principal (Accompagnement Travaux, Audit Sécurité / Salubrité)."""
    root = ""
    url = SITE + d["slug"]

    etapes = "\n".join(
        f'''        <li class="tl-step reveal">
          <span class="tl-num">{i}</span>
          <div class="tl-body">
            <h3>{e(s['titre'])}{' <span class="tl-option">En option</span>' if s['option'] else ''}</h3>
            {blocs_html(s['html'])}
          </div>
        </li>''' for i, s in enumerate(d["etapes"], 1))

    faq = "\n".join(
        f'''        <details class="faq-item faq-rich"{' open' if i == 0 else ''}>
          <summary><h3>{e(f['question'])}</h3></summary>
          <div class="faq-answer">{blocs_html(f['html'])}</div>
        </details>''' for i, f in enumerate(d["faq"]))

    pourquoi = "\n".join(
        f'''          <div class="why-item reveal">
            <h3>{e(t)}</h3>
            <p>{e(x)}</p>
          </div>''' for t, x in pourquoi_items)

    offres = "\n".join(
        f'''        <article class="offer-card reveal">
          <h3>{e(o['titre'])}</h3>
          <p>{e(o['texte'])}</p>
          <p class="offer-dispo">{e(o['dispo'])}</p>
          <a href="{root}{o['lien']}" class="btn btn-link">{e(o['bouton'])} →</a>
        </article>''' for o in d["offres"])

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Service",
                "@id": url + "#service",
                "name": d["nom"],
                "serviceType": d["service_type"],
                "description": " ".join(d["intro"]),
                "url": url,
                "provider": {"@id": SITE + "#organisation"},
                "areaServed": {"@type": "Country", "name": "France"},
                "audience": {"@type": "Audience", "audienceType": "Mandataires judiciaires à la protection des majeurs (MJPM) et majeurs protégés"},
                "hasOfferCatalog": {
                    "@type": "OfferCatalog",
                    "name": d["etude_titre"],
                    "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["titre"] + (" (en option)" if s["option"] else ""), "description": texte_brut(s["html"])}} for s in d["etapes"]],
                },
            },
            *([{
                "@type": "HowTo",
                "name": d["etude_titre"],
                "description": d["etude_intro"],
                "step": [{"@type": "HowToStep", "position": i, "name": s["titre"], "text": texte_brut(s["html"])} for i, s in enumerate(d["etapes"], 1)],
            }] if d.get("howto") else []),
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": d["nom"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [{"@type": "Question", "name": f["question"], "acceptedAnswer": {"@type": "Answer", "text": texte_brut(f["html"])}} for f in d["faq"]],
            },
        ],
    }

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE DE PAGE ============ -->
  <section class="hero page-hero">
    <div class="container page-hero-grid">
      <div>
        <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
          <ol>
            <li><a href="{root}./">Accueil</a></li>
            <li aria-current="page">{e(d['nom'])}</li>
          </ol>
        </nav>
        <p class="eyebrow hero-anim">{e(d['eyebrow'])}</p>
        <h1 class="hero-title" data-split>{e(d['h1'])}</h1>
        {''.join(f'<p class="lead hero-anim">{e(x)}</p>' for x in d['intro'])}
        <div class="btn-row hero-anim">
          <a href="{TALLY}" class="btn btn-primary" target="_blank" rel="noopener">{e(d['cta_bouton'])}</a>
          <a href="tel:+33778242775" class="btn btn-ghost">07 78 24 27 75</a>
        </div>
        <p class="badge badge-green hero-anim">🇫🇷 {e(d['badge'])}</p>
      </div>
      <div class="page-hero-photo hero-anim">
        <img src="{root}{d['image']}" alt="{ea(d['image_alt'])}" width="900" height="600" fetchpriority="high">
      </div>
    </div>
  </section>

  <!-- ============ ÉTUDE TECHNIQUE ============ -->
  <section class="section">
    <div class="container">
      <div class="section-head reveal">
        <p class="eyebrow">{e(d['deroule_eyebrow'])}</p>
        <h2>{e(d['etude_titre'])}</h2>
        <p class="section-intro">{e(d['etude_intro'])}</p>
        {''.join(f'<p class="section-intro">{e(x)}</p>' for x in d.get('etude_paragraphes', []))}
      </div>
      <ol class="timeline">
{etapes}
      </ol>
    </div>
  </section>

  <!-- ============ FAQ ============ -->
  <section class="section section-alt" id="faq" aria-labelledby="faq-title">
    <div class="container faq-wrap">
      <div class="section-head reveal">
        <p class="eyebrow">Foire aux questions</p>
        <h2 id="faq-title">{e(d['faq_titre'])}</h2>
        <p class="faq-intro">Une autre question&nbsp;? <a href="{root}contact">Contactez-nous</a>.</p>
      </div>
      <div class="faq-list reveal">
{faq}
      </div>
    </div>
  </section>

  <!-- ============ POURQUOI PLATEO ============ -->
  <section class="section">
    <div class="container">
      <div class="section-head center reveal">
        <p class="eyebrow">Pourquoi utiliser Plateo&nbsp;?</p>
        <h2>Un service élaboré pour les MJPM et les Majeurs Protégés</h2>
      </div>
      <div class="why-grid">
{pourquoi}
      </div>
    </div>
  </section>

  <!-- ============ OFFRES COMPLÉMENTAIRES ============ -->
  <section class="section section-dark-soft">
    <div class="container">
      <div class="section-head reveal">
        <p class="eyebrow">Nos autres services</p>
        <h2>Des offres complémentaires</h2>
      </div>
      <div class="grid-3">
{offres}
      </div>
    </div>
  </section>

  <!-- ============ CTA ============ -->
  <section class="section">
    <div class="container">
      <div class="cta-band reveal">
        <div>
          <h2>{e(d['cta_titre'])}</h2>
          <p>{e(d['cta_texte'])}</p>
        </div>
        <div class="cta-actions">
          <a href="{TALLY}" class="btn btn-primary btn-lg" target="_blank" rel="noopener">{e(d['cta_bouton'])}</a>
          <a href="tel:+33778242775" class="btn btn-link">ou appelez le 07 78 24 27 75</a>
        </div>
      </div>
    </div>
  </section>

</main>
'''
    return head(d["title"], d["description"], url, root, ld) + body + foot(root)


def slugify(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def date_fr(iso):
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    a, m, j = iso.split("-")
    return f"{int(j)} {mois[int(m) - 1]} {a}"


def page_media(d):
    root = "../"  # la liste est servie à /media/ (media/index.html)
    p = d["page"]
    url = SITE + p["slug"] + "/"
    arts = [a for a in d["articles"] if not a.get("masquer")]
    cats = []
    for a in arts:
        if a["categorie"] not in cats:
            cats.append(a["categorie"])
    if "Autre" in cats:  # « Autre » toujours en dernier
        cats.remove("Autre")
        cats.append("Autre")

    filtres = f'''<button type="button" class="chip is-active" data-filter="" aria-pressed="true">Tous <span>{len(arts)}</span></button>''' + "".join(
        f'''<button type="button" class="chip" data-filter="{slugify(c)}" aria-pressed="false">{e(c)} <span>{sum(a['categorie'] == c for a in arts)}</span></button>'''
        for c in cats)

    def carte(a):
        img = f'<div class="article-media"><img src="{a["image"]}" alt="" loading="lazy"></div>' if a.get("image") else ""
        meta = f'<time datetime="{a["date"]}">{date_fr(a["date"])}</time>' if a.get("date") else ""
        resume = f'<p>{e(a["resume"])}</p>' if a.get("resume") else ""
        return f'''        <a class="article-card{' has-media' if img else ''}" href="{a['slug']}" data-cat="{slugify(a['categorie'])}" data-search="{ea(slugify(a['titre'] + ' ' + (a.get('resume') or '')))}">
          {img}<span class="tag">{e(a['categorie'])}</span>
          <h2>{e(a['titre'])}</h2>
          {resume}
          <span class="article-foot">{meta}<span class="trade-more">Lire l'article →</span></span>
        </a>'''

    cartes = "\n".join(carte(a) for a in arts)

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url + "#page",
                "url": url,
                "name": p["title"],
                "description": p["description"],
                "inLanguage": "fr-FR",
                "isPartOf": {"@id": SITE + "#site"},
                "publisher": {"@id": SITE + "#organisation"},
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(arts),
                    "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{url}{a['slug']}", "name": a["titre"]} for i, a in enumerate(arts, 1)],
                },
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": "Le média", "item": url},
                ],
            },
        ],
    }

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE DE PAGE ============ -->
  <section class="hero page-hero">
    <div class="container">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Le média</li>
        </ol>
      </nav>
      <div class="page-hero-text">
        <h1 class="hero-title" data-split>{e(p['h1'])}</h1>
        {''.join(f'<p class="lead hero-anim">{e(x)}</p>' for x in p['intro'])}
      </div>
    </div>
  </section>

  <!-- ============ ARTICLES ============ -->
  <section class="section" data-filter-list>
    <div class="container">
      <div class="media-tools">
        <div class="chips" role="group" aria-label="Filtrer par catégorie">
          {filtres}
        </div>
        <label class="search">
          <span class="sr-only">Rechercher un article</span>
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M20 20l-4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <input type="search" placeholder="Rechercher un article…" data-search-input>
        </label>
      </div>
      <p class="media-count" aria-live="polite" data-count-label>{len(arts)} articles</p>
      <div class="grid-3 articles-grid">
{cartes}
      </div>
      <p class="media-empty" hidden data-empty>Aucun article ne correspond à votre recherche. <a href="{root}contact">Posez-nous votre question</a>.</p>
    </div>
  </section>

  <!-- ============ CTA ============ -->
  <section class="section section-alt">
    <div class="container">
      <div class="cta-band reveal">
        <div>
          <h2>Une question sur le logement d'un bénéficiaire&nbsp;?</h2>
          <p>Décrivez-nous la situation : nous vous orientons vers la bonne solution.</p>
        </div>
        <div class="cta-actions">
          <a href="{TALLY}" class="btn btn-primary btn-lg" target="_blank" rel="noopener">Faire une demande</a>
          <a href="tel:+33778242775" class="btn btn-link">ou appelez le 07 78 24 27 75</a>
        </div>
      </div>
    </div>
  </section>

</main>
'''
    return head(p["title"], p["description"], url, root, ld) + body + foot(root)


CTA_ARTICLE = {
    "Réglementation": ("Des travaux à prévoir pour respecter la réglementation ?", "Plateo vous aide à cadrer les travaux nécessaires chez votre bénéficiaire.", "accompagnement-travaux-plateo", "Découvrir l'Accompagnement Travaux"),
    "Étude de cas": ("Une situation similaire chez un bénéficiaire ?", "Décrivez-nous la situation : nous étudierons les solutions possibles.", "accompagnement-travaux-plateo", "Découvrir l'Accompagnement Travaux"),
}
CTA_DEFAUT = ("Besoin d'un artisan chez un bénéficiaire ?", "Dépannages et travaux dans toutes les spécialités, avec un interlocuteur unique.", "les-specialites", "Voir nos spécialités")


def page_article(a, tous):
    root = "../"
    url = f"{SITE}media/{a['slug']}"
    corps = (ROOT / "data" / "articles" / f"{a['slug']}.html").read_text(encoding="utf-8").replace("{{root}}", root)
    corps = niveaux_titres(corps)
    mots = len(re.sub(r"<[^>]+>", " ", corps).split())
    lecture = max(1, round(mots / 200))
    resume = a.get("resume") or texte_brut([corps])[:155].rsplit(" ", 1)[0] + "…"
    meta_desc = meta_description(a.get("resume") or "", corps)
    titre, texte, lien, bouton = CTA_ARTICLE.get(a["categorie"], CTA_DEFAUT)

    autres = [x for x in tous if x["slug"] != a["slug"] and not x.get("masquer")]
    lies = [x for x in autres if x["categorie"] == a["categorie"]]
    lies = sorted(lies, key=lambda x: x.get("date") or "", reverse=True)
    lies = sorted(lies, key=lambda x: not x.get("a_la_une"))  # « à la une » d'abord, puis les plus récents
    lies = (lies + [x for x in autres if x not in lies])[:3]
    cartes = "\n".join(
        f'''        <a class="article-card has-media" href="{root}media/{x['slug']}">
          {f'<div class="article-media"><img src="{x["image"]}" alt="" loading="lazy"></div>' if x.get("image") else ''}<span class="tag">{e(x['categorie'])}</span>
          <h3>{e(x['titre'])}</h3>
          <span class="trade-more">Lire l'article →</span>
        </a>''' for x in lies)

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": url + "#article",
                "mainEntityOfPage": url,
                "headline": a["titre"],
                "description": resume,
                "inLanguage": "fr-FR",
                "articleSection": a["categorie"],
                "wordCount": mots,
                **({"image": a["image"]} if a.get("image") else {}),
                **({"datePublished": a["date"]} if a.get("date") else {}),
                **({"dateModified": a.get("maj") or a["date"]} if a.get("date") else {}),
                "author": {"@type": "Person", "name": a.get("auteur", "Plateo")},
                "publisher": {"@id": SITE + "#organisation"},
                "isPartOf": {"@id": SITE + "media/#page"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": "Le média", "item": SITE + "media/"},
                    {"@type": "ListItem", "position": 3, "name": a["titre"], "item": url},
                ],
            },
        ],
    }

    meta = " · ".join(filter(None, [
        f"Par {e(a.get('auteur', 'Plateo'))}",
        f'<time datetime="{a["date"]}">{date_fr(a["date"])}</time>' if a.get("date") else "",
        f"{lecture} min de lecture",
    ]))

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE D'ARTICLE ============ -->
  <section class="hero page-hero article-hero">
    <div class="container article-narrow">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li><a href="{root}media/">Le média</a></li>
          <li aria-current="page">{e(a['categorie'])}</li>
        </ol>
      </nav>
      <h1 class="hero-anim">{e(a['titre'])}</h1>
      {f'<p class="lead hero-anim">{e(a["resume"])}</p>' if a.get("resume") else ''}
      <p class="article-meta hero-anim">{meta}</p>
    </div>
  </section>

  <article class="section article-body-section">
    <div class="container article-narrow">
      {f'<img class="article-cover" src="{a["image"]}" alt="" fetchpriority="high">' if a.get("image") else ''}
      <div class="prose">
{corps}
      </div>

      <aside class="article-cta">
        <p class="article-cta-title">{e(titre)}</p>
        <p>{e(texte)}</p>
        <div class="btn-row">
          <a href="{root}{lien}" class="btn btn-primary">{e(bouton)}</a>
          <a href="{TALLY}" class="btn btn-ghost" target="_blank" rel="noopener">Faire une demande</a>
        </div>
      </aside>
    </div>
  </article>

  <!-- ============ ARTICLES LIÉS ============ -->
  <section class="section section-alt">
    <div class="container">
      <div class="section-head split">
        <div>
          <p class="eyebrow">Le média</p>
          <h2>À lire aussi</h2>
        </div>
        <a href="{root}media/" class="btn btn-ghost">Tous les articles</a>
      </div>
      <div class="grid-3 articles-grid">
{cartes}
      </div>
    </div>
  </section>

</main>
'''
    return head(f"{a['titre']} | Plateo", meta_desc, url, root, ld) + body + foot(root)


def page_ressources(d):
    root = ""
    url = SITE + d["slug"]
    f = d["formulaire"]
    check = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M5 12.5l4.2 4.2L19 7"/></svg>'

    livres = "\n".join(
        f'''        <article class="book reveal" id="{l['id']}">
          <div class="book-cover"><img src="{l['couverture']}" alt="Couverture du livre blanc #{l['numero']} : {ea(l['titre'])}" loading="lazy"></div>
          <div class="book-body">
            <p class="tag">Livre blanc #{l['numero']} · {l['pages']} pages</p>
            <h2>{e(l['titre'])}</h2>
            <ul class="book-points">
              {''.join(f'<li>{check}<span>{e(p)}</span></li>' for p in l['points'])}
            </ul>
            <a href="#formulaire" class="btn btn-primary" data-choose-book="{l['id']}">Recevoir ce livre blanc</a>
          </div>
        </article>''' for l in d["livres"])

    choix = "\n".join(
        f'''            <label class="check"><input type="checkbox" name="livres_blancs" value="#{l['numero']} {ea(l['titre'])}" data-book="{l['id']}"> <span>#{l['numero']} – {e(l['titre'])}</span></label>'''
        for l in d["livres"])
    structures = "\n".join(
        f'''            <label class="check"><input type="radio" name="structure" value="{ea(s)}" required> <span>{e(s)}</span></label>'''
        for s in f["structures"])

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url + "#page",
                "url": url,
                "name": d["title"],
                "description": d["description"],
                "inLanguage": "fr-FR",
                "isPartOf": {"@id": SITE + "#site"},
                "mainEntity": {
                    "@type": "ItemList",
                    "itemListElement": [{"@type": "ListItem", "position": i, "item": {
                        "@type": "Book", "name": f"Livre blanc #{l['numero']} : {l['titre']}", "numberOfPages": l["pages"],
                        "bookFormat": "https://schema.org/EBook", "inLanguage": "fr-FR", "image": l["couverture"],
                        "author": {"@id": SITE + "#organisation"}, "isAccessibleForFree": True,
                        "abstract": " ; ".join(l["points"])}} for i, l in enumerate(d["livres"], 1)],
                },
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": "Ressources", "item": url},
                ],
            },
        ],
    }

    body = f'''
<main id="contenu">

  <!-- ============ EN-TÊTE DE PAGE ============ -->
  <section class="hero page-hero">
    <div class="container">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Ressources</li>
        </ol>
      </nav>
      <div class="page-hero-text">
        <h1 class="hero-title" data-split>{e(d['h1'])}</h1>
        {''.join(f'<p class="lead hero-anim">{e(x)}</p>' for x in d['intro'])}
        <div class="btn-row hero-anim">
          <a href="#formulaire" class="btn btn-primary">Recevoir les livres blancs</a>
        </div>
      </div>
    </div>
  </section>

  <!-- ============ LIVRES BLANCS ============ -->
  <section class="section">
    <div class="container books">
{livres}
    </div>
  </section>

  <!-- ============ FORMULAIRE ============ -->
  <section class="section section-dark-soft" id="formulaire">
    <div class="container form-wrap">
      <div class="form-intro reveal">
        <p class="eyebrow">Gratuit</p>
        <h2>Recevez les livres blancs par mail</h2>
        <p>Choisissez un ou plusieurs livres blancs : nous vous les envoyons dans votre boîte mail.</p>
        <p class="form-privacy">{e(f['confidentialite'])}</p>
      </div>
      <form class="lead-form reveal" action="https://api.web3forms.com/submit" method="POST" data-lead-form
            data-success="{ea(f['succes'])}" data-error="{ea(f['erreur'])}">
        <input type="hidden" name="access_key" value="{ea(f['cle'])}">
        <input type="hidden" name="subject" value="{ea(f['objet'])}">
        <input type="hidden" name="from_name" value="Site Plateo – Ressources">
        <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">

        <fieldset>
          <legend>Livre(s) blanc(s) souhaité(s) <span aria-hidden="true">*</span></legend>
          <div class="check-grid">
{choix}
          </div>
        </fieldset>

        <div class="form-row">
          <label class="field">
            <span>Prénom <span aria-hidden="true">*</span></span>
            <input type="text" name="prenom" autocomplete="given-name" required>
          </label>
          <label class="field">
            <span>Adresse e-mail <span aria-hidden="true">*</span></span>
            <input type="email" name="email" autocomplete="email" required>
          </label>
        </div>

        <fieldset>
          <legend>Vous êtes <span aria-hidden="true">*</span></legend>
          <div class="check-grid">
{structures}
          </div>
          <label class="field assoc-field" data-show-if="Association tutélaire" hidden>
            <span>Nom de votre association <span aria-hidden="true">*</span></span>
            <input type="text" name="association" autocomplete="organization">
          </label>
        </fieldset>

        <label class="check consent">
          <input type="checkbox" name="consentement" value="oui" required>
          <span>J'accepte que Plateo utilise mes coordonnées pour m'envoyer le ou les livres blancs demandés. <a href="{root}mentions-legales">Politique de confidentialité</a></span>
        </label>

        <button type="submit" class="btn btn-primary btn-lg">Recevoir les livres blancs</button>
        <p class="form-status" role="status" aria-live="polite" hidden></p>
      </form>
    </div>
  </section>

</main>
'''
    return head(d["title"], d["description"], url, root, ld) + body + foot(root)


def page_mentions():
    root = ""
    url = SITE + "mentions-legales"
    corps = (ROOT / "data" / "mentions-legales.html").read_text(encoding="utf-8")
    titres = [(i, re.sub(r"^[0-9]+[.] ", "", t)) for i, t in re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', corps)]
    sommaire = "".join(f'<li><a href="#{i}">{e(t)}</a></li>' for i, t in titres)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url + "#page", "url": url, "name": "Mentions légales et politique de confidentialité",
         "inLanguage": "fr-FR", "isPartOf": {"@id": SITE + "#site"}, "publisher": {"@id": SITE + "#organisation"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Mentions légales", "item": url}]}]}
    body = f'''
<main id="contenu">
  <section class="hero page-hero article-hero legal-hero">
    <div class="container article-narrow">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Mentions légales</li>
        </ol>
      </nav>
      <h1 class="hero-anim">Mentions légales et politique de confidentialité</h1>
      <p class="article-meta hero-anim">Dernière mise à jour : {date_fr(MAJ_MENTIONS)}</p>
    </div>
  </section>
  <section class="section">
    <div class="container article-narrow">
      <nav class="legal-toc" aria-label="Sommaire"><p>Sommaire</p><ol>{sommaire}</ol></nav>
      <div class="prose legal">
{corps}
      </div>
    </div>
  </section>
</main>
'''
    return head("Mentions légales et politique de confidentialité | Plateo",
                "Mentions légales du site Plateo (PLATEO SASU, Marseille) et politique de confidentialité : données collectées, finalités, durées de conservation et droits.",
                url, root, ld) + body + foot(root)


def page_contact(f):
    root = ""
    url = SITE + "contact"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "ContactPage", "@id": url + "#page", "url": url, "name": "Contact", "inLanguage": "fr-FR",
         "isPartOf": {"@id": SITE + "#site"}, "about": {"@id": SITE + "#organisation"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Contact", "item": url}]}]}
    icon = lambda d: f'<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="{d}"/></svg>'
    body = f'''
<main id="contenu">

  <section class="hero page-hero">
    <div class="container">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Contact</li>
        </ol>
      </nav>
      <div class="page-hero-text">
        <h1 class="hero-title" data-split>Besoin d'informations&nbsp;?</h1>
        <p class="lead hero-anim">Une question ou un projet&nbsp;? Remplissez le formulaire ci-dessous, nous vous répondons rapidement.</p>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container contact-grid">
      <div class="contact-cards">
        <a class="contact-card reveal" href="tel:+33778242775">{icon("M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z")}<span><strong>Téléphone</strong>07 78 24 27 75</span></a>
        <a class="contact-card reveal" href="mailto:contact@plateo.fr">{icon("M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm18 2-10 7L2 6")}<span><strong>Adresse mail</strong>contact@plateo.fr</span></a>
        <div class="contact-card reveal">{icon("M12 22s-8-7.6-8-13a8 8 0 0 1 16 0c0 5.4-8 13-8 13zm0-10a3 3 0 1 0 0-6 3 3 0 0 0 0 6z")}<span><strong>Siège</strong>13004 Marseille</span></div>
        <div class="contact-devis reveal">
          <p class="contact-devis-title">Une demande de travaux&nbsp;?</p>
          <p>Pour un devis, un dépannage ou un accompagnement, utilisez directement notre formulaire de demande.</p>
          <a href="{TALLY}" class="btn btn-primary" target="_blank" rel="noopener">Faire une demande de travaux</a>
        </div>
      </div>

      <form class="lead-form contact-form reveal" action="https://api.web3forms.com/submit" method="POST" data-lead-form
            data-success="Merci ! Votre message a bien été envoyé. Nous revenons vers vous rapidement."
            data-error="{ea(f['erreur'])}">
        <h2>Écrivez-nous</h2>
        <input type="hidden" name="access_key" value="{ea(f['cle'])}">
        <input type="hidden" name="subject" value="Nouveau message – formulaire de contact du site Plateo">
        <input type="hidden" name="from_name" value="Site Plateo – Contact">
        <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
        <div class="form-row">
          <label class="field"><span>Prénom <span aria-hidden="true">*</span></span><input type="text" name="prenom" autocomplete="given-name" required></label>
          <label class="field"><span>Nom <span aria-hidden="true">*</span></span><input type="text" name="nom" autocomplete="family-name" required></label>
        </div>
        <label class="field"><span>Adresse e-mail <span aria-hidden="true">*</span></span><input type="email" name="email" autocomplete="email" required></label>
        <label class="field"><span>Message <span aria-hidden="true">*</span></span><textarea name="message" rows="6" required></textarea></label>
        <p class="form-notice">Vos données servent uniquement à répondre à votre message. <a href="{root}mentions-legales#donnees">En savoir plus</a></p>
        <button type="submit" class="btn btn-primary btn-lg">Envoyer le message</button>
        <p class="form-status" role="status" aria-live="polite" hidden></p>
      </form>
    </div>
  </section>

</main>
'''
    return head("Contact : demandez un devis ou posez votre question | Plateo",
                "Contactez Plateo, coordination de travaux pour les MJPM à Marseille et partout en France : 07 78 24 27 75, contact@plateo.fr, ou via notre formulaire.",
                url, root, ld) + body + foot(root)


CLIENT_PHRASE = {"Association tutélaire": "une association tutélaire", "MJPM indépendant": "un MJPM indépendant",
                 "Préposé d'établissement": "un préposé d'établissement", "Coordinateur de parcours complexe": "un coordinateur de parcours complexe",
                 "CHRS": "un CHRS"}


def carte_projet(r, root, metiers, titre_tag="h3", filtre=False):
    m = metiers.get(r["specialite"], {})
    attrs = f' data-cat="{r["specialite"]}" data-search="{ea(slugify(r["titre"] + " " + r["client"] + " " + m.get("nom", "")))}"' if filtre else ""
    return f'''        <a class="project-card" href="{root}projects/{r['slug']}"{attrs}>
          <div class="project-media"><img src="{r['image']}" alt="Photo du chantier : {ea(r['titre'].lower())}" loading="lazy"></div>
          <div class="project-body">
            <span class="tag">{e(r['client'])}</span>
            <{titre_tag}>{e(r['titre'])}</{titre_tag}>
            <span class="project-spec">{e(m.get('nom', ''))}</span>
          </div>
        </a>'''


def page_projets(reals, metiers):
    root = ""
    url = SITE + "projets"
    visibles = [r for r in reals if not r.get("masquer")]
    ordre = [s for s in metiers if any(r["specialite"] == s for r in visibles)]
    filtres = f'<button type="button" class="chip is-active" data-filter="" aria-pressed="true">Toutes <span>{len(visibles)}</span></button>' + "".join(
        f'<button type="button" class="chip" data-filter="{s}" aria-pressed="false">{e(metiers[s]["nom"])} <span>{sum(r["specialite"] == s for r in visibles)}</span></button>'
        for s in ordre)
    cartes = "\n".join(carte_projet(r, root, metiers, "h2", filtre=True) for r in visibles)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": "Les réalisations de Plateo", "inLanguage": "fr-FR",
         "isPartOf": {"@id": SITE + "#site"}, "about": {"@id": SITE + "#organisation"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(visibles), "itemListElement": [
             {"@type": "ListItem", "position": i, "url": f"{SITE}projects/{r['slug']}", "name": r["titre"]} for i, r in enumerate(visibles, 1)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Réalisations", "item": url}]}]}
    body = f'''
<main id="contenu">

  <section class="hero page-hero">
    <div class="container">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li aria-current="page">Réalisations</li>
        </ol>
      </nav>
      <div class="page-hero-text">
        <h1 class="hero-title" data-split>Nos réalisations</h1>
        <p class="lead hero-anim">Associations tutélaires, MJPM indépendants, préposés d'établissements : ils nous ont confié des travaux chez leurs bénéficiaires. Découvrez quelques exemples de chantiers.</p>
      </div>
    </div>
  </section>

  <section class="section" data-filter-list>
    <div class="container">
      <div class="media-tools">
        <div class="chips" role="group" aria-label="Filtrer par spécialité">
          {filtres}
        </div>
      </div>
      <p class="media-count" aria-live="polite" data-count-label data-unit="réalisation">{len(visibles)} réalisations</p>
      <div class="grid-4 projects-grid projects-all">
{cartes}
      </div>
      <p class="media-empty" hidden data-empty>Aucune réalisation dans cette catégorie pour le moment.</p>
    </div>
  </section>

  <section class="section section-alt">
    <div class="container">
      <div class="cta-band reveal">
        <div>
          <h2>Des travaux à prévoir chez un bénéficiaire&nbsp;?</h2>
          <p>Décrivez-nous le besoin : nous étudierons les solutions possibles.</p>
        </div>
        <div class="cta-actions">
          <a href="{TALLY}" class="btn btn-primary btn-lg" target="_blank" rel="noopener">Faire une demande</a>
          <a href="{root}les-specialites" class="btn btn-link">Voir nos spécialités →</a>
        </div>
      </div>
    </div>
  </section>

</main>
'''
    return head("Nos réalisations : travaux chez les majeurs protégés | Plateo",
                "Exemples de chantiers réalisés par Plateo pour des associations tutélaires, MJPM indépendants et préposés d'établissements : adaptation, remise en état, dépannages…",
                url, root, ld) + body + foot(root)


def page_projet(r, reals, metiers):
    root = "../"
    url = f"{SITE}projects/{r['slug']}"
    m = metiers.get(r["specialite"], {})
    qui = CLIENT_PHRASE.get(r["client"])
    texte = r.get("texte") or ""
    intro = f"Chantier réalisé par Plateo pour {qui}." if qui else "Chantier réalisé par Plateo."
    autres = [x for x in reals if x["slug"] != r["slug"] and not x.get("masquer")]
    lies = ([x for x in autres if x["specialite"] == r["specialite"]] + [x for x in autres if x["specialite"] != r["specialite"]])[:4]
    cartes = "\n".join(carte_projet(x, root, metiers) for x in lies)
    desc = couper(f"{r['titre']} : {texte or intro} Plateo coordonne les travaux chez les majeurs protégés pour les MJPM.")
    # Plusieurs chantiers portent le même nom : on les distingue par le client et l'année
    homonymes = [x for x in reals if x["titre"] == r["titre"] and not x.get("masquer")]
    titre_page = r["titre"]
    if len(homonymes) > 1:
        precision = ", ".join(filter(None, [r.get("client"), (r.get("date") or "")[:4]]))
        if sum(1 for x in homonymes if x.get("client") == r.get("client")
               and (x.get("date") or "")[:4] == (r.get("date") or "")[:4]) > 1:
            precision += f", n° {homonymes.index(r) + 1}"
        titre_page = f"{r['titre']} ({precision})"
        desc = couper(f"{r['titre']} ({precision}) : {texte or intro} Plateo coordonne les travaux chez les majeurs protégés.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CreativeWork", "@id": url + "#realisation", "url": url, "name": r["titre"], "inLanguage": "fr-FR",
         "description": texte or intro, **({"image": r["image"]} if r.get("image") else {}),
         **({"dateCreated": r["date"]} if r.get("date") else {}),
         "creator": {"@id": SITE + "#organisation"}, "about": m.get("nom", "")},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Réalisations", "item": SITE + "projets"},
            {"@type": "ListItem", "position": 3, "name": r["titre"], "item": url}]}]}
    body = f'''
<main id="contenu">

  <section class="hero page-hero article-hero">
    <div class="container article-narrow">
      <nav class="breadcrumb hero-anim" aria-label="Fil d'Ariane">
        <ol>
          <li><a href="{root}./">Accueil</a></li>
          <li><a href="{root}projets">Réalisations</a></li>
          <li aria-current="page">{e(r['titre'])}</li>
        </ol>
      </nav>
      <h1 class="hero-anim">{e(r['titre'])}</h1>
      <p class="article-meta hero-anim">{e(r['client'])}{' · ' + e(m['nom']) if m else ''}</p>
    </div>
  </section>

  <article class="section article-body-section">
    <div class="container article-narrow">
      {f'<img class="article-cover project-cover" src="{r["image"]}" alt="Photo du chantier : {ea(r["titre"].lower())}" fetchpriority="high">' if r.get("image") else ''}
      <div class="prose">
        <p>{e(intro)}</p>
        {f'<p>{e(texte)}</p>' if texte else ''}
      </div>
      {f"""<aside class="article-cta">
        <p class="article-cta-title">{e(m['nom'])}</p>
        <p>{e(m['intro'])}</p>
        <div class="btn-row">
          <a href="{root}les-specialites#{r['specialite']}" class="btn btn-primary">Découvrir nos interventions</a>
          <a href="{TALLY}" class="btn btn-ghost" target="_blank" rel="noopener">Faire une demande</a>
        </div>
      </aside>""" if m else ''}
    </div>
  </article>

  <section class="section section-alt">
    <div class="container">
      <div class="section-head split">
        <div>
          <p class="eyebrow">Réalisations</p>
          <h2>D'autres chantiers</h2>
        </div>
        <a href="{root}projets" class="btn btn-ghost">Toutes les réalisations</a>
      </div>
      <div class="grid-4 projects-grid">
{cartes}
      </div>
    </div>
  </section>

</main>
'''
    return head(f"{titre_page} – Réalisation | Plateo", desc, url, root, ld) + body + foot(root)


def page_renvoi(cible, nom, prefixe="../"):
    """Page de renvoi pour une ancienne adresse (équivalent d'une redirection 301)."""
    return f'''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{e(nom)} – Plateo</title>
  <link rel="canonical" href="{SITE + cible.split('#')[0]}">
  <meta http-equiv="refresh" content="0; url={prefixe}{cible}">
  <script>location.replace("{prefixe}{cible}");</script>
</head>
<body>
  <p>Cette page a été déplacée : <a href="{prefixe}{cible}">{e(nom)}</a>.</p>
</body>
</html>
'''


# Anciennes adresses Webflow sans équivalent direct : renvoi vers la page la plus proche
RENVOIS = {
    "groupes-de-travail": ("media/", "Le média"),
    "groupe-de-travail/comment-gerer-un-degat-des-eaux": ("media/comment-gerer-un-degat-des-eaux-dans-le-logement-dun-majeur-protege", "Comment gérer un dégât des eaux ?"),
    "groupe-de-travail/le-contrat-dentretien-des-chaudieres-gaz": ("media/est-ce-quun-contrat-dentretien-est-obligatoire-pour-une-chaudiere-a-gaz", "Le contrat d'entretien des chaudières gaz"),
    "search": ("media/", "Le média"),
    "blog-author/malaika-h": ("media/", "Le média"),
    "blog-author/nathalie-p": ("media/", "Le média"),
    "blog-author/raphael-w": ("a-propos#equipe", "Notre équipe"),
    "blog-author/romain-cordier": ("a-propos#equipe", "Notre équipe"),
    "template/changelog": ("./", "Accueil"),
    "template/licence": ("./", "Accueil"),
    "template/style-guide": ("./", "Accueil"),
    # Redirections 301 configurées dans Webflow
    "media-copy": ("ressources", "Ressources"),
    "service-plateo": ("accompagnement-travaux-plateo", "L'Accompagnement Travaux"),
    "services-plateo": ("accompagnement-travaux-plateo", "L'Accompagnement Travaux"),
    "contact-travail": ("contact", "Contact"),
    "blog-travail": ("media/", "Le média"),
    "blog/index": ("media/", "Le média"),  # /blog (dossier, car d'anciennes adresses /blog/... existent)
    "blog/depannage-reparation/deboucher-ses-canalisations-avec-des-produits-ecologiques": ("media/deboucher-ses-canalisations-avec-des-produits-ecologiques", "Déboucher ses canalisations avec des produits écologiques"),
    "contact-v2": ("contact", "Contact"),
    "untitled": ("mentions-legales", "Mentions légales"),
    "presentation": ("a-propos", "À propos"),
    "projects/index": ("projets", "Réalisations"),  # /projects (dossier des fiches) -> /projets
}


def page_404():
    """Page d'erreur servie par GitHub Pages ; liens absolus car elle s'affiche à n'importe quelle adresse."""
    return f'''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Page introuvable | Plateo</title>
  <meta name="robots" content="noindex">
  <link rel="icon" type="image/png" href="/assets/img/favicon.png">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
<main class="hero page-hero" style="min-height:100vh;display:flex;align-items:center">
  <div class="container page-hero-text">
    <a href="/"><img src="/assets/img/Plateo_logo_principale_dark.png" alt="Plateo." width="160" height="61" style="margin-bottom:40px"></a>
    <h1>Cette page est introuvable</h1>
    <p class="lead">Elle a peut-être été déplacée ou supprimée. Voici quelques pistes pour retrouver ce que vous cherchez :</p>
    <div class="btn-row">
      <a href="/" class="btn btn-primary">Retour à l'accueil</a>
      <a href="/les-specialites" class="btn btn-ghost">Nos spécialités</a>
      <a href="/media/" class="btn btn-ghost">Le média</a>
      <a href="/contact" class="btn btn-ghost">Nous contacter</a>
    </div>
  </div>
</main>
</body>
</html>
'''


def update_sitemap(urls):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        u, lastmod = u if isinstance(u, tuple) else (u, None)
        lm = f"\n    <lastmod>{lastmod}</lastmod>" if lastmod else ""
        lines.append(f"  <url>\n    <loc>{u}</loc>{lm}\n  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    d = json.loads((ROOT / "data" / "travaux.json").read_text(encoding="utf-8"))
    sync_index()
    sync_index_faq(faq_data())
    print("✓ index.html (menu, pied de page et FAQ synchronisés)")

    out = ROOT / f"{d['page']['slug']}.html"
    out.write_text(local_images(page_travaux(d), ""), encoding="utf-8")
    print(f"✓ {out.name}")

    (ROOT / "services").mkdir(exist_ok=True)
    for m in d["metiers"]:
        (ROOT / "services" / f"{m['slug']}.html").write_text(
            page_renvoi(f"{d['page']['slug']}#{m['slug']}", m["nom"]), encoding="utf-8")
    print(f"✓ services/ : {len(d['metiers'])} anciennes adresses renvoyées vers la page")

    ap = json.loads((ROOT / "data" / "a-propos.json").read_text(encoding="utf-8"))
    (ROOT / f"{ap['slug']}.html").write_text(local_images(page_apropos(ap), ""), encoding="utf-8")
    print(f"✓ {ap['slug']}.html")

    piliers = []
    for nom in ["accompagnement", "audit"]:
        pd = json.loads((ROOT / "data" / f"{nom}.json").read_text(encoding="utf-8"))
        (ROOT / f"{pd['slug']}.html").write_text(local_images(page_pilier(pd, d["pourquoi"]), ""), encoding="utf-8")
        piliers.append(SITE + pd["slug"])
        print(f"✓ {pd['slug']}.html")

    md = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    (ROOT / "media").mkdir(exist_ok=True)
    (ROOT / f"{md['page']['slug']}.html").unlink(missing_ok=True)
    (ROOT / "media" / "index.html").write_text(local_images(page_media(md), "../"), encoding="utf-8")
    print(f"✓ media/index.html ({sum(not a.get('masquer') for a in md['articles'])} articles listés)")

    (ROOT / "media").mkdir(exist_ok=True)
    n = 0
    for art in md["articles"]:
        if art.get("masquer") and art.get("renvoi"):  # doublon : renvoi vers l'article conservé
            (ROOT / "media" / f"{art['slug']}.html").write_text(page_renvoi(f"media/{art['renvoi']}", art["titre"]), encoding="utf-8")
            continue
        if (ROOT / "data" / "articles" / f"{art['slug']}.html").exists():
            (ROOT / "media" / f"{art['slug']}.html").write_text(local_images(page_article(art, md["articles"]), "../"), encoding="utf-8")
            n += 1
    print(f"✓ media/ : {n} articles")

    rs = json.loads((ROOT / "data" / "ressources.json").read_text(encoding="utf-8"))
    (ROOT / f"{rs['slug']}.html").write_text(local_images(page_ressources(rs), ""), encoding="utf-8")
    print(f"✓ {rs['slug']}.html")

    metiers = {m["slug"]: m for m in d["metiers"]}
    reals = json.loads((ROOT / "data" / "realisations.json").read_text(encoding="utf-8"))["realisations"]
    (ROOT / "projets.html").write_text(local_images(page_projets(reals, metiers), ""), encoding="utf-8")
    (ROOT / "projects").mkdir(exist_ok=True)
    for r in reals:
        (ROOT / "projects" / f"{r['slug']}.html").write_text(local_images(page_projet(r, reals, metiers), "../"), encoding="utf-8")
    print(f"✓ projets.html et projects/ : {len(reals)} réalisations")

    (ROOT / "contact.html").write_text(page_contact(rs["formulaire"]), encoding="utf-8")
    (ROOT / "mentions-legales.html").write_text(page_mentions(), encoding="utf-8")
    print("✓ contact.html, mentions-legales.html")

    for ancien, (cible, nom) in RENVOIS.items():
        f = ROOT / f"{ancien}.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(page_renvoi(cible, nom, "../" * ancien.count("/")), encoding="utf-8")
    (ROOT / "404.html").write_text(page_404(), encoding="utf-8")
    print(f"✓ {len(RENVOIS)} anciennes adresses Webflow renvoyées, 404.html")

    update_sitemap([SITE, SITE + d["page"]["slug"], *piliers, SITE + ap["slug"], SITE + rs["slug"], SITE + "contact", SITE + "mentions-legales", SITE + "projets", SITE + md["page"]["slug"] + "/"]
                   + [(f"{SITE}projects/{r['slug']}", r.get("date")) for r in reals if not r.get("masquer")]
                   + [(f"{SITE}media/{x['slug']}", x.get("maj") or x.get("date")) for x in md["articles"] if not x.get("masquer")])
    print("✓ sitemap.xml")


if __name__ == "__main__":
    main()
