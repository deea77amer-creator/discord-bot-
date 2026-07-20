import discord
from discord.ext import commands
import sqlite3

DB_FILE = "database.db"

def get_user_data(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    conn.close()
    return {"points": row[0] if row else 1000}

def add_points(guild_id, user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE guild_id = ? AND user_id = ?", (amount, str(guild_id), str(user_id)))
    conn.commit()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    new_points = cursor.fetchone()[0]
    conn.close()
    return new_points

AUCTION_ITEMS = [
    {"id": 1, "name": "🚗 سيارة رياضية خارقة", "price": 12000, "desc": "سيارة سرعة فائقة وتصميم عصري فريد."},
    {"id": 2, "name": "🛥️ يخت فاخر للأمراء", "price": 45000, "desc": "يخت بحري مجهز بالكامل للرحلات الفاخرة."},
    {"id": 3, "name": "🏰 قصر ملكي تاريخي", "price": 100000, "desc": "قصر واسع يضم حدائق ومرافق أسطورية."},
    {"id": 4, "name": "🚁 طائرة هليكوبتر خاصة", "price": 75000, "desc": "طائرة جوية للسفر السريع بين المدن."},
    {"id": 5, "name": "⌚ ساعة رولكس ذهبية مرصعة", "price": 8500, "desc": "ساعة فخمة تزيد من هيبتك في السيرفر."},
    {"id": 6, "name": "🗡️ سيف نادرة الأسطوري", "price": 5000, "desc": "سيف تاريخي معزز لقوة المحاربين."},
    {"id": 7, "name": "🏢 برج تجاري في وسط المدينة", "price": 150000, "desc": "استثمار ضخم يدر عليك أرباحاً طائلة."},
    {"id": 8, "name": "🏍️ دراجة نارية سريعة جداً", "price": 3500, "desc": "دراجة مخصصة لسباقات الشوارع الحماسية."},
    {"id": 9, "name": "💎 جوهرة الألماس الزرقاء النادرة", "price": 25000, "desc": "قطعة ألماس صافية وعالية القيمة."},
    {"id": 10, "name": "🦁 حيوان أليف مفترس (أسد ملكي)", "price": 60000, "desc": "مرافق قوي ومخلص يحمي ممتلكاتك."}
]

class AuctionSelect(discord.ui.Select):
    def __init__(self, guild_id, user_id):
        self.guild_id = guild_id
        self.user_id = user_id
        options = [discord.SelectOption(label=f"{i['name']} ({i['price']} نقطة)", value=str(i['id']), description=i['desc'][:50]) for i in AUCTION_ITEMS]
        super().__init__(placeholder="اختر السلعة التي تريد شراءها من المزاد...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
            return
        item_id = int(self.values[0])
        item = next(i for i in AUCTION_ITEMS if i["id"] == item_id)
        user_data = get_user_data(self.guild_id, self.user_id)
        embed = discord.Embed(title="🛒 نظام المزاد", color=discord.Color.gold())
        if user_data["points"] >= item["price"]:
            new_bal = add_points(self.guild_id, self.user_id, -item["price"])
            embed.description = f"🎉 مبروك يا {interaction.user.mention}! اشتريت **{item['name']}** بنجاح!\n• السعر المدفوع: **{item['price']}** نقطة\n• رصيدك المتبقي: **{new_bal}** نقطة"
            embed.color = discord.Color.green()
        else:
            embed.description = f"❌ عذراً، لا تمتلك نقاط كافية لشراء **{item['name']}**.\n• السعر: **{item['price']}** نقطة\n• رصيدك الحالي: **{user_data['points']}** نقطة"
            embed.color = discord.Color.red()
        await interaction.response.edit_message(embed=embed, view=None)

class AuctionView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.add_item(AuctionSelect(guild_id, user_id))

class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="مزاد")
    async def auction_cmd(self, ctx):
        embed = discord.Embed(
            title="🏛️ سوق المزاد العام للسيرفر",
            description="مرحباً بك في المزاد! اختر السلعة المناسبة لك من القائمة أدناه:",
            color=discord.Color.gold()
        )
        for item in AUCTION_ITEMS:
            embed.add_field(name=f"#{item['id']} - {item['name']}", value=f"السعر: **{item['price']}** نقطة\n{item['desc']}", inline=False)
        await ctx.send(embed=embed, view=AuctionView(ctx.guild.id, str(ctx.author.id)))

async def setup(bot):
    await bot.add_cog(AuctionCog(bot))
