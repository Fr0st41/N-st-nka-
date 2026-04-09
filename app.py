# ==========================================
# 1. IMPORTY (Nástroje, které aplikace potřebuje)
# ==========================================
import os                  # Pro čtení tajných hesel ze serveru (proměnné prostředí)
import random              # Generování náhody (hody kostkou, míchání drátků u bomby)
import base64              # Převádí nahrané obrázky na dlouhý text, aby šly uložit do databáze
import uuid                # Generuje unikátní kódy pro každý papírek (např. 'a7b3c9d1')
import re                  # Hledání speciálních znaků (např. hashtagů v textu)
from datetime import datetime # Zjišťování aktuálního času (např. 14:30)

# Knihovny pro běh samotného webu (Flask)
from flask import Flask, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

# Knihovny pro umělou inteligenci a databázi
from openai import OpenAI
import httpx
from pymongo import MongoClient

# Založení aplikace
app = Flask(__name__)
# Tajný klíč pro bezpečné přihlašování (vytvoří se nový při každém startu)
app.secret_key = os.urandom(24) 

# ==========================================
# 2. NASTAVENÍ UMĚLÉ INTELIGENCE (AI)
# ==========================================
# Bere si API klíč a adresu ze školního serveru
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")
MODEL_NAME = "gemma3:27b"

# Vytvoření "klienta", přes kterého si budeme s AI psát
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    http_client=httpx.Client(verify=False)
)

# ==========================================
# 3. PŘIPOJENÍ K DATABÁZI (MongoDB)
# ==========================================
# Řekneme aplikaci, kde databáze bydlí (adresa 'db')
mongo_uri = os.environ.get("MONGO_URI", "mongodb://db:27017/")
mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

# Vytvoříme hlavní databázi a v ní dvě "složky" (kolekce)
db = mongo_client.nastenka_databaze
kolekce_vzkazu = db.vzkazy       # Sem ukládáme papírky
kolekce_uzivatelu = db.uzivatele # Sem ukládáme registrované lidi

# ==========================================
# 4. FUNKCE PRO AI (S PAMĚTÍ - RAG)
# ==========================================
def ask_ai(prompt):
    try:
        # Než se zeptáme AI, vytáhneme posledních 20 vzkazů, aby věděla, o čem se třída baví
        nedavne_vzkazy = list(kolekce_vzkazu.find().sort("cas_vytvoreni", -1).limit(20))
        kontext = "Historie nástěnky:\n"
        for m in nedavne_vzkazy:
            kontext += f"- {m.get('author', 'Někdo')}: {m.get('text', '')}\n"

        # Příkaz, jak se má AI chovat
        systemovy_pokyn = "Jsi vtipný asistent na třídní nástěnce. Odpovídej stručně.\n" + kontext

        # Odeslání dotazu a čekání na odpověď
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": systemovy_pokyn},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Promiň, spím nebo mám poruchu. (Chyba: {str(e)})"

