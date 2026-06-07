"""Epimetheus CLI entry point."""

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="epimetheus",
        description="Epimetheus — a terminal companion who learns how humans talk",
    )
    sub = parser.add_subparsers(dest="command")

    # ---- crawl ----
    crawl_p = sub.add_parser("crawl", help="Crawl forum data")
    crawl_p.add_argument("--source", default="v2ex", choices=["v2ex", "reddit"])
    crawl_p.add_argument("--max", type=int, default=500, help="Max new topics per run")
    crawl_p.add_argument("--loop", action="store_true", help="Run continuously")
    crawl_p.add_argument("--loop-interval", type=int, default=3600, help="Seconds between loops")
    crawl_p.add_argument("--data-dir", default="./data")
    crawl_p.add_argument("--subreddits", default=None, help="Comma-separated subreddit list")

    # ---- stats ----
    stats_p = sub.add_parser("stats", help="Show crawl statistics")
    stats_p.add_argument("--source", default="v2ex")
    stats_p.add_argument("--days", type=int, default=7)
    stats_p.add_argument("--data-dir", default="./data")

    # ---- analyze (placeholder) ----
    sub.add_parser("analyze", help="Analyze crawled data to extract speech patterns")

    # ---- chat (placeholder) ----
    sub.add_parser("chat", help="Start conversation with Epimetheus")

    args = parser.parse_args()

    if args.command == "crawl":
        asyncio.run(_cmd_crawl(args))
    elif args.command == "stats":
        _cmd_stats(args)
    elif args.command == "analyze":
        _cmd_placeholder("analyze", "Not yet implemented — see docs/phase1-mvp.md")
    elif args.command == "chat":
        _cmd_placeholder("chat", "Not yet implemented — see docs/phase1-mvp.md")
    else:
        parser.print_help()


async def _cmd_crawl(args):
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("all_proxy")
    if args.source == "reddit":
        from epimetheus.crawler import RedditCrawler

        subs = args.subreddits.split(",") if args.subreddits else None
        crawler = RedditCrawler(
            data_dir=args.data_dir,
            delay_min=float(os.getenv("CRAWL_DELAY_MIN", 2.0)),
            delay_max=float(os.getenv("CRAWL_DELAY_MAX", 4.0)),
            proxy=proxy,
        )
    else:
        from epimetheus.crawler import V2EXCrawler

        crawler = V2EXCrawler(
            data_dir=args.data_dir,
            delay_min=float(os.getenv("CRAWL_DELAY_MIN", 1.5)),
            delay_max=float(os.getenv("CRAWL_DELAY_MAX", 3.0)),
            proxy=proxy,
        )
        subs = None

    try:
        if args.loop:
            print(f"Starting continuous crawl loop "
                  f"(source={args.source}, interval={args.loop_interval}s)")
            while True:
                if isinstance(crawler, V2EXCrawler):
                    progress = await crawler.crawl_incremental(max_new_topics=args.max)
                else:
                    progress = await crawler.crawl_incremental(
                        max_new_topics=args.max, subreddits=subs)
                _print_progress(progress)
                await asyncio.sleep(args.loop_interval)
        else:
            if isinstance(crawler, V2EXCrawler):
                progress = await crawler.crawl_incremental(max_new_topics=args.max)
            else:
                progress = await crawler.crawl_incremental(
                    max_new_topics=args.max, subreddits=subs)
            _print_progress(progress)
    finally:
        await crawler.close()


def _cmd_stats(args):
    from epimetheus.crawler import V2EXCrawler

    crawler = V2EXCrawler(data_dir=args.data_dir)
    stats = crawler.get_stats(days=args.days)
    total = crawler.total_stored()
    crawler.db.close()

    print(f"\n{'='*50}")
    print(f"  V2EX Crawl Stats (last {args.days} days)")
    print(f"  Total topics stored: {total}")
    print(f"{'='*50}")
    print(f"{'Date':<12} {'Topics':<10} {'Replies':<10} {'Skipped':<10} {'Failed':<10}")
    print("-" * 52)
    for s in stats:
        print(f"{s['date']:<12} {s['topics_crawled']:<10} {s['replies_saved']:<10} "
              f"{s['topics_skipped']:<10} {s['topics_failed']:<10}")
    print()


def _print_progress(progress):
    from epimetheus.crawler.base import CrawlProgress
    print(f"[{progress.started_at.strftime('%H:%M:%S')}] "
          f"done={progress.topics_done} "
          f"replies={progress.replies_saved} "
          f"skipped={progress.topics_skipped} "
          f"failed={progress.topics_failed} "
          f"last_id={progress.last_topic_id}")


def _cmd_placeholder(cmd: str, msg: str):
    print(f"`epimetheus {cmd}` — {msg}")


def cli():
    main()


if __name__ == "__main__":
    cli()
