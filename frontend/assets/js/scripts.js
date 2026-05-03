// Com nginx como proxy reverso, todas as rotas Flask são relativas ao mesmo domínio.
const ACEITE_BASE = "";

/* ── TABS ──────────────────────────────────────────────────────────── */
function switchTab(tab, btn) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + tab).classList.add("active");
  btn.classList.add("active");
}

/* ── BILLING TOGGLE ────────────────────────────────────────────────── */
var isAnual = false;
var prices = { starter:["39","33"], business:["69","59"], bplus:["99","84"], enterprise:["149","127"] };
var cents  = { starter:[",90",",92"], business:[",90",",42"], bplus:[",90",",92"], enterprise:[",90",",42"] };

function toggleBilling() {
  isAnual = !isAnual;
  const sw = document.getElementById("toggle-billing");
  const lm = document.getElementById("lbl-mensal");
  const la = document.getElementById("lbl-anual");
  if (isAnual) { sw.classList.add("on"); lm.classList.remove("active"); la.classList.add("active"); }
  else         { sw.classList.remove("on"); lm.classList.add("active"); la.classList.remove("active"); }
  const idx = isAnual ? 1 : 0;
  ["starter","business","bplus","enterprise"].forEach(k => {
    const el = document.getElementById("p-" + k); if (el) el.textContent = prices[k][idx];
    const ce = document.getElementById("c-" + k); if (ce) ce.textContent = cents[k][idx];
  });
}

/* ── CHECKOUT (redireciona direto para o aceite digital) ───────────── */
function openModal(plan) {
  const shared = ["Starter", "Business", "Business Plus", "Enterprise"];
  const fixed  = {
    "Dedicado Essencial":    "ded_essencial_mensal",
    "Dedicado Profissional": "ded_profissional_mensal",
    "Dedicado Enterprise":   "ded_enterprise_mensal",
    "Mail Lite 5GB":         "zoho_mail_lite_5_mensal",
    "Mail Lite 10GB":        "zoho_mail_lite_10_mensal",
    "Mail Premium":          "zoho_mail_premium_mensal",
    "Workplace Padrão":      "zoho_workplace_std_mensal",
    "Workplace Profissional":"zoho_workplace_pro_mensal",
  };

  let plan_id;
  if (shared.includes(plan)) {
    plan_id = plan.toLowerCase().replace(/\s+/g, "_") + (isAnual ? "_anual" : "_mensal");
  } else {
    plan_id = fixed[plan];
  }

  if (!plan_id) {
    const msg = encodeURIComponent("Olá! Tenho interesse no plano " + plan + ". Podem me ajudar?");
    window.open("https://wa.me/5585991293286?text=" + msg, "_blank");
    return;
  }

  window.location.href = ACEITE_BASE + "/aceite/?plan_id=" + plan_id;
}

/* ── SMOOTH SCROLL ─────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", function(e) {
      const t = document.querySelector(this.getAttribute("href"));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: "smooth" }); }
    });
  });
});
