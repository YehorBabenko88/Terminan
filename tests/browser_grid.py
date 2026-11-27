"""Offline Chromium regression for Terminan's Grid UI.

Run: python tests/browser_grid.py
Use BROWSER_EXECUTABLE if Playwright Chromium or the local Edge is unavailable.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright


PRICE = "9007199254740993.123456789"
VOLUME = "0.000000000000000000123400"
HTML = Path(__file__).resolve().parents[1] / "terminan" / "index.html"
STALE_REQUEST = threading.Event()
RELEASE_STALE = threading.Event()
STALE_TIMEFRAME_REQUEST = threading.Event()
RELEASE_STALE_TIMEFRAME = threading.Event()
REQUESTS = []


class Fixtures(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        symbol = query.get("symbol", [""])[0]
        timeframe = query.get("timeframe", [""])[0]
        REQUESTS.append((url.path, symbol, timeframe))
        status = 200
        last_price = PRICE if symbol == "ETHUSDT" else "105.001"
        if url.path == "/":
            self.reply(status, "text/html; charset=utf-8", HTML.read_bytes())
            return
        if url.path == "/api/instruments":
            value = ["BTCUSDT", "ETHUSDT", "EMPTYUSDT", "FAILUSDT", "LEGACYUSDT"]
        elif url.path == "/api/status":
            value = {"mode": "READ_ONLY", "grid": True}
        elif url.path == "/api/levels":
            value = [{"timeframe": "1d", "side": "high", "price": last_price}]
        elif url.path == "/api/logs":
            value = {"events": [symbol]}
        elif url.path == "/api/research":
            value = [symbol]
        elif url.path == "/api/candles":
            if symbol == "BTCUSDT":
                STALE_REQUEST.set()
                RELEASE_STALE.wait(8)
                value = [{"o": "100", "h": "110", "l": "90", "c": "105"}] * 3
            elif timeframe == "3m":
                STALE_TIMEFRAME_REQUEST.set()
                RELEASE_STALE_TIMEFRAME.wait(8)
                value = [{"o": "100", "h": "110", "l": "90", "c": "105"}] * 2
            elif symbol == "FAILUSDT":
                status, value = 503, {"error": "fixture unavailable"}
            elif timeframe != "1m" or symbol in {"EMPTYUSDT", "LEGACYUSDT"}:
                value = []
            else:
                value = [{
                    "o": PRICE, "h": PRICE, "l": PRICE, "c": PRICE,
                    "buy": None, "poc": None,
                    "quality_status": "INCOMPLETE", "quality_reasons": ["missing_trade_data"],
                }, {"o": None, "h": None, "l": "3", "c": None}]
        elif url.path == "/api/grid/footprint":
            row = {"price": last_price, "buy": VOLUME, "sell": None, "delta": None}
            value = {
                "version": 2, "symbol": symbol, "timeframe": "1m", "rows": [row],
                "coverage": {"status": "PARTIAL", "reason": "fixture_gap"},
            }
            if symbol == "EMPTYUSDT":
                value["rows"] = []
            elif symbol == "LEGACYUSDT":
                value = [row]
            elif symbol == "FAILUSDT":
                status, value = 503, {"error": "fixture unavailable"}
        else:
            status, value = 404, {}
        self.reply(status, "application/json", json.dumps(value).encode())

    def reply(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except ConnectionError:
            pass

    def log_message(self, *_args):
        pass


def run():
    with ThreadingHTTPServer(("127.0.0.1", 0), Fixtures) as server, sync_playwright() as pw:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        edge = Path(os.environ.get("ProgramFiles(x86)", "")) / (
            "Microsoft/Edge/Application/msedge.exe"
        )
        executable = os.environ.get("BROWSER_EXECUTABLE") or (str(edge) if edge.is_file() else None)
        with pw.chromium.launch(executable_path=executable, headless=True) as browser:
            page = browser.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.add_init_script("""
                window.canvasLabels = [];
                const original = CanvasRenderingContext2D.prototype.fillText;
                CanvasRenderingContext2D.prototype.fillText = function (label, ...args) {
                    window.canvasLabels.push(label);
                    return original.call(this, label, ...args);
                };
            """)
            page_errors = []
            try:
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                assert STALE_REQUEST.wait(5), "old BTC candle request did not reach the fixture"
                page.get_by_role("button", name="ETHUSDT", exact=True).click()
                expect(page.locator("#research")).to_contain_text("ETHUSDT")
                RELEASE_STALE.set()
                page.wait_for_load_state("networkidle")
                expect(page.locator("#selected")).to_contain_text("ETHUSDT")
                expect(page.locator("#chartmsg")).to_contain_text("1 свечей")
                expect(page.locator("#chartmsg")).to_contain_text("INCOMPLETE")
                expect(page.locator("#footprint")).to_contain_text(f"{PRICE} | Buy {VOLUME} | Sell — | Δ —")
                expect(page.locator("#footprint")).to_contain_text("PARTIAL")
                expect(page.locator("#footprint")).to_contain_text("fixture_gap")
                assert f"1d high {PRICE}" in page.evaluate("window.canvasLabels")
                expect(page.locator("#levels")).to_contain_text(PRICE)
                expect(page.locator("#candle-values")).to_contain_text(PRICE)
                expect(page.locator("#candle-values")).to_contain_text("POC —")
                assert not any(path == "/api/grid/candles" for path, _, _ in REQUESTS)

                REQUESTS.clear()
                page.locator("#tf").select_option("3m")
                assert STALE_TIMEFRAME_REQUEST.wait(5), "old 3m request did not reach the fixture"
                page.locator("#tf").select_option("5m")
                expect(page.locator("#chartmsg")).to_contain_text("Нет свечей")
                assert ("/api/candles", "ETHUSDT", "5m") in REQUESTS
                assert not any(path == "/api/grid/candles" for path, _, _ in REQUESTS)
                RELEASE_STALE_TIMEFRAME.set()
                page.wait_for_load_state("networkidle")
                expect(page.locator("#chartmsg")).to_contain_text("Нет свечей")
                expect(page.locator("#footprint")).to_contain_text("1m")

                page.locator("#tf").select_option("1m")
                page.get_by_role("button", name="EMPTYUSDT", exact=True).click()
                expect(page.locator("#footprint")).to_contain_text("Нет доступных footprint")
                expect(page.locator("#footprint")).to_contain_text("PARTIAL")
                expect(page.locator("#chartmsg")).to_contain_text("Нет свечей")

                page.get_by_role("button", name="FAILUSDT", exact=True).click()
                expect(page.locator("#chartmsg")).to_contain_text("Свечи недоступны")
                expect(page.locator("#footprint")).to_contain_text("Grid недоступен")
                expect(page.locator("#error")).to_contain_text("fixture unavailable")

                page.get_by_role("button", name="LEGACYUSDT", exact=True).click()
                expect(page.locator("#footprint")).to_contain_text(VOLUME)
                assert not page_errors, page_errors
            finally:
                RELEASE_STALE.set()
                RELEASE_STALE_TIMEFRAME.set()
                server.shutdown()
    print("PASS: Chromium stale refresh, precise labels, nullable rows, coverage, empty and unavailable feeds")


if __name__ == "__main__":
    run()
