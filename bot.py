“””
TPS67 — Bot Telegram + Serveur Mini App
“””

import os
import json
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# =====================

# CONFIGURATION

# =====================

BOT_TOKEN   = os.environ.get(“BOT_TOKEN”,   “VOTRE_TOKEN_ICI”)
WEBAPP_URL  = os.environ.get(“WEBAPP_URL”,  “https://votre-app.railway.app”)
ADMIN_CHAT_ID = os.environ.get(“ADMIN_CHAT_ID”, “”)

# =====================

# STORAGE

# =====================

DATA_FILE = “data.json”

def load_data():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
return {
“users”: [],
“products”: [],
“categories”: [“Premium”, “Classic”, “Limited”],
“orders”: [],
“settings”: {},
“start_buttons”: [],   # boutons configurés dans l’admin
“welcome_text”: “”     # texte de bienvenue configurable
}

def save_data(data):
with open(DATA_FILE, “w”, encoding=“utf-8”) as f:
json.dump(data, f, ensure_ascii=False, indent=2)

# =====================

# FLASK APP

# =====================

app = Flask(**name**, static_folder=”.”)

@app.route(”/”)
def index():
return send_from_directory(”.”, “index.html”)

@app.route(”/admin”)
def admin():
return send_from_directory(”.”, “admin.html”)

# — PRODUCTS —

@app.route(”/api/products”, methods=[“GET”])
def get_products():
data = load_data()
return jsonify({
“products”:   data.get(“products”, []),
“categories”: data.get(“categories”, [])
})

@app.route(”/api/products”, methods=[“POST”])
def add_product():
data = load_data()
product = request.json
product[“id”] = len(data[“products”]) + 1
data[“products”].append(product)
save_data(data)
return jsonify({“success”: True, “product”: product})

@app.route(”/api/products/<int:pid>”, methods=[“PUT”])
def update_product(pid):
data = load_data()
for i, p in enumerate(data[“products”]):
if p[“id”] == pid:
data[“products”][i] = {**p, **request.json}
save_data(data)
return jsonify({“success”: True})
return jsonify({“success”: False}), 404

@app.route(”/api/products/<int:pid>”, methods=[“DELETE”])
def delete_product(pid):
data = load_data()
data[“products”] = [p for p in data[“products”] if p[“id”] != pid]
save_data(data)
return jsonify({“success”: True})

# — CATEGORIES —

@app.route(”/api/categories”, methods=[“GET”])
def get_categories():
data = load_data()
return jsonify({“categories”: data.get(“categories”, [])})

@app.route(”/api/categories”, methods=[“POST”])
def add_category():
data = load_data()
cat = request.json.get(“name”, “”).strip()
if cat and cat not in data[“categories”]:
data[“categories”].append(cat)
save_data(data)
return jsonify({“success”: True, “categories”: data[“categories”]})

# — SETTINGS (nom boutique, tg username…) —

@app.route(”/api/settings”, methods=[“GET”])
def get_settings():
data = load_data()
return jsonify(data.get(“settings”, {}))

@app.route(”/api/settings”, methods=[“POST”])
def save_settings():
data = load_data()
data[“settings”] = request.json
save_data(data)
return jsonify({“success”: True})

# — INFO PAGE —

@app.route(”/api/info”, methods=[“GET”])
def get_info():
data = load_data()
return jsonify(data.get(“info”, {}))

@app.route(”/api/info”, methods=[“POST”])
def save_info():
data = load_data()
data[“info”] = request.json
save_data(data)
return jsonify({“success”: True})

# — BOUTONS /START —

@app.route(”/api/start-buttons”, methods=[“GET”])
def get_start_buttons():
data = load_data()
return jsonify({
“buttons”:      data.get(“start_buttons”, []),
“welcome_text”: data.get(“welcome_text”, “”)
})

@app.route(”/api/start-buttons”, methods=[“POST”])
def save_start_buttons():
data = load_data()
data[“start_buttons”] = request.json.get(“buttons”, [])
data[“welcome_text”]  = request.json.get(“welcome_text”, “”)
save_data(data)
return jsonify({“success”: True})

# — BROADCAST —

@app.route(”/api/broadcast”, methods=[“POST”])
def broadcast():
data    = load_data()
message = request.json.get(“message”, “”)
if not message:
return jsonify({“success”: False, “error”: “Message vide”})

```
users = data.get("users", [])
sent  = 0

import asyncio
from telegram import Bot

async def send_all():
    nonlocal sent
    bot = Bot(token=BOT_TOKEN)
    for uid in users:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"📣 *TPS67*\n\n{message}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception as e:
            logging.warning(f"Erreur envoi {uid}: {e}")

asyncio.run(send_all())
return jsonify({"success": True, "sent": sent})
```

@app.route(”/api/users/count”, methods=[“GET”])
def user_count():
data = load_data()
return jsonify({“count”: len(data.get(“users”, []))})

# =====================

# HELPERS BOT

# =====================

def build_keyboard(start_buttons):
“””
Construit le clavier inline depuis la config admin.
Chaque bouton a : label, type (miniapp | url), value, emoji
Les boutons sont groupés par paires sur la même ligne si side_by_side=True
“””
if not start_buttons:
return InlineKeyboardMarkup([[
InlineKeyboardButton(“🛍️ Boutique TPS67”, web_app=WebAppInfo(url=WEBAPP_URL))
]])

```
rows = []
i = 0
while i < len(start_buttons):
    btn = start_buttons[i]
    label = f"{btn.get('emoji','')} {btn.get('label','Bouton')}".strip()

    if btn.get("type") == "miniapp":
        tg_btn = InlineKeyboardButton(label, web_app=WebAppInfo(url=WEBAPP_URL))
    else:
        url = btn.get("value", "https://t.me/")
        if not url.startswith("http"):
            url = f"https://t.me/{url.lstrip('@')}"
        tg_btn = InlineKeyboardButton(label, url=url)

    # Regrouper sur la même ligne si le suivant est "side_by_side"
    next_btn = start_buttons[i + 1] if i + 1 < len(start_buttons) else None
    if next_btn and next_btn.get("side_by_side"):
        next_label = f"{next_btn.get('emoji','')} {next_btn.get('label','')}".strip()
        if next_btn.get("type") == "miniapp":
            tg_next = InlineKeyboardButton(next_label, web_app=WebAppInfo(url=WEBAPP_URL))
        else:
            nurl = next_btn.get("value", "https://t.me/")
            if not nurl.startswith("http"):
                nurl = f"https://t.me/{nurl.lstrip('@')}"
            tg_next = InlineKeyboardButton(next_label, url=nurl)
        rows.append([tg_btn, tg_next])
        i += 2
    else:
        rows.append([tg_btn])
        i += 1

return InlineKeyboardMarkup(rows)
```

# =====================

# BOT HANDLERS

# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
data = load_data()

```
# Enregistrer l'utilisateur
if user.id not in data["users"]:
    data["users"].append(user.id)
    save_data(data)

# Texte de bienvenue personnalisé ou par défaut
welcome = data.get("welcome_text", "").strip()
if not welcome:
    shop_name = data.get("settings", {}).get("shopName", "TPS67")
    welcome = (
        f"👋 Bienvenue *{user.first_name}* !\n\n"
        f"🏪 *{shop_name}*\n\n"
        f"Découvre notre catalogue complet 👇"
    )

keyboard = build_keyboard(data.get("start_buttons", []))

await update.message.reply_text(
    welcome,
    parse_mode="Markdown",
    reply_markup=keyboard
)
```

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
text = update.message.text
data = load_data()

```
# Notifier l'admin si ça ressemble à une commande
if any(w in text.lower() for w in ["commander", "commande", "order", "achat"]):
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🛒 *Nouvelle commande !*\n\n"
                    f"👤 {user.first_name} (@{user.username or 'N/A'})\n"
                    f"🆔 `{user.id}`\n\n"
                    f"📝 {text}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Erreur admin notif: {e}")

    await update.message.reply_text(
        "✅ *Message reçu !*\n\nNous te répondons très vite. Merci 🙏",
        parse_mode="Markdown"
    )
else:
    keyboard = build_keyboard(data.get("start_buttons", []))
    await update.message.reply_text(
        "👇 Accède à notre boutique ici :",
        reply_markup=keyboard
    )
```

async def error_handler(update, context):
logging.error(f”Erreur bot: {context.error}”)

# =====================

# MAIN

# =====================

def run_flask():
port = int(os.environ.get(“PORT”, 8080))
app.run(host=“0.0.0.0”, port=port, debug=False)

def run_bot():
logging.basicConfig(level=logging.INFO)
tg_app = Application.builder().token(BOT_TOKEN).build()
tg_app.add_handler(CommandHandler(“start”, start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg_app.add_error_handler(error_handler)
logging.info(“✅ Bot TPS67 démarré !”)
tg_app.run_polling(drop_pending_updates=True)

if **name** == “**main**”:
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
run_bot()
