"""
utils.py — Configurações compartilhadas: SMTP, banco de dados e planos.
"""
import os, smtplib, psycopg2
from dotenv import load_dotenv

load_dotenv()

# ── SMTP ─────────────────────────────────────────────────────────────────────
SMTP_HOST   = os.getenv("SMTP_HOST",  "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER",  "")
SMTP_PASS   = os.getenv("SMTP_PASS",  "")
EMAIL_FROM  = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_REPLY = os.getenv("EMAIL_REPLY", "comercial@hostweb.com.br")

def smtp_conn():
    conn = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
    conn.ehlo()
    conn.starttls()
    conn.login(SMTP_USER, SMTP_PASS)
    return conn

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
