# File: /app/core/security.py
import os
import base64
from typing import Optional, Union
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# PASSWORD HASHING
# =============================================================================

# Create password context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password (str): The plain text password to verify
        hashed_password (str): The hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    
    Args:
        password (str): The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise ValueError("Failed to hash password")

# =============================================================================
# CREDENTIAL ENCRYPTION
# =============================================================================

class CredentialCrypto:
    """
    Class to handle encryption and decryption of sensitive credentials.
    Uses Fernet (symmetric encryption) for secure credential storage.
    """
    
    def __init__(self, fernet_key: Optional[str] = None):
        """
        Initialize the crypto handler.
        
        Args:
            fernet_key (str, optional): Base64 encoded Fernet key.
                                      If None, will try to load from environment.
        """
        if fernet_key is None:
            fernet_key = os.getenv("FERNET_KEY")
            
        if not fernet_key:
            raise ValueError(
                "FERNET_KEY environment variable is required for credential encryption. "
                "Generate one using: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            # Ensure the key is in bytes format
            if isinstance(fernet_key, str):
                fernet_key = fernet_key.encode()
            
            self.fernet = Fernet(fernet_key)
        except Exception as e:
            logger.error(f"Error initializing Fernet encryption: {e}")
            raise ValueError("Invalid FERNET_KEY. Please generate a new one.")
    
    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data (str): The plain text data to encrypt
            
        Returns:
            str: Base64 encoded encrypted data
        """
        if not data:
            return ""
        
        try:
            # Convert string to bytes
            data_bytes = data.encode('utf-8')
            
            # Encrypt the data
            encrypted_data = self.fernet.encrypt(data_bytes)
            
            # Return base64 encoded string for database storage
            return base64.b64encode(encrypted_data).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data (str): Base64 encoded encrypted data
            
        Returns:
            str: The decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt the data
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            
            # Convert bytes back to string
            return decrypted_bytes.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise ValueError("Failed to decrypt data. Data may be corrupted or key may be invalid.")

# Global crypto instance (initialized lazily)
_crypto_instance: Optional[CredentialCrypto] = None

def get_crypto_instance() -> CredentialCrypto:
    """
    Get or create the global crypto instance.
    
    Returns:
        CredentialCrypto: The crypto instance
    """
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = CredentialCrypto()
    return _crypto_instance

def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data using the global crypto instance.
    
    Args:
        data (str): The plain text data to encrypt
        
    Returns:
        str: Base64 encoded encrypted data
    """
    crypto = get_crypto_instance()
    return crypto.encrypt_data(data)

def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt encrypted data using the global crypto instance.
    
    Args:
        encrypted_data (str): Base64 encoded encrypted data
        
    Returns:
        str: The decrypted plain text data
    """
    crypto = get_crypto_instance()
    return crypto.decrypt_data(encrypted_data)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_fernet_key() -> str:
    """
    Generate a new Fernet key for encryption.
    
    Returns:
        str: Base64 encoded Fernet key
    """
    return Fernet.generate_key().decode()

def derive_key_from_password(password: str, salt: bytes = None) -> bytes:
    """
    Derive a Fernet key from a password using PBKDF2.
    This is useful if you want to derive encryption keys from user passwords.
    
    Args:
        password (str): The password to derive key from
        salt (bytes, optional): Salt for key derivation. If None, generates new salt.
        
    Returns:
        bytes: The derived key
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def validate_credential_data(data: dict) -> bool:
    """
    Validate that credential data contains required fields.
    
    Args:
        data (dict): Dictionary containing credential data
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['api_key', 'secret_key', 'user_id', 'password']
    return all(field in data and data[field] for field in required_fields)

def encrypt_client_credentials(credentials: dict) -> dict:
    """
    Encrypt client broker credentials for database storage.
    
    Args:
        credentials (dict): Dictionary containing plain text credentials
        
    Returns:
        dict: Dictionary containing encrypted credentials
    """
    if not validate_credential_data(credentials):
        raise ValueError("Invalid credential data. All fields (api_key, secret_key, user_id, password) are required.")
    
    encrypted_creds = {}
    for key, value in credentials.items():
        if value:  # Only encrypt non-empty values
            encrypted_creds[f"encrypted_{key}"] = encrypt_data(str(value))
    
    return encrypted_creds

def decrypt_client_credentials(encrypted_credentials: dict) -> dict:
    """
    Decrypt client broker credentials from database storage.
    
    Args:
        encrypted_credentials (dict): Dictionary containing encrypted credentials
        
    Returns:
        dict: Dictionary containing decrypted credentials
    """
    decrypted_creds = {}
    for key, value in encrypted_credentials.items():
        if key.startswith("encrypted_") and value:
            # Remove 'encrypted_' prefix to get the original key name
            original_key = key.replace("encrypted_", "")
            decrypted_creds[original_key] = decrypt_data(value)
    
    return decrypted_creds

# =============================================================================
# TESTING UTILITIES (for development only)
# =============================================================================

def test_encryption_decryption():
    """
    Test encryption and decryption functionality.
    This function is for development/testing purposes only.
    """
    test_data = "test_api_key_12345"
    
    print("=== Testing Encryption/Decryption ===")
    print(f"Original data: {test_data}")
    
    try:
        # Encrypt
        encrypted = encrypt_data(test_data)
        print(f"Encrypted data: {encrypted}")
        
        # Decrypt
        decrypted = decrypt_data(encrypted)
        print(f"Decrypted data: {decrypted}")
        
        # Verify
        if test_data == decrypted:
            print("✅ Encryption/Decryption test PASSED")
        else:
            print("❌ Encryption/Decryption test FAILED")
            
    except Exception as e:
        print(f"❌ Encryption/Decryption test ERROR: {e}")

def test_password_hashing():
    """
    Test password hashing functionality.
    This function is for development/testing purposes only.
    """
    test_password = "TestPassword123!"
    
    print("=== Testing Password Hashing ===")
    print(f"Original password: {test_password}")
    
    try:
        # Hash password
        hashed = get_password_hash(test_password)
        print(f"Hashed password: {hashed}")
        
        # Verify correct password
        is_valid = verify_password(test_password, hashed)
        print(f"Correct password verification: {is_valid}")
        
        # Verify incorrect password
        is_invalid = verify_password("WrongPassword", hashed)
        print(f"Incorrect password verification: {is_invalid}")
        
        if is_valid and not is_invalid:
            print("✅ Password hashing test PASSED")
        else:
            print("❌ Password hashing test FAILED")
            
    except Exception as e:
        print(f"❌ Password hashing test ERROR: {e}")

if __name__ == "__main__":
    # Run tests if script is executed directly
    print("🔒 Security Module Tests")
    test_password_hashing()
    print()
    test_encryption_decryption()
    print()
    print("To generate a new Fernet key, run:")
    print("python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")