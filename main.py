import os
import sqlite3
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import random

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

bot = commands.Bot(command_prefix="!", intents=intents)

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
        CREATE TABLE IF NOT EXISTS cooldowns (
            guild_id TEXT,
            user_id TEXT,
            game_name TEXT,
            last_time TEXT,
            PRIMARY KEY (guild_id, user_id, game_name)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            guild_id TEXT PRIMARY KEY,
            welcome_channel INTEGER,
            leave_channel INTEGER,
            games_channel INTEGER,
            records_channel INTEGER
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

def add_points(guild_id, user_id, amount):
    data = get_user_data(guild_id, user_id)
    new_points = data["points"] + amount
    update_user_data(guild_id, user_id, points=new_points)
    return new_points

def get_config(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT welcome_channel, leave_channel, games_channel, records_channel FROM config WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "welcome_channel": row[0],
            "leave_channel": row[1],
            "games_channel": row[2],
            "records_channel": row[3]
        }
    return {}

def save_config_key(guild_id, key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO config (guild_id, {key}) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET {key} = ?", (str(guild_id), value, value))
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    print(f"البوت جاهز ومتصل بقاعدة البيانات المحلية باسم: {bot.user}")

# --- نظام الترحيب والمغادرة ---
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

# --- نظام الكول داون (دقيقتان) ---
COOLDOWN_TIME = timedelta(minutes=2)

def check_cooldown(guild_id, user_id, game_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT last_time FROM cooldowns WHERE guild_id = ? AND user_id = ? AND game_name = ?", (str(guild_id), str(user_id), game_name))
    row = cursor.fetchone()
    conn.close()
    if row:
        last_time = datetime.fromisoformat(row[0])
        now = datetime.now()
        if now - last_time < COOLDOWN_TIME:
            remaining = COOLDOWN_TIME - (now - last_time)
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            return False, f"{mins} دقيقة و {secs} ثانية"
    return True, ""

def set_cooldown(guild_id, user_id, game_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("INSERT INTO cooldowns (guild_id, user_id, game_name, last_time) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id, user_id, game_name) DO UPDATE SET last_time = ?", (str(guild_id), str(user_id), game_name, now_str, now_str))
    conn.commit()
    conn.close()

# --- واجهات الألعاب الـ 15 التفاعلية ---

# 1. عجلة الحظ
class WheelView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🎡 تدوير العجلة", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليست لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "wheel")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "wheel")
        await interaction.response.edit_message(embed=discord.Embed(title="🎡 جاري تدوير العجلة...", color=discord.Color.gold()), view=None)
        await asyncio.sleep(1.5)
        won = random.choice([10, 25, 50, 100, 200, 0, 500])
        embed = discord.Embed(title="🎡 عجلة الحظ", color=discord.Color.gold())
        if won > 0:
            tot = add_points(self.guild_id, self.user_id, won)
            embed.description = f"🎉 مبروك ربحت **{won}** نقطة! الرصيد: **{tot}**"
        else:
            embed.description = "❌ خسارة، العجلة وقفت على الصفر."
        await interaction.edit_original_response(embed=embed)

# 2. النرد
class DiceView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🎲 ارمِ النرد", style=discord.ButtonStyle.blurple)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "dice")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "dice")
        await interaction.response.edit_message(embed=discord.Embed(title="🎲 جاري رمي النرد...", color=discord.Color.blue()), view=None)
        await asyncio.sleep(1.5)
        u, b = random.randint(1, 6), random.randint(1, 6)
        embed = discord.Embed(title="🎲 تحدي النرد", description=f"رقمك: {u} | رقم البوت: {b}", color=discord.Color.blue())
        if u > b:
            tot = add_points(self.guild_id, self.user_id, 40)
            embed.description += f"\n🏆 فزت وربحت **40** نقطة! (الرصيد: {tot})"
        elif u < b:
            embed.description += "\n❌ خسرت أمام البوت!"
        else:
            tot = add_points(self.guild_id, self.user_id, 10)
            embed.description += f"\n🤝 تعادل! منحت **10** نقاط."
        await interaction.edit_original_response(embed=embed)

# 3. الصناديق
class BoxesView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.winning = random.randint(1, 3)

    @discord.ui.button(label="📦 صندوق 1", style=discord.ButtonStyle.secondary)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, 1)
    @discord.ui.button(label="📦 صندوق 2", style=discord.ButtonStyle.secondary)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, 2)
    @discord.ui.button(label="📦 صندوق 3", style=discord.ButtonStyle.secondary)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, 3)

    async def process(self, interaction, choice):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "boxes")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "boxes")
        
        embed = discord.Embed(title="📦 فتح الصناديق", color=discord.Color.purple())
        if choice == self.winning:
            tot = add_points(self.guild_id, self.user_id, 50)
            embed.description = f"🎉 مبروك! اخترت الصندوق الصحيح وربحت **50** نقطة! (الرصيد: {tot})"
        else:
            embed.description = f"❌ حظ أوفر! الصندوق الصحيح كان رقم {self.winning}."
        await interaction.response.edit_message(embed=embed, view=None)

