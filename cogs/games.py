import os
import sqlite3
import discord
from discord.ext import commands
import random
from datetime import datetime, timedelta

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

    @discord.ui.button(label="قبول التحدي 🎮", style=discord.ButtonStyle.green)
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

BASE_MARKET_ITEMS = {
    "سيف أسطوري": 300,
    "درع الماس": 250,
    "صندوق سري نادر": 150,
    "مفتاح ذهبي": 100,
    "جرعة حظ": 75,
    "سيارة سباق فارهة": 600
}

def update_and_get_market_prices(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, price FROM market_prices WHERE guild_id = ?", (str(guild_id),))
    rows = cursor.fetchall()
    current_prices = {row[0]: row[1] for row in rows}
    
    for item, base_price in BASE_MARKET_ITEMS.items():
        if item not in current_prices:
            current_prices[item] = base_price
        else:
            change_percent = random.uniform(-0.20, 0.25)
            new_price = int(current_prices[item] * (1 + change_percent))
            if new_price < 20: 
                new_price = 20
            current_prices[item] = new_price
        cursor.execute("INSERT OR REPLACE INTO market_prices (guild_id, item_name, price) VALUES (?, ?, ?)", (str(guild_id), item, current_prices[item]))
    conn.commit()
    conn.close()
    return current_prices

def get_user_inventory(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND quantity > 0", (str(guild_id), str(user_id)))
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def add_to_inventory(guild_id, user_id, item_name, qty):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (str(guild_id), str(user_id), item_name))
    row = cursor.fetchone()
    current_qty = row[0] if row else 0
    new_qty = current_qty + qty
    cursor.execute("INSERT OR REPLACE INTO user_inventory (guild_id, user_id, item_name, quantity) VALUES (?, ?, ?, ?)", (str(guild_id), str(user_id), item_name, new_qty))
    conn.commit()
    conn.close()

def remove_from_inventory(guild_id, user_id, item_name, qty):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (str(guild_id), str(user_id), item_name))
    row = cursor.fetchone()
    if not row or row[0] < qty:
        conn.close()
        return False
    new_qty = row[0] - qty
    cursor.execute("UPDATE user_inventory SET quantity = ? WHERE guild_id = ? AND user_id = ? AND item_name = ?", (new_qty, str(guild_id), str(user_id), item_name))
    conn.commit()
    conn.close()
    return True

