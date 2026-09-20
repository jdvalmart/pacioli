"""Pacioli backend package.

Layers:

- ``database``: SQLite data layer (money in cents, versioned migrations).
- ``money``: currency formatting and parsing (Colombian conventions).
- ``config``: persistent application configuration (XDG).
- ``services``: integrations with external systems (Ollama AI).
- ``main``: FastAPI application factory (routers registered in later phases).
"""
