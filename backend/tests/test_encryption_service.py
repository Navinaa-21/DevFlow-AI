import pytest
from cryptography.fernet import Fernet
from app.core.security_encryption import TokenEncryptionService, EncryptionError

# Generated test key
TEST_KEY = Fernet.generate_key().decode("utf-8")

def test_token_encryption_decryption_roundtrip():
    service = TokenEncryptionService(key=TEST_KEY)
    raw_token = "gho_1234567890abcdefghijklmnopqrstuvwxyz"
    
    encrypted = service.encrypt_token(raw_token)
    assert encrypted != raw_token
    assert service.is_encrypted(encrypted) is True
    
    decrypted = service.decrypt_token(encrypted)
    assert decrypted == raw_token

def test_encryption_prevents_double_encryption():
    service = TokenEncryptionService(key=TEST_KEY)
    raw_token = "gho_test_token_sample"
    
    first_pass = service.encrypt_token(raw_token)
    second_pass = service.encrypt_token(first_pass)
    
    assert first_pass == second_pass
    assert service.decrypt_token(second_pass) == raw_token

def test_decryption_of_legacy_plaintext_token():
    service = TokenEncryptionService(key=TEST_KEY)
    plaintext_legacy = "gho_legacy_plaintext_token"
    
    # Should safely return plaintext without throwing an exception
    result = service.decrypt_token(plaintext_legacy)
    assert result == plaintext_legacy

def test_missing_or_invalid_key_raises_encryption_error():
    with pytest.raises(EncryptionError):
        TokenEncryptionService(key="")
        
    with pytest.raises(EncryptionError):
        TokenEncryptionService(key="invalid_base64_key")
