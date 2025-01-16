# Rowan AI Assistant

## Overview
Rowan is a modular AI assistant system with multiple interface capabilities and skill modules.

## Core Features
- Modular architecture
- Discord integration 
- Calendar management
- Personal memory system
- Context-aware responses
- GUI interface with modern design

## Installation

### Prerequisites
- Python 3.8+
- MongoDB
- Ollama API running locally

### Setup
```bash
# Clone repository 
git clone https://github.com/[username]/rowan.git

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example config/.env
# Update .env with your settings
```

## Module System
- Discord Module - Chat interface and server management
- Calendar Module - Google Calendar integration and event management
- Memory System - Persistent storage and context management
- GUI Module - Modern desktop interface with customtkinter

## Development

### Project Structure
```
rowan/
├── core/                 # Core system components
├── modules/             # Interface and skill modules  
├── data/               # Data storage and logs
├── config/             # Configuration files
└── utils/              # Utility functions
```

### Planned Features
- Email integration
- Music control
- Weather module
- Task management 
- Web search
- File management
- System monitoring
- Text summarization
- Translation services
- Voice interaction
- Image generation
- Note taking
- Calculator
- News aggregation
- Smart home control

## Contributing
See CONTRIBUTING.md for guidelines.

## License
MIT License - See LICENSE for details.