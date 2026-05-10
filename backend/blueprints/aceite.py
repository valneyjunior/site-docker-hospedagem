"""
blueprints/aceite.py — Aceite digital com validade jurídica.

Bases legais:
  - Marco Civil da Internet (Lei 12.965/2014) art. 7º e 10º
  - LGPD (Lei 13.709/2018) — consentimento explícito e registrado
  - Código Civil (Lei 10.406/2002) art. 107
  - CDC (Lei 8.078/1990)
  - MP 2.200-2/2001 e Lei 14.063/2020 — validade de assinaturas eletrônicas

Rotas:
  GET  /aceite/           — página de aceite
  POST /aceite/confirmar  — registra aceite no PostgreSQL, envia e-mail, cria sessão Stripe
  POST /aceite/gerar      — gera PDF de aceite (download direto)
  GET  /aceite/verificar  — consulta protocolo no banco
"""

from flask import Blueprint, request, jsonify, send_file, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import qrcode, hashlib, uuid, os, io, stripe, psycopg2, psycopg2.extras
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

from utils import PLANS, smtp_conn, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_REPLY, get_db

aceite_bp = Blueprint(
    "aceite",
    __name__,
    template_folder="../templates",
    static_folder="../static",
    url_prefix="/aceite"
)

VERIFICACAO_BASE_URL = os.getenv("VERIFICACAO_URL", "https://hostweb.com.br/verificar-aceite")
VERSAO_TERMOS        = "v1.0-2026"

