"""Print the bookmarks made in the last 7 days to STDOUT.

Usage:

    $ python foxtail/__main__.py [firefox_dir] [--hours <HH>] [--days <DD>]
    $ python -m foxtail [firefox_dir] [--hours <HH>] [--days <DD>]

"""

import argparse
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path
from warnings import warn

VERSION = "1.0.1"
CACHE_PATH = Path.home() / ".cache/foxtail"


@dataclass
class Result:
    url: str
    title: str
    time: int
    # summary: str = ""

    def get_date(self) -> datetime.date:
        return (
            datetime.fromtimestamp(int(self.time / 1e6), timezone.utc)
            .astimezone()
            .date()
            .isoformat()
        )


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    cur_time = datetime.now().astimezone()

    parser.add_argument(
        "firefox_dir",
        nargs="?",
        default="~/.mozilla/firefox",
    )

    parser.add_argument(
        "--after",
        type=str,
        default=(cur_time - timedelta(days=7)).isoformat(),
    )
    parser.add_argument(
        "--before",
        type=str,
        default=cur_time.isoformat(),
    )

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="markdown",
        choices=["markdown", "table"],
    )

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        default=False,
    )
    # parser.add_argument("-i", "--interactive", action="store_true", default=False)
    return parser.parse_args()


def foxtail() -> list[str]:
    args = parse()
    if args.version:
        print(VERSION)
        return

    if args.before < args.after:
        raise ValueError()

    after = datetime.fromisoformat(args.after)
    before = datetime.fromisoformat(args.before)

    database = get_database(args.firefox_dir)

    database_cp = CACHE_PATH / "places.sqlite"
    database_cp.parent.mkdir(exist_okay=True, parents=True)
    shutil.copy(database, database_cp)

    results = query_database(database_cp, after=after, before=before)

    # TODO interactive mode

    if args.format == "markdown":
        lines = format_results_markdown(results)
    else:
        lines = format_results_table(results)

    return lines


def get_database(firefox_dir: Path | str) -> Path:
    firefox_dir = Path(firefox_dir).expanduser()
    databases = [fp for fp in firefox_dir.glob("**/*.sqlite") if fp.stem == "places"]

    if len(databases) == 0:
        raise FileNotFoundError("Couldn't find `places.sqlite`.")

    database = databases[0]
    if (n_databases := len(databases)) > 1:
        warn(f"Found {n_databases} `places.sqlite` files, using {str(database)}.")

    return database


def query_database(database: Path, after: datetime, before: datetime) -> list[Result]:
    with sqlite3.connect(database) as con:
        cursor = con.cursor()

        query = f"""
        SELECT p.url, b.title, b.dateAdded
        FROM moz_places p INNER JOIN moz_bookmarks b
        ON p.id = b.fk
        WHERE b.dateAdded > {after.timestamp() * 1e6}
        AND b.dateAdded < {before.timestamp() * 1e6};
        """

        return [Result(*row) for row in cursor.execute(query).fetchall()]


def format_results_table(results: list[Result]) -> list[str]:
    return [
        "\t".join([result.get_date(), result.title, result.url])
        for result in sorted(results, key=lambda x: x.time)
    ]


def format_results_markdown(results: list[Result]) -> list[str]:
    grouped_results = {
        k: sorted(v, key=lambda x: x.time)
        for k, v in groupby(
            results,
            key=lambda x: x.get_date(),
        )
    }

    lines = []
    for date in sorted(grouped_results.keys()):
        lines.append(f"## {date}")
        lines.append("")

        date_results = sorted(grouped_results[date], key=lambda x: x.time)
        for result in date_results:
            title_escaped = result.title.replace("]", "\]").replace("[", "\[")
            lines.append(f"[{title_escaped}]({result.url})")
            lines.append("")

    return lines


def main() -> int:
    exit_code = 0
    try:
        print("\n".join(foxtail()))
    except Exception as err:
        print(f"Encountered error: {str(err)}", file=sys.stderr)
        exit_code = 1
        if os.environ.get("FOXTAIL_DEBUG", "false").lower().startswith("t"):
            raise err
    return exit_code


if __name__ == "__main__":
    main()
