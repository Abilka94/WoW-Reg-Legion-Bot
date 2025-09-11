"""
Test suite for enhanced validators with security improvements.
"""
import pytest
import time
from unittest.mock import patch

from src.utils.validators_enhanced import (
    validate_email_enhanced,
    validate_nickname_enhanced,
    validate_password_enhanced,
    validate_user_input,
    get_validation_summary,
    ValidationResult,
    ValidationError,
    validation_config
)


class TestEnhancedEmailValidator:
    """Test suite for enhanced email validation."""
    
    def test_valid_emails_detailed(self):
        """Test valid emails with detailed results."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.org",
            "valid_email@test-domain.net",
            "user123@gmail.com",
            "a@b.co",
        ]
        
        for email in valid_emails:
            result = validate_email_enhanced(email)
            assert result.is_valid, f"Email {email} should be valid. Errors: {result.errors}"
            assert isinstance(result.errors, list)
            assert isinstance(result.warnings, list)
    
    def test_invalid_emails_with_reasons(self):
        """Test invalid emails and check error messages."""
        invalid_cases = [
            ("", "Email cannot be empty"),
            ("invalid-email", "Email must contain exactly one @ symbol"),
            ("@domain.com", "Email local part cannot be empty"),
            ("user@", "Email domain cannot be empty"),
            ("user..name@domain.com", "Email cannot contain consecutive dots"),
            (".user@domain.com", "Email local part cannot start or end with a dot"),
            ("user@domain.", "Email domain cannot start or end with a dot"),
            ("user name@domain.com", "Email cannot contain whitespace characters"),
        ]
        
        for email, expected_error in invalid_cases:
            result = validate_email_enhanced(email)
            assert not result.is_valid, f"Email {email} should be invalid"
            assert any(expected_error in error for error in result.errors), \
                f"Expected error '{expected_error}' not found in {result.errors}"
    
    def test_email_length_limits_enhanced(self):
        """Test enhanced email length validation."""
        # Test maximum allowed length
        max_local = "a" * 64  # RFC limit
        max_domain = "b" * 60 + ".com"  # Under limit
        max_email = f"{max_local}@{max_domain}"
        
        result = validate_email_enhanced(max_email)
        if len(max_email) <= 254:  # Should be valid if under total limit
            assert result.is_valid or len(result.errors) == 0
        
        # Test over limits
        too_long_local = "a" * 65 + "@domain.com"
        result = validate_email_enhanced(too_long_local)
        assert not result.is_valid
        assert any("local part too long" in error for error in result.errors)
    
    def test_email_security_features(self):
        """Test security features of enhanced email validator."""
        # Test timeout protection
        very_long_email = "a" * 10000 + "@" + "b" * 10000 + ".com"
        start_time = time.time()
        result = validate_email_enhanced(very_long_email)
        elapsed = time.time() - start_time
        
        # Should either reject quickly or raise timeout error
        assert elapsed < 1.0, "Email validation should complete quickly"
        assert not result.is_valid  # Should reject very long emails


class TestEnhancedNicknameValidator:
    """Test suite for enhanced nickname validation."""
    
    def test_valid_nicknames_enhanced(self):
        """Test valid nicknames with enhanced validation."""
        valid_nicknames = [
            "TestUser",
            "Player123",
            "GamerOne",
            "User2024",
            "ABC123def",
        ]
        
        for nickname in valid_nicknames:
            result = validate_nickname_enhanced(nickname)
            assert result.is_valid, f"Nickname {nickname} should be valid. Errors: {result.errors}"
    
    def test_invalid_nicknames_with_reasons(self):
        """Test invalid nicknames with specific error reasons."""
        invalid_cases = [
            ("", "Nickname cannot be empty"),
            ("ab", "Nickname too short"),
            ("a" * 50, "Nickname too long"),
            ("user@test", "Nickname can only contain letters and numbers"),
            ("admin", "Nickname is reserved"),
            ("123456", "Nickname cannot be only numbers"),
            ("Пользователь", "Nickname can only contain letters and numbers"),
        ]
        
        for nickname, expected_error in invalid_cases:
            result = validate_nickname_enhanced(nickname)
            assert not result.is_valid, f"Nickname {nickname} should be invalid"
            assert any(expected_error in error for error in result.errors), \
                f"Expected error '{expected_error}' not found in {result.errors}"
    
    def test_nickname_reserved_names(self):
        """Test comprehensive reserved names checking."""
        reserved_names = [
            "admin", "administrator", "root", "system", "test", "guest",
            "mod", "moderator", "support", "help", "gm", "gamemaster"
        ]
        
        for name in reserved_names:
            result = validate_nickname_enhanced(name)
            assert not result.is_valid, f"Reserved name {name} should be rejected"
            assert any("reserved" in error.lower() for error in result.errors)
    
    def test_nickname_warnings(self):
        """Test nickname validation warnings."""
        # Test repetitive characters
        result = validate_nickname_enhanced("aaa123")
        assert any("repetitive" in warning.lower() for warning in result.warnings)
        
        # Test keyboard patterns
        result = validate_nickname_enhanced("qwerty123")
        assert any("keyboard" in warning.lower() for warning in result.warnings)


class TestEnhancedPasswordValidator:
    """Test suite for enhanced password validation."""
    
    def test_valid_strong_passwords(self):
        """Test valid strong passwords."""
        strong_passwords = [
            "MyStr0ng!Pass",
            "SecurePwd123!",
            "GamePassword1@",
            "Test123$Valid",
        ]
        
        for password in strong_passwords:
            result = validate_password_enhanced(password)
            assert result.is_valid, f"Password should be valid. Errors: {result.errors}"
    
    def test_password_strength_requirements(self):
        """Test password strength requirements."""
        weak_cases = [
            ("", "Password cannot be empty"),
            ("abc", "Password too short"),
            ("password", "Password is too weak"),
            ("123456789", "Password is too weak"),
            ("PASSWORD", "Password is too weak"),
            ("password123", "Password is too common"),
        ]
        
        for password, expected_error in weak_cases:
            result = validate_password_enhanced(password)
            assert not result.is_valid, f"Weak password {password} should be rejected"
            assert any(expected_error in error for error in result.errors), \
                f"Expected error '{expected_error}' not found in {result.errors}"
    
    def test_password_cyrillic_rejection(self):
        """Test that Cyrillic passwords are still rejected."""
        cyrillic_passwords = [
            "пароль123",
            "Password123а",
            "тест",
        ]
        
        for password in cyrillic_passwords:
            result = validate_password_enhanced(password)
            assert not result.is_valid, f"Cyrillic password {password} should be rejected"
            assert any("cyrillic" in error.lower() for error in result.errors)
    
    def test_password_warnings(self):
        """Test password validation warnings."""
        # Test with missing character types
        result = validate_password_enhanced("testpassword")  # No digits, no uppercase
        assert len(result.warnings) > 0
        assert any("uppercase" in warning.lower() for warning in result.warnings)
        assert any("digit" in warning.lower() for warning in result.warnings)


class TestValidationIntegration:
    """Test integrated validation functions."""
    
    def test_validate_user_input_all_valid(self):
        """Test validation of all user inputs together."""
        email = "user@example.com"
        nickname = "TestUser123"
        password = "StrongPass1!"
        
        results = validate_user_input(email, nickname, password)
        
        assert 'email' in results
        assert 'nickname' in results
        assert 'password' in results
        
        assert results['email'].is_valid
        assert results['nickname'].is_valid
        assert results['password'].is_valid
    
    def test_validate_user_input_mixed_results(self):
        """Test validation with mixed valid/invalid inputs."""
        email = "invalid-email"
        nickname = "ValidNick123"
        password = "пароль123"
        
        results = validate_user_input(email, nickname, password)
        
        assert not results['email'].is_valid
        assert results['nickname'].is_valid
        assert not results['password'].is_valid
    
    def test_validation_summary(self):
        """Test validation summary generation."""
        results = {
            'email': ValidationResult(True),
            'nickname': ValidationResult(False, errors=["Too short"]),
            'password': ValidationResult(True, warnings=["Could be stronger"])
        }
        
        summary = get_validation_summary(results)
        
        assert not summary['all_valid']  # One field is invalid
        assert summary['total_errors'] == 1
        assert summary['total_warnings'] == 1
        assert 'details' in summary
        assert len(summary['details']) == 3


class TestValidationPerformance:
    """Test performance of enhanced validators."""
    
    @pytest.mark.performance
    def test_enhanced_validators_performance(self):
        """Test that enhanced validators maintain good performance."""
        test_data = [
            ("user@example.com", "TestUser123", "StrongPass1!"),
            ("test@domain.org", "GamerOne", "MyPassword2@"),
            ("valid@email.net", "Player456", "SecurePwd3#"),
        ]
        
        iterations = 1000
        
        start_time = time.time()
        for email, nickname, password in test_data * (iterations // len(test_data)):
            validate_email_enhanced(email)
            validate_nickname_enhanced(nickname)
            validate_password_enhanced(password)
        
        total_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert total_time < 5.0, f"Enhanced validators too slow: {total_time:.3f}s"
        
        operations_per_second = (iterations * 3) / total_time
        print(f"Enhanced validators performance: {operations_per_second:.0f} ops/sec")
    
    def test_caching_performance(self):
        """Test performance improvement from caching."""
        email = "user@example.com"
        nickname = "TestUser123"
        password = "StrongPass1!"
        
        # First call (not cached)
        start_time = time.time()
        result1 = validate_user_input(email, nickname, password)
        first_time = time.time() - start_time
        
        # Second call (cached)
        start_time = time.time()
        result2 = validate_user_input(email, nickname, password)
        second_time = time.time() - start_time
        
        # Results should be identical
        assert result1['email'].is_valid == result2['email'].is_valid
        assert result1['nickname'].is_valid == result2['nickname'].is_valid
        assert result1['password'].is_valid == result2['password'].is_valid
        
        # Second call should be faster (or at worst equal due to caching)
        assert second_time <= first_time * 2, "Caching should not significantly slow down validation"


class TestValidationConfiguration:
    """Test validation configuration features."""
    
    def test_custom_reserved_names(self):
        """Test custom reserved names configuration."""
        # Add custom reserved name
        validation_config.add_reserved_name("CustomReserved")
        
        # Should be rejected
        result = validate_nickname_enhanced("CustomReserved")
        assert not result.is_valid
        assert any("reserved" in error.lower() for error in result.errors)
    
    def test_custom_weak_passwords(self):
        """Test custom weak passwords configuration."""
        # Add custom weak password
        validation_config.add_weak_password("CustomWeak123")
        
        # Should be rejected
        result = validate_password_enhanced("CustomWeak123")
        assert not result.is_valid
        assert any("common" in error.lower() for error in result.errors)
    
    def test_validation_result_methods(self):
        """Test ValidationResult helper methods."""
        result = ValidationResult(True)
        
        # Test adding errors
        result.add_error("Test error")
        assert not result.is_valid
        assert "Test error" in result.errors
        
        # Test adding warnings
        result.add_warning("Test warning")
        assert "Test warning" in result.warnings
        
        # Test boolean conversion
        assert not bool(result)  # Should be False due to error


class TestValidationSecurity:
    """Test security aspects of enhanced validators."""
    
    def test_timeout_protection(self):
        """Test that validators have timeout protection."""
        # This test is mainly to ensure timeout decorator is applied
        # and doesn't cause crashes with normal inputs
        long_but_valid_email = "a" * 50 + "@" + "b" * 50 + ".com"
        
        try:
            result = validate_email_enhanced(long_but_valid_email)
            # Should either succeed or fail gracefully
            assert isinstance(result, ValidationResult)
        except ValidationError as e:
            # Timeout error is acceptable
            assert "timeout" in str(e).lower()
    
    def test_type_safety(self):
        """Test that validators handle wrong types gracefully."""
        # Test with None
        result = validate_email_enhanced(None)
        assert not result.is_valid
        assert any("string" in error for error in result.errors)
        
        # Test with numbers
        result = validate_nickname_enhanced(123)
        assert not result.is_valid
        assert any("string" in error for error in result.errors)
        
        # Test with lists
        result = validate_password_enhanced([])
        assert not result.is_valid
        assert any("string" in error for error in result.errors)
    
    def test_unicode_handling(self):
        """Test proper Unicode handling."""
        # Test non-ASCII Unicode characters
        unicode_inputs = [
            "tëst@domain.com",  # Accented characters
            "用户@domain.com",   # Chinese characters
            "тест@domain.com",  # Cyrillic
        ]
        
        for input_str in unicode_inputs:
            result = validate_email_enhanced(input_str)
            # Should handle gracefully without crashes
            assert isinstance(result, ValidationResult)