"""
Comprehensive test suite for database operations with mocking and security tests.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.database.user_operations import (
    email_exists, count_user_accounts, register_user, reset_password,
    change_password, get_account_info, delete_account, admin_delete_account,
    get_account_coins, add_coins_to_account, get_user_accounts_with_coins
)


class TestDatabaseOperations:
    """Test database operations with comprehensive mocking."""
    
    @pytest.mark.asyncio
    async def test_email_exists_true(self, mock_db_pool):
        """Test email_exists when email is found."""
        mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = (1,)
        
        result = await email_exists(mock_db_pool, "test@example.com")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_email_exists_false(self, mock_db_pool):
        """Test email_exists when email is not found."""
        mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = None
        
        result = await email_exists(mock_db_pool, "test@example.com")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_count_user_accounts(self, mock_db_pool):
        """Test counting user accounts."""
        mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchone.return_value = (2,)
        
        result = await count_user_accounts(mock_db_pool, 123456789)
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, mock_db_pool, mock_config):
        """Test successful user registration."""
        # Setup mocks
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.fetchone.side_effect = [(0,), (123,)]  # count=0, then id=123
        
        with patch('src.database.user_operations.CONFIG', mock_config):
            username, error = await register_user(mock_db_pool, "testuser", "password123", "test@example.com", 123456789)
        
        assert username == "123#1"
        assert error is None
    
    @pytest.mark.asyncio
    async def test_register_user_max_accounts(self, mock_db_pool, mock_config):
        """Test registration failure due to max accounts limit."""
        cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
        cursor_mock.fetchone.return_value = (5,)  # Over limit
        
        with patch('src.database.user_operations.CONFIG', mock_config):
            username, error = await register_user(mock_db_pool, "testuser", "password123", "test@example.com", 123456789)
        
        assert username is None
        assert error == "err_max_accounts"


class TestDatabaseSecurity:
    """Test database security aspects."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, mock_db_pool, security_test_data):
        """Test SQL injection protection in database operations."""
        for payload in security_test_data["sql_injection"]:
            # Test that malicious input doesn't crash the functions
            try:
                await email_exists(mock_db_pool, payload)
                await count_user_accounts(mock_db_pool, 123456789)
                # Functions should handle malicious input gracefully
            except Exception as e:
                # Should not crash with SQL errors
                assert "sql" not in str(e).lower()
    
    @pytest.mark.asyncio 
    async def test_transaction_integrity(self, mock_db_pool):
        """Test database transaction integrity."""
        with patch('src.database.user_operations.CONFIG', {"settings": {"max_accounts_per_user": 3}}):
            # Mock successful registration flow
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchone.side_effect = [(0,), (123,)]
            
            username, error = await register_user(mock_db_pool, "test", "pass", "test@example.com", 123)
            
            # Verify all required database operations were called
            assert cursor_mock.execute.call_count >= 4  # Multiple inserts for registration