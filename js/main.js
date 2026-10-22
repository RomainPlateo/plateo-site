/* Plateo — scripts du site (sans dépendance) */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Menu mobile ---------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('main-nav');
  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
      nav.classList.toggle('is-open', open);
    };
    toggle.addEventListener('click', function () {
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1080) setOpen(false);
    });
  }

  /* ---------- Hero : le titre apparaît mot par mot ---------- */
  document.querySelectorAll('[data-split]').forEach(function (title) {
    var i = 0, step = 70;
    (function split(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (child) {
        if (child.nodeType === 3) {
          var frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach(function (part) {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            var w = document.createElement('span');
            w.className = 'word';
            w.style.animationDelay = (0.15 + i++ * step / 1000) + 's';
            w.textContent = part;
            frag.appendChild(w);
          });
          node.replaceChild(frag, child);
        } else if (child.nodeType === 1) {
          split(child);
        }
      });
    })(title);
    var hero = title.closest('.hero');
    if (hero) hero.style.setProperty('--after-title', (0.25 + i * step / 1000) + 's');
  });

  /* ---------- Presse : l'illustration s'affiche seulement si le fichier existe ---------- */
  document.querySelectorAll('.press-media img').forEach(function (img) {
    img.loading = 'eager';
    var show = function () { if (img.naturalWidth > 0) img.closest('.press-card').classList.add('has-img'); };
    if (img.complete) show();
    img.addEventListener('load', show);
  });

  /* ---------- Ombre de l'en-tête au défilement ---------- */
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 8); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- Bandeau presse : duplication pour un défilement continu ---------- */
  document.querySelectorAll('.marquee-track').forEach(function (track) {
    if (reduceMotion) return;
    Array.prototype.slice.call(track.children).forEach(function (item) {
      var clone = item.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      clone.querySelectorAll('a').forEach(function (a) { a.tabIndex = -1; });
      track.appendChild(clone);
    });
  });

  /* ---------- Compteurs animés ---------- */
  function animateCount(el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target) || reduceMotion) return;
    var duration = 1400, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString('fr-FR');
      if (p < 1) requestAnimationFrame(step);
    }
    el.textContent = '0';
    requestAnimationFrame(step);
  }

  /* ---------- Apparition au défilement ---------- */
  var revealEls = document.querySelectorAll('.reveal');
  var counters = document.querySelectorAll('[data-count]');

  if ('IntersectionObserver' in window) {
    var revealObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          revealObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(function (el, i) {
      el.style.transitionDelay = (i % 4) * 70 + 'ms';
      revealObs.observe(el);
    });

    var countObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          countObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { countObs.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('is-visible'); });
  }

  /* ---------- Média : filtres par catégorie et recherche ---------- */
  document.querySelectorAll('[data-filter-list]').forEach(function (zone) {
    var chips = zone.querySelectorAll('[data-filter]');
    var input = zone.querySelector('[data-search-input]');
    var cards = zone.querySelectorAll('[data-cat]');
    var label = zone.querySelector('[data-count-label]');
    var empty = zone.querySelector('[data-empty]');
    var cat = '';
    var norm = function (s) {
      return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-');
    };
    var apply = function () {
      var words = norm(input ? input.value : '').split('-').filter(Boolean);
      var n = 0;
      cards.forEach(function (c) {
        var hay = c.getAttribute('data-search');
        var ok = (!cat || c.getAttribute('data-cat') === cat) &&
                 words.every(function (w) { return hay.indexOf(w) !== -1; });
        c.hidden = !ok;
        if (ok) n++;
      });
      var unit = (label && label.getAttribute('data-unit')) || 'article';
      if (label) label.textContent = n + ' ' + unit + (n > 1 ? 's' : '');
      if (empty) empty.hidden = n !== 0;
    };
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        cat = chip.getAttribute('data-filter');
        chips.forEach(function (c) {
          var on = c === chip;
          c.classList.toggle('is-active', on);
          c.setAttribute('aria-pressed', String(on));
        });
        apply();
      });
    });
    if (input) input.addEventListener('input', apply);
  });

  /* ---------- Ressources : choix du livre blanc et envoi du formulaire ---------- */
  document.querySelectorAll('[data-choose-book]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var box = document.querySelector('[data-book="' + btn.getAttribute('data-choose-book') + '"]');
      if (box) box.checked = true;
    });
  });

  document.querySelectorAll('[data-lead-form]').forEach(function (form) {
    var status = form.querySelector('.form-status');
    var books = form.querySelectorAll('input[name="livres_blancs"]');
    // Champ « Nom de votre association » : visible et obligatoire seulement pour une association tutélaire
    form.querySelectorAll('[data-show-if]').forEach(function (field) {
      var input = field.querySelector('input');
      var radios = form.querySelectorAll('input[name="structure"]');
      var sync = function () {
        var on = Array.prototype.some.call(radios, function (r) {
          return r.checked && r.value === field.getAttribute('data-show-if');
        });
        field.hidden = !on;
        input.required = on;
        if (!on) input.value = '';
      };
      radios.forEach(function (r) {
        r.addEventListener('change', function () {
          sync();
          if (!field.hidden) input.focus();
        });
      });
      sync();
    });

    var show = function (msg, ok) {
      status.hidden = false;
      status.textContent = msg;
      status.className = 'form-status ' + (ok ? 'is-ok' : 'is-error');
    };
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var chosen = Array.prototype.filter.call(books, function (b) { return b.checked; });
      if (books.length && !chosen.length) {
        show('Choisissez au moins un livre blanc.', false);
        books[0].focus();
        return;
      }
      var data = new FormData(form);
      data.set('livres_blancs', chosen.map(function (b) { return b.value; }).join(' | '));
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      fetch(form.action, { method: 'POST', body: data, headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json().then(function (j) { return r.ok && j.success !== false; }); })
        .then(function (ok) {
          if (ok) {
            form.querySelectorAll('fieldset, .form-row, .consent, button').forEach(function (el) { el.hidden = true; });
            show(form.getAttribute('data-success'), true);
          } else {
            show(form.getAttribute('data-error'), false);
          }
        })
        .catch(function () { show(form.getAttribute('data-error'), false); })
        .then(function () { btn.disabled = false; });
    });
  });

  /* ---------- Année du copyright ---------- */
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });
})();