# ── Texto dos termos (SHA-256 garante integridade após aceite) ───────────────
TERMO_TEXTO = """
TERMO DE ACEITE DIGITAL – SERVIÇOS HOSTWEB
Hospedagem cPanel (Compartilhada e Dedicada) e Licenciamento Zoho
Versão v1.0-2026

IMPORTANTE: Este Termo de Aceite Digital ("Termo") regula as condições para contratação e uso dos serviços da Hostweb Data Center e Serviços LTDA EPP ("HOSTWEB"), pelo cliente ("CONTRATANTE"). Ao clicar em "Concordo e quero contratar" ou ao concluir o pagamento/contratação no portal, o CONTRATANTE declara que leu, compreendeu e concorda integralmente com este Termo.

1. OBJETO
1.1. Este Termo regula a prestação dos seguintes serviços, conforme o plano/itens contratados no ato da compra: hospedagem de sites e e-mails em ambiente cPanel (servidores compartilhados); servidores dedicados cPanel/WHM (recursos exclusivos) com serviços adicionais de administração, quando contratados; licenciamento e gestão de e-mail corporativo Zoho (revenda/parceria), quando contratado.
1.2. O escopo exato (recursos, limites, valores, periodicidade e adicionais) é aquele exibido no portal/proposta comercial na data da contratação e na fatura/ordem de serviço correspondente.

2. PLANOS, RECURSOS E LIMITES DE USO
2.1. Os recursos variam conforme o plano contratado e podem ser alterados por upgrade/downgrade, quando disponível.
2.2. Hospedagem Compartilhada: ambiente compartilhado com limitação de CPU, RAM e I/O. Backups via cPanel são funcionalidades de apoio; o CONTRATANTE permanece responsável por manter cópias próprias.
2.3. Servidores Dedicados: recursos de hardware exclusivos conforme plano contratado. O suporte técnico está disponível em horário comercial, de segunda a sexta-feira, das 8h às 18h (BRT), salvo acordos específicos de nível de serviço (SLA) distintos formalizados em contrato.

3. SERVIÇOS ZOHO (REVENDA/PARCERIA)
3.1. A Hostweb atua como revendedora/parceira. O serviço Zoho é prestado pela Zoho Corporation e está sujeito às políticas e limitações técnicas do fornecedor.
3.2. O armazenamento é por usuário/caixa postal conforme plano Zoho adquirido.

4. DISPONIBILIDADE (SLA)
4.1. Hospedagem Compartilhada: SLA de referência de 99,5% ao mês. Servidores Dedicados administrados pela Hostweb: SLA de referência de 99,9% ao mês.
4.2. Em caso de indisponibilidade superior ao SLA, o CONTRATANTE poderá solicitar crédito proporcional mediante abertura de chamado em até 7 (sete) dias após o evento.
4.3. Não se consideram indisponibilidades: manutenções programadas, falhas de terceiros, ataques DDoS fora da capacidade de mitigação contratada, mau uso e incidentes fora do controle razoável da Hostweb.

5. PAGAMENTO, RENOVAÇÃO, SUSPENSÃO E EXCLUSÃO DE DADOS
5.1. Os serviços são pré-pagos, com renovação conforme periodicidade escolhida (mensal/anual), cobrados via cartão de crédito/débito pela plataforma Stripe.
5.2. Em caso de atraso: após 3 dias do vencimento, o serviço poderá ser suspenso; após 15 dias, o serviço poderá ser cancelado e os dados poderão ser removidos.
5.3. Antes de qualquer remoção definitiva de dados, a Hostweb enviará comunicação ao e-mail cadastrado com antecedência mínima de 7 (sete) dias.
5.4. Cancelamentos de planos anuais antes do término podem gerar cobrança proporcional ou perda do desconto aplicado.

6. USOS PROIBIDOS E ABUSO
6.1. É proibido utilizar a infraestrutura Hostweb para: envio de spam, hospedagem de conteúdo ilegal, pirataria, phishing, malware, ataques, varreduras (scans) ou tráfego malicioso.
6.2. A Hostweb poderá suspender imediatamente o serviço em caso de risco à infraestrutura ou a terceiros.

7. SEGURANÇA E RESPONSABILIDADES DO CONTRATANTE
7.1. O CONTRATANTE é responsável por: manter senhas fortes, guardar credenciais e controlar acessos; manter aplicações atualizadas; e pelo conteúdo hospedado e comunicações enviadas.
7.2. A Hostweb não se responsabiliza por incidentes decorrentes de má configuração, falhas de aplicações do CONTRATANTE ou senhas comprometidas.

8. PROTEÇÃO DE DADOS (LGPD)
8.1. As partes comprometem-se a cumprir a Lei Geral de Proteção de Dados (Lei nº 13.709/2018 – LGPD).
8.2. Em regra, o CONTRATANTE é o Controlador dos dados pessoais tratados em seus sites/e-mails, e a Hostweb atua como Operadora.
8.3. Havendo incidente relevante com impacto em dados pessoais, a Hostweb comunicará o CONTRATANTE em prazo razoável.

9. RESCISÃO E PORTABILIDADE
9.1. O CONTRATANTE pode solicitar cancelamento a qualquer tempo, observadas eventuais regras de fidelidade.
9.2. Mediante solicitação e estando adimplente, o CONTRATANTE poderá solicitar exportação de dados antes do encerramento.

10. SEGURANÇA DA INFORMAÇÃO (ISO 27001)
10.1. A Hostweb opera conforme os requisitos da norma ABNT NBR ISO/IEC 27001, mantendo um Sistema de Gestão de Segurança da Informação (SGSI) certificado, com controles aplicados à confidencialidade, integridade e disponibilidade das informações.
10.2. Os controles de segurança abrangem: gestão de ativos, controle de acesso lógico e físico, criptografia de dados em trânsito e em repouso, gestão de vulnerabilidades, monitoramento contínuo de eventos e procedimentos formalizados de resposta a incidentes.
10.3. Incidentes de segurança que possam afetar os dados do CONTRATANTE serão notificados em até 72 horas a partir da ciência do evento, conforme exigências da LGPD (Lei 13.709/2018) e boas práticas da ISO 27001.
10.4. O CONTRATANTE compromete-se a não realizar ações que comprometam a integridade, a confidencialidade ou a disponibilidade dos sistemas e da infraestrutura compartilhada, sob pena de suspensão imediata e responsabilização civil e criminal.
10.5. A Hostweb realiza auditorias internas e externas periódicas como parte do ciclo de melhoria contínua do SGSI, assegurando a conformidade permanente com os controles da norma.

11. DISPOSIÇÕES GERAIS
11.1. A Hostweb poderá atualizar este Termo para adequação técnica/jurídica, publicando versão atualizada no portal com indicação da nova versão.
11.2. Considera-se válido o e-mail cadastrado no portal para envio de notificações e avisos.
11.3. Foro: Comarca de Fortaleza/CE, com renúncia a qualquer outro, para dirimir eventuais controvérsias.

Registro do aceite: Ao aceitar digitalmente, ficam registrados data/hora UTC (ISO 8601), IP, User-Agent, CPF/CNPJ, identificador do pedido e e-mail do CONTRATANTE, formando prova eletrônica do aceite nos termos da MP 2.200-2/2001, Lei 14.063/2020, Marco Civil da Internet (Lei 12.965/2014) e LGPD (Lei 13.709/2018).
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def gerar_hash_termo():
    return hashlib.sha256(TERMO_TEXTO.encode("utf-8")).hexdigest()


def _capturar_metadados():
    """Coleta IP, User-Agent, timestamps UTC/BRT, protocolo e hash do termo."""
    ip_raw = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    return {
        "ip":            ip_raw.split(",")[0].strip(),
        "user_agent":    request.headers.get("User-Agent", "desconhecido")[:512],
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp_brt": datetime.now(pytz.timezone("America/Fortaleza")).strftime("%d/%m/%Y %H:%M:%S BRT"),
        "protocolo":     "HW-" + uuid.uuid4().hex[:10].upper(),
        "hash_termo":    gerar_hash_termo(),
    }


def _salvar_aceite(protocolo, nome, email, cpf_cnpj, empresa, plano, plan_id,
                   ip, user_agent, timestamp_utc, timestamp_brt, hash_termo):
    """Persiste aceite no PostgreSQL."""
    conn = get_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO aceites
                        (protocolo, nome, email, cpf_cnpj, empresa, plano, plan_id,
                         ip, user_agent, timestamp_utc, timestamp_brt,
                         versao_termos, hash_sha256)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (protocolo, nome, email, cpf_cnpj, empresa, plano, plan_id,
                      ip, user_agent, timestamp_utc, timestamp_brt,
                      VERSAO_TERMOS, hash_termo))
    finally:
        conn.close()


def enviar_email_confirmacao(email_cliente, nome, plano, protocolo,
                              timestamp_brt, timestamp_utc, ip, versao_termos):
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP não configurado — e-mail de confirmação não enviado.")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"]  = f"Confirmação de Aceite Digital — Hostweb | Protocolo {protocolo}"
    msg["From"]     = f"Hostweb <{EMAIL_FROM}>"
    msg["To"]       = email_cliente
    msg["Reply-To"] = EMAIL_REPLY

    html = f"""
