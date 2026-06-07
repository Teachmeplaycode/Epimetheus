"""Reddit forum crawler — using Reddit's public JSON API (no OAuth needed for reads).

Reddit provides .json suffix on any URL for machine-readable access.
Rate limit for non-OAuth: ~10 req/min. With OAuth (free app): 60 req/min.
We'll use OAuth for production, anonymous for testing.
"""

import asyncio
import json
import os
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx

from epimetheus.crawler.base import BaseCrawler, CrawlProgress, Reply, Topic


class RedditCrawler(BaseCrawler):
    """Incremental crawler for Reddit public API.

    Target subreddits (configurable):
    - r/programming (technical discussion)
    - r/learnprogramming (learning/help patterns)
    - r/ExperiencedDevs (senior dev conversations)
    - r/cscareerquestions (career talk)

    Robots.txt note: Reddit's public .json API is accessible.
    Rate limit is the main constraint, not robots.txt.
    """

    BASE = "https://www.reddit.com"
    OAUTH_BASE = "https://oauth.reddit.com"
    UA = "Epimetheus/0.1 (research project; incremental crawl)"

    DEFAULT_SUBREDDITS = [
        "programming",
        "learnprogramming",
        "ExperiencedDevs",
        "cscareerquestions",
    ]

    def __init__(
        self,
        data_dir: str | Path = "./data",
        client_id: str | None = None,
        client_secret: str | None = None,
        delay_min: float = 2.0,
        delay_max: float = 4.0,
        proxy: str | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw" / "reddit"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.delay_min = delay_min
        self.delay_max = delay_max

        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")

        # Persistent HTTP client
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.UA},
            timeout=httpx.Timeout(30.0),
            proxy=proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"),
        )
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

        # Dedup DB
        self.db_path = self.raw_dir / "crawl_progress.db"
        self.db = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_progress (
                topic_id TEXT PRIMARY KEY,
                subreddit TEXT NOT NULL,
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

    # ---- Auth ----

    async def _authenticate(self) -> str:
        """Get OAuth bearer token (script app, no user context needed)."""
        if self._access_token and datetime.now().timestamp() < self._token_expiry:
            return self._access_token

        if not self.client_id or not self.client_secret:
            # Anonymous fallback: use .json suffix, lower rate limit
            return ""

        resp = await self.client.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            headers={"User-Agent": self.UA},
        )

        if resp.status_code == 200:
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expiry = datetime.now().timestamp() + data["expires_in"] - 60
            return self._access_token

        return ""

    def _headers(self) -> dict:
        h = {"User-Agent": self.UA}
        if self._access_token:
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    # ---- Public API ----

    async def get_latest_topic_ids(
        self, limit: int = 100, subreddit: str = "programming"
    ) -> list[str]:
        """Get newest post IDs from a subreddit."""
        data = await self._request(
            f"/r/{subreddit}/new.json",
            params={"limit": min(limit, 100)},
        )
        if not data:
            return []

        posts = data.get("data", {}).get("children", [])
        return [p["data"]["id"] for p in posts]

    async def get_topic_with_replies(self, topic_id: str) -> tuple[Topic, list[Reply]]:
        """Fetch a Reddit post + all comments.

        Reddit's API returns the post and comments in a single request:
        GET /comments/{post_id}.json
        Returns [post_data, comments_data]
        """
        data = await self._request(f"/comments/{topic_id}.json", params={"limit": 500})

        if not data or len(data) < 2:
            raise ValueError(f"Post {topic_id} not found")

        post_data = data[0]["data"]["children"][0]["data"]
        comments_data = data[1]["data"]["children"]

        topic = Topic(
            id=post_data["id"],
            title=post_data.get("title", ""),
            content=post_data.get("selftext", ""),
            author=post_data.get("author", "[deleted]"),
            node=post_data.get("subreddit", "unknown"),
            created_at=datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc),
            reply_count=post_data.get("num_comments", 0),
            url=f"https://www.reddit.com{post_data.get('permalink', '')}",
        )

        replies = self._extract_replies(comments_data, topic_id)

        return topic, replies

    def _extract_replies(self, children: list, topic_id: str, depth: int = 0) -> list[Reply]:
        """Recursively extract comments from Reddit's nested tree."""
        results = []
        idx = 0

        for child in children:
            if child["kind"] == "more":
                continue  # "load more comments" stub, skip

            data = child["data"]
            results.append(Reply(
                id=data["id"],
                topic_id=topic_id,
                content=data.get("body", ""),
                author=data.get("author", "[deleted]"),
                floor=idx,
                created_at=datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc),
                thanks_count=data.get("ups", 0),
            ))
            idx += 1

            # Recurse into nested replies (limit depth to 3 for sanity)
            if depth < 3 and data.get("replies") and isinstance(data["replies"], dict):
                nested = data["replies"]["data"]["children"]
                results.extend(self._extract_replies(nested, topic_id, depth + 1))

        return results

    async def crawl_incremental(
        self, max_new_topics: int = 200, subreddits: list[str] | None = None
    ) -> CrawlProgress:
        """Main entry: crawl new posts across configured subreddits."""
        progress = CrawlProgress(source="reddit")

        if subreddits is None:
            subreddits = self.DEFAULT_SUBREDDITS

        # Authenticate if credentials available
        token = await self._authenticate()
        mode = "OAuth" if token else "anonymous"
        per_sub = max(10, max_new_topics // len(subreddits))

        for subreddit in subreddits:
            new_ids = await self.get_latest_topic_ids(limit=per_sub, subreddit=subreddit)

            uncrawled = []
            for tid in new_ids:
                if not self._is_crawled(tid):
                    uncrawled.append(tid)
                else:
                    progress.topics_skipped += 1

            for topic_id in uncrawled:
                try:
                    topic, replies = await self.get_topic_with_replies(topic_id)

                    self._append_topic(topic)
                    for reply in replies:
                        self._append_reply(reply)

                    self._mark_crawled(topic_id, subreddit, "done")
                    progress.topics_done += 1
                    progress.replies_saved += len(replies)
                    progress.last_topic_id = topic_id

                    await self._delay()

                except Exception as e:
                    self._mark_crawled(topic_id, subreddit, "failed", str(e))
                    progress.topics_failed += 1
                    await self._delay()

        self._save_stats(progress)

        return progress

    # ---- Internal (same pattern as V2EX) ----

    def _is_crawled(self, topic_id: str) -> bool:
        row = self.db.execute(
            "SELECT status FROM crawl_progress WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        return row is not None and row[0] == "done"

    def _mark_crawled(self, topic_id: str, subreddit: str, status: str, error: str | None = None):
        self.db.execute(
            """INSERT OR REPLACE INTO crawl_progress
               (topic_id, subreddit, status, crawled_at, error_msg)
               VALUES (?, ?, ?, ?, ?)""",
            (topic_id, subreddit, status, datetime.now(timezone.utc).isoformat(), error),
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
        self, endpoint: str, params: dict | None = None, auth_required: bool = False
    ) -> dict | list | None:
        """Unified HTTP request with OAuth header."""
        url = f"{self.BASE}{endpoint}"

        for attempt in range(4):
            try:
                await self._delay()

                headers = self._headers()
                resp = await self.client.get(url, params=params, headers=headers)

                if resp.status_code == 401 and not auth_required:
                    # Token expired, re-auth and retry
                    self._access_token = None
                    await self._authenticate()
                    continue

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
