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
    "starter_mensal":            {"name": "Starter Mensal",           "price_id": "price_1TB28K72l5zV6G90wCnu60Wx"},
    "business_mensal":           {"name": "Business Mensal",          "price_id": "price_business_mensal"},
    "business_plus_mensal":      {"name": "Business Plus Mensal",     "price_id": "price_business_plus_mensal"},
    "enterprise_mensal":         {"name": "Enterprise Mensal",        "price_id": "price_enterprise_mensal"},
    "starter_anual":             {"name": "Starter Anual",            "price_id": "price_starter_anual"},
    "business_anual":            {"name": "Business Anual",           "price_id": "price_business_anual"},
    "business_plus_anual":       {"name": "Business Plus Anual",      "price_id": "price_business_plus_anual"},
    "enterprise_anual":          {"name": "Enterprise Anual",         "price_id": "price_enterprise_anual"},
    "ded_essencial_mensal":      {"name": "Dedicado Essencial",       "price_id": "price_ded_essencial"},
    "ded_profissional_mensal":   {"name": "Dedicado Profissional",    "price_id": "price_ded_profissional"},
    "ded_enterprise_mensal":     {"name": "Dedicado Enterprise",      "price_id": "price_ded_enterprise"},
    "zoho_mail_lite_5_mensal":   {"name": "Zoho Mail Lite 5GB",      "price_id": "price_zoho_lite_5"},
    "zoho_mail_lite_10_mensal":  {"name": "Zoho Mail Lite 10GB",     "price_id": "price_zoho_lite_10"},
    "zoho_mail_premium_mensal":  {"name": "Zoho Mail Premium",       "price_id": "price_zoho_premium"},
    "zoho_workplace_std_mensal": {"name": "Zoho Workplace Padrão",   "price_id": "price_zoho_wp_std"},
    "zoho_workplace_pro_mensal": {"name": "Zoho Workplace Pro",      "price_id": "price_zoho_wp_pro"},
}
