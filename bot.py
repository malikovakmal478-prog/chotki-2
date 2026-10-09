import os
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR (Render Environment Variables dan olinadi) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKENINGIZNI_YOZING")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # Telegram ID raqamingiz
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    # Foydalanuvchilar
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        balance INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'uz'
    )""")
    # Tizim sozlamalari
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    # Mahsulotlar (O'yinlar va paketlar)
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game TEXT,
        name TEXT,
        price INTEGER,
        image_url TEXT
    )""")
    
    # Boshlang'ich sozlamalar
    defaults = [
        ("brand_name", "Syrexa"),
        ("card_number", "8600 0000 0000 0000"),
        ("card_holder", "SYREXA PAY"),
        ("start_photo", "https://i.ibb.co/vzR0jYq/syrexa-banner.jpg"),
        ("pubg_photo", "https://i.ibb.co/K2Lsmg1/pubg-banner.jpg"),
        ("ff_photo", "https://i.ibb.co/VMyh02S/freefire-banner.jpg"),
        ("required_channel", "@syrexa_rasmiy")
    ]
    for key, val in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
        
    # Boshlang'ich o'yin paketlari
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        default_prods = [
            ("PUBG", "60 UC", 13000, "https://i.ibb.co/K2Lsmg1/pubg-banner.jpg"),
            ("PUBG", "325 UC", 65000, "https://i.ibb.co/K2Lsmg1/pubg-banner.jpg"),
            ("PUBG", "660 UC", 125000, "https://i.ibb.co/K2Lsmg1/pubg-banner.jpg"),
            ("PUBG", "1800 UC", 320000, "https://i.ibb.co/K2Lsmg1/pubg-banner.jpg"),
            ("FREEFIRE", "100 + 10 Almaz", 14000, "https://i.ibb.co/VMyh02S/freefire-banner.jpg"),
            ("FREEFIRE", "310 + 31 Almaz", 42000, "https://i.ibb.co/VMyh02S/freefire-banner.jpg"),
            ("FREEFIRE", "520 + 52 Almaz", 70000, "https://i.ibb.co/VMyh02S/freefire-banner.jpg")
        ]
        c.executemany("INSERT INTO products (game, name, price, image_url) VALUES (?, ?, ?, ?)", default_prods)
        
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# --- TELEGRAM BOT QISMI ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or ""

    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", 
              (user_id, first_name, username))
    conn.commit()
    conn.close()

    web_url = f"{BASE_URL}/app?user_id={user_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Ilovani ochish", web_app=WebAppInfo(url=web_url))],
        [
            InlineKeyboardButton(text="📢 Bizning kanal", url=f"https://t.me/{get_setting('required_channel').replace('@', '')}"),
            InlineKeyboardButton(text="👨‍💻 Qo'llab-quvvatlash", url="https://t.me/syrexa_support")
        ]
    ])

    start_text = (
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"<b>Syrexa</b> o'yin valyutalari do'koniga xush kelibsiz.\n"
        f"Tezkor, hamyonbop va 100% xavfsiz UC va Almaz xaridlari."
    )
    
    banner = get_setting("start_photo")
    try:
        await message.answer_photo(photo=banner, caption=start_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(start_text, reply_markup=kb, parse_mode="HTML")

# --- ADMIN BUYRUQLARI ---
@dp.message(Command("admin"))
async def admin_panel_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    total_users, total_bal = c.fetchone()
    conn.close()

    admin_text = (
        f"⚙️ <b>SYREXA BOSHQARUV PANELI</b>\n\n"
        f"👥 Foydalanuvchilar soni: <b>{total_users}</b>\n"
        f"💰 Umumiy foydalanuvchilar balansi: <b>{total_bal or 0} so'm</b>\n"
        f"💳 Hozirgi karta: <code>{get_setting('card_number')}</code> ({get_setting('card_holder')})\n"
        f"📢 Majburiy kanal: <b>{get_setting('required_channel')}</b>\n\n"
        f"<b>Tahrirlash buyruqlari:</b>\n"
        f"• <code>/setcard 8600... Ism Familiya</code> - Kartani yangilash\n"
        f"• <code>/setchannel @kanal</code> - Kanalni almashtirish\n"
        f"• <code>/setphoto start/pubg/ff [URL_RASM]</code> - Rasmlarni o'zgartirish\n"
        f"• <code>/balance [USER_ID] [SUMMA]</code> - Balans berish yoki ayirish (+/-)\n"
        f"• <code>/additem PUBG/FREEFIRE [Nomi] [Narxi] [Rasm_URL]</code> - Yangi paket qo'shish"
    )
    await message.answer(admin_text, parse_mode="HTML")

@dp.message(F.text.startswith("/setcard"))
async def admin_set_card(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        set_setting("card_number", parts[1])
        set_setting("card_holder", parts[2])
        await message.answer("✅ Karta ma'lumotlari muvaffaqiyatli saqlandi!")

@dp.message(F.text.startswith("/balance"))
async def admin_set_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) == 3:
        uid, amount = int(parts[1]), int(parts[2])
        conn = sqlite3.connect("syrexa.db")
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
        conn.commit()
        conn.close()
        await message.answer(f"✅ User ID: {uid} balansiga {amount} so'm kiritildi!")

@dp.message(F.text.startswith("/setphoto"))
async def admin_set_photo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) == 3:
        key_type, url = parts[1], parts[2]
        if key_type == "start": set_setting("start_photo", url)
        elif key_type == "pubg": set_setting("pubg_photo", url)
        elif key_type == "ff": set_setting("ff_photo", url)
        await message.answer("✅ Rasm URL yangilandi!")

