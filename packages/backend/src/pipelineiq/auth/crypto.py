import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from pipelineiq.config import Settings


class SecretCipher:
    """Encrypt secrets before persistence using Fernet authenticated encryption."""

    def __init__(self, settings: Settings) -> None:
        if settings.ENCRYPTION_KEY:
            key = settings.ENCRYPTION_KEY.encode()
        else:
            digest = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
            key = base64.urlsafe_b64encode(digest)
        self._cipher = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt stored secret") from exc
