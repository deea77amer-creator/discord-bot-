import os
import sqlite3
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- إعداد سيرفر الـ Flask الوهمي لمنع Port Timeout ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# --- تم تعديل البوت ليصبح كلاس يدعم تحميل الملفات تلقائياً ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # تحميل الملفات تلقائياً من مجلد cogs إن وجد
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    cog_name = f'cogs.{filename[:-3]}'
                    try:
                        await self.load_extension(cog_name)
                        print(f"تم تحميل الملف بنجاح: {filename}")
                    except commands.errors.ExtensionAlreadyLoaded:
                        pass

    async def on_ready(self):
        print(f"البوت جاهز ومتصل بقاعدة البيانات المحلية باسم: {self.user}")

bot = MyBot()

# --- نظام قاعدة البيانات المحلية SQLite (حفظ دائم) ---
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            guild_id TEXT,
            user_id TEXT,
            joins INTEGER DEFAULT 0,
            leaves INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            checkins_count INTEGER DEFAULT 0,
            manual_leaves_count INTEGER DEFAULT 0,
            last_checkin TEXT DEFAULT "",
            last_leave TEXT DEFAULT "",
            PRIMARY KEY (guild_id, user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            guild_id TEXT PRIMARY KEY,
            welcome_channel INTEGER,
            leave_channel INTEGER,
            games_channel INTEGER,
            records_channel INTEGER,
            top_channel INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_data(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT joins, leaves, points, checkins_count, manual_leaves_count, last_checkin, last_leave FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)", (str(guild_id), str(user_id)))
        conn.commit()
        data = {"joins": 0, "leaves": 0, "points": 0, "checkins_count": 0, "manual_leaves_count": 0, "last_checkin": "", "last_leave": ""}
    else:
        data = {
            "joins": row[0], "leaves": row[1], "points": row[2],
            "checkins_count": row[3], "manual_leaves_count": row[4],
            "last_checkin": row[5], "last_leave": row[6]
        }
    conn.close()
    return data

def update_user_data(guild_id, user_id, **kwargs):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    get_user_data(guild_id, user_id)
    for key, val in kwargs.items():
        cursor.execute(f"UPDATE users SET {key} = ? WHERE guild_id = ? AND user_id = ?", (val, str(guild_id), str(user_id)))
    conn.commit()
    conn.close()

def get_config(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT welcome_channel, leave_channel, games_channel, records_channel, top_channel FROM config WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "welcome_channel": row[0],
            "leave_channel": row[1],
            "games_channel": row[2],
            "records_channel": row[3],
            "top_channel": row[4]
        }
    return {}

def save_config_key(guild_id, key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO config (guild_id, {key}) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET {key} = ?", (str(guild_id), value, value))
    conn.commit()
    conn.close()

# --- نظام الترحيب والمغادرة (الأساسي) ---
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    data = get_user_data(guild_id, user_id)
    new_joins = data["joins"] + 1
    update_user_data(guild_id, user_id, joins=new_joins)

    config = get_config(guild_id)
    if config.get("welcome_channel"):
        channel = member.guild.get_channel(config["welcome_channel"])
        if channel:
            embed = discord.Embed(title="✨ | وعاد النور إلى السيرفر!", description=f"أهلاً ومرحباً بك يا {member.mention}\n• عدد مرات دخولك: **{new_joins}**", color=discord.Color.gold())
            await channel.send(content=f"حياك الله {member.mention} 🚀", embed=embed)

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    data = get_user_data(guild_id, user_id)
    new_leaves = data["leaves"] + 1
    update_user_data(guild_id, user_id, leaves=new_leaves)

    config = get_config(guild_id)
    if config.get("leave_channel"):
        channel = member.guild.get_channel(config["leave_channel"])
        if channel:
            embed = discord.Embed(title="👋 | طير غادرنا!", description=f"العضو **{member.name}** طلع.\n• إجمالي مرات خروجه: **{new_leaves}**", color=discord.Color.red())
            await channel.send(embed=embed)

# --- أوامر تحديد القنوات ---
@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx):
    save_config_key(ctx.guild.id, "welcome_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الترحيب** بنجاح!")

@bot.command(name="تحديد_الخروج")
@commands.has_permissions(administrator=True)
async def set_leave(ctx):
    save_config_key(ctx.guild.id, "leave_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الخروج** بنجاح!")

@bot.command(name="تحديد_الألعاب")
@commands.has_permissions(administrator=True)
async def set_games(ctx):
    save_config_key(ctx.guild.id, "games_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الألعاب** بنجاح!")

@bot.command(name="تحديد_السجلات")
@commands.has_permissions(administrator=True)
async def set_records(ctx):
    save_config_key(ctx.guild.id, "records_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **السجلات** بنجاح!")

@bot.command(name="تحديد_التوب")
@commands.has_permissions(administrator=True)
async def set_top(ctx):
    save_config_key(ctx.guild.id, "top_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **التوب** بنجاح!")

# --- معالجة الأوامر والرسائل الأساسية (نقاطي والتوب) ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    text_lower = text.lower()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    config = get_config(guild_id)

    # أمر نقاطي
    if text_lower == "نقاطي":
        data = get_user_data(guild_id, user_id)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{data['points']}** نقطة.")

    # أمر التوب (أكثر الأعضاء نقاطاً)
    elif text_lower in ["توب", "!top", "top"]:
        if config.get("top_channel") and message.channel.id != config["top_channel"]:
            await message.delete()
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, points FROM users WHERE guild_id = ? ORDER BY points DESC LIMIT 10", (guild_id,))
        top_users = cursor.fetchall()
        conn.close()

        embed = discord.Embed(title="🏆 قائمة لوحة الشرف (Top 10)", description="أكثر الأعضاء جمعاً للنقاط في السيرفر:", color=discord.Color.gold())
        
        if not top_users:
            embed.description = "لا توجد أي بيانات مسجلة حتى الآن."
        else:
            description_lines = []
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for index, (u_id, pts) in enumerate(top_users):
                member = message.guild.get_member(int(u_id))
                name = member.display_name if member else f"مغادر ({u_id})"
                medal = medals[index] if index < len(medals) else f"•"
                description_lines.append(f"{medal} **{name}** — `{pts}` نقطة")
            embed.description = "\n".join(description_lines)

        await message.channel.send(embed=embed)

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("خطأ: التوكن غير موجود!")
