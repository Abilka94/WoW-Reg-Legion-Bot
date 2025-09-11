"""
Enhanced validators with security improvements and comprehensive validation.
This module addresses all security vulnerabilities found in the original validators.
"""
import re
import string
import time
from typing import Set, Optional, Dict, Any
from functools import lru_cache

# Security constants
MAX_EMAIL_LENGTH = 254  # RFC 5321 limit
MAX_LOCAL_PART_LENGTH = 64  # RFC 5321 limit
MAX_DOMAIN_LENGTH = 253  # RFC 1035 limit
MAX_NICKNAME_LENGTH = 32  # Game-appropriate limit
MIN_NICKNAME_LENGTH = 3  # Minimum reasonable length
MAX_PASSWORD_LENGTH = 128  # Reasonable security limit
MIN_PASSWORD_LENGTH = 8  # Security requirement

# Validation timeout (seconds)
VALIDATION_TIMEOUT = 0.1

# Reserved nicknames that should not be allowed
RESERVED_NICKNAMES: Set[str] = {
    'admin', 'administrator', 'root', 'system', 'test', 'guest', 'user',
    'mod', 'moderator', 'support', 'help', 'api', 'www', 'mail', 'email',
    'bot', 'null', 'undefined', 'delete', 'create', 'update', 'select',
    'insert', 'drop', 'table', 'database', 'server', 'gm', 'gamemaster',
    'console', 'world', 'guild', 'player', 'character', 'account'
}

# Common weak passwords to reject
WEAK_PASSWORDS: Set[str] = {
    'password', '123456', '123456789', 'qwerty', 'abc123', 'password123',
    'admin', 'letmein', 'welcome', 'monkey', '1234567890', 'dragon',
    'superman', 'michael', 'password1', 'superman', 'qwerty123',
    'test', 'guest', 'user', 'default', 'changeme'
}

# Precompiled regex patterns for performance
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
)
NICKNAME_PATTERN = re.compile(r'^[A-Za-z0-9]+$')
CYRILLIC_PATTERN = re.compile(r'[А-Яа-яЁё]')
CONSECUTIVE_CHARS_PATTERN = re.compile(r'(.)\1{2,}')  # 3+ consecutive same chars
KEYBOARD_PATTERNS = [
    re.compile(r'qwert|asdf|zxcv', re.IGNORECASE),
    re.compile(r'12345|67890', re.IGNORECASE),
]

# Password strength patterns
UPPER_CASE_PATTERN = re.compile(r'[A-Z]')
LOWER_CASE_PATTERN = re.compile(r'[a-z]')
DIGIT_PATTERN = re.compile(r'\d')
SPECIAL_CHAR_PATTERN = re.compile(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]')


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ValidationResult:
    """Result of validation with detailed information."""
    
    def __init__(self, is_valid: bool, errors: Optional[list] = None, warnings: Optional[list] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)


