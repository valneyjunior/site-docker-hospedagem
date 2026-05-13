/**
 * aceite.js — Aceite digital + checkout Asaas
 *
 * Fluxo:
 *   1. Usuário preenche form e aceita os termos
 *   2. POST /aceite/confirmar → salva aceite no DB, cria cliente Asaas
 *      → retorna { ok, protocolo, customerId, planName, value }
 *   3. Exibe seção de pagamento (Cartão / PIX / Boleto) no design Hostweb
 *   4. Frontend chama /api/pay/... com os dados do método escolhido
 */

document.addEventListener("DOMContentLoaded", function () {
  const form       = document.getElementById("aceite-form");
  const btnAceitar = document.getElementById("btn-aceitar");
  const formErro   = document.getElementById("form-erro");
  const sucessoBox = document.getElementById("sucesso-box");
  const protocDisp = document.getElementById("protocolo-display");

  if (!form) return;

  // ── Máscaras de input ──────────────────────────────────────────────────────
  document.getElementById("telefone")?.addEventListener("input", function (e) {
    let v = e.target.value.replace(/\D/g, "");
    if (v.length > 0) v = "(" + v;
    if (v.length > 3) v = v.slice(0, 3) + ") " + v.slice(3);
    if (v.length > 10) v = v.slice(0, 10) + "-" + v.slice(10, 14);
    e.target.value = v;
  });

  document.getElementById("cpf_cnpj")?.addEventListener("input", function (e) {
    let v = e.target.value.replace(/\D/g, "");
    if (v.length <= 11) {
      v = v.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    } else {
      v = v.replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
           .replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
    }
    e.target.value = v;
  });

  // ── Submit do aceite ───────────────────────────────────────────────────────
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const nome     = document.getElementById("nome")?.value.trim()     || "";
    const email    = document.getElementById("email")?.value.trim()    || "";
    const cpf_cnpj = document.getElementById("cpf_cnpj")?.value.trim() || "";
    const telefone = document.getElementById("telefone")?.value.trim() || "";
    const empresa  = document.getElementById("empresa")?.value.trim()  || "";
    const dominio  = document.getElementById("dominio")?.value.trim()  || "";
    const aceito   = document.getElementById("aceito")?.checked  || false;
    const lgpd     = document.getElementById("lgpd")?.checked    || false;

    const planIdHidden = document.getElementById("plan_id")?.value.trim() || "";
    const planoSelect  = document.getElementById("plano");
    const plan_id      = planIdHidden || (planoSelect?.value.trim() || "");

    if (!nome)                       { showErro("⚠️ Informe o nome completo."); return; }
    if (!email || !email.includes("@")) { showErro("⚠️ Informe um e-mail válido."); return; }
    if (!cpf_cnpj)                   { showErro("⚠️ Informe o CPF ou CNPJ."); return; }
    if (!telefone)                   { showErro("⚠️ Informe o telefone/WhatsApp."); return; }
    if (!dominio)                    { showErro("⚠️ Informe o domínio a hospedar."); return; }
    if (!plan_id)                    { showErro("⚠️ Selecione o plano a contratar."); return; }
    if (!aceito)                     { showErro("⚠️ Você precisa aceitar os Termos de Uso."); return; }
    if (!lgpd)                       { showErro("⚠️ Você precisa autorizar o tratamento de dados (LGPD)."); return; }

    btnAceitar.disabled    = true;
    btnAceitar.textContent = "Registrando aceite…";
    hideErro();

    try {
      const resp = await fetch("/aceite/confirmar", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ nome, email, cpf_cnpj, telefone, empresa, dominio, plan_id, aceito, lgpd }),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.erro || `Erro ${resp.status}`);

      // Salva contexto de pagamento
      window._asaas = {
        customerId: data.customerId,
        value:      data.value,
        planName:   data.planName,
        nome,
        email,
        cpf_cnpj,
        telefone,
        dominio,
      };

      // Exibe protocolo
      form.style.display = "none";
      if (protocDisp) protocDisp.textContent = data.protocolo;
      if (sucessoBox) sucessoBox.style.display = "block";

      // Atualiza e exibe seção de pagamento
      window._asaas.dominio = data.dominio || dominio;
      const valFmt = "R$ " + data.value.toFixed(2).replace(".", ",");
      document.getElementById("pag-plano-nome-disp").textContent = data.planName;
      document.getElementById("pag-valor-disp").textContent      = valFmt;
      document.getElementById("btn-pagar").textContent           = "Pagar " + valFmt;

      setTimeout(() => {
        const sec = document.getElementById("pagamento-section");
        sec.style.display = "block";
        sec.scrollIntoView({ behavior: "smooth" });
      }, 1200);

    } catch (err) {
      showErro("❌ " + err.message);
      btnAceitar.disabled    = false;
      btnAceitar.textContent = "Concordo e quero contratar";
    }
  });

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

