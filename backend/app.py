from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests as _http
import os

from utils import PLANS, graph_send_email, EMAIL_FROM, EMAIL_REPLY

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

ASAAS_API_KEY  = os.getenv("ASAAS_API_KEY", "")
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://sandbox.asaas.com/api")

_asaas_verify = "sandbox" not in ASAAS_BASE_URL
_asaas_http   = _http.Session()
_asaas_http.verify = _asaas_verify
if not _asaas_verify:
    import urllib3; urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _asaas_headers():
    return {"Content-Type": "application/json", "access_token": ASAAS_API_KEY}


from blueprints.aceite import aceite_bp
from blueprints.pages import pages_bp
app.register_blueprint(aceite_bp)
app.register_blueprint(pages_bp)


def enviar_email_boas_vindas(email_cliente, nome, plano):
    html = (
        "<html><body style='font-family:Segoe UI,sans-serif;background:#f5f5f7;padding:32px'>"
        "<div style='max-width:560px;margin:0 auto;background:#fff;border-radius:16px;"
        "box-shadow:0 4px 24px rgba(0,0,0,.08)'>"
        "<div style='background:linear-gradient(135deg,#e8001c,#6b0fa8);padding:32px;text-align:center;border-radius:16px 16px 0 0'>"
        "<h1 style='color:#fff;margin:0 0 4px;font-size:1.5rem;font-weight:800'>Hostweb</h1>"
        "<p style='color:rgba(255,255,255,.8);margin:0;font-size:.9rem'>Pagamento Confirmado!</p>"
        "</div>"
        "<div style='padding:32px'>"
        f"<p style='color:#333'>Olá, <strong>{nome}</strong>!</p>"
        f"<p style='color:#555;line-height:1.7'>Seu plano <strong style='color:#e8001c'>"
        f"{plano}</strong> já está ativo. Em breve você receberá as credenciais de acesso.</p>"
        "<div style='background:#fff5f5;border-radius:10px;padding:20px;margin:20px 0;"
        "border-left:4px solid #e8001c'>"
        "<p style='margin:0;font-size:.85rem;color:#444'><strong>Próximos passos:</strong><br><br>"
        "1. Verifique seu e-mail com as credenciais de acesso ao painel.<br>"
        "2. Suporte: <a href='https://hostweb.com.br/suporte' style='color:#e8001c'>hostweb.com.br/suporte</a><br>"
        "3. WhatsApp: <a href='https://wa.me/5585991293286' style='color:#e8001c'>+55 85 99129-3286</a><br>"
        "4. Atendimento: segunda a sexta, das 8h às 18h</p>"
        "</div>"
        "<p style='color:#999;font-size:.78rem;text-align:center'>"
        "Hostweb Data Center e Serviços LTDA EPP — CNPJ 07.797.967/0001-60 — Fortaleza, CE</p>"
        "</div></div></body></html>"
    )
    try:
        graph_send_email(
            to        = email_cliente,
            subject   = f"Bem-vindo à Hostweb! Seu plano {plano} está ativo",
            html_body = html,
            reply_to  = EMAIL_REPLY,
        )
        print(f"E-mail boas-vindas enviado → {email_cliente}")
    except Exception as e:
        print(f"Falha boas-vindas (Graph): {e}")


# ── CRIAR CLIENTE ─────────────────────────────────────────────────────────────
@app.route("/api/customers", methods=["POST"])
def create_customer():
    data = request.json
    payload = {
        "name":                 data.get("name"),
        "cpfCnpj":              data.get("cpfCnpj"),
        "email":                data.get("email"),
        "phone":                data.get("phone"),
        "notificationDisabled": True,
    }
    resp = _asaas_http.post(f"{ASAAS_BASE_URL}/v3/customers", headers=_asaas_headers(), json=payload)
    if resp.status_code in (200, 201):
        return jsonify({"success": True, "customerId": resp.json()["id"]})
    return jsonify({"success": False, "error": resp.json()}), 400


# ── CARTÃO DE CRÉDITO ─────────────────────────────────────────────────────────
@app.route("/api/pay/credit-card", methods=["POST"])
def pay_credit_card():
    data     = request.json
    due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload  = {
        "customer":    data["customerId"],
        "billingType": "CREDIT_CARD",
        "value":       data["value"],
        "dueDate":     due_date,
        "description": data.get("description", "Plano Hostweb"),
        "creditCard": {
            "holderName":  data["card"]["holderName"],
            "number":      data["card"]["number"],
            "expiryMonth": data["card"]["expiryMonth"],
            "expiryYear":  data["card"]["expiryYear"],
            "ccv":         data["card"]["ccv"],
        },
        "creditCardHolderInfo": {
            "name":          data["holder"]["name"],
            "email":         data["holder"]["email"],
            "cpfCnpj":       data["holder"]["cpfCnpj"],
            "postalCode":    data["holder"]["postalCode"],
            "addressNumber": data["holder"]["addressNumber"],
            "phone":         data["holder"]["phone"],
        },
        "remoteIp": request.remote_addr,
    }
    resp = _asaas_http.post(f"{ASAAS_BASE_URL}/v3/payments", headers=_asaas_headers(), json=payload)
    if resp.status_code in (200, 201):
        result = resp.json()
        return jsonify({"success": True, "paymentId": result["id"], "status": result["status"]})
    return jsonify({"success": False, "error": resp.json()}), 400


