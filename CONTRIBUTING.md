# Contributing to AI Agents Sandbox

Thank you for your interest in contributing to AI Agents Sandbox! We welcome contributions from the community.

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-agents-sandbox.git
   cd ai-agents-sandbox
   ```

2. **Install in development mode:**
   ```bash
   # Using uv (recommended)
   uv pip install -e .[dev]
   
   # Or using pip
   pip install -e .[dev]
   ```

3. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## 📝 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests and Linting

```bash
# Run tests
pytest

# Run linting
ruff check .
black --check .
mypy src/ai_sbx

# Format code
black .
ruff check --fix .
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add amazing new feature"
```

Follow conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ai_sbx --cov-report=term-missing

# Run specific test file
pytest tests/test_cli.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test names
- Include both positive and negative test cases

Example test:
```python
def test_feature_works_correctly():
    """Test that feature produces expected output."""
    result = my_function("input")
    assert result == "expected_output"
```

## 🐳 Docker Images

### Building Images

```bash
# Build base image
docker build -t ai-agents-sandbox/base:dev -f images/base/Dockerfile .

# Build variant
docker build -t ai-agents-sandbox/python:dev -f images/python/Dockerfile .
```

### Testing Images

```bash
# Run container
docker run -it --rm ai-agents-sandbox/base:dev /bin/bash

# Test specific functionality
docker run --rm ai-agents-sandbox/python:dev python --version
```

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use type hints for function parameters and returns
- Include examples in docstrings when helpful

Example:
```python
def process_config(config: dict) -> ProjectConfig:
    """Process raw configuration into ProjectConfig object.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Processed ProjectConfig instance
        
    Example:
        >>> config = {"name": "my-project", "path": "/path/to/project"}
        >>> result = process_config(config)
        >>> result.name
        'my-project'
    """
```

### User Documentation

- Update README.md for user-facing changes
- Add detailed guides in `docs/` for complex features
- Include examples and common use cases

## 🎯 Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Keep functions small and focused
- Avoid deep nesting

### Security

- Never commit secrets or credentials
- Validate all user inputs
- Follow principle of least privilege
- Document security implications

### Performance

- Consider performance implications
- Add benchmarks for performance-critical code
- Use caching where appropriate
- Optimize Docker image sizes

## 🐛 Reporting Issues

### Before Creating an Issue

1. Check existing issues to avoid duplicates
2. Try to reproduce with latest version
3. Gather relevant information:
   - OS and version
   - Python version
   - Docker version
   - Error messages and logs

### Creating an Issue

Use issue templates when available and include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Relevant code snippets or configuration
- Error messages or logs

## 💡 Suggesting Features

### Feature Requests

1. Check if feature already requested
2. Clearly describe the use case
3. Explain why existing features don't solve it
4. Provide examples if possible

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] PR description explains changes
- [ ] No sensitive information included

## 🤝 Code of Conduct

### Be Respectful

- Use welcoming and inclusive language
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Be Professional

- Stay on topic
- Provide helpful feedback
- Be patient with new contributors
- Help others learn and grow

## 📬 Getting Help

- **Questions:** Open a [Discussion](https://github.com/alexsteeel/ai-agents-sandbox/discussions)
- **Bugs:** Create an [Issue](https://github.com/alexsteeel/ai-agents-sandbox/issues)
- **Security:** Email security concerns privately

## 🎉 Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes for significant contributions
- Special thanks in documentation

Thank you for contributing to AI Agents Sandbox!