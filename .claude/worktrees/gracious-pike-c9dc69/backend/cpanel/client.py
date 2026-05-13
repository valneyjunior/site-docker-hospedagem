"""
cpanel/client.py — Wrapper para WHM JSON API v1.

Autenticação via API Token (header Authorization: whm USER:TOKEN).
SSL verify desativado por padrão pois servidores WHM frequentemente usam
certificados autoassinados; configure WHM_VERIFY_SSL=true em produção com cert válido.
"""
import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WHM_HOST   = os.getenv("WHM_HOST", "")
WHM_PORT   = int(os.getenv("WHM_PORT", "2087"))
WHM_USER   = os.getenv("WHM_USER", "root")
WHM_TOKEN  = os.getenv("WHM_TOKEN", "")
WHM_SSL    = os.getenv("WHM_VERIFY_SSL", "false").lower() == "true"


def _base_url():
    return f"https://{WHM_HOST}:{WHM_PORT}/json-api"


def _headers():
    return {"Authorization": f"whm {WHM_USER}:{WHM_TOKEN}"}


def whm_post(function, params):
    """Chama WHM JSON API v1 via POST. Levanta RuntimeError em caso de falha."""
    if not WHM_HOST or not WHM_TOKEN:
        raise RuntimeError("WHM não configurado: defina WHM_HOST e WHM_TOKEN.")
    url  = f"{_base_url()}/{function}"
    resp = requests.post(
        url,
        headers=_headers(),
        data=params,
        verify=WHM_SSL,
        timeout=30,
    )
    resp.raise_for_status()
    data   = resp.json()
    result = data.get("metadata", {}).get("result", data.get("result", "1"))
    if str(result) != "1":
        reason = (
            data.get("metadata", {}).get("reason")
            or data.get("data", {}).get("reason")
            or str(data)
        )
        raise RuntimeError(f"WHM API error [{function}]: {reason}")
    return data


def criar_conta_cpanel(username, domain, password, package, email_contato):
    """Cria conta cPanel via WHM createacct."""
    return whm_post("createacct", {
        "username":     username,
        "domain":       domain,
        "password":     password,
        "plan":         package,
        "contactemail": email_contato,
        "reseller":     0,
        "ip":           "n",
        "cgi":          1,
        "frontpage":    0,
        "hasshell":     0,
    })


def criar_pacote_whm(name, quota, bwlimit, maxaddon, maxpop, maxsql, maxftp):
    """Cria pacote de hospedagem no WHM (addpkg).

    Passe 0 ou 'unlimited' para recursos ilimitados.
    """
    return whm_post("addpkg", {
        "name":     name,
        "quota":    quota,
        "bwlimit":  bwlimit,
        "maxaddon": maxaddon,
        "maxpop":   maxpop,
        "maxsql":   maxsql,
        "maxftp":   maxftp,
        "maxsub":   "unlimited",
        "maxpark":  "unlimited",
        "cgi":      1,
        "frontpage": 0,
        "hasshell": 0,
    })


def listar_pacotes_whm():
    """Retorna pacotes existentes no WHM."""
    return whm_post("listpkgs", {})
