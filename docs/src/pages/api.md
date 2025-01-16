# File: /rowan-docs/src/pages/api.md

# Rowan AI Assistant API Documentation

## Overview
The Rowan AI assistant provides a RESTful API that allows developers to interact with its functionalities programmatically. This document outlines the available API endpoints, their request and response formats, and examples of how to use them.

## Base URL
The base URL for the API is:
```
http://localhost:8000/api
```

## Endpoints

### 1. Get Status
- **Endpoint:** `/status`
- **Method:** `GET`
- **Description:** Checks the status of the API server.

#### Request
No parameters are required.

#### Response
- **Status Code:** `200 OK`
- **Response Body:**
```json
{
    "status": "online"
}
```

### 2. Send Message
- **Endpoint:** `/send`
- **Method:** `POST`
- **Description:** Sends a message to the Rowan AI assistant for processing.

#### Request
- **Headers:**
  - `Content-Type: application/json`
  - `X-API-Key: {your_api_key}`

- **Body:**
```json
{
    "message": "Your message here"
}
```

#### Response
- **Status Code:** `200 OK`
- **Response Body:**
```json
{
    "response": "Rowan's response to your message"
}
```

### 3. Get Modules
- **Endpoint:** `/modules`
- **Method:** `GET`
- **Description:** Retrieves a list of available modules in the Rowan AI assistant.

#### Request
No parameters are required.

#### Response
- **Status Code:** `200 OK`
- **Response Body:**
```json
{
    "modules": [
        "conversation",
        "calendar",
        "discord",
        "api"
    ]
}
```

## Error Handling
In case of an error, the API will return an appropriate status code and a response body with an error message.

### Example Error Response
- **Status Code:** `400 Bad Request`
- **Response Body:**
```json
{
    "error": "Invalid input"
}
```

## Conclusion
This API allows for seamless integration with the Rowan AI assistant, enabling developers to leverage its capabilities in their applications. For further details on specific modules and their functionalities, refer to the [Modules Documentation](modules.md).