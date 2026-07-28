import os
import hashlib
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

def derive_aes_key(passphrase: str) -> bytes:
    """Derives a 256-bit (32-byte) binary key from secret passphrase using SHA-256."""
    return hashlib.sha256(passphrase.encode("utf-8")).digest()

def anonymize_name(name: str, prefix: str = "CUST", salt: str = "PySyncSalt") -> str:
    """Generates a clean, deterministic anonymized ID from a customer or package name."""
    clean = name.strip().lower()
    h = hashlib.sha256(f"{salt}:{clean}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"

def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """Encrypts raw bytes using AES-256-CBC with a 16-byte random IV and PKCS7 padding."""
    key = derive_aes_key(passphrase)
    iv = os.urandom(16)
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Return 16-byte IV prepended to ciphertext (compatible with PHP openssl_decrypt)
    return iv + ciphertext

def decrypt_bytes(encrypted_payload: bytes, passphrase: str) -> Optional[bytes]:
    """Decrypts AES-256-CBC payload formatted as 16-byte IV + ciphertext."""
    if len(encrypted_payload) <= 16:
        return None
    try:
        key = derive_aes_key(passphrase)
        iv = encrypted_payload[:16]
        ciphertext = encrypted_payload[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def encrypt_file_to_bytes(src_file_path: str, passphrase: str) -> Optional[bytes]:
    """Reads local file and encrypts contents to AES-256-CBC payload."""
    try:
        with open(src_file_path, "rb") as f:
            raw_bytes = f.read()
        return encrypt_bytes(raw_bytes, passphrase)
    except Exception as e:
        print(f"Error encrypting file '{src_file_path}': {e}")
        return None
