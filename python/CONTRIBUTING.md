# Contributing to Silk Screen Processor

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_color_separation.py

# Run with coverage
pytest --cov=core tests/
```

## Code Style

We use:
- Black for formatting
- Flake8 for linting
- Type hints where applicable

Format code before committing:
```bash
black core/ utils/ config/
flake8 core/ utils/ config/
```

## Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Format code
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open Pull Request

## Reporting Bugs

Use GitHub Issues and include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

## Feature Requests

Open an issue with:
- Clear description
- Use cases
- Expected behavior
