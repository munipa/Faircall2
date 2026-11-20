"""Build the static FairCall website for GitHub Pages into docs/.

It writes the same data the API serves as JSON files, plus a copy of
web/index.html that reads them, so the site needs no server.

Usage:
    python -m scripts.build_site            # writes docs/index.html and docs/data/
then commit docs/ and push. In the repo's Settings > Pages, set the source to
"Deploy from a branch", branch main, folder /docs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "index.html"
MARKER = "<script>\nconst $ ="


def build(out_dir: Path = ROOT / "docs") -> dict:
    from api import main as api

    data = out_dir / "data"
    data.mkdir(parents=True, exist_ok=True)      # files are overwritten in place

    def write(name: str, payload) -> None:
        (data / name).write_text(json.dumps(payload, separators=(",", ":")))

    seasons = api.seasons()
    if not seasons:
        raise SystemExit("no leaderboards in reports/; run python -m analysis.umpire_stats first")
    write("seasons.json", seasons)
    ids = set()
    for s in seasons:
        board = api.leaderboard(s)
        write(f"leaderboard_{s}.json", board)
        ids.update(int(r["umpire_id"]) for r in board)
        try:
            write(f"framing_{s}.json", api.framing(s))
        except HTTPException:
            pass
    write("umpires.json", {str(i): api.umpire(i) for i in sorted(ids)})
    built = {"seasons": seasons, "umpires": len(ids)}
    for name, fn in (("trends.json", api.trends), ("advisor.json", api._advisor)):
        try:
            write(name, fn())
            built[name] = True
        except HTTPException:
            built[name] = False
            print(f"skipped {name} (its report hasn't been built yet)")

    page = WEB.read_text()
    if MARKER not in page:
        raise SystemExit("web/index.html has changed; can't find where to switch on static mode")
    page = page.replace(MARKER, "<script>window.FAIRCALL_STATIC = true;</script>\n" + MARKER, 1)
    (out_dir / "index.html").write_text(page)
    (out_dir / ".nojekyll").write_text("")      # serve files as they are
    print(f"built {out_dir}/index.html with {len(seasons)} seasons and {len(ids)} umpires")
    return built


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--out", type=Path, default=ROOT / "docs")
    build(p.parse_args().out)


if __name__ == "__main__":
    main()
