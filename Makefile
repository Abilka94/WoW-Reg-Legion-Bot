# Makefile for WoW Registration Bot Testing and Quality Assurance

.PHONY: help install test test-unit test-integration test-security test-performance
.PHONY: lint format check-security coverage clean
.PHONY: test-all quality-check ci-check

# Default target
help:
	@echo "Available targets:"
	@echo "  install          - Install all dependencies"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-security   - Run security tests only"
	@echo "  test-performance - Run performance tests only"
	@echo "  lint            - Run all linters"
	@echo "  format          - Format code with black and isort"
	@echo "  check-security  - Run security analysis"
	@echo "  coverage        - Generate coverage report"
	@echo "  quality-check   - Run complete quality checks"
	@echo "  ci-check        - Run CI/CD pipeline locally"
	@echo "  clean           - Clean generated files"

# Installation
install:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# Testing targets
test:
	python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

test-unit:
	python -m pytest tests/unit/ -v --tb=short -p no:postgresql

test-integration:
	python -m pytest tests/integration/ -v --tb=short -p no:postgresql

test-security:
	python -m pytest tests/security/ -v --tb=short -p no:postgresql

test-performance:
	python -m pytest tests/performance/ -v --tb=short -p no:postgresql -m performance

# Code quality
lint:
	@echo "Running flake8..."
	flake8 src/ tests/
	@echo "Running pylint..."
	pylint src/
	@echo "Running mypy..."
	mypy src/

format:
	@echo "Formatting with black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/

check-security:
	@echo "Running bandit security analysis..."
	bandit -r src/ -f json -o reports/bandit-report.json || true
	bandit -r src/
	@echo "Running safety check..."
	safety check --json --output reports/safety-report.json || true
	safety check

# Coverage
coverage:
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-report=term
	@echo "Coverage report generated in htmlcov/"

# Quality checks
quality-check: format lint check-security test coverage
	@echo "Quality check completed!"

# CI/CD simulation
ci-check:
	@echo "Running CI/CD pipeline locally..."
	@echo "1. Code formatting check..."
	black --check src/ tests/
	isort --check-only src/ tests/
	@echo "2. Linting..."
	flake8 src/ tests/
	pylint src/ --fail-under=8.0
	@echo "3. Security analysis..."
	bandit -r src/ --severity-level medium
	safety check
	@echo "4. Testing..."
	python -m pytest tests/ --cov=src --cov-fail-under=85 -p no:postgresql
	@echo "CI/CD pipeline completed successfully!"

# Test specific validators
test-validators:
	python -m pytest tests/unit/test_validators.py -v -p no:postgresql
	python -m pytest tests/unit/test_validators_enhanced.py -v -p no:postgresql

# Test database operations
test-database:
	python -m pytest tests/unit/test_database_operations.py -v -p no:postgresql

# Generate reports
reports:
	@mkdir -p reports
	python -m pytest tests/ --html=reports/test-report.html --self-contained-html --cov=src --cov-report=html:reports/coverage
	flake8 src/ --format=html --htmldir=reports/flake8 || true
	pylint src/ --output-format=json > reports/pylint-report.json || true
	bandit -r src/ -f json -o reports/bandit-report.json || true

# Clean up generated files
clean:
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf coverage.xml
	rm -rf reports/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Development helpers
dev-setup: install
	@echo "Setting up development environment..."
	pre-commit install || echo "pre-commit not available"

quick-test:
	python -m pytest tests/unit/ -x -v -p no:postgresql

watch-test:
	python -m pytest tests/unit/ --tb=short -p no:postgresql -f

# Performance benchmarking
benchmark:
	python -m pytest tests/performance/ --benchmark-only --benchmark-sort=mean -p no:postgresql

# Memory profiling
profile-memory:
	python -m pytest tests/performance/test_performance.py::TestMemoryUsage -v -s -p no:postgresql

# Load testing
load-test:
	python -m pytest tests/performance/test_performance.py::TestLoadTesting -v -s -p no:postgresql

# Static analysis with semgrep (if available)
semgrep-scan:
	semgrep --config=auto src/ --json --output=reports/semgrep-report.json || true
	semgrep --config=auto src/

# Generate security report
security-report: check-security semgrep-scan
	@echo "Security analysis completed. Check reports/ directory for detailed reports."

# Check for dependency vulnerabilities
audit-deps:
	safety check --json --output reports/safety-audit.json || true
	pip-audit --format=json --output=reports/pip-audit.json || true

# Full quality assurance pipeline
qa: clean dev-setup format lint check-security test coverage reports
	@echo "Complete QA pipeline finished!"

# Docker support (if Dockerfile exists)
docker-test:
	docker build -t wow-bot-test .
	docker run --rm wow-bot-test make test

# Documentation generation (if docs exist)
docs:
	@if [ -d "docs" ]; then \
		echo "Generating documentation..."; \
		cd docs && make html; \
	else \
		echo "No docs directory found"; \
	fi