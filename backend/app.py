from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import stripe, os

from utils import PLANS, graph_send_email, EMAIL_FROM, EMAIL_REPLY

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SUCCESS_URL    = os.getenv(
    "SUCCESS_URL",
    "http://localhost/sucesso?session_id={CHECKOUT_SESSION_ID}"
)
CANCEL_URL     = os.getenv("CANCEL_URL", "http://localhost/?cancelado=1")

from blueprints.aceite import aceite_bp
from blueprints.pages import pages_bp
app.register_blueprint(aceite_bp)
app.register_blueprint(pages_bp)


# ── E-MAIL DE BOAS-VINDAS ─────────────────────────────────────────────────────
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


# ── ROTAS ─────────────────────────────────────────────────────────────────────
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Cria sessão Stripe diretamente (sem aceite). Mantido para testes."""
    data    = request.get_json()
    plan_id = data.get("plan_id")
    email   = data.get("email")
    nome    = data.get("nome", "Cliente")
    empresa = data.get("empresa", "")

    plan = PLANS.get(plan_id)
    if not plan:
        return jsonify({"error": f"Plano não encontrado: {plan_id}"}), 400

    try:
        params = {
            "mode":       "subscription",
            "line_items": [{"price": plan["price_id"], "quantity": 1}],
            "success_url": SUCCESS_URL,
            "cancel_url":  CANCEL_URL,
            "metadata": {
                "plan_id":   plan_id,
                "plan_name": plan["name"],
                "nome":      nome,
                "empresa":   empresa,
            },
        }
        if email:
            params["customer_email"] = email
        session = stripe.checkout.Session.create(**params)
        return jsonify({"url": session.url})
    except stripe.error.StripeError as e:
        return jsonify({"error": str(e.user_message)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get-session", methods=["GET"])
def get_session():
    """Retorna dados de uma sessão Stripe (usada pela página sucesso.html)."""
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id obrigatório"}), 400
    try:
        s    = stripe.checkout.Session.retrieve(session_id)
        meta = dict(s.get("metadata") or {})
        return jsonify({
            "customer_email": s.get("customer_email") or (s.get("customer_details") or {}).get("email", ""),
            "amount_total":   s.get("amount_total"),
            "plan_name":      meta.get("plan_name", ""),
            "metadata":       meta,
        })
    except stripe.error.StripeError as e:
        return jsonify({"error": str(e.user_message)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/webhook", methods=["POST"])
def webhook():
    payload    = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    etype = event["type"]

    if etype == "checkout.session.completed":
        s     = event["data"]["object"]
        email = s.get("customer_email") or s.get("customer_details", {}).get("email", "")
        meta  = s.get("metadata", {})
        plano = meta.get("plan_name", "N/A")
        nome  = meta.get("nome", "Cliente")
        print(f"Pagamento confirmado | Plano: {plano} | E-mail: {email}")
        if email:
            enviar_email_boas_vindas(email, nome, plano)

    elif etype == "invoice.payment_succeeded":
        amount = event["data"]["object"].get("amount_paid", 0) / 100
        print(f"Renovação paga | R$ {amount:.2f}")

    elif etype == "customer.subscription.deleted":
        print(f"Assinatura cancelada | {event['data']['object'].get('customer')}")

    elif etype == "invoice.payment_failed":
        print(f"Pagamento falhou | {event['data']['object'].get('customer_email')}")

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    from utils import get_db
    db_ok = False
    try:
        conn = get_db()
        conn.close()
        db_ok = True
    except Exception:
        pass
    from utils import AZURE_CLIENT_ID
    key = stripe.api_key or ""
    return jsonify({
        "status":      "online",
        "database":    "ok" if db_ok else "erro",
        "stripe_mode": "test" if "test" in key else "live",
        "graph_email": "ok" if AZURE_CLIENT_ID else "não configurado",
        "blueprints":  ["aceite", "pages"],
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Hostweb Backend (Docker) -> http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
