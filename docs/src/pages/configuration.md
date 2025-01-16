# Configuration Settings for Rowan AI Assistant

## Overview
This document outlines the configuration settings for the Rowan AI assistant. Proper configuration is essential for the assistant to function correctly and to customize its behavior according to your needs.

## Environment Variables
Rowan AI uses several environment variables to manage its configuration. These variables should be defined in the `.env` file located in the `config` directory. Below are the key environment variables you need to set:

- `DISCORD_TOKEN`: The token for the Discord bot integration.
- `API_PORT`: The port on which the API will run (default is `7692`).
- `MONGODB_URI`: The connection string for the MongoDB database.
- `OLLAMA_API_KEY`: The API key for the Ollama service.

## Configuration File
In addition to environment variables, Rowan AI uses a configuration file to manage settings. The configuration file is typically named `config.json` and should be placed in the `config` directory. Below is an example structure of the configuration file:

```json
{
    "api_port": 7692,
    "rowan": {
        "api_key": "your_api_key_here",
        "other_setting": "value"
    },
    "modules": {
        "calendar": true,
        "discord": true,
        "api": true
    }
}
```

### Configuration Options
- **api_port**: Specifies the port for the API service.
- **rowan**: Contains settings specific to the Rowan AI assistant.
- **modules**: A list of enabled modules. Set to `true` to enable a module or `false` to disable it.

## Customizing Behavior
To customize the behavior of the Rowan AI assistant, you can modify the values in the configuration file and environment variables. Ensure that any changes made are valid and follow the expected formats.

## Conclusion
Proper configuration is crucial for the Rowan AI assistant to operate effectively. Make sure to review and update the configuration settings as needed to suit your environment and requirements.