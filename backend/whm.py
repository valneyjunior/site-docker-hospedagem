"""
whm.py — Provisionamento automático de contas cPanel via WHM JSON API.
"""
import os, re, secrets, string, unicodedata, requests
from dotenv import load_dotenv

load_dotenv()

WHM_HOST      = os.getenv("WHM_HOST", "")
WHM_API_TOKEN = os.getenv("WHM_API_TOKEN", "")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _whm_headers() -> dict:
    return {"Authorization": f"whm root:{WHM_API_TOKEN}"}


def _normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return re.sub(r"[^a-z]", "", nfkd.encode("ascii", "ignore").decode().lower())


def gerar_username(nome: str) -> str:
    """Primeiras 5 letras do nome + 3 dígitos aleatórios (max 8 chars, padrão WHM)."""
    letras  = _normalizar(nome.replace(" ", ""))[:5] or "hw"
    digitos = "".join(secrets.choice(string.digits) for _ in range(3))
    return letras + digitos


def gerar_senha(comprimento: int = 16) -> str:
    """Senha aleatória segura: maiúsculas, minúsculas, números e símbolos."""
    alfabeto = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(comprimento))
        if (any(c.isupper() for c in senha)
                and any(c.islower() for c in senha)
                and any(c.isdigit() for c in senha)
                and any(c in "!@#$%&*" for c in senha)):
            return senha


def criar_conta_cpanel(dominio: str, email: str, nome: str,
                       whm_package: str) -> tuple[str | None, str | None, bool, str]:
    """
    Cria conta cPanel via WHM JSON API.
    Retorna (username, senha, sucesso, mensagem).
    """
    if not WHM_HOST or not WHM_API_TOKEN:
        return None, None, False, "WHM_HOST ou WHM_API_TOKEN não configurado"

    username = gerar_username(nome)
    senha    = gerar_senha()

    try:
        resp = requests.get(
            f"https://{WHM_HOST}:2087/json-api/createacct",
            headers=_whm_headers(),
            params={
                "username":     username,
                "domain":       dominio,
                "password":     senha,
                "contactemail": email,
                "plan":         whm_package,
                "reseller":     0,
            },
            verify=False,
            timeout=30,
        )
        resp.raise_for_status()
        resultado = resp.json().get("result", [{}])[0]
        if resultado.get("status") == 1:
            return username, senha, True, resultado.get("statusmsg", "Conta criada")
        return None, None, False, resultado.get("statusmsg", "Erro desconhecido no WHM")
    except Exception as exc:
        return None, None, False, str(exc)


def suspender_conta(username: str, razao: str = "inadimplencia") -> bool:
    """Suspende uma conta cPanel (usado em caso de inadimplência)."""
    if not WHM_HOST or not WHM_API_TOKEN:
        return False
    try:
        resp = requests.get(
            f"https://{WHM_HOST}:2087/json-api/suspendacct",
            headers=_whm_headers(),
            params={"user": username, "reason": razao},
            verify=False,
            timeout=15,
        )
        return resp.json().get("result", [{}])[0].get("status") == 1
    except Exception:
        return False


def reativar_conta(username: str) -> bool:
    """Reativa conta cPanel suspensa."""
    if not WHM_HOST or not WHM_API_TOKEN:
        return False
    try:
        resp = requests.get(
            f"https://{WHM_HOST}:2087/json-api/unsuspendacct",
            headers=_whm_headers(),
            params={"user": username},
            verify=False,
            timeout=15,
        )
        return resp.json().get("result", [{}])[0].get("status") == 1
    except Exception:
        return False
