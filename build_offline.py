"""Build the browser-only and Python-backed single-file Iris pages."""

from __future__ import annotations

import base64
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui"
OFFLINE_OUTPUT = ROOT / "Iris_Classifier_Offline.html"
LOCAL_OUTPUT = ROOT / "Iris_Classifier_Local.html"


def data_uri(path: Path, media_type: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def script_json(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> None:
    landing = (UI / "landing.html").read_text(encoding="utf-8")
    form = (UI / "index.html").read_text(encoding="utf-8")
    landing_css = (UI / "landing.css").read_text(encoding="utf-8")
    form_css = (UI / "offline-form.css").read_text(encoding="utf-8")
    landing_js = (UI / "landing.js").read_text(encoding="utf-8")
    offline_js = (UI / "offline.js").read_text(encoding="utf-8")
    local_js = (UI / "local.js").read_text(encoding="utf-8")

    if "fetch('/api/info')" not in landing_js:
        raise RuntimeError("The landing script changed; review the offline build.")
    story_js = landing_js.split("fetch('/api/info')", 1)[0]
    video = data_uri(UI / "assets" / "iris-scroll.mp4", "video/mp4")
    opening_image = data_uri(UI / "assets" / "iris-opening.jpg", "image/jpeg")
    final_image = data_uri(UI / "assets" / "iris-final.jpg", "image/jpeg")

    body = landing.split("<body>", 1)[1].split("</body>", 1)[0]
    body = body.replace('href="/"', 'href="#top"')
    body = body.replace('href="/predict"', 'href="#classify"')
    body = body.replace('poster="/assets/iris-opening.jpg"', f'poster="{opening_image}"')
    body = body.replace('src="/assets/iris-scroll.mp4"', f'src="{video}"')
    landing_css = landing_css.replace("/assets/iris-opening.jpg", opening_image)
    landing_css = landing_css.replace("/assets/iris-final.jpg", final_image)

    form_start = form.index('<div class="workspace-grid">')
    form_end = form.index("</main>", form_start)
    form_markup = form[form_start:form_end]
    classifier = f"""
    <section class="classifier-section" id="classify" aria-labelledby="classifier-title">
      <a class="classifier-back" href="#top">↑ BACK TO STORY</a>
      <div class="classifier-intro">
        <p class="section-tag">02 / THE CLASSIFIER</p>
        <h2 id="classifier-title">Measure a flower.<br><em>See its species.</em></h2>
        <p class="classifier-copy">Enter four positive measurements in centimeters. MODEL_LOCATION</p>
        BACKEND_STATUS
      </div>
      {form_markup}
    </section>
"""
    body = body.replace("  </main>", classifier + "  </main>", 1)

    def render(title: str, description: str, page_body: str, data_scripts: str, app_script: str) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#08080b">
  <meta name="description" content="{description}">
  <title>{title}</title>
  <style>\n{landing_css}\n{form_css}\n</style>
</head>
<body id="top">
{page_body}
{data_scripts}
  <script>\n{story_js}\n{app_script}\n</script>
</body>
</html>
"""

    offline_body = body.replace("MODEL_LOCATION", "This saved model runs in your browser.").replace("BACKEND_STATUS", "")
    offline_data = (f"<script id=\"model-data\" type=\"application/json\">{script_json(ROOT / 'model.json')}</script>\n"
                    f"<script id=\"metrics-data\" type=\"application/json\">{script_json(ROOT / 'metrics.json')}</script>")
    OFFLINE_OUTPUT.write_text(render("Iris classifier · Offline", "Browser-only Iris species classifier with no server required.",
                                     offline_body, offline_data, offline_js), encoding="utf-8")
    print(f"Built {OFFLINE_OUTPUT} ({OFFLINE_OUTPUT.stat().st_size:,} bytes)")

    local_body = body.replace("MODEL_LOCATION", "The Python model runs on this laptop.")
    local_body = local_body.replace("BACKEND_STATUS", '<p class="backend-status" id="backend-status" role="status">Checking the local Python model…</p>')
    LOCAL_OUTPUT.write_text(render("Iris classifier · Local model", "Iris classifier with a browser interface and a local Python model.",
                                   local_body, "", local_js), encoding="utf-8")
    print(f"Built {LOCAL_OUTPUT} ({LOCAL_OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
