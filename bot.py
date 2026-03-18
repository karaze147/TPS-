import os
import json
import logging
import asyncio
from flask import Flask, request, jsonify, send_from_directory
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN   = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL  = os.environ.get('WEBAPP_URL', '')          # URL de ta mini app (Railway)
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')         # URL publique du serveur + /webhook
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
DATA_FILE   = 'data.json'
PORT        = int(os.environ.get('PORT', 8080))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# DATA
# ============================================================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': [],
        'products': [],
        'categories': ['Premium', 'Classic', 'Limited'],
        'settings': {
            'tgUsername': '',
            'tgBtnText': 'Commander sur Telegram',
            'shopName': 'TPS67',
            'shopSub': 'Boutique officielle'
        },
        'info': {'desc': '', 'hours': '', 'slogan': '', 'socials': []},
        'start_buttons': [],
        'welcome_text': ''
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# ---------- PRODUCTS ----------
@app.route('/api/products', methods=['GET'])
def get_products():
    data = load_data()
    return jsonify({
        'products': data.get('products', []),
        'categories': data.get('categories', [])
    })

@app.route('/api/products', methods=['POST'])
def add_product():
    data = load_data()
    product = request.json
    existing_ids = [p.get('id', 0) for p in data['products']]
    product['id'] = max(existing_ids, default=0) + 1
    data['products'].append(product)
    save_data(data)
    return jsonify({'success': True, 'id': product['id']})

@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = load_data()
    for i, p in enumerate(data['products']):
        if p.get('id') == pid:
            data['products'][i] = {**p, **request.json, 'id': pid}
            save_data(data)
            return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Produit introuvable'}), 404

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    data = load_data()
    data['products'] = [p for p in data['products'] if p.get('id') != pid]
    save_data(data)
    return jsonify({'success': True})

# ---------- CATEGORIES ----------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    data = load_data()
    return jsonify({'categories': data.get('categories', [])})

@app.route('/api/categories', methods=['POST'])
def add_category():
    data = load_data()
    cat = request.json.get('name', '').strip()
    if not cat:
        return jsonify({'success': False, 'error': 'Nom vide'}), 400
    if cat not in data['categories']:
        data['categories'].append(cat)
        save_data(data)
    return jsonify({'success': True})

@app.route('/api/categories/<string:name>', methods=['DELETE'])
def delete_category(name):
    data = load_data()
    data['categories'] = [c for c in data['categories'] if c != name]
    save_data(data)
    return jsonify({'success': True})

# ---------- SETTINGS ----------
@app.route('/api/settings', methods=['GET'])
def get_settings():
    data = load_data()
    return jsonify(data.get('settings', {}))

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = load_data()
    data['settings'] = request.json
    save_data(data)
    return jsonify({'success': True})

# ---------- INFO ----------
@app.route('/api/info', methods=['GET'])
def get_info():
    data = load_data()
    return jsonify(data.get('info', {}))

@app.route('/api/info', methods=['POST'])
def save_info():
    data = load_data()
    data['info'] = request.json
    save_data(data)
    return jsonify({'success': True})

# ---------- START BUTTONS ----------
@app.route('/api/start-buttons', methods=['GET'])
def get_start_buttons():
    data = load_data()
    return jsonify({
        'buttons': data.get('start_buttons', []),
        'welcome_text': data.get('welcome_text', '')
    })

@app.route('/api/start-buttons', methods=['POST'])
def save_start_buttons():
    data = load_data()
    data['start_buttons'] = request.json.get('buttons', [])
    data['welcome_text']  = request.json.get('welcome_text', '')
    save_data(data)
    return jsonify({'success': True})

