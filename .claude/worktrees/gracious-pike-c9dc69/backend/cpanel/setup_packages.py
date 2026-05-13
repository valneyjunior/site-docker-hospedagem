"""
cpanel/setup_packages.py — Script one-time para criar os pacotes WHM.

Execute uma vez antes de ativar o provisionamento automático:
    cd backend && python -m cpanel.setup_packages

Verifica quais pacotes já existem e cria apenas os ausentes.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from cpanel.client import criar_pacote_whm, listar_pacotes_whm
from cpanel.packages import PACKAGE_SPECS


def main():
    print("=== Setup de pacotes WHM — Hostweb ===\n")

    print("Consultando pacotes existentes...")
    try:
        resp     = listar_pacotes_whm()
        existing = {
            pkg.get("name", "")
            for pkg in resp.get("data", {}).get("pkg", [])
        }
        print(f"Pacotes existentes: {existing or '(nenhum)'}\n")
    except Exception as exc:
        print(f"ERRO ao listar pacotes: {exc}")
        sys.exit(1)

    for pkg_name, specs in PACKAGE_SPECS.items():
        if pkg_name in existing:
            print(f"[OK]  {pkg_name} — já existe, pulando.")
            continue
        try:
            criar_pacote_whm(
                name     = pkg_name,
                quota    = specs["quota"],
                bwlimit  = specs["bwlimit"],
                maxaddon = specs["maxaddon"],
                maxpop   = specs["maxpop"],
                maxsql   = specs["maxsql"],
                maxftp   = specs["maxftp"],
            )
            print(f"[CRIADO] {pkg_name}")
        except Exception as exc:
            print(f"[ERRO]  {pkg_name}: {exc}")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
