# v3tov2proxy

Radikoolのために、NHKのv3 APIで返されるJSONをV2形式に変換するプロキシアプリ(以下proxy)。

# 動作

proxyはWebサーバとして動作し、Radikoolのnhk.xmlに書いてあるNHK用の番組表取得URLをこれに向けることで、代わりにV3 APIで番組表を取得し、Radikoolが理解できるようにJSONを変換して返す。

# 使い方

Radikoolを動作させているPCでproxyを起動するか、常時起動しているようなPCがある場合はそれを使う。

## Radikool側の変更

files/nhk.xml内のTimeTableタグに記述してあるURLをプロキシのアドレスにする。
```xml:nhk.xml
  <RadioStation>
    <Id>R1_tokyo</Id>
    <Name>ラジオ第1(東京)</Name>
    ～略～
    <TimeTable>http://localhost:8080/papiPgDateRadio?service=r1&amp;area=130&amp;date=[YYYY-MM-DD]&amp;key=_ENTER_YOUR_KEY_</TimeTable>

```

プロトコルはHTTPにする。Radikoolと同じPCでproxyを動作させるなら、ホスト名はlocalhostにする。APIのパスに/v3は不要(proxy内に書いてあるため)。
_ENTER_YOUR_KEY_部分は自分のkeyに置き換えること。
他のRadioStationについても同じように変更する。

## proxy側

Python実行環境があれば
'python v3tov2proxy.py'で起動する。またはバイナリも作成してあるので、
v3tov2proxy.exeを起動する。defaultではポート番号8080で待ち受ける。--portオプションで変更することも可能。基本的に常時起動しておく。

# 開発環境

Anaconda + Python 3.13.11

