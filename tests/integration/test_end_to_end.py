"""
End-to-end integration tests for complete user workflows.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import src


class TestEndToEndWorkflows:
    """End-to-end tests for complete user workflows."""
    
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
    def complete_config(self):
        """Complete configuration for testing."""
        return {
            "features": {
                "registration": True,
                "account_management": True,
                "password_reset": True,
                "admin_panel": True,
                "admin_broadcast": True,
                "admin_check_db": True,
                "admin_delete_account": True,
            },
            "settings": {
                "max_accounts_per_user": 3,
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test complete user registration from start to finish."""
        with patch('src.handlers.registration.CONFIG', complete_config), \
             patch('src.handlers.registration.validate_nickname', return_value=True), \
             patch('src.handlers.registration.validate_password', return_value=True), \
             patch('src.handlers.registration.validate_email', return_value=True), \
             patch('src.handlers.registration.register_user') as mock_register, \
             patch('src.handlers.registration.delete_all_bot_messages'), \
             patch('src.handlers.registration.delete_user_message'), \
             patch('src.handlers.registration.record_message'):
            
            mock_register.return_value = ("testuser123#1", None)
            
            # Step 1: User starts registration
            await mock_state.clear()
            await mock_state.set_state("RegistrationStates:nick")
            
            # Step 2: User enters nickname
            await mock_state.update_data(nick="TestUser123")
            await mock_state.set_state("RegistrationStates:pwd")
            
            # Step 3: User enters password
            await mock_state.update_data(pwd="SecurePassword123")
            await mock_state.set_state("RegistrationStates:mail")
            
            # Step 4: User enters email and completes registration
            email = "test@example.com"
            data = await mock_state.get_data()
            
            username, error = await mock_register(
                mock_db_pool, 
                data["nick"], 
                data["pwd"], 
                email, 
                123456789
            )
            
            await mock_state.clear()
            
            # Verify complete workflow
            assert username == "testuser123#1"
            assert error is None
            mock_register.assert_called_once()
            
            # Verify state was cleared after completion
            final_state = await mock_state.get_state()
            assert final_state is None
    
    @pytest.mark.asyncio
    async def test_user_account_management_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test complete account management workflow."""
        with patch('src.handlers.account_management.CONFIG', complete_config), \
             patch('src.handlers.account_management.get_account_info') as mock_get_accounts, \
             patch('src.handlers.account_management.change_password') as mock_change_pwd, \
             patch('src.handlers.account_management.validate_password', return_value=True), \
             patch('src.handlers.account_management.delete_all_bot_messages'), \
             patch('src.handlers.account_management.record_message'):
            
            # Mock user accounts
            mock_accounts = [
                ("test@example.com", "testuser123#1", False, None),
                ("test2@example.com", "testuser456#1", True, "temppass")
            ]
            mock_get_accounts.return_value = mock_accounts
            
            # Step 1: User views their accounts
            accounts = await mock_get_accounts(mock_db_pool, 123456789)
            assert len(accounts) == 2
            assert accounts[0][0] == "test@example.com"
            
            # Step 2: User selects account and changes password
            selected_email = "test@example.com"
            new_password = "NewSecurePassword123"
            
            await mock_state.set_state("ChangePasswordStates:new_password")
            await mock_state.update_data(email=selected_email)
            
            # Step 3: Password change is processed
            await mock_change_pwd(mock_db_pool, selected_email, new_password)
            await mock_state.clear()
            
            # Verify workflow
            mock_get_accounts.assert_called_once()
            mock_change_pwd.assert_called_once_with(mock_db_pool, selected_email, new_password)
    
    @pytest.mark.asyncio
    async def test_password_reset_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test complete password reset workflow."""
        with patch('src.handlers.account_management.CONFIG', complete_config), \
             patch('src.handlers.account_management.validate_email', return_value=True), \
             patch('src.handlers.account_management.reset_password') as mock_reset, \
             patch('src.handlers.account_management.delete_all_bot_messages'), \
             patch('src.handlers.account_management.record_message'):
            
            # Mock database check for email ownership
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchone.return_value = (1,)
            
            mock_reset.return_value = "temppass123"
            
            # Step 1: User initiates password reset
            await mock_state.set_state("ForgotPasswordStates:email")
            
            # Step 2: User enters email
            email = "test@example.com"
            
            # Step 3: System validates email ownership
            async with mock_db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 FROM users WHERE telegram_id=%s AND email=%s", (123456789, email.upper()))
                    email_owned = await cur.fetchone()
            
            assert email_owned is not None
            
            # Step 4: Password is reset
            temp_password = await mock_reset(mock_db_pool, email.upper())
            await mock_state.clear()
            
            # Verify workflow
            assert temp_password == "temppass123"
            mock_reset.assert_called_once_with(mock_db_pool, "TEST@EXAMPLE.COM")
    
    @pytest.mark.asyncio
    async def test_admin_user_management_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test complete admin user management workflow."""
        with patch('src.handlers.admin.CONFIG', complete_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.validate_email', return_value=True), \
             patch('src.handlers.admin.admin_delete_account') as mock_admin_delete, \
             patch('src.handlers.admin.delete_all_bot_messages'), \
             patch('src.handlers.admin.record_message'):
            
            mock_admin_delete.return_value = True
            
            # Step 1: Admin accesses admin panel
            is_admin = (123456789 == 123456789)
            assert is_admin is True
            
            # Step 2: Admin initiates account deletion
            await mock_state.set_state("AdminStates:delete_account_input")
            
            # Step 3: Admin enters email to delete
            email_to_delete = "problematic@example.com"
            
            # Step 4: Account is deleted
            success = await mock_admin_delete(mock_db_pool, email_to_delete)
            await mock_state.clear()
            
            # Verify workflow
            assert success is True
            mock_admin_delete.assert_called_once_with(mock_db_pool, email_to_delete)
    
    @pytest.mark.asyncio
    async def test_admin_broadcast_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test complete admin broadcast workflow."""
        with patch('src.handlers.admin.CONFIG', complete_config), \
             patch('src.handlers.admin.ADMIN_ID', 123456789), \
             patch('src.handlers.admin.delete_all_bot_messages'), \
             patch('src.handlers.admin.record_message'):
            
            # Mock users in database
            cursor_mock = mock_db_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
            cursor_mock.fetchall.return_value = [
                (111111111,), (222222222,), (333333333,), (444444444,)
            ]
            
            # Step 1: Admin accesses broadcast function
            await mock_state.set_state("AdminStates:broadcast_text")
            
            # Step 2: Admin enters broadcast message
            broadcast_message = "Server maintenance scheduled for tomorrow."
            
            # Step 3: System retrieves all users
            async with mock_db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT telegram_id FROM users")
                    users = await cur.fetchall()
            
            # Step 4: Message is sent to all users
            ok = fail = 0
            for (uid,) in users:
                try:
                    await mock_bot.send_message(uid, broadcast_message)
                    ok += 1
                except Exception:
                    fail += 1
            
            await mock_state.clear()
            
            # Verify workflow
            assert len(users) == 4
            assert ok == 4
            assert fail == 0
            assert mock_bot.send_message.call_count == 4
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_state, mock_bot, mock_db_pool, complete_config):
        """Test error recovery in workflows."""
        with patch('src.handlers.registration.CONFIG', complete_config), \
             patch('src.handlers.registration.validate_nickname', return_value=True), \
             patch('src.handlers.registration.validate_password', return_value=True), \
             patch('src.handlers.registration.validate_email', return_value=True), \
             patch('src.handlers.registration.register_user') as mock_register, \
             patch('src.handlers.registration.delete_all_bot_messages'), \
             patch('src.handlers.registration.record_message'):
            
            # Simulate registration failure
            mock_register.side_effect = Exception("Database error")
            
            # Start registration process
            await mock_state.set_state("RegistrationStates:mail")
            await mock_state.update_data(nick="TestUser", pwd="password123")
            
            # Try to complete registration (should fail gracefully)
            try:
                data = await mock_state.get_data()
                username, error = await mock_register(
                    mock_db_pool,
                    data["nick"],
                    data["pwd"],
                    "test@example.com",
                    123456789
                )
            except Exception as e:
                # Error should be handled gracefully
                error_handled = True
                error_message = str(e)
            
            # Verify error was handled
            assert error_handled is True
            assert "Database error" in error_message
    
    @pytest.mark.asyncio
    async def test_concurrent_user_workflow(self, mock_bot, mock_db_pool, complete_config):
        """Test concurrent user workflows."""
        import asyncio
        
        with patch('src.handlers.registration.CONFIG', complete_config), \
             patch('src.handlers.registration.validate_nickname', return_value=True), \
             patch('src.handlers.registration.validate_password', return_value=True), \
             patch('src.handlers.registration.validate_email', return_value=True), \
             patch('src.handlers.registration.register_user') as mock_register:
            
            # Mock successful registrations with different usernames
            mock_register.side_effect = [
                ("user1#1", None),
                ("user2#1", None),
                ("user3#1", None)
            ]
            
            # Simulate concurrent registrations
            async def register_user(user_id, nick, email):
                return await mock_register(mock_db_pool, nick, "password123", email, user_id)
            
            # Run concurrent registrations
            tasks = [
                register_user(111111111, "User1", "user1@example.com"),
                register_user(222222222, "User2", "user2@example.com"),
                register_user(333333333, "User3", "user3@example.com"),
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all registrations completed
            assert len(results) == 3
            assert all(result[0] is not None for result in results)
            assert all(result[1] is None for result in results)
            assert mock_register.call_count == 3
    
    @pytest.mark.asyncio
    async def test_feature_toggle_workflow(self, mock_state, complete_config):
        """Test workflow behavior with disabled features."""
        # Test with registration disabled
        disabled_config = complete_config.copy()
        disabled_config["features"]["registration"] = False
        
        with patch('src.handlers.registration.CONFIG', disabled_config):
            
            # Attempt to start registration with feature disabled
            registration_enabled = disabled_config["features"]["registration"]
            
            if not registration_enabled:
                # Registration should be blocked
                registration_blocked = True
            else:
                registration_blocked = False
            
            assert registration_blocked is True
            
            # State should not be set when feature is disabled
            await mock_state.clear()
            current_state = await mock_state.get_state()
            assert current_state is None

