from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

class EncryptionError(Exception):
    """Exception raised for errors during token encryption/decryption operations."""
    pass

class TokenEncryptionService:
    """
    Dedicated security service handling symmetric encryption (Fernet AES-128) 
    for sensitive OAuth tokens stored at rest.
    """
    def __init__(self, key: str | None = None) -> None:
        raw_key = key or settings.OAUTH_TOKEN_ENCRYPTION_KEY
        if not raw_key:
            raise EncryptionError("OAUTH_TOKEN_ENCRYPTION_KEY is not configured in settings.")
        
        try:
            key_bytes = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key
            self.fernet = Fernet(key_bytes)
        except Exception as e:
            raise EncryptionError(f"Invalid OAUTH_TOKEN_ENCRYPTION_KEY format: {str(e)}")

    def encrypt_token(self, plaintext: str) -> str:
        """
        Encrypts a plaintext OAuth token into a URL-safe Fernet ciphertext string.
        """
        if not plaintext:
            return ""
        
        # Prevent double encryption by validating if it's already an encrypted Fernet token
        if self.is_encrypted(plaintext):
            return plaintext

        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Token encryption failed: {str(e)}")

    def decrypt_token(self, token_val: str) -> str:
        """
        Decrypts a Fernet ciphertext token back into original plaintext.
        If the value is already plaintext (not encrypted), returns it safely.
        """
        if not token_val:
            return ""

        try:
            decrypted_bytes = self.fernet.decrypt(token_val.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            # If token is not valid Fernet ciphertext, return original plaintext for backwards compatibility
            return token_val
        except Exception as e:
            raise EncryptionError(f"Token decryption failed: {str(e)}")

    def is_encrypted(self, token_val: str) -> bool:
        """
        Safely checks if a string is a valid Fernet ciphertext encrypted under the active key.
        """
        if not token_val:
            return False
        try:
            self.fernet.decrypt(token_val.encode("utf-8"))
            return True
        except InvalidToken:
            return False
        except Exception:
            return False

# Global instance lazy wrapper helper
def get_encryption_service() -> TokenEncryptionService:
    return TokenEncryptionService()
