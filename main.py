from flask import Flask, request, render_template, jsonify
import os
from quetion import dict_bot

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)

@app.route('/')
def home():
    return render_template('Main.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    answer = dict_bot(question)
    return jsonify({'answer': answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

