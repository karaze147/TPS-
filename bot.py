import os
import json
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get(“BOT_TOKEN”, “”)
WEBAPP_URL = os.environ.get(“WEBAPP_URL”, “https://tps67.onrender.com”)
ADMIN_CHAT_ID = os.environ.get(“ADMIN_CHAT_ID”, “”)

DATA_FILE = “data.json”

def load_data():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
return {“users”: [], “products”: [], “categories”: [], “orders”: [], “settings”: {}, “start_buttons”: [], “welcome_text”: “”}

def save_data(data):
with open(DATA_FILE, “w”, encoding=“utf-8”) as f:
json.dump(data, f, ensure_ascii=False, indent=2)

app = Flask(**name**, static_folder=”.”)

@app.route(”/”)
def index():
return send_from_directory(”.”, “index.html”)

@app.route(”/admin”)
def admin():
return send_from_directory(”.”, “admin.html”)

@app.route(”/api/products”, methods=[“GET”])
def get_products():
data = load_data()
return jsonify({“products”: data.get(“products”, []), “categories”: data.get(“categories”, [])})

@app.route(”/api/products”, methods=[“POST”])
def add_product():
data = load_data()
product = request.json
product[“id”] = len(data[“products”]) + 1
data[“products”].append(product)
save_data(data)
return jsonify({“success”: True})

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
return jsonify({“success”: True})

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

@app.route(”/api/start-buttons”, methods=[“GET”])
def get_start_buttons():
data = load_data()
return jsonify({“buttons”: data.get(“start_buttons”, []), “welcome_text”: data.get(“welcome_text”, “”)})

@app.route(”/api/start-buttons”, methods=[“POST”])
def save_start_buttons():
data = load_data()
data[“start_buttons”] = request.json.get(“buttons”, [])
data[“welcome_text”] = request.json.get(“welcome_text”, “”)
save_data(data)
return jsonify({“success”: True})

@app.route(”/api/broadcast”, methods=[“POST”])
def broadcast():
data = load_data()
message = request.json.get(“message”, “”)
if not message:
return jsonify({“success”: False})
users = data.get(“users”, [])
sent = 0
import asyncio
from telegram import Bot
async def send_all():
nonlocal sent
bot = Bot(token=BOT_TOKEN)
for uid in users:
try:
await bot.send_message(chat_id=uid, text=“TPS67\n\n” + message)
sent += 1
except Exception as e:
logging.warning(str(e))
asyncio.run(send_all())
return jsonify({“success”: True, “sent”: sent})

@app.route(”/api/users/count”, methods=[“GET”])
def user_count():
data = load_data()
return jsonify({“count”: len(data.get(“users”, []))})

def build_keyboard(start_buttons):
if not start_buttons:
return InlineKeyboardMarkup([[InlineKeyboardButton(“Boutique TPS67”, web_app=WebAppInfo(url=WEBAPP_URL))]])
rows = []
i = 0
while i < len(start_buttons):
btn = start_buttons[i]
label = (btn.get(“emoji”, “”) + “ “ + btn.get(“label”, “Bouton”)).strip()
if btn.get(“type”) == “miniapp”:
tg_btn = InlineKeyboardButton(label, web_app=WebAppInfo(url=WEBAPP_URL))
else:
url = btn.get(“value”, “”)
if not url.startswith(“http”):
url = “https://t.me/” + url.lstrip(”@”)
tg_btn = InlineKeyboardButton(label, url=url)
next_btn = start_buttons[i + 1] if i + 1 < len(start_buttons) else None
if next_btn and next_btn.get(“side_by_side”):
next_label = (next_btn.get(“emoji”, “”) + “ “ + next_btn.get(“label”, “”)).strip()
if next_btn.get(“type”) == “miniapp”:
tg_next = InlineKeyboardButton(next_label, web_app=WebAppInfo(url=WEBAPP_URL))
else:
nurl = next_btn.get(“value”, “”)
if not nurl.startswith(“http”):
nurl = “https://t.me/” + nurl.lstrip(”@”)
tg_next = InlineKeyboardButton(next_label, url=nurl)
rows.append([tg_btn, tg_next])
i += 2
else:
rows.append([tg_btn])
i += 1
return InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
data = load_data()
if user.id not in data[“users”]:
data[“users”].append(user.id)
save_data(data)
welcome = data.get(“welcome_text”, “”).strip()
if not welcome:
name = data.get(“settings”, {}).get(“shopName”, “TPS67”)
welcome = “Bienvenue “ + user.first_name + “ !\n\n” + name + “\n\nDecouvre notre catalogue complet”
keyboard = build_keyboard(data.get(“start_buttons”, []))
await update.message.reply_text(welcome, reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
text = update.message.text
data = load_data()
if any(w in text.lower() for w in [“commander”, “commande”, “order”]):
if ADMIN_CHAT_ID:
try:
await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=“Nouvelle commande !\n\n” + user.first_name + “ (@” + (user.username or “N/A”) + “)\n\n” + text)
except Exception as e:
logging.error(str(e))
await update.message.reply_text(“Message recu ! Nous te repondons tres vite.”)
else:
keyboard = build_keyboard(data.get(“start_buttons”, []))
await update.message.reply_text(“Acces a notre boutique :”, reply_markup=keyboard)

async def error_handler(update, context):
logging.error(str(context.error))

def run_flask():
port = int(os.environ.get(“PORT”, 8080))
app.run(host=“0.0.0.0”, port=port, debug=False)

def run_bot():
logging.basicConfig(level=logging.INFO)
tg_app = Application.builder().token(BOT_TOKEN).build()
tg_app.add_handler(CommandHandler(“start”, start))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg_app.add_error_handler(error_handler)
logging.info(“Bot TPS67 demarre !”)
tg_app.run_polling(drop_pending_updates=True)

if **name** == “**main**”:
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
run_bot()
