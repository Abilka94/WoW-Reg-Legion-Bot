"""
Performance testing suite for the WoW Registration Bot.
"""
import asyncio
import time
import pytest
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock
from memory_profiler import profile

from src.utils.validators import validate_email, validate_nickname, validate_password
from src.utils.validators_enhanced import (
    validate_email_enhanced, validate_nickname_enhanced, validate_password_enhanced
)


class TestValidatorPerformance:
    """Performance tests for validator functions."""
    
    @pytest.mark.performance
    def test_email_validator_performance(self):
        """Test email validator performance under load."""
        test_emails = [
            "user@example.com",
            "test.email@domain.org", 
            "valid_email@test-domain.net",
            "user123@gmail.com",
            "firstname.lastname@company.co.uk",
        ] * 1000  # 5000 total tests
        
        start_time = time.perf_counter()
        for email in test_emails:
            validate_email(email)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        operations_per_second = len(test_emails) / total_time
        
        # Should process at least 10,000 emails per second
        assert operations_per_second > 10000, \
            f"Email validation too slow: {operations_per_second:.0f} ops/sec (minimum: 10,000)"
        
        print(f"Email validator: {operations_per_second:.0f} ops/sec ({total_time:.3f}s total)")
    
    @pytest.mark.performance
    def test_nickname_validator_performance(self):
        """Test nickname validator performance under load."""
        test_nicknames = [
            "TestUser", "Player123", "GamerOne", "User2024", "TestAccount"
        ] * 1000  # 5000 total tests
        
        start_time = time.perf_counter()
        for nickname in test_nicknames:
            validate_nickname(nickname)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        operations_per_second = len(test_nicknames) / total_time
        
        # Should process at least 20,000 nicknames per second
        assert operations_per_second > 20000, \
            f"Nickname validation too slow: {operations_per_second:.0f} ops/sec (minimum: 20,000)"
        
        print(f"Nickname validator: {operations_per_second:.0f} ops/sec ({total_time:.3f}s total)")
    
    @pytest.mark.performance
    def test_password_validator_performance(self):
        """Test password validator performance under load."""
        test_passwords = [
            "password123", "StrongPass1", "MySecretPwd", "GamePass2024", "ValidPassword"
        ] * 1000  # 5000 total tests
        
        start_time = time.perf_counter()
        for password in test_passwords:
            validate_password(password)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        operations_per_second = len(test_passwords) / total_time
        
        # Should process at least 15,000 passwords per second
        assert operations_per_second > 15000, \
            f"Password validation too slow: {operations_per_second:.0f} ops/sec (minimum: 15,000)"
        
        print(f"Password validator: {operations_per_second:.0f} ops/sec ({total_time:.3f}s total)")


class TestEnhancedValidatorPerformance:
    """Performance tests for enhanced validator functions."""
    
    @pytest.mark.performance
    def test_enhanced_validators_overhead(self):
        """Test performance overhead of enhanced validators vs original."""
        test_data = [
            ("user@example.com", "TestUser123", "password123"),
            ("test@domain.org", "GamerOne", "StrongPass1"),
            ("valid@email.net", "Player456", "MySecretPwd"),
        ] * 1000  # 3000 total tests per validator type
        
        # Test original validators
        start_time = time.perf_counter()
        for email, nickname, password in test_data:
            validate_email(email)
            validate_nickname(nickname)
            validate_password(password)
        original_time = time.perf_counter() - start_time
        
        # Test enhanced validators
        start_time = time.perf_counter()
        for email, nickname, password in test_data:
            validate_email_enhanced(email)
            validate_nickname_enhanced(nickname)
            validate_password_enhanced(password)
        enhanced_time = time.perf_counter() - start_time
        
        # Enhanced validators should not be more than 5x slower
        overhead_ratio = enhanced_time / original_time
        assert overhead_ratio < 5.0, \
            f"Enhanced validators too slow: {overhead_ratio:.2f}x overhead (max: 5.0x)"
        
        print(f"Original validators: {original_time:.3f}s")
        print(f"Enhanced validators: {enhanced_time:.3f}s")
        print(f"Overhead ratio: {overhead_ratio:.2f}x")


