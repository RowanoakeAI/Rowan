from setuptools import setup, find_packages

setup(
    name="rowan",
    version="0.1.0",
    description="Rowan Assistant - An AI-powered personal assistant",
    author="Rowdy Project",
    packages=find_packages(),
    install_requires=[
        "customtkinter",
        "sv_ttk",
        "pymongo",
        "cryptography",
        "Pillow",  # Required for customtkinter
        "discord.py",
        "google-api-python-client",  # For calendar integration
        "google-auth-oauthlib",
        "requests",  # For Ollama API calls
    ],
    entry_points={
        'console_scripts': [
            'rowan=core.rowan_assistant:main',
        ],
    },
    python_requires='>=3.8',
    include_package_data=True,
    package_data={
        'modules.discord': ['emojibank.json'],
        'config': ['.env', 'settings.py', 'memory_config.py'],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
)