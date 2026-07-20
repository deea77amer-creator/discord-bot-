import discord
from discord.ext import commands
import sqlite3
from datetime import datetime

DB_FILE = "auth_system.db"

def init_auth_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_logs (
            guild_id TEXT,
            user_id TEXT,
            action TEXT,
            timestamp TEXT,
            PRIMARY KEY (guild_id, user_id, action, timestamp)
        )
    """)
    conn.commit()
    conn.close()

init_auth_db()

def log_action(guild_id, user_id, action):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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

        if text in ["دخول", "/دخول"]:
            if channel_id != self.LOGIN_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            log_action(guild_id, user_id, "دخول")
            await message.channel.send(f"✅ يا {message.author.mention}, تم تسجيل **الدخول** بنجاح في القناة المخصصة.")
            return

        if text in ["خروج", "/خروج"]:
            if channel_id != self.LOGOUT_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            log_action(guild_id, user_id, "خروج")
            await message.channel.send(f"🚪 يا {message.author.mention}, تم تسجيل **الخروج** بنجاح في القناة المخصصة.")
            return

        if text in ["سجل", "/سجل"]:
            stats = get_user_stats(guild_id, user_id)
            embed = discord.Embed(
                title=f"📊 سِجِلات الحُضُور والانصِرَاف لـ {message.author.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="📥 عدد مرات الدخول", value=f"`{stats['دخول']}` مرة", inline=True)
            embed.add_field(name="📤 عدد مرات الخروج", value=f"`{stats['خروج']}` مرة", inline=True)
            embed.set_footer(text="💡 يتم احتساب السجلات من القنوات المخصصة فقط.")
            await message.channel.send(embed=embed)
            return

async def setup(bot):
    await bot.add_cog(AuthCog(bot))
