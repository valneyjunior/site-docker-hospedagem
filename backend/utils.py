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
    "starter_mensal":            {"name": "Starter Mensal",           "price_id": "price_1TB28K72l5zV6G90wCnu60Wx", "mode": "subscription"},
    "business_mensal":           {"name": "Business Mensal",          "price_id": "price_business_mensal",           "mode": "subscription"},
    "business_plus_mensal":      {"name": "Business Plus Mensal",     "price_id": "price_business_plus_mensal",      "mode": "subscription"},
    "enterprise_mensal":         {"name": "Enterprise Mensal",        "price_id": "price_enterprise_mensal",         "mode": "subscription"},
    "starter_anual":             {"name": "Starter Anual",            "price_id": "price_starter_anual",             "mode": "subscription"},
    "business_anual":            {"name": "Business Anual",           "price_id": "price_business_anual",            "mode": "subscription"},
    "business_plus_anual":       {"name": "Business Plus Anual",      "price_id": "price_business_plus_anual",       "mode": "subscription"},
    "enterprise_anual":          {"name": "Enterprise Anual",         "price_id": "price_enterprise_anual",          "mode": "subscription"},
    "ded_essencial_mensal":      {"name": "Dedicado Essencial",       "price_id": "price_ded_essencial",             "mode": "subscription"},
    "ded_profissional_mensal":   {"name": "Dedicado Profissional",    "price_id": "price_ded_profissional",          "mode": "subscription"},
    "ded_enterprise_mensal":     {"name": "Dedicado Enterprise",      "price_id": "price_ded_enterprise",            "mode": "subscription"},
    "zoho_mail_lite_5_mensal":   {"name": "Zoho Mail Lite 5GB",      "price_id": "price_zoho_lite_5",               "mode": "subscription"},
    "zoho_mail_lite_10_mensal":  {"name": "Zoho Mail Lite 10GB",     "price_id": "price_zoho_lite_10",              "mode": "subscription"},
    "zoho_mail_premium_mensal":  {"name": "Zoho Mail Premium",       "price_id": "price_zoho_premium",              "mode": "subscription"},
    "zoho_workplace_std_mensal": {"name": "Zoho Workplace Padrão",   "price_id": "price_zoho_wp_std",               "mode": "subscription"},
    "zoho_workplace_pro_mensal": {"name": "Zoho Workplace Pro",      "price_id": "price_zoho_wp_pro",               "mode": "subscription"},
    # ── Hospedagem de Sites (novos) ───────────────────────────────────────────
    "sites_basico_mensal":       {"name": "Sites Básico",             "price_id": "price_1TB28K72l5zV6G90wCnu60Wx", "mode": "subscription"},
    "sites_plus_mensal":         {"name": "Sites Plus",               "price_id": "price_sites_plus",                "mode": "subscription"},
    "sites_pro_mensal":          {"name": "Sites Pro",                "price_id": "price_sites_pro",                 "mode": "subscription"},
    # ── Hospedagem de E-mail (novos) ──────────────────────────────────────────
    "email_starter_mensal":      {"name": "E-mail Starter",           "price_id": "price_email_starter",             "mode": "subscription"},
    "email_business_mensal":     {"name": "E-mail Business",          "price_id": "price_email_business",            "mode": "subscription"},
    "email_enterprise_mensal":   {"name": "E-mail Enterprise",        "price_id": "price_email_enterprise",          "mode": "subscription"},
    # ── Domínios (pagamento único anual) ──────────────────────────────────────
    "dominio_com_br":            {"name": "Domínio .com.br",          "price_id": "price_dominio_com_br",            "mode": "payment"},
    "dominio_com":               {"name": "Domínio .com",             "price_id": "price_dominio_com",               "mode": "payment"},
    "dominio_net":               {"name": "Domínio .net",             "price_id": "price_dominio_net",               "mode": "payment"},
    "dominio_org":               {"name": "Domínio .org",             "price_id": "price_dominio_org",               "mode": "payment"},
}
