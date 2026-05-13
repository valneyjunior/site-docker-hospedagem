/**
 * aceite.js — Lógica do aceite digital Hostweb
 *
 * Fluxo:
 *   1. Usuário preenche o formulário e marca os dois checkboxes obrigatórios
 *   2. POST /aceite/confirmar → backend registra aceite (CSV + JSON) e cria sessão Stripe
 *   3. Backend retorna { ok, protocolo, url }
 *   4. Frontend exibe protocolo por 2 segundos e redireciona para Stripe
 */

document.addEventListener("DOMContentLoaded", function () {
  const form         = document.getElementById("aceite-form");
  const btnAceitar   = document.getElementById("btn-aceitar");
  const formErro     = document.getElementById("form-erro");
  const sucessoBox   = document.getElementById("sucesso-box");
  const protocDisp   = document.getElementById("protocolo-display");

  if (!form) return;

  // ── Scroll indicator ────────────────────────────────────────────────────
  const termoScroll = document.getElementById("termo-scroll");
  const indicator   = document.getElementById("scroll-indicator");
  if (termoScroll && indicator) {
    termoScroll.addEventListener("scroll", function () {
      const atBottom =
        termoScroll.scrollTop + termoScroll.clientHeight >= termoScroll.scrollHeight - 50;
      indicator.style.opacity = atBottom ? "0" : "1";
    });
  }

  // ── Submissão do formulário ──────────────────────────────────────────────
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const nome     = document.getElementById("nome")?.value.trim()     || "";
    const email    = document.getElementById("email")?.value.trim()    || "";
    const cpf_cnpj = document.getElementById("cpf_cnpj")?.value.trim() || "";
    const empresa  = document.getElementById("empresa")?.value.trim()  || "";
    const domain   = document.getElementById("domain")?.value.trim().toLowerCase() || "";
    const aceito   = document.getElementById("aceito")?.checked  || false;
    const lgpd     = document.getElementById("lgpd")?.checked    || false;

    // plan_id: vem do campo oculto (pré-preenchido pela URL) ou do select
    const planIdHidden = document.getElementById("plan_id")?.value.trim() || "";
    const planoSelect  = document.getElementById("plano");
    const plan_id      = planIdHidden || (planoSelect?.value.trim() || "");

    // Planos que exigem domínio
    const planosComDominio = new Set([
      "sites_basico_mensal", "sites_plus_mensal", "sites_pro_mensal",
      "ded_essencial_mensal", "ded_profissional_mensal", "ded_enterprise_mensal",
    ]);
    const dominioRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$/;

    // Validação client-side
    if (!nome) { showErro("⚠️ Informe o nome completo."); return; }
    if (!email || !email.includes("@")) { showErro("⚠️ Informe um e-mail válido."); return; }
    if (!cpf_cnpj) { showErro("⚠️ Informe o CPF ou CNPJ."); return; }
    if (!plan_id) { showErro("⚠️ Selecione o plano a contratar."); return; }
    if (planosComDominio.has(plan_id) && !domain) {
      showErro("⚠️ Informe o domínio para o plano de hospedagem."); return;
    }
    if (domain && !dominioRegex.test(domain)) {
      showErro("⚠️ Formato de domínio inválido. Ex: meusite.com.br"); return;
    }
    if (!aceito) { showErro("⚠️ Você precisa ler e aceitar os Termos de Uso."); return; }
    if (!lgpd) { showErro("⚠️ Você precisa autorizar o tratamento de dados (LGPD)."); return; }

    // UI: loading
    btnAceitar.disabled    = true;
    btnAceitar.textContent = "Registrando aceite…";
    hideErro();

    try {
      const resp = await fetch("/aceite/confirmar", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ nome, email, cpf_cnpj, empresa, domain, plan_id, aceito, lgpd }),
      });

      const data = await resp.json();

      if (!resp.ok) throw new Error(data.erro || `Erro ${resp.status}`);

      // ── Aceite registrado — exibe protocolo e redireciona ──────────────
      form.style.display = "none";
      if (protocDisp) protocDisp.textContent = data.protocolo;
      if (sucessoBox) sucessoBox.style.display = "block";

      // Redireciona para Stripe após 2 segundos
      setTimeout(() => { window.location.href = data.url; }, 2000);

    } catch (err) {
      showErro("❌ " + err.message);
      btnAceitar.disabled    = false;
      btnAceitar.textContent = "Concordo e quero contratar";
    }
  });

  // ── Helpers ──────────────────────────────────────────────────────────────
  function showErro(msg) {
    if (!formErro) return;
    formErro.textContent   = msg;
    formErro.style.display = "block";
    formErro.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideErro() {
    if (!formErro) return;
    formErro.style.display = "none";
  }
});
