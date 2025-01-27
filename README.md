# foxtail 🦊
A script to help write about recent firefox bookmarks using the base libraries of Python 3.10.

Calling `foxtail` will query your recent firefox bookmarks

```markdown
## 2024-12-18

[Jupyter notebooks as e2e tests | exotext](https://rakhim.exotext.com/jupyter-notebooks-as-e2e-tests)

## 2024-12-20

[A Gentle Introduction to Graph Neural Networks](https://distill.pub/2021/gnn-intro/)

[How to Make LLMs Shut Up | Greptile Blog](https://www.greptile.com/blog/make-llms-shut-up)

## 2024-12-21

[GitHub - izabera/pseudo3d](https://github.com/izabera/pseudo3d)

[Front Rack Mobility Constraints and How to Fix Them - \[P\]rehab](https://theprehabguys.com/front-rack-mobility/)
```

This tool also offers an interactive mode, so that you can add commentary to each bookmark.


## Installation

Using `pipx`:
```bash
pipx install git+https://github.com/BlakeJC94/foxtail.git
```

Or, using `curl`:
```bash
mkdir -p ~/.local/bin
curl https://raw.githubusercontent.com/BlakeJC94/scratchpad/main/bookmarks/foxtail/__main__.py > ~/.local/bin/foxtail
chmod a+x ~/.local/bin/foxtail
```

## Usage
Display docs with `foxtail -h`:
```
usage: foxtail [-h] [--after AFTER] [--before BEFORE] [-o [OUTPUT]]
               [-f {markdown,table,json,csv}] [-v] [-i]
               [firefox_dir]

positional arguments:
  firefox_dir           Directory path for Mozilla Firefox profiles (default:
                        ~/.mozilla/firefox).

options:
  -h, --help            show this help message and exit
  --after AFTER         Return results after this ISO-formatted datetime,
                        (default: 7 days ago).
  --before BEFORE       Return results before this ISO-formatted datetime,
                        (default: now).
  -o, --output [OUTPUT]
                        Output file path (default: `./foxtail.txt`)
  -f, --format {markdown,table,json,csv}
                        Output format choice ('markdown', 'table', 'json', or
                        'csv'; default: markdown).
  -v, --version         Show version information and exit.
  -i, --interactive     Enable interactive mode for inputting summaries.
```

## Issues and contributions
Raise an issue here if problems are encountered (or if there's any feature requests). PRs
are welcomed as well!
