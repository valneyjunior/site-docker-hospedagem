from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests as _http
import os

from utils import PLANS, graph_send_email, EMAIL_FROM, EMAIL_REPLY, get_db
from whm import criar_conta_cpanel, suspender_conta, reativar_conta

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
    html = render_template("email/boas_vindas.html", nome=nome, plano=plano)
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


# ── PROVISIONAMENTO ───────────────────────────────────────────────────────────
def _email_credenciais(email, nome, plano, dominio, username, senha):
    cpanel_url = f"https://{os.getenv('WHM_HOST', 'seu-servidor')}:2083"
    html = render_template(
        "email/credenciais_cpanel.html",
        nome=nome, plano=plano, dominio=dominio,
        username=username, senha=senha, cpanel_url=cpanel_url,
    )
    try:
        graph_send_email(
            to        = email,
            subject   = f"Hostweb — Acesso ao cPanel: {dominio}",
            html_body = html,
            reply_to  = EMAIL_REPLY,
        )
        print(f"E-mail credenciais enviado → {email}")
    except Exception as exc:
        print(f"Falha e-mail credenciais: {exc}")


def _provisionar(payment_id: str, customer_id: str):
    """Busca aceite, cria conta WHM e registra em provisionamentos."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # busca aceite pelo customer_id do Asaas
            cur.execute(
                "SELECT id, nome, email, plan_id, plano, dominio FROM aceites "
                "WHERE asaas_customer_id = %s ORDER BY criado_em DESC LIMIT 1",
                (customer_id,)
            )
            row = cur.fetchone()
            if not row:
                print(f"[PROVISIONING] Aceite não encontrado para customer={customer_id}")
                return

            aceite_id, nome, email, plan_id, plano, dominio = row

            # evita duplo provisionamento
            cur.execute(
                "SELECT id FROM provisionamentos WHERE asaas_payment_id = %s", (payment_id,)
            )
            if cur.fetchone():
                print(f"[PROVISIONING] Pagamento {payment_id} já provisionado — ignorado")
                return

            # registra como pendente
            cur.execute("""
                INSERT INTO provisionamentos
                    (aceite_id, asaas_payment_id, asaas_customer_id, dominio, plano, status)
                VALUES (%s, %s, %s, %s, %s, 'pendente')
                RETURNING id
            """, (aceite_id, payment_id, customer_id, dominio, plano))
            prov_id = cur.fetchone()[0]
        conn.commit()

        plan_info   = PLANS.get(plan_id or "", {})
        whm_package = plan_info.get("whm_package")

        if not whm_package:
            # plano sem provisionamento automático (Zoho, dedicado, domínio)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE provisionamentos SET status='manual', erro_msg=%s WHERE id=%s",
                    ("Plano requer provisionamento manual.", prov_id)
                )
            conn.commit()
            enviar_email_boas_vindas(email, nome, plano)
            print(f"[PROVISIONING] Plano {plan_id} marcado para provisionamento manual")
            return

        username, senha, ok, msg = criar_conta_cpanel(dominio or "", email, nome, whm_package)

        if ok:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE provisionamentos
                    SET status='provisionado', cpanel_username=%s, whm_package=%s,
                        provisionado_em=NOW(), erro_msg=NULL
                    WHERE id=%s
                """, (username, whm_package, prov_id))
            conn.commit()
            _email_credenciais(email, nome, plano, dominio or "", username, senha)
            print(f"[PROVISIONING] OK | {dominio} | user={username} | plano={whm_package}")
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE provisionamentos SET status='erro', erro_msg=%s WHERE id=%s",
                    (msg, prov_id)
                )
            conn.commit()
            enviar_email_boas_vindas(email, nome, plano)
            print(f"[PROVISIONING] ERRO | {dominio} | {msg}")

    except Exception as exc:
        print(f"[PROVISIONING] Exceção: {exc}")
    finally:
        conn.close()


# ── WEBHOOK ───────────────────────────────────────────────────────────────────
@app.route("/api/webhook/asaas", methods=["POST"])
def webhook_asaas():
    data       = request.json or {}
    event      = data.get("event")
    payment    = data.get("payment", {})
    payment_id = payment.get("id", "")
    customer_id = payment.get("customer", "")
    print(f"[WEBHOOK] {event} | payment={payment_id} | customer={customer_id}")

    if event in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        if payment_id and customer_id:
            _provisionar(payment_id, customer_id)

    elif event == "PAYMENT_OVERDUE":
        # busca username e suspende
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT cpanel_username FROM provisionamentos WHERE asaas_customer_id=%s "
                    "AND status='provisionado' LIMIT 1", (customer_id,)
                )
                row = cur.fetchone()
            conn.close()
            if row and row[0]:
                suspender_conta(row[0], razao="inadimplencia")
                print(f"[WEBHOOK] Conta suspensa: {row[0]}")
        except Exception as exc:
            print(f"[WEBHOOK] Erro ao suspender: {exc}")

    elif event == "PAYMENT_RECEIVED" and payment.get("status") == "RECEIVED":
        # reativação após pagamento de conta em atraso
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT cpanel_username FROM provisionamentos WHERE asaas_customer_id=%s "
                    "AND status='provisionado' LIMIT 1", (customer_id,)
                )
                row = cur.fetchone()
            conn.close()
            if row and row[0]:
                reativar_conta(row[0])
                print(f"[WEBHOOK] Conta reativada: {row[0]}")
        except Exception as exc:
            print(f"[WEBHOOK] Erro ao reativar: {exc}")

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
