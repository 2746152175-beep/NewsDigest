"""Shared data structures used across the news agent pipeline."""

from dataclasses import dataclass


@dataclass
class Item:
    """Normalized news item shared by R0-R3 stages."""

    id: str
    title: str
    url: str
    summary: str
    source: str
    source_type: str
    published_at: str
    author: str
