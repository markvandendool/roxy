# Contributing to ROXY

## Development Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

- **Formatting**: Black (line length 127)
- **Linting**: Flake8
- **Type Checking**: MyPy
- **Testing**: Pytest

## Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=services --cov-report=html
```

## Commit Guidelines

- Use descriptive commit messages
- Follow conventional commits format
- Run tests before committing
- Pre-commit hooks will run automatically

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add tests
4. Ensure all tests pass
5. Update documentation
6. Submit PR

## Code Review

- All PRs require review
- Tests must pass
- Code must be formatted
- Documentation must be updated
