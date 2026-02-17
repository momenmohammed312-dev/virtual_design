.PHONY: help install test clean run bundle docker

help:
	@echo "Silk Screen Python Engine - Make Commands"
	@echo ""
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make test-install - Test installation"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make run        - Run demo"
	@echo "  make bundle     - Create distribution bundle"
	@echo "  make docker     - Build Docker image"
	@echo ""

install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test:
	pytest tests/ -v
	@echo "✅ Tests complete"

test-install:
	python scripts/test_installation.py
	@echo "✅ Installation test complete"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf output/ bundle/
	@echo "✅ Cleaned"

run:
	python scripts/demo.py tests/test_samples/test.jpg
	@echo "✅ Demo complete"

bundle:
	python scripts/build_bundle.py
	@echo "✅ Bundle created"

docker:
	docker build -t silk_screen_processor .
	@echo "✅ Docker image built"

docker-run:
	docker-compose up
	@echo "✅ Docker container ran"
