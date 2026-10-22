"""Armazenamento de imagens do Django no ImageKit."""

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
        path = quote(str(name).lstrip("/"), safe="/")
        return f"{self.endpoint}/{path}"

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
            raise ValueError("Modo de leitura inválido.")

        with urlopen(self.url(name), timeout=30) as response:
            content = response.read()

        return File(io.BytesIO(content), name=name)

    def _save(self, name, content):
        path = PurePosixPath(str(name))

        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.name
        ):
            raise ValueError("Caminho de imagem inválido.")

        folder = (
            "/"
            if str(path.parent) == "."
            else f"/{path.parent}"
        )

        filename = path.name
        boundary = uuid.uuid4().hex

        fields = {
            "fileName": filename,
            "folder": folder,
            "useUniqueFileName": "false",
            "overwriteFile": "false",
            "isPrivateFile": "false",
        }

        parts = []

        for key, value in fields.items():
            parts.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode()
            )

        content.seek(0)

        mime = (
            mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        parts.extend(
            [
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; '
                    f'name="file"; filename="{filename}"\r\n'
                    f"Content-Type: {mime}\r\n\r\n"
                ).encode(),
                content.read(),
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )

        auth = base64.b64encode(
            f"{self.private_key}:".encode()
        ).decode()

        request = Request(
            self.upload_url,
            data=b"".join(parts),
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": (
                    f"multipart/form-data; boundary={boundary}"
                ),
            },
            method="POST",
        )

        with urlopen(request, timeout=120) as response:
            result = json.load(response)

        remote_path = result["filePath"].lstrip("/")

        if remote_path != str(path):
            raise ValueError(
                "O ImageKit retornou um caminho inesperado."
            )

        return remote_path