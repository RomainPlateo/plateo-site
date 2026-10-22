/*
  Récupère les 13 illustrations de la section « Ils parlent de nous » du site Webflow.

  Mode d'emploi :
  1. Ouvre https://www.plateo.fr dans Chrome.
  2. Appuie sur F12 (ou clic droit > Inspecter), onglet « Console ».
  3. Colle tout ce fichier et appuie sur Entrée. Si Chrome demande d'autoriser
     plusieurs téléchargements, accepte.
  4. Range les 13 fichiers téléchargés dans le dossier assets/img/presse/ du site.
*/
(async () => {
  const noms = [
    'au-secours-mes-parents-vieillissent', 'bfm-marseille', 'b-smart', 'la-provence-1',
    'tpbm-mesinfos', 'initiatives', 'storm-media', 'la-provence-2', 'le-meridional',
    'les-nouvelles-publications', 'demain-en-solutions', 'france-bleu-provence', 'soyez-audacieux'
  ];
  const heading = [...document.querySelectorAll('h2')].find(h => /parlent de nous/i.test(h.textContent));
  const section = heading && (heading.closest('section') || heading.parentElement.parentElement);
  const imgs = section ? [...section.querySelectorAll('a img')] : [];
  console.log(imgs.length + ' illustrations trouvées');
  for (let i = 0; i < imgs.length && i < noms.length; i++) {
    const url = imgs[i].currentSrc || imgs[i].src;
    console.log(noms[i] + '.jpg  <-  ' + url);
    try {
      const blob = await (await fetch(url)).blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = noms[i] + '.jpg';
      a.click();
      await new Promise(r => setTimeout(r, 400));
    } catch (e) {
      console.warn('Téléchargement impossible pour ' + noms[i] + ' : ouvre le lien ci-dessus et enregistre l’image.');
    }
  }
})();
