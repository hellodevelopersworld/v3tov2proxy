"""
API v3 to v2 Proxy Tool
Copyright (c) 2026 hellodevelopersworld
Released under the MIT license
https://opensource.org/license/mit
"""

import httpx
from fastapi import FastAPI, Request, Response
from typing import Any, Dict
import json
import pathlib
import dataclasses
import argparse

# pyinstaller --onefile v3tov2proxy.py

"""
v2の場合
v2 → timetable.xml
start_time → Id, Start
end_time → End
title → Title
content → info

v3 → v2
publication
    name → title
    description → content
    startDate → start_time
    endDate → end_time
"""

@dataclasses.dataclass
class V3Publication:
    name: str
    description: str
    startDate: str
    endDate: str
    def to_v2_dict(self):
        return { 'start_time': self.startDate, 'end_time': self.endDate, 'title': self.name, 'content': self.description }

"""
timetable.xml
ex.
  <RadioProgram>
    <Id>R1_tokyo_20260205050003</Id>
    <StationId>R1_tokyo</StationId>
    <Start>2026-02-05T05:00:03</Start>
    <End>2026-02-05T05:50:00</End>
    <Title>マイあさ！ 木曜5時台 ニュース・気象情報／たより（和歌山・山梨）／健康ライフ</Title>
    <Actor />
    <Info>「マイあさ！」木曜5時台 ▼キャスター 上野速人・福島佑理 ▼気象情報 佐藤万里奈 ▽ニュース・気象情報 ▽たより「一目30万本 紀州石上田辺梅林」大﨑健志（和歌山） ▽きょうは何の日 ▽アンコール健康ライフ「動脈硬化を招く 脂質異常症に注意（4）家族性高コレステロール血症を放置しない」 小倉正恒（順天堂大学医療科学部臨床検査学科 教授） ▽たより「伝統の臼づくりを担う若手職人」窪田真弓（山梨）</Info>
  </RadioProgram>

<Id> nhk.xmlのIdとstart_timeから作られる
<StationId> nhk.xmlのId
<Start>
<End>
<Title>
<Actor>
<Info>

"""
app = FastAPI()

# デバッグ用
V2_URL = "https://api.nhk.or.jp/v2"
# 実際のAPIサーバのベースURL (v3)
V3_URL = "https://program-api.nhk.jp/v3"

# デバッグ用
def get_service_v2(path_name: str) -> str:
    if 'r1' in path_name:
        return 'r1'
    elif 'r2' in path_name:
        return 'r2'
    elif 'r3' in path_name:
        return 'r3'
    return ''

# デバッグ用
def get_version(path_name: str) -> str:
    if path_name.startswith('pg'):
        return 'v2'
    elif path_name.startswith('papiPgDateRadio'):
        return 'v3'
    return 'unknown'

# デバッグ用
def get_date_v2(path_name: str) -> str:
    p = pathlib.Path(path_name)
    return p.stem