# ── PIX ───────────────────────────────────────────────────────────────────────
@app.route("/api/pay/pix", methods=["POST"])
def pay_pix():
    data     = request.json
    due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload  = {
        "customer":    data["customerId"],
        "billingType": "PIX",
        "value":       data["value"],
        "dueDate":     due_date,
        "description": data.get("description", "Plano Hostweb"),
    }
    resp = _asaas_http.post(f"{ASAAS_BASE_URL}/v3/payments", headers=_asaas_headers(), json=payload)
    if resp.status_code not in (200, 201):
        return jsonify({"success": False, "error": resp.json()}), 400

    payment    = resp.json()
    payment_id = payment["id"]

    pix_resp = _asaas_http.get(
        f"{ASAAS_BASE_URL}/v3/payments/{payment_id}/pixQrCode",
        headers=_asaas_headers(),
    )
    if pix_resp.status_code == 200:
        pix = pix_resp.json()
        return jsonify({
            "success":        True,
            "paymentId":      payment_id,
            "status":         payment["status"],
            "pixQrCode":      pix.get("encodedImage"),
            "pixCopyPaste":   pix.get("payload"),
            "expirationDate": pix.get("expirationDate"),
        })
    return jsonify({"success": True, "paymentId": payment_id, "status": payment["status"],
                    "pixQrCode": None}), 200


# ── BOLETO ────────────────────────────────────────────────────────────────────
@app.route("/api/pay/boleto", methods=["POST"])
def pay_boleto():
    data     = request.json
    due_date = data.get("dueDate", (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))
    payload  = {
        "customer":    data["customerId"],
        "billingType": "BOLETO",
        "value":       data["value"],
        "dueDate":     due_date,
        "description": data.get("description", "Plano Hostweb"),
    }
    resp = _asaas_http.post(f"{ASAAS_BASE_URL}/v3/payments", headers=_asaas_headers(), json=payload)
    if resp.status_code in (200, 201):
        result = resp.json()
        return jsonify({
            "success":     True,
            "paymentId":   result["id"],
            "status":      result["status"],
            "bankSlipUrl": result.get("bankSlipUrl"),
            "invoiceUrl":  result.get("invoiceUrl"),
        })
    return jsonify({"success": False, "error": resp.json()}), 400


# ── STATUS ────────────────────────────────────────────────────────────────────
@app.route("/api/payments/<payment_id>/status", methods=["GET"])
def check_payment_status(payment_id):
    resp = _asaas_http.get(f"{ASAAS_BASE_URL}/v3/payments/{payment_id}", headers=_asaas_headers())
    if resp.status_code == 200:
        result = resp.json()
        return jsonify({"success": True, "paymentId": result["id"], "status": result["status"]})
    return jsonify({"success": False, "error": resp.json()}), 400


# ── WEBHOOK ───────────────────────────────────────────────────────────────────
@app.route("/api/webhook/asaas", methods=["POST"])
def webhook_asaas():
    data       = request.json or {}
    event      = data.get("event")
    payment    = data.get("payment", {})
    payment_id = payment.get("id")
    status     = payment.get("status")
    print(f"[WEBHOOK] {event} | payment={payment_id} | status={status}")

    if event in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        customer_email = payment.get("customer", {}).get("email") if isinstance(payment.get("customer"), dict) else ""
        description    = payment.get("description", "Plano Hostweb")
        if customer_email:
            enviar_email_boas_vindas(customer_email, "Cliente", description)

    return jsonify({"received": True}), 200


# ── HEALTH ────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    from utils import get_db, AZURE_CLIENT_ID
    db_ok = False
    try:
        conn = get_db(); conn.close(); db_ok = True
    except Exception:
        pass
    return jsonify({
        "status":      "online",
        "database":    "ok" if db_ok else "erro",
        "gateway":     "asaas",
        "asaas_env":   "sandbox" if "sandbox" in ASAAS_BASE_URL else "producao",
        "graph_email": "ok" if AZURE_CLIENT_ID else "não configurado",
        "blueprints":  ["aceite", "pages"],
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Hostweb Backend (Docker) -> http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
