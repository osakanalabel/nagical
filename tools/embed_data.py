"""data/*.json の釣り場データを、index.html の DB と PREFDEF に埋め込む（ビルドなしの単一HTMLなので、データを直したら実行する）。

使い方: python tools/embed_data.py        （index.html を書き換える）
        python tools/embed_data.py --check （食い違いがあれば終了コード1。書き換えない）
"""
import glob, io, json, re, sys

ROOT = __file__.replace("\\", "/").rsplit("/tools/", 1)[0]
HTML = ROOT + "/index.html"


def compact(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def load():
    spots, prefs, ids = [], [], set()
    for path in sorted(glob.glob(ROOT + "/data/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        for s in d["spots"]:
            assert s["id"] not in ids, f"id が重複: {s['id']}"
            ids.add(s["id"])
            e = {"id": s["id"], "n": s["name"], "k": s["kind"], "type": s["type"], "pref": s["pref"],
                 "r": s["region"], "a": s.get("area") or s["region"], "m": s["municipality"],
                 "lat": s["lat"], "lon": s["lon"]}
            if s.get("status"):
                e["status"] = s["status"]
            if s.get("notes"):
                e["note"] = s["notes"]
            spots.append(e)
        prefs += d.get("prefs", [])
    for p in prefs:  # プリセットの id が実在するか
        for pr in p["presets"]:
            for i in pr["spots"]:
                assert i in ids, f"プリセット {pr['name']} の id が見つからない: {i}"
    return spots, prefs


def main():
    spots, prefs = load()
    h = io.open(HTML, encoding="utf-8", newline="").read()
    new, n = re.subn(
        r"(?<=\nconst DB=)\[.*?\];\n(// [^\n]*\nconst PREFDEF=)\[.*?\];\n",
        lambda m: compact(spots) + ";\n" + m.group(1) + compact(prefs) + ";\n", h, count=1, flags=re.S)
    assert n == 1, "index.html に DB / PREFDEF の行が見つからない"
    if "--check" in sys.argv:
        print("一致" if new == h else "食い違い（python tools/embed_data.py で埋め込み直す）")
        sys.exit(0 if new == h else 1)
    io.open(HTML, "w", encoding="utf-8", newline="").write(new)
    print(f"埋め込みました: 釣り場{len(spots)}か所、県{len(prefs)}")


main()
