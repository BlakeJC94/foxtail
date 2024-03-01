"""Print the bookmarks made in the last 7 days to STDOUT.

Usage:

    $ python foxtail/__main__.py [firefox_dir] [--hours <HH>] [--days <DD>]
    $ python -m foxtail [firefox_dir] [--hours <HH>] [--days <DD>]

"""

import argparse
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from time import time
from typing import Dict, List, Tuple
from warnings import warn

VERSION = "1.0.1"


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("firefox_dir", nargs="?", default="~/.mozilla/firefox")
    parser.add_argument("--hours", type=int, default=0)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("-v", "--version", action="store_true", default=False)
    return parser.parse_args()


def main():
    args = parse()
    if args.version:
        print(VERSION)
        return

    delta = timedelta(days=args.days, hours=args.hours).total_seconds()

    database = get_database(args.firefox_dir)
    with tempfile.TemporaryDirectory() as tmpdirname:
        database_cp = Path(tmpdirname) / "places.sqlite"
        shutil.copy(database, database_cp)
        results = query_database(database_cp, delta=delta)

    lines = format_results(results)
    print("\n".join(lines))


def get_database(firefox_dir: Path | str) -> Path:
    firefox_dir = Path(firefox_dir).expanduser()
    databases = [fp for fp in firefox_dir.glob("**/*.sqlite") if fp.stem == "places"]

    if len(databases) == 0:
        raise FileNotFoundError("Couldn't find `places.sqlite`.")

    database = databases[0]
    if (n_databases := len(databases)) > 1:
        warn(f"Found {n_databases} `places.sqlite` files, using {str(database)}.")

    return database


def query_database(database: Path, delta: float | int) -> List[Tuple[str, str, int]]:
    cur_time = time()
    with sqlite3.connect(database) as con:
        cursor = con.cursor()

        query = f"""
        SELECT p.url, b.title, b.dateAdded
        FROM moz_places p INNER JOIN moz_bookmarks b
        ON p.id = b.fk
        WHERE b.dateAdded > {(cur_time - delta) * 1e6};
        """

        return cursor.execute(query).fetchall()


def format_results(results: List[Tuple[str, str, int]]) -> List[str]:
    grouped_results: Dict[str, List[Tuple[str, str, int]]] = {
        k: list(v)
        for k, v in groupby(
            results, key=lambda x: datetime.fromtimestamp(int(x[2] / 1e6)).date()
        )
    }

    lines = []
    lines.append("# Bookmarks from the last week")
    lines.append("")

    for date in sorted(grouped_results.keys()):
        lines.append(f"## {date}")
        lines.append("")

        date_results = sorted(grouped_results[date], key=lambda x: x[2])
        for url, title_raw, _ in date_results:
            title = title_raw.replace("]", "\]").replace("[", "\[")
            lines.append(f"[{title}]({url})")
            lines.append("")

    return lines


if __name__ == "__main__":
    main()