# 4. حجر ورقة مقص
class RpsView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🪨 حجر", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "حجر")
    @discord.ui.button(label="📄 ورقة", style=discord.ButtonStyle.primary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "ورقة")
    @discord.ui.button(label="✂️ مقص", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "مقص")

    async def play(self, interaction, choice):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "rps")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "rps")
        
        bot_choice = random.choice(["حجر", "ورقة", "مقص"])
        embed = discord.Embed(title="✂️ حجر ورقة مقص", color=discord.Color.teal())
        embed.add_field(name="اختيارك:", value=choice)
        embed.add_field(name="اختيار البوت:", value=bot_choice)

        if choice == bot_choice:
            embed.description = "🤝 تعادل!"
        elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
            tot = add_points(self.guild_id, self.user_id, 30)
            embed.description = f"🏆 فزت وربحت **30** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "❌ خسرتم أمام البوت!"
        await interaction.response.edit_message(embed=embed, view=None)

# 5. تخمين الرقم
class GuessView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.target = random.randint(1, 5)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def n1(self, interaction: discord.Interaction, button: discord.ui.Button): await self.chk(interaction, 1)
    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def n2(self, interaction: discord.Interaction, button: discord.ui.Button): await self.chk(interaction, 2)
    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def n3(self, interaction: discord.Interaction, button: discord.ui.Button): await self.chk(interaction, 3)
    @discord.ui.button(label="4", style=discord.ButtonStyle.blurple)
    async def n4(self, interaction: discord.Interaction, button: discord.ui.Button): await self.chk(interaction, 4)
    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple)
    async def n5(self, interaction: discord.Interaction, button: discord.ui.Button): await self.chk(interaction, 5)

    async def chk(self, interaction, num):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "guess")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "guess")
        
        embed = discord.Embed(title="🔢 تخمين الرقم", color=discord.Color.dark_blue())
        if num == self.target:
            tot = add_points(self.guild_id, self.user_id, 40)
            embed.description = f"🎉 ممتاز! الرقم الصحيح كان {self.target}، ربحت **40** نقطة! (الرصيد: {tot})"
        else:
            embed.description = f"❌ خطأ! الرقم الصحيح كان {self.target}."
        await interaction.response.edit_message(embed=embed, view=None)

# 6. حظك اليوم
class LuckView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🔮 اكشف حظك", style=discord.ButtonStyle.green)
    async def luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "luck")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "luck")
        
        pr = random.choice([15, 30, 60, 0, 100])
        embed = discord.Embed(title="🔮 حظك اليوم", color=discord.Color.magenta())
        if pr > 0:
            tot = add_points(self.guild_id, self.user_id, pr)
            embed.description = f"✨ حظك اليوم رائع! ربحت **{pr}** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "🌧️ حظك اليوم عاصف، لم تفز بشيء."
        await interaction.response.edit_message(embed=embed, view=None)

# 7. تحدي السرعة
class SpeedView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="⚡ اضغط بأقصى سرعة!", style=discord.ButtonStyle.red)
    async def spd(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "speed")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "speed")
        tot = add_points(self.guild_id, self.user_id, 35)
        embed = discord.Embed(title="⚡ تحدي السرعة", description=f"🚀 يا أسرع البرق! منحت **35** نقطة! (الرصيد: {tot})", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=None)

