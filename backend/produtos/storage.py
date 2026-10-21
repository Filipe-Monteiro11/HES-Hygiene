    
import base64
import io
import json
import mimetypes
import uuid
from pathlib import PurePosixPath
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class ImageKitStorage(Storage):
    upload_url = "https://upload.imagekit.io/api/v1/files/upload"

    def __init__(self):
        self.endpoint = settings.IMAGEKIT_URL_ENDPOINT.rstrip("/")
        self.private_key = settings.IMAGEKIT_PRIVATE_KEY

    def url(self, name):
        return f"{self.endpoint}/{quote(name.lstrip('/'), safe='/')}"

    def exists(self, name):
        request = Request(self.url(name), method="HEAD")

        try:
            with urlopen(request, timeout=15):
                return True
        except HTTPError as error:
            if error.code == 404:
                return False
            raise

    def _open(self, name, mode="rb"):
        if mode not in ("r", "rb"):
            raise ValueError("Modo de abertura não suportado.")

        with urlopen(self.url(name), timeout=30) as response:
            content = response.read()

        return File(io.BytesIO(content), name=name)

    def _save(self, name, content):
        caminho = PurePosixPath(name)

        if caminho.is_absolute() or ".." in caminho.parts:
            raise ValueError("Caminho de imagem inválido.")

        pasta = str(caminho.parent)
        pasta = "/" if pasta == "." else f"/{pasta}"

        boundary = uuid.uuid4().hex
        nome = caminho.name

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

        content.seek(0)

        partes.extend([
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{nome}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode(),
            content.read(),
            f"\r\n--{boundary}--\r\n".encode(),
        ])

        auth = base64.b64encode(
            f"{self.private_key}:".encode()
        ).decode()

        request = Request(
            self.upload_url,
            data=b"".join(partes),
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )

        with urlopen(request, timeout=120) as response:
            resultado = json.load(response)

        caminho_remoto = resultado["filePath"].lstrip("/")

        if caminho_remoto != name.lstrip("/"):
            raise ValueError("O ImageKit retornou um caminho diferente.")

        return caminho_remoto
