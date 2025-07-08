"""
Enhanced Credential Encryption and Management System
"""
import asyncio
import base64
import hashlib
import secrets
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from ingestion.base.exceptions import ConfigurationException

logger = logging.getLogger(__name__)

class EncryptionType(Enum):
    """Encryption types supported"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    HYBRID = "hybrid"

class CredentialType(Enum):
    """Types of credentials"""
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    DATABASE_URL = "database_url"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    USERNAME_PASSWORD = "username_password"

@dataclass
class EncryptionConfig:
    """Encryption configuration"""
    encryption_type: EncryptionType
    key_rotation_days: int = 90
    backup_keys_count: int = 3
    require_hsm: bool = False
    audit_access: bool = True
    
class CredentialEncryption:
    """Advanced credential encryption system"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.encryption_keys = {}
        self.key_rotation_schedule = {}
        self.audit_log = []
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        # Try to get from environment first
        master_key_b64 = getattr(settings, 'MASTER_ENCRYPTION_KEY', None)
        
        if master_key_b64:
            try:
                return base64.b64decode(master_key_b64)
            except Exception as e:
                logger.error(f"Failed to decode master key from settings: {e}")
        
        # Generate new master key
        master_key = Fernet.generate_key()
        
        # Store in secure location (this should be done externally in production)
        logger.warning("Generated new master key. Store securely: %s", 
                      base64.b64encode(master_key).decode())
        
        return master_key
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def _generate_key_pair(self) -> tuple:
        """Generate RSA key pair for asymmetric encryption"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def create_credential_vault(self, vault_name: str, encryption_config: EncryptionConfig) -> str:
        """Create a new credential vault"""
        vault_id = f"vault_{vault_name}_{secrets.token_hex(8)}"
        
        # Generate vault-specific encryption key
        if encryption_config.encryption_type == EncryptionType.SYMMETRIC:
            vault_key = Fernet.generate_key()
            self.encryption_keys[vault_id] = {
                'type': 'symmetric',
                'key': vault_key,
                'created_at': datetime.now(),
                'config': encryption_config
            }
        elif encryption_config.encryption_type == EncryptionType.ASYMMETRIC:
            private_key, public_key = self._generate_key_pair()
            self.encryption_keys[vault_id] = {
                'type': 'asymmetric',
                'private_key': private_key,
                'public_key': public_key,
                'created_at': datetime.now(),
                'config': encryption_config
            }
        
        # Schedule key rotation
        rotation_date = datetime.now() + timedelta(days=encryption_config.key_rotation_days)
        self.key_rotation_schedule[vault_id] = rotation_date
        
        logger.info(f"Created credential vault: {vault_id}")
        return vault_id
    
    def encrypt_credential(self, vault_id: str, credential_data: Dict[str, Any], 
                          credential_type: CredentialType) -> Dict[str, Any]:
        """Encrypt credential data"""
        if vault_id not in self.encryption_keys:
            raise ConfigurationException(f"Vault {vault_id} not found")
        
        vault_info = self.encryption_keys[vault_id]
        
        try:
            # Prepare credential data
            credential_json = json.dumps(credential_data, sort_keys=True)
            credential_bytes = credential_json.encode('utf-8')
            
            # Add metadata
            metadata = {
                'credential_type': credential_type.value,
                'encrypted_at': datetime.now().isoformat(),
                'vault_id': vault_id,
                'checksum': hashlib.sha256(credential_bytes).hexdigest()
            }
            
            # Encrypt based on vault type
            if vault_info['type'] == 'symmetric':
                fernet = Fernet(vault_info['key'])
                encrypted_data = fernet.encrypt(credential_bytes)
                
                encrypted_credential = {
                    'encrypted_data': base64.b64encode(encrypted_data).decode(),
                    'encryption_type': 'symmetric',
                    'metadata': metadata
                }
            
            elif vault_info['type'] == 'asymmetric':
                # Load public key
                public_key = serialization.load_pem_public_key(vault_info['public_key'])
                
                # Encrypt with public key
                encrypted_data = public_key.encrypt(
                    credential_bytes,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                encrypted_credential = {
                    'encrypted_data': base64.b64encode(encrypted_data).decode(),
                    'encryption_type': 'asymmetric',
                    'metadata': metadata
                }
            
            # Audit log
            self._log_credential_access('encrypt', vault_id, credential_type.value)
            
            return encrypted_credential
            
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            raise ConfigurationException(f"Encryption failed: {e}")
    
    def decrypt_credential(self, vault_id: str, encrypted_credential: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt credential data"""
        if vault_id not in self.encryption_keys:
            raise ConfigurationException(f"Vault {vault_id} not found")
        
        vault_info = self.encryption_keys[vault_id]
        
        try:
            encrypted_data = base64.b64decode(encrypted_credential['encrypted_data'])
            metadata = encrypted_credential['metadata']
            
            # Decrypt based on type
            if vault_info['type'] == 'symmetric':
                fernet = Fernet(vault_info['key'])
                decrypted_bytes = fernet.decrypt(encrypted_data)
            
            elif vault_info['type'] == 'asymmetric':
                # Load private key
                private_key = serialization.load_pem_private_key(
                    vault_info['private_key'],
                    password=None
                )
                
                # Decrypt with private key
                decrypted_bytes = private_key.decrypt(
                    encrypted_data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
            
            # Verify checksum
            actual_checksum = hashlib.sha256(decrypted_bytes).hexdigest()
            expected_checksum = metadata['checksum']
            
            if actual_checksum != expected_checksum:
                raise ConfigurationException("Credential integrity check failed")
            
            # Parse credential data
            credential_json = decrypted_bytes.decode('utf-8')
            credential_data = json.loads(credential_json)
            
            # Audit log
            self._log_credential_access('decrypt', vault_id, metadata['credential_type'])
            
            return credential_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise ConfigurationException(f"Decryption failed: {e}")
    
    def rotate_vault_key(self, vault_id: str) -> bool:
        """Rotate encryption key for a vault"""
        if vault_id not in self.encryption_keys:
            return False
        
        vault_info = self.encryption_keys[vault_id]
        
        try:
            # Generate new key
            if vault_info['type'] == 'symmetric':
                new_key = Fernet.generate_key()
                
                # Backup old key
                old_key = vault_info['key']
                vault_info['previous_keys'] = vault_info.get('previous_keys', [])
                vault_info['previous_keys'].append({
                    'key': old_key,
                    'rotated_at': datetime.now()
                })
                
                # Keep only recent backup keys
                config = vault_info['config']
                if len(vault_info['previous_keys']) > config.backup_keys_count:
                    vault_info['previous_keys'] = vault_info['previous_keys'][-config.backup_keys_count:]
                
                # Update current key
                vault_info['key'] = new_key
                vault_info['rotated_at'] = datetime.now()
            
            elif vault_info['type'] == 'asymmetric':
                private_key, public_key = self._generate_key_pair()
                
                # Backup old keys
                old_private = vault_info['private_key']
                old_public = vault_info['public_key']
                vault_info['previous_keys'] = vault_info.get('previous_keys', [])
                vault_info['previous_keys'].append({
                    'private_key': old_private,
                    'public_key': old_public,
                    'rotated_at': datetime.now()
                })
                
                # Keep only recent backup keys
                config = vault_info['config']
                if len(vault_info['previous_keys']) > config.backup_keys_count:
                    vault_info['previous_keys'] = vault_info['previous_keys'][-config.backup_keys_count:]
                
                # Update current keys
                vault_info['private_key'] = private_key
                vault_info['public_key'] = public_key
                vault_info['rotated_at'] = datetime.now()
            
            # Update rotation schedule
            rotation_date = datetime.now() + timedelta(days=vault_info['config'].key_rotation_days)
            self.key_rotation_schedule[vault_id] = rotation_date
            
            logger.info(f"Rotated key for vault: {vault_id}")
            self._log_credential_access('key_rotation', vault_id, 'system')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate key for vault {vault_id}: {e}")
            return False
    
    def check_key_rotation_schedule(self) -> List[str]:
        """Check which vaults need key rotation"""
        vaults_to_rotate = []
        current_time = datetime.now()
        
        for vault_id, rotation_date in self.key_rotation_schedule.items():
            if current_time >= rotation_date:
                vaults_to_rotate.append(vault_id)
        
        return vaults_to_rotate
    
    def _log_credential_access(self, operation: str, vault_id: str, credential_type: str):
        """Log credential access for audit"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'vault_id': vault_id,
            'credential_type': credential_type,
            'source': 'credential_encryption'
        }
        
        self.audit_log.append(log_entry)
        
        # Keep only recent audit logs
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
    
    def get_audit_log(self, vault_id: str = None, hours: int = 24) -> List[Dict]:
        """Get audit log for credential access"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_logs = []
        for log_entry in self.audit_log:
            log_time = datetime.fromisoformat(log_entry['timestamp'])
            if log_time > cutoff_time:
                if vault_id is None or log_entry['vault_id'] == vault_id:
                    filtered_logs.append(log_entry)
        
        return filtered_logs
    
    def export_vault_keys(self, vault_id: str, export_password: str) -> str:
        """Export vault keys for backup (encrypted)"""
        if vault_id not in self.encryption_keys:
            raise ConfigurationException(f"Vault {vault_id} not found")
        
        vault_info = self.encryption_keys[vault_id]
        
        # Create export data
        export_data = {
            'vault_id': vault_id,
            'vault_info': vault_info,
            'exported_at': datetime.now().isoformat(),
            'export_version': '1.0'
        }
        
        # Encrypt export data
        salt = secrets.token_bytes(16)
        export_key = self._derive_key(export_password, salt)
        fernet = Fernet(base64.urlsafe_b64encode(export_key))
        
        export_json = json.dumps(export_data, default=str)
        encrypted_export = fernet.encrypt(export_json.encode())
        
        # Create final export package
        export_package = {
            'salt': base64.b64encode(salt).decode(),
            'encrypted_data': base64.b64encode(encrypted_export).decode(),
            'checksum': hashlib.sha256(encrypted_export).hexdigest()
        }
        
        self._log_credential_access('export', vault_id, 'system')
        
        return base64.b64encode(json.dumps(export_package).encode()).decode()
    
    def import_vault_keys(self, export_data: str, import_password: str) -> str:
        """Import vault keys from backup"""
        try:
            # Decode export package
            export_package = json.loads(base64.b64decode(export_data).decode())
            
            salt = base64.b64decode(export_package['salt'])
            encrypted_data = base64.b64decode(export_package['encrypted_data'])
            expected_checksum = export_package['checksum']
            
            # Verify checksum
            actual_checksum = hashlib.sha256(encrypted_data).hexdigest()
            if actual_checksum != expected_checksum:
                raise ConfigurationException("Import data integrity check failed")
            
            # Decrypt import data
            import_key = self._derive_key(import_password, salt)
            fernet = Fernet(base64.urlsafe_b64encode(import_key))
            
            decrypted_json = fernet.decrypt(encrypted_data)
            import_data = json.loads(decrypted_json.decode())
            
            # Restore vault
            vault_id = import_data['vault_id']
            vault_info = import_data['vault_info']
            
            # Convert datetime strings back to datetime objects
            vault_info['created_at'] = datetime.fromisoformat(vault_info['created_at'])
            if 'rotated_at' in vault_info:
                vault_info['rotated_at'] = datetime.fromisoformat(vault_info['rotated_at'])
            
            # Restore vault
            self.encryption_keys[vault_id] = vault_info
            
            # Update rotation schedule
            config = vault_info['config']
            rotation_date = datetime.now() + timedelta(days=config.key_rotation_days)
            self.key_rotation_schedule[vault_id] = rotation_date
            
            logger.info(f"Imported vault keys: {vault_id}")
            self._log_credential_access('import', vault_id, 'system')
            
            return vault_id
            
        except Exception as e:
            logger.error(f"Failed to import vault keys: {e}")
            raise ConfigurationException(f"Import failed: {e}")

class CredentialManager:
    """High-level credential management interface"""
    
    def __init__(self):
        self.encryption = CredentialEncryption()
        self.credential_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def store_api_credentials(self, crm_source: str, credentials: Dict[str, Any]) -> str:
        """Store API credentials for a CRM source"""
        vault_name = f"{crm_source}_api_credentials"
        
        # Create vault if not exists
        vault_id = self.get_or_create_vault(vault_name, CredentialType.API_KEY)
        
        # Encrypt and store credentials
        encrypted_creds = self.encryption.encrypt_credential(
            vault_id, credentials, CredentialType.API_KEY
        )
        
        # Store in database
        self._store_encrypted_credential(crm_source, encrypted_creds)
        
        return vault_id
    
    def get_api_credentials(self, crm_source: str) -> Dict[str, Any]:
        """Get API credentials for a CRM source"""
        cache_key = f"credentials_{crm_source}"
        
        # Check cache first
        if cache_key in self.credential_cache:
            cache_entry = self.credential_cache[cache_key]
            if datetime.now() - cache_entry['cached_at'] < timedelta(seconds=self.cache_ttl):
                return cache_entry['credentials']
        
        # Get from database
        encrypted_creds = self._get_encrypted_credential(crm_source)
        if not encrypted_creds:
            raise ConfigurationException(f"No credentials found for {crm_source}")
        
        # Decrypt credentials
        vault_id = encrypted_creds['metadata']['vault_id']
        credentials = self.encryption.decrypt_credential(vault_id, encrypted_creds)
        
        # Cache credentials
        self.credential_cache[cache_key] = {
            'credentials': credentials,
            'cached_at': datetime.now()
        }
        
        return credentials
    
    def get_or_create_vault(self, vault_name: str, credential_type: CredentialType) -> str:
        """Get existing vault or create new one"""
        # Check if vault exists
        existing_vault = self._find_vault_by_name(vault_name)
        if existing_vault:
            return existing_vault
        
        # Create new vault
        encryption_config = self._get_encryption_config(credential_type)
        vault_id = self.encryption.create_credential_vault(vault_name, encryption_config)
        
        return vault_id
    
    def _get_encryption_config(self, credential_type: CredentialType) -> EncryptionConfig:
        """Get encryption configuration for credential type"""
        if credential_type in [CredentialType.PRIVATE_KEY, CredentialType.CERTIFICATE]:
            return EncryptionConfig(
                encryption_type=EncryptionType.ASYMMETRIC,
                key_rotation_days=30,
                backup_keys_count=5,
                audit_access=True
            )
        else:
            return EncryptionConfig(
                encryption_type=EncryptionType.SYMMETRIC,
                key_rotation_days=90,
                backup_keys_count=3,
                audit_access=True
            )
    
    def _store_encrypted_credential(self, crm_source: str, encrypted_creds: Dict[str, Any]):
        """Store encrypted credential in database"""
        from ingestion.models.common import APICredential
        
        # Update or create credential record
        credential, created = APICredential.objects.update_or_create(
            crm_source=crm_source,
            defaults={
                'credentials': encrypted_creds,
                'is_active': True
            }
        )
        
        if created:
            logger.info(f"Created encrypted credentials for {crm_source}")
        else:
            logger.info(f"Updated encrypted credentials for {crm_source}")
    
    def _get_encrypted_credential(self, crm_source: str) -> Optional[Dict[str, Any]]:
        """Get encrypted credential from database"""
        from ingestion.models.common import APICredential
        
        try:
            credential = APICredential.objects.get(crm_source=crm_source, is_active=True)
            return credential.credentials
        except APICredential.DoesNotExist:
            return None
    
    def _find_vault_by_name(self, vault_name: str) -> Optional[str]:
        """Find vault by name"""
        for vault_id, vault_info in self.encryption.encryption_keys.items():
            if vault_name in vault_id:
                return vault_id
        return None
    
    def rotate_all_keys(self):
        """Rotate all keys that are due for rotation"""
        vaults_to_rotate = self.encryption.check_key_rotation_schedule()
        
        for vault_id in vaults_to_rotate:
            success = self.encryption.rotate_vault_key(vault_id)
            if success:
                logger.info(f"Successfully rotated key for vault {vault_id}")
            else:
                logger.error(f"Failed to rotate key for vault {vault_id}")
    
    def clear_credential_cache(self):
        """Clear credential cache"""
        self.credential_cache.clear()
        logger.info("Credential cache cleared")
    
    def get_credential_audit_log(self, crm_source: str = None, hours: int = 24) -> List[Dict]:
        """Get credential access audit log"""
        return self.encryption.get_audit_log(crm_source, hours)

# Global credential manager instance
credential_manager = CredentialManager()

# Async task for automatic key rotation
async def automatic_key_rotation():
    """Automatic key rotation task"""
    while True:
        try:
            credential_manager.rotate_all_keys()
            await asyncio.sleep(3600)  # Check every hour
        except Exception as e:
            logger.error(f"Error in automatic key rotation: {e}")
            await asyncio.sleep(3600)

# Start automatic key rotation
def start_key_rotation():
    """Start automatic key rotation"""
    asyncio.create_task(automatic_key_rotation())
    logger.info("Automatic key rotation started")

# Enhanced API credential model
class EnhancedAPICredential(models.Model):
    """Enhanced API credential model with encryption metadata"""
    
    crm_source = models.CharField(max_length=50, unique=True)
    credentials = models.JSONField()  # Encrypted credential data
    vault_id = models.CharField(max_length=100)
    credential_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    
    # Security
    last_rotation = models.DateTimeField(null=True, blank=True)
    rotation_required = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'enhanced_api_credentials'
        verbose_name = 'Enhanced API Credential'
        verbose_name_plural = 'Enhanced API Credentials'
    
    def __str__(self):
        return f"{self.crm_source} Credentials"
    
    def mark_accessed(self):
        """Mark credential as accessed"""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])
    
    def needs_rotation(self) -> bool:
        """Check if credential needs rotation"""
        if self.rotation_required:
            return True
        
        if self.last_rotation is None:
            return True
        
        # Check if rotation is overdue (90 days)
        rotation_due = self.last_rotation + timedelta(days=90)
        return timezone.now() > rotation_due