<html><body style="font-family:Segoe UI,sans-serif;background:#f5f5f7;padding:32px">
<div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;
  box-shadow:0 4px 24px rgba(0,0,0,.08)">
  <div style="background:linear-gradient(135deg,#e8001c,#6b0fa8);padding:32px;text-align:center;
    border-radius:16px 16px 0 0">
    <img src="https://hostweb.com.br/wp-content/uploads/2021/03/Logo-Hostweb.png"
      alt="Hostweb" style="height:48px;filter:brightness(0) invert(1)">
    <h1 style="color:#fff;margin:16px 0 0;font-size:1.3rem">Aceite Digital Registrado</h1>
    <p style="color:rgba(255,255,255,.8);font-size:.85rem;margin:6px 0 0">
      Registro eletrônico com validade jurídica</p>
  </div>
  <div style="padding:32px">
    <p style="color:#333">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#555;line-height:1.7">
      Seu aceite digital foi registrado com sucesso e possui
      <strong>validade jurídica</strong> conforme MP 2.200-2/2001,
      Lei 14.063/2020, Marco Civil da Internet e LGPD.
    </p>
    <div style="background:#f9f5ff;border:1px solid #d8b4fe;border-radius:10px;
      padding:20px;margin:20px 0">
      <h3 style="color:#6b0fa8;margin:0 0 14px;font-size:.95rem">
        🔐 Dados do Aceite Digital
      </h3>
      <table style="width:100%;font-size:.85rem;border-collapse:collapse">
        <tr style="background:#f0e6ff">
          <td style="padding:8px;font-weight:700;color:#6b0fa8;width:40%">Protocolo</td>
          <td style="padding:8px;font-family:monospace;color:#e8001c;font-weight:700">{protocolo}</td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Plano contratado</td>
          <td style="padding:8px">{plano}</td>
        </tr>
        <tr style="background:#f0e6ff">
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Data/Hora (BRT)</td>
          <td style="padding:8px">{timestamp_brt}</td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Data/Hora (UTC)</td>
          <td style="padding:8px;font-family:monospace;font-size:.8rem">{timestamp_utc}</td>
        </tr>
        <tr style="background:#f0e6ff">
          <td style="padding:8px;font-weight:700;color:#6b0fa8">IP registrado</td>
          <td style="padding:8px;font-family:monospace">{ip}</td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:700;color:#6b0fa8">Versão dos termos</td>
          <td style="padding:8px">{versao_termos}</td>
        </tr>
      </table>
    </div>
    <p style="color:#555;font-size:.85rem">
      Termos completos: <a href="https://hostweb.com.br/termos" style="color:#6b0fa8">
        hostweb.com.br/termos</a>
    </p>
    <p style="color:#555;font-size:.85rem">
      Dúvidas? 📞 (85) 3288-2062 &nbsp;|&nbsp;
      💬 <a href="https://wa.me/5585991293286" style="color:#6b0fa8">WhatsApp</a> &nbsp;|&nbsp;
      Atendimento em até <strong>4 horas úteis</strong>
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
    <p style="color:#999;font-size:.75rem;text-align:center">
      Hostweb Data Center e Serviços LTDA EPP — CNPJ 07.797.967/0001-60 — Fortaleza, CE<br>
      Validade: MP 2.200-2/2001 · Lei 14.063/2020 · LGPD
    </p>
  </div>
