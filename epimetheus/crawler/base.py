"""Crawler base classes and utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator


@dataclass
class Topic:
    id: str
    title: str
    content: str
    author: str
    node: str
    created_at: datetime
    reply_count: int
    url: str


@dataclass
class Reply:
    id: str
    topic_id: str
    content: str
    author: str
    floor: int
    created_at: datetime
    thanks_count: int = 0


@dataclass
class CrawlProgress:
    source: str
    topics_done: int = 0
    topics_skipped: int = 0
    topics_failed: int = 0
    replies_saved: int = 0
    last_topic_id: str | None = None
    started_at: datetime = field(default_factory=datetime.now)


class BaseCrawler(ABC):
    """Abstract base for forum crawlers."""

    @abstractmethod
    async def get_latest_topic_ids(self, limit: int = 100) -> list[str]:
        """Get the most recent topic IDs for incremental discovery."""

    @abstractmethod
    async def get_topic_with_replies(self, topic_id: str) -> tuple[Topic, list[Reply]]:
        """Fetch a single topic and all its replies."""

    @abstractmethod
    async def crawl_incremental(self, max_new_topics: int) -> CrawlProgress:
        """Crawl new topics since last run. Returns progress stats."""
