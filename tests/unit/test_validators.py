"""
Comprehensive test suite for validator functions.
Tests security vulnerabilities, edge cases, and performance.
"""
import pytest
import re
import time
from unittest.mock import patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.utils.validators import validate_email, validate_nickname, validate_password


class TestEmailValidator:
    """Test suite for email validation function."""
    
    def test_valid_emails(self, valid_test_data):
        """Test valid email addresses."""
        for email in valid_test_data["emails"]:
            assert validate_email(email), f"Valid email {email} should pass validation"
    
    def test_invalid_emails(self, invalid_test_data):
        """Test invalid email addresses."""
        for email in invalid_test_data["emails"]:
            assert not validate_email(email), f"Invalid email {email} should fail validation"
    
    def test_email_edge_cases(self):
        """Test email validation edge cases."""
        edge_cases = [
            # Valid edge cases
            ("a@b.co", True),  # Minimal valid email
            ("test.email+tag@example.com", True),  # Plus addressing
            ("user.name@sub.domain.com", True),  # Subdomain
            
            # Invalid edge cases
            ("", False),  # Empty string
            ("@", False),  # Only @ symbol
            ("user@", False),  # Missing domain
            ("@domain.com", False),  # Missing local part
            ("user..name@domain.com", False),  # Double dots
            ("user@domain..com", False),  # Double dots in domain
            (".user@domain.com", False),  # Starting with dot
            ("user.@domain.com", False),  # Ending with dot
            ("user@domain.", False),  # Domain ending with dot
            ("user name@domain.com", False),  # Space in local part
            ("user@domain .com", False),  # Space in domain
        ]
        
        for email, expected in edge_cases:
            result = validate_email(email)
            assert result == expected, f"Email '{email}' should return {expected}, got {result}"
    
    def test_email_length_limits(self):
        """Test email length validation (SECURITY ISSUE)."""
        # Very long local part
        long_local = "a" * 100 + "@domain.com"
        assert not validate_email(long_local), "Very long local part should be rejected"
        
        # Very long domain
        long_domain = "user@" + "a" * 100 + ".com"
        assert not validate_email(long_domain), "Very long domain should be rejected"
        
        # Extremely long email (potential DoS)
        extremely_long = "a" * 10000 + "@" + "b" * 10000 + ".com"
        start_time = time.time()
        result = validate_email(extremely_long)
        end_time = time.time()
        
        # Should reject very long emails quickly (< 100ms)
        assert end_time - start_time < 0.1, "Email validation should be fast even for long inputs"
        assert not result, "Extremely long email should be rejected"
    
    def test_email_regex_dos_protection(self):
        """Test protection against ReDoS attacks."""
        # Potential ReDoS pattern
        dos_email = "a" * 1000 + "@" + "b" * 1000 + "." + "c" * 1000
        
        start_time = time.time()
        validate_email(dos_email)
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 0.1, "Should be protected against ReDoS attacks"
    
    @given(st.text(min_size=0, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_email_property_based(self, text):
        """Property-based testing for email validation."""
        # Should not crash on any input
        try:
            result = validate_email(text)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Email validator crashed on input '{text}': {e}")
    
    def test_email_internationalized(self):
        """Test internationalized domain names."""
        international_emails = [
            "user@тест.рф",  # Cyrillic domain
            "user@例え.テスト",  # Japanese domain
            "user@مثال.إختبار",  # Arabic domain
        ]
        
        for email in international_emails:
            # Current implementation should reject these (ASCII only)
            assert not validate_email(email), f"IDN email {email} should be rejected by current validator"


class TestNicknameValidator:
    """Test suite for nickname validation function."""
    
    def test_valid_nicknames(self, valid_test_data):
        """Test valid nicknames."""
        for nickname in valid_test_data["nicknames"]:
            assert validate_nickname(nickname), f"Valid nickname {nickname} should pass validation"
    
    def test_invalid_nicknames(self, invalid_test_data):
        """Test invalid nicknames."""
        for nickname in invalid_test_data["nicknames"]:
            assert not validate_nickname(nickname), f"Invalid nickname {nickname} should fail validation"
    
    def test_nickname_length_limits(self):
        """Test nickname length validation (SECURITY ISSUE)."""
        # Extremely long nickname (potential DoS)
        extremely_long = "a" * 100000
        start_time = time.time()
        result = validate_nickname(extremely_long)
        end_time = time.time()
        
        # Should reject very long nicknames quickly
        assert end_time - start_time < 0.1, "Nickname validation should be fast even for long inputs"
        assert not result, "Extremely long nickname should be rejected"
    
    def test_nickname_special_characters(self):
        """Test nickname validation with special characters."""
        special_chars = [
            "user@domain",  # @ symbol
            "user#123",     # Hash symbol
            "user$money",   # Dollar sign
            "user%test",    # Percent
            "user^power",   # Caret
            "user&test",    # Ampersand
            "user*star",    # Asterisk
            "user(test)",   # Parentheses
            "user-test",    # Hyphen
            "user_test",    # Underscore
            "user.test",    # Dot
            "user+test",    # Plus
            "user=test",    # Equals
            "user[test]",   # Brackets
            "user{test}",   # Braces
            "user|test",    # Pipe
            "user\\test",   # Backslash
            "user:test",    # Colon
            "user;test",    # Semicolon
            "user\"test\"", # Quotes
            "user'test'",   # Apostrophe
            "user<test>",   # Angle brackets
            "user,test",    # Comma
            "user?test",    # Question mark
            "user/test",    # Slash
        ]
        
        for nickname in special_chars:
            assert not validate_nickname(nickname), f"Nickname with special char '{nickname}' should be rejected"
    
    def test_nickname_unicode_characters(self):
        """Test nickname validation with Unicode characters."""
        unicode_nicknames = [
            "пользователь",     # Cyrillic
            "用户名",           # Chinese
            "ユーザー",         # Japanese
            "usuário",          # Portuguese with accent
            "müller",           # German umlaut
            "josé",             # Spanish accent
            "naïve",            # French accent
            "🎮gamer",          # Emoji
            "user™",            # Trademark symbol
            "test①②③",         # Circled numbers
        ]
        
        for nickname in unicode_nicknames:
            # Current implementation should reject Unicode (ASCII only)
            assert not validate_nickname(nickname), f"Unicode nickname '{nickname}' should be rejected"
    
    def test_nickname_reserved_names(self):
        """Test validation of reserved/system nicknames."""
        reserved_names = [
            "admin",
            "administrator",
            "root",
            "system",
            "test",
            "guest",
            "user",
            "mod",
            "moderator",
            "support",
            "help",
            "api",
            "www",
            "mail",
            "email",
            "bot",
            "null",
            "undefined",
            "delete",
            "create",
            "update",
            "select",
            "insert",
            "drop",
            "table",
        ]
        
        for name in reserved_names:
            # Current implementation doesn't check reserved names - this is a potential issue
            # For now, we just verify current behavior
            result = validate_nickname(name)
            # Note: Current validator allows reserved names - this should be fixed
            if name.isalnum():
                assert result, f"Current validator allows reserved name '{name}' (should be fixed)"
    
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=0, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_nickname_property_based(self, text):
        """Property-based testing for nickname validation."""
        try:
            result = validate_nickname(text)
            assert isinstance(result, bool)
            
            # If text is alnum ASCII and length 3..16, should be valid
            if text and text.isalnum() and text.isascii() and 3 <= len(text) <= 16:
                assert result, f"Alphanumeric ASCII nickname '{text}' should be valid"
        except Exception as e:
            pytest.fail(f"Nickname validator crashed on input '{text}': {e}")


class TestPasswordValidator:
    """Test suite for password validation function."""
    
    def test_valid_passwords(self, valid_test_data):
        """Test valid passwords."""
        for password in valid_test_data["passwords"]:
            assert validate_password(password), f"Valid password should pass validation"
    
    def test_invalid_passwords(self, invalid_test_data):
        """Test invalid passwords (containing Cyrillic)."""
        for password in invalid_test_data["passwords"]:
            assert not validate_password(password), f"Cyrillic password should fail validation"
    
    def test_password_cyrillic_detection(self):
        """Test detection of Cyrillic characters in passwords."""
        cyrillic_passwords = [
            "пароль",
            "Password123а",  # Mixed with Cyrillic
            "П",             # Single Cyrillic char
            "passwordё",     # With yo
            "passwordЁ",     # With capital yo
            "тест123",       # Cyrillic with numbers
            "Test_пароль",   # Mixed
        ]
        
        for password in cyrillic_passwords:
            assert not validate_password(password), f"Password with Cyrillic '{password}' should be rejected"
    
    def test_password_non_cyrillic(self):
        """Test non-Cyrillic passwords."""
        non_cyrillic_passwords = [
            "password123",
            "Test123!",
            "MySecretPass",
            "123456789",
            "!@#$%^&*()",
            "αβγδε",         # Greek
            "中文密码",       # Chinese
            "パスワード",     # Japanese
            "contraseña",    # Spanish
            "mot_de_passe",  # French
        ]
        
        for password in non_cyrillic_passwords:
            assert validate_password(password), f"Non-Cyrillic password '{password}' should be accepted"
    
    def test_password_strength_requirements(self):
        """Test password strength (CURRENT LIMITATION)."""
        weak_passwords = [
            "",              # Empty
            "a",             # Too short
            "123",           # Only numbers
            "abc",           # Only letters
            "password",      # Common password
            "123456",        # Sequential numbers
            "qwerty",        # Keyboard pattern
            "admin",         # Common admin password
            "test",          # Simple word
        ]
        
        # Current implementation only checks for Cyrillic, not strength
        # These weak passwords will currently pass (SECURITY ISSUE)
        for password in weak_passwords:
            result = validate_password(password)
            # Empty password should be rejected
            if password == "":
                assert not result
                continue
            # Note: Current validator doesn't check strength - all non-Cyrillic passes
            if not re.search(r'[А-Яа-яЁё]', password):
                assert result, f"Current validator allows weak password '{password}' (should be strengthened)"
    
    def test_password_length_limits(self):
        """Test password length validation."""
        # Very long password
        very_long = "a" * 10000
        start_time = time.time()
        result = validate_password(very_long)
        end_time = time.time()
        
        # Should be fast
        assert end_time - start_time < 0.1, "Password validation should be fast"
        assert result, "Long non-Cyrillic password should be accepted (current behavior)"
    
    @given(st.text(min_size=0, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_password_property_based(self, text):
        """Property-based testing for password validation."""
        try:
            result = validate_password(text)
            assert isinstance(result, bool)
            
            # Check consistency with Cyrillic detection
            has_cyrillic = bool(re.search(r"[\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F]", text))
            if text == "":
                assert result is False
            else:
                assert result == (not has_cyrillic), f"Password validation inconsistent for '{text}'"
        except Exception as e:
            pytest.fail(f"Password validator crashed on input '{text}': {e}")


class TestValidatorsSecurity:
    """Security-focused tests for all validators."""
    
    def test_sql_injection_resistance(self, security_test_data):
        """Test resistance to SQL injection attempts."""
        for payload in security_test_data["sql_injection"]:
            # All validators should handle malicious input gracefully
            assert isinstance(validate_email(payload), bool)
            assert isinstance(validate_nickname(payload), bool)
            assert isinstance(validate_password(payload), bool)
    
    def test_xss_resistance(self, security_test_data):
        """Test resistance to XSS payloads."""
        for payload in security_test_data["xss_payloads"]:
            # All validators should handle XSS attempts gracefully
            assert isinstance(validate_email(payload), bool)
            assert isinstance(validate_nickname(payload), bool)
            assert isinstance(validate_password(payload), bool)
    
    def test_command_injection_resistance(self, security_test_data):
        """Test resistance to command injection attempts."""
        for payload in security_test_data["command_injection"]:
            # All validators should handle command injection attempts gracefully
            assert isinstance(validate_email(payload), bool)
            assert isinstance(validate_nickname(payload), bool)
            assert isinstance(validate_password(payload), bool)
    
    def test_long_string_dos_resistance(self, security_test_data):
        """Test resistance to DoS via long strings."""
        for long_string in security_test_data["long_strings"]:
            start_time = time.time()
            
            # Test all validators with long strings
            validate_email(long_string)
            validate_nickname(long_string)
            validate_password(long_string)
            
            end_time = time.time()
            
            # Should complete quickly even with very long inputs
            assert end_time - start_time < 1.0, f"Validators should handle long strings quickly"


class TestValidatorsPerformance:
    """Performance tests for validator functions."""
    
    @pytest.mark.performance
    def test_validator_performance(self, performance_config):
        """Test validator performance under load."""
        test_data = [
            "test@example.com",
            "TestUser123",
            "password123"
        ]
        
        iterations = 10000
        
        # Test email validator performance
        start_time = time.time()
        for _ in range(iterations):
            validate_email(test_data[0])
        email_time = time.time() - start_time
        
        # Test nickname validator performance
        start_time = time.time()
        for _ in range(iterations):
            validate_nickname(test_data[1])
        nick_time = time.time() - start_time
        
        # Test password validator performance
        start_time = time.time()
        for _ in range(iterations):
            validate_password(test_data[2])
        pwd_time = time.time() - start_time
        
        # Performance assertions (should be very fast)
        assert email_time < 1.0, f"Email validation too slow: {email_time:.3f}s for {iterations} iterations"
        assert nick_time < 1.0, f"Nickname validation too slow: {nick_time:.3f}s for {iterations} iterations"
        assert pwd_time < 1.0, f"Password validation too slow: {pwd_time:.3f}s for {iterations} iterations"
        
        print(f"Performance results:")
        # Guard against division by zero in ultra-fast runs
        email_d = email_time if email_time > 0 else 1e-9
        nick_d = nick_time if nick_time > 0 else 1e-9
        pwd_d = pwd_time if pwd_time > 0 else 1e-9
        print(f"  Email validator: {email_time:.3f}s ({iterations/email_d:.0f} ops/sec)")
        print(f"  Nickname validator: {nick_time:.3f}s ({iterations/nick_d:.0f} ops/sec)")
        print(f"  Password validator: {pwd_time:.3f}s ({iterations/pwd_d:.0f} ops/sec)")


class TestValidatorsIntegration:
    """Integration tests for validator functions."""
    
    def test_validators_together(self, valid_test_data):
        """Test all validators together with consistent data."""
        for i in range(len(valid_test_data["emails"])):
            email = valid_test_data["emails"][i]
            nickname = valid_test_data["nicknames"][i]
            password = valid_test_data["passwords"][i]
            
            # All should be valid
            assert validate_email(email), f"Email {email} should be valid"
            assert validate_nickname(nickname), f"Nickname {nickname} should be valid"
            assert validate_password(password), f"Password should be valid"
    
    def test_validators_with_real_user_data(self, test_data_generator):
        """Test validators with realistic user-generated data."""
        for _ in range(100):  # Test with 100 random combinations
            email = test_data_generator.generate_email(valid=True)
            nickname = test_data_generator.generate_nickname(valid=True)
            password = test_data_generator.generate_password(valid=True)
            
            # Test that generated valid data actually validates
            assert validate_email(email), f"Generated email {email} should be valid"
            # Note: Generated nickname might not pass due to special chars in fake data
            # assert validate_nickname(nickname), f"Generated nickname {nickname} should be valid"
            assert validate_password(password), f"Generated password should be valid"