class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self):
        """Test database connection pool performance under load."""
        from src.database.user_operations import email_exists
        
        # Mock database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Test concurrent operations
        async def check_email(email):
            return await email_exists(mock_pool, email)
        
        test_emails = [f"user{i}@example.com" for i in range(100)]
        
        start_time = time.perf_counter()
        tasks = [check_email(email) for email in test_emails]
        await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        operations_per_second = len(test_emails) / total_time
        
        # Should handle at least 1000 concurrent database operations per second
        assert operations_per_second > 1000, \
            f"Database operations too slow: {operations_per_second:.0f} ops/sec (minimum: 1,000)"
        
        print(f"Database operations: {operations_per_second:.0f} ops/sec ({total_time:.3f}s total)")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_registration_performance(self):
        """Test user registration performance."""
        from src.database.user_operations import register_user
        
        # Mock database components
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [(0,), (123,)]  # User count, then new ID
        mock_cursor.rowcount = 1
        
        # Mock configuration
        mock_config = {"settings": {"max_accounts_per_user": 5}}
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("src.database.user_operations.CONFIG", mock_config)
            
            # Test registration performance
            registrations = []
            start_time = time.perf_counter()
            
            for i in range(50):  # 50 registrations
                result = await register_user(
                    mock_pool, f"user{i}", f"password{i}", f"user{i}@example.com", 123456789 + i
                )
                registrations.append(result)
            
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            registrations_per_second = len(registrations) / total_time
            
            # Should handle at least 100 registrations per second
            assert registrations_per_second > 100, \
                f"Registration too slow: {registrations_per_second:.0f} reg/sec (minimum: 100)"
            
            print(f"Registration performance: {registrations_per_second:.0f} reg/sec ({total_time:.3f}s total)")


class TestMemoryUsage:
    """Memory usage tests."""
    
    @pytest.mark.performance
    def test_validator_memory_usage(self):
        """Test memory usage of validators under load."""
        import tracemalloc
        
        # Start memory tracing
        tracemalloc.start()
        
        # Baseline memory
        snapshot1 = tracemalloc.take_snapshot()
        
        # Run validators with large dataset
        test_data = []
        for i in range(10000):
            email = f"user{i}@example{i}.com"
            nickname = f"User{i}"
            password = f"password{i}123"
            
            validate_email(email)
            validate_nickname(nickname)
            validate_password(password)
            
            # Keep some data in memory to test for leaks
            if i % 1000 == 0:
                test_data.append((email, nickname, password))
        
        # Memory after operations
        snapshot2 = tracemalloc.take_snapshot()
        
        # Calculate memory difference
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_memory_mb = sum(stat.size_diff for stat in top_stats) / 1024 / 1024
        
        # Memory usage should be reasonable (less than 50MB for 10k operations)
        assert total_memory_mb < 50, \
            f"Excessive memory usage: {total_memory_mb:.2f}MB (max: 50MB)"
        
        print(f"Memory usage for 10k validations: {total_memory_mb:.2f}MB")
        
        tracemalloc.stop()
    
    @pytest.mark.performance
    def test_memory_leak_detection(self):
        """Test for memory leaks in validators."""
        gc.collect()  # Clean up before test
        initial_objects = len(gc.get_objects())
        
        # Run many validation cycles
        for cycle in range(100):
            for i in range(100):
                validate_email(f"test{i}@example.com")
                validate_nickname(f"User{i}")
                validate_password(f"password{i}")
            
            # Force garbage collection every 10 cycles
            if cycle % 10 == 0:
                gc.collect()
        
        gc.collect()  # Final cleanup
        final_objects = len(gc.get_objects())
        
        # Object count should not increase significantly
        object_increase = final_objects - initial_objects
        increase_percentage = (object_increase / initial_objects) * 100
        
        assert increase_percentage < 10, \
            f"Potential memory leak: {increase_percentage:.1f}% object increase"
        
        print(f"Object count change: {object_increase} ({increase_percentage:.1f}%)")