# ---------- BROADCAST ----------
@app.route('/api/broadcast', methods=['POST'])
def broadcast():
    data = load_data()
    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'error': 'Message vide'}), 400
    if not BOT_TOKEN:
        return jsonify({'success': False, 'error': 'BOT_TOKEN manquant'}), 500

    users = data.get('users', [])
    sent = 0
    failed = 0

    async def send_all():
        nonlocal sent, failed
        bot = Bot(token=BOT_TOKEN)
        for uid in users:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=f'📣 *TPS67*\n\n{message}',
                    parse_mode='Markdown'
                )
                sent += 1
            except Exception as e:
                logger.warning(f'Broadcast failed for {uid}: {e}')
                failed += 1

    asyncio.run(send_all())
    return jsonify({'success': True, 'sent': sent, 'failed': failed})

# ---------- USERS ----------
@app.route('/api/users/count', methods=['GET'])
def user_count():
    data = load_data()
    return jsonify({'count': len(data.get('users', []))})

# ============================================================
# TELEGRAM BOT HANDLERS
# ============================================================
def build_keyboard(start_buttons, webapp_url):
    """Construit le clavier inline depuis la config admin."""
    if not start_buttons:
        if webapp_url:
            return InlineKeyboardMarkup([[
                InlineKeyboardButton('🛍️ Boutique TPS67', web_app=WebAppInfo(url=webapp_url))
            ]])
        return None

    rows = []
    i = 0
    while i < len(start_buttons):
        btn = start_buttons[i]
        label = (btn.get('emoji', '') + ' ' + btn.get('label', 'Bouton')).strip()

        def make_button(b, lbl):
            if b.get('type') == 'miniapp' and webapp_url:
                return InlineKeyboardButton(lbl, web_app=WebAppInfo(url=webapp_url))
            val = b.get('value', '').strip()
            if not val.startswith('http'):
                val = 'https://t.me/' + val.lstrip('@')
            return InlineKeyboardButton(lbl, url=val)

        tg_btn = make_button(btn, label)
        next_btn = start_buttons[i + 1] if i + 1 < len(start_buttons) else None

        if next_btn and next_btn.get('side_by_side'):
            next_label = (next_btn.get('emoji', '') + ' ' + next_btn.get('label', '')).strip()
            tg_next = make_button(next_btn, next_label)
            rows.append([tg_btn, tg_next])
            i += 2
        else:
            rows.append([tg_btn])
            i += 1

    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()

    # Enregistrer l'utilisateur
    if user.id not in data['users']:
        data['users'].append(user.id)
        save_data(data)
        logger.info(f'Nouvel utilisateur: {user.first_name} ({user.id})')

    # Message de bienvenue
    welcome = data.get('welcome_text', '').strip()
    if not welcome:
        shop_name = data.get('settings', {}).get('shopName', 'TPS67')
        welcome = (
            f'👋 Bienvenue *{user.first_name}* !\n\n'
            f'🏪 *{shop_name}*\n\n'
            f'Découvre notre catalogue en cliquant ci-dessous 👇'
        )

    keyboard = build_keyboard(data.get('start_buttons', []), WEBAPP_URL)

    await update.message.reply_text(
        welcome,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

    # Notifier l'admin d'un nouvel utilisateur
    if ADMIN_CHAT_ID and user.id not in data['users'][:-1]:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f'👤 Nouvel utilisateur : {user.first_name} (@{user.username or "—"})\nID: `{user.id}`',
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f'Notif admin failed: {e}')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    data = load_data()

    # Enregistrer si pas encore connu
    if user.id not in data['users']:
        data['users'].append(user.id)
        save_data(data)

    # Détection de commande
    keywords_order = ['commander', 'commande', 'order', 'acheter', 'prix', 'tarif']
    if any(w in text.lower() for w in keywords_order):
        # Notifier l'admin
        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f'🛒 *Nouvelle demande de commande !*\n\n'
                        f'👤 {user.first_name} (@{user.username or "—"})\n'
                        f'🆔 `{user.id}`\n\n'
                        f'💬 {text}'
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f'Admin notif error: {e}')

        await update.message.reply_text(
            '✅ Message reçu ! Nous te répondons très vite. 🚀'
        )
    else:
        keyboard = build_keyboard(data.get('start_buttons', []), WEBAPP_URL)
        await update.message.reply_text(
            '🛍️ Accède à notre boutique :',
            reply_markup=keyboard
        )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /admin — ouvre le panel uniquement pour l'admin."""
    user = update.effective_user
    if not ADMIN_CHAT_ID or str(user.id) != str(ADMIN_CHAT_ID).strip():
        await update.message.reply_text('⛔ Accès refusé.')
        return

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('🔐 Panel Admin', web_app=WebAppInfo(url=WEBAPP_URL + '/admin'))
    ]])
    await update.message.reply_text(
        '👋 Bienvenue dans le panel admin !',
        reply_markup=keyboard
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /stats — statistiques rapides pour l'admin."""
    user = update.effective_user
    if not ADMIN_CHAT_ID or str(user.id) != str(ADMIN_CHAT_ID).strip():
        await update.message.reply_text('⛔ Accès refusé.')
        return

    data = load_data()
    nb_users    = len(data.get('users', []))
    nb_products = len(data.get('products', []))
    nb_cats     = len(data.get('categories', []))
    shop_name   = data.get('settings', {}).get('shopName', 'TPS67')

    await update.message.reply_text(
        f'📊 *Stats {shop_name}*\n\n'
        f'👥 Utilisateurs : *{nb_users}*\n'
        f'📦 Produits : *{nb_products}*\n'
        f'🗂️ Catégories : *{nb_cats}*',
        parse_mode='Markdown'
    )

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Bot error: {context.error}', exc_info=context.error)


# ============================================================
# WEBHOOK ENDPOINT
# ============================================================
tg_app = None

@app.route('/webhook', methods=['POST'])
def webhook():
    """Reçoit les updates Telegram via webhook."""
    global tg_app
    if not tg_app:
        return jsonify({'error': 'Bot non initialisé'}), 500

    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run(tg_app.process_update(update))
    return jsonify({'ok': True})

@app.route('/api/set-webhook', methods=['GET'])
def set_webhook():
    """Route utilitaire pour enregistrer le webhook Telegram."""
    if not BOT_TOKEN or not WEBHOOK_URL:
        return jsonify({'error': 'BOT_TOKEN ou WEBHOOK_URL manquant'}), 400

    async def _set():
        bot = Bot(token=BOT_TOKEN)
        result = await bot.set_webhook(url=WEBHOOK_URL + '/webhook')
        info = await bot.get_webhook_info()
        return result, str(info)

    ok, info = asyncio.run(_set())
    return jsonify({'success': ok, 'info': info})

@app.route('/api/webhook-info', methods=['GET'])
def webhook_info():
    """Infos sur le webhook actuel."""
    async def _info():
        bot = Bot(token=BOT_TOKEN)
        return await bot.get_webhook_info()
    info = asyncio.run(_info())
    return jsonify({'url': info.url, 'pending': info.pending_update_count})

# ============================================================
# INIT BOT
# ============================================================
def init_bot():
    global tg_app
    if not BOT_TOKEN:
        logger.warning('BOT_TOKEN non défini — bot désactivé')
        return

    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler('start', start))
    tg_app.add_handler(CommandHandler('admin', admin_command))
    tg_app.add_handler(CommandHandler('stats', stats_command))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    tg_app.add_error_handler(error_handler)

    async def _init():
        await tg_app.initialize()
        # Enregistrer le webhook automatiquement si WEBHOOK_URL défini
        if WEBHOOK_URL:
            bot = Bot(token=BOT_TOKEN)
            await bot.set_webhook(url=WEBHOOK_URL + '/webhook')
            logger.info(f'Webhook enregistré : {WEBHOOK_URL}/webhook')
        else:
            logger.warning('WEBHOOK_URL non défini — webhook non enregistré')

    asyncio.run(_init())
    logger.info('Bot TPS67 initialisé ✅')

# ============================================================
# ENTRYPOINT
# ============================================================
if __name__ == '__main__':
    init_bot()
    app.run(host='0.0.0.0', port=PORT, debug=False)
