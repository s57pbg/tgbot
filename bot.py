import asyncio
import datetime
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatPermissions
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNERS = ["irusakusa", "FourDoorsMoreVVhores"]

DB = "bot.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= DB =================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'user',
            nickname TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            user_id INTEGER,
            date TEXT
        )
        """)

        await db.commit()

# ================= РОЛИ =================
async def get_role(user: types.User):
    if user.username in OWNERS:
        return "owner"

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT role FROM users WHERE user_id=?", (user.id,))
        row = await cur.fetchone()
        return row[0] if row else "user"

# ================= АКТИВНОСТЬ =================
@dp.message()
async def track(message: types.Message):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO activity VALUES (?, ?)",
            (message.from_user.id, str(datetime.date.today()))
        )
        await db.commit()

# ================= ВЫДАЧА РОЛЕЙ =================
@dp.message(F.text.startswith("/роль"))
async def set_role(message: types.Message):
    role = await get_role(message.from_user)
    if role != "owner":
        return await message.answer("Только владелец")

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        new_role = message.text.split()[1]
    else:
        _, user_id, new_role = message.text.split()
        user_id = int(user_id)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)",
            (user_id, new_role)
        )
        await db.commit()

    await message.answer("Роль выдана")

# ================= МУТ =================
@dp.message(F.text.startswith("/мут"))
async def mute(message: types.Message):
    role = await get_role(message.from_user)
    if role not in ["mod", "admin", "owner"]:
        return await message.answer("Нет прав")

    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение пользователя")

    user_id = message.reply_to_message.from_user.id

    try:
        minutes = int(message.text.split()[1])
    except:
        return await message.answer("/мут 10 (минуты)")

    until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

    await message.chat.restrict(
        user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )

    await message.answer(f"Мут на {minutes} минут")

# ================= КИК =================
@dp.message(F.text.startswith("/кик"))
async def kick(message: types.Message):
    role = await get_role(message.from_user)
    if role not in ["admin", "owner"]:
        return await message.answer("Нет прав")

    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение")

    user_id = message.reply_to_message.from_user.id

    await message.chat.ban(user_id)
    await message.chat.unban(user_id)

    await message.answer("Кик выполнен")

# ================= БАН =================
@dp.message(F.text.startswith("/бан"))
async def ban(message: types.Message):
    role = await get_role(message.from_user)
    if role != "owner":
        return await message.answer("Только владелец")

    if not message.reply_to_message:
        return await message.answer("Ответь на сообщение")

    user_id = message.reply_to_message.from_user.id

    await message.chat.ban(user_id)

    await message.answer("Пользователь забанен")

# ================= НИК =================
@dp.message(F.text.startswith("/мойник"))
async def set_nick(message: types.Message):
    nick = message.text.split(maxsplit=1)[1]

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, nickname) VALUES (?, ?)",
            (message.from_user.id, nick)
        )
        await db.commit()

    await message.answer("Ник сохранён")

@dp.message(F.text == "/ники")
async def nick_list(message: types.Message):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT user_id, nickname FROM users WHERE nickname IS NOT NULL")
        rows = await cur.fetchall()

    text = "\n".join([f"{u} — {n}" for u, n in rows])
    await message.answer(text or "Нет ников")

# ================= СТАТА =================
@dp.message(F.text == "/стата")
async def stats(message: types.Message):
    today = str(datetime.date.today())

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT COUNT(*) FROM activity WHERE date=?", (today,))
        day = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM activity")
        total = (await cur.fetchone())[0]

    await message.answer(f"Сегодня: {day}\nВсего: {total}")

# ================= ВЫХОД ИЗ ЧАТА =================
@dp.message(F.left_chat_member)
async def left(message: types.Message):
    user_id = message.left_chat_member.id

    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM activity WHERE user_id=?", (user_id,))
        await db.commit()

# ================= СТАРТ =================
async def main():
    await init_db()
    await dp.start_polling(bot)

asyncio.run(main())