import sqlite3

import pathlib

# 1. このPythonファイル (.py) 自身の場所（ディレクトリ）を取得
base_dir = pathlib.Path(__file__).parent

db_path = base_dir / 'collector.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. 実行したいSQL文を書く（テーブル名は実際の名称に変更してください）
sql = "SELECT url, title FROM articles"  # 例: articlesテーブルからurlのデータを取得するSQL文

# 3. SQLを実行してデータを取得する
cursor.execute(sql)
rows = cursor.fetchall() #データをリストとして取得

# 4. 取得したデータを表示する
for row in rows:
    print(row)

# 5. データベースとの接続を閉じる
conn.close()