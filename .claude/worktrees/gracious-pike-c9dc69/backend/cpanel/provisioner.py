"""
cpanel/provisioner.py — Lógica de provisionamento automático de contas cPanel.

Fluxo pós-pagamento (chamado pelo webhook Stripe):
  1. Verifica idempotência (session_stripe já processada?)
  2. Identifica tipo de plano: auto / manual / ignorar
  3. Auto: gera usuário+senha, chama WHM API, persiste no DB
  4. Manual: registra como pendente_manual e notifica equipe
  5. Envia e-mail de credenciais ao cliente (planos auto)
  6. Notifica equipe via Slack e e-mail interno

Nota: provisionar_async() executa em thread daemon para não bloquear o
webhook do Stripe (timeout ~30s). Para produção com alto volume, substituir
por fila (Celery/RQ).
"""
import os
import re
import secrets
import string
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests as _requests

from cpanel.client import criar_conta_cpanel
from cpanel.packages import AUTO_PROVISION_PLANS, MANUAL_PLANS, PLAN_PACKAGES
from utils import EMAIL_FROM, EMAIL_REPLY, SMTP_PASS, SMTP_USER, get_db, smtp_conn

WHM_HOST           = os.getenv("WHM_HOST", "")
SLACK_WEBHOOK_URL  = os.getenv("SLACK_WEBHOOK_URL", "")
EMAIL_NOTIFY       = os.getenv("EMAIL_NOTIFY_INTERNAL", "comercial@hostweb.com.br")

# Planos que não usam cPanel (sem provisionamento)
_SKIP_PLANS = {
    "zoho_mail_lite_5_mensal", "zoho_mail_lite_10_mensal",
    "zoho_mail_premium_mensal", "zoho_workplace_std_mensal",
    "zoho_workplace_pro_mensal",
    "email_starter_mensal", "email_business_mensal", "email_enterprise_mensal",
    "dominio_com_br", "dominio_com", "dominio_net", "dominio_org",
}


# ── Geração de credenciais ────────────────────────────────────────────────────

def _gerar_username(email):
    """Gera username compatível com cPanel: até 8 chars, alfanumérico, começa com letra."""
    prefix = email.split("@")[0]
    clean  = re.sub(r"[^a-zA-Z0-9]", "", prefix).lower()
    if not clean or not clean[0].isalpha():
        clean = "hw" + clean
    return clean[:8] or "hwuser"


def _gerar_senha():
    """Gera senha forte de 16 caracteres usando secrets."""
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(chars) for _ in range(16))


# ── Banco de dados ────────────────────────────────────────────────────────────

def _username_disponivel(username):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM provisionamentos WHERE cpanel_user = %s AND status != 'erro'",
                (username,),
            )
            return cur.fetchone() is None
    finally:
        conn.close()


def _username_unico(base):
    """Retorna username único adicionando sufixo hex se necessário."""
    if _username_disponivel(base):
        return base
    for _ in range(10):
        suffix   = secrets.token_hex(1)          # 2 chars hex
        username = base[:6] + suffix
        if _username_disponivel(username):
            return username
    raise RuntimeError("Não foi possível gerar username único para " + base)


def _ja_provisionado(session_stripe):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM provisionamentos WHERE session_stripe = %s",
                (session_stripe,),
            )
            row = cur.fetchone()
            return row is not None and row[0] in ("ativo", "pendente_manual", "criando")
    finally:
        conn.close()


def _salvar(session_stripe, protocolo, nome, email, domain, plano, plan_id,
            servidor, cpanel_user, status, erro_msg=None):
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO provisionamentos
                        (session_stripe, protocolo_aceite, nome, email, domain,
                         plano, plan_id, servidor, cpanel_user, status, erro_msg)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (session_stripe) DO NOTHING
                    """,
                    (session_stripe, protocolo, nome, email, domain,
                     plano, plan_id, servidor, cpanel_user, status, erro_msg),
                )
    finally:
        conn.close()


def _atualizar_status(session_stripe, status, erro_msg=None):
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE provisionamentos
                       SET status = %s, erro_msg = %s, atualizado_em = NOW()
                       WHERE session_stripe = %s""",
                    (status, erro_msg, session_stripe),
                )
    finally:
        conn.close()


# ── Notificações ──────────────────────────────────────────────────────────────

def _slack(mensagem):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        _requests.post(SLACK_WEBHOOK_URL, json={"text": mensagem}, timeout=10)
    except Exception as exc:
        print(f"[provisioner] Slack falhou: {exc}")


