"""Infrastructure adapters. This layer depends inward.

Concrete job sources, persistence, LLM vendors, and Temporal clients belong
here only. Adding a provider must not change domain or application packages.
"""
