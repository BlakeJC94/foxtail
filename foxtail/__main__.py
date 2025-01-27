"""A script to help write about recent firefox bookmarks."""

import argparse
import json
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path
from warnings import warn

VERSION = "3.0.0"
CACHE_PATH = Path.home() / ".cache/foxtail"


@dataclass
class Result:
    """A class to represent a bookmark record.

    Attributes:
        url: The URL of the result.
        title: The title of the result.
        time: The timestamp in microseconds. This will be used to get the date component of the result.
        summary: The summary of the result. Default value is an empty string.
    """

    url: str
    title: str
    time: int
    summary: str = ""

    def get_date(self) -> str:
        """Get the date part of the timestamp in the specified timezone and format it as ISO 8601
        standard.

        Returns:
            The date component of the result.
        """
        return (
            datetime.fromtimestamp(int(self.time / 1e6), timezone.utc)
            .astimezone()
            .date()
            .isoformat()
        )


class InputCache:
    """Cache manager for the summary inputs."""

    cache = CACHE_PATH / "input.sqlite3"

    def __init__(self):
        """Initialize the input cache. If the file does not exist, create a new table. Otherwise, purge old entries."""
        if not self.cache.exists():
            with sqlite3.connect(self.cache) as con:
                cursor = con.cursor()
                cursor.execute("CREATE TABLE input(url, summary, timeAdded)")
                con.commit()
        else:
            cur_time = datetime.now().astimezone()
            delta = timedelta(days=30)
            with sqlite3.connect(self.cache) as con:
                cursor = con.cursor()
                cursor.execute(
                    f"DELETE FROM input WHERE timeAdded < {(cur_time - delta).timestamp()};"
                )
                con.commit()

    def __contains__(self, url: str) -> bool:
        """Check if a URL is in the cache."""
        with sqlite3.connect(self.cache) as con:
            cursor = con.cursor()
            query = f"SELECT url FROM input WHERE url = '{url}';"
            result = cursor.execute(query).fetchall()
            return True if result else False

    def __getitem__(self, url: str) -> str:
        """Get the summary for a URL from the cache. If not found, raise KeyError."""
        with sqlite3.connect(self.cache) as con:
            cursor = con.cursor()
            query = f"""
            SELECT url, summary
            FROM input
            WHERE url = '{url}';
            """
            result = cursor.execute(query).fetchall()
        if not result:
            raise KeyError(f"'{url}' not found")
        return result[0][1]

    def __setitem__(self, url: str, summary: str) -> None:
        """Set the summary for a URL in the cache and update its timeAdded timestamp."""
        cur_time = datetime.now().astimezone().timestamp()
        with sqlite3.connect(self.cache) as con:
            cursor = con.cursor()
            query = f"""
            UPDATE input
            SET summary = '{summary}', timeAdded = {cur_time}
            WHERE url = '{url}';
            """
            cursor.execute(query)
            con.commit()

    def get(self, url: str, fallback=None):
        """Get the summary for a URL from the cache. If not found, return the fallback value."""
        if url not in self:
            return fallback
        return self[url]


def parse() -> argparse.Namespace:
    """Parse CLI arguments using argparse.

    Returns:
        argparse.Namespace: Parsed command line arguments as an argparse_namespace object.
    """
    parser = argparse.ArgumentParser()
    cur_time = datetime.now().astimezone()

    parser.add_argument(
        "firefox_dir",
        nargs="?",
        default="~/.mozilla/firefox",
        help="Directory path for Mozilla Firefox profiles (default: ~/.mozilla/firefox).",
    )

    parser.add_argument(
        "--after",
        type=str,
        default=(cur_time - timedelta(days=7)).isoformat(),
        help="Return results after this ISO-formatted datetime, (default: 7 days ago).",
    )
    parser.add_argument(
        "--before",
        type=str,
        default=cur_time.isoformat(),
        help="Return results before this ISO-formatted datetime, (default: now).",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        nargs="?",
        help="Output file path (default: ./foxtail.txt)",
    )

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="markdown",
        choices=["markdown", "table", "json", "csv"],
        help="Output format choice ('markdown', 'table', 'json', or 'csv'; default: markdown).",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        default=False,
        help="Show version information and exit.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        default=False,
        help="Enable interactive mode for inputting summaries.",
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite output file if present.",
    )

    return parser.parse_args()


