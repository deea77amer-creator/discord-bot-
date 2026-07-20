import random
import discord
from discord.ext import commands
import os
import json

DATA_FILE = "stats.json"
CONFIG_FILE = "config.json"

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_points(guild_id, user_id, amount):
    stats = load_data(DATA_FILE)
    g_id = str(guild_id)
    u_id = str(user_id)
    if g_id not in stats: stats[g_id] = {}
    if u_id not in stats[g_id]: 
        stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
    if "points" not in stats[g_id][u_id]: 
        stats[g_id][u_id]["points"] = 0
    
    stats[g_id][u_id]["points"] += amount
    save_data(stats, DATA_FILE)
    return stats[g_id][u_id]["points"]

class FunGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # أمر تحديد قناة الألعاب (إداري)
    @commands.command(name="تحديد_الألعاب")
    @commands.has_permissions(administrator=True)
    async def set_games_channel(self, ctx):
        config = load_data(CONFIG_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in config: config[guild_id] = {}
        config[guild_id]["games_channel"] = ctx.channel.id
        save_data(config, CONFIG_FILE)
        await ctx.send("✅ تم تعيين هذه القناة **للألعاب** بنجاح!")

    # قائمة الألعاب
    @commands.command(name="الالعاب")
    async def games_menu(self, ctx):
        embed = discord.Embed(
            title="🎮 | قائمة ألعاب السيرفر",
            description="جميع الألعاب تعمل **بدون رموز** مباشرة في الشات المخصص للألعاب:\n",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎡 عجلة الحظ", value="اكتب: `عجلة` (تدوير العجلة وربح نقاط)", inline=False)
        embed.add_field(name="🎲 تحدي النرد", value="اكتب: `نرد` أو `زهر` (تحدي البوت بالنرد)", inline=False)
        embed.add_field(name="📦 فتح الصناديق", value="اكتب: `صناديق` أو `كنز` (صناديق مفاجئة قد تحتوي كنز أو قنبلة)", inline=False)
        embed.add_field(name="✂️ حجر ورقة مقص", value="اكتب: `مقص حجر` (أو ورقة / مقص)", inline=False)
        embed.add_field(name="🎯 التخمين الرقمي", value="اكتب: `تخمين [رقم من 1 إلى 10]`", inline=False)
        embed.add_field(name="🔮 حظك اليوم", value="اكتب: `حظك` (لفحص حظك اليومي وكسب النقاط)", inline=False)
        embed.set_footer(text="استمتع باللعب واجمع أكبر عدد من النقاط!")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        text = message.content.strip().lower()
        guild_id = str(message.guild.id)
        
        # قائمة الكلمات المفتاحية للألعاب
        game_keywords = ["عجلة", "نرد", "زهر", "صناديق", "كنز", "مقص", "تخمين", "حظك", "الالعاب"]
        
        # تحقق هل الكلمة مطابقة للألعاب
        matched = False
        for kw in game_keywords:
            if text == kw or text.startswith(kw + " "):
                matched = True
                break
                
        if not matched:
            return

        # فحص قناة الألعاب المخصصة
        config = load_data(CONFIG_FILE)
        games_channel_id = config.get(guild_id, {}).get("games_channel")
        
        if games_channel_id and message.channel.id != games_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, الألعاب مخصصة فقط في قناة الألعاب المحددة!")
            import asyncio
            await asyncio.sleep(4)
            await warn.delete()
            return

        ctx = await self.bot.get_context(message)

        # تنفيذ الألعاب بناءً على الكلمة المدخلة
        if text == "الالعاب":
            await self.games_menu(ctx)

        elif text in ["عجلة"]:
            prizes = [10, 25, 50, 100, 200, 0, 500, 50]
            weights = [30, 25, 20, 10, 5, 5, 2, 3]
            won = random.choices(prizes, weights=weights)[0]
            
            embed = discord.Embed(title="🎡 | عجلة الحظ الكبرى", description=f"يا هلا يا {message.author.mention}, قمت بتدوير العجلة...", color=discord.Color.gold())
            if won > 0:
                total = add_points(message.guild.id, message.author.id, won)
                embed.add_field(name="النتيجة:", value=f"🎉 مبروك! ربحت **{won} نقطة**!\n💰 رصيدك الإجمالي: **{total} نقطة**")
            else:
                embed.add_field(name="النتيجة:", value=" خسارة! العجلة وقفت على الصفر، حظاً أوفر!")
            await message.channel.send(embed=embed)

        elif text in ["نرد", "زهر"]:
            user_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            
            embed = discord.Embed(title="🎲 | تحدي النرد", color=discord.Color.blue())
            embed.add_field(name=f"رقمك:", value=f"**{user_roll}**", inline=True)
            embed.add_field(name="رقم البوت:", value=f"**{bot_roll}**", inline=True)
            
            if user_roll > bot_roll:
                total = add_points(message.guild.id, message.author.id, 40)
                embed.description = f"🏆 مبروك فزت على البوت وربحت **40 نقطة**! (الرصيد: {total})"
            elif user_roll < bot_roll:
                embed.description = "❌ فاز البوت عليك! حظاً أوفر."
            else:
                total = add_points(message.guild.id, message.author.id, 10)
                embed.description = f"🤝 تعادلتم! تم منحك **10 نقاط** كمكافأة."
            await message.channel.send(embed=embed)

        elif text in ["صناديق", "كنز"]:
            boxes = ["💎 كنز ثمين (150 نقطة)", "🪙 قطعة ذهبية (50 نقطة)", "💨 صندوق فارغ", "💣 قنبلة (-20 نقطة)"]
            weights = [10, 30, 45, 15]
            result = random.choices(boxes, weights=weights)[0]
            points_map = {"💎 كنز ثمين (150 نقطة)": 150, "🪙 قطعة ذهبية (50 نقطة)": 50, "💨 صندوق فارغ": 0, "💣 قنبلة (-20 نقطة)": -20}
            won = points_map[result]
            total = add_points(message.guild.id, message.author.id, won)
            
            embed = discord.Embed(title="📦 | فتح الصناديق السرية", description=f"يا {message.author.mention}, اخترت صندوقاً وطلع لك:\n**{result}**\n\n💰 رصيدك الحالي: **{total} نقطة**", color=discord.Color.purple())
            await message.channel.send(embed=embed)

        elif text.startswith("مقص"):
            parts = message.content.strip().split()
            if len(parts) < 2 or parts[1] not in ["حجر", "ورقة", "مقص"]:
                await message.channel.send(f"⚠️ الاستخدام الصحيح:\n`مقص حجر` أو `مقص ورقة` أو `مقص مقص`")
                return
            choice = parts[1]
            bot_choice = random.choice(["حجر", "ورقة", "مقص"])
            
            embed = discord.Embed(title="✂️ | حجر، ورقة، مقص", color=discord.Color.orange())
            embed.add_field(name="اختيارك:", value=choice, inline=True)
            embed.add_field(name="اختيار البوت:", value=bot_choice, inline=True)
            
            if choice == bot_choice:
                embed.description = "🤝 تعادلنا!"
            elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
                total = add_points(message.guild.id, message.author.id, 35)
                embed.description = f"🎉 مبروك فزت! ربحت **35 نقطة** (الرصيد: {total})"
            else:
                embed.description = "❌ خسرت أمام البوت!"
            await message.channel.send(embed=embed)

        elif text.startswith("تخمين"):
            parts = message.content.strip().split()
            if len(parts) < 2 or not parts[1].isdigit():
                await message.channel.send(f"⚠️ الاستخدام الصحيح:\n`تخمين 7` (اختر رقماً من 1 إلى 10)")
                return
            number = int(parts[1])
            if not (1 <= number <= 10):
                await message.channel.send("⚠️ أرجو اختيار رقم بين 1 و 10 فقط!")
                return
                
            secret = random.randint(1, 10)
            if number == secret:
                total = add_points(message.guild.id, message.author.id, 100)
                await message.channel.send(f"🎯 كفووو يا {message.author.mention}! الرقم الصحيح كان **{secret}**، ربحت جائزة كبرى **100 نقطة**! (الرصيد: {total})")
            else:
                await message.channel.send(f"❌ للأسف تخمينك خطأ. الرقم الصحيح كان **{secret}**، حظاً أوفر!")

        elif text in ["حظك", "حظك_اليوم"]:
            fortunes = [
                ("حظك ممتاز اليوم! ربحت 60 نقطة.", 60),
                ("يومك سعيد، استمتع بـ 30 نقطة.", 30),
                ("الأمور عادية، خذ 10 نقاط.", 10),
                ("اليوم يحمل لك مفاجأة! ربحت 80 نقطة.", 80),
                ("حظك سيء اليوم، ما ربحت شيء.", 0)
            ]
            text_result, prize = random.choice(fortunes)
            total = add_points(message.guild.id, message.author.id, prize)
            
            embed = discord.Embed(title="🔮 | طالع حظك اليوم", description=f"{message.author.mention}\n{text_result}\n\n💰 رصيدك الإجمالي: **{total} نقطة**", color=discord.Color.teal())
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FunGames(bot))