class MarketSelect(discord.ui.Select):
    def __init__(self, items, mode, guild_id, user_id):
        self.mode = mode
        self.g_id = guild_id
        self.u_id = user_id
        options = []
        for name in items:
            if len(options) < 25:
                options.append(discord.SelectOption(label=name[:100], value=name[:100]))
        super().__init__(placeholder="اختر الغرض من القائمة..." if mode == "buy" else "اختر الغرض لبيعه...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.u_id):
            return await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
        selected_item = self.values[0]
        if self.mode == "buy":
            prices = update_and_get_market_prices(self.g_id)
            price = prices.get(selected_item, 50)
            view = QuantitySelectView(self.g_id, self.u_id, selected_item, price, "buy")
            await interaction.response.edit_message(embed=discord.Embed(title="🛒 حدد كمية الشراء", description=f"الغرض المختار: **{selected_item}**\nسعر القطعة: **{price}** نقطة.\nاختر الكمية المطلوبة:", color=discord.Color.gold()), view=view)
        else:
            inv = get_user_inventory(self.g_id, self.u_id)
            qty = inv.get(selected_item, 0)
            prices = update_and_get_market_prices(self.g_id)
            price = prices.get(selected_item, 50)
            view = QuantitySelectView(self.g_id, self.u_id, selected_item, price, "sell", max_qty=qty)
            await interaction.response.edit_message(embed=discord.Embed(title="💸 حدد كمية البيع", description=f"الغرض المختار: **{selected_item}**\nالمتوفر لديك: **{qty}**\nاختر الكمية للبيع:", color=discord.Color.purple()), view=view)

class QuantitySelect(discord.ui.Select):
    def __init__(self, item_name, price, mode, max_qty=50):
        self.item_name = item_name
        self.price = price
        self.mode = mode
        limit = 50 if mode == "buy" else min(50, max_qty)
        options = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, limit + 1)]
        super().__init__(placeholder="اختر الكمية (الحد الأقصى 50)...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        qty = int(self.values[0])
        view: QuantitySelectView = self.view
        if str(interaction.user.id) != str(view.u_id):
            return await interaction.response.send_message("❌ ليست لك!", ephemeral=True)
        
        g_id = view.g_id
        u_id = view.u_id
        
        if self.mode == "buy":
            total_cost = self.price * qty
            user_pts = get_user_data(g_id, u_id)
            if user_pts < total_cost:
                return await interaction.response.edit_message(embed=discord.Embed(title="❌ خطأ", description=f"رصيدك ({user_pts}) لا يكفي لشراء `{qty}` من **{self.item_name}** بتكلفة `{total_cost}` نقطة!", color=discord.Color.red()), view=None)
            add_points(g_id, u_id, -total_cost)
            add_to_inventory(g_id, u_id, self.item_name, qty)
            new_tot = get_user_data(g_id, u_id)
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 نجاح الشراء", description=f"تم شراء `{qty}` من **{self.item_name}** بقيمة `{total_cost}` نقطة!\nرصيدك الحالي: **{new_tot}** نقطة.", color=discord.Color.green()), view=None)
        else:
            success = remove_from_inventory(g_id, u_id, self.item_name, qty)
            if not success:
                return await interaction.response.edit_message(embed=discord.Embed(title="❌ خطأ", description="الكمية غير متوفرة في حقيبتك!", color=discord.Color.red()), view=None)
            total_earned = int(self.price * 0.8 * qty)
            if total_earned < 1: 
                total_earned = qty * 10
            new_tot = add_points(g_id, u_id, total_earned)
            await interaction.response.edit_message(embed=discord.Embed(title="💸 نجاح البيع", description=f"تم بيع `{qty}` من **{self.item_name}** واسترداد **{total_earned}** نقطة!\nرصيدك الحالي: **{new_tot}** نقطة.", color=discord.Color.green()), view=None)

class QuantitySelectView(discord.ui.View):
    def __init__(self, g_id, u_id, item_name, price, mode, max_qty=50):
        super().__init__(timeout=60)
        self.g_id = g_id
        self.u_id = u_id
        self.add_item(QuantitySelect(item_name, price, mode, max_qty))

class TransferSelect(discord.ui.Select):
    def __init__(self, items, g_id, u_id, target_id):
        self.g_id = g_id
        self.u_id = u_id
        self.target_id = target_id
        options = [discord.SelectOption(label=f"{name} (الكمية: {qty})", value=name) for name, qty in items.items() if qty > 0]
        super().__init__(placeholder="اختر الغرض المطلوب تحويله...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.u_id):
            return await interaction.response.send_message("❌ ليست لك!", ephemeral=True)
        item_name = self.values[0]
        view = TransferQtyView(self.g_id, self.u_id, self.target_id, item_name)
        await interaction.response.edit_message(embed=discord.Embed(title="📦 تحديد كمية التحويل", description=f"الغرض: **{item_name}**\nاختر الكمية المراد تحويلها:", color=discord.Color.blue()), view=view)

class TransferQtySelect(discord.ui.Select):
    def __init__(self, g_id, u_id, target_id, item_name):
        self.g_id = g_id
        self.u_id = u_id
        self.target_id = target_id
        self.item_name = item_name
        inv = get_user_inventory(g_id, u_id)
        max_q = inv.get(item_name, 1)
        options = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, min(51, max_q + 1))]
        super().__init__(placeholder="اختر الكمية...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.u_id):
            return await interaction.response.send_message("❌ ليست لك!", ephemeral=True)
        qty = int(self.values[0])
        success = remove_from_inventory(self.g_id, self.u_id, self.item_name, qty)
        if not success:
            return await interaction.response.edit_message(embed=discord.Embed(title="❌ خطأ", description="فشل التحويل لعدم كفاية الكمية.", color=discord.Color.red()), view=None)
        add_to_inventory(self.g_id, self.target_id, self.item_name, qty)
        target_member = interaction.guild.get_member(int(self.target_id))
        target_name = target_member.mention if target_member else "المستخدم"
        await interaction.response.edit_message(embed=discord.Embed(title="✅ تم التحويل بنجاح", description=f"تم تحويل `{qty}` من **{self.item_name}** إلى {target_name} بنجاح!", color=discord.Color.green()), view=None)

class TransferQtyView(discord.ui.View):
    def __init__(self, g_id, u_id, target_id, item_name):
        super().__init__(timeout=60)
        self.add_item(TransferQtySelect(g_id, u_id, target_id, item_name))

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

        if text in ["اسعار", "الأسعار", "/اسعار", "أسعار"]:
            prices = update_and_get_market_prices(guild_id)
            embed = discord.Embed(title="📈 سُوق المِزَاد العَالَمِي", description="إليك أسعار الأغراض الحالية:", color=discord.Color.gold())
            for item, price in prices.items():
                embed.add_field(name=item, value=f"💰 **{price}** نقطة", inline=True)
            await message.channel.send(embed=embed)
            return

        if text in ["شراء", "/شراء"]:
            prices = update_and_get_market_prices(guild_id)
            view = discord.ui.View(timeout=60)
            view.add_item(MarketSelect(list(prices.keys()), "buy", guild_id, user_id))
            await message.channel.send(embed=discord.Embed(title="🛒 متجر الشراء التفاعلي", description="اختر الغرض الذي تريد شراءه من القائمة أدناه:", color=discord.Color.gold()), view=view)
            return

        if text in ["بيع", "/بيع"]:
            inv = get_user_inventory(guild_id, user_id)
            if not inv:
                return await message.channel.send("❌ حقيبتك فارغة تماماً ولا توجد ممتلكات لبيعها!", delete_after=5)
            view = discord.ui.View(timeout=60)
            view.add_item(MarketSelect(list(inv.keys()), "sell", guild_id, user_id))
            await message.channel.send(embed=discord.Embed(title="💸 سوق البيع التفاعلي", description="اختر الغرض الذي تريد بيعه من ممتلكاتك:", color=discord.Color.purple()), view=view)
            return

        if text.startswith("تحويل ") or text.startswith("/تحويل "):
            parts = message.content.strip().split()
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح:\n• لتحويل أغراض: `تحويل @الشخص اغراض`\n• لتحويل نقاط: `تحويل @الشخص نقاط`", delete_after=5)
            
            target_user = message.mentions[0]
            if target_user.id == user_id:
                return await message.channel.send("❌ لا يمكنك التحويل لنفسك!", delete_after=5)
            
            sub_type = parts[2].lower()
            if "اغراض" in sub_type or "أغراض" in sub_type or "ممتلكات" in sub_type:
                inv = get_user_inventory(guild_id, user_id)
                if not inv:
                    return await message.channel.send("❌ ليس لديك أي أغراض لتحويلها!", delete_after=5)
                view = discord.ui.View(timeout=60)
                view.add_item(TransferSelect(inv, guild_id, user_id, target_user.id))
                await message.channel.send(embed=discord.Embed(title="🔄 تحويل الأغراض والممتلكات", description=f"المرسل إليه: {target_user.mention}\nاختر الغرض المراد تحويله:", color=discord.Color.blue()), view=view)
                return

            elif "نقاط" in sub_type or "رصيد" in sub_type:
                if len(parts) < 4:
                    return await message.channel.send("❌ يرجى تحديد عدد النقاط المراد تحويلها. مثال: `تحويل @الشخص نقاط 50`", delete_after=5)
                try:
                    amount = int(parts[3])
                except ValueError:
                    return await message.channel.send("❌ يرجى كتابة رقم صحيح للنقاط.", delete_after=5)
                
                if amount <= 0:
                    return await message.channel.send("❌ يجب أن يكون المبلغ أكبر من صفر.", delete_after=5)
                
                user_pts = get_user_data(guild_id, user_id)
                if user_pts < amount:
                    return await message.channel.send(f"❌ رصيدك الحالي ({user_pts}) لا يكفي لتحويل `{amount}` نقطة!", delete_after=5)
                
                add_points(guild_id, user_id, -amount)
                add_points(guild_id, target_user.id, amount)
                new_tot = get_user_data(guild_id, user_id)
                await message.channel.send(f"✅ تم تحويل **{amount}** نقطة بنجاح إلى {target_user.mention}!\nرصيدك الحالي: `{new_tot}` نقطة.")
                return

        if text in ["ممتلكات", "/ممتلكات", "حقيبتي", "أغراضي"]:
            inv = get_user_inventory(guild_id, user_id)
            embed = discord.Embed(title=f"🎒 مُمْتَلَكَات وحَقِيبَة {message.author.display_name}", color=discord.Color.purple())
            if not inv:
                embed.description = "❌ حقيبتك فارغة تماماً!"
            else:
                desc = "".join([f"• **{itm}** ⟵ الكمية: `{qty}`\n" for itm, qty in inv.items()])
                embed.description = desc
            await message.channel.send(embed=embed)
            return

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
