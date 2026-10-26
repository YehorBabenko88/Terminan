"""Offline, loopback-only Chromium/Edge G0 smoke evidence; never a physical PASS."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18765/")
    parser.add_argument("--browser", choices=("chromium", "msedge"), default="chromium")
    parser.add_argument("--output", default="qa-evidence")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    u = urlsplit(args.url)
    if (u.scheme != "http" or u.hostname != "127.0.0.1"
            or u.path not in ("", "/") or u.query or u.fragment
            or u.username or u.password or u.port is None or u.port == 0):
        parser.error("Only explicit http://127.0.0.1:PORT/ is allowed")
    allowed_origin = "%s://%s:%s" % (u.scheme, u.hostname, u.port)
    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        parser.error("Evidence output must be an empty directory")
    git = subprocess.run(["git", "-C", args.repo, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=False)
    source_sha = git.stdout.strip() if git.returncode == 0 else None
    if not source_sha or len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        parser.error("A valid pinned Git HEAD is required for provenance")
    evidence = {
        "classification": "OFFLINE_SYNTHETIC_BROWSER_NOT_LIVE",
        "physical_pass": False,
        "source_sha": source_sha,
        "browser": args.browser,
        "utc": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "files_sha256": {},
        "not_tested": ["real desktop GPU/FPS", "CPU/RAM", "physical high-DPI",
                       "live sources", "GAP/STALE", "reconnect", "trading"],
    }
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, channel="msedge" if args.browser == "msedge" else None)
        for dpr in (1, 1.5, 2):
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                device_scale_factor=dpr, service_workers="block")
            context.route("**/*", lambda route: route.continue_()
                          if ("%s://%s:%s" % (urlsplit(route.request.url).scheme,
                              urlsplit(route.request.url).hostname,
                              urlsplit(route.request.url).port)) == allowed_origin
                          else route.abort())
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda err: errors.append("pageerror"))
            page.on("console", lambda msg: errors.append("console.error")
                    if msg.type == "error" else None)
            check = {"dpr": dpr, "status": "FAIL"}
            try:
                response = page.goto(args.url, wait_until="domcontentloaded", timeout=15000)
                check["http_status"] = response.status if response else None
                check["title"] = page.title()[:100]
                check["blank_screen"] = not bool(page.locator("body").inner_text().strip())
                check["controls_present"] = all(
                    page.locator("#" + key).count() == 1
                    for key in ("symbols", "selected", "tf", "refresh", "chart", "error"))
                for width, height in ((1280, 800), (800, 600), (1920, 1080)):
                    page.set_viewport_size({"width": width, "height": height})
                    page.wait_for_timeout(200)
                    name = "browser_%s_dpr%s_%sx%s.png" % (
                        args.browser, str(dpr).replace(".", "_"), width, height)
                    page.screenshot(path=str(out / name))
                reloaded = page.reload(wait_until="domcontentloaded", timeout=15000)
                check["reload_ok"] = bool(reloaded and reloaded.status == 200)
                check["reload_blank_screen"] = not bool(page.locator("body").inner_text().strip())
                check["reload_controls_present"] = all(
                    page.locator("#" + key).count() == 1
                    for key in ("symbols", "selected", "tf", "refresh", "chart", "error"))
                check["console_error_count"] = len(errors)
                check["status"] = ("SYNTHETIC_SMOKE_PASS"
                    if check["http_status"] == 200 and not check["blank_screen"]
                    and check["controls_present"] and check["reload_ok"]
                    and not check["reload_blank_screen"] and check["reload_controls_present"]
                    and not errors else "FAIL")
            except Exception as exc:
                check["error_type"] = type(exc).__name__
            evidence["checks"].append(check)
            context.close()
        browser.close()
    for path in sorted(out.glob("*.png")):
        evidence["files_sha256"][path.name] = digest(path)
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest), "sha256": digest(manifest),
                      "statuses": [c["status"] for c in evidence["checks"]]}))
    return 0 if all(c["status"] == "SYNTHETIC_SMOKE_PASS"
                    for c in evidence["checks"]) else 1

if __name__ == "__main__":
    sys.exit(main())
