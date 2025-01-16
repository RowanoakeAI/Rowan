# File: /rowan-docs/src/pages/modules.md

# Rowan AI Assistant Modules

## Overview
The Rowan AI assistant is designed with a modular architecture, allowing for easy integration and management of various functionalities. Each module serves a specific purpose and can be enabled or disabled based on user requirements.

## Available Modules

### 1. Conversation Module
- **Functionality**: Enables natural language interaction with the Rowan AI assistant.
- **Usage**: This module processes user input and generates appropriate responses.
- **Configuration**: No specific configuration is required. Ensure it is enabled in the settings.

### 2. Calendar Module
- **Functionality**: Manages calendar events and scheduling.
- **Usage**: Users can add, check, and remove events from their calendar.
- **Configuration**: Requires access to a calendar API. Configure the API keys in the environment settings.

### 3. Discord Module
- **Functionality**: Integrates with Discord to allow interaction through Discord servers.
- **Usage**: Users can send and receive messages via Discord channels.
- **Configuration**: Requires a Discord bot token. Set the token in the configuration file.

### 4. API Module
- **Functionality**: Provides a REST API interface for external applications to interact with Rowan.
- **Usage**: Allows for sending messages, checking status, and managing modules programmatically.
- **Configuration**: The API runs on port 7692. Ensure the port is open and accessible.

## Module Management
Modules can be managed through the Rowan settings. Users can enable or disable modules as needed, ensuring that only the required functionalities are active.

## Conclusion
The modular design of Rowan allows for flexibility and customization, making it a powerful tool for various applications. For more details on each module's specific commands and functionalities, refer to the respective module documentation.