// ── Seleção do método de pagamento ────────────────────────────────────────────
window._selectedMethod = "cartao";

function selPag(method, el) {
  window._selectedMethod = method;

  document.querySelectorAll(".pag-tab").forEach(t => t.classList.remove("active"));
  el.classList.add("active");

  document.querySelectorAll(".pag-metodo").forEach(f => f.style.display = "none");
  document.getElementById("pag-" + method).style.display = "block";

  const val    = window._asaas?.value || 0;
  const valFmt = "R$ " + val.toFixed(2).replace(".", ",");
  const labels = {
    cartao: "Pagar " + valFmt,
    pix:    "Gerar PIX — " + valFmt,
    boleto: "Gerar Boleto — " + valFmt,
  };
  document.getElementById("btn-pagar").textContent = labels[method];
  document.getElementById("pag-erro").style.display = "none";
}

// ── Processar pagamento ───────────────────────────────────────────────────────
async function processarPagamento() {
  const btn   = document.getElementById("btn-pagar");
  const errEl = document.getElementById("pag-erro");

  btn.disabled    = true;
  btn.textContent = "Processando…";
  errEl.style.display = "none";

  try {
    let result;
    if (window._selectedMethod === "cartao") result = await _pagarCartao();
    else if (window._selectedMethod === "pix") result = await _pagarPix();
    else result = await _pagarBoleto();

    if (result.success) {
      _mostrarResultado(result);
    } else {
      const msg = result.error?.errors?.[0]?.description
               || result.error?.description
               || "Erro ao processar pagamento.";
      errEl.textContent   = "❌ " + msg;
      errEl.style.display = "block";
      _resetBtnPagar();
    }
  } catch (e) {
    errEl.textContent   = "❌ Erro de conexão. Tente novamente.";
    errEl.style.display = "block";
    _resetBtnPagar();
  }
}

function _resetBtnPagar() {
  const btn    = document.getElementById("btn-pagar");
  const val    = window._asaas?.value || 0;
  const valFmt = "R$ " + val.toFixed(2).replace(".", ",");
  const labels = { cartao: "Pagar " + valFmt, pix: "Gerar PIX — " + valFmt, boleto: "Gerar Boleto — " + valFmt };
  btn.disabled    = false;
  btn.textContent = labels[window._selectedMethod];
}

// ── Cartão ────────────────────────────────────────────────────────────────────
async function _pagarCartao() {
  const a = window._asaas;
  const raw = document.getElementById("cardNumber").value.replace(/\s/g, "");
  const exp = document.getElementById("cardExpiry").value.split("/");

  const resp = await fetch("/api/pay/credit-card", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customerId:  a.customerId,
      value:       a.value,
      description: a.planName,
      card: {
        holderName:  document.getElementById("cardHolder").value,
        number:      raw,
        expiryMonth: exp[0],
        expiryYear:  "20" + (exp[1] || ""),
        ccv:         document.getElementById("cardCvv").value,
      },
      holder: {
        name:          a.nome,
        email:         a.email,
        cpfCnpj:       a.cpf_cnpj.replace(/\D/g, ""),
        postalCode:    document.getElementById("holderCep").value.replace(/\D/g, ""),
        addressNumber: document.getElementById("holderNum").value,
        phone:         a.telefone.replace(/\D/g, ""),
      },
    }),
  });
  return resp.json();
}

// ── PIX ───────────────────────────────────────────────────────────────────────
async function _pagarPix() {
  const a = window._asaas;
  const resp = await fetch("/api/pay/pix", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customerId: a.customerId, value: a.value, description: a.planName }),
  });
  return resp.json();
}

// ── Boleto ────────────────────────────────────────────────────────────────────
async function _pagarBoleto() {
  const a = window._asaas;
  const resp = await fetch("/api/pay/boleto", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customerId: a.customerId, value: a.value, description: a.planName }),
  });
  return resp.json();
}