# ==========================================
# 5. VZHLED WEBU (HTML, CSS a JavaScript)
# ==========================================
# Proměnná HTML_MAIN obsahuje celý vizuál (barvy, animace, tlačítka a Focus mód).
HTML_MAIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="utf-8">
    <title>Třídní Nástěnka ✨</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        * { box-sizing: border-box; }
        body { font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 0 0 40px 0; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #2c3e50; }
        h1 { text-align: center; color: #1a252f; font-weight: 800; font-size: 2.5em; margin-top: 30px; letter-spacing: -1px; padding: 0 10px;}
        
        .auth-bar { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 12px 20px; text-align: center; font-size: 0.9em; border-bottom: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .auth-bar a { color: #e74c3c; font-weight: 600; text-decoration: none; margin-left: 15px; padding: 6px 12px; border-radius: 20px; background: rgba(231, 76, 60, 0.1); transition: 0.2s; display: inline-block;}
        
        .controls { text-align: center; margin-bottom: 20px; padding: 0 15px; width: 100%; max-width: 900px; margin-left: auto; margin-right: auto;}
        .main-form { background: #ffffff; padding: 20px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #edf2f7; width: 100%; }
        
        .form-row { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: center; }
        .form-row-bottom { margin-top: 15px; border-top: 1px solid #eee; padding-top: 15px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 15px;}
        
        input[type="text"], input[type="password"] { padding: 12px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-family: inherit; transition: 0.3s; outline: none; flex-grow: 1; }
        input[type="text"]:focus { border-color: #3498db; }
        button { padding: 12px 20px; background-color: #3498db; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-family: inherit; transition: 0.2s; white-space: nowrap;}
        button:hover { filter: brightness(1.1); transform: translateY(-1px); }
        .ai-btn { padding: 12px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; white-space: nowrap; text-align: center;}
        
        .type-selector { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; width: 100%; margin-bottom: 15px;}
        .type-radio { display: none; }
        .type-label { padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 20px; cursor: pointer; font-size: 0.9em; font-weight: bold; color: #7f8c8d; transition: 0.2s;}
        .type-radio:checked + .type-label { background: #2c3e50; color: white; border-color: #2c3e50; transform: scale(1.05); }

        .board { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 10px 20px; max-width: 1400px; margin: 0 auto; }
        
        .note-card { 
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(15px); padding: 20px; border-radius: 16px; 
            border: 1px solid #fff; box-shadow: 0 8px 20px rgba(0,0,0,0.06); transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); 
            display: flex; flex-direction: column; width: 100%; position: relative;
            max-height: 420px; overflow: hidden;
        }
        .note-card:hover { transform: translateY(-3px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .note-card.pinned { border: 2px solid #e74c3c; background: #fffdfd; }
        
        .note-card.expanded {
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) !important;
            width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;
            z-index: 1000; box-shadow: 0 20px 60px rgba(0,0,0,0.5); cursor: default;
        }
        
        #overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(3px); z-index: 999; cursor: pointer;
        }
        #overlay.active { display: block; }
        
        .expand-btn { position: absolute; top: 15px; right: 15px; background: rgba(255,255,255,0.9); border: 1px solid #e2e8f0; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); z-index: 10; font-size: 1.1em; padding: 0;}
        .expand-btn:hover { background: #3498db; color: white; border-color: #3498db; }
        .close-btn { display: none; position: absolute; top: 15px; right: 15px; background: #e74c3c; color: white; border: none; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; font-size: 1.1em; font-weight: bold; padding: 0;}
        .close-btn:hover { background: #c0392b; transform: scale(1.1); }
        
        .note-card.expanded .close-btn { display: flex; }
        .note-card.expanded .expand-btn { display: none; }

        .note-card.duel { border: 2px solid #f39c12; background: linear-gradient(135deg, #fff 0%, #fdfbf7 100%); }
        .note-card.guess { border: 2px solid #3498db; background: linear-gradient(135deg, #fff 0%, #ebf5fb 100%); }
        .note-card.dice { border: 2px solid #9b59b6; background: linear-gradient(135deg, #fff 0%, #f4ebf9 100%); }
        .note-card.bomb { border: 2px solid #e74c3c; background: linear-gradient(135deg, #fff 0%, #fdedec 100%); }
        
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        @keyframes shake { 0% { transform: translateX(0); } 25% { transform: translateX(-3px) rotate(-1deg); } 50% { transform: translateX(3px) rotate(1deg); } 75% { transform: translateX(-3px) rotate(-1deg); } 100% { transform: translateX(0); } }
        @keyframes explode { 0% { transform: scale(1); background: #e74c3c; } 50% { transform: scale(1.1); background: #c0392b; } 100% { transform: scale(1); background: #fee2e2; border-color: #e74c3c;} }
        
        .anim-shake { animation: shake 0.5s infinite; }
        .anim-explode { animation: explode 0.8s ease-out forwards; }
        .anim-pulse { animation: pulse 2s infinite; }

        .game-title { font-weight: 800; font-size: 1.2em; text-align: center; margin-bottom: 10px; }
        .duel-buttons, .bomb-wires { display: flex; justify-content: space-around; margin: 15px 0; flex-wrap: wrap; gap: 10px;}
        .game-btn { font-size: 2em; background: #fff; border: 2px solid #e2e8f0; border-radius: 50%; width: 60px; height: 60px; cursor: pointer; transition: 0.2s; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
        .game-btn:hover { transform: scale(1.15) rotate(5deg); }
        
        .wire { width: 100%; height: 15px; border-radius: 10px; cursor: pointer; margin-bottom: 8px; transition: 0.2s; border: 2px solid rgba(0,0,0,0.2); position: relative;}
        .wire:hover { transform: scaleX(1.05); }
        .wire.red { background: #e74c3c; } .wire.blue { background: #3498db; } .wire.green { background: #2ecc71; } .wire.yellow { background: #f1c40f; }
        .wire.cut { opacity: 0.3; cursor: not-allowed; text-align: center; color: white; font-size: 10px; line-height: 15px; }

        .duel-result { text-align: center; font-size: 1.1em; font-weight: 800; padding: 10px; border-radius: 10px; margin-top: 10px; }
        .duel-win { background: #d4edda; color: #155724; }
        .duel-lose { background: #f8d7da; color: #721c24; }
        
        .meta { font-size: 0.85em; color: #7f8c8d; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; padding-right: 40px;}
        .note-text { font-size: 1.1em; line-height: 1.5; flex-grow: 1; word-wrap: break-word; color: #34495e; margin-bottom: 15px; }
        
        .note-image { width: 100%; max-height: 200px; object-fit: cover; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee; background: #f8f9fa;}
        .note-card.expanded .note-image { max-height: 50vh; object-fit: contain; }
        
        .reactions-container { margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 5px;}
        .badge { display: inline-block; background: #f1f2f6; padding: 5px 10px; border-radius: 15px; font-size: 0.85em; color: #2c3e50; border: 1px solid #e2e8f0; }
        .emoji-bar { display: flex; flex-wrap: wrap; gap: 5px; background: #fff; padding: 5px; border-radius: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #edf2f7;}
        .btn-react { background: none; border: none; cursor: pointer; font-size: 1.2em; padding: 4px; border-radius: 50%; transition: 0.2s; }
        
        .replies { background: #f8fafc; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #e2e8f0;}
        .reply-item { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #edf2f7; word-wrap: break-word;}
        .del-btn { background: rgba(231, 76, 60, 0.1); color: #e74c3c; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; transition: 0.2s; font-weight: bold; font-size: 0.9em;}
        .del-btn:hover { background: #e74c3c; color: white;}

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
            .type-selector { gap: 8px; }
            .type-label { flex: 1 1 40%; text-align: center; padding: 10px 5px; font-size: 0.85em; display: block;}
        }
    </style>
    <script>
        // Přepíná viditelnost formulářů podle toho, jakou minihru uživatel nahoře zaklikne
        function toggleForms() {
            var type = document.querySelector('input[name="post_type"]:checked').value;
            document.getElementById('normal-options').style.display = (type === 'normal') ? 'block' : 'none';
            document.getElementById('duel-options').style.display = (type === 'duel') ? 'block' : 'none';
            document.getElementById('guess-options').style.display = (type === 'guess') ? 'block' : 'none';
            document.getElementById('bomb-options').style.display = (type === 'bomb') ? 'block' : 'none';
            document.getElementById('dice-options').style.display = (type === 'dice') ? 'block' : 'none';
        }
        
        // FOCUS MÓD: Funkce pro zvětšení papírku
        let isExpanded = false; // Pamatuje si, jestli je něco zvětšené
        function openCard(id) {
            document.querySelectorAll('.note-card.expanded').forEach(c => c.classList.remove('expanded'));
            document.getElementById('card-' + id).classList.add('expanded'); // Zvětší konkrétní lístek
            document.getElementById('overlay').classList.add('active'); // Ztmaví pozadí
            isExpanded = true;
        }
        // FOCUS MÓD: Funkce pro zavření papírku
        function closeCards() {
            document.querySelectorAll('.note-card.expanded').forEach(c => c.classList.remove('expanded'));
            document.getElementById('overlay').classList.remove('active');
            isExpanded = false;
        }
    </script>
</head>
<body>
    <div id="overlay" onclick="closeCards()" title="Zavřít"></div>

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
        {% if error %} <div style="background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-bottom: 15px;">⚠️ {{ error }}</div> {% endif %}
        
        {% if session.username %}
            <form method="POST" action="/add" class="main-form" enctype="multipart/form-data">
                <div class="type-selector">
                    <label><input type="radio" name="post_type" value="normal" class="type-radio" checked onchange="toggleForms()"><span class="type-label">📝 Vzkaz</span></label>
                    <label><input type="radio" name="post_type" value="duel" class="type-radio" onchange="toggleForms()"><span class="type-label">⚔️ RPS Duel</span></label>
                    <label><input type="radio" name="post_type" value="dice" class="type-radio" onchange="toggleForms()"><span class="type-label">🎲 Kostky</span></label>
                    <label><input type="radio" name="post_type" value="guess" class="type-radio" onchange="toggleForms()"><span class="type-label">🔢 Číslo</span></label>
                    <label><input type="radio" name="post_type" value="bomb" class="type-radio" onchange="toggleForms()"><span class="type-label">💣 Bomba</span></label>
                </div>

                <div id="normal-options"><div class="form-row"><input type="text" name="msg" placeholder="Napiš vzkaz... (@AI)"><input type="file" name="image" accept="image/*" style="font-size:0.8em; max-width:200px;"></div></div>
                <div id="duel-options" style="display: none; background: #fdfbf7; padding: 15px; border-radius: 12px; border: 2px dashed #f39c12; text-align: center;"><span style="display:block; margin-bottom: 10px; font-weight: 800; color: #d35400;">Zvol svou tajnou zbraň:</span><div style="display: flex; justify-content: center; gap: 10px;"><label><input type="radio" name="duel_move" value="🪨" checked> 🪨 Kámen</label><label><input type="radio" name="duel_move" value="✂️"> ✂️ Nůžky</label><label><input type="radio" name="duel_move" value="📄"> 📄 Papír</label></div></div>
                <div id="dice-options" style="display: none; background: #f4ebf9; padding: 15px; border-radius: 12px; border: 2px dashed #9b59b6; text-align: center;"><span style="font-weight: 800; color: #8e44ad;">Hoď kostkou a uvidíme, jestli tě někdo překoná! 🎲</span></div>
                <div id="guess-options" style="display: none; background: #ebf5fb; padding: 15px; border-radius: 12px; border: 2px dashed #3498db; text-align: center;"><span style="display:block; font-weight: 800; color: #2980b9;">Systém tajně vymyslí číslo od 1 do 100.</span></div>
                <div id="bomb-options" style="display: none; background: #fdedec; padding: 15px; border-radius: 12px; border: 2px dashed #e74c3c; text-align: center;"><span style="display:block; font-weight: 800; color: #c0392b;">Položíš na nástěnku bombu. Někdo ji bude muset zneškodnit!</span></div>
                
                <div class="form-row-bottom">
                    {% if session.role == 'admin' %} <label style="color: #e74c3c; font-weight: 600;"><input type="checkbox" name="is_important"> 📌 Důležité</label> {% endif %}
                    <div style="display: flex; gap: 10px; width: 100%;">
                        <button type="submit" style="flex-grow: 1;">Přidat na nástěnku</button>
                    </div>
                </div>
            </form>
        {% else %}
            <div class="main-form">
                <h3 style="margin-top: 0; color: #2c3e50;">Přihlášení / Registrace</h3>
                <form method="POST" action="/auth" class="form-row">
                    <input type="text" name="username" placeholder="Jméno" required>
                    <input type="password" name="password" placeholder="Heslo" required>
                    <button type="submit" name="action" value="login">Přihlásit</button>
                    <button type="submit" name="action" value="register" style="background: #2ecc71;">Registrovat</button>
                </form>
            </div>
        {% endif %}
    </div>

    <div class="board" id="board-container">
        {% for msg in messages %}
            <div id="card-{{ msg.id }}" class="note-card {% if msg.is_pinned %}pinned{% endif %} {{ msg.type }} {% if msg.type == 'bomb' and msg.bomb_state == 'exploded' %}anim-explode{% endif %}">
                
                <button type="button" class="expand-btn" onclick="openCard('{{ msg.id }}')" title="Zvětšit zprávu do popředí">🔍</button>
                <button type="button" class="close-btn" onclick="closeCards()" title="Zavřít">✖</button>

                <div class="meta">
                    <span>👤 <b>{{ msg.author }}</b> | 🕒 {{ msg.timestamp }}</span>
                    {% if msg.is_pinned %} <span title="Důležité" style="font-size: 1.2em;">📌</span> {% endif %}
                </div>
                
                {% if msg.type == 'guess' %}
                    <div class="game-title" style="color: #2980b9;">🔢 HÁDEJ ČÍSLO (1-100) 🔢</div>
                    {% if msg.guess_state == 'finished' %}
                        <div class="duel-result duel-win">🎉 Hra skončila! Číslo bylo {{ msg.secret_number }}.</div>
                    {% else %}
                        <div style="text-align: center; color: #e74c3c; font-weight: bold; margin-bottom: 10px;" class="anim-pulse">Piš tipy do komentářů 👇</div>
                    {% endif %}

                {% elif msg.type == 'duel' %}
                    <div class="game-title" style="color: #e67e22;">⚔️ KÁMEN NŮŽKY PAPÍR ⚔️</div>
                    {% if msg.duel_state == 'waiting' %}
                        <div style="text-align: center; color: #7f8c8d;">Čeká na odvážlivce...</div>
                        {% if session.username and session.username != msg.author %}
                            <form method="POST" action="/play_duel" class="duel-buttons">
                                <input type="hidden" name="note_id" value="{{ msg.id }}">
                                <button type="submit" name="move" value="🪨" class="game-btn">🪨</button>
                                <button type="submit" name="move" value="✂️" class="game-btn">✂️</button>
                                <button type="submit" name="move" value="📄" class="game-btn">📄</button>
                            </form>
                        {% endif %}
                    {% else %}
                        <div style="text-align: center; font-size: 1.2em; margin: 10px 0;"><b>{{ msg.author }}</b> ({{ msg.p1_move }}) vs <b>{{ msg.p2 }}</b> ({{ msg.p2_move }})</div>
                        <div class="duel-result {% if msg.winner == 'TIE' %}duel-tie{% else %}duel-win{% endif %}">{% if msg.winner == 'TIE' %}Remíza! 🤝{% else %}🏆 Vítěz: {{ msg.winner }}!{% endif %}</div>
                    {% endif %}
                    
                {% elif msg.type == 'dice' %}
                    <div class="game-title" style="color: #8e44ad;">🎲 SOUBOJ V KOSTKÁCH 🎲</div>
                    <div style="text-align: center; font-size: 1.5em; margin: 10px 0;"><b>{{ msg.author }}</b> hodil: <span style="background: #e2e8f0; padding: 5px 15px; border-radius: 8px;">{{ msg.p1_roll }}</span></div>
                    {% if msg.dice_state == 'waiting' %}
                        {% if session.username and session.username != msg.author %}
                            <form method="POST" action="/play_dice" style="text-align: center;">
                                <input type="hidden" name="note_id" value="{{ msg.id }}">
                                <button type="submit" style="background: #9b59b6; color: white; border:none; border-radius: 8px; font-weight:bold; font-size: 1.1em; padding: 15px 30px; cursor: pointer;">Zkusit ho přehodit! 🎲</button>
                            </form>
                        {% endif %}
                    {% else %}
                        <div style="text-align: center; font-size: 1.5em; margin: 10px 0;"><b>{{ msg.p2 }}</b> hodil: <span style="background: #e2e8f0; padding: 5px 15px; border-radius: 8px;">{{ msg.p2_roll }}</span></div>
                        <div class="duel-result {% if msg.winner == 'TIE' %}duel-tie{% else %}duel-win{% endif %}">{% if msg.winner == 'TIE' %}Remíza! 🤝{% else %}🏆 Vítěz: {{ msg.winner }}!{% endif %}</div>
                    {% endif %}

                {% elif msg.type == 'bomb' %}
                    <div class="game-title" style="color: #c0392b;">💣 ZNEŠKODNI BOMBU 💣</div>
                    {% if msg.bomb_state == 'active' %}
                        <div style="text-align: center; font-size: 3em; margin: 10px 0;" class="anim-shake">💣</div>
                        <div style="text-align: center; color: #7f8c8d; margin-bottom: 10px; font-weight: bold;">Ustřihni správný drátek!</div>
                        <form method="POST" action="/cut_wire" style="width: 100%;">
                            <input type="hidden" name="note_id" value="{{ msg.id }}">
                            {% for color in ['red', 'blue', 'green', 'yellow'] %}
                                {% if color in msg.cut_wires %}
                                    <div class="wire {{ color }} cut">Přestřiženo</div>
                                {% else %}
                                    {% if session.username %}<button type="submit" name="wire_color" value="{{ color }}" class="wire {{ color }}" title="Ustřihnout {{ color }}"></button>{% else %}<div class="wire {{ color }}"></div>{% endif %}
                                {% endif %}
                            {% endfor %}
                        </form>
                    {% elif msg.bomb_state == 'defused' %}
                        <div style="text-align: center; font-size: 3em; margin: 10px 0;">🎉</div>
                        <div class="duel-result duel-win">Bomba zneškodněna hrdinou: <b>{{ msg.hero }}</b>!</div>
                    {% elif msg.bomb_state == 'exploded' %}
                        <div style="text-align: center; font-size: 3em; margin: 10px 0;">💥</div>
                        <div class="duel-result duel-lose">BOMBA VYBOUCHLA! Odpálil ji: <b>{{ msg.hero }}</b>.</div>
                    {% endif %}

                {% else %}
                    {% if msg.image %} <img src="{{ msg.image }}" class="note-image"> {% endif %}
                    <div class="note-text">{{ msg.text }}</div>
                {% endif %}
                
                <hr style="border: 0; border-top: 1px dashed #e2e8f0; margin: 15px 0;">

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
                    </form>
                    {% if session.username == msg.author or session.role == 'admin' %}
                    <form method="POST" action="/delete" style="margin:0;">
                        <input type="hidden" name="note_id" value="{{ msg.id }}">
                        <button type="submit" class="del-btn">🗑️</button>
                    </form>
                    {% endif %}
                </div>
                
                {% if msg.replies %}
                <div class="replies">
                    {% for r in msg.replies %}
                        <div class="reply-item">
                            <div class="reply-meta">{{ r.author }}</div>
                            <div class="reply-text">{% if '🤖 Rozhodčí' in r.author %}<b style="color: #e74c3c;">{{ r.text }}</b>{% else %}{{ r.text }}{% endif %}</div>
                        </div>
                    {% endfor %}
                </div>
                {% endif %}

                {% if session.username %}
                <form method="POST" action="/reply" style="display:flex; gap:5px; margin-top:auto;">
                    <input type="hidden" name="note_id" value="{{ msg.id }}">
                    <input type="text" name="reply_text" placeholder="Odpověz..." required style="flex-grow:1; padding:10px; border:1px solid #e2e8f0; border-radius:8px;">
                    <button type="submit" style="background:#2c3e50; padding: 10px 15px; border-radius:8px; color: white; border: none;">↪</button>
                </form>
                {% endif %}
            </div>
        {% endfor %}
    </div>

    <script>
        setInterval(function() {
            let active = document.activeElement;
            // Detekuje, jestli zrovna nepíšeš do formuláře
            let isTyping = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'PASSWORD');
            
            // Nepřenačítá data, pokud zrovna píšeš, nebo pokud máš rozkliknutý papírek přes půl obrazovky (isExpanded)
            if (!isTyping && !isExpanded) {
                // cache: no-store přikazuje prohlížeči, ať si nevymýšlí a stáhne čistá data ze serveru
                fetch(window.location.href, { cache: "no-store" })
                    .then(response => response.text())
                    .then(html => {
                        let parser = new DOMParser();
                        let doc = parser.parseFromString(html, 'text/html');
                        let newBoard = doc.getElementById('board-container');
                        let currentBoard = document.getElementById('board-container');
                        // Vymění nástěnku za novou, jen pokud se na ní něco změnilo
                        if (newBoard && currentBoard.innerHTML !== newBoard.innerHTML) {
                            currentBoard.innerHTML = newBoard.innerHTML;
                        }
                    }).catch(err => {});
            }
        }, 5000);
    </script>
</body>
</html>
"""


# ==========================================
# 6. ROUTOVÁNÍ (Co dělá jaká adresa webu)
# ==========================================

# Hlavní stránka (Načtení všech zpráv z databáze)
@app.route('/', methods=['GET'])
def home():
    error = request.args.get('error')
    try: 
        # Získání dat, řazení nejdřív podle PINu, pak podle času
        vzkazy_z_db = list(kolekce_vzkazu.find().sort([("is_pinned", -1), ("cas_vytvoreni", -1)]))
    except Exception: 
        vzkazy_z_db = []
    return render_template_string(HTML_MAIN, messages=vzkazy_z_db, error=error)

# Zpracování registrace a loginu
@app.route('/auth', methods=['POST'])
def auth():
    akce = request.form.get('action')
    username = request.form.get('username').strip()
    password = request.form.get('password')

    if not username or not password: return redirect('/?error=Vyplň jméno i heslo!')

    if akce == 'register':
        if kolekce_uzivatelu.find_one({"username": username}): return redirect('/?error=Jméno zabrané!')
        
        # Vytvoření admina (kdo první založí 'admin', je admin)
        role = 'admin' if username.lower() == 'admin' and not kolekce_uzivatelu.find_one({"role": "admin"}) else 'user'
        
        # POZOR: Pro školní účely ukládáme heslo v čistém textu, aby šlo číst v databázi!
        kolekce_uzivatelu.insert_one({"username": username, "password": password, "role": role})
        session['username'] = username; session['role'] = role
        
    elif akce == 'login':
        user = kolekce_uzivatelu.find_one({"username": username})
        # Kontrola hesla podle uloženého čistého textu
        if user and user['password'] == password:
            session['username'] = user['username']; session['role'] = user['role']
        else: return redirect('/?error=Špatné jméno nebo heslo!')
    return redirect('/')

# Odhlášení ze session
@app.route('/logout')
def logout(): session.clear(); return redirect('/')

# Zpracování "Přidat papírek"
@app.route('/add', methods=['POST'])
def add_note():
    if 'username' not in session: return redirect('/?error=Musíš být přihlášený!')

    post_type = request.form.get('post_type', 'normal')
    text = request.form.get('msg', '')
    
    note_id = uuid.uuid4().hex[:8] # Náhodné ID dokumentu
    new_note = {
        "id": note_id, "author": session['username'], "timestamp": datetime.now().strftime("%H:%M"),
        "cas_vytvoreni": datetime.now(), "replies": [], "reactions": {},
        "is_pinned": (request.form.get('is_important') == 'on' and session.get('role') == 'admin'),
        "type": post_type
    }

    # Podle post_type přidáme specifická data pro hry
    if post_type == 'normal':
        if not text: return redirect('/')
        file = request.files.get('image')
        new_note["text"] = text
        if file and file.filename: new_note["image"] = "data:" + file.content_type + ";base64," + base64.b64encode(file.read()).decode('utf-8')
        # Odchytnutí @AI
        if "@AI" in text.upper():
            ai_reply = ask_ai(text.replace("@AI", "").replace("@ai", "").strip() or "Ahoj.")
            new_note["replies"].append({"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")})
    
    elif post_type == 'duel':
        new_note["duel_state"] = "waiting"
        new_note["p1_move"] = request.form.get('duel_move', '🪨')
    
    elif post_type == 'dice':
        new_note["dice_state"] = "waiting"
        new_note["p1_roll"] = random.randint(1, 6) # Hod kostkou na serveru
        
    elif post_type == 'guess':
        new_note["guess_state"] = "active"
        new_note["secret_number"] = random.randint(1, 100) # Tajné číslo na serveru
        
    elif post_type == 'bomb':
        new_note["bomb_state"] = "active"
        new_note["cut_wires"] = []
        colors = ['red', 'blue', 'green', 'yellow']
        random.shuffle(colors)
        new_note["defuse_wire"] = colors[0] # Správný drát
        new_note["boom_wire"] = colors[1]   # Výbušný drát

    kolekce_vzkazu.insert_one(new_note)
    return redirect('/')

# ==========================================
# 7. LOGIKA HER
# ==========================================

@app.route('/play_duel', methods=['POST'])
def play_duel():
    if 'username' not in session: return redirect('/')
    duel = kolekce_vzkazu.find_one({"id": request.form.get('note_id'), "type": "duel", "duel_state": "waiting"})
    # Kontrola aby hráč nehrál proti sobě
    if duel and duel['author'] != session['username']:
        p1, p2 = duel['p1_move'], request.form.get('move')
        win = 'TIE' if p1 == p2 else duel['author'] if (p1=='🪨' and p2=='✂️') or (p1=='✂️' and p2=='📄') or (p1=='📄' and p2=='🪨') else session['username']
        kolekce_vzkazu.update_one({"id": duel['id']}, {"$set": {"duel_state": "finished", "p2": session['username'], "p2_move": p2, "winner": win}})
    return redirect('/')

@app.route('/play_dice', methods=['POST'])
def play_dice():
    if 'username' not in session: return redirect('/')
    dice = kolekce_vzkazu.find_one({"id": request.form.get('note_id'), "type": "dice", "dice_state": "waiting"})
    if dice and dice['author'] != session['username']:
        p1_roll, p2_roll = dice['p1_roll'], random.randint(1, 6)
        win = 'TIE' if p1_roll == p2_roll else dice['author'] if p1_roll > p2_roll else session['username']
        kolekce_vzkazu.update_one({"id": dice['id']}, {"$set": {"dice_state": "finished", "p2": session['username'], "p2_roll": p2_roll, "winner": win}})
    return redirect('/')

@app.route('/cut_wire', methods=['POST'])
def cut_wire():
    if 'username' not in session: return redirect('/')
    bomb = kolekce_vzkazu.find_one({"id": request.form.get('note_id'), "type": "bomb", "bomb_state": "active"})
    wire = request.form.get('wire_color')
    if bomb and wire not in bomb.get('cut_wires', []):
        state = "defused" if wire == bomb['defuse_wire'] else "exploded" if wire == bomb['boom_wire'] else "active"
        upd = {"$push": {"cut_wires": wire}}
        if state != "active": upd["$set"] = {"bomb_state": state, "hero": session['username']}
        kolekce_vzkazu.update_one({"id": bomb['id']}, upd)
    return redirect('/')

# ==========================================
# 8. ODPOVĚDI (A Robot pro hádání čísel)
# ==========================================
@app.route('/reply', methods=['POST'])
def add_reply():
    if 'username' not in session: return redirect('/')
    note_id, text = request.form.get('note_id'), request.form.get('reply_text')
    if not text or not note_id: return redirect('/')
    
    # 1. Normální přidání odpovědi
    kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": session['username'], "text": text, "timestamp": datetime.now().strftime("%H:%M")}}})
    
    msg = kolekce_vzkazu.find_one({"id": note_id})
    
    # 2. Reakce robota na Hádání čísla
    if msg.get('type') == 'guess' and msg.get('guess_state') == 'active':
        try:
            tip, tajne = int(text.strip()), msg['secret_number']
            if tip == tajne: 
                kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 Rozhodčí", "text": f"🎉 BINGO! {session['username']} uhodl(a) číslo {tajne}!", "timestamp": datetime.now().strftime("%H:%M")}}, "$set": {"guess_state": "finished"}})
            else:
                smer = "⬆️ víc" if tip < tajne else "⬇️ míň"
                kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 Rozhodčí", "text": f"{smer} než {tip}!", "timestamp": datetime.now().strftime("%H:%M")}}})
        except ValueError: pass # Ignoruje se, pokud uživatel napíše písmena
        
    # 3. Odpověď umělé inteligence
    elif msg.get('type') == 'normal' and "@AI" in text.upper():
        ai_reply = ask_ai(text.replace("@AI", "").replace("@ai", "").strip() or "Ahoj.")
        kolekce_vzkazu.update_one({"id": note_id}, {"$push": {"replies": {"author": "🤖 AI Asistent", "text": ai_reply, "timestamp": datetime.now().strftime("%H:%M")}}})
    return redirect('/')

# ==========================================
# 9. POMOCNÉ FUNKCE A DATABÁZE ADMINA
# ==========================================
@app.route('/delete', methods=['POST'])
def delete_note():
    if 'username' not in session: return redirect('/')
    vzkaz = kolekce_vzkazu.find_one({"id": request.form.get('note_id')})
    # Smazat může jen ten, kdo to vytvořil, nebo Admin
    if vzkaz and (vzkaz['author'] == session['username'] or session.get('role') == 'admin'): kolekce_vzkazu.delete_one({"id": vzkaz['id']})
    return redirect(request.referrer or '/')

@app.route('/react', methods=['POST'])
def react_note():
    emoji = request.form.get('emoji')
    # $inc znamená "Zvyš číslo o 1"
    if emoji in ['👍', '❤️', '😂', '😮']: kolekce_vzkazu.update_one({"id": request.form.get('note_id')}, {"$inc": {f"reactions.{emoji}": 1}})
    return redirect(request.referrer or '/')

@app.route('/admin-db')
def view_database():
    # Zabezpečení stránky!
    if session.get('role') != 'admin': return "<h1 style='color:red;'>Přístup odepřen! Nejsi admin.</h1>", 403
    
    html_db = """<!DOCTYPE html><html lang="cs"><head><meta charset="utf-8"><title>Tajný pohled</title><style>body { font-family: sans-serif; padding: 20px; background: #1e1e1e; color: #fff; } table { border-collapse: collapse; width: 100%; margin-bottom: 40px; background: #2d2d2d; box-shadow: 0 4px 8px rgba(0,0,0,0.5);} th, td { border: 1px solid #444; padding: 12px; text-align: left; vertical-align: top;} th { background: #3498db; color: #fff; font-size: 1.1em;} a.back { color: #fff; background: #e74c3c; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-bottom: 20px;} .comment-box { background: #1a1a1a; padding: 10px; border-radius: 5px; margin-top: 5px; font-size: 0.9em; border-left: 3px solid #3498db;}</style></head><body><h1>🕵️‍♂️ Databáze v MongoDB</h1><a href="/" class="back">⬅️ Zpět</a><h2>Kolekce: Uživatelé</h2><table><tr><th>Jméno</th><th>Role</th><th>Čisté heslo 🔑</th></tr>{% for u in uzivatele %}<tr><td><b>{{ u.username }}</b></td><td>{{ u.role }}</td><td style="color: #f1c40f; font-family: monospace; font-size: 1.1em;">{{ u.password }}</td></tr>{% endfor %}</table><h2>Kolekce: Vzkazy</h2><table><tr><th>Typ</th><th>Autor</th><th>Hlavní zpráva / Stav hry</th><th>Komentáře 💬</th></tr>{% for v in vzkazy %}<tr><td><span style="background: #555; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;">{{ v.type }}</span></td><td><b>{{ v.author }}</b></td><td>{% if v.text %}{{ v.text }}<br>{% endif %} {% if v.type == 'guess' %}<span style="color: #3498db;">Tajné číslo je: <b>{{ v.secret_number }}</b></span>{% endif %}</td><td>{% if v.replies %}{% for r in v.replies %}<div class="comment-box"><b style="color: #2ecc71;">{{ r.author }}</b> [{{ r.timestamp }}]: {{ r.text }}</div>{% endfor %}{% else %}<i style="color: #777;">Zatím bez komentářů</i>{% endif %}</td></tr>{% endfor %}</table></body></html>"""
    
    # Výpis dat přímo do tabulek
    return render_template_string(html_db, uzivatele=list(kolekce_uzivatelu.find()), vzkazy=list(kolekce_vzkazu.find().sort("cas_vytvoreni", -1)))

if __name__ == '__main__':
    # Spuštění aplikace
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
