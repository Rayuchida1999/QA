from qa_db import qa_db


def dict_bot(question):
    q = question.strip()
    # 完全一致
    if q in qa_db:
        if q == "ipad右上に通信不可":
            return {
                "text": qa_db[q],
                "image": "photo/1.jpg"
            }
        return qa_db[q]
    # 部分一致候補をリストアップ
    candidates = [key for key in qa_db if key in q or q in key]
    if candidates:
        # ボタン候補をJSON風文字列で返す
        return {"__suggest__": candidates}
    return "すみません、その質問にはまだ対応していません。"
