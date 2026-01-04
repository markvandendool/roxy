# Contributing to ROXY

Thank you for your interest in contributing to ROXY!

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Systemd (for service management)

### Setup Steps

1. **Clone Repository**:
   ```bash
   git clone https://github.com/yourusername/roxy.git
   cd roxy
   ```

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   # Create config
   cp config.json.example config.json
   
   # Generate auth token
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > secret.token
   chmod 600 secret.token
   ```

4. **Start Infrastructure**:
   ```bash
   cd compose
   docker-compose -f docker-compose.foundation.yml up -d
   ```

5. **Run Tests**:
   ```bash
   pytest tests/ --cov=. --cov-report=html
   ```

## Code Style

### Python

- **Formatter**: Black
- **Linter**: Pylint
- **Type Checking**: mypy

```bash
# Format code
black .

# Lint code
pylint roxy_core.py roxy_commands.py

# Type check
mypy roxy_core.py roxy_commands.py
```

### Style Guidelines

- Use type hints for all functions
- Follow PEP 8
- Use descriptive variable names
- Add docstrings to all functions/classes
- Keep functions focused and small

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_security.py

# With coverage
pytest --cov=. --cov-report=html

# Marked tests
pytest -m integration
```

### Writing Tests

- Use pytest fixtures from `tests/conftest.py`
- Test both success and failure cases
- Mock external dependencies
- Aim for 80%+ coverage

### Test Structure

```python
def test_feature_name():
    """Test description"""
    # Arrange
    setup_data = ...
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected
```

## Pull Request Process

1. **Create Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Write code
   - Add tests
   - Update documentation

3. **Run Checks**:
   ```bash
   # Format
   black .
   
   # Lint
   pylint roxy_core.py
   
   # Type check
   mypy roxy_core.py
   
   # Tests
   pytest
   ```

4. **Commit Changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and Create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `perf:` Performance improvement

## Documentation

### Code Documentation

- Add docstrings to all functions/classes
- Use Google-style docstrings
- Include examples for complex functions

### API Documentation

- Update `openapi.yaml` for API changes
- Update `docs/API.md` for endpoint changes

### Architecture Documentation

- Update `docs/ARCHITECTURE.md` for structural changes
- Update runbooks for operational changes

## Code Review

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] No security issues
- [ ] Performance considered

## Questions?

- Check existing documentation
- Open an issue for questions
- Contact maintainers

Thank you for contributing!
