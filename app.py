from flask import Flask, request, render_template, jsonify
import openai
import os
import sqlite3
from quetion import dict_bot  # 追加

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

@app.before_first_request
def setup():
    init_db()

@app.route('/')
def home():
    return render_template('Main.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question')

    # まずローカルQ&Aで回答を試みる
    answer = dict_bot(question)
    if answer == "すみません、その質問にはまだ対応していません。":
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは親切なQAアシスタントです。"},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            answer = response['choices'][0]['message']['content'].strip()
        except Exception as e:
            answer = f"エラーが発生しました: {str(e)}"

    # DBに保存
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO history (question, answer) VALUES (?, ?)', (question, answer))
    conn.commit()
    conn.close()
    return jsonify({'answer': answer})

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT question, answer FROM history ORDER BY id DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    # [{q:..., a:...}, ...] の形で返す
    history = [{'q': row[0], 'a': row[1]} for row in rows]
    return jsonify({'history': history})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)