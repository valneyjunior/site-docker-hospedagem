"""
utils.py — Configurações compartilhadas: Microsoft Graph e-mail, banco de dados e planos.
"""
import os, psycopg2, requests as _http
from dotenv import load_dotenv

load_dotenv()

# ── MICROSOFT GRAPH ───────────────────────────────────────────────────────────
AZURE_TENANT_ID     = os.getenv("AZURE_TENANT_ID",     "")
AZURE_CLIENT_ID     = os.getenv("AZURE_CLIENT_ID",     "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
GRAPH_SENDER        = os.getenv("GRAPH_SENDER",        "")
EMAIL_REPLY         = os.getenv("EMAIL_REPLY",         "comercial@hostweb.com.br")

# mantido para compatibilidade com imports existentes em aceite.py
EMAIL_FROM  = GRAPH_SENDER
SMTP_USER   = ""
SMTP_PASS   = ""

def _get_graph_token() -> str:
    """Obtém access token via client credentials (OAuth2)."""
    url  = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type":    "client_credentials",
        "client_id":     AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope":         "https://graph.microsoft.com/.default",
    }
    r = _http.post(url, data=data, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def graph_send_email(to: str, subject: str, html_body: str,
                     reply_to: str | None = None) -> None:
    """Envia e-mail via Microsoft Graph API (Mail.Send application permission)."""
    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, GRAPH_SENDER]):
        print("Graph API não configurada — e-mail não enviado.")
        return

    token   = _get_graph_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "message": {
            "subject": subject,
            "body":    {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to}}],
            **({"replyTo": [{"emailAddress": {"address": reply_to}}]} if reply_to else {}),
        },
        "saveToSentItems": True,
    }
    url = f"https://graph.microsoft.com/v1.0/users/{GRAPH_SENDER}/sendMail"
    r   = _http.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    print(f"E-mail enviado via Graph → {to} | {subject[:50]}")

# ── BANCO DE DADOS ────────────────────────────────────────────────────────────
def get_db():
    """Retorna uma conexão psycopg2. Fechar após o uso."""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ── PLANOS ────────────────────────────────────────────────────────────────────
PLANS = {
    # ── Hospedagem Compartilhada (legado) ─────────────────────────────────────
    "starter_mensal":            {"name": "Starter Mensal",           "value": 39.90},
    "business_mensal":           {"name": "Business Mensal",          "value": 69.90},
    "business_plus_mensal":      {"name": "Business Plus Mensal",     "value": 99.90},
    "enterprise_mensal":         {"name": "Enterprise Mensal",        "value": 149.90},
    "starter_anual":             {"name": "Starter Anual",            "value": 407.04},
    "business_anual":            {"name": "Business Anual",           "value": 713.04},
    "business_plus_anual":       {"name": "Business Plus Anual",      "value": 1019.04},
    "enterprise_anual":          {"name": "Enterprise Anual",         "value": 1529.04},
    "ded_essencial_mensal":      {"name": "Dedicado Essencial",       "value": 499.00},
    "ded_profissional_mensal":   {"name": "Dedicado Profissional",    "value": 799.00},
    "ded_enterprise_mensal":     {"name": "Dedicado Enterprise",      "value": 1299.00},
    "zoho_mail_lite_5_mensal":   {"name": "Zoho Mail Lite 5GB",      "value": 95.00},
    "zoho_mail_lite_10_mensal":  {"name": "Zoho Mail Lite 10GB",     "value": 152.00},
    "zoho_mail_premium_mensal":  {"name": "Zoho Mail Premium",       "value": 285.00},
    "zoho_workplace_std_mensal": {"name": "Zoho Workplace Padrão",   "value": 190.00},
    "zoho_workplace_pro_mensal": {"name": "Zoho Workplace Pro",      "value": 380.00},
    # ── Hospedagem de Sites ───────────────────────────────────────────────────
    "sites_basico_mensal":       {"name": "Hospedagem Básico",        "value": 9.90},
    "sites_plus_mensal":         {"name": "Hospedagem Plus",          "value": 19.90},
    "sites_pro_mensal":          {"name": "Hospedagem Pro",           "value": 39.90},
    # ── Hospedagem de E-mail ──────────────────────────────────────────────────
    "email_starter_mensal":      {"name": "E-mail Starter",           "value": 14.90},
    "email_business_mensal":     {"name": "E-mail Business",          "value": 29.90},
    "email_enterprise_mensal":   {"name": "E-mail Enterprise",        "value": 49.90},
    # ── Domínios (pagamento único anual) ──────────────────────────────────────
    "dominio_com_br":            {"name": "Domínio .com.br",          "value": 39.90},
    "dominio_com":               {"name": "Domínio .com",             "value": 59.90},
    "dominio_net":               {"name": "Domínio .net",             "value": 59.90},
    "dominio_org":               {"name": "Domínio .org",             "value": 59.90},
}
