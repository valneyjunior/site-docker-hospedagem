import re
import requests as http
from flask import Blueprint, render_template, request, jsonify

pages_bp = Blueprint("pages", __name__)

# RDAP endpoints por TLD
RDAP_ENDPOINTS = {
    "com.br":  "https://rdap.registro.br/domain/{}",
    "net.br":  "https://rdap.registro.br/domain/{}",
    "org.br":  "https://rdap.registro.br/domain/{}",
    "com":     "https://rdap.verisign.com/com/v1/domain/{}",
    "net":     "https://rdap.verisign.com/net/v1/domain/{}",
    "org":     "https://rdap.publicinterestregistry.org/rdap/domain/{}",
}

PRECO_DOMINIO = {
    "com.br": "R$ 39,90/ano",
    "net.br": "R$ 39,90/ano",
    "org.br": "R$ 39,90/ano",
    "com":    "R$ 59,90/ano",
    "net":    "R$ 49,90/ano",
    "org":    "R$ 49,90/ano",
}

PLAN_ID_DOMINIO = {
    "com.br": "dominio_com_br",
    "net.br": "dominio_net_br",
    "org.br": "dominio_org_br",
    "com":    "dominio_com",
    "net":    "dominio_net",
    "org":    "dominio_org",
}

def _check_rdap(fqdn, tld):
    url = RDAP_ENDPOINTS.get(tld, "").format(fqdn)
    if not url:
        return None
    try:
        r = http.get(url, timeout=6, headers={"Accept": "application/json"})
        if r.status_code == 404:
            return True   # disponível
        if r.status_code == 200:
            return False  # registrado
    except Exception:
        pass
    return None  # indeterminado

@pages_bp.route("/verificar-dominio")
def verificar_dominio():
    nome = request.args.get("nome", "").strip().lower()
    extensoes = request.args.getlist("ext") or list(RDAP_ENDPOINTS.keys())

    # valida nome: apenas letras, números e hífen, sem ponto
    nome_limpo = re.sub(r"[^a-z0-9\-]", "", nome.split(".")[0])
    if not nome_limpo or len(nome_limpo) < 2:
        return jsonify({"erro": "Nome de domínio inválido."}), 400

    resultados = []
    for ext in extensoes:
        if ext not in RDAP_ENDPOINTS:
            continue
        fqdn = f"{nome_limpo}.{ext}"
        status = _check_rdap(fqdn, ext)
        resultados.append({
            "dominio":    fqdn,
            "tld":        ext,
            "disponivel": status,
            "preco":      PRECO_DOMINIO.get(ext, "—"),
            "plan_id":    PLAN_ID_DOMINIO.get(ext, ""),
        })

    return jsonify({"nome": nome_limpo, "resultados": resultados})


@pages_bp.route("/")
def home():
    return render_template("home.html")


@pages_bp.route("/hospedagem-sites")
def hospedagem_sites():
    return render_template("hospedagem_sites.html")


@pages_bp.route("/hospedagem-email")
def hospedagem_email():
    return render_template("hospedagem_email.html")


@pages_bp.route("/zoho")
def zoho():
    return render_template("zoho.html")


@pages_bp.route("/dominios")
def dominios():
    return render_template("dominios.html")


@pages_bp.route("/sucesso")
def sucesso():
    return render_template("sucesso.html")


@pages_bp.route("/termos")
def termos():
    return render_template("termos.html")
