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
app.secret_key = os.urandom(24)

# --- KONFIGURACE AI ---
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        body { font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 0 0 40px 0; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #2c3e50; }
        h1 { text-align: center; color: #1a252f; font-weight: 800; font-size: 2.5em; margin-top: 30px; letter-spacing: -1px;}
        
        .auth-bar { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); padding: 12px 20px; text-align: center; font-size: 0.9em; border-bottom: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .auth-bar a { color: #e74c3c; font-weight: 600; text-decoration: none; margin-left: 15px; padding: 4px 10px; border-radius: 20px; background: rgba(231, 76, 60, 0.1); transition: 0.2s;}
        .auth-bar a:hover { background: rgba(231, 76, 60, 0.2); }
        
        .controls { text-align: center; margin-bottom: 30px; padding: 0 15px; }
        .main-form { background: #ffffff; padding: 20px; border-radius: 16px; display: inline-block; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #edf2f7; max-width: 100%; box-sizing: border-box; }
        input[type="text"], input[type="password"] { padding: 10px 15px; border: 2px solid #e2e8f0; border-radius: 8px; margin: 5px; font-family: inherit; transition: 0.3s; outline: none; }
        input[type="text"]:focus, input[type="password"]:focus { border-color: #3498db; }
        button { padding: 10px 20px; background-color: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-family: inherit; transition: 0.2s; }
        button:hover { background-color: #2980b9; transform: translateY(-1px); }
        .ai-btn { display: inline-block; margin-left: 10px; padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3); }
        
        .filters { text-align: center; margin-bottom: 30px; }
        .tag-btn { display: inline-block; background: #fff; padding: 6px 14px; border-radius: 20px; margin: 4px; text-decoration: none; color: #34495e; font-size: 0.85em; font-weight: 600; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; border: 1px solid #e2e8f0; }
        .tag-btn:hover { background: #3498db; color: #fff; border-color: #3498db; }
        
        .board { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; padding: 10px 30px; max-width: 1400px; margin: 0 auto; }
        .note-card { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(15px); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,1); box-shadow: 0 10px 25px rgba(0,0,0,0.05); transition: transform 0.3s, box-shadow 0.3s; display: flex; flex-direction: column; }
        .note-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .note-card.pinned { border: 2px solid #e74c3c; background: #fffdfd; }
        
        /* STYL PRO DUEL KARTIČKU */
        .note-card.duel { border: 2px solid #f39c12; background: linear-gradient(135deg, #fff 0%, #fdfbf7 100%); }
        .duel-title { font-weight: 800; color: #e67e22; font-size: 1.2em; text-align: center; margin-bottom: 15px; }
        .duel-buttons { display: flex; justify-content: space-around; margin: 15px 0; }
        .duel-btn { font-size: 2em; background: none; border: 2px solid #e2e8f0; border-radius: 50%; width: 60px; height: 60px; cursor: pointer; transition: 0.2s; }
        .duel-btn:hover { background: #f39c12; border-color: #f39c12; transform: scale(1.1); }
        .duel-result { text-align: center; font-size: 1.2em; font-weight: 800; padding: 10px; border-radius: 10px; margin-top: 10px; }
        .duel-win { background: #d4edda; color: #155724; }
        .duel-lose { background: #f8d7da; color: #721c24; }
        .duel-tie { background: #fff3cd; color: #856404; }
        
        .meta { font-size: 0.85em; color: #7f8c8d; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;}
        .meta b { color: #2c3e50; font-weight: 600; }
        .note-text { font-size: 1.1em; line-height: 1.5; flex-grow: 1; word-wrap: break-word; color: #34495e; margin-bottom: 15px; }
        .note-image { width: 100%; max-height: 200px; object-fit: cover; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee;}
        
        .reactions-container { margin-bottom: 15px; }
        .badge { display: inline-block; background: #f1f2f6; padding: 4px 8px; border-radius: 12px; font-size: 0.85em; margin-right: 5px; margin-bottom: 5px; color: #2c3e50; border: 1px solid #e2e8f0; }
        .emoji-bar { display: flex; gap: 5px; background: #fff; padding: 5px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); width: fit-content; border: 1px solid #edf2f7;}
        .btn-react { background: none; border: none; cursor: pointer; font-size: 1.2em; padding: 2px 5px; border-radius: 50%; transition: 0.2s; }
        .btn-react:hover { background: #f1f2f6; transform: scale(1.2); }
        
        .replies { background: #f8fafc; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e2e8f0;}
        .reply-item { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #edf2f7; }
        .reply-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
        .reply-meta { font-size: 0.75em; color: #95a5a6; margin-bottom: 3px; font-weight: 600;}
        .reply-text { font-size: 0.95em; color: #475569; }
        
        .del-btn { background: rgba(231, 76, 60, 0.1); color: #e74c3c; border: none; padding: 5px 10px; border-radius: 8px; cursor: pointer; transition: 0.2s;}
        .del-btn:hover { background: #e74c3c; color: white;}
        .error-msg { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #f87171; display: inline-block;}
    </style>
    <script>
        function toggleDuel() {
            var duelOptions = document.getElementById('duel-options');
            var isDuel = document.getElementById('is-duel').checked;
            duelOptions.style.display = isDuel ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <div class="auth-bar">
        {% if session.username %}
            👤 Přihlášen jako: <b>{{ session.username }}</b> 
            {% if session.role == 'admin' %} <span style="color: #f39c12; font-weight: bold;">(Admin)</span> {% endif %}
            <a href="/logout">Odhlásit se</a>
        {% else %}
            Nejsi přihlášen. Můžeš číst, ale pro psaní vzkazů se musíš zaregistrovat.
        {% endif %}
    </div>

    <h1>Třídní Nástěnka ✨</h1>
    
    <div class="controls">
        {% if error %} <div class="error-msg">⚠️ {{ error }}</div> {% endif %}
        
        {% if session.username %}
            <form method="POST" action="/add" class="main-form" enctype="multipart/form-data">
                <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: center;">
                    <span style="font-weight: 600; color: #34495e;">{{ session.username }}</span>
                    <input type="text" name="msg" placeholder="Napiš vzkaz... (@AI) (#tag)" required style="width: 300px;">
                    <input type="file" name="image" accept="image/*" style="font-size: 0.8em; color: #7f8c8d;">
                </div>
                
                <div style="margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">
                    <label style="margin-right: 15px; font-weight: 600; cursor: pointer; color: #e67e22;">
                        <input type="checkbox" name="is_duel" id="is-duel" onchange="toggleDuel()"> ⚔️ Vytvořit 1v1 Duel
                    </label>
                    {% if session.role == 'admin' %}
                        <label style="margin-right: 15px; font-size: 0.9em; color: #e74c3c; font-weight: 600;">
                            <input type="checkbox" name="is_important"> 📌 Důležité
                        </label>
                    {% endif %}
                    
                    <div id="duel-options" style="display: none; margin-top: 10px; background: #fdfbf7; padding: 10px; border-radius: 8px; border: 1px solid #f39c12;">
                        Vyber svou tajnou zbraň:<br>
                        <label><input type="radio" name="duel_move" value="🪨" checked> 🪨 Kámen</label>
                        <label><input type="radio" name="duel_move" value="✂️"> ✂️ Nůžky</label>
                        <label><input type="radio" name="duel_move" value="📄"> 📄 Papír</label>
                    </div>

                    <div style="margin-top: 15px;">
                        <button type="submit">Vystavit vzkaz</button>
                        <a href="/ai" class="ai-btn">🤖 AI Poradna</a>
                    </div>
                </div>
            </form>
        {% else %}
            <div class="main-form">
                <h3 style="margin-top: 0; color: #2c3e50;">Přihlášení / Registrace</h3>
                <form method="POST" action="/auth" style="display:flex; gap: 10px; justify-content: center;">
                    <input type="text" name="username" placeholder="Jméno" required style="width: 120px;">
                    <input type="password" name="password" placeholder="Heslo" required style="width: 120px;">
                    <button type="submit" name="action" value="login">Přihlásit</button>
                    <button type="submit" name="action" value="register" style="background: #2ecc71;">Registrovat</button>
                </form>
            </div>
        {% endif %}
    </div>

    <div class="board" id="board-container">
        {% for msg in messages %}
            <div class="note-card {% if msg.is_pinned %}pinned{% endif %} {% if msg.type == 'duel' %}duel{% endif %}">
                
                <div class="meta">
                    <span>👤 <b>{{ msg.author }}</b> | 🕒 {{ msg.timestamp }}</span>
                    {% if msg.is_pinned %} <span title="Důležité" style="font-size: 1.2em;">📌</span> {% endif %}
                </div>
                
                {% if msg.type == 'duel' %}
                    <div class="duel-title">⚔️ VÝZVA NA SOUBOJ ⚔️</div>
                    <div class="note-text" style="text-align: center;">{{ msg.text }}</div>
                    
                    {% if msg.duel_state == 'waiting' %}
                        <div style="text-align: center; color: #7f8c8d; margin-bottom: 10px;">Čeká na odvážlivce...</div>
                        
                        {% if session.username and session.username != msg.author %}
                            <form method="POST" action="/play_duel" class="duel-buttons">
                                <input type="hidden" name="note_id" value="{{ msg.id }}">
                                <button type="submit" name="move" value="🪨" class="duel-btn" title="Kámen">🪨</button>
                                <button type="submit" name="move" value="✂️" class="duel-btn" title="Nůžky">✂️</button>
                                <button type="submit" name="move" value="📄" class="duel-btn" title="Papír">📄</button>
                            </form>
                        {% elif not session.username %}
                            <div style="text-align: center; font-size: 0.8em; color: #e74c3c;">Pro přijetí výzvy se musíš přihlásit.</div>
                        {% else %}
                            <div style="text-align: center; font-size: 0.8em; color: #f39c12;">Nemůžeš hrát sám se sebou.</div>
                        {% endif %}
                        
                    {% else %}
                        <div style="text-align: center; font-size: 1.5em; margin: 10px 0;">
                            <b>{{ msg.author }}</b> ({{ msg.p1_move }}) <br> <span style="font-size: 0.6em; color: #95a5a6;">vs</span> <br> <b>{{ msg.p2 }}</b> ({{ msg.p2_move }})
                        </div>
                        
                        {% if msg.winner == 'TIE' %}
                            <div class="duel-result duel-tie">Remíza! 🤝</div>
                        {% else %}
                            <div class="duel-result duel-win">🏆 Vítěz: {{ msg.winner }}!</div>
                        {% endif %}
                    {% endif %}
                    <hr style="border: 0; border-top: 1px dashed #e2e8f0; margin: 15px 0;">
                {% else %}
                    {% if msg.image %} <img src="{{ msg.image }}" class="note-image"> {% endif %}
                    <div class="note-text">{{ msg.text }}</div>
                {% endif %}
                
                <div class="reactions-container">
                    {% for emoji, count in msg.reactions.items() %}
                        <span class="badge">{{ emoji }} {{ count }}</span>
                    {% endfor %}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <form method="POST" action="/react" class="emoji-bar">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" name="emoji" value="👍" class="btn-react">👍</button>
                        <button type="submit" name="emoji" value="❤️" class="btn-react">❤️</button>
                        <button type="submit" name="emoji" value="😂" class="btn-react">😂</button>
                        <button type="submit" name="emoji" value="😮" class="btn-react">😮</button>
                        <button type="submit" name="emoji" value="😢" class="btn-react">😢</button>
                        <button type="submit" name="emoji" value="🙏" class="btn-react">🙏</button>
                    </form>
                    
                    {% if session.username == msg.author or session.role == 'admin' %}
                    <form method="POST" action="/delete" style="margin:0;">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" class="del-btn" title="Smazat">🗑️</button>
                    </form>
                    {% endif %}
                </div>
                
                {% if msg.replies %}
                <div class="replies">
                    {% for r in msg.replies %}
                        <div class="reply-item">
                            <div class="reply-meta">{{ r.author }}</div>
                            <div class="reply-text">{{ r.text }}</div>
                        </div>
                    {% endfor %}
                </div>
                {% endif %}

                {% if session.username %}
                <form method="POST" action="/reply" style="display:flex; gap:5px; margin-top:auto;">
                    <input type="hidden" name="note_id" value="{{ msg.id }}">
                    <input type="text" name="reply_text" placeholder="Napsat odpověď..." required style="flex-grow:1; padding:8px; border:1px solid #e2e8f0; border-radius:6px; font-size: 0.85em;">
                    <button type="submit" style="background:#2c3e50; padding: 8px 12px; border-radius:6px; color: white; border: none; cursor: pointer;">↪</button>
                </form>
                {% endif %}
            </div>
        {% endfor %}
    </div>

    <script>
        let isTyping = false;
        document.addEventListener('focusin', function(e) { if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') isTyping = true; });
        document.addEventListener('focusout', function(e) { isTyping = false; });

        setInterval(function() {
            if (!isTyping) {
                fetch(window.location.href)
                    .then(response => response.text())
                    .then(html => {
                        let parser = new DOMParser();
                        let doc = parser.parseFromString(html, 'text/html');
                        let newBoard = doc.getElementById('board-container');
                        if (newBoard) document.getElementById('board-container').innerHTML = newBoard.innerHTML;
                    })
                    .catch(err => console.log('Chyba refreshu:', err));
            }
        }, 5000);
    </script>
</body>
</html>
"""

HTML_AI = """<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><title>AI Poradna</title><style>body { font-family: sans-serif; margin: 40px; background: #eef2f5; } .container { max-width: 600px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); } input { padding: 10px; width: 70%; border: 1px solid #ccc; border-radius: 5px; } button { padding: 10px 20px; background: #007BFF; color: white; border: none; border-radius: 5px; cursor: pointer; } .result { background: #f8f9fa; padding: 15px; border-left: 5px solid #007BFF; margin-top: 20px; } .error { background: #ffe6e6; padding: 15px; border-left: 5px solid #d9534f; margin-top: 20px; color: #a94442; }</style></head><body><div class="container"><h1 style="color: #007BFF; margin-top: 0;">Online AI Poradna 🤖</h1><form method="POST" action="/ai"><input type="text" name="query" placeholder="Zeptej se umělé inteligence..." required> <button type="submit">Odeslat</button></form><br><a href="/" style="font-weight: bold; color: #333; text-decoration: none;">⬅️ Zpět na Nástěnku</a>{% if answer %}<div class="result"><p><strong>Dotaz:</strong> {{ question }}</p><p><strong>AI:</strong> {{ answer }}</p></div>{% elif error %}<div class="error"><p><strong>Chyba:</strong> {{ error }}</p></div>{% endif %}</div></body></html>"""

# --- ROUTOVÁNÍ ---
@app.route('/', methods=['GET'])
def home():
    error = request.args.get('error')
    vsechny_tagy = list(kolekce_vzkazu.distinct("tags"))
    vsechny_tagy = [t for t in vsechny_tagy if t] 
    
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

    if not username or not password: return redirect('/?error=Vyplň jméno i heslo!')

    if akce == 'register':
        if kolekce_uzivatelu.find_one({"username": username}): return redirect('/?error=Toto jméno už je zabrané!')
        if username.lower() == 'admin' and not kolekce_uzivatelu.find_one({"role": "admin"}): role = 'admin'
        else: role = 'user'

        kolekce_uzivatelu.insert_one({"username": username, "password": generate_password_hash(password), "role": role})
        session['username'] = username
        session['role'] = role

    elif akce == 'login':
        user = kolekce_uzivatelu.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
        else: return redirect('/?error=Špatné jméno nebo heslo!')

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add', methods=['POST'])
def add_note():
    if 'username' not in session: return redirect('/?error=Musíš být přihlášený!')

    author = session['username']
    text = request.form.get('msg')
    is_important = request.form.get('is_important') == 'on'
    is_duel = request.form.get('is_duel') == 'on'
    duel_move = request.form.get('duel_move')
    
    nalezeno_tagu = re.findall(r"#(\w+)", text)
    is_pinned = True if is_important and session.get('role') == 'admin' else False

    file = request.files.get('image')
    img_b64 = None
    if file and file.filename and not is_duel:
        img_b64 = "data:" + file.content_type + ";base64," + base64.b64encode(file.read()).decode('utf-8')
    
    if text:
        note_id = uuid.uuid4().hex[:8]
        new_note = {
            "id": note_id,
            "author": author,
            "text": text,
            "timestamp": datetime.now().strftime("%H:%M"),
            "cas_vytvoreni": datetime.now(),
            "image": img_b64,
            "replies": [],
            "reactions": {},
            "tags": nalezeno_tagu,
            "is_pinned": is_pinned,
            "type": "duel" if is_duel else "normal"
        }

        # Pokud je to duel, přidáme speciální data
        if is_duel:
            new_note["duel_state"] = "waiting" # waiting / finished
            new_note["p1_move"] = duel_move    # To co vybral autor
            new_note["p2"] = None              # Zatím nikdo
            new_note["p2_move"] = None
            new_note["winner"] = None

        kolekce_vzkazu.insert_one(new_note)

        # AI nereaguje na duely, jen na normální text
        if "@AI" in text.upper() and not is_duel:
            prompt = text.replace("@AI", "").replace("@ai", "").strip()
            ai_reply = ask_ai(prompt if prompt else "Ahoj.")
            kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")}}})
            
    return redirect('/')

# --- LOGIKA PRO VYHODNOCENÍ DUELU ---
@app.route('/play_duel', methods=['POST'])
def play_duel():
    if 'username' not in session: return redirect('/')
    
    note_id = request.form.get('note_id')
    p2_move = request.form.get('move') # Zbraň soupeře
    p2_name = session['username']
    
    duel = kolekce_vzkazu.find_one({"id": note_id, "type": "duel", "duel_state": "waiting"})
    
    if duel and duel['author'] != p2_name:
        p1_move = duel['p1_move']
        p1_name = duel['author']
        
        # Kdo vyhrál?
        if p1_move == p2_move:
            winner = 'TIE'
        elif (p1_move == '🪨' and p2_move == '✂️') or \
             (p1_move == '✂️' and p2_move == '📄') or \
             (p1_move == '📄' and p2_move == '🪨'):
            winner = p1_name
        else:
            winner = p2_name
            
        # Aktualizace v databázi
        kolekce_vzkazu.update_one(
            {"id": note_id},
            {"$set": {
                "duel_state": "finished",
                "p2": p2_name,
                "p2_move": p2_move,
                "winner": winner
            }}
        )
        
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_note():
    if 'username' not in session: return redirect('/')
    note_id = request.form.get('note_id')
    if note_id:
        vzkaz = kolekce_vzkazu.find_one({"id": note_id})
        if vzkaz and (vzkaz['author'] == session['username'] or session.get('role') == 'admin'):
            kolekce_vzkazu.delete_one({"id": note_id})
    return redirect(request.referrer or '/')

@app.route('/react', methods=['POST'])
def react_note():
    note_id = request.form.get('note_id')
    emoji = request.form.get('emoji')
    povoleny_emojis = ['👍', '❤️', '😂', '😮', '😢', '🙏']
    if note_id and emoji in povoleny_emojis:
        kolekce_vzkazu.update_one({"id": note_id}, {"$inc": {f"reactions.{emoji}": 1}})
    return redirect(request.referrer or '/')

@app.route('/reply', methods=['POST'])
def add_reply():
    if 'username' not in session: return redirect('/?error=Musíš se přihlásit!')
    note_id = request.form.get('note_id')
    author = session['username']
    reply_text = request.form.get('reply_text')
    
    if reply_text and note_id:
        kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": author, "text": reply_text, "timestamp": datetime.now().strftime("%H:%M")}}})
        if "@AI" in reply_text.upper():
            ai_reply = ask_ai(reply_text.replace("@AI", "").replace("@ai", "").strip() or "Ahoj.")
            kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")}}})
    return redirect('/')

@app.route('/ai', methods=['GET', 'POST'])
def ai_page():
    answer, question, error = None, None, None
    if request.method == 'POST':
        question = request.form.get('query')
        answer = ask_ai(question)
        if answer.startswith("Promiň"): error = answer; answer = None
    return render_template_string(HTML_AI, question=question, answer=answer, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
