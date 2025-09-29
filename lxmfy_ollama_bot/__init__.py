"""LXMFy Ollama Bot - AI-powered chatbot for the LXMF network.

This package provides a complete chatbot solution that integrates Ollama AI models
with the LXMF (Local eXtended Message Format) network for decentralized messaging.
"""

from .bot import OllamaAPI, create_bot

__version__ = "1.2.0"
__all__ = ["OllamaAPI", "create_bot"]
