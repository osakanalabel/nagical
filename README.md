# ナギカル（nagical）

北海道の釣り場で、どの日にどこへ行くかを風で決めるためのスマホ向けウェブアプリです。

https://osakanalabel.github.io/nagical/

<img src="qr.svg" width="160" alt="ナギカルのQRコード">

ブラウザのメニューからホーム画面に追加できます。くわしくは「PWA」で検索してみてください。

使い方はアプリ内の「使い方」にあります。

## データと注意

- 予報：[Open-Meteo](https://open-meteo.com/)（[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)）
- 祝日：[holidays-jp](https://github.com/holidays-jp/api)
- 予報は目安です。出かける前と現地で必ず確かめてください。

## 開発メモ

- `index.html` 1ファイルで動きます。ビルドはありません。
- ローカルでの確認：`python -m http.server 8000` を起動して http://localhost:8000/ を開く。
- 公開：`sw.js` の `VERSION` を上げてから `main` にプッシュする（上げないと利用者の端末に古い版が残ります）。
- 詳しくは [CLAUDE.md](CLAUDE.md)。
