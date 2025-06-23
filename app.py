from flask import Flask, request, render_template, jsonify
import openai
import os
import sqlite3
from question import dict_bot

app = Flask(__name__, static_folder='static', template_folder='templates')

# Render.comでは環境変数で管理
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        if answer == "すみません、その質問にはまだ対応していません。":
            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたは親切なQAアシスタントです。"},
                        {"role": "user", "content": question}
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                    api_key=openai.api_key  # 追加
                )
                answer = response.choices[0].message.content.strip()
            except Exception as e:
                answer = f"エラーが発生しました: {str(e)}"

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