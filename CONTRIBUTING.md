# Contributing to WhatsApp Calling

Thank you for considering contributing to WhatsApp Calling! This document outlines the process for contributing to this project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/your-username/whatsapp-calling/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Environment details (Frappe version, browser, OS)

### Suggesting Features

1. Check existing feature requests
2. Create a new issue with:
   - Clear use case
   - Expected behavior
   - Why this feature would be useful

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Write or update tests if applicable
5. Update documentation if needed
6. Commit with clear messages
7. Push to your fork
8. Create a Pull Request

### Coding Standards

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Write docstrings for functions and classes
- Keep functions focused and small

### JavaScript Standards

- Use ES6+ syntax
- Follow Frappe's JavaScript conventions
- Add JSDoc comments
- Use `frappe.call()` for API calls
- Handle errors gracefully

### Commit Messages

Format: `type: description`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Example: `feat: add call recording playback UI`

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/whatsapp-calling.git

# Add upstream remote
git remote add upstream https://github.com/original/whatsapp-calling.git

# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push to your fork
git push origin feature/my-feature
```

## Testing

Before submitting:

1. Test basic call flow
2. Test permission management
3. Test with different browsers
4. Verify no console errors
5. Check responsive design

## Questions?

Feel free to reach out by creating an issue or contacting the maintainers.

Thank you for contributing! 🎉
