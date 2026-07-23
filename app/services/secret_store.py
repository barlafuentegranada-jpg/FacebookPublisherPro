import base64
import getpass
import hashlib
import hmac
import json
import os
import platform
from pathlib import Path


class SecretStore:
    def set_secret(self, key, value):
        raise NotImplementedError

    def get_secret(self, key):
        raise NotImplementedError

    def delete_secret(self, key):
        raise NotImplementedError


class LocalEncryptedSecretStore(SecretStore):
    """Temporary local encrypted store until OS credential integration is added."""

    def __init__(self, path=None):
        self.path = Path(path or "config/secrets.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def set_secret(self, key, value):
        data = self._read()
        data[key] = self._encrypt(value)
        self._write(data)
        return key

    def get_secret(self, key):
        data = self._read()
        payload = data.get(key)

        if not payload:
            return None

        return self._decrypt(payload)

    def delete_secret(self, key):
        data = self._read()
        data.pop(key, None)
        self._write(data)

    def _encrypt(self, value):
        salt = os.urandom(16)
        nonce = os.urandom(16)
        plain = str(value).encode("utf-8")
        cipher = self._xor(plain, salt, nonce)
        mac = hmac.new(self._key(salt), nonce + cipher, hashlib.sha256).digest()
        return {
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(cipher).decode("ascii"),
            "mac": base64.b64encode(mac).decode("ascii"),
        }

    def _decrypt(self, payload):
        salt = base64.b64decode(payload["salt"])
        nonce = base64.b64decode(payload["nonce"])
        cipher = base64.b64decode(payload["ciphertext"])
        expected = base64.b64decode(payload["mac"])
        actual = hmac.new(self._key(salt), nonce + cipher, hashlib.sha256).digest()

        if not hmac.compare_digest(expected, actual):
            raise RuntimeError("Secret integrity check failed.")

        return self._xor(cipher, salt, nonce).decode("utf-8")

    def _xor(self, data, salt, nonce):
        output = bytearray()
        counter = 0

        while len(output) < len(data):
            block = hashlib.sha256(self._key(salt) + nonce + counter.to_bytes(4, "big")).digest()
            output.extend(block)
            counter += 1

        return bytes(value ^ output[index] for index, value in enumerate(data))

    def _key(self, salt):
        material = "|".join([getpass.getuser(), platform.node(), str(self.path.resolve())]).encode("utf-8")
        return hashlib.pbkdf2_hmac("sha256", material, salt, 200000, dklen=32)

    def _read(self):
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data):
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


secret_store = LocalEncryptedSecretStore()
