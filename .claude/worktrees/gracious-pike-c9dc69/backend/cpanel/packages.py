"""
cpanel/packages.py — Mapeamento plan_id → pacote WHM e especificações de recursos.

Planos sites_* são provisionados automaticamente após o pagamento.
Planos ded_* requerem ação manual da equipe Hostweb.
Demais planos (zoho, email, domínio) não utilizam cPanel.
"""

# plan_id (Stripe/sistema) → nome do pacote no WHM
PLAN_PACKAGES = {
    "sites_basico_mensal": "hw_sites_basico",
    "sites_plus_mensal":   "hw_sites_plus",
    "sites_pro_mensal":    "hw_sites_pro",
}

# Planos que disparam provisionamento automático ao receber webhook Stripe
AUTO_PROVISION_PLANS = set(PLAN_PACKAGES.keys())

# Planos que exigem provisionamento manual (dedicado)
MANUAL_PLANS = {
    "ded_essencial_mensal",
    "ded_profissional_mensal",
    "ded_enterprise_mensal",
}

# Especificações de recursos por pacote WHM
# quota/bwlimit em MB; 0 = unlimited no WHM
PACKAGE_SPECS = {
    "hw_sites_basico": {
        "quota":    10240,   # 10 GB disco
        "bwlimit":  51200,   # 50 GB tráfego/mês
        "maxaddon": 1,       # domínios addon
        "maxpop":   20,      # contas de e-mail
        "maxsql":   5,       # bancos de dados
        "maxftp":   5,       # contas FTP
    },
    "hw_sites_plus": {
        "quota":    30720,   # 30 GB disco
        "bwlimit":  102400,  # 100 GB tráfego/mês
        "maxaddon": 5,
        "maxpop":   50,
        "maxsql":   15,
        "maxftp":   15,
    },
    "hw_sites_pro": {
        "quota":    0,       # unlimited
        "bwlimit":  0,       # unlimited
        "maxaddon": 0,       # unlimited
        "maxpop":   0,       # unlimited
        "maxsql":   0,       # unlimited
        "maxftp":   0,       # unlimited
    },
}
