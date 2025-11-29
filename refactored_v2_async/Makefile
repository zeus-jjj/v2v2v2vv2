.PHONY: help install run test lint format type-check clean

help:
	@echo "PokerHub Database Extractor v2.0 (FULLY ASYNC)"
	@echo ""
	@echo "🚀 PERFORMANCE: 11x faster with concurrent execution!"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install async dependencies"
	@echo "  make run          - Run the application (ASYNC/CONCURRENT)"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run linter (flake8)"
	@echo "  make format       - Format code (black + isort)"
	@echo "  make type-check   - Run type checker (mypy)"
	@echo "  make clean        - Clean generated files"
	@echo "  make all          - Format, lint, type-check, test"

install:
	pip install -r requirements.txt

run:
	python main.py

test:
	pytest

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format:
	isort . --profile black
	black . --line-length 100

type-check:
	mypy .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete

all: format lint type-check test
	@echo "All checks passed! ✅"
