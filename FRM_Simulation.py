from flask import Flask, render_template, request, jsonify, session
import csv
import random
import pandas as pd
import os
from datetime import datetime
import time

app = Flask(__name__)
app.secret_key = "cfa-mbs-quiz-2026"

# Load questions (NO CHANGES to your CSV)
questions = []
with open("mbs_questions.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    questions = list(reader)

# Score history file
HISTORY_FILE = "quiz_history.csv"

def init_history():
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=['date', 'score', 'total', 'pct']).to_csv(HISTORY_FILE, index=False)

init_history()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    session['start_time'] = time.time()
    session['time_left'] = 90 * 60  # 90 minutes in seconds
    session['questions'] = random.sample(questions, len(questions))  # Random order
    session['current_q'] = 0
    session['user_answers'] = {}
    session['score'] = 0
    return render_template("quiz.html", questions=session['questions'], current_q=0)

@app.route("/quiz_data")
def quiz_data():
    if 'start_time' not in session:
        print("quiz_data: no start_time in session")
        return jsonify({'error': 'Quiz not started'})

    q_idx = session['current_q']
    print("quiz_data: current_q =", q_idx)

    if q_idx >= len(session['questions']):
        print("quiz_data: finished, len =", len(session['questions']))
        return jsonify({'finished': True})

    q = session['questions'][q_idx]
    time_elapsed = time.time() - session['start_time']
    time_left = max(0, session['time_left'] - time_elapsed)

    return jsonify({
        'question': q,
        'current': q_idx + 1,
        'total': len(session['questions']),
        'time_left': int(time_left),
        'user_answer': session['user_answers'].get(q_idx)
    })

@app.route("/submit_answer", methods=['POST'])
def submit_answer():
    data = request.json
    print("submit_answer: got", data)
    q_idx = data['q_idx']
    answer = data['answer']

    session['user_answers'][q_idx] = answer
    q = session['questions'][q_idx]

    if answer.upper() == q['correct'].upper():
        session['score'] += 1

    session['current_q'] = min(session['current_q'] + 1, len(session['questions']))
    print("submit_answer: new current_q =", session['current_q'])
    return jsonify({'success': True})


@app.route("/finish")
def finish():
    if 'start_time' not in session:
        return "Quiz not started"
    
    score = session['score']
    total = len(session['questions'])
    pct = (score / total) * 100
    
    # Save to history
    history = pd.DataFrame({
        'date': [datetime.now().strftime('%Y-%m-%d %H:%M')],
        'score': [score],
        'total': [total],
        'pct': [f"{pct:.1f}%"]
    })
    history.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
    
    # Detailed report
    report = []
    for i, q in enumerate(session['questions']):
        user_ans = session['user_answers'].get(i, 'Not answered')
        correct = q['correct']
        result = '✅' if user_ans.upper() == correct.upper() else '❌'
        report.append({
            'q_num': i+1,
            'question': q['question'][:100] + '...',
            'your_ans': user_ans,
            'correct': correct,
            'result': result
        })
    
    session.clear()
    return render_template("report.html", score=score, total=total, pct=pct, report=report)

@app.route("/history")
def history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        return render_template("history.html", history=df.to_dict('records'))
    return render_template("history.html", history=[])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