def _email_interno(assunto, corpo_html):
    if not SMTP_USER or not SMTP_PASS:
        return
    msg             = MIMEMultipart("alternative")
    msg["Subject"]  = assunto
    msg["From"]     = f"Hostweb Automação <{EMAIL_FROM}>"
    msg["To"]       = EMAIL_NOTIFY
    msg["Reply-To"] = EMAIL_REPLY
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    try:
        with smtp_conn() as conn:
            conn.sendmail(EMAIL_FROM, EMAIL_NOTIFY, msg.as_string())
    except Exception as exc:
        print(f"[provisioner] E-mail interno falhou: {exc}")


def _email_credenciais(email, nome, domain, cpanel_user, senha, plano):
    if not SMTP_USER or not SMTP_PASS:
        return
    cpanel_url = f"https://{domain}:2083"
    msg             = MIMEMultipart("alternative")
    msg["Subject"]  = f"Hostweb — Credenciais do seu cPanel ({domain})"
    msg["From"]     = f"Hostweb <{EMAIL_FROM}>"
    msg["To"]       = email
    msg["Reply-To"] = EMAIL_REPLY

    html = f"""
<html><body style="font-family:Segoe UI,sans-serif;background:#f5f5f7;padding:32px">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
  box-shadow:0 4px 24px rgba(0,0,0,.08)">
  <div style="background:linear-gradient(135deg,#e8001c,#6b0fa8);padding:32px;
    text-align:center;border-radius:16px 16px 0 0">
    <img src="https://hostweb.com.br/wp-content/uploads/2021/03/Logo-Hostweb.png"
      alt="Hostweb" style="height:48px;filter:brightness(0) invert(1)">
    <h1 style="color:#fff;margin:16px 0 0;font-size:1.3rem">Sua hospedagem está pronta!</h1>
  </div>
  <div style="padding:32px">
    <p style="color:#333">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#555;line-height:1.7">
      Sua conta de hospedagem <strong style="color:#e8001c">{plano}</strong>
      foi criada. Acesse o cPanel com as credenciais abaixo:
    </p>
    <div style="background:#f9f5ff;border:1px solid #d8b4fe;border-radius:10px;
      padding:20px;margin:20px 0">
      <table style="width:100%;font-size:.9rem;border-collapse:collapse">
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8;width:42%">Domínio</td>
          <td style="padding:8px">{domain}</td>
        </tr>
        <tr style="background:#f0e6ff">
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Usuário cPanel</td>
          <td style="padding:8px;font-family:monospace;font-weight:700">{cpanel_user}</td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Senha</td>
          <td style="padding:8px;font-family:monospace;font-weight:700">{senha}</td>
        </tr>
        <tr style="background:#f0e6ff">
          <td style="padding:8px;font-weight:700;color:#6b0fa8">URL cPanel</td>
          <td style="padding:8px">
            <a href="{cpanel_url}" style="color:#6b0fa8">{cpanel_url}</a>
          </td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8">FTP / SFTP</td>
          <td style="padding:8px">{domain} (portas 21 / 22)</td>
        </tr>
      </table>
    </div>
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;
      padding:16px;margin:16px 0">
      <p style="margin:0;font-size:.85rem;color:#856404">
        <strong>Importante:</strong> Troque sua senha no primeiro acesso e
        guarde em local seguro. Não compartilhe suas credenciais.
      </p>
    </div>
    <p style="color:#555;font-size:.85rem">
      Suporte:
      <a href="https://hostweb.com.br/suporte" style="color:#6b0fa8">hostweb.com.br/suporte</a>
      &nbsp;|&nbsp;
      WhatsApp: <a href="https://wa.me/5585991293286" style="color:#6b0fa8">85 99129-3286</a>
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
    <p style="color:#999;font-size:.75rem;text-align:center">
      Hostweb Data Center e Serviços LTDA EPP — CNPJ 07.797.967/0001-60 — Fortaleza, CE
    </p>
  </div>
</div>
</body></html>
"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtp_conn() as conn:
            conn.sendmail(EMAIL_FROM, email, msg.as_string())
        print(f"[provisioner] Credenciais enviadas → {email}")
    except Exception as exc:
        print(f"[provisioner] Falha ao enviar credenciais: {exc}")


# ── Provisionamento ───────────────────────────────────────────────────────────

def provisionar(session_stripe, meta, email_cliente):
    """Provisiona conta cPanel após confirmação de pagamento Stripe."""
    plan_id   = meta.get("plan_id", "")
    plano     = meta.get("plan_name", plan_id)
    nome      = meta.get("nome", "Cliente")
    domain    = meta.get("domain", "").strip().lower()
    protocolo = meta.get("protocolo_aceite", "")

    if plan_id in _SKIP_PLANS:
        print(f"[provisioner] Plano {plan_id} não usa cPanel. Ignorando.")
        return

    if _ja_provisionado(session_stripe):
        print(f"[provisioner] Sessão {session_stripe} já processada. Ignorando.")
        return

    # ── Planos dedicados: registra para ação manual ───────────────────────
    if plan_id in MANUAL_PLANS:
        _salvar(session_stripe, protocolo, nome, email_cliente, domain,
                plano, plan_id, WHM_HOST, "", "pendente_manual")

        _slack(
            f":wrench: *Provisionamento manual necessário*\n"
            f"Cliente: {nome} ({email_cliente})\n"
            f"Plano: {plano} | Domínio: `{domain}`\n"
            f"Protocolo: `{protocolo}`\n"
            f"Ação: provisionar manualmente no WHM."
        )
        _email_interno(
            f"[Hostweb] Provisionamento manual: {plano} — {domain}",
            f"<p>Cliente <strong>{nome}</strong> ({email_cliente}) contratou "
            f"<strong>{plano}</strong>.</p>"
            f"<p>Domínio: <strong>{domain}</strong></p>"
            f"<p>Protocolo: {protocolo}</p>"
            f"<p style='color:#e8001c'><strong>Ação: provisionar manualmente no WHM.</strong></p>",
        )
        print(f"[provisioner] Plano dedicado registrado para provisionamento manual: {domain}")
        return

    if plan_id not in AUTO_PROVISION_PLANS:
        print(f"[provisioner] Plano {plan_id} não mapeado. Ignorando.")
        return

    if not domain:
        _slack(f":x: *ERRO provisionamento* — domínio ausente para sessão `{session_stripe}` ({plano})")
        print(f"[provisioner] Domínio ausente para {session_stripe}. Abortando.")
        return

    package = PLAN_PACKAGES[plan_id]
    base    = _gerar_username(email_cliente)

    try:
        username = _username_unico(base)
        senha    = _gerar_senha()

        _salvar(session_stripe, protocolo, nome, email_cliente, domain,
                plano, plan_id, WHM_HOST, username, "criando")

        criar_conta_cpanel(username, domain, senha, package, email_cliente)

        _atualizar_status(session_stripe, "ativo")
        print(f"[provisioner] cPanel criado: {username}@{domain} ({plano})")

        _email_credenciais(email_cliente, nome, domain, username, senha, plano)

        _slack(
            f":white_check_mark: *Nova conta cPanel provisionada*\n"
            f"Cliente: {nome} ({email_cliente})\n"
            f"Usuário: `{username}` | Domínio: `{domain}`\n"
            f"Plano: {plano} | Servidor: `{WHM_HOST}`"
        )
        _email_interno(
            f"[Hostweb] ✅ cPanel provisionado: {username}@{domain}",
            f"<table style='border-collapse:collapse;font-family:sans-serif;font-size:.9rem'>"
            f"<tr><td style='padding:6px;font-weight:bold'>Cliente</td><td style='padding:6px'>{nome}</td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>E-mail</td><td style='padding:6px'>{email_cliente}</td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>Usuário cPanel</td><td style='padding:6px'><code>{username}</code></td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>Domínio</td><td style='padding:6px'>{domain}</td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>Plano</td><td style='padding:6px'>{plano}</td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>Servidor WHM</td><td style='padding:6px'>{WHM_HOST}</td></tr>"
            f"<tr><td style='padding:6px;font-weight:bold'>Protocolo</td><td style='padding:6px'>{protocolo}</td></tr>"
            f"</table>",
        )

    except Exception as exc:
        _atualizar_status(session_stripe, "erro", str(exc))
        print(f"[provisioner] ERRO ao provisionar {domain}: {exc}")
        _slack(
            f":x: *ERRO no provisionamento cPanel*\n"
            f"Cliente: {nome} ({email_cliente}) | Domínio: `{domain}` | Plano: {plano}\n"
            f"Erro: `{exc}`\n"
            f"Ação: provisionar manualmente no WHM."
        )
        _email_interno(
            f"[Hostweb] ❌ ERRO provisionamento: {domain}",
            f"<p style='color:red'><strong>Falha ao provisionar conta cPanel.</strong></p>"
            f"<p>Cliente: {nome} ({email_cliente})</p>"
            f"<p>Domínio: {domain} | Plano: {plano}</p>"
            f"<p>Erro: <code>{exc}</code></p>"
            f"<p style='color:#e8001c'><strong>Ação: provisionar manualmente no WHM.</strong></p>",
        )


def provisionar_async(session_stripe, meta, email_cliente):
    """Executa provisionar() em thread daemon para não bloquear o webhook Stripe."""
    t = threading.Thread(
        target=provisionar,
        args=(session_stripe, meta, email_cliente),
        daemon=True,
    )
    t.start()
