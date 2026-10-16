"""ナギカル：仮データでの表示確認スクリプト

Open-Meteo・祝日API・Google Fonts への通信を横取りし、仮の予報データを返して
スマホ幅（390px）で各画面を開く。スクリーンショットを shots/ に保存し、
JSエラー・横スクロールの有無・予報APIへの取得回数を表示する。

使い方:
  pip install playwright && python -m playwright install chromium
  python3 tools/mock_check.py            # 雨のある仮データ
  python3 tools/mock_check.py --snow     # 大雪の日を混ぜる
"""
import argparse
import datetime
import json
import math
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").as_uri()
SHOTS = ROOT / "shots"

ap = argparse.ArgumentParser()
ap.add_argument("--snow", action="store_true", help="大雪（weather_code 75）の日を混ぜる")
args = ap.parse_args()

JST = datetime.timezone(datetime.timedelta(hours=9))
start = datetime.datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1)
N = 12 * 24  # past_days=1 + forecast_days=11
T = [(start + datetime.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(N)]
DAYS = [(start + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(12)]


def forecast(seed):
    def code(i):
        if args.snow and (i // 24) % 5 == 2:
            return 75
        return [0, 1, 2, 3, 61, 80][i // 7 % 6]
    return {
        "hourly": {
            "time": T,
            "temperature_2m": [12 + 4 * math.sin(i / 24 * 6.28) for i in range(N)],
            "precipitation_probability": [(i * 13 + seed * 29) % 90 if (i // 24 + seed) % 3 == 0 else 10 for i in range(N)],
            "weather_code": [code(i) for i in range(N)],
            "wind_speed_10m": [max(0, 3.5 + seed + 2.5 * math.sin(i / 7 + seed)) for i in range(N)],
            "wind_direction_10m": [(i * 13 + seed * 90) % 360 for i in range(N)],
            "wind_gusts_10m": [6 + 3 * math.sin(i / 9) for i in range(N)],
        },
        "daily": {"time": DAYS, "sunrise": [d + "T06:02" for d in DAYS], "sunset": [d + "T16:51" for d in DAYS]},
    }


MARINE = {"hourly": {"time": T, "sea_surface_temperature": [15.3] * N,
                     "sea_level_height_msl": [0.2 * math.sin(i / 12.4 * 6.28) for i in range(N)]}}

count = {"forecast": 0}


def on_forecast(route):
    count["forecast"] += 1
    # 釣り場ごとに値を少し変える
    seed = (hash(route.request.url) % 3) - 1
    route.fulfill(body=json.dumps(forecast(seed)), content_type="application/json")


SHOTS.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    page.route("**/holidays-jp.github.io/**", lambda r: r.abort())
    page.route("**/api.open-meteo.com/**", on_forecast)
    page.route("**/marine-api.open-meteo.com/**",
               lambda r: r.fulfill(body=json.dumps(MARINE), content_type="application/json"))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(HTML)
    page.wait_for_timeout(800)
    page.screenshot(path=str(SHOTS / "1-list.png"), full_page=True)
    print("初回表示の取得回数:", count["forecast"])

    page.reload()
    page.wait_for_timeout(500)
    print("すぐリロードした後の取得回数（増えないこと）:", count["forecast"])

    page.click("button.cell[data-d] >> nth=0")
    page.wait_for_timeout(300)
    page.screenshot(path=str(SHOTS / "2-detail.png"), full_page=True)

    page.goto(HTML + "#/spots")
    page.wait_for_timeout(400)
    page.screenshot(path=str(SHOTS / "3-spots.png"), full_page=True)

    page.goto(HTML)
    page.wait_for_timeout(400)
    page.click("#help-btn")
    page.wait_for_timeout(300)
    page.screenshot(path=str(SHOTS / "4-help.png"))

    print("横幅（390なら横スクロールなし）:", page.evaluate("document.documentElement.scrollWidth"))
    print("JSエラー:", errors or "なし")
    print("スクリーンショット:", SHOTS)
    browser.close()