# 8. حساب سريع
class MathView(discord.ui.View):
    def __init__(self, guild_id, user_id, ans):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.ans = ans

    @discord.ui.button(label="✅ إجابة صحيحة", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ans_chk(interaction, True)
    @discord.ui.button(label="❌ إجابة خاطئة", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ans_chk(interaction, False)

    async def ans_chk(self, interaction, user_val):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "math")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "math")
        
        embed = discord.Embed(title="🧮 لعبة الحساب", color=discord.Color.orange())
        if user_val == self.ans:
            tot = add_points(self.guild_id, self.user_id, 45)
            embed.description = f"🎉 إجابتك ذكية وصحيحة! ربحت **45** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "❌ إجابة غير دقيقة، حظاً أوفر."
        await interaction.response.edit_message(embed=embed, view=None)

# 9. الكنز المفقود
class TreasureView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="💎 حفر للبحث عن الكنز", style=discord.ButtonStyle.green)
    async def dig(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "treasure")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "treasure")
        
        rew = random.choice([50, 100, 0, 150])
        embed = discord.Embed(title="💎 الكنز المفقود", color=discord.Color.gold())
        if rew > 0:
            tot = add_points(self.guild_id, self.user_id, rew)
            embed.description = f"🏴‍☠️ وجدت صندوق كنز يحتوي على **{rew}** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "⛏️ لم تجد سوى الصخور والغبار."
        await interaction.response.edit_message(embed=embed, view=None)

# 10. بلنتي (ركلة جزاء)
class PenaltyView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="⚽ تسديد يمين", style=discord.ButtonStyle.blurple)
    async def r(self, interaction: discord.Interaction, button: discord.ui.Button): await self.kick(interaction, "يمين")
    @discord.ui.button(label="⚽ تسديد يسار", style=discord.ButtonStyle.blurple)
    async def l(self, interaction: discord.Interaction, button: discord.ui.Button): await self.kick(interaction, "يسار")
    @discord.ui.button(label="⚽ تسديد بالمنتصف", style=discord.ButtonStyle.blurple)
    async def m(self, interaction: discord.Interaction, button: discord.ui.Button): await self.kick(interaction, "منتصف")

    async def kick(self, interaction, dir):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "penalty")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "penalty")
        
        gk = random.choice(["يمين", "يسار", "منتصف"])
        embed = discord.Embed(title="⚽ ركلة جزاء", color=discord.Color.green())
        if dir != gk:
            tot = add_points(self.guild_id, self.user_id, 40)
            embed.description = f"⚽ **هدف ساحق!** الحارس طار للاتجاه الخاطئ ({gk}). ربحت **40** نقطة! (الرصيد: {tot})"
        else:
            embed.description = f"🧤 تصدى الحارس للكرة ببراعة!"
        await interaction.response.edit_message(embed=embed, view=None)

# 11. كرة السلة
class BasketballView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🏀 رامية ثلاثية", style=discord.ButtonStyle.orange)
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "basketball")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "basketball")
        
        success = random.choice([True, False, True])
        embed = discord.Embed(title="🏀 كرة السلة", color=discord.Color.orange())
        if success:
            tot = add_points(self.guild_id, self.user_id, 35)
            embed.description = f"🎯 سلة تاريخية! ثلاث نقاط ذهبية وربحت **35** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "❌ اصطدمت الكرة بالحافة وخرجت."
        await interaction.response.edit_message(embed=embed, view=None)

# 12. صيد السمك
class FishingView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🎣 رمي الصنارة", style=discord.ButtonStyle.primary)
    async def fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "fishing")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "fishing")
        
        catch = random.choice([20, 50, 0, 80])
        embed = discord.Embed(title="🎣 صيد السمك", color=discord.Color.blue())
        if catch > 0:
            tot = add_points(self.guild_id, self.user_id, catch)
            embed.description = f"🐟 اصطدت سمكة قيمة وربحت **{catch}** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "🌊 لم تسحب سوى الأعشاب البحرية."
        await interaction.response.edit_message(embed=embed, view=None)

# 13. سباق السيارات
class RacingView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="🏎️ ضغط وقود", style=discord.ButtonStyle.red)
    async def race(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "racing")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "racing")
        
        win = random.choice([True, False])
        embed = discord.Embed(title="🏎️ سباق السيارات", color=discord.Color.dark_red())
        if win:
            tot = add_points(self.guild_id, self.user_id, 45)
            embed.description = f"🏆 قطعت خط النهاية أولاً وربحت **45** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "💥 تعطلت سيارتك في المنعطف الأخير."
        await interaction.response.edit_message(embed=embed, view=None)