def foxtail(args: argparse.Namespace) -> list[str]:
    """Generates Foxtail summary from a given query interval.

    Args:
        args: CLI arguments.

    Returns:
        Formatted Foxtail summary as strings.
    """
    if args.version:
        print(VERSION)
        return

    if args.before < args.after:
        raise ValueError("Invalid query interval")

    after = datetime.fromisoformat(args.after)
    before = datetime.fromisoformat(args.before)

    database = get_database(args.firefox_dir)

    database_cp = CACHE_PATH / "places.sqlite"
    database_cp.parent.mkdir(exist_ok=True, parents=True)
    shutil.copy(database, database_cp)

    results = query_database(database_cp, after=after, before=before)

    if args.interactive:
        results = input_summaries(results)

    formatter = {
        "markdown": format_results_markdown,
        "table": format_results_table,
        "json": format_results_json,
        "csv": format_results_csv,
    }.get(args.format)
    lines = formatter(results)

    return lines


def input_summaries(results: list[Result]) -> list[Result]:
    print(f"Starting interactive annotation mode for {len(results)} entries")
    print("Use Ctrl-D to exit")
    print("========")
    cache = InputCache()
    for i, result in enumerate(results, start=1):
        print(f"{i}: {result.title}")
        print(result.url)
        summary = cache.get(result.url, "")
        if summary:
            print(">> Previous summary:")
            for line in summary.split("\n"):
                print(f">> {line}")

        try:
            summary = multiline_input("> ", 2)
            cache[result.url] = summary
        except EOFError:
            break

        result.summary = summary
        print("")
    print("========")
    return results


def multiline_input(prompt, max_returns) -> str:
    x = input(prompt)
    inp = [x]
    n_lines = 1 if x == "" else 0
    while n_lines < max_returns:
        x = input(prompt)
        inp.append(x)
        if x == "":
            n_lines += 1
    return "\n".join(inp).strip()


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
        "\t".join(
            [
                result.get_date(),
                result.title,
                result.url,
                result.summary.replace("\n", "\\n"),
            ]
        )
        for result in sorted(results, key=lambda x: x.time)
    ]


def format_results_csv(results: list[Result]) -> list[str]:
    return [
        ",".join(
            [
                result.get_date(),
                result.title,
                result.url,
                result.summary.replace("\n", "\\n"),
            ]
        )
        for result in sorted(results, key=lambda x: x.time)
    ]


def format_results_json(results: list[Result]) -> list[str]:
    output = {
        "results": [
            {
                "date": result.get_date(),
                "title": result.title,
                "url": result.url,
                "summary": result.summary.replace("\n", "\\n"),
            }
            for result in sorted(results, key=lambda x: x.time)
        ]
    }
    output = json.dumps(output, indent=2)
    return output.split("\n")


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
            if result.summary:
                lines.append(result.summary)
                lines.append("")

    return lines


def check_python_version():
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 10:  # noqa: PLR2004
        raise RuntimeError("foxtail requires Python >= 3.10")


def main() -> int:
    exit_code = 0
    try:
        check_python_version()
        args = parse()
        file = Path(args.output or "./foxtail.txt")
        if file.exists() and not args.overwrite:
            raise FileExistsError(f"Output file {str(file)} already exists.")
        foxtail_output = "\n".join(foxtail(args))
        file.parent.mkdir(exist_ok=True, parents=True)
        suffix = {
            "markdown": ".md",
            "table": ".txt",
            "json": ".json",
            "csv": ".csv",
        }.get(args.format)
        file = file.with_suffix(suffix)
        with open(file, "w") as f:
            print(foxtail_output, file=f)
        print(f"Generated output at {str(file)}", file=sys.stderr)
    except Exception as err:
        print(f"Encountered error: {str(err)}", file=sys.stderr)
        exit_code = 1
        if os.environ.get("FOXTAIL_DEBUG", "false").lower().startswith("t"):
            raise err
    return exit_code


if __name__ == "__main__":
    main()
