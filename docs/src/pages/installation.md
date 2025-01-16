# Installation Instructions for Rowan AI Assistant

## Prerequisites
Before you begin, ensure you have the following installed on your system:
- **Python 3.8 or higher**: Rowan requires Python to run. You can download it from [python.org](https://www.python.org/downloads/).
- **Node.js**: Required for running the documentation site. Download it from [nodejs.org](https://nodejs.org/).
- **MongoDB**: Rowan uses MongoDB for data storage. You can find installation instructions at [mongodb.com](https://www.mongodb.com/try/download/community).

## Cloning the Repository
To get started with Rowan, clone the repository to your local machine using the following command:

```bash
git clone https://github.com/RowanoakeAI/Rowan.git
```

## Installing Dependencies
Navigate to the project directory and install the required Python and Node.js dependencies:

1. **Python Dependencies**:
   Change to the Rowan directory and install the Python dependencies:

   ```bash
   cd Rowan
   pip install -r requirements.txt
   ```

2. **Node.js Dependencies**:
   In the same directory, install the Node.js dependencies for the documentation site:

   ```bash
   cd rowan-docs
   npm install
   ```

## Configuring the Environment
Rowan requires some configuration to run properly. Follow these steps to set up your environment:

1. **Copy the Example Environment File**:
   Create a new environment configuration file by copying the example provided:

   ```bash
   cp config/.env.example config/.env
   ```

2. **Edit the Configuration File**:
   Open the `config/.env` file in a text editor and update the necessary variables, such as your MongoDB connection string and any API keys required for specific modules.

## Running the Application
Once everything is set up, you can run the Rowan AI assistant and the documentation site:

1. **Start the Rowan AI Assistant**:
   In the Rowan directory, run the following command:

   ```bash
   python main.py
   ```

2. **Start the Documentation Site**:
   In the `rowan-docs` directory, start the documentation site with:

   ```bash
   npm start
   ```

You should now have the Rowan AI assistant running and the documentation site accessible in your web browser. Enjoy using Rowan!