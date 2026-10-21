import argparse
import base64
import json
import mimetypes
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from decouple import AutoConfig

BASE_DIR = Path(__file__).resolve().parent
config = AutoConfig(search_path=BASE_DIR)

ZIP_PATH = Path.home() / "Downloads" / "obbbzrboaegstiysddnh.storage.zip"
ZIP_PREFIX = "obbbzrboaegstiysddnh/produtos/"
LOG_PATH = BASE_DIR / "imagekit_uploads.jsonl"

API_URL = "https://upload.imagekit.io/api/v1/files/upload"
PRIVATE_KEY = config("IMAGEKIT_PRIVATE_KEY", default="")


def listar_imagens(arquivo):
    imagens = []

    for item in arquivo.infolist():
        if item.is_dir() or not item.filename.startswith(ZIP_PREFIX):
            continue

        caminho = item.filename.removeprefix(ZIP_PREFIX)
        partes = PurePosixPath(caminho).parts

        if not partes or ".." in partes:
            raise ValueError(f"Caminho inválido: {item.filename}")

        imagens.append((item, caminho))

    return imagens


def arquivos_enviados():
    if not LOG_PATH.exists():
        return set()

    enviados = set()

    for linha in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            registro = json.loads(linha)
            if registro.get("status") == "ok":
                enviados.add(registro["caminho"])

    return enviados


def enviar_imagem(nome, pasta, conteudo):
    boundary = uuid.uuid4().hex

    campos = {
        "fileName": nome,
        "folder": pasta,
        "useUniqueFileName": "false",
        "overwriteFile": "false",
        "isPrivateFile": "false",
    }

    partes = []

    for chave, valor in campos.items():
        partes.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{chave}"\r\n\r\n'
            f"{valor}\r\n".encode()
        )

    mime = mimetypes.guess_type(nome)[0] or "application/octet-stream"

    partes.extend([
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{nome}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode(),
        conteudo,
        f"\r\n--{boundary}--\r\n".encode(),
    ])

    autenticacao = base64.b64encode(
        f"{PRIVATE_KEY}:".encode()
    ).decode()

    requisicao = Request(
        API_URL,
        data=b"".join(partes),
        headers={
            "Authorization": f"Basic {autenticacao}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    with urlopen(requisicao, timeout=120) as resposta:
        return json.load(resposta)


def registrar(caminho, resultado):
    with LOG_PATH.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps({
            "status": "ok",
            "caminho": caminho,
            "url": resultado["url"],
            "file_id": resultado["fileId"],
        }, ensure_ascii=False) + "\n")


def executar(upload=False):
    if not ZIP_PATH.is_file():
        raise FileNotFoundError(f"ZIP não encontrado: {ZIP_PATH}")

    if upload and not PRIVATE_KEY.startswith("private_"):
        raise ValueError("IMAGEKIT_PRIVATE_KEY não configurada.")

    with zipfile.ZipFile(ZIP_PATH) as arquivo:
        imagens = listar_imagens(arquivo)

        print(f"Imagens encontradas: {len(imagens)}")
        print(f"Modo: {'UPLOAD' if upload else 'VERIFICAÇÃO'}")

        if not upload:
            print("Nenhum arquivo será enviado.")
            for _, caminho in imagens[:10]:
                print(caminho)
            return

        enviados = arquivos_enviados()
        sucesso = 0
        erros = 0

        for indice, (item, caminho) in enumerate(imagens, 1):
            if caminho in enviados:
                continue

            partes = PurePosixPath(caminho)
            nome = partes.name
            pasta = "/" + "/".join(partes.parts[:-1])

            try:
                conteudo = arquivo.read(item)
                resultado = enviar_imagem(nome, pasta, conteudo)

                caminho_remoto = resultado.get("filePath", "").lstrip("/")

                if caminho_remoto != caminho:
                    raise ValueError("Caminho remoto diferente do original.")

                registrar(caminho, resultado)
                sucesso += 1

                print(f"[{indice}/{len(imagens)}] OK: {caminho}")

            except (HTTPError, URLError, ValueError, OSError) as erro:
                erros += 1
                print(f"[{indice}/{len(imagens)}] ERRO: {caminho}")
                print(f"Tipo: {type(erro).__name__}")

        print("\nTransferência finalizada.")
        print(f"Enviados: {sucesso}")
        print(f"Erros: {erros}")
        print(f"Anteriormente enviados: {len(enviados)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Autoriza o envio das imagens ao ImageKit.",
    )

    argumentos = parser.parse_args()
    executar(upload=argumentos.upload)