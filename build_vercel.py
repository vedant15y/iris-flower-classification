"""Build the static HTML and saved Python model into vercel-site/."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_UI = ROOT / "ui"
SITE = ROOT / "vercel-site"
PUBLIC = SITE / "public"


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "assets").mkdir(parents=True, exist_ok=True)

    static_files = {
        "landing.css": "landing.css",
        "landing.js": "landing.js",
        "styles.css": "styles.css",
        "app.js": "app.js",
    }
    for source, target in static_files.items():
        shutil.copy2(SOURCE_UI / source, PUBLIC / target)

    landing = (SOURCE_UI / "landing.html").read_text(encoding="utf-8")
    (PUBLIC / "index.html").write_text(
        landing.replace("LOCAL PROJECT · 2026", "IRIS PROJECT · 2026"), encoding="utf-8"
    )
    shutil.copy2(SOURCE_UI / "index.html", PUBLIC / "predict.html")
    for asset in (SOURCE_UI / "assets").iterdir():
        if asset.is_file():
            shutil.copy2(asset, PUBLIC / "assets" / asset.name)

    for filename in ("iris_classifier.py", "model.json", "metrics.json"):
        shutil.copy2(ROOT / filename, SITE / filename)

    print(f"Vercel project ready: {SITE}")


if __name__ == "__main__":
    main()
