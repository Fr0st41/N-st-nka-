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

# --- VZHLED (RESPONZIVNÍ HTML & CSS) ---
HTML_MAIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="utf-8">
    <title>Digitální Nástěnka ✨</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        * { box-sizing: border-box; } /* Zabrání přetékání prvků */
        
        body { font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 0 0 40px 0; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #2c3e50; }
        h1 { text-align: center; color: #1a252f; font-weight: 800; font-size: 2.5em; margin-top: 30px; letter-spacing: -1px; padding: 0 10px;}
        
        .auth-bar { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 12px 20px; text-align: center; font-size: 0.9em; border-bottom: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .auth-bar a { color: #e74c3c; font-weight: 600; text-decoration: none; margin-left: 15px; padding: 6px 12px; border-radius: 20px; background: rgba(231, 76, 60, 0.1); transition: 0.2s; display: inline-block;}
        .auth-bar a:hover { background: rgba(231, 76, 60, 0.2); }
        
        .controls { text-align: center; margin-bottom: 20px; padding: 0 15px; width: 100%; max-width: 800px; margin-left: auto; margin-right: auto;}
        .main-form { background: #ffffff; padding: 20px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #edf2f7; width: 100%; }
        
        /* Flexboxy pro formuláře */
        .form-row { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: center; }
        .form-row-bottom { margin-top: 15px; border-top: 1px solid #eee; padding-top: 15px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 15px;}
        
        input[type="text"], input[type="password"] { padding: 12px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-family: inherit; transition: 0.3s; outline: none; flex-grow: 1; }
        input[type="text"]:focus, input[type="password"]:focus { border-color: #3498db; }
        input[type="file"] { font-size: 0.85em; color: #7f8c8d; max-width: 100%; overflow: hidden; }
        
        button { padding: 12px 20px; background-color: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-family: inherit; transition: 0.2s; white-space: nowrap;}
        button:hover { background-color: #2980b9; transform: translateY(-1px); }
        
        .ai-btn { padding: 12px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3); white-space: nowrap; text-align: center;}
        
        .filters { text-align: center; margin-bottom: 20px; padding: 0 10px; }
        .tag-btn { display: inline-block; background: #fff; padding: 8px 16px; border-radius: 20px; margin: 4px; text-decoration: none; color: #34495e; font-size: 0.9em; font-weight: 600; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; border: 1px solid #e2e8f0; }
        .tag-btn:hover { background: #3498db; color: #fff; border-color: #3498db; }
        
        /* RESPONZIVNÍ GRID PRO KARTIČKY */
        .board { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; padding: 10px 20px; max-width: 1400px; margin: 0 auto; }
        
        .note-card { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(15px); padding: 20px; border-radius: 16px; border: 1px solid #fff; box-shadow: 0 8px 20px rgba(0,0,0,0.06); transition: transform 0.3s; display: flex; flex-direction: column; width: 100%;}
        .note-card:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,0,0,0.1); }
        .note-card.pinned { border: 2px solid #e74c3c; background: #fffdfd; }
        .note-card.duel { border: 2px solid #f39c12; background: linear-gradient(135deg, #fff 0%, #fdfbf7 100%); }
        
        .duel-title { font-weight: 800; color: #e67e22; font-size: 1.2em; text-align: center; margin-bottom: 15px; }
        .duel-buttons { display: flex; justify-content: space-around; margin: 15px 0; }
        .duel-btn { font-size: 2em; background: none; border: 2px solid #e2e8f0; border-radius: 50%; width: 60px; height: 60px; cursor: pointer; transition: 0.2s; display: flex; align-items: center; justify-content: center;}
        .duel-btn:hover { background: #f39c12; border-color: #f39c12; transform: scale(1.1); }
        .duel-result { text-align: center; font-size: 1.1em; font-weight: 800; padding: 10px; border-radius: 10px; margin-top: 10px; }
        .duel-win { background: #d4edda; color: #155724; }
        .duel-tie { background: #fff3cd; color: #856404; }
        
        .meta { font-size: 0.85em; color: #7f8c8d; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;}
        .note-text { font-size: 1.1em; line-height: 1.5; flex-grow: 1; word-wrap: break-word; color: #34495e; margin-bottom: 15px; }
        .note-image { width: 100%; max-height: 250px; object-fit: cover; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee;}
        
        .reactions-container { margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 5px;}
        .badge { display: inline-block; background: #f1f2f6; padding: 5px 10px; border-radius: 15px; font-size: 0.85em; color: #2c3e50; border: 1px solid #e2e8f0; }
        
        .emoji-bar { display: flex; flex-wrap: wrap; gap: 5px; background: #fff; padding: 5px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #edf2f7;}
        .btn-react { background: none; border: none; cursor: pointer; font-size: 1.2em; padding: 4px; border-radius: 50%; transition: 0.2s; }
        
        .replies { background: #f8fafc; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e2e8f0;}
        .reply-item { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #edf2f7; word-wrap: break-word;}
        .reply-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
        .reply-meta { font-size: 0.75em; color: #95a5a6; margin-bottom: 3px; font-weight: 600;}
        .reply-text { font-size: 0.95em; color: #475569; }
        
        .del-btn { background: rgba(231, 76, 60, 0.1); color: #e74c3c; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; transition: 0.2s; font-weight: bold; font-size: 0.9em;}
        .del-btn:hover { background: #e74c3c; color: white;}
        .error-msg { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #f87171; display: inline-block; width: 100%;}

        /* ----- MOBILNÍ OPTIMALIZACE (MEDIA QUERIES) ----- */
        @media (max-width: 600px) {
            h1 { font-size: 2em; margin-top: 20px; }
            .auth-bar { display: flex; flex-direction: column; gap: 10px; padding: 15px; }
            .auth-bar a { margin-left: 0; }
            
            .controls { padding: 0 10px; }
            .main-form { padding: 15px; }
            .form-row { flex-direction: column; align-items: stretch; }
            .form-row input[type="text"], .form-row input[type="password"] { width: 100% !important; }
            .form-row-bottom { flex-direction: column; align-items: stretch; gap: 10px;}
            
            button, .ai-btn { width: 100%; display: block; margin: 0; }
            
            .board { grid-template-columns: 1fr; padding: 10px; gap: 15px;}
            .note-card { padding: 15px; }
            
            .emoji-bar { justify-content: center; width: 100%; margin-bottom: 10px; }
            .card-actions { flex-direction: column; align-items: stretch; }
            .del-btn { width: 100%; margin-top: 5px; }
        }
    </style>
    <script>
        setInterval(function() {
            // Zkontrolujeme, na co má uživatel zrovna kliknuto
            let active = document.activeElement;
            let isTyping = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'PASSWORD');

            if (!isTyping) {
                // cache: 'no-store' je ten magický příkaz, který zakáže prohlížeči používat stará data!
                fetch(window.location.href, { cache: "no-store" })
                    .then(response => response.text())
                    .then(html => {
                        let parser = new DOMParser();
                        let doc = parser.parseFromString(html, 'text/html');
                        let newBoard = doc.getElementById('board-container');
                        let currentBoard = document.getElementById('board-container');
                        
                        // Přepíšeme to jen tehdy, když se obsah fakt změnil (aby to neblikalo zbytečně)
                        if (newBoard && currentBoard.innerHTML !== newBoard.innerHTML) {
                            currentBoard.innerHTML = newBoard.innerHTML;
                        }
                    })
                    .catch(err => console.log('Chyba refreshu:', err));
            }
        }, 5000);
    </script>
</head>
<body>
    <div class="auth-bar">
        {% if session.username %}
            <span>👤 <b>{{ session.username }}</b> {% if session.role == 'admin' %} <span style="color: #f39c12;">(Admin)</span> {% endif %}</span>
            <a href="/logout">Odhlásit se</a>
        {% else %}
            <span>Nejsi přihlášen. Můžeš číst, pro psaní se musíš zaregistrovat.</span>
        {% endif %}
    </div>

    <h1>Třídní Nástěnka ✨</h1>
    
    <div class="controls">
        {% if error %} <div class="error-msg">⚠️ {{ error }}</div> {% endif %}
        
        {% if session.username %}
            <form method="POST" action="/add" class="main-form" enctype="multipart/form-data">
                <div class="form-row">
                    <input type="text" name="msg" placeholder="Napiš vzkaz... (@AI) (#tag)" required>
                    <input type="file" name="image" accept="image/*">
                </div>
                
                <div class="form-row-bottom">
                    <label style="font-weight: 600; cursor: pointer; color: #e67e22; display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" name="is_duel" id="is-duel" onchange="toggleDuel()"> ⚔️ 1v1 Duel
                    </label>
                    {% if session.role == 'admin' %}
                        <label style="color: #e74c3c; font-weight: 600; display: flex; align-items: center; gap: 5px;">
                            <input type="checkbox" name="is_important"> 📌 Důležité
                        </label>
                    {% endif %}
                    
                    <div id="duel-options" style="display: none; width: 100%; background: #fdfbf7; padding: 15px; border-radius: 8px; border: 1px solid #f39c12; text-align: center; margin-top: 10px;">
                        <span style="display:block; margin-bottom: 10px; font-weight: bold;">Vyber svou tajnou zbraň:</span>
                        <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                            <label><input type="radio" name="duel_move" value="🪨" checked> 🪨 Kámen</label>
                            <label><input type="radio" name="duel_move" value="✂️"> ✂️ Nůžky</label>
                            <label><input type="radio" name="duel_move" value="📄"> 📄 Papír</label>
                        </div>
                    </div>

                    <div style="display: flex; gap: 10px; width: 100%; flex-wrap: wrap;">
                        <button type="submit" style="flex-grow: 1;">Vystavit vzkaz</button>
                        <a href="/ai" class="ai-btn" style="flex-grow: 1;">🤖 AI Poradna</a>
                    </div>
                </div>
            </form>
        {% else %}
            <div class="main-form">
                <h3 style="margin-top: 0; color: #2c3e50;">Přihlášení / Registrace</h3>
                <form method="POST" action="/auth" class="form-row">
                    <input type="text" name="username" placeholder="Jméno" required>
                    <input type="password" name="password" placeholder="Heslo" required>
                    <div style="display: flex; gap: 10px; width: 100%;">
                        <button type="submit" name="action" value="login" style="flex: 1;">Přihlásit</button>
                        <button type="submit" name="action" value="register" style="background: #2ecc71; flex: 1;">Registrovat</button>
                    </div>
                </form>
            </div>
        {% endif %}
    </div>

    <div class="filters">
        <a href="/" class="tag-btn" style="background: #2c3e50; color: white;">Vše</a>
        {% for tag in all_tags %}
            <a href="/?tag={{ tag }}" class="tag-btn">#{{ tag }}</a>
        {% endfor %}
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
                            <div style="text-align: center; font-size: 0.85em; color: #e74c3c; padding: 10px;">Pro přijetí výzvy se přihlas.</div>
                        {% else %}
                            <div style="text-align: center; font-size: 0.85em; color: #f39c12; padding: 10px;">Nemůžeš hrát sám se sebou.</div>
                        {% endif %}
                        
                    {% else %}
                        <div style="text-align: center; font-size: 1.3em; margin: 15px 0;">
                            <b>{{ msg.author }}</b> ({{ msg.p1_move }}) <br> <span style="font-size: 0.7em; color: #95a5a6;">vs</span> <br> <b>{{ msg.p2 }}</b> ({{ msg.p2_move }})
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
                
                <div class="card-actions" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; gap: 10px;">
                    <form method="POST" action="/react" class="emoji-bar" style="margin: 0;">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" name="emoji" value="👍" class="btn-react">👍</button>
                        <button type="submit" name="emoji" value="❤️" class="btn-react">❤️</button>
                        <button type="submit" name="emoji" value="😂" class="btn-react">😂</button>
                        <button type="submit" name="emoji" value="😮" class="btn-react">😮</button>
                        <button type="submit" name="emoji" value="😢" class="btn-react">😢</button>
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
                    <input type="text" name="reply_text" placeholder="Odpověz..." required style="flex-grow:1; padding:10px; border:1px solid #e2e8f0; border-radius:8px; font-size: 0.9em;">
                    <button type="submit" style="background:#2c3e50; padding: 10px 15px; border-radius:8px; color: white; border: none; cursor: pointer;">↪</button>
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

HTML_AI = """<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><title>AI Poradna</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body { font-family: sans-serif; margin: 0; padding: 20px; background: #eef2f5; } .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); } input { padding: 12px; width: 100%; box-sizing: border-box; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 10px;} button { padding: 12px 20px; width: 100%; background: #007BFF; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;} .result { background: #f8f9fa; padding: 15px; border-left: 5px solid #007BFF; margin-top: 20px; word-wrap: break-word;} .error { background: #ffe6e6; padding: 15px; border-left: 5px solid #d9534f; margin-top: 20px; color: #a94442; } a.back-link { display: inline-block; margin-top: 15px; font-weight: bold; color: #333; text-decoration: none; }</style></head><body><div class="container"><h2 style="color: #007BFF; margin-top: 0;">Online AI Poradna 🤖</h2><form method="POST" action="/ai"><input type="text" name="query" placeholder="Zeptej se AI..." required> <button type="submit">Odeslat dotaz</button></form><a href="/" class="back-link">⬅️ Zpět na Nástěnku</a>{% if answer %}<div class="result"><p><strong>Dotaz:</strong> {{ question }}</p><p><strong>AI:</strong> {{ answer }}</p></div>{% elif error %}<div class="error"><p><strong>Chyba:</strong> {{ error }}</p></div>{% endif %}</div></body></html>"""

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

        if is_duel:
            new_note["duel_state"] = "waiting"
            new_note["p1_move"] = duel_move
            new_note["p2"] = None
            new_note["p2_move"] = None
            new_note["winner"] = None

        kolekce_vzkazu.insert_one(new_note)

        if "@AI" in text.upper() and not is_duel:
            prompt = text.replace("@AI", "").replace("@ai", "").strip()
            ai_reply = ask_ai(prompt if prompt else "Ahoj.")
            kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")}}})
            
    return redirect('/')

@app.route('/play_duel', methods=['POST'])
def play_duel():
    if 'username' not in session: return redirect('/')
    
    note_id = request.form.get('note_id')
    p2_move = request.form.get('move')
    p2_name = session['username']
    
    duel = kolekce_vzkazu.find_one({"id": note_id, "type": "duel", "duel_state": "waiting"})
    
    if duel and duel['author'] != p2_name:
        p1_move = duel['p1_move']
        p1_name = duel['author']
        
        if p1_move == p2_move: winner = 'TIE'
        elif (p1_move == '🪨' and p2_move == '✂️') or (p1_move == '✂️' and p2_move == '📄') or (p1_move == '📄' and p2_move == '🪨'): winner = p1_name
        else: winner = p2_name
            
        kolekce_vzkazu.update_one({"id": note_id}, {"$set": {"duel_state": "finished", "p2": p2_name, "p2_move": p2_move, "winner": winner}})
        
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
@app.route('/admin-db')
def view_database():
    # 1. Ochrana: Pustíme tam POUZE admina
    if session.get('role') != 'admin':
        return "<h1 style='color:red;'>Přístup odepřen! Nejsi admin.</h1>", 403

    # 2. Vytáhneme úplně všechna data z obou kolekcí
    všichni_uzivatele = list(kolekce_uzivatelu.find())
    všechny_vzkazy = list(kolekce_vzkazu.find())

    # 3. Jednoduché HTML pro zobrazení syrových dat v tabulkách
    html_db = """
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="utf-8">
        <title>Tajný pohled do Databáze</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #1e1e1e; color: #fff; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 40px; background: #2d2d2d; }
            th, td { border: 1px solid #444; padding: 10px; text-align: left; }
            th { background: #333; color: #4CAF50; }
            a { color: #3498db; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🕵️‍♂️ Syrová data v MongoDB</h1>
        <a href="/">⬅️ Zpět na nástěnku</a>

        <h2>Kolekce: Uživatelé</h2>
        <table>
            <tr><th>Jméno</th><th>Role</th><th>Zašifrované heslo (Hash)</th></tr>
            {% for u in uzivatele %}
            <tr>
                <td>{{ u.username }}</td>
                <td>{{ u.role }}</td>
                <td style="font-family: monospace; font-size: 0.8em; color: #aaa;">{{ u.password }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Kolekce: Vzkazy</h2>
        <table>
            <tr><th>Autor</th><th>Text</th><th>Reakce</th><th>Odpovědi</th></tr>
            {% for v in vzkazy %}
            <tr>
                <td><b>{{ v.author }}</b></td>
                <td>{{ v.text }}</td>
                <td>{{ v.reactions }}</td>
                <td>{{ v.replies | length }} odpovědí</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    return render_template_string(html_db, uzivatele=všichni_uzivatele, vzkazy=všechny_vzkazy)
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
