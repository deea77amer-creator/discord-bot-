import discord
from discord.ext import commands
import sqlite3
from datetime import datetime

DB_FILE = "database.db"

def init_auth_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_logs (
            guild_id TEXT,
            user_id TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)
    # توحيد جدول النقاط مع جدول الألعاب لضمان عدم ضياعها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            guild_id TEXT,
            user_id TEXT,
            points INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_status (
            guild_id TEXT,
            user_id TEXT,
            last_action TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    conn.commit()
    conn.close()

init_auth_db()

def get_user_data(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT OR IGNORE INTO users (guild_id, user_id, points) VALUES (?, ?, 0)", (str(guild_id), str(user_id)))
        conn.commit()
        points = 0
    else:
        points = row[0]
    conn.close()
    return points

def add_points(guild_id, user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current = get_user_data(guild_id, user_id)
    new_points = current + amount
    cursor.execute("UPDATE users SET points = ? WHERE guild_id = ? AND user_id = ?", (new_points, str(guild_id), str(user_id)))
    conn.commit()
    conn.close()
    return new_points

def get_user_status(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT last_action FROM user_status WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def update_user_status(guild_id, user_id, action):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # تحديث آخر حركة للمستخدم
    cursor.execute("""
        INSERT INTO user_status (guild_id, user_id, last_action)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) 
        DO UPDATE SET last_action = ?
    """, (str(guild_id), str(user_id), action, action))
    
    # تسجيل الحركة في السجلات
    now_str = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO auth_logs (guild_id, user_id, action, timestamp)
        VALUES (?, ?, ?, ?)
    """, (str(guild_id), str(user_id), action, now_str))
    
    conn.commit()
    conn.close()

def get_user_stats(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT action, COUNT(*) FROM auth_logs
        WHERE guild_id = ? AND user_id = ?
        GROUP BY action
    """, (str(guild_id), str(user_id)))
    rows = cursor.fetchall()
    conn.close()
    
    stats = {"دخول": 0, "خروج": 0}
    for action, count in rows:
        if action in stats:
            stats[action] = count
    return stats

class AuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LOGIN_CHANNEL_ID = 1528779670911320174
        self.LOGOUT_CHANNEL_ID = 1528604200710308011

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        last_act = get_user_status(guild_id, user_id)

        if text in ["دخول", "/دخول"]:
            if channel_id != self.LOGIN_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            if last_act == "دخول":
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(f"❌ يا {message.author.mention}, لقد قمت بتسجيل **الدخول** مسبقاً ولا يمكنك تكراره حتى تسجل الخروج!", delete_after=5)

            update_user_status(guild_id, user_id, "دخول")
            new_pts = add_points(guild_id, user_id, 5) # مكافأة 5 نقاط عند تسجيل الدخول
            await message.channel.send(f"✅ يا {message.author.mention}, تم تسجيل **الدخول** بنجاح! (رصيد النقاط: {new_pts} نقطة).")
            return

        if text in ["خروج", "/خروج"]:
            if channel_id != self.LOGOUT_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            if last_act == "خروج" or last_act is None:
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(f"❌ يا {message.author.mention}, أنت لم تقم بتسجيل الدخول أساساً لتسجل الخروج!", delete_after=5)

            update_user_status(guild_id, user_id, "خروج")
            current_pts = get_user_data(guild_id, user_id)
            await message.channel.send(f"🚪 يا {message.author.mention}, تم تسجيل **الخروج** بنجاح. (رصيد النقاط: {current_pts} نقطة).")
            return

        if text in ["سجل", "/سجل", "نقاطي"]:
            stats = get_user_stats(guild_id, user_id)
            current_pts = get_user_data(guild_id, user_id)
            embed = discord.Embed(
                title=f"📊 سِجِلات الحُضُور ونِقَاط لـ {message.author.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="📥 مرات الدخول", value=f"`{stats['دخول']}` مرة", inline=True)
            embed.add_field(name="📤 مرات الخروج", value=f"`{stats['خروج']}` مرة", inline=True)
            embed.add_field(name="⭐ رصيد النقاط", value=f"`{current_pts}` نقطة", inline=False)
            embed.set_footer(text="💡 يتم حفظ النقاط بشكل دائم ومشاركته مع الألعاب.")
            await message.channel.send(embed=embed)
            return

async def setup(bot):
    await bot.add_cog(AuthCog(bot))