# 14. التعدين
class MiningView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="⛏️ تعدين ذهب", style=discord.ButtonStyle.secondary)
    async def mine(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "mining")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "mining")
        
        gold = random.choice([30, 60, 90, 0])
        embed = discord.Embed(title="⛏️ التعدين", color=discord.Color.dark_gray())
        if gold > 0:
            tot = add_points(self.guild_id, self.user_id, gold)
            embed.description = f"🪙 استخرجت قطع ذهبية بقيمة **{gold}** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "🪨 حفرت في صخور صلبة ولم تجد شيئاً."
        await interaction.response.edit_message(embed=embed, view=None)

# 15. المبارزة
class DuelView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="⚔️ هجوم بالساحة", style=discord.ButtonStyle.red)
    async def duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ ليس لك!", ephemeral=True)
            return
        can, rem = check_cooldown(self.guild_id, self.user_id, "duel")
        if not can:
            await interaction.response.send_message(f"⏳ ينتظر {rem}", ephemeral=True)
            return
        set_cooldown(self.guild_id, self.user_id, "duel")
        
        win = random.choice([True, False])
        embed = discord.Embed(title="⚔️ ساحة المبارزة", color=discord.Color.blurple())
        if win:
            tot = add_points(self.guild_id, self.user_id, 60)
            embed.description = f"🛡️ انتصرت على خصمك الشرس في المعركة! ربحت **60** نقطة! (الرصيد: {tot})"
        else:
            embed.description = "🩸 هُزمت في الساحة، انسحب لتتعافى."
        await interaction.response.edit_message(embed=embed, view=None)


