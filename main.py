import os
from google.cloud import storage
from google.cloud import secretmanager
import requests
from flask import Request
from bs4 import BeautifulSoup
from datetime import datetime

project_id = "isdf-orix-info"
bucket_name = "orix-info-bucket"
line_token_secret_id = "line-token-secret"
orix_info_url = 'https://shop.buffaloes.co.jp/info/'
line_notify_url = "https://notify-api.line.me/api/notify"


def main(request: Request):
    # URLからHTMLを取得
    response = requests.get(orix_info_url)

    # BeautifulSoupを使って解析
    soup = BeautifulSoup(response.text, 'html.parser')

    # 新着情報のリストを取得
    news_list = soup.find_all('dt')

    # GCSクライアントを作成
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    # 今日の日付を取得
    today = datetime.now().strftime('%Y.%m.%d')

    for news in news_list:
        # 日付が今日のものだけチェック
        if news.text == today:
            next_tag = news.find_next_sibling('dd')
            message = f'{today}_{next_tag.text}'.replace('\n', '').rstrip()
            blob_name = f'{today}_{next_tag.a.text}'
            print(f'{message}')
            # GCSバケット内にそのIDのファイルが存在するかを確認
            blob = storage.Blob(blob_name, bucket)

            if not blob.exists():
                # lineに情報を送信 (上記のsend_to_slack関数を使用)
                line_notify(message)
                # GCSバケット内に空のファイルを作成して、そのIDのニュースが送信されたことをマーク
                blob.upload_from_string('')

    return 'OK'


def line_notify(message):
    line_token = get_secret(line_token_secret_id)
    headers = {"Authorization": f"Bearer {line_token}"}
    data = {"message": message}
    requests.post(line_notify_url, headers=headers, data=data)


def get_secret(secret_id, version_id="1"):
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(project_id, secret_id, version_id)
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')
