const ACEITE_BASE = "";

var hostingPeriod = 'mensal';
var emailPeriod   = 'mensal';

const PERIOD_MULT  = { mensal: 1.0, '12m': 0.95, '24m': 0.90 };
const PERIOD_BADGE = { mensal: '',   '12m': '-5%', '24m': '-10%' };

/* ── CUSTOM SELECTS ─────────────────────────────────────────────────── */
function initCustomSelects() {
  document.querySelectorAll('.hw-select').forEach(sel => {
    sel.querySelector('.hw-select-btn').addEventListener('click', e => {
      e.stopPropagation();
      const wasOpen = sel.classList.contains('open');
      closeAllSelects();
      if (!wasOpen) sel.classList.add('open');
    });
    sel.querySelectorAll('.hw-select-item').forEach(item => {
      item.addEventListener('click', () => {
        sel.querySelectorAll('.hw-select-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        sel.querySelector('.hw-select-val').textContent =
          item.dataset.label || item.childNodes[0].textContent.trim();
        sel.classList.remove('open');
        handleSelect(sel.id, item.dataset.value);
      });
    });
  });
  document.addEventListener('click', closeAllSelects);
}

function closeAllSelects() {
  document.querySelectorAll('.hw-select.open').forEach(s => s.classList.remove('open'));
}

function handleSelect(id, val) {
  if (id === 'sel-hosting-period') {
    hostingPeriod = val;
    applyPeriod('hosting', val);

  } else if (id === 'sel-email-type') {
    toggleGroup('pg-zoho', 'pg-cpanel', val === 'zoho');
    const ps = document.getElementById('sel-email-period');
    if (ps) ps.style.display = val === 'zoho' ? '' : 'none';

  } else if (id === 'sel-email-period') {
    emailPeriod = val;
    applyPeriod('email', val);

  } else if (id === 'sel-domain-cat') {
    filterDomains(val);
  }
}

/* ── PRICE UPDATE ───────────────────────────────────────────────────── */
function applyPeriod(section, period) {
  const mult       = PERIOD_MULT[period]  || 1.0;
  const badge      = PERIOD_BADGE[period] || '';
  const discounted = period !== 'mensal';

  document.querySelectorAll(`[data-section="${section}"][data-base]`).forEach(card => {
    const base = parseFloat(card.dataset.base);
    if (isNaN(base)) return;

    const price = (base * mult).toFixed(2);
    const [whole, dec] = price.split('.');

    const amountEl = card.querySelector('.hw-amount');
    const centsEl  = card.querySelector('.hw-cents');
    if (amountEl) amountEl.textContent = whole;
    if (centsEl)  centsEl.textContent  = ',' + dec;

    const origEl = card.querySelector('.hw-plan-orig');
    if (origEl) {
      origEl.textContent    = 'R$ ' + base.toFixed(2).replace('.', ',') + '/mês';
      origEl.style.visibility = discounted ? 'visible' : 'hidden';
    }

    const badgeEl = card.querySelector('.hw-disc-badge');
    if (badgeEl) {
      badgeEl.textContent  = badge;
      badgeEl.style.display = discounted ? 'flex' : 'none';
    }
  });
}

function toggleGroup(idA, idB, showA) {
  const a = document.getElementById(idA);
  const b = document.getElementById(idB);
  if (a) a.classList.toggle('active', showA);
  if (b) b.classList.toggle('active', !showA);
}

/* ── DOMAIN FILTER ──────────────────────────────────────────────────── */
function filterDomains(cat) {
  document.querySelectorAll('.domain-row').forEach(row => {
    const cats = (row.dataset.cats || '').split(',');
    row.style.display = (cat === 'all' || cats.includes(cat)) ? '' : 'none';
  });
}

/* ── CHECKOUT ───────────────────────────────────────────────────────── */
function openModal(plan, section) {
  const period = section === 'email' ? emailPeriod : hostingPeriod;

  const zohoMap = {
    "Mail Lite 5GB":         "zoho_mail_lite_5_mensal",
    "Mail Lite 10GB":        "zoho_mail_lite_10_mensal",
    "Mail Premium":          "zoho_mail_premium_mensal",
    "Workplace Padrão":      "zoho_workplace_std_mensal",
    "Workplace Profissional":"zoho_workplace_pro_mensal",
  };
  const dedMap = {
    "Dedicado Essencial":    "ded_essencial_mensal",
    "Dedicado Profissional": "ded_profissional_mensal",
    "Dedicado Enterprise":   "ded_enterprise_mensal",
  };
  const shared = ["Starter","Business","Business Plus","Enterprise"];

  let plan_id;

  if (shared.includes(plan)) {
    if (period === '24m') {
      window.open("https://wa.me/5585991293286?text=" +
        encodeURIComponent("Olá! Quero contratar o plano " + plan + " por 24 meses. Podem me ajudar?"), "_blank");
      return;
    }
    plan_id = plan.toLowerCase().replace(/\s+/g, "_") + (period === '12m' ? '_anual' : '_mensal');
  } else if (zohoMap[plan]) {
    plan_id = zohoMap[plan];
  } else if (dedMap[plan]) {
    plan_id = dedMap[plan];
  } else {
    window.open("https://wa.me/5585991293286?text=" +
      encodeURIComponent("Olá! Interesse no plano " + plan + ". Podem me ajudar?"), "_blank");
    return;
  }

  window.location.href = ACEITE_BASE + "/aceite/?plan_id=" + plan_id;
}

/* ── INIT ───────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initCustomSelects();
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", function(e) {
      const t = document.querySelector(this.getAttribute("href"));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: "smooth" }); }
    });
  });
});