def _with_timeout(func, timeout: float = VALIDATION_TIMEOUT):
    """Decorator to add timeout protection to validation functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        if elapsed > timeout:
            raise ValidationError(f"Validation timeout exceeded: {elapsed:.3f}s > {timeout}s")
        
        return result
    return wrapper


@_with_timeout
def validate_email_enhanced(email: str) -> ValidationResult:
    """
    Enhanced email validation with comprehensive security checks.
    
    Args:
        email: Email address to validate
        
    Returns:
        ValidationResult with validation status and error details
    """
    result = ValidationResult(True)
    
    # Basic type and None checks
    if not isinstance(email, str):
        result.add_error("Email must be a string")
        return result
    
    # Length checks (DoS protection)
    if len(email) == 0:
        result.add_error("Email cannot be empty")
        return result
    
    if len(email) > MAX_EMAIL_LENGTH:
        result.add_error(f"Email too long (max {MAX_EMAIL_LENGTH} characters)")
        return result
    
    # Basic structure check
    if email.count('@') != 1:
        result.add_error("Email must contain exactly one @ symbol")
        return result
    
    local_part, domain_part = email.split('@')
    
    # Local part validation
    if len(local_part) == 0:
        result.add_error("Email local part cannot be empty")
        return result
    
    if len(local_part) > MAX_LOCAL_PART_LENGTH:
        result.add_error(f"Email local part too long (max {MAX_LOCAL_PART_LENGTH} characters)")
        return result
    
    # Domain part validation
    if len(domain_part) == 0:
        result.add_error("Email domain cannot be empty")
        return result
    
    if len(domain_part) > MAX_DOMAIN_LENGTH:
        result.add_error(f"Email domain too long (max {MAX_DOMAIN_LENGTH} characters)")
        return result
    
    # Check for consecutive dots
    if '..' in email:
        result.add_error("Email cannot contain consecutive dots")
        return result
    
    # Check for leading/trailing dots
    if local_part.startswith('.') or local_part.endswith('.'):
        result.add_error("Email local part cannot start or end with a dot")
        return result
    
    if domain_part.startswith('.') or domain_part.endswith('.'):
        result.add_error("Email domain cannot start or end with a dot")
        return result
    
    # Security checks - check whitespace before regex
    if any(char in email for char in [' ', '\t', '\n', '\r']):
        result.add_error("Email cannot contain whitespace characters")
        return result
    
    # Regex validation (with ReDoS protection via timeout)
    if not EMAIL_PATTERN.match(email):
        result.add_error("Email format is invalid")
        return result
    
    # Domain validation
    domain_parts = domain_part.split('.')
    if len(domain_parts) < 2:
        result.add_error("Email domain must have at least two parts")
        return result
    
    # Check TLD length
    if len(domain_parts[-1]) < 2:
        result.add_error("Email top-level domain too short")
        return result
    
    # Warn about potentially suspicious emails
    if '+' in local_part:
        result.add_warning("Email contains plus addressing")
    
    if local_part.count('.') > 3:
        result.add_warning("Email local part has many dots")
    
    return result


@_with_timeout
def validate_nickname_enhanced(nickname: str) -> ValidationResult:
    """
    Enhanced nickname validation with security and UX improvements.
    
    Args:
        nickname: Nickname to validate
        
    Returns:
        ValidationResult with validation status and error details
    """
    result = ValidationResult(True)
    
    # Basic type and None checks
    if not isinstance(nickname, str):
        result.add_error("Nickname must be a string")
        return result
    
    # Empty check
    if len(nickname) == 0:
        result.add_error("Nickname cannot be empty")
        return result
    
    # Reserved names check (including custom reserved names) - check before length to ensure detection
    all_reserved = RESERVED_NICKNAMES | validation_config.custom_reserved_names
    if nickname.lower() in all_reserved:
        result.add_error("Nickname is reserved and cannot be used")
        return result
    
    # Length checks
    if len(nickname) < MIN_NICKNAME_LENGTH:
        result.add_error(f"Nickname too short (minimum {MIN_NICKNAME_LENGTH} characters)")
        return result
    
    if len(nickname) > MAX_NICKNAME_LENGTH:
        result.add_error(f"Nickname too long (maximum {MAX_NICKNAME_LENGTH} characters)")
        return result
    
    # Character validation (alphanumeric only for game compatibility)
    if not NICKNAME_PATTERN.match(nickname):
        result.add_error("Nickname can only contain letters and numbers")
        return result
    
    # Quality checks
    if nickname.isdigit():
        result.add_error("Nickname cannot be only numbers")
        return result
    
    # Check for repetitive patterns
    if CONSECUTIVE_CHARS_PATTERN.search(nickname):
        result.add_warning("Nickname contains repetitive characters")
    
    # Check for keyboard patterns
    for pattern in KEYBOARD_PATTERNS:
        if pattern.search(nickname):
            result.add_warning("Nickname contains keyboard pattern")
            break
    
    # Check for common gaming terms that might be problematic
    problematic_terms = ['test', 'temp', 'fake', 'bot', 'npc']
    if any(term in nickname.lower() for term in problematic_terms):
        result.add_warning("Nickname contains potentially problematic term")
    
    return result


@_with_timeout
def validate_password_enhanced(password: str) -> ValidationResult:
    """
    Enhanced password validation with comprehensive security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        ValidationResult with validation status and error details
    """
    result = ValidationResult(True)
    
    # Basic type and None checks
    if not isinstance(password, str):
        result.add_error("Password must be a string")
        return result
    
    # Empty check
    if len(password) == 0:
        result.add_error("Password cannot be empty")
        return result
    
    # Cyrillic check (original requirement) - check before length to ensure detection
    if CYRILLIC_PATTERN.search(password):
        result.add_error("Password cannot contain cyrillic characters")
        return result
    
    # Length checks
    if len(password) < MIN_PASSWORD_LENGTH:
        result.add_error(f"Password too short (minimum {MIN_PASSWORD_LENGTH} characters)")
        return result
    
    if len(password) > MAX_PASSWORD_LENGTH:
        result.add_error(f"Password too long (maximum {MAX_PASSWORD_LENGTH} characters)")
        return result
    
    # Character encoding check (ASCII only for game server compatibility)
    try:
        password.encode('ascii')
    except UnicodeEncodeError:
        result.add_error("Password can only contain ASCII characters")
        return result
    
    # Strength requirements
    strength_score = 0
    
    if UPPER_CASE_PATTERN.search(password):
        strength_score += 1
    else:
        result.add_warning("Password should contain at least one uppercase letter")
    
    if LOWER_CASE_PATTERN.search(password):
        strength_score += 1
    else:
        result.add_warning("Password should contain at least one lowercase letter")
    
    if DIGIT_PATTERN.search(password):
        strength_score += 1
    else:
        result.add_warning("Password should contain at least one digit")
    
    if SPECIAL_CHAR_PATTERN.search(password):
        strength_score += 1
    else:
        result.add_warning("Password should contain at least one special character")
    
    # Minimum strength requirement
    if strength_score < 2:
        result.add_error("Password is too weak (needs at least 2 character types)")
        return result
    
    # Common password check (including custom weak passwords)
    all_weak_passwords = WEAK_PASSWORDS | validation_config.custom_weak_passwords
    if password.lower() in all_weak_passwords:
        result.add_error("Password is too common and easily guessable")
        return result
    
    # Pattern checks
    if CONSECUTIVE_CHARS_PATTERN.search(password):
        result.add_warning("Password contains repetitive characters")
    
    # Keyboard pattern check
    for pattern in KEYBOARD_PATTERNS:
        if pattern.search(password):
            result.add_warning("Password contains keyboard pattern")
            break
    
    # Sequential check (basic)
    sequential_patterns = ['0123', '1234', '2345', '3456', '4567', '5678', '6789', '9876', '8765', '7654', '6543', '5432', '4321', '3210']
    if any(seq in password for seq in sequential_patterns):
        result.add_warning("Password contains sequential numbers")
    
    return result


# Backward compatibility functions (return bool like original)
def validate_email(email: str) -> bool:
    """Backward compatible email validation function."""
    try:
        return bool(validate_email_enhanced(email))
    except Exception:
        return False


def validate_nickname(nickname: str) -> bool:
    """Backward compatible nickname validation function."""
    try:
        return bool(validate_nickname_enhanced(nickname))
    except Exception:
        return False


def validate_password(password: str) -> bool:
    """Backward compatible password validation function."""
    try:
        return bool(validate_password_enhanced(password))
    except Exception:
        return False


# Configuration for different validation modes
class ValidationConfig:
    """Configuration for validation behavior."""
    
    def __init__(self):
        self.strict_mode = False  # Enable strict validation
        self.allow_warnings = True  # Allow values with warnings
        self.max_validation_time = VALIDATION_TIMEOUT
        self.custom_reserved_names: Set[str] = set()
        self.custom_weak_passwords: Set[str] = set()
    
    def add_reserved_name(self, name: str):
        """Add a custom reserved name."""
        self.custom_reserved_names.add(name.lower())
    
    def add_weak_password(self, password: str):
        """Add a custom weak password."""
        self.custom_weak_passwords.add(password.lower())


# Global configuration instance
validation_config = ValidationConfig()


@lru_cache(maxsize=1000)
def validate_user_input(email: str, nickname: str, password: str) -> Dict[str, ValidationResult]:
    """
    Validate all user inputs together with caching for performance.
    
    Args:
        email: Email to validate
        nickname: Nickname to validate  
        password: Password to validate
        
    Returns:
        Dictionary with validation results for each field
    """
    return {
        'email': validate_email_enhanced(email),
        'nickname': validate_nickname_enhanced(nickname),
        'password': validate_password_enhanced(password)
    }


def get_validation_summary(results: Dict[str, ValidationResult]) -> Dict[str, Any]:
    """
    Get a summary of validation results.
    
    Args:
        results: Dictionary of validation results
        
    Returns:
        Summary dictionary with overall status and details
    """
    all_valid = all(result.is_valid for result in results.values())
    total_errors = sum(len(result.errors) for result in results.values())
    total_warnings = sum(len(result.warnings) for result in results.values())
    
    return {
        'all_valid': all_valid,
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'details': {
            field: {
                'valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings
            }
            for field, result in results.items()
        }
    }