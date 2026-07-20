import discord
from discord.ext import commands
import sqlite3
import random
import asyncio

DB_FILE = "database.db"

def get_config(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT games_channel FROM config WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return int(row[0])
    return 1528588181371490344

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

# --- نظام تحدي النرد بين عضوين ---
class DiceAcceptView(discord.ui.View):
    def __init__(self, challenger, target, amount, guild_id):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.target = target
        self.amount = amount
        self.guild_id = guild_id
        self.value = None

    @discord.ui.button(label="قبول التحدي 🎲", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ هذا التحدي ليس موجهاً لك!", ephemeral=True)
        
        target_pts = get_user_data(self.guild_id, self.target.id)
        challenger_pts = get_user_data(self.guild_id, self.challenger.id)
        
        if target_pts < self.amount or challenger_pts < self.amount:
            return await interaction.response.edit_message(content="❌ ألغي التحدي لعدم كفاية رصيد أحد الطرفين!", embed=None, view=None)
        
        add_points(self.guild_id, self.challenger.id, -self.amount)
        add_points(self.guild_id, self.target.id, -self.amount)
        
        c_roll = random.randint(1, 6)
        t_roll = random.randint(1, 6)
        
        desc = f"🎲 **نتائج تحدي النرد**:\n\n{self.challenger.mention} رمى النرد وحصل على: `{c_roll}`\n{self.target.mention} رمى النرد وحصل على: `{t_roll}`\n\n"
        
        if c_roll > t_roll:
            total_prize = self.amount * 2
            add_points(self.guild_id, self.challenger.id, total_prize)
            desc += f"🏆 الفائز هو {self.challenger.mention} وقد ربح `{total_prize}` نقطة!"
        elif t_roll > c_roll:
            total_prize = self.amount * 2
            add_points(self.guild_id, self.target.id, total_prize)
            desc += f"🏆 الفائز هو {self.target.mention} وقد ربح `{total_prize}` نقطة!"
        else:
            add_points(self.guild_id, self.challenger.id, self.amount)
            add_points(self.guild_id, self.target.id, self.amount)
            desc += "🤝 تعادل! تم إرجاع النقاط للطرفين."
            
        await interaction.response.edit_message(embed=discord.Embed(title="⚔️ نتيجة معركة النرد", description=desc, color=discord.Color.gold()), view=None)
        self.stop()

    @discord.ui.button(label="رفض ❌", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ ليس مسموحاً لك الرفض!", ephemeral=True)
        await interaction.response.edit_message(content=f"❌ قام {self.target.mention} برفض تحدي النرد.", embed=None, view=None)
        self.stop()

# --- نظام لعبة التحدي التفاعلية بين الأعضاء ---
class GameSelectionDropdown(discord.ui.Select):
    def __init__(self, challenger, target, amount, guild_id):
        self.challenger = challenger
        self.target = target
        self.amount = amount
        self.guild_id = guild_id
        
        options = [
            discord.SelectOption(label="حجر ورقة مقص", description="لعبة الكلاسيكية السريعة", emoji="✂️"),
            discord.SelectOption(label="سباق السرعة والتركيز", description="أيهما أسرع في الضغط", emoji="⚡"),
            discord.SelectOption(label="عجلة الحظ الكبرى", description="اختر رقماً حظك يقرره", emoji="🎡")
        ]
        super().__init__(placeholder="اختر نوع اللعبة للتحدي...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ الخصم فقط هو من يمكنه اختيار اللعبة!", ephemeral=True)
        
        game_choice = self.values[0]
        target_pts = get_user_data(self.guild_id, self.target.id)
        challenger_pts = get_user_data(self.guild_id, self.challenger.id)
        
        if target_pts < self.amount or challenger_pts < self.amount:
            return await interaction.response.edit_message(content="❌ ألغي التحدي لعدم كفاية الرصيد لدى أحد الطرفين.", embed=None, view=None)
        
        add_points(self.guild_id, self.challenger.id, -self.amount)
        add_points(self.guild_id, self.target.id, -self.amount)
        
        total_prize = self.amount * 2
        winner = random.choice([self.challenger, self.target])
        loser = self.target if winner == self.challenger else self.challenger
        
        add_points(self.guild_id, winner.id, total_prize)
        
        desc = f"🎮 تم اختيار لعبة: **{game_choice}**\n\n" \
               f"⚔️ التحدي دار بين {self.challenger.mention} و {self.target.mention}\n" \
               f"🏆 **الفائز:** {winner.mention}\n" \
               f"💸 **الخاسر:** {loser.mention}\n" \
               f"💰 حصل الفائز على جائزة قدرها **{total_prize}** نقطة!"
               
        await interaction.response.edit_message(embed=discord.Embed(title="🔥 نتيجة التحدي التفاعلي", description=desc, color=discord.Color.green()), view=None)

class ChallengeGameAcceptView(discord.ui.View):
    def __init__(self, challenger, target, amount, guild_id):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.target = target
        self.amount = amount
        self.guild_id = guild_id

    @discord.ui.button(label="قبول التحدي والتاريخ 🎮", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ هذا التحدي ليس لك!", ephemeral=True)
        
        view = discord.ui.View(timeout=30)
        view.add_item(GameSelectionDropdown(self.challenger, self.target, self.amount, self.guild_id))
        await interaction.response.edit_message(content=f"✅ قبل {self.target.mention} التحدي! الآن يرجى منه اختيار اللعبة من القائمة أدناه:", embed=None, view=view)

    @discord.ui.button(label="رفض ❌", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ ليس مسموحاً لك بالرفض!", ephemeral=True)
        await interaction.response.edit_message(content=f"❌ رفض {self.target.mention} التحدي.", embed=None, view=None)
        self.stop()

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        allowed_channel = get_config(guild_id)

        # أوامر النرد وتحدي النرد
        if text.startswith("نرد ") or text.startswith("/نرد "):
            parts = message.content.strip().split()
            if len(parts) >= 2 and message.mentions:
                target = message.mentions[0]
                if target.id == user_id:
                    return await message.channel.send("❌ لا يمكنك تحدي نفسك!", delete_after=5)
                if len(parts) < 3:
                    return await message.channel.send("❌ يرجى تحديد مبلغ الرهان للنرد. مثال: `نرد @الشخص 50`", delete_after=5)
                try:
                    amount = int(parts[2])
                except ValueError:
                    return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ.", delete_after=5)
                
                if amount <= 0:
                    return await message.channel.send("❌ يجب أن يكون الرهان أكبر من صفر.", delete_after=5)
                
                user_pts = get_user_data(guild_id, user_id)
                if user_pts < amount:
                    return await message.channel.send(f"❌ رصيدك ({user_pts}) لا يكفي للرهان بهذا المبلغ!", delete_after=5)
                
                view = DiceAcceptView(message.author, target, amount, guild_id)
                embed = discord.Embed(title="🎲 تحدي نرد بين العضوين", description=f"{message.author.mention} يحدي {target.mention} في لعبة النرد بمبلغ **{amount}** نقطة!\nهل توافق على التحدي؟", color=discord.Color.blue())
                return await message.channel.send(content=target.mention, embed=embed, view=view)

        # أوامر تحدي عامة بين الأعضاء
        if text.startswith("تحدي ") or text.startswith("/تحدي "):
            parts = message.content.strip().split()
            if len(parts) >= 2 and message.mentions:
                target = message.mentions[0]
                if target.id == user_id:
                    return await message.channel.send("❌ لا يمكنك تحدي نفسك!", delete_after=5)
                if len(parts) < 3:
                    return await message.channel.send("❌ يرجى تحديد مبلغ الرهان للتحدي. مثال: `تحدي @الشخص 100`", delete_after=5)
                try:
                    amount = int(parts[2])
                except ValueError:
                    return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ.", delete_after=5)
                
                if amount <= 0:
                    return await message.channel.send("❌ يجب أن يكون الرهان أكبر من صفر.", delete_after=5)
                
                user_pts = get_user_data(guild_id, user_id)
                if user_pts < amount:
                    return await message.channel.send(f"❌ رصيدك ({user_pts}) لا يكفي للرهان بهذا المبلغ!", delete_after=5)
                
                view = ChallengeGameAcceptView(message.author, target, amount, guild_id)
                embed = discord.Embed(title="⚔️ طلب تحدي تفاعلي جديد", description=f"{message.author.mention} يرسل تحدياً تفاعلياً إلى {target.mention} بمبلغ **{amount}** نقطة!\nاختر القبول للبدء واختيار اللعبة:", color=discord.Color.red())
                return await message.channel.send(content=target.mention, embed=embed, view=view)

        # ألعاب فردية بسيطة
        if text in ["حظ", "/حظ", "روليت"]:
            user_pts = get_user_data(guild_id, user_id)
            if user_pts < 20:
                return await message.channel.send("❌ تحتاج إلى 20 نقطة على الأقل للعب الحظ!", delete_after=5)
            
            add_points(guild_id, user_id, -20)
            roll = random.randint(1, 100)
            if roll > 60:
                reward = 50
                new_tot = add_points(guild_id, user_id, reward)
                await message.channel.send(f"🎉 مبروك! حصلت على رقم حظ `{roll}` وربحت **{reward}** نقطة!\nرصيدك الآن: `{new_tot}`")
            else:
                new_tot = get_user_data(guild_id, user_id)
                await message.channel.send(f"😢 حظاً أوفر! رقم الحظ كان `{roll}` وخسرت 20 نقطة.\nرصيدك الآن: `{new_tot}`")
            return

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
