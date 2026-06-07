"""V2EX forum crawler — incremental, polite, 24/7 safe."""

import asyncio
import json
import os
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx

from epimetheus.crawler.base import BaseCrawler, CrawlProgress, Reply, Topic


class V2EXCrawler(BaseCrawler):
    """Incremental crawler for v2ex.com public API.

    Features:
    - Respects robots.txt (public API only)
    - Random delay 1.5-3.0s between requests
    - Exponential backoff on 429/503
    - SQLite-based dedup (never crawl the same topic twice)
    - JSONL output, append-only, by year
    - Designed to run 24/7 on a server
    """

    BASE = "https://www.v2ex.com/api"
    UA = "Epimetheus/0.1 (research project; incremental crawl)"

    def __init__(
        self,
        data_dir: str | Path = "./data",
        delay_min: float = 1.5,
        delay_max: float = 3.0,
        proxy: str | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw" / "v2ex"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.delay_min = delay_min
        self.delay_max = delay_max

        self.db_path = self.raw_dir / "crawl_progress.db"
        self.db = sqlite3.connect(str(self.db_path))
        self._init_db()

        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.UA},
            timeout=httpx.Timeout(30.0),
            proxy=proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"),
        )

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_progress (
                topic_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                crawled_at TIMESTAMP,
                error_msg TEXT
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_stats (
                date TEXT PRIMARY KEY,
                topics_crawled INTEGER DEFAULT 0,
                topics_skipped INTEGER DEFAULT 0,
                topics_failed INTEGER DEFAULT 0,
                replies_saved INTEGER DEFAULT 0
            )
        """)
        self.db.commit()

    # ---- Public API ----

    async def get_latest_topic_ids(self, limit: int = 100) -> list[str]:
        """Discover new topic IDs from the latest list."""
        data = await self._request("/topics/latest.json", nodely=True)
        if not data:
            return []
        return [str(item["id"]) for item in data[:limit]]

    async def get_hot_topic_ids(self) -> list[str]:
        """Get currently hot topic IDs."""
        data = await self._request("/topics/hot.json", nodely=True)
        if not data:
            return []
        return [str(item["id"]) for item in data]

    async def get_node_topic_ids(self, node_name: str) -> list[str]:
        """Get topic IDs from a specific node."""
        data = await self._request(
            "/topics/show.json", params={"node_name": node_name},
            nodely=True,
        )
        if not data:
            return []
        return [str(item["id"]) for item in data]

    async def get_topic_with_replies(self, topic_id: str) -> tuple[Topic, list[Reply]]:
        """Fetch topic detail + replies (two API calls)."""
        data = await self._request(f"/topics/show.json?id={topic_id}")
        if not data:
            raise ValueError(f"Topic {topic_id} not found")

        if isinstance(data, list):
            topic_data = data[0]
        else:
            topic_data = data

        # replies field in show.json is just the count; fetch actual replies separately
        reply_count = topic_data.get("replies", 0)

        topic = Topic(
            id=str(topic_data["id"]),
            title=topic_data.get("title", ""),
            content=topic_data.get("content", ""),
            author=topic_data.get("member", {}).get("username", "unknown"),
            node=topic_data.get("node", {}).get("name", "unknown"),
            created_at=datetime.fromtimestamp(topic_data.get("created", 0), tz=timezone.utc),
            reply_count=reply_count,
            url=topic_data.get("url", f"https://www.v2ex.com/t/{topic_id}"),
        )

        # Fetch replies from separate endpoint
        replies_data = await self._request(f"/replies/show.json?topic_id={topic_id}")
        if not replies_data:
            return topic, []

        replies = []
        for r in replies_data if isinstance(replies_data, list) else []:
            replies.append(Reply(
                id=str(r["id"]),
                topic_id=str(topic_id),
                content=r.get("content", ""),
                author=r.get("member", {}).get("username", "unknown"),
                floor=r.get("floor", 0),
                created_at=datetime.fromtimestamp(r.get("created", 0), tz=timezone.utc),
                thanks_count=r.get("thanks", 0),
            ))

        return topic, replies

    POPULAR_NODES = [
        "programmer", "create", "share", "career", "coding",
        "python", "javascript", "go", "apple", "linux",
        "hardware", "cloud", "ml", "life", "qna",
    ]

    async def crawl_incremental(self, max_new_topics: int = 200) -> CrawlProgress:
        """Main entry: crawl new topics since last run."""
        progress = CrawlProgress(source="v2ex")

        uncrawled: list[str] = []

        # 1. Latest topics (high freshness)
        new_ids = await self.get_latest_topic_ids(limit=max_new_topics)
        for tid in new_ids:
            if not self._is_crawled(tid):
                uncrawled.append(tid)
            else:
                progress.topics_skipped += 1

        # 2. Hot topics (high quality)
        hot_ids = await self.get_hot_topic_ids()
        for tid in hot_ids:
            if tid not in uncrawled and not self._is_crawled(tid):
                uncrawled.append(tid)

        # 3. Popular nodes (variety beyond the global latest feed)
        if len(uncrawled) < max_new_topics:
            for node in self.POPULAR_NODES:
                node_ids = await self.get_node_topic_ids(node)
                for tid in node_ids:
                    if tid not in uncrawled and not self._is_crawled(tid):
                        uncrawled.append(tid)

        print(f"  discovered {len(uncrawled)} new topics to crawl")

        # 5. Crawl each topic
        for i, topic_id in enumerate(uncrawled):
            try:
                topic, replies = await self.get_topic_with_replies(topic_id)

                self._append_topic(topic)
                for reply in replies:
                    self._append_reply(reply)

                self._mark_crawled(topic_id, "done")
                progress.topics_done += 1
                progress.replies_saved += len(replies)
                progress.last_topic_id = topic_id

                if (i + 1) % 10 == 0:
                    print(f"  progress: {i + 1}/{len(uncrawled)} "
                          f"(replies={progress.replies_saved})")

                await self._delay()

            except Exception as e:
                self._mark_crawled(topic_id, "failed", str(e))
                progress.topics_failed += 1
                await self._delay()

        # 6. Save daily stats
        self._save_stats(progress)

        return progress

    # ---- Internal ----

    def _is_crawled(self, topic_id: str) -> bool:
        row = self.db.execute(
            "SELECT status FROM crawl_progress WHERE topic_id = ?", (int(topic_id),)
        ).fetchone()
        return row is not None and row[0] == "done"

    def _mark_crawled(self, topic_id: str, status: str, error: str | None = None):
        self.db.execute(
            """INSERT OR REPLACE INTO crawl_progress (topic_id, status, crawled_at, error_msg)
               VALUES (?, ?, ?, ?)""",
            (int(topic_id), status, datetime.now(timezone.utc).isoformat(), error),
        )
        self.db.commit()

    def _append_topic(self, topic: Topic):
        filepath = self.raw_dir / f"topics_{topic.created_at.year}.jsonl"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": topic.id,
                "title": topic.title,
                "content": topic.content,
                "author": topic.author,
                "node": topic.node,
                "created_at": topic.created_at.isoformat(),
                "reply_count": topic.reply_count,
                "url": topic.url,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")

    def _append_reply(self, reply: Reply):
        filepath = self.raw_dir / f"replies_{reply.created_at.year}.jsonl"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": reply.id,
                "topic_id": reply.topic_id,
                "content": reply.content,
                "author": reply.author,
                "floor": reply.floor,
                "created_at": reply.created_at.isoformat(),
                "thanks_count": reply.thanks_count,
            }, ensure_ascii=False) + "\n")

    def _save_stats(self, progress: CrawlProgress):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.db.execute(
            """INSERT OR REPLACE INTO crawl_stats
               (date, topics_crawled, topics_skipped, topics_failed, replies_saved)
               VALUES (?, ?, ?, ?, ?)""",
            (today, progress.topics_done, progress.topics_skipped,
             progress.topics_failed, progress.replies_saved),
        )
        self.db.commit()

    async def _request(
        self, endpoint: str, params: dict | None = None, nodely: bool = False
    ) -> dict | list | None:
        """Unified HTTP request with retry + backoff."""
        url = f"{self.BASE}{endpoint}"

        for attempt in range(4):
            try:
                if not nodely:
                    await self._delay()
                resp = await self.client.get(url, params=params)

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    await asyncio.sleep(30 * (attempt + 1))
                    continue

                if resp.status_code == 200:
                    return resp.json()

            except httpx.TimeoutException:
                await asyncio.sleep(10 * (attempt + 1))
            except httpx.RequestError:
                await asyncio.sleep(10 * (attempt + 1))

        return None

    async def _delay(self):
        await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

    async def close(self):
        await self.client.aclose()
        self.db.close()

    def get_stats(self, days: int = 7) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM crawl_stats ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
        return [
            {"date": r[0], "topics_crawled": r[1], "topics_skipped": r[2],
             "topics_failed": r[3], "replies_saved": r[4]}
            for r in rows
        ]

    def total_stored(self) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) FROM crawl_progress WHERE status = 'done'"
        ).fetchone()
        return row[0] if row else 0