// ── Exibir resultado ──────────────────────────────────────────────────────────
function _mostrarResultado(data) {
  document.getElementById("pag-form-content").style.display = "none";
  const res = document.getElementById("pag-resultado");
  res.style.display = "block";

  if (window._selectedMethod === "cartao") {
    res.innerHTML = `
      <div class="pag-resultado-inner">
        <div class="pag-resultado-icon">✅</div>
        <h3>Pagamento aprovado!</h3>
        <p>Seu plano <strong>${window._asaas.planName}</strong> já está ativo.</p>
        <p>Você receberá os dados de acesso por e-mail em breve.</p>
        <span class="pag-badge pag-badge-ok">CONFIRMADO</span>
        <a href="/" class="pag-btn-voltar">Voltar ao início</a>
      </div>`;

  } else if (window._selectedMethod === "pix") {
    const qrHtml = data.pixQrCode
      ? `<div class="pag-qr-box"><img src="data:image/png;base64,${data.pixQrCode}" alt="QR Code PIX"></div>`
      : "";
    const copyHtml = data.pixCopyPaste
      ? `<p class="pag-copy-label">Ou copie o código PIX:</p>
         <div class="pag-copy-paste" onclick="copiarPix(this)">${data.pixCopyPaste}</div>`
      : "";

    res.innerHTML = `
      <div class="pag-resultado-inner pag-resultado-pix">
        <div class="pag-resultado-icon">⚡</div>
        <h3>PIX gerado!</h3>
        <p>Escaneie o QR Code ou copie o código abaixo</p>
        <span class="pag-badge pag-badge-pending">AGUARDANDO PAGAMENTO</span>
        ${qrHtml}
        ${copyHtml}
        <p class="pag-info-small">O plano será ativado automaticamente após a confirmação do PIX.</p>
      </div>`;

    if (data.paymentId) _iniciarPolling(data.paymentId);

  } else {
    const url = data.bankSlipUrl || data.invoiceUrl || "#";
    res.innerHTML = `
      <div class="pag-resultado-inner">
        <div class="pag-resultado-icon">📄</div>
        <h3>Boleto gerado!</h3>
        <p>Clique abaixo para visualizar e pagar o boleto.</p>
        <span class="pag-badge pag-badge-pending">AGUARDANDO PAGAMENTO</span>
        <a href="${url}" target="_blank" class="pag-btn-boleto">Abrir Boleto</a>
        <p class="pag-info-small">Vencimento em 3 dias úteis. O plano é ativado após a compensação bancária.</p>
      </div>`;
  }

  res.scrollIntoView({ behavior: "smooth" });
}

// ── Polling PIX ───────────────────────────────────────────────────────────────
function _iniciarPolling(paymentId) {
  let tentativas = 0;
  const max = 60;
  const intervalo = setInterval(async () => {
    if (++tentativas > max) { clearInterval(intervalo); return; }
    try {
      const r = await fetch(`/api/payments/${paymentId}/status`);
      const d = await r.json();
      if (d.status === "RECEIVED" || d.status === "CONFIRMED") {
        clearInterval(intervalo);
        document.getElementById("pag-resultado").innerHTML = `
          <div class="pag-resultado-inner">
            <div class="pag-resultado-icon">✅</div>
            <h3>PIX confirmado!</h3>
            <p>Seu plano <strong>${window._asaas.planName}</strong> já está ativo.</p>
            <span class="pag-badge pag-badge-ok">CONFIRMADO</span>
            <a href="/" class="pag-btn-voltar">Voltar ao início</a>
          </div>`;
      }
    } catch (_) {}
  }, 5000);
}

// ── Copiar código PIX ─────────────────────────────────────────────────────────
function copiarPix(el) {
  navigator.clipboard.writeText(el.textContent).then(() => {
    const orig = el.textContent;
    el.textContent  = "✓ Copiado!";
    el.style.color  = "var(--purple)";
    setTimeout(() => { el.textContent = orig; el.style.color = ""; }, 2000);
  });
}

// ── Máscara cartão (adicionada dinamicamente) ─────────────────────────────────
document.addEventListener("input", function (e) {
  if (e.target.id === "cardNumber") {
    let v = e.target.value.replace(/\D/g, "");
    v = v.replace(/(\d{4})(?=\d)/g, "$1 ");
    e.target.value = v.slice(0, 19);
  }
  if (e.target.id === "cardExpiry") {
    let v = e.target.value.replace(/\D/g, "");
    if (v.length >= 2) v = v.slice(0, 2) + "/" + v.slice(2);
    e.target.value = v.slice(0, 5);
  }
  if (e.target.id === "holderCep") {
    let v = e.target.value.replace(/\D/g, "");
    if (v.length > 5) v = v.slice(0, 5) + "-" + v.slice(5);
    e.target.value = v.slice(0, 9);
  }
});
