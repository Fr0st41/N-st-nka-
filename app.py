import os
import random
import base64
import uuid
import re
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import httpx
from pymongo import MongoClient

app = Flask(__name__)
# Generuje zcela náhodný klíč pokaždé, když se aplikace zapne (není potřeba .env)
app.secret_key = os.urandom(24)

# --- KONFIGURACE AI ---
# Tyhle proměnné si školní server dodá automaticky sám!
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")
MODEL_NAME = "gemma3:27b"

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    http_client=httpx.Client(verify=False)
)

# --- PŘIPOJENÍ K DATABÁZI ---
mongo_uri = os.environ.get("MONGO_URI", "mongodb://db:27017/")
mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = mongo_client.nastenka_databaze
kolekce_vzkazu = db.vzkazy
kolekce_uzivatelu = db.uzivatele

NOTE_COLORS = ["#fffacd", "#e0ffff", "#e6e6fa", "#ffdab9", "#d8f8d8", "#ffe4e1"]

# --- FUNKCE AI S PAMĚTÍ (RAG) ---
def ask_ai(prompt):
    try:
        nedavne_vzkazy = list(kolekce_vzkazu.find().sort("cas_vytvoreni", -1).limit(20))
        kontext = "Historie nástěnky:\n"
        for m in nedavne_vzkazy:
            kontext += f"- {m.get('author', 'Někdo')}: {m.get('text', '')}\n"

        systemovy_pokyn = "Jsi vtipný asistent na třídní nástěnce. Odpovídej stručně.\n" + kontext

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": systemovy_pokyn},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Promiň, spím nebo mám poruchu. (Chyba API: {str(e)})"