def transform_v3_to_v2(v3_data: Dict[str, Any], service: str) -> Dict[str, Any]:
    """
    ここでJSONの形式を v3 から v2 へ変換します。
    """
    if len(v3_data.keys()) != 1: # r1, r2, r3のどれか1つを期待
        raise KeyError("unexpected v3 response 1")
    if list(v3_data.keys())[0] != service: # ex. r1
        raise KeyError("unexpected v3 response 2")
    v3_publications = list()
    for publication in v3_data[service]["publication"]:
        v3_publications.append(V3Publication(publication['name'], publication['description'], publication['startDate'], publication['endDate']))
    v2_data = {
        "list": { service: [x.to_v2_dict() for x in v3_publications] }
    }
    return v2_data

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path_name: str):
    is_debug = request.app.state.debug
    #print(path_name) # ex. v2 pg/list/130/r1/2026-02-04.json
    if is_debug:
        print(request.query_params)
    # 1. クライアントからのリクエストをキャッチ
    url = f"{V3_URL}/{path_name}"
    method = request.method
    headers = dict(request.headers)
    # ホストヘッダーは転送先のものに書き換える必要がある場合が多い
    headers.pop("host", None)
    content = await request.body()

    # クエリパラメータを辞書として取得
    params = dict(request.query_params)

    # 何故かradikoolからYYYYMMDDの形式で来るので、YYYY-MM-DDの形式に変換
    # date パラメータが存在し、かつ YYYYMMDD (8桁) かチェックして変換
    target_date = params.get("date")
    if target_date and len(target_date) == 8 and target_date.isdigit():
        # スライスを使って YYYYMMDD -> YYYY-MM-DD に整形
        formatted_date = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
        params["date"] = formatted_date
        #print(f"Date converted: {target_date} -> {formatted_date}")

    async with httpx.AsyncClient() as client:
        # 2. v3サーバへリクエストを転送
        target_response = await client.request(
            method,
            url,
            headers=headers,
            content=content,
            params=params,
        )

        # 3. レスポンスがJSONの場合のみ変換処理を行う
        if "application/json" in target_response.headers.get("content-type", ""):
            try:
                response_json = target_response.json()
                # データの変換を実行
                v2_json = transform_v3_to_v2(response_json, params.get('service'))
                if is_debug:
                    version = get_version(path_name)
                    if version == 'v2' or version == 'v3':
                        service = ''
                        date = ''
                        if version == 'v2':
                            service = get_service_v2(path_name)
                            date = get_date_v2(path_name)
                        else: # v3
                            params = request.query_params
                            service = params.get('service')
                            date = params.get("date")
                        filename = f"response-{version}-{service}-{date}-dump.json"
                        # そのまま保存
                        with open(filename, "wb") as f:
                            f.write(target_response.content)
                        filename = f"response-{version}-{service}-{date}-readable.json"
                        # 読めるようにして保存
                        readable_json_str = json.dumps(response_json, indent=4, ensure_ascii=False)
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write(readable_json_str)
                        if version == 'v3':
                            filename = f"response-v2-{service}-{date}-converted.json"
                            with open(filename, "w", encoding='utf-8') as f:
                                json.dump(v2_json, f, indent=4)
                
                return Response(
                    content=json.dumps(v2_json), # 
                    status_code=target_response.status_code,
                    headers={"Content-Type": "application/json"}
                )
            except Exception as e:
                print(f"JSON transformation failed: {e}")
                # 変換失敗時はそのまま返すか、エラーを返す
        
        # JSON以外（または変換不要）の場合はそのまま返す
        return Response(
            content=target_response.content,
            status_code=target_response.status_code,
            headers=dict(target_response.headers)
        )

if __name__ == "__main__":
    """ デバッグ用
    v3_filename = 'response-v3-r1-2026-02-05-dump.json'
    with open(v3_filename, encoding='utf-8') as f:
        d = json.load(f)
        v2_json = transform_v3_to_v2(d)
        v2_filename = v3_filename.replace('v3', 'v2')
        v2_filename = v2_filename.replace('dump', 'converted')
        with open(v2_filename, "w", encoding='utf-8') as f:
            json.dump(v2_json, f, indent=4)
    """
    # 1. argparseの設定
    parser = argparse.ArgumentParser(description="API変換プロキシ")
    
    # --debug オプション (指定すると True になる)
    parser.add_argument("--debug", action="store_true", help="デバッグモードで実行する")
    
    # --port オプション (デフォルトは 8080)
    parser.add_argument("--port", type=int, default=8080, help="待ち受けポート番号")
    
    args = parser.parse_args()

    # 2. 引数の値を FastAPI の state に保持（リクエストハンドラ内で参照するため）
    app.state.debug = args.debug

    print(f"Starting proxy on port {args.port} (Debug: {args.debug})")

    # 3. 指定されたポートで起動
    import uvicorn
    # 指定したポートで起動。元のプログラムの接続先をここに向ける。
    uvicorn.run(app, host="0.0.0.0", port=args.port)