class TestConcurrencyPerformance:
    """Concurrency performance tests."""
    
    @pytest.mark.performance
    def test_concurrent_validation_performance(self):
        """Test validator performance under concurrent load."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def validation_worker(worker_id):
            """Worker function for concurrent validation."""
            results = []
            for i in range(1000):
                email = f"worker{worker_id}_user{i}@example.com"
                nickname = f"Worker{worker_id}User{i}"
                password = f"worker{worker_id}pass{i}"
                
                results.append((
                    validate_email(email),
                    validate_nickname(nickname),
                    validate_password(password)
                ))
            return len(results)
        
        # Test with multiple concurrent workers
        num_workers = 10
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(validation_worker, i) for i in range(num_workers)]
            
            total_validations = 0
            for future in as_completed(futures):
                total_validations += future.result()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        validations_per_second = total_validations / total_time
        
        # Should handle at least 50,000 concurrent validations per second
        assert validations_per_second > 50000, \
            f"Concurrent validation too slow: {validations_per_second:.0f} ops/sec (minimum: 50,000)"
        
        print(f"Concurrent validation: {validations_per_second:.0f} ops/sec with {num_workers} workers")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_async_database_concurrency(self):
        """Test async database operation concurrency."""
        from src.database.user_operations import email_exists, count_user_accounts
        
        # Mock database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (0,)
        
        async def mixed_operations(batch_id):
            """Mix of different database operations."""
            tasks = []
            for i in range(50):
                if i % 2 == 0:
                    tasks.append(email_exists(mock_pool, f"batch{batch_id}_user{i}@example.com"))
                else:
                    tasks.append(count_user_accounts(mock_pool, 123456789 + batch_id * 1000 + i))
            
            results = await asyncio.gather(*tasks)
            return len(results)
        
        # Run multiple concurrent batches
        num_batches = 20
        start_time = time.perf_counter()
        
        batch_tasks = [mixed_operations(i) for i in range(num_batches)]
        batch_results = await asyncio.gather(*batch_tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        total_operations = sum(batch_results)
        operations_per_second = total_operations / total_time
        
        # Should handle at least 5,000 async database operations per second
        assert operations_per_second > 5000, \
            f"Async DB operations too slow: {operations_per_second:.0f} ops/sec (minimum: 5,000)"
        
        print(f"Async DB operations: {operations_per_second:.0f} ops/sec with {num_batches} batches")


class TestLoadTesting:
    """Load testing scenarios."""
    
    @pytest.mark.performance
    def test_registration_load_simulation(self):
        """Simulate high registration load."""
        from src.utils.validators import validate_email, validate_nickname, validate_password
        
        # Simulate 1000 simultaneous registrations
        registration_data = []
        for i in range(1000):
            registration_data.append({
                'email': f"user{i}@example{i%10}.com",
                'nickname': f"User{i}",
                'password': f"SecurePass{i}123!"
            })
        
        # Track successful validations
        successful_validations = 0
        failed_validations = 0
        
        start_time = time.perf_counter()
        
        for data in registration_data:
            try:
                email_valid = validate_email(data['email'])
                nick_valid = validate_nickname(data['nickname'])
                pass_valid = validate_password(data['password'])
                
                if email_valid and nick_valid and pass_valid:
                    successful_validations += 1
                else:
                    failed_validations += 1
            except Exception:
                failed_validations += 1
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        success_rate = (successful_validations / len(registration_data)) * 100
        throughput = len(registration_data) / total_time
        
        # Should maintain high success rate and throughput
        assert success_rate > 95, f"Low success rate: {success_rate:.1f}% (minimum: 95%)"
        assert throughput > 5000, f"Low throughput: {throughput:.0f} reg/sec (minimum: 5,000)"
        
        print(f"Load test results: {success_rate:.1f}% success, {throughput:.0f} reg/sec")
    
    @pytest.mark.performance
    def test_stress_testing_limits(self):
        """Test system behavior under extreme load."""
        import psutil
        
        # Monitor system resources
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()
        
        # Extreme load test
        start_time = time.perf_counter()
        operations_completed = 0
        
        try:
            for batch in range(100):  # 100 batches
                for i in range(1000):  # 1000 operations per batch
                    validate_email(f"stress{batch}_{i}@example.com")
                    validate_nickname(f"Stress{batch}User{i}")
                    validate_password(f"StressPassword{batch}_{i}")
                    operations_completed += 3
                
                # Check resources every 10 batches
                if batch % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory
                    
                    # Break if memory usage becomes excessive
                    if memory_increase > 500:  # More than 500MB increase
                        print(f"Breaking due to high memory usage: {memory_increase:.1f}MB")
                        break
        
        except Exception as e:
            print(f"Stress test failed after {operations_completed} operations: {e}")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        operations_per_second = operations_completed / total_time
        
        print(f"Stress test: {operations_completed} operations in {total_time:.2f}s")
        print(f"Performance: {operations_per_second:.0f} ops/sec")
        print(f"Memory usage: {memory_increase:.1f}MB increase")
        
        # Should complete a reasonable number of operations without crashes
        assert operations_completed > 50000, \
            f"Stress test completed too few operations: {operations_completed}"