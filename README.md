# Site Plateo — version code (HTML / CSS / JS)

Reconstruction de www.plateo.fr (Webflow) en code pur, sans framework ni dépendance,
aux couleurs de la charte Plateo (Dark blue, Optimistic blue, police Outfit).

## Contenu

```
plateo-site/
├── index.html                    Accueil (écrit à la main ; menu, pied de page et FAQ synchronisés)
├── les-specialites.html          Les Spécialités (6 corps d'état)        ┐
├── accompagnement-travaux-plateo.html, audit-securite-salubrite.html     │
├── a-propos.html, ressources.html, contact.html, mentions-legales.html   │ générés par
├── media/index.html + media/*.html   Le média et les 82 articles         │ scripts/build.py
├── projets.html + projects/*.html    Réalisations et 34 fiches           │
├── services/*.html               Renvois des anciennes pages services    ┘
├── templates/                    Menu et pied de page communs
├── data/                         Tous les textes (JSON / HTML)
├── css/style.css, js/main.js     Styles et scripts
├── assets/                       Images, logos, police Outfit
├── scripts/                      build.py, importer-articles.py, importer-realisations.py, rapatrier-images.py
└── sitemap.xml, robots.txt, llms.txt
```

## Voir le site en local

Les liens internes utilisent les mêmes adresses que le site actuel, sans « .html »
(ex. `/a-propos`, `/services/depannages`) pour ne rien perdre en référencement.
GitHub Pages sait les servir. En local, utilise un serveur qui les gère aussi :

```
cd plateo-site
npx serve
```
puis ouvre l'adresse indiquée (http://localhost:3000).

## Règle de nommage des futures pages

Chaque page garde l'adresse qu'elle a sur Webflow :
`a-propos.html`, `accompagnement-travaux-plateo.html`, `audit-securite-salubrite.html`,
`media/<nom-de-l-article>.html`, `projects/<nom>.html`…
Penser à ajouter chaque nouvelle page dans `sitemap.xml`.

## SEO déjà en place

- Titre, description et aperçus de partage (image `assets/img/og-plateo.jpg`)
- Données structurées schema.org (entreprise, services, réseaux sociaux)
- `robots.txt`, `sitemap.xml` et `llms.txt` (présentation du site pour les IA)
- Police Outfit hébergée sur le site (aucun appel à Google : plus rapide et conforme RGPD)
- Images en WebP allégées, dimensions déclarées

## Générer les pages

```
python3 scripts/build.py
```

- `templates/header.html` et `templates/footer.html` : menu et pied de page, communs
  à tout le site (accueil compris). Une modification ici s'applique partout.
- `data/travaux.json` : textes de la page « Les Spécialités » (`les-specialites.html`),
  une section par corps d'état.
- Les 6 anciennes adresses `/services/<métier>` sont des pages de renvoi
  vers `/les-specialites#<métier>` (générées automatiquement).
- `data/a-propos.json` : textes de la page « À propos » (`a-propos.html`).
- `data/faq.json` : FAQ commune à l'accueil et à « Les Spécialités ».
- Le script met aussi à jour `sitemap.xml`.

Ordre à respecter : `build.py`, puis `rapatrier-images.py`.

## Articles du média

Les 82 articles viennent de l'export CSV de la collection Webflow :

```
python3 scripts/importer-articles.py export.csv
python3 scripts/build.py
python3 scripts/rapatrier-images.py
```

- `data/articles.json` : titre, catégorie, date, résumé, image, auteur de chaque article.
  `"masquer": true` retire un article de la liste ; avec `"renvoi": "<slug>"`, son adresse
  renvoie vers un autre article.
- `data/articles/<slug>.html` : texte de l'article (modifiable directement).
- Pour un nouvel article : ajouter une entrée dans `articles.json` et son fichier texte.

## Formulaire des livres blancs (page Ressources)

Le formulaire envoie les demandes par mail via Web3Forms (gratuit, 250 demandes/mois) :
1. Sur https://web3forms.com, saisir l'adresse qui doit recevoir les demandes.
2. Copier la clé reçue par mail dans `data/ressources.json` (champ `"cle"`).
3. Lancer `python3 scripts/build.py`.

Cette clé n'est pas secrète : elle est faite pour être visible dans la page.

## Avant de résilier Webflow

Les illustrations, photos d'équipe et logos partenaires pointent encore vers le CDN
Webflow. Lance une fois :

```
python3 scripts/rapatrier-images.py
```
Le script télécharge tout dans `assets/img/webflow/` et met les liens à jour.

## Illustrations « Ils parlent de nous »

Les cartes presse affichent une illustration si le fichier existe dans
`assets/img/presse/` (ex. `bfm-marseille.jpg`), sinon une carte texte.
Pour récupérer les 13 illustrations du site Webflow : voir le mode d'emploi
en haut de `scripts/recuperer-presse.js`.

## Mettre en ligne

Le dossier est 100 % statique : il se dépose tel quel sur GitHub Pages, Netlify,
Vercel, OVH, o2switch… (aucune compilation).

## Pages restant à créer

Les liens internes sont déjà en place et pointent vers :
`a-propos.html`, `accompagnement-travaux.html`, `audit-securite-salubrite.html`,
`projets.html`, `media.html`, `ressources.html`, `contact.html`, `mentions-legales.html`,
`services/*.html` (6 pages) et `media/*.html` (articles).

Les formulaires restent sur Tally (https://tally.so/r/3y695p).

## Points d'attention

- Les URL changent (ex. `/a-propos` → `/a-propos.html`). Pour garder le référencement,
  prévoir des redirections 301 chez l'hébergeur, ou passer en dossiers
  (`a-propos/index.html`) pour conserver les URL actuelles.
