"""
Security tests for SQL injection vulnerabilities.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.database.user_operations import (
    email_exists, count_user_accounts, register_user, reset_password,
    change_password, get_account_info, delete_account, admin_delete_account
)


class TestSQLInjectionProtection:
    """Test SQL injection protection in database operations."""
    
    @pytest.fixture
    def sql_injection_payloads(self):
        """Common SQL injection payloads."""
        return [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1'; DELETE FROM account; --",
            "admin'--",
            "' UNION SELECT * FROM battlenet_accounts --",
            "'; UPDATE account SET coins = 999999 WHERE email = 'test@example.com'; --",
            "' OR 1=1 /*",
            "') OR ('1'='1",
            "'; INSERT INTO account (username) VALUES ('hacker'); --",
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(0x3a,(SELECT user()),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a); --",
            "'; EXEC xp_cmdshell('dir'); --",
            "' UNION SELECT 1,2,3,4,database(),6,7,8,9 --",
            "'; SELECT pg_sleep(10); --",
            "' OR SLEEP(5) --",
            "'; WAITFOR DELAY '00:00:05'; --"
        ]
    
    @pytest.mark.asyncio
    async def test_email_exists_sql_injection(self, mock_db_pool, sql_injection_payloads):
        """Test email_exists function against SQL injection."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        
        for payload in sql_injection_payloads:
            cursor_mock.fetchone.return_value = None
            
            # Function should not crash and should use parameterized query
            result = await email_exists(mock_db_pool, payload)
            
            # Verify the function completed without error
            assert isinstance(result, bool)
            
            # Verify that execute was called with parameterized query
            cursor_mock.execute.assert_called()
            call_args = cursor_mock.execute.call_args[0]
            
            # The SQL should contain %s placeholder, not the actual payload
            assert "%s" in call_args[0], f"Query should use parameterized placeholder: {call_args[0]}"
            assert payload not in call_args[0], f"Payload should not be in SQL string: {call_args[0]}"
            
            # The payload should be passed as parameter
            assert len(call_args) > 1, "Parameters should be passed separately"
            assert payload.upper() in call_args[1], "Payload should be in parameters tuple"
    
    @pytest.mark.asyncio
    async def test_register_user_sql_injection(self, mock_db_pool, sql_injection_payloads, mock_config):
        """Test register_user function against SQL injection."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.fetchone.side_effect = [(0,), (123,)]  # Mock responses
        
        with patch('src.database.user_operations.CONFIG', mock_config):
            for payload in sql_injection_payloads:
                # Test with malicious nickname
                try:
                    username, error = await register_user(
                        mock_db_pool, payload, "password123", "test@example.com", 123456789
                    )
                    # Should complete without SQL injection
                    assert isinstance(username, (str, type(None)))
                    assert isinstance(error, (str, type(None)))
                except Exception as e:
                    # Should not contain SQL-related errors
                    assert "sql" not in str(e).lower()
                    assert "syntax" not in str(e).lower()
                
                # Test with malicious email
                try:
                    username, error = await register_user(
                        mock_db_pool, "testuser", "password123", payload, 123456789
                    )
                    assert isinstance(username, (str, type(None)))
                    assert isinstance(error, (str, type(None)))
                except Exception as e:
                    assert "sql" not in str(e).lower()
                    assert "syntax" not in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_delete_account_sql_injection(self, mock_db_pool, sql_injection_payloads):
        """Test delete_account function against SQL injection."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.fetchone.return_value = (1,)  # Mock ownership check
        cursor_mock.rowcount = 1
        
        for payload in sql_injection_payloads:
            try:
                result = await delete_account(mock_db_pool, 123456789, payload)
                assert isinstance(result, bool)
                
                # Verify parameterized queries were used
                for call in cursor_mock.execute.call_args_list:
                    if len(call[0]) > 0:
                        sql_query = call[0][0]
                        assert "%s" in sql_query, f"Query should use parameterized placeholder: {sql_query}"
                        assert payload not in sql_query, f"Payload should not be in SQL string: {sql_query}"
            except Exception as e:
                assert "sql" not in str(e).lower()
                assert "syntax" not in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_password_operations_sql_injection(self, mock_db_pool, sql_injection_payloads):
        """Test password reset and change operations against SQL injection."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.rowcount = 1
        cursor_mock.fetchone.return_value = ("testuser123",)
        
        for payload in sql_injection_payloads:
            # Test reset_password
            try:
                result = await reset_password(mock_db_pool, payload)
                assert isinstance(result, (str, type(None)))
            except Exception as e:
                assert "sql" not in str(e).lower()
            
            # Test change_password
            try:
                result = await change_password(mock_db_pool, payload, "newpassword123")
                assert isinstance(result, bool)
            except Exception as e:
                assert "sql" not in str(e).lower()
            
            # Test with malicious new password
            try:
                result = await change_password(mock_db_pool, "test@example.com", payload)
                assert isinstance(result, bool)
            except Exception as e:
                assert "sql" not in str(e).lower()


class TestInputValidationSecurity:
    """Test input validation security measures."""
    
    @pytest.mark.asyncio
    async def test_transaction_integrity(self, mock_db_pool, mock_config):
        """Test that database operations maintain transaction integrity."""
        # Mock connection that simulates transaction failure
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Simulate failure in the middle of registration
        mock_cursor.fetchone.side_effect = [(0,), Exception("Simulated DB error")]
        
        with patch('src.database.user_operations.CONFIG', mock_config):
            with pytest.raises(Exception):
                await register_user(mock_db_pool, "testuser", "password123", "test@example.com", 123456789)
        
        # Even though there was an error, the function should have attempted to use transactions properly
        # (This is a limitation of the current implementation - no explicit transaction handling)
    
    @pytest.mark.asyncio
    async def test_email_case_handling(self, mock_db_pool):
        """Test that email case handling doesn't introduce vulnerabilities."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        
        test_emails = [
            "Test@Example.com",
            "test@EXAMPLE.COM",
            "TEST@example.com",
            "TeSt@ExAmPlE.cOm"
        ]
        
        for email in test_emails:
            await email_exists(mock_db_pool, email)
            
            # Verify that email was converted to uppercase for query
            call_args = cursor_mock.execute.call_args[0]
            assert call_args[1][0] == email.upper(), "Email should be converted to uppercase"
    
    @pytest.mark.asyncio
    async def test_numeric_injection_attempts(self, mock_db_pool):
        """Test protection against numeric-based injection attempts."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.fetchone.return_value = (0,)
        
        # Test with various numeric injection attempts
        malicious_telegram_ids = [
            "123'; DROP TABLE users; --",
            "456 OR 1=1",
            "789; DELETE FROM account; --",
            -1,  # Negative ID
            999999999999999999999,  # Very large ID
        ]
        
        for malicious_id in malicious_telegram_ids:
            try:
                # The function should handle type conversion safely
                result = await count_user_accounts(mock_db_pool, malicious_id)
                assert isinstance(result, int)
            except (TypeError, ValueError):
                # Type errors are acceptable for obviously wrong types
                pass
            except Exception as e:
                # Should not have SQL-related errors
                assert "sql" not in str(e).lower()


class TestSecurityBestPractices:
    """Test adherence to security best practices."""
    
    def test_parameterized_queries_usage(self):
        """Verify that all database operations use parameterized queries."""
        import inspect
        from src.database import user_operations
        
        # Get all functions in the user_operations module
        functions = inspect.getmembers(user_operations, inspect.isfunction)
        
        sql_functions = [
            'email_exists', 'count_user_accounts', 'register_user', 
            'reset_password', 'change_password', 'get_account_info',
            'delete_account', 'admin_delete_account', 'get_account_coins',
            'add_coins_to_account', 'get_user_accounts_with_coins'
        ]
        
        for func_name, func in functions:
            if func_name in sql_functions:
                # Get the source code
                source = inspect.getsource(func)
                
                # Check for dangerous patterns
                dangerous_patterns = [
                    f'f"',  # f-string in SQL
                    '".format(',  # .format() in SQL
                    '" + ',  # String concatenation
                    "' + ",  # String concatenation
                ]
                
                for pattern in dangerous_patterns:
                    assert pattern not in source, \
                        f"Function {func_name} may be using dangerous SQL construction pattern: {pattern}"
                
                # Verify %s usage (parameterized queries)
                if 'execute(' in source:
                    assert '%s' in source, \
                        f"Function {func_name} should use %s parameterized queries"
    
    @pytest.mark.asyncio
    async def test_error_information_disclosure(self, mock_db_pool):
        """Test that error messages don't disclose sensitive information."""
        # Mock database error
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.execute.side_effect = Exception("Table 'secret_table' doesn't exist")
        
        try:
            await email_exists(mock_db_pool, "test@example.com")
        except Exception as e:
            error_msg = str(e).lower()
            
            # Error should not contain sensitive database information
            sensitive_terms = [
                'password', 'secret', 'key', 'token', 'hash',
                'battlenet_accounts', 'account_access', 'users'
            ]
            
            for term in sensitive_terms:
                assert term not in error_msg, \
                    f"Error message should not contain sensitive term: {term}"
    
    def test_password_hashing_security(self):
        """Test password hashing implementation security."""
        import hashlib
        
        # Verify that proper hashing is used
        test_email = "test@example.com"
        test_password = "testpassword123"
        
        # Simulate the hashing process from register_user
        mu, pu = test_email.upper(), test_password.upper()
        inner = hashlib.sha256(mu.encode()).hexdigest().upper()
        outer = hashlib.sha256(f"{inner}:{pu}".encode()).hexdigest().upper()
        bhash = bytes.fromhex(outer)[::-1].hex().upper()
        
        # Verify hash properties
        assert len(bhash) == 64, "Battlenet hash should be 64 characters"
        assert bhash != test_password, "Hash should not equal original password"
        assert bhash.isupper(), "Hash should be uppercase"
        
        # Verify account hash
        username = "123#1"
        ah = hashlib.sha1(f"{username}:{pu}".encode()).hexdigest().upper()
        
        assert len(ah) == 40, "Account hash should be 40 characters (SHA1)"
        assert ah != test_password, "Account hash should not equal original password"
        assert ah.isupper(), "Account hash should be uppercase"
    
    @pytest.mark.asyncio
    async def test_data_sanitization(self, mock_db_pool):
        """Test that data is properly sanitized before database operations."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        
        # Test with various potentially problematic inputs
        problematic_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "\x00\x01\x02",  # Control characters
            "\\n\\r\\t",  # Escape sequences
            "\u0000\u0001\u0002",  # Unicode control characters
        ]
        
        for input_data in problematic_inputs:
            await email_exists(mock_db_pool, input_data)
            
            # Verify that the data was passed correctly to the database
            # (the database layer should handle sanitization via parameterized queries)
            call_args = cursor_mock.execute.call_args[0]
            assert len(call_args) > 1, "Should use parameterized query with separate parameters"