# --- WEB APP (HTML, CSS, JS) QISMI ---
async def app_handler(request):
    user_id = request.query.get("user_id", "0")
    conn = sqlite3.connect("syrexa.db")
    c = conn.cursor()
    c.execute("SELECT balance, lang FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    balance = u[0] if u else 0
    
    c.execute("SELECT id, game, name, price, image_url FROM products")
    products = c.fetchall()
    conn.close()

    card_num = get_setting("card_number")
    card_name = get_setting("card_holder")

    # To'liq zamonaviy PayerPin uslubidagi Dark UI (Neon)
    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Syrexa Shop</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: #0c0f1d; color: #fff; padding-bottom: 70px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #13172d; }}
        .balance-box {{ background: linear-gradient(135deg, #1f2544, #14172b); border-radius: 12px; padding: 12px 18px; display: flex; justify-content: space-between; align-items: center; margin: 15px; border: 1px solid #2a315c; }}
        .btn-add {{ background: #5a54f4; color: #fff; border: none; padding: 8px 14px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
        .banner {{ margin: 0 15px; border-radius: 14px; overflow: hidden; background: linear-gradient(45deg, #2b1055, #7597de); padding: 15px; text-align: center; font-size: 18px; font-weight: bold; }}
        .title {{ padding: 15px; font-size: 18px; font-weight: bold; color: #b5b9d5; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 0 15px; }}
        .card {{ background: #161a33; border: 1px solid #232950; border-radius: 12px; padding: 10px; text-align: center; cursor: pointer; transition: 0.2s; }}
        .card:active {{ transform: scale(0.97); }}
        .card img {{ width: 100%; height: 90px; object-fit: cover; border-radius: 8px; }}
        .card .name {{ margin-top: 8px; font-size: 14px; font-weight: bold; }}
        .card .price {{ color: #2ecc71; font-size: 13px; margin-top: 4px; }}
        .navbar {{ position: fixed; bottom: 0; left: 0; width: 100%; height: 60px; background: #13172d; display: flex; justify-content: space-around; align-items: center; border-top: 1px solid #22284b; }}
        .nav-item {{ color: #7f86aa; text-align: center; font-size: 11px; cursor: pointer; text-decoration: none; }}
        .nav-item.active {{ color: #5a54f4; font-weight: bold; }}
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); align-items: center; justify-content: center; }}
        .modal-content {{ background: #181d3b; padding: 20px; border-radius: 16px; width: 85%; max-width: 320px; text-align: center; border: 1px solid #333c70; }}
        .modal-content input {{ width: 100%; padding: 10px; margin: 10px 0; border-radius: 8px; border: 1px solid #333c70; background: #0d1024; color: #fff; }}
    </style>
</head>
<body>

    <div class="header">
        <h2 style="color: #6366f1; letter-spacing: 1px;">⚡ SYREXA</h2>
        <span style="background: #232950; padding: 4px 10px; border-radius: 12px; font-size: 12px;">UZ / RU</span>
    </div>

    <div class="balance-box">
        <div>
            <div style="font-size: 12px; color: #8e95bf;">Hisob balansi:</div>
            <div style="font-size: 20px; font-weight: bold; color: #fff;">{balance:,} so'm</div>
        </div>
        <button class="btn-add" onclick="showTopUp()">+ To'ldirish</button>
    </div>

    <div class="banner">
        🔥 ENG TEZ VA ARZON UC & ALMAZ XIZMATI
    </div>

    <div class="title">O'yin paketlari</div>
    <div class="grid">
"""
    for p in products:
        pid, game, name, price, img = p
        html += f"""
        <div class="card" onclick="buyItem('{name}', {price})">
            <img src="{img}" alt="{game}">
            <div class="name">{name}</div>
            <div class="price">{price:,} so'm</div>
        </div>
        """

    html += f"""
    </div>

    <!-- To'lov Modali -->
    <div id="topup-modal" class="modal">
        <div class="modal-content">
            <h3>Hisobni to'ldirish</h3>
            <p style="font-size: 12px; color: #aaa; margin: 8px 0;">Karta raqamiga to'lov qiling:</p>
            <p style="background: #0d1024; padding: 8px; border-radius: 6px; font-family: monospace; font-size: 16px; color: #2ecc71;">{card_num}</p>
            <p style="font-size: 12px; color: #888; margin-bottom: 12px;">{card_name}</p>
            <button class="btn-add" style="width: 100%;" onclick="closeTopUp()">Tushunarli</button>
        </div>
    </div>

    <div class="navbar">
        <div class="nav-item active">🏠 Asosiy</div>
        <div class="nav-item" onclick="showTopUp()">💳 Hamyon</div>
        <div class="nav-item" onclick="Telegram.WebApp.close()">❌ Chiqish</div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        function showTopUp() {{
            document.getElementById('topup-modal').style.display = 'flex';
        }}
        function closeTopUp() {{
            document.getElementById('topup-modal').style.display = 'none';
        }}
        function buyItem(name, price) {{
            const balance = {balance};
            if(balance < price) {{
                alert("Mablag' yetarli emas! Iltimos, oldin balansingizni to'ldiring.");
                showTopUp();
            }} else {{
                let playerId = prompt(name + " olish uchun Player ID (o'yin hisob raqami)ni kiriting:");
                if(playerId) {{
                    alert("Buyurtma qabul qilindi! Tez orada hisobingizga tushiriladi.");
                }}
            }}
        }}
    </script>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html")

# --- SERVERNI ISHGA TUSHIRISH ---
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    import asyncio
    asyncio.create_task(dp.start_polling(bot))

def main():
    app = web.Application()
    app.router.add_get('/app', app_handler)
    app.on_startup.append(on_startup)
    web.run_app(app, host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
