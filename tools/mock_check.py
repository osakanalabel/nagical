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


# 海洋APIは past_days=7（水温の前後1週間）。予報は9日先までで、その先は null
start7 = start - datetime.timedelta(days=6)
N7 = 18 * 24
T7 = [(start7 + datetime.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(N7)]
D7 = [(start7 + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(18)]
MARINE = {"hourly": {"time": T7, "sea_surface_temperature": [15.3] * N7,
                     "sea_level_height_msl": [0.2 * math.sin(i / 12.4 * 6.28) for i in range(N7)]},
          "daily": {"time": D7, "sea_surface_temperature_mean": [round(17.5 - 0.2 * i, 1) if i < 16 else None for i in range(18)]}}

count = {"forecast": 0, "lastyear": 0}


def on_marine(route):
    url = route.request.url
    if "start_date=" in url:  # 前年の水温（日付を指定）
        count["lastyear"] += 1
        q = dict(x.split("=", 1) for x in url.split("?", 1)[1].split("&"))
        a = datetime.date.fromisoformat(q["start_date"])
        b = datetime.date.fromisoformat(q["end_date"])
        days = [(a + datetime.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
        body = {"daily": {"time": days, "sea_surface_temperature_mean": [round(18.6 - 0.18 * i, 1) for i in range(len(days))]}}
    else:
        body = MARINE
    route.fulfill(body=json.dumps(body), content_type="application/json")


def on_forecast(route):
    count["forecast"] += 1
    # 釣り場ごとに値を少し変える
    seed = (hash(route.request.url) % 3) - 1
    route.fulfill(body=json.dumps(forecast(seed)), content_type="application/json")


SHOTS.mkdir(exist_ok=True)
with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
    except Exception:
        browser = p.chromium.launch(channel="msedge")  # Playwright のブラウザを入れていないときは、端末の Edge を使う
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    page.route("**/holidays-jp.github.io/**", lambda r: r.abort())
    page.route("**/api.open-meteo.com/**", on_forecast)
    page.route("**/marine-api.open-meteo.com/**", on_marine)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(HTML)
    # 保存が空なので初回の画面（おすすめリスト）が出る。海釣りの先頭のリストを作る
    page.screenshot(path=str(SHOTS / "0-new.png"))
    page.click("#new-genre [data-t=sea]")
    page.click("#new-items .dbrow >> nth=0")
    page.wait_for_timeout(800)
    page.screenshot(path=str(SHOTS / "1-list.png"), full_page=True)
    print("初回表示の取得回数:", count["forecast"])

    page.reload()
    page.wait_for_timeout(500)
    print("すぐリロードした後の取得回数（増えないこと）:", count["forecast"])

    page.click("button.cell[data-d] >> nth=0")
    page.wait_for_timeout(300)
    page.screenshot(path=str(SHOTS / "2-detail.png"), full_page=True)
    print("詳細を開いた後の前年水温の取得回数（1）:", count["lastyear"])
    page.click("#next")
    page.wait_for_timeout(300)
    page.reload()
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "2b-detail-next.png"), full_page=True)
    print("次の日・リロード後の前年水温の取得回数（1のまま）:", count["lastyear"])

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
