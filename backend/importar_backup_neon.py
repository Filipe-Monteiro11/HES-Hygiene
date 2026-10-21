
import argparse
import gzip
import io
import re
from pathlib import Path

import django
from django.conf import settings
from django.db import connection, transaction

import os

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_neon"
django.setup()

BACKUP = (
    Path.home()
    / "Downloads"
    / "db_cluster-21-10-2026@04-45-32.backup.gz"
)

TABELAS = {
    "auth_user": 1,
    "produtos_categoria": 19,
    "produtos_subcategoria": 30,
    "produtos_produto": 287,
    "django_admin_log": 1886,
}

ORDEM = list(TABELAS)

PADRAO_COPY = re.compile(
    r"^COPY public\.([a-z_]+) \(([a-z_, ]+)\) FROM stdin;$"
)


def ler_backup():
    dados = {}
    tabela = None
    colunas = None
    linhas = []

    with gzip.open(BACKUP, "rt", encoding="utf-8") as arquivo:
        for linha in arquivo:
            if tabela is None:
                encontrado = PADRAO_COPY.match(linha.rstrip("\n"))

                if encontrado:
                    tabela, colunas = encontrado.groups()
                    linhas = []

                continue

            if linha.rstrip("\r\n") == r"\.":
                if tabela in TABELAS or tabela == "django_content_type":
                    dados[tabela] = {
                        "colunas": colunas,
                        "linhas": linhas,
                    }

                tabela = None
                colunas = None
                linhas = []
                continue

            if tabela in TABELAS or tabela == "django_content_type":
                linhas.append(linha)

    return dados


def verificar_backup(dados):
    for tabela, esperado in TABELAS.items():
        atual = len(dados.get(tabela, {}).get("linhas", []))

        if atual != esperado:
            raise RuntimeError(
                f"Backup inválido: {tabela} tem {atual} "
                f"registros; esperado: {esperado}."
            )

    if "django_content_type" not in dados:
        raise RuntimeError("Content types ausentes no backup.")


def verificar_destino(dados):
    if connection.settings_dict["NAME"] != "hes_atacado":
        raise RuntimeError("Banco de destino incorreto.")

    if not connection.settings_dict["HOST"].endswith(".neon.tech"):
        raise RuntimeError("O destino não é um servidor Neon.")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, app_label, model FROM django_content_type"
        )
        destino = {
            str(identificador): (app, modelo)
            for identificador, app, modelo in cursor.fetchall()
        }

        origem = {}

        for linha in dados["django_content_type"]["linhas"]:
            identificador, app, modelo = linha.rstrip("\n").split("\t")
            origem[identificador] = (app, modelo)

        if origem != destino:
            raise RuntimeError(
                "Os IDs de content types diferem entre os bancos. "
                "Importação interrompida para preservar o histórico."
            )

        for tabela in ORDEM:
            cursor.execute(f"SELECT COUNT(*) FROM public.{tabela}")
            quantidade = cursor.fetchone()[0]

            if quantidade:
                raise RuntimeError(
                    f"A tabela {tabela} não está vazia: "
                    f"{quantidade} registros."
                )


def importar(dados):
    with transaction.atomic():
        verificar_destino(dados)

        connection.ensure_connection()
        cursor = connection.connection.cursor()

        try:
            for tabela in ORDEM:
                registro = dados[tabela]
                conteudo = "".join(registro["linhas"])

                comando = (
                    f"COPY public.{tabela} "
                    f"({registro['colunas']}) FROM STDIN"
                )

                cursor.copy_expert(
                    comando,
                    io.StringIO(conteudo),
                )

                print(
                    f"[OK] {tabela}: "
                    f"{len(registro['linhas'])} registros"
                )

            for tabela in ORDEM:
                cursor.execute(
                    "SELECT pg_get_serial_sequence(%s, 'id')",
                    (f"public.{tabela}",),
                )
                sequencia = cursor.fetchone()[0]

                if sequencia:
                    cursor.execute(
                        f"""
                        SELECT setval(
                            %s,
                            (SELECT MAX(id) FROM public.{tabela}),
                            true
                        )
                        """,
                        (sequencia,),
                    )

            for tabela, esperado in TABELAS.items():
                cursor.execute(
                    f"SELECT COUNT(*) FROM public.{tabela}"
                )

                if cursor.fetchone()[0] != esperado:
                    raise RuntimeError(
                        f"Falha na verificação de {tabela}."
                    )

        finally:
            cursor.close()

    print("\nIMPORTAÇÃO CONCLUÍDA COM SUCESSO!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Autoriza a importação dos dados para o Neon.",
    )
    argumentos = parser.parse_args()

    if not BACKUP.is_file():
        raise FileNotFoundError(f"Backup não encontrado: {BACKUP}")

    dados = ler_backup()
    verificar_backup(dados)

    print("BACKUP VALIDADO")
    print(f"Destino: {connection.settings_dict['NAME']}")

    for tabela, quantidade in TABELAS.items():
        print(f"{tabela}: {quantidade}")

    if not argumentos.apply:
        verificar_destino(dados)
        print("\nSIMULAÇÃO APROVADA.")
        print("Nenhum registro foi importado.")
        return

    importar(dados)


if __name__ == "__main__":
    main()
