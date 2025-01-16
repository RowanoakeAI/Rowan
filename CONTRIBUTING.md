# Contributing to Rowan

## Overview
Rowan is a modular AI assistant system. This guide outlines contribution guidelines and best practices.

## Getting Started
1. Fork the repository
2. Create a feature branch
3. Set up development environment
4. Make your changes
5. Submit a pull request

## Development Environment
- Python 3.8 or higher required
- Install dependencies: `pip install -r requirements.txt`
- Set up environment variables in `config/.env`

## Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document classes and functions
- Keep functions focused and single-purpose

## Modules
### Adding New Modules
1. Create module in `modules/` directory
2. Implement `ModuleInterface`
3. Add initialization in `core/module_manager.py`
4. Document functionality
5. Add error handling

### Module Guidelines
- Independent operation
- Clear error handling
- Memory system integration
- Context awareness
- Performance optimization

## Testing
- Write unit tests for new features
- Test edge cases
- Verify memory system integration
- Check module interactions
- Validate error handling

## Documentation
- Update relevant README sections
- Document new features
- Include usage examples
- Note dependencies
- Describe error scenarios

## Pull Requests
- Clear description of changes
- Reference related issues
- Include test results
- Follow commit message format
- Keep changes focused

## Need Help?
- Check existing issues
- Review documentation
- Contact maintainers

## License
This project is licensed under MIT License