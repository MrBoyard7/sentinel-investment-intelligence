"""
Sentinel: an AI-powered investment intelligence & alert system.

Sentinel watches government, regulatory, legal, and industry sources for
developments relevant to a configurable investment theme, scores each item
for importance and sentiment using an LLM, stores everything in a
queryable dashboard, and raises alerts when something significant happens.

This package is intentionally structured around five stages that map
directly onto the required workflow:

    Source -> Collection -> AI Analysis -> Dashboard -> Alert

See docs/architecture.md for the full design write-up.
"""

__version__ = "1.0.0"
