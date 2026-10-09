import os
import json
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN_KIRITING")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- DATABASE ---
def get_db():
    conn = sqlite3.connect("syrexa.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        balance INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'uz'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_key TEXT,
        name TEXT,
        price INTEGER,
        badge TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        price INTEGER,
        player_id TEXT,
        status TEXT DEFAULT 'Kutilmoqda'
    )""")

    # Standart sozlamalar
    defaults = [
        ("brand", "Syrexa"),
        ("card_uzcard", "8600 0000 0000 0000"),
        ("card_uzcard_holder", "SYREXA PAY"),
        ("card_humo", "9860 0000 0000 0000"),
        ("card_humo_holder", "SYREXA PAY"),
        ("channel", "@syrexa"),
        ("support_url", "https://t.me/syrexa_support"),
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Standart o'yin paketlari (PUBG & Free Fire)
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        packages = [
            # PUBG Mobile UC
            ("pubg", "60 UC", 13000, "⚡ Tezkor"),
            ("pubg", "325 UC", 65000, "🔥 Mashhur"),
            ("pubg", "660 UC", 125000, "💎 Tavsiya"),
            ("pubg", "1800 UC", 320000, "VIP"),
            ("pubg", "3850 UC", 640000, "PRO"),
            ("pubg", "8100 UC", 1280000, "MAX"),
            # Free Fire Almaz
            ("freefire", "100 + 10 Almaz", 14000, "⚡"),
            ("freefire", "310 + 31 Almaz", 42000, "🔥 Mashhur"),
            ("freefire", "520 + 52 Almaz", 70000, "💎 Tavsiya"),
            ("freefire", "1060 + 106 Almaz", 138000, "VIP"),
            ("freefire", "2180 + 218 Almaz", 275000, "MAX")
        ]
        c.executemany("INSERT INTO products (game_key, name, price, badge) VALUES (?, ?, ?, ?)", packages)

    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else ""

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# --- BOT HANDLERS ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    fname = message.from_user.first_name
    uname = message.from_user.username or ""

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (uid, fname, uname))
    conn.commit()
    conn.close()

    web_url = f"{BASE_URL}/?user_id={uid}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Ilovani ochish", web_app=WebAppInfo(url=web_url))],
        [
            InlineKeyboardButton(text="📢 Bizning kanal", url=f"https://t.me/{get_setting('channel').replace('@', '')}"),
            InlineKeyboardButton(text="💬 Qo'llab-quvvatlash", url=get_setting("support_url"))
        ]
    ])

    await message.answer(
        f"Xush kelibsiz, <b>{fname}</b>!\n\n"
        f"<b>Syrexa</b> do'koni orqali o'yinlarga eng arzon va tezkor to'lovlarni amalga oshiring.",
        reply_markup=kb,
        parse_mode="HTML"
    )

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    u_count, total_bal = c.fetchone()
    conn.close()

    text = (
        f"⚙️ <b>SYREXA ADMIN BOSHQARUV PANELI</b>\n\n"
        f"👥 Foydalanuvchilar soni: <b>{u_count} ta</b>\n"
        f"💰 Umumiy balans: <b>{total_bal or 0:,} so'm</b>\n"
        f"💳 Uzcard: <code>{get_setting('card_uzcard')}</code> ({get_setting('card_uzcard_holder')})\n"
        f"💳 Humo: <code>{get_setting('card_humo')}</code> ({get_setting('card_humo_holder')})\n"
        f"📢 Kanal: <b>{get_setting('channel')}</b>\n\n"
        f"<b>Boshqaruv buyruqlari:</b>\n"
        f"• <code>/balans [user_id] [summa]</code> — Foydalanuvchi balansini oshirish/kamaytirish (masalan: <code>/balans 123456789 50000</code>)\n"
        f"• <code>/uzcard [raqam] [F.I.O]</code> — Uzcard kartasini o'zgartirish\n"
        f"• <code>/humo [raqam] [F.I.O]</code> — Humo kartasini o'zgartirish\n"
        f"• <code>/kanal @kanal_nomi</code> — Majburiy kanalni yangilash\n"
        f"• <code>/addprice [pubg/freefire] [nomi] [narxi]</code> — Yangi paket qo'shish"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text.startswith("/balans"))
async def adm_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) == 3:
        uid, amount = int(parts[1]), int(parts[2])
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
        conn.commit()
        conn.close()
        await message.answer(f"✅ User {uid} balansiga {amount:,} so'm qo'shildi/ayirildi.")

@dp.message(F.text.startswith("/uzcard"))
async def adm_uzcard(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        set_setting("card_uzcard", parts[1])
        set_setting("card_uzcard_holder", parts[2])
        await message.answer("✅ Uzcard ma'lumotlari yangilandi!")

@dp.message(F.text.startswith("/humo"))
async def adm_humo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        set_setting("card_humo", parts[1])
        set_setting("card_humo_holder", parts[2])
        await message.answer("✅ Humo ma'lumotlari yangilandi!")

@dp.message(F.text.startswith("/kanal"))
async def adm_kanal(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) == 2:
        set_setting("channel", parts[1])
        await message.answer(f"✅ Kanal yangilandi: {parts[1]}")

# --- API BUYURTMA QABUL QILISH ---
async def api_order(request):
    data = await request.json()
    uid = data.get("user_id")
    price = data.get("price")
    title = data.get("title")
    player_id = data.get("player_id")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    user = c.fetchone()
    if not user or user["balance"] < price:
        conn.close()
        return web.json_response({"ok": False, "msg": "Mablag' yetarli emas!"})

    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, uid))
    c.execute("INSERT INTO orders (user_id, title, price, player_id) VALUES (?, ?, ?, ?)", (uid, title, price, player_id))
    order_id = c.lastrowid
    conn.commit()
    conn.close()

    # Adminga xabar berish
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🛒 <b>Yangi xarid #{order_id}!</b>\n\n"
            f"👤 Foydalanuvchi ID: <code>{uid}</code>\n"
            f"📦 Mahsulot: <b>{title}</b>\n"
            f"💰 Narxi: <b>{price:,} so'm</b>\n"
            f"🎯 Player ID: <code>{player_id}</code>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    return web.json_response({"ok": True, "msg": "Buyurtmangiz qabul qilindi!"})

# --- MINI APP WEB INTERFEYSI (PAYERPIN 1:1 KLONI) ---
async def webapp_handler(request):
    user_id = request.query.get("user_id", "0")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    balance = u["balance"] if u else 0
    first_name = u["first_name"] if u else "Foydalanuvchi"

    c.execute("SELECT * FROM products")
    products = [dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
    user_orders = [dict(row) for row in c.fetchall()]
    conn.close()

    card_uzcard = get_setting("card_uzcard")
    card_uzcard_holder = get_setting("card_uzcard_holder")
    card_humo = get_setting("card_humo")
    card_humo_holder = get_setting("card_humo_holder")

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Syrexa</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {{
            --bg-dark: #0a0c16;
            --panel-bg: #141729;
            --card-bg: #181c33;
            --card-border: #232948;
            --primary-purple: #6c5ce7;
            --primary-gradient: linear-gradient(135deg, #7053ff 0%, #4a28d9 100%);
            --text-main: #ffffff;
            --text-muted: #8b92b2;
            --accent-green: #00e676;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; user-select: none; }}
        body {{ background-color: var(--bg-dark); color: var(--text-main); padding-bottom: 85px; }}

        /* TEPADAGI PANEL */
        .top-nav {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; }}
        .user-greeting {{ display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }}
        .user-greeting span {{ color: #ffd166; }}
        .lang-switch {{ background: #1c213d; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; color: #a5b4fc; border: 1px solid var(--card-border); }}

        /* BALANS BLOKI (PAYERPIN USLUBI) */
        .balance-container {{ background: linear-gradient(180deg, #181d38 0%, #121528 100%); margin: 8px 16px 14px; border-radius: 18px; padding: 16px 18px; border: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
        .bal-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600; display: flex; align-items: center; gap: 6px; }}
        .bal-value {{ font-size: 24px; font-weight: 800; color: #fff; margin-top: 4px; }}
        .bal-value span {{ font-size: 14px; color: var(--text-muted); font-weight: 600; }}
        .btn-deposit {{ background: var(--primary-gradient); color: #fff; border: none; padding: 10px 18px; border-radius: 12px; font-weight: 700; font-size: 13px; cursor: pointer; box-shadow: 0 4px 14px rgba(112, 83, 255, 0.4); }}

        /* 2 TA TUGMA: PROMOKOD VA SUPPORT */
        .quick-actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0 16px 14px; }}
        .action-card {{ background: #151930; border: 1px solid var(--card-border); border-radius: 14px; padding: 12px; display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 600; cursor: pointer; }}

        /* ASOSIY BANNER (NEON DISK) */
        .main-banner {{ margin: 0 16px 18px; border-radius: 18px; background: linear-gradient(135deg, #2b1154 0%, #150f38 100%); border: 1px solid #4a2b91; padding: 18px; position: relative; overflow: hidden; text-align: center; }}
        .main-banner h3 {{ font-size: 18px; font-weight: 900; color: #fff; letter-spacing: 0.5px; text-shadow: 0 0 12px rgba(255,255,255,0.3); }}
        .main-banner p {{ font-size: 12px; color: #c4b5fd; margin-top: 4px; font-weight: 600; }}

        /* BO'LIM SARLAVHASI */
        .section-header {{ display: flex; justify-content: space-between; align-items: center; padding: 0 16px 12px; }}
        .section-header h4 {{ font-size: 15px; font-weight: 700; color: #fff; }}
        .section-header a {{ font-size: 12px; color: #818cf8; text-decoration: none; font-weight: 600; }}

        /* O'YINLAR TO'RI (PayerPin o'yinlari) */
        .games-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 0 16px; margin-bottom: 24px; }}
        .game-item {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 8px 6px; text-align: center; cursor: pointer; transition: 0.2s; }}
        .game-item:active {{ transform: scale(0.94); }}
        .game-thumb {{ width: 100%; aspect-ratio: 1/1; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 26px; margin-bottom: 6px; }}
        .game-item .title {{ font-size: 11px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

        /* PAKETLAR MODALI / BO'LIMI */
        .packages-view {{ display: none; padding: 0 16px; }}
        .packages-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .pack-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px; text-align: center; cursor: pointer; transition: 0.2s; position: relative; }}
        .pack-card:active {{ transform: scale(0.96); border-color: var(--primary-purple); }}
        .pack-badge {{ position: absolute; top: 6px; right: 6px; font-size: 9px; background: #312e81; color: #a5b4fc; padding: 2px 6px; border-radius: 8px; font-weight: 700; }}
        .pack-title {{ font-size: 15px; font-weight: 800; margin-top: 6px; }}
        .pack-price {{ font-size: 13px; font-weight: 700; color: var(--accent-green); margin-top: 4px; }}

        /* TO'LOV BO'LIMI (POPOLNENIYE) */
        .pay-view {{ display: none; padding: 0 16px; }}
        .pay-methods {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
        .method-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 14px; cursor: pointer; text-align: left; }}
        .method-card.active {{ border-color: var(--primary-purple); background: #1c2242; }}
        .method-card h5 {{ font-size: 13px; font-weight: 800; }}
        .method-card span {{ font-size: 10px; color: var(--text-muted); }}

        .pay-box {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 16px; margin-top: 12px; }}
        .card-num-box {{ background: #0c0e18; border: 1px dashed #3a4266; border-radius: 12px; padding: 12px; font-family: monospace; font-size: 16px; color: #00e676; display: flex; justify-content: space-between; align-items: center; margin: 10px 0; }}

        /* BUYURTMALAR ROYXATI */
        .orders-view {{ display: none; padding: 0 16px; }}
        .order-row {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 12px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}

        /* PASTKI NAVIGATSIYA (PAYERPIN 5 TA TUGMA) */
        .bottom-bar {{ position: fixed; bottom: 0; left: 0; right: 0; height: 68px; background: #101323; border-top: 1px solid var(--card-border); display: flex; justify-content: space-around; align-items: center; z-index: 999; }}
        .bar-item {{ display: flex; flex-direction: column; align-items: center; gap: 3px; font-size: 10px; color: var(--text-muted); font-weight: 600; cursor: pointer; }}
        .bar-item.active {{ color: var(--primary-purple); }}
        .bar-item svg {{ width: 20px; height: 20px; fill: currentColor; }}

        /* MODAL */
        .modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; align-items: center; justify-content: center; padding: 20px; }}
        .modal-body {{ background: #171b30; border: 1px solid var(--card-border); border-radius: 20px; padding: 20px; width: 100%; max-width: 320px; text-align: center; }}
        .modal-body input {{ width: 100%; padding: 12px; background: #0c0f1c; border: 1px solid var(--card-border); border-radius: 10px; color: #fff; margin: 12px 0; font-size: 14px; outline: none; }}
        .modal-btn {{ width: 100%; background: var(--primary-gradient); color: #fff; border: none; padding: 12px; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; }}
    </style>
</head>
<body>

    <!-- ASOSIY SAHIFA -->
    <div id="view-home">
        <div class="top-nav">
            <div class="user-greeting">
                <span>👋</span> Привет, {first_name}
            </div>
            <div class="lang-switch">UZ / RU</div>
        </div>

        <div class="balance-container">
            <div>
                <div class="bal-title">💳 БАЛАНС</div>
                <div class="bal-value">{balance:,} <span>сум</span></div>
            </div>
            <button class="btn-deposit" onclick="switchTab('topup')">+ Пополнить</button>
        </div>

        <div class="quick-actions">
            <div class="action-card" onclick="alert('Promokodlar tez kunda qo\\'shiladi!')">
                🎟️ <span>Промокоды</span>
            </div>
            <div class="action-card" onclick="window.location.href='https://t.me/syrexa_support'">
                🎧 <span>Поддержка</span>
            </div>
        </div>

        <div class="main-banner">
            <h3>⚡ ENG TEZ VA ARZON UC & ALMAZ</h3>
            <p>100% XAVFSIZ VA AVTOMATIK XIZMAT</p>
        </div>

        <div class="section-header">
            <h4>Популярные игры</h4>
            <a href="javascript:void(0)" onclick="switchTab('games')">Все</a>
        </div>

        <div class="games-grid">
            <div class="game-item" onclick="openGame('pubg', 'PUBG Mobile')">
                <div class="game-thumb" style="background:#e17055;">🪖</div>
                <div class="title">PUBG Mobile</div>
            </div>
            <div class="game-item" onclick="openGame('freefire', 'Free Fire')">
                <div class="game-thumb" style="background:#fdcb6e;">🔥</div>
                <div class="title">Free Fire</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#0984e3;">⚔️</div>
                <div class="title">MLBB</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#6c5ce7;">👑</div>
                <div class="title">Clash Royale</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#00b894;">🎯</div>
                <div class="title">StandOff 2</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#e84393;">⭐</div>
                <div class="title">Stars</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#d63031;">🤖</div>
                <div class="title">Roblox</div>
            </div>
            <div class="game-item" onclick="alert('Tez kunda qo\\'shiladi!')">
                <div class="game-thumb" style="background:#fd79a8;">🥊</div>
                <div class="title">Brawl Stars</div>
            </div>
        </div>
    </div>

    <!-- O'YIN PAKETLARI SAHIFASI -->
    <div id="view-packages" class="packages-view">
        <div class="section-header" style="padding-top:16px;">
            <h4 id="game-title">O'yin paketlari</h4>
            <a href="javascript:void(0)" onclick="closeGame()">Orqaga ✖</a>
        </div>
        <div class="packages-grid" id="pack-container"></div>
    </div>

    <!-- HISOB TO'LDIRISH SAHIFASI (PAYERPIN TOPUP KLONI) -->
    <div id="view-topup" class="pay-view">
        <div class="section-header" style="padding-top:16px;">
            <h4>Пополнение баланса</h4>
        </div>

        <div class="pay-methods">
            <div class="method-card active" id="m-uzcard" onclick="selectMethod('uzcard')">
                <h5>UZCARD</h5>
                <span>Перевод на карту</span>
            </div>
            <div class="method-card" id="m-humo" onclick="selectMethod('humo')">
                <h5>HUMO</h5>
                <span>Перевод на карту</span>
            </div>
        </div>

        <div class="pay-box">
            <div style="font-size:12px; color:var(--text-muted);">To'lov uchun karta raqami:</div>
            <div class="card-num-box">
                <span id="display-card">{card_uzcard}</span>
                <span style="cursor:pointer; font-size:13px; color:#818cf8;" onclick="copyCard()">Nusxa</span>
            </div>
            <div style="font-size:12px; color:#fff;" id="display-holder">{card_uzcard_holder}</div>
            <div style="margin-top:12px; font-size:11px; color:#f87171; line-height:1.4;">
                ⚠️ Faqat bitta o'tkazma bilan to'lang. To'lov qilgach, chekni qo'llab-quvvatlash xizmatiga yuboring.
            </div>
            <button class="modal-btn" style="margin-top:14px; background:#10b981;" onclick="window.location.href='https://t.me/syrexa_support'">
                ✅ Men to'lov qildim (Chek yuborish)
            </button>
        </div>
    </div>

    <!-- BUYURTMALAR SAHIFASI -->
    <div id="view-orders" class="orders-view">
        <div class="section-header" style="padding-top:16px;">
            <h4>Mening buyurtmalarim</h4>
        </div>
        <div id="orders-list">
"""
    if user_orders:
        for ord in user_orders:
            html += f"""
            <div class="order-row">
                <div>
                    <div style="font-weight:700; font-size:14px;">{ord['title']}</div>
                    <div style="font-size:11px; color:var(--text-muted);">ID: {ord['player_id']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-weight:700; color:var(--accent-green);">{ord['price']:,} so'm</div>
                    <div style="font-size:10px; color:#fbbf24;">{ord['status']}</div>
                </div>
            </div>
            """
    else:
        html += """<div style="text-align:center; padding:40px; color:var(--text-muted);">Hozircha buyurtmalar yo'q</div>"""

    html += f"""
        </div>
    </div>

    <!-- XARID MODALI -->
    <div class="modal" id="buy-modal">
        <div class="modal-body">
            <h4 id="buy-item-name">Mahsulot xaridi</h4>
            <div style="font-size:12px; color:var(--text-muted); margin-top:4px;" id="buy-item-price"></div>
            <input type="text" id="player-id-input" placeholder="O'yindagi ID (Player ID)ni kiriting">
            <button class="modal-btn" onclick="submitOrder()">Sotib olish</button>
            <button class="modal-btn" style="background:transparent; color:var(--text-muted); margin-top:6px;" onclick="closeModal('buy-modal')">Bekor qilish</button>
        </div>
    </div>

    <!-- PASTKI NAVIGATSIYA MENYUSI -->
    <div class="bottom-bar">
        <div class="bar-item active" id="tab-home" onclick="switchTab('home')">
            <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
            Главная
        </div>
        <div class="bar-item" id="tab-games" onclick="switchTab('games')">
            <svg viewBox="0 0 24 24"><path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-10 7H8v3H6v-3H3v-2h3V8h2v3h3v2zm4.5 2c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm4-3c-.83 0-1.5-.67-1.5-1.5S18.67 9 19.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            Игры
        </div>
        <div class="bar-item" id="tab-topup" onclick="switchTab('topup')">
            <svg viewBox="0 0 24 24"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            Пополнить
        </div>
        <div class="bar-item" id="tab-orders" onclick="switchTab('orders')">
            <svg viewBox="0 0 24 24"><path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
            Заказы
        </div>
        <div class="bar-item" onclick="Telegram.WebApp.close()">
            <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            Выход
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        const allProducts = {json.dumps(products)};
        const currentBalance = {balance};
        const currentUserId = {user_id};
        let activeItem = null;

        function switchTab(tab) {{
            document.getElementById('view-home').style.display = tab === 'home' ? 'block' : 'none';
            document.getElementById('view-packages').style.display = 'none';
            document.getElementById('view-topup').style.display = tab === 'topup' ? 'block' : 'none';
            document.getElementById('view-orders').style.display = tab === 'orders' ? 'block' : 'none';

            document.querySelectorAll('.bar-item').forEach(el => el.classList.remove('active'));
            if (tab === 'home') document.getElementById('tab-home').classList.add('active');
            if (tab === 'games') openGame('pubg', 'PUBG Mobile');
            if (tab === 'topup') document.getElementById('tab-topup').classList.add('active');
            if (tab === 'orders') document.getElementById('tab-orders').classList.add('active');
        }}

        function openGame(gameKey, gameTitle) {{
            document.getElementById('view-home').style.display = 'none';
            document.getElementById('view-topup').style.display = 'none';
            document.getElementById('view-orders').style.display = 'none';
            document.getElementById('view-packages').style.display = 'block';
            document.getElementById('game-title').innerText = gameTitle;

            const container = document.getElementById('pack-container');
            container.innerHTML = '';
            const filtered = allProducts.filter(p => p.game_key === gameKey);

            filtered.forEach(p => {{
                const card = document.createElement('div');
                card.className = 'pack-card';
                card.onclick = () => selectProduct(p);
                card.innerHTML = `
                    <div class="pack-badge">${{p.badge}}</div>
                    <div class="pack-title">${{p.name}}</div>
                    <div class="pack-price">${{p.price.toLocaleString()}} сум</div>
                `;
                container.appendChild(card);
            }});
        }}

        function closeGame() {{
            switchTab('home');
        }}

        function selectProduct(p) {{
            if (currentBalance < p.price) {{
                alert("Mablag' yetarli emas! Iltimos, oldin hisobingizni to'ldiring.");
                switchTab('topup');
                return;
            }}
            activeItem = p;
            document.getElementById('buy-item-name').innerText = p.name;
            document.getElementById('buy-item-price').innerText = p.price.toLocaleString() + " so'm";
            document.getElementById('player-id-input').value = '';
            document.getElementById('buy-modal').style.display = 'flex';
        }}

        function closeModal(id) {{
            document.getElementById(id).style.display = 'none';
        }}

        async function submitOrder() {{
            const pid = document.getElementById('player-id-input').value.trim();
            if (!pid) {{
                alert("Iltimos, o'yin ID raqamingizni kiriting!");
                return;
            }}
            closeModal('buy-modal');

            const res = await fetch('/api/order', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    user_id: currentUserId,
                    price: activeItem.price,
                    title: activeItem.name,
                    player_id: pid
                }})
            }});
            const data = await res.json();
            alert(data.msg);
            if (data.ok) location.reload();
        }}

        function selectMethod(method) {{
            document.getElementById('m-uzcard').classList.remove('active');
            document.getElementById('m-humo').classList.remove('active');
            if (method === 'uzcard') {{
                document.getElementById('m-uzcard').classList.add('active');
                document.getElementById('display-card').innerText = "{card_uzcard}";
                document.getElementById('display-holder').innerText = "{card_uzcard_holder}";
            }} else {{
                document.getElementById('m-humo').classList.add('active');
                document.getElementById('display-card').innerText = "{card_humo}";
                document.getElementById('display-holder').innerText = "{card_humo_holder}";
            }}
        }}

        function copyCard() {{
            const card = document.getElementById('display-card').innerText;
            navigator.clipboard.writeText(card);
            alert("Karta raqami nusxalandi: " + card);
        }}
    </script>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")

# --- SERVER ISHGA TUSHIRISH ---
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    import asyncio
    asyncio.create_task(dp.start_polling(bot))

def main():
    app = web.Application()
    app.router.add_get('/', webapp_handler)
    app.router.add_post('/api/order', api_order)
    app.on_startup.append(on_startup)
    web.run_app(app, host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
