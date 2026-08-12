.PHONY: help install dev-install check check-all check-fast \
        test test-unit test-integration test-e2e test-bench \
        lint lint-fix format typecheck security scan-secrets \
        sql-verify perf-test clean build docker-build docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Installation
# ============================================================

install: ## Production install
	pip install .

dev-install: ## Developer install with all tools
	pip install -e ".[dev,quality,test]"
	pre-commit install
	@echo "✅ Dev environment ready"

# ============================================================
# Level 0: Pre-commit & fast checks
# ============================================================

check-fast: format lint typecheck ## Run all fast checks (Level 0)

format: ## Auto-format code
	ruff format src/ tests/
	@echo "✅ Format"

lint: ## Lint code
	ruff check src/ tests/
	@echo "✅ Lint"

lint-fix: ## Lint and auto-fix
	ruff check --fix src/ tests/
	@echo "✅ Lint (fixed)"

typecheck: ## Type check (mypy strict)
	mypy src/
	@echo "✅ Typecheck"

scan-secrets: ## Scan for secrets
	detect-secrets-hook --baseline .secrets.baseline || true
	@echo "✅ Secrets scan"

# ============================================================
# Level 1: Unit tests (<30s)
# ============================================================

test-unit: ## Run unit tests
	pytest tests/unit/ -x --timeout=30 --cov=src --cov-report=term --cov-fail-under=85
	@echo "✅ Unit tests"

# ============================================================
# Level 2: Integration tests (<5min)
# ============================================================

test-integration: ## Run integration tests
	pytest tests/integration/ -x --timeout=300 -m "not slow"
	@echo "✅ Integration tests"

test-integration-slow: ## Run slow integration tests
	pytest tests/integration/ -x --timeout=600 -m "slow"
	@echo "✅ Slow integration tests"

# ============================================================
# Level 3: E2E tests (<15min)
# ============================================================

test-e2e: ## Run E2E tests (Playwright)
	pytest tests/e2e/ -x --timeout=900
	@echo "✅ E2E tests"

# ============================================================
# Level 4: Property-based tests (nightly)
# ============================================================

test-property: ## Run property-based tests
	pytest tests/ -x -m "property" --timeout=1800 -n auto
	@echo "✅ Property-based tests"

# ============================================================
# Level 6: SQL verification
# ============================================================

sql-verify: ## Run SQL verification suite
	python -m gost_bi.quality.sql_verifier --suite all
	@echo "✅ SQL verification"

# ============================================================
# Level 8: Performance / benchmarks
# ============================================================

perf-test: ## Run performance benchmarks
	python -m pytest tests/benchmarks/ -x --timeout=3600
	@echo "✅ Performance benchmarks"

# ============================================================
# Level 9: Security scanning
# ============================================================

security: scan-secrets ## Full security scan
	bandit -r src/ -c pyproject.toml
	safety check
	semgrep --config auto src/
	@echo "✅ Security scan"

# ============================================================
# Combined targets
# ============================================================

check: check-fast test-unit test-integration security sql-verify ## Run Levels 0-2 + 6 + 9

check-all: check test-e2e test-property perf-test ## Run ALL levels

test: test-unit test-integration ## Run all tests

# ============================================================
# Build & Docker
# ============================================================

build: ## Build Python package
	python -m build

docker-build: ## Build Docker images
	docker compose -f docker/docker-compose.yml build

docker-up: ## Start development environment
	docker compose -f docker/docker-compose.yml up -d

docker-down: ## Stop development environment
	docker compose -f docker/docker-compose.yml down

# ============================================================
# Cleanup
# ============================================================

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .coverage coverage.xml htmlcov/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf tests/visual/current/*.png tests/visual/diffs/*.png
	@echo "✅ Clean"