</div>
</body></html>
"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtp_conn() as conn:
            conn.sendmail(EMAIL_FROM, email_cliente, msg.as_string())
        print(f"E-mail confirmação enviado → {email_cliente} | {protocolo}")
    except Exception as e:
        print(f"Falha e-mail confirmação: {e}")


def gerar_qrcode_bytes(url):
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def gerar_pdf(nome, email, cpf_cnpj, empresa, plano, ip, protocolo,
              timestamp_brt, timestamp_utc, versao_termos, hash_termo):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    cor_primaria   = colors.HexColor("#e8001c")
    cor_secundaria = colors.HexColor("#6b0fa8")
    cor_cinza      = colors.HexColor("#555555")

    s_titulo    = ParagraphStyle("titulo",    parent=styles["Title"],
        fontSize=16, textColor=cor_primaria, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"],
        fontSize=10, textColor=cor_secundaria, spaceAfter=12,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_corpo     = ParagraphStyle("corpo",     parent=styles["Normal"],
        fontSize=8.5, leading=13, textColor=colors.HexColor("#333333"),
        spaceAfter=6, alignment=TA_JUSTIFY, fontName="Helvetica")
    s_secao     = ParagraphStyle("secao",     parent=styles["Normal"],
        fontSize=9.5, textColor=cor_primaria, spaceBefore=10, spaceAfter=4,
        fontName="Helvetica-Bold")
    s_rodape_titulo = ParagraphStyle("rodape_titulo", parent=styles["Normal"],
        fontSize=9, textColor=cor_primaria, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=6)
    s_rodape_item = ParagraphStyle("rodape_item", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#333333"), fontName="Helvetica",
        alignment=TA_LEFT, leading=12)
    s_hash  = ParagraphStyle("hash",  parent=styles["Normal"],
        fontSize=6.5, textColor=cor_cinza, fontName="Courier",
        alignment=TA_CENTER, spaceAfter=4)
    s_legal = ParagraphStyle("legal", parent=styles["Normal"],
        fontSize=7.5, textColor=cor_cinza, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=4)

    story = []
    story.append(Paragraph("HOSTWEB DATA CENTER", s_titulo))
    story.append(Paragraph(
        f"Termo de Aceite Digital — Serviços de Hospedagem e E-mail Corporativo ({versao_termos})",
        s_subtitulo))
    story.append(HRFlowable(width="100%", thickness=2, color=cor_primaria, spaceAfter=12))

    dados = [
        ["Protocolo:",    protocolo,           "Data/Hora (BRT):", timestamp_brt],
        ["Nome:",         nome,                "Data/Hora (UTC):", timestamp_utc],
        ["E-mail:",       email,               "CPF/CNPJ:",        cpf_cnpj],
        ["Empresa:",      empresa or "—",      "Plano:",           plano],
        ["IP de Origem:", ip,                  "Versão Termos:",   versao_termos],
        ["Foro:",         "Fortaleza/CE",       "Bases Legais:",    "MP 2.200-2/2001 · Lei 14.063/2020"],
    ]
    t = Table(dados, colWidths=[3.5*cm, 7.2*cm, 3.5*cm, 3.3*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",       (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",       (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",       (2,0), (2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",       (0,0), (-1,-1), 7.5),
        ("TEXTCOLOR",      (0,0), (0,-1),  cor_primaria),
        ("TEXTCOLOR",      (2,0), (2,-1),  cor_primaria),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#f0f0f0"), colors.white]),
        ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("PADDING",        (0,0), (-1,-1), 5),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    for linha in TERMO_TEXTO.strip().split("\n"):
        linha = linha.strip()
        if not linha:
            story.append(Spacer(1, 4)); continue
        prefixos_secao = [f"{i}." for i in range(1, 11)] + [
            "TERMO", "IMPORTANTE", "Registro", "Versão"]
        if any(linha.startswith(p) for p in prefixos_secao):
            story.append(Paragraph(linha, s_secao))
        else:
            story.append(Paragraph(linha, s_corpo))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1.5, color=cor_secundaria, spaceAfter=10))
    story.append(Paragraph("✓  REGISTRO DE ACEITE DIGITAL — PROVA ELETRÔNICA", s_rodape_titulo))

    url_ver = f"{VERIFICACAO_BASE_URL}?protocolo={protocolo}"
    qr_img  = RLImage(gerar_qrcode_bytes(url_ver), width=2.5*cm, height=2.5*cm)

    rodape_dados = [
        [Paragraph(f"<b>Protocolo:</b> {protocolo}", s_rodape_item)],
        [Paragraph(f"<b>Data/Hora (BRT):</b> {timestamp_brt}", s_rodape_item)],
        [Paragraph(f"<b>Data/Hora (UTC/ISO 8601):</b> {timestamp_utc}", s_rodape_item)],
        [Paragraph(f"<b>E-mail:</b> {email}", s_rodape_item)],
        [Paragraph(f"<b>CPF/CNPJ:</b> {cpf_cnpj}", s_rodape_item)],
        [Paragraph(f"<b>IP de Origem:</b> {ip}", s_rodape_item)],
        [Paragraph(f"<b>Plano Contratado:</b> {plano}", s_rodape_item)],
        [Paragraph(f"<b>Versão dos Termos:</b> {versao_termos}", s_rodape_item)],
        [Paragraph(
            "<b>Validade Legal:</b> MP 2.200-2/2001 · Lei 14.063/2020 · LGPD · Marco Civil",
            s_rodape_item)],
    ]
    tabela_rodape = Table(
        [[Table(rodape_dados, colWidths=[12.5*cm]), qr_img]],
        colWidths=[13*cm, 3.5*cm]
    )
    tabela_rodape.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f5f5f5")),
        ("BOX",        (0,0), (-1,-1), 1, cor_secundaria),
        ("PADDING",    (0,0), (-1,-1), 8),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tabela_rodape)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"SHA-256 do Termo ({versao_termos}): {hash_termo}", s_hash))
    story.append(Paragraph(
        "Este documento possui validade jurídica nos termos da MP 2.200-2/2001 e Lei 14.063/2020. "
        "O aceite eletrônico registrado acima equivale à assinatura do CONTRATANTE. "
        "Bases legais adicionais: Marco Civil (Lei 12.965/2014), LGPD (Lei 13.709/2018), "
        "Código Civil art. 107 e CDC (Lei 8.078/1990).",
        s_legal
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ── Rotas ─────────────────────────────────────────────────────────────────────

@aceite_bp.route("/")
def pagina_aceite():
    plan_id  = request.args.get("plan_id", "").strip()
    email    = request.args.get("email",   "").strip()
    nome     = request.args.get("nome",    "").strip()
    empresa  = request.args.get("empresa", "").strip()
    plan_info = PLANS.get(plan_id, {})
    plan_nome = plan_info.get("name", plan_id.replace("_", " ").title() if plan_id else "")
    return render_template(
        "aceite.html",
        plan_id=plan_id,
        plan_nome=plan_nome,
        email=email,
        nome=nome,
        empresa=empresa,
        versao_termos=VERSAO_TERMOS,
        hash_termos=gerar_hash_termo(),
    )


@aceite_bp.route("/confirmar", methods=["POST"])
def confirmar_aceite():
    """
    Fluxo principal de contratação:
    1. Valida campos e checkboxes
    2. Captura metadados (IP, User-Agent, timestamps)
    3. Persiste no PostgreSQL
    4. Envia e-mail de confirmação (LGPD art. 8º)
    5. Cria sessão Stripe e retorna a URL de checkout
    """
    data     = request.get_json(force=True)
    nome     = (data.get("nome",     "") or "").strip()
    email    = (data.get("email",    "") or "").strip()
    cpf_cnpj = (data.get("cpf_cnpj", "") or "").strip()
    empresa  = (data.get("empresa",  "") or "").strip()
    plan_id  = (data.get("plan_id",  "") or "").strip()
    aceito   = data.get("aceito", False)
    lgpd     = data.get("lgpd",   False)

    if not all([nome, email, cpf_cnpj, plan_id, aceito, lgpd]):
        return jsonify({"erro": "Preencha todos os campos obrigatórios e aceite os termos."}), 400

    plan_info = PLANS.get(plan_id)
    if not plan_info:
        return jsonify({"erro": f"Plano inválido: {plan_id}"}), 400

    plano_nome = plan_info["name"]
    price_id   = plan_info["price_id"]

    meta = _capturar_metadados()
    _salvar_aceite(
        meta["protocolo"], nome, email, cpf_cnpj, empresa, plano_nome, plan_id,
        meta["ip"], meta["user_agent"],
        meta["timestamp_utc"], meta["timestamp_brt"], meta["hash_termo"],
    )
    enviar_email_confirmacao(
        email, nome, plano_nome, meta["protocolo"],
        meta["timestamp_brt"], meta["timestamp_utc"], meta["ip"], VERSAO_TERMOS,
    )

    success_url = os.getenv(
        "SUCCESS_URL",
        "http://localhost/sucesso?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = os.getenv("CANCEL_URL", "http://localhost/?cancelado=1")

    stripe_mode = plan_info.get("mode", "subscription")
    try:
        session = stripe.checkout.Session.create(
            mode=stripe_mode,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email,
            metadata={
                "plan_id":          plan_id,
                "plan_name":        plano_nome,
                "nome":             nome,
                "empresa":          empresa,
                "protocolo_aceite": meta["protocolo"],
            },
        )
    except Exception as e:
        return jsonify({"erro": f"Erro ao criar sessão de pagamento: {e}"}), 500

    return jsonify({
        "ok":        True,
        "protocolo": meta["protocolo"],
        "url":       session.url,
    })


@aceite_bp.route("/gerar", methods=["POST"])
def gerar_aceite():
    """Gera e retorna PDF de aceite para download (uso interno/admin)."""
    data     = request.get_json(force=True)
    nome     = (data.get("nome",     "") or "").strip()
    email    = (data.get("email",    "") or "").strip()
    cpf_cnpj = (data.get("cpf_cnpj", "") or "").strip()
    empresa  = (data.get("empresa",  "") or "").strip()
    plano    = (data.get("plano",    "") or "").strip()
    aceito   = data.get("aceito", False)

    if not all([nome, email, plano, aceito]):
        return jsonify({"erro": "Preencha todos os campos obrigatórios e aceite os termos."}), 400

    meta = _capturar_metadados()
    _salvar_aceite(
        meta["protocolo"], nome, email, cpf_cnpj, empresa, plano, "",
        meta["ip"], meta["user_agent"],
        meta["timestamp_utc"], meta["timestamp_brt"], meta["hash_termo"],
    )
    pdf_buf = gerar_pdf(
        nome, email, cpf_cnpj, empresa, plano, meta["ip"],
        meta["protocolo"], meta["timestamp_brt"], meta["timestamp_utc"],
        VERSAO_TERMOS, meta["hash_termo"],
    )
    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Hostweb_Aceite_{meta['protocolo']}.pdf",
    )


@aceite_bp.route("/verificar", methods=["GET"])
def verificar_aceite():
    """Consulta protocolo de aceite no PostgreSQL."""
    protocolo = request.args.get("protocolo", "").strip().upper()
    if not protocolo:
        return jsonify({"erro": "Protocolo não informado."}), 400

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM aceites WHERE protocolo = %s", (protocolo,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({"valido": False, "mensagem": "Protocolo não encontrado."}), 404

    data = dict(row)
    for k, v in data.items():
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
    return jsonify({"valido": True, **data})
