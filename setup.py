#!/usr/bin/env python3
"""
A1 Agentic System - Smart Contract Exploit Generation Framework
Based on the research paper: "A1: An Autonomous Agent for Exploit Generation"
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="a1-agentic-system",
    version="1.0.0",
    author="A1 Research Team",
    author_email="research@a1-system.com",
    description="Autonomous agent for smart contract exploit generation using Grok-4-0709",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/a1-research/a1-agentic-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "praisonai>=0.0.50",
        "web3>=6.15.1",
        "eth-abi>=4.2.1",
        "py-solc-x>=2.0.2",
        "requests>=2.31.0",
        "aiohttp>=3.9.1",
        "asyncio>=3.4.3",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "rich>=13.7.0",
        "click>=8.1.7",
        "pandas>=2.1.4",
        "numpy>=1.24.3",
        "eth-utils>=2.3.1",
        "eth-typing>=3.5.2",
        "hexbytes>=0.3.1",
        "openai>=1.6.1",
        "anthropic>=0.8.1",
        "groq>=0.4.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "a1-system=main:main",
        ],
    },
)