# --- معالجة الأوامر والرسائل والألعاب ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    text_lower = text.lower()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    config = get_config(guild_id)

    # أمر دخول
    if text_lower == "دخول":
        if config.get("records_channel") and message.channel.id != config["records_channel"]:
            await message.delete()
            return
        today = datetime.now().strftime("%Y-%m-%d")
        data = get_user_data(guild_id, user_id)
        if data["last_checkin"] == today:
            await message.channel.send(f"⚠️ يا {message.author.mention}، سجلت دخولك اليوم مسبقاً!")
        else:
            cnt = data["checkins_count"] + 1
            update_user_data(guild_id, user_id, last_checkin=today, checkins_count=cnt)
            await message.channel.send(f"📥 **تم تسجيل الحضور** يا {message.author.mention}!\nالمجموع: **{cnt}**")

    # أمر خروج
    elif text_lower == "خروج":
        if config.get("records_channel") and message.channel.id != config["records_channel"]:
            await message.delete()
            return
        today = datetime.now().strftime("%Y-%m-%d")
        data = get_user_data(guild_id, user_id)
        if data["last_leave"] == today:
            await message.channel.send(f"⚠️ يا {message.author.mention}، سجلت خروجك اليوم مسبقاً!")
        else:
            cnt = data["manual_leaves_count"] + 1
            update_user_data(guild_id, user_id, last_leave=today, manual_leaves_count=cnt)
            await message.channel.send(f"📤 **تم تسجيل الخروج** يا {message.author.mention}!\nالمجموع: **{cnt}**")

    # أمر سجل
    elif text_lower.startswith("سجل"):
        if config.get("records_channel") and message.channel.id != config["records_channel"]:
            await message.delete()
            return
        target = message.mentions[0] if message.mentions else message.author
        data = get_user_data(guild_id, target.id)
        embed = discord.Embed(title=f"📊 سجل الحضور لـ {target.display_name}", color=discord.Color.green())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="📥 الدخول", value=f"**{data['checkins_count']}**", inline=False)
        embed.add_field(name="📤 الخروج", value=f"**{data['manual_leaves_count']}**", inline=False)
        await message.channel.send(embed=embed)

    # أمر نقاطي
    elif text_lower == "نقاطي":
        data = get_user_data(guild_id, user_id)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{data['points']}** نقطة.")

    # أمر التوب (أكثر الأعضاء نقاطاً)
    elif text_lower in ["توب", "!top", "top"]:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, points FROM users WHERE guild_id = ? ORDER BY points DESC LIMIT 10", (guild_id,))
        top_users = cursor.fetchall()
        conn.close()

        embed = discord.Embed(title="🏆 قائمة لوحة الشرف (Top 10)", description="أكثر الأعضاء جمعاً للننقاط في السيرفر:", color=discord.Color.gold())
        
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

    # تشغيل الألعاب الـ 15 التفاعلية
    else:
        if config.get("games_channel") and message.channel.id != config["games_channel"]:
            pass

        if text_lower == "عجلة":
            await message.channel.send(embed=discord.Embed(title="🎡 عجلة الحظ الكبرى", description=f"يا {message.author.mention}, اضغط للتدوير:", color=discord.Color.gold()), view=WheelView(guild_id, user_id))
        elif text_lower in ["نرد", "زهر"]:
            await message.channel.send(embed=discord.Embed(title="🎲 تحدي النرد", description=f"يا {message.author.mention}, اضغط للرمي:", color=discord.Color.blue()), view=DiceView(guild_id, user_id))
        elif text_lower == "صناديق":
            await message.channel.send(embed=discord.Embed(title="📦 فتح الصناديق", description=f"يا {message.author.mention}, اختر صندوقاً:", color=discord.Color.purple()), view=BoxesView(guild_id, user_id))
        elif text_lower in ["مقص", "حجر ورقة مقص"]:
            await message.channel.send(embed=discord.Embed(title="✂️ حجر ورقة مقص", description=f"يا {message.author.mention}, اختر سلاحك:", color=discord.Color.teal()), view=RpsView(guild_id, user_id))
        elif text_lower == "تخمين":
            await message.channel.send(embed=discord.Embed(title="🔢 تخمين الرقم (من 1 إلى 5)", description=f"يا {message.author.mention}, خمن الرقم الصحيح:", color=discord.Color.dark_blue()), view=GuessView(guild_id, user_id))
        elif text_lower == "حظك":
            await message.channel.send(embed=discord.Embed(title="🔮 حظك اليوم", description=f"يا {message.author.mention}, اكتشف حظك:", color=discord.Color.magenta()), view=LuckView(guild_id, user_id))
        elif text_lower == "تحدي السرعة":
            await message.channel.send(embed=discord.Embed(title="⚡ تحدي السرعة", description=f"يا {message.author.mention}, اثبت سرعتك:", color=discord.Color.red()), view=SpeedView(guild_id, user_id))
        elif text_lower == "حساب":
            n1, n2 = random.randint(1, 20), random.randint(1, 20)
            res = n1 + n2
            is_true = random.choice([True, False])
            fake_res = res if is_true else res + random.choice([-2, 2, 3])
            await message.channel.send(embed=discord.Embed(title="🧮 لعبة الحساب السريع", description=f"يا {message.author.mention}, هل المعادلة التالية صحيحة؟\n**{n1} + {n2} = {fake_res}**", color=discord.Color.orange()), view=MathView(guild_id, user_id, is_true))
        elif text_lower == "كنز":
            await message.channel.send(embed=discord.Embed(title="💎 الكنز المفقود", description=f"يا {message.author.mention}, ابدأ الحفر:", color=discord.Color.gold()), view=TreasureView(guild_id, user_id))
        elif text_lower == "بلنتي":
            await message.channel.send(embed=discord.Embed(title="⚽ ركلة جزاء", description=f"يا {message.author.mention}, اختر زاوية التسديد:", color=discord.Color.green()), view=PenaltyView(guild_id, user_id))
        elif text_lower == "سلة":
            await message.channel.send(embed=discord.Embed(title="🏀 كرة السلة", description=f"يا {message.author.mention}, صوب السلة:", color=discord.Color.orange()), view=BasketballView(guild_id, user_id))
        elif text_lower == "صيد":
            await message.channel.send(embed=discord.Embed(title="🎣 صيد السمك", description=f"يا {message.author.mention}, ارمِ الصنارة:", color=discord.Color.blue()), view=FishingView(guild_id, user_id))
        elif text_lower == "سيارات":
            await message.channel.send(embed=discord.Embed(title="🏎️ سباق السيارات", description=f"يا {message.author.mention}, انطلق بالسباق:", color=discord.Color.dark_red()), view=RacingView(guild_id, user_id))
        elif text_lower == "تعدين":
            await message.channel.send(embed=discord.Embed(title="⛏️ التعدين", description=f"يا {message.author.mention}, ابدأ التنقيب:", color=discord.Color.dark_gray()), view=MiningView(guild_id, user_id))
        elif text_lower == "مبارزة":
            await message.channel.send(embed=discord.Embed(title="⚔️ ساحة المبارزة", description=f"يا {message.author.mention}, ادخل المبارزة:", color=discord.Color.blurple()), view=DuelView(guild_id, user_id))

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("خطأ: التوكن غير موجود!")
