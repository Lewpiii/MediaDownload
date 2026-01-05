# Contributing to Media Download Bot

Thank you for your interest in contributing to Media Download Bot! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Git
- Discord Bot Token
- Basic knowledge of Discord.py

### Setting up Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/media-download-bot.git
   cd media-download-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp env.example .env
   # Add your tokens to .env
   ```

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small

### Commit Messages
Use clear, descriptive commit messages:
```
feat: add new download option
fix: resolve vote verification bug
docs: update README with new features
refactor: improve file organization logic
```

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests if applicable
   - Update documentation if needed

3. **Test your changes**
   ```bash
   python check_env.py
   python test_topgg.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide a clear description
   - Reference any related issues
   - Include screenshots if applicable

## 🐛 Reporting Issues

When reporting issues, please include:

- **Description**: Clear description of the issue
- **Steps to reproduce**: How to reproduce the issue
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: Python version, OS, etc.
- **Logs**: Any relevant error messages

## 💡 Feature Requests

When suggesting features:

- **Description**: Clear description of the feature
- **Use case**: Why this feature would be useful
- **Implementation ideas**: How it could be implemented
- **Alternatives**: Other ways to achieve the same goal

## 🧪 Testing

### Running Tests
```bash
# Check environment configuration
python check_env.py

# Test Top.gg API connection
python test_topgg.py

# Test bot functionality
python bot.py
```

### Test Coverage
- Test new features thoroughly
- Test edge cases
- Test error conditions
- Verify backward compatibility

## 📚 Documentation

### Code Documentation
- Add docstrings to all functions and classes
- Include type hints where appropriate
- Explain complex logic with comments

### User Documentation
- Update README.md for new features
- Add examples for new commands
- Update setup instructions if needed

## 🔒 Security

### Sensitive Information
- Never commit tokens or API keys
- Use environment variables for configuration
- Follow security best practices

### Code Review
- All code changes require review
- Security-sensitive changes need extra scrutiny
- Follow the principle of least privilege

## 🎯 Areas for Contribution

### High Priority
- Bug fixes
- Performance improvements
- Security enhancements
- Documentation improvements

### Medium Priority
- New features
- UI/UX improvements
- Code refactoring
- Test coverage

### Low Priority
- Code style improvements
- Minor optimizations
- Additional examples

## 📞 Getting Help

- **Discord**: Join our support server
- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For general questions and ideas

## 🙏 Recognition

Contributors will be:
- Listed in the README
- Mentioned in release notes
- Given credit in commit messages

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Media Download Bot! 🎉
