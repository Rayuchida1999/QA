from flask import Flask, request, render_template, jsonify
import os
import sqlite3
import requests
from question import dict_bot

app = Flask(__name__, static_folder='static', template_folder='templates')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

DB_PATH = 'qa_history.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('Main.html')

@app.route('/ask', methods=['POST'])
def ask():
    init_db()  # 追加: テーブルがなければ作成
    try:
        data = request.get_json()
        question = data.get('question')

        # まずローカルQ&Aで回答を試みる
        answer = dict_bot(question)
        # 画像付き回答の場合
        if isinstance(answer, dict) and "text" in answer and "image" in answer:
            # DBに保存（テキストのみ）
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT INTO history (question, answer) VALUES (?, ?)', (question, answer["text"]))
            conn.commit()
            conn.close()
            return jsonify({'answer': answer["text"], 'image': answer["image"]})
        if answer == "すみません、その質問にはまだ対応していません。":
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                }
                payload = {
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "あなたは親切なQAアシスタントです。"},
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    groq_data = response.json()
                    answer = groq_data["choices"][0]["message"]["content"].strip()
                else:
                    answer = f"Groq APIエラー: {response.status_code} - {response.text}"
            except Exception as e:
                answer = f"Groq API通信エラー: {str(e)}"

        # DBに保存
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO history (question, answer) VALUES (?, ?)', (question, answer))
        conn.commit()
        conn.close()
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'answer': f"サーバー側でエラーが発生しました: {str(e)}"}), 500

@app.route('/history', methods=['GET'])
def get_history():
    init_db()  # 追加: テーブルがなければ作成
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT question, answer FROM history ORDER BY id DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    # [{q:..., a:...}, ...] の形で返す
    history = [{'q': row[0], 'a': row[1]} for row in rows]
    return jsonify({'history': history})

if __name__ == "__main__":
    # セキュリティ警告: この開発サーバは本番環境で使用しないでください。
    # 本番運用時はgunicornやuwsgiなどのWSGIサーバを利用してください。
    init_db()  # サーバ起動前にDB初期化
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)