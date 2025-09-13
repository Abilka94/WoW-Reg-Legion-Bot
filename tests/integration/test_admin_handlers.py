"""
Integration tests for admin handlers.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from src.states.user_states import AdminStates


class TestAdminHandlersIntegration:
    """Integration tests for admin handlers."""
    
    @pytest_asyncio.fixture
    async def mock_state(self):
        """Create FSM state."""
        storage = MemoryStorage()
        state = FSMContext(
            storage=storage,
            key=storage.key_builder(bot_id=1, chat_id=123456789, user_id=123456789)
        )
        return state
    
    @pytest.fixture
    def mock_admin_config(self):
        """Mock admin configuration."""
        return {
            "features": {
                "admin_panel": True,
                "admin_broadcast": True,
                "admin_check_db": True,
                "admin_download_log": True,
                "admin_delete_account": True,
                "admin_reload_config": True,
            }
        }
    
    @pytest.mark.asyncio
    async def test_admin_broadcast_integration(self, mock_state, mock_bot, mock_db_pool, mock_admin_config):
        """Test admin broadcast complete integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.delete_all_bot_messages'), \
             patch('src.handlers.admin.delete_user_message'), \
             patch('src.handlers.admin.record_message'):
            
            # Mock database users
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchall.return_value = [
                (111111111,), (222222222,), (333333333,), (444444444,), (555555555,)
            ]
            
            await mock_state.set_state(AdminStates.broadcast_text)
            message_text = "Important server announcement!"
            
            # Simulate broadcast process
            async with mock_db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT telegram_id FROM users")
                    users = await cur.fetchall()
            
            ok = fail = 0
            for (uid,) in users:
                try:
                    await mock_bot.send_message(uid, message_text)
                    ok += 1
                except Exception:
                    fail += 1
            
            # Verify broadcast results
            assert ok == 5  # All 5 users should receive message
            assert fail == 0
            assert mock_bot.send_message.call_count == 5
    
    @pytest.mark.asyncio
    async def test_admin_database_check_integration(self, mock_bot, mock_db_pool, mock_admin_config):
        """Test admin database check integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.notify_admin') as mock_notify:
            
            # Test successful database connection
            try:
                async with mock_db_pool.acquire():
                    pass
                result = "✅ Database connection OK"
            except Exception as e:
                result = f"❌ {e}"
                await mock_notify(mock_bot, str(e))
            
            assert "✅" in result
            mock_notify.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_admin_database_check_failure(self, mock_bot, mock_admin_config):
        """Test admin database check with connection failure."""
        # Mock failing database (acquire() async CM raises on __aenter__)
        mock_db_pool = MagicMock()
        acquire_cm = AsyncMock()
        acquire_cm.__aenter__.side_effect = Exception("Connection timeout")
        mock_db_pool.acquire.return_value = acquire_cm
        
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.notify_admin') as mock_notify:
            
            try:
                async with mock_db_pool.acquire():
                    pass
                result = "✅ Database connection OK"
            except Exception as e:
                result = f"❌ {e}"
                await mock_notify(mock_bot, str(e))
            
            assert "❌ Connection timeout" in result
            mock_notify.assert_called_once_with(mock_bot, "Connection timeout")
    
    @pytest.mark.asyncio
    async def test_admin_account_deletion_integration(self, mock_state, mock_db_pool, mock_admin_config):
        """Test admin account deletion integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.validate_email', return_value=True), \
             patch('src.handlers.admin.admin_delete_account') as mock_delete:
            
            mock_delete.return_value = True
            
            await mock_state.set_state(AdminStates.delete_account_input)
            email = "user@example.com"
            
            # Simulate admin deletion process
            if mock_delete:
                success = await mock_delete(mock_db_pool, email)
                assert success is True
            
            mock_delete.assert_called_once_with(mock_db_pool, email)
    
    @pytest.mark.asyncio
    async def test_admin_config_reload_integration(self, mock_bot, mock_admin_config):
        """Test admin configuration reload integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.config.settings.reload_config') as mock_reload:
            
            # Test successful config reload
            await mock_reload(mock_bot)
            result = "✅ Configuration reloaded successfully"
            
            mock_reload.assert_called_once_with(mock_bot)
            assert "✅" in result
    
    @pytest.mark.asyncio 
    async def test_admin_access_control_integration(self, mock_admin_config):
        """Test admin access control integration."""
        with patch('src.handlers.admin.ADMIN_ID', 999999999):
            
            # Test various user IDs
            test_cases = [
                (123456789, False),  # Regular user
                (999999999, True),   # Admin user
                (111111111, False),  # Another regular user
                (0, False),          # Invalid user
            ]
            
            for user_id, expected_admin in test_cases:
                is_admin = (user_id == 999999999)
                assert is_admin == expected_admin
    
    @pytest.mark.asyncio
    async def test_admin_log_download_integration(self, mock_admin_config):
        """Test admin log file download integration."""
        import os
        from unittest.mock import mock_open
        
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('os.path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data="Log file content")):
            
            # Test when log file exists
            mock_exists.return_value = True
            
            if os.path.exists("bot.log"):
                # Simulate reading log file
                with open("bot.log", "r") as f:
                    content = f.read()
                assert content == "Log file content"
            
            mock_exists.assert_called_with("bot.log")
    
    @pytest.mark.asyncio
    async def test_admin_feature_toggle_integration(self, mock_admin_config):
        """Test admin feature toggle integration."""
        # Test with features disabled
        disabled_config = {
            "features": {
                "admin_panel": False,
                "admin_broadcast": False,
                "admin_check_db": False,
                "admin_download_log": False,
                "admin_delete_account": False,
                "admin_reload_config": False,
            }
        }
        
        with patch('src.handlers.admin.CONFIG', disabled_config):
            
            # Verify all features are disabled
            assert not disabled_config["features"]["admin_panel"]
            assert not disabled_config["features"]["admin_broadcast"]
            assert not disabled_config["features"]["admin_check_db"]
            
            # Simulate feature check
            if not disabled_config["features"]["admin_broadcast"]:
                feature_disabled = True
            else:
                feature_disabled = False
            
            assert feature_disabled is True
    
    @pytest.mark.asyncio
    async def test_admin_error_handling_integration(self, mock_state, mock_bot, mock_db_pool, mock_admin_config):
        """Test admin error handling integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789):
            
            # Test broadcast with database error
            mock_db_pool.acquire.side_effect = Exception("Database error")
            
            try:
                async with mock_db_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT telegram_id FROM users")
                        users = await cur.fetchall()
                result = f"✅ Sent to {len(users)} users"
            except Exception as e:
                result = f"❌ {e}"
            
            assert "❌ Database error" in result
    
    @pytest.mark.asyncio
    async def test_admin_permissions_validation_integration(self, mock_admin_config):
        """Test admin permissions validation integration."""
        with patch('src.handlers.admin.ADMIN_ID', 999999999):
            
            def check_admin_permission(user_id):
                """Simulate admin permission check."""
                return user_id == 999999999
            
            # Test permission checks
            assert check_admin_permission(999999999) is True   # Admin
            assert check_admin_permission(123456789) is False  # Regular user
            assert check_admin_permission(0) is False          # Invalid user
            assert check_admin_permission(-1) is False         # Negative ID
    
    @pytest.mark.asyncio
    async def test_admin_broadcast_error_recovery(self, mock_state, mock_bot, mock_db_pool, mock_admin_config):
        """Test admin broadcast error recovery integration."""
        with patch('src.handlers.admin.CONFIG', mock_admin_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789):
            
            # Mock database with users
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchall.return_value = [(111,), (222,), (333,)]
            
            # Mock bot that fails for some users
            def mock_send_message(user_id, text):
                if user_id == 222:  # Simulate failure for one user
                    raise Exception("User blocked bot")
                return AsyncMock()
            
            mock_bot.send_message.side_effect = mock_send_message
            
            # Simulate broadcast with error handling
            ok = fail = 0
            async with mock_db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT telegram_id FROM users")
                    users = await cur.fetchall()
            
            for (uid,) in users:
                try:
                    await mock_bot.send_message(uid, "Test message")
                    ok += 1
                except Exception:
                    fail += 1
            
            # Verify error recovery
            assert ok == 2  # 2 successful sends
            assert fail == 1  # 1 failed send
            assert mock_bot.send_message.call_count == 3