# --- VZHLED (HTML & CSS) ---
HTML_MAIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="utf-8">
    <title>Digitální Nástěnka 📌</title>
    <style>
        body { font-family: 'Comic Sans MS', cursive, sans-serif; margin: 0; padding: 20px; min-height: 100vh; background-color: #c19a6b; background-image: url('https://www.transparenttextures.com/patterns/cork-board.png'); }
        h1 { text-align: center; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); }
        .controls { text-align: center; margin-bottom: 20px; }
        .main-form { background: rgba(255,255,255,0.95); padding: 15px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .main-form input[type="text"], .main-form input[type="password"] { padding: 8px; border: 1px solid #ccc; border-radius: 5px; margin: 3px; }
        .main-form button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .ai-btn { display: inline-block; margin-left: 15px; padding: 10px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        
        .filters { text-align: center; margin-bottom: 20px; }
        .tag-btn { display: inline-block; background: #fff; padding: 5px 10px; border-radius: 15px; margin: 3px; text-decoration: none; color: #333; font-size: 0.9em; box-shadow: 1px 1px 3px rgba(0,0,0,0.2); }
        .tag-btn:hover { background: #eee; }
        
        .board { display: flex; flex-wrap: wrap; gap: 30px; justify-content: center; padding: 10px; }
        
        .sticky-note { width: 280px; min-height: 250px; padding: 25px 20px 10px 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.4); position: relative; display: flex; flex-direction: column; transition: transform 0.2s; }
        .sticky-note.pinned { border: 3px solid #d9534f; box-shadow: 0 0 20px rgba(217,83,79,0.5); transform: rotate(0deg) !important; }
        .sticky-note:nth-child(even):not(.pinned) { transform: rotate(2deg); }
        .sticky-note:nth-child(odd):not(.pinned) { transform: rotate(-2deg); }
        .sticky-note:hover { transform: rotate(0deg) scale(1.05); z-index: 10; }
        .sticky-note::before { content: ""; position: absolute; top: 10px; left: 50%; transform: translateX(-50%); width: 15px; height: 15px; background-color: #d9534f; border-radius: 50%; box-shadow: 1px 1px 3px rgba(0,0,0,0.5); }
        
        .meta { font-size: 0.8em; color: #555; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; }
        .note-text { font-size: 1.1em; flex-grow: 1; word-wrap: break-word; font-weight: bold; color: #222; margin-bottom: 10px; }
        .note-image { width: 100%; max-height: 180px; object-fit: cover; border-radius: 5px; margin-bottom: 10px; }
        
        .replies { margin-bottom: 15px; font-size: 0.9em; color: #333; }
        .reply-item { border-left: 2px solid rgba(0,0,0,0.3); padding-left: 8px; margin-bottom: 8px; background: rgba(255,255,255,0.3); border-radius: 0 5px 5px 0; padding: 5px; }
        
        .actions { display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed rgba(0,0,0,0.3); padding-top: 10px; font-size: 0.9em; }
        .action-btn { background: none; border: none; cursor: pointer; font-size: 1.1em; }
        
        .auth-bar { background: rgba(0,0,0,0.8); color: white; padding: 10px; text-align: center; margin: -20px -20px 20px -20px; font-family: sans-serif; }
        .auth-bar a { color: #4CAF50; font-weight: bold; text-decoration: none; margin-left: 15px; }
        .error-msg { color: #ffeb3b; font-weight: bold; margin-bottom: 10px; background: rgba(0,0,0,0.5); padding: 5px; display: inline-block; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="auth-bar">
        {% if session.username %}
            👤 Přihlášen jako: <b>{{ session.username }}</b> 
            {% if session.role == 'admin' %} <span style="color: gold;">(Admin)</span> {% endif %}
            <a href="/logout">🚪 Odhlásit se</a>
        {% else %}
            Nejsi přihlášen. Můžeš číst, ale pro psaní vzkazů se musíš přihlásit/zaregistrovat.
        {% endif %}
    </div>

    <h1>Třídní Nástěnka 📌</h1>
    
    <div class="controls">
        {% if error %} <div class="error-msg">⚠️ {{ error }}</div> {% endif %}
        
        {% if session.username %}
            <form method="POST" action="/add" class="main-form" enctype="multipart/form-data">
                <div>
                    <span style="font-weight: bold; margin-right: 10px;">{{ session.username }}</span>
                    <input type="text" name="msg" placeholder="Napiš vzkaz... (@AI) (#tag)" required style="width: 250px;">
                    <input type="file" name="image" accept="image/*">
                </div>
                <div style="margin-top: 10px;">
                    {% if session.role == 'admin' %}
                        <label><input type="checkbox" name="is_important"> 📌 Důležité připnutí</label>
                    {% endif %}
                    <button type="submit">Připíchnout</button>
                </div>
            </form>
            <a href="/ai" class="ai-btn">🤖 AI Poradna</a>
        {% else %}
            <div class="main-form">
                <h3>Přihlášení / Registrace</h3>
                <form method="POST" action="/auth" style="display:inline-block; margin-right: 20px;">
                    <input type="text" name="username" placeholder="Jméno" required style="width: 100px;">
                    <input type="password" name="password" placeholder="Heslo" required style="width: 100px;">
                    <button type="submit" name="action" value="login" style="background: #007BFF;">Přihlásit</button>
                    <button type="submit" name="action" value="register">Zaregistrovat</button>
                </form>
                <a href="/ai" class="ai-btn">🤖 AI Poradna</a>
            </div>
        {% endif %}
    </div>

    <div class="filters">
        <a href="/" class="tag-btn">Všechny vzkazy</a>
        {% for tag in all_tags %}
            <a href="/?tag={{ tag }}" class="tag-btn">#{{ tag }}</a>
        {% endfor %}
    </div>

    <div class="board">
        {% for msg in messages %}
            <div class="sticky-note {% if msg.is_pinned %}pinned{% endif %}" style="background-color: {{ msg.color }};">
                <div class="meta">
                    <span>👤 <b>{{ msg.author }}</b> | 🕒 {{ msg.timestamp }}</span>
                    {% if msg.is_pinned %} <span title="Důležité">📌</span> {% endif %}
                </div>
                
                {% if msg.image %} <img src="{{ msg.image }}" class="note-image"> {% endif %}
                <div class="note-text">{{ msg.text }}</div>
                
                <div class="replies">
                    {% for r in msg.replies %}
                        <div class="reply-item">
                            <div style="font-size: 0.75em; color: #666;">👤 <b>{{ r.author }}</b></div>
                            <div>{{ r.text }}</div>
                        </div>
                    {% endfor %}
                </div>
                
                <div class="actions">
                    <form method="POST" action="/like" style="margin:0;">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" class="action-btn">❤️ {{ msg.likes }}</button>
                    </form>
                    
                    {% if session.username == msg.author or session.role == 'admin' %}
                    <form method="POST" action="/delete" style="margin:0;">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" class="action-btn" title="Smazat vzkaz">🗑️</button>
                    </form>
                    {% endif %}
                </div>

                {% if session.username %}
                <form method="POST" action="/reply" style="display:flex; gap:5px; margin-top:10px;">
                    <input type="hidden" name="note_id" value="{{ msg.id }}">
                    <input type="text" name="reply_text" placeholder="Odpověz jako {{ session.username }}..." required style="flex-grow:1; padding:3px; border:1px solid #ccc; border-radius:3px;">
                    <button type="submit" style="background:#333; color:white; border:none; border-radius:3px; cursor:pointer;">↪</button>
                </form>
                {% endif %}
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

HTML_AI = """<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><title>AI Poradna</title><style>body { font-family: sans-serif; margin: 40px; background: #eef2f5; } .container { max-width: 600px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); } input { padding: 10px; width: 70%; border: 1px solid #ccc; border-radius: 5px; } button { padding: 10px 20px; background: #007BFF; color: white; border: none; border-radius: 5px; cursor: pointer; } .result { background: #f8f9fa; padding: 15px; border-left: 5px solid #007BFF; margin-top: 20px; } .error { background: #ffe6e6; padding: 15px; border-left: 5px solid #d9534f; margin-top: 20px; color: #a94442; }</style></head><body><div class="container"><h1 style="color: #007BFF; margin-top: 0;">Online AI Poradna 🤖</h1><form method="POST" action="/ai"><input type="text" name="query" placeholder="Zeptej se umělé inteligence..." required> <button type="submit">Odeslat</button></form><br><a href="/" style="font-weight: bold; color: #333; text-decoration: none;">⬅️ Zpět na Nástěnku</a>{% if answer %}<div class="result"><p><strong>Dotaz:</strong> {{ question }}</p><p><strong>AI:</strong> {{ answer }}</p></div>{% elif error %}<div class="error"><p><strong>Chyba:</strong> {{ error }}</p></div>{% endif %}</div></body></html>"""

# --- ROUTOVÁNÍ ---

@app.route('/', methods=['GET'])
def home():
    error = request.args.get('error')
    vsechny_tagy = kolekce_vzkazu.distinct("tags")
    vybrany_tag = request.args.get('tag')
    dotaz = {"tags": vybrany_tag} if vybrany_tag else {}

    try:
        vzkazy_z_db = list(kolekce_vzkazu.find(dotaz).sort([("is_pinned", -1), ("cas_vytvoreni", -1)]))
    except Exception as e:
        vzkazy_z_db = []
        
    return render_template_string(HTML_MAIN, messages=vzkazy_z_db, all_tags=vsechny_tagy, error=error)

@app.route('/auth', methods=['POST'])
def auth():
    akce = request.form.get('action')
    username = request.form.get('username').strip()
    password = request.form.get('password')

    if not username or not password:
        return redirect('/?error=Vyplň jméno i heslo!')

    if akce == 'register':
        if kolekce_uzivatelu.find_one({"username": username}):
            return redirect('/?error=Toto jméno už je zabrané!')

        # FÍGL ZDE: Pokud se jmenuješ 'admin' a ještě v databázi žádný admin není, dostaneš roli admina!
        if username.lower() == 'admin' and not kolekce_uzivatelu.find_one({"role": "admin"}):
            role = 'admin'
        else:
            role = 'user'

        kolekce_uzivatelu.insert_one({
            "username": username,
            "password": generate_password_hash(password),
            "role": role
        })
        session['username'] = username
        session['role'] = role

    elif akce == 'login':
        user = kolekce_uzivatelu.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
        else:
            return redirect('/?error=Špatné jméno nebo heslo!')

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add', methods=['POST'])
def add_note():
    if 'username' not in session:
        return redirect('/?error=Musíš být přihlášený!')

    author = session['username']
    text = request.form.get('msg')
    is_important = request.form.get('is_important') == 'on'
    
    nalezeno_tagu = re.findall(r"#(\w+)", text)
    is_pinned = True if is_important and session.get('role') == 'admin' else False

    file = request.files.get('image')
    img_b64 = None
    if file and file.filename:
        img_b64 = "data:" + file.content_type + ";base64," + base64.b64encode(file.read()).decode('utf-8')
    
    if text:
        note_id = uuid.uuid4().hex[:8]
        new_note = {
            "id": note_id,
            "author": author,
            "text": text,
            "color": random.choice(NOTE_COLORS),
            "timestamp": datetime.now().strftime("%H:%M"),
            "cas_vytvoreni": datetime.now(),
            "image": img_b64,
            "replies": [],
            "likes": 0,
            "tags": nalezeno_tagu,
            "is_pinned": is_pinned
        }

        kolekce_vzkazu.insert_one(new_note)

        if "@AI" in text.upper():
            prompt = text.replace("@AI", "").replace("@ai", "").strip()
            ai_reply = ask_ai(prompt if prompt else "Ahoj.")
            kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {
                "author": "🤖 AI Asistent",
                "text": ai_reply,
                "timestamp": datetime.now().strftime("%H:%M")
            }}})
            
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_note():
    if 'username' not in session:
        return redirect('/')

    note_id = request.form.get('note_id')
    if note_id:
        vzkaz = kolekce_vzkazu.find_one({"id": note_id})
        if vzkaz and (vzkaz['author'] == session['username'] or session.get('role') == 'admin'):
            kolekce_vzkazu.delete_one({"id": note_id})
            
    return redirect(request.referrer or '/')

@app.route('/like', methods=['POST'])
def like_note():
    note_id = request.form.get('note_id')
    if note_id:
        kolekce_vzkazu.update_one({"id": note_id}, {"$inc": {"likes": 1}})
    return redirect(request.referrer or '/')

@app.route('/reply', methods=['POST'])
def add_reply():
    if 'username' not in session:
        return redirect('/?error=Musíš se přihlásit!')

    note_id = request.form.get('note_id')
    author = session['username']
    reply_text = request.form.get('reply_text')
    
    if reply_text and note_id:
        nova_odpoved = {"author": author, "text": reply_text, "timestamp": datetime.now().strftime("%H:%M")}
        kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": nova_odpoved}})
                
        if "@AI" in reply_text.upper():
            prompt = reply_text.replace("@AI", "").replace("@ai", "").strip()
            ai_reply = ask_ai(prompt if prompt else "Ahoj.")
            ai_odpoved = {"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")}
            kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": ai_odpoved}})
                
    return redirect('/')

@app.route('/ai', methods=['GET', 'POST'])
def ai_page():
    answer, question, error = None, None, None
    if request.method == 'POST':
        question = request.form.get('query')
        answer = ask_ai(question)
        if answer.startswith("Promiň"):
            error = answer
            answer = None
    return render_template_string(HTML_AI, question=question, answer=answer, error=error)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
