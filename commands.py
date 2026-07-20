import os
import json
import discord
from discord.ext import commands

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

class TopCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر تحديد قناة التوب (مشابه لباقي أوامر التحديد عندك)
    @commands.command(name="تحديد_التوب")
    @commands.has_permissions(administrator=True)
    async def set_top(self, ctx):
        config = load_data(CONFIG_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in config: config[guild_id] = {}
        config[guild_id]["top_channel"] = ctx.channel.id
        save_data(config, CONFIG_FILE)
        await ctx.send("✅ تم تعيين هذه القناة **للوحة الترتيب (التوب)** بنجاح!")

    # 2. الاستماع لكلمة "توب" ورصد مكان القناة
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        text = message.content.strip()
        guild_id = str(message.guild.id)

        if text == "توب":
            config = load_data(CONFIG_FILE)
            top_channel_id = config.get(guild_id, {}).get("top_channel")
            
            # التحقق من أن الأمر مكتوب في قناة التوب المحددة (إذا تم تحديدها)
            if top_channel_id and message.channel.id != top_channel_id:
                await message.delete()
                warn = await message.channel.send(f"❌ عذراً {message.author.mention}, هذا الأمر مخصص فقط في قناة التوب!")
                import asyncio
                await asyncio.sleep(4)
                await warn.delete()
                return

            stats = load_data(DATA_FILE)
            guild_stats = stats.get(guild_id, {})

            if not guild_stats:
                await message.channel.send("📊 لا توجد بيانات نقاط مسجلة حتى الآن في هذا السيرفر!")
                return

            # جمع الأفراد ونقاطهم وترتيبهم تنازلياً
            users_points = []
            for user_id, data in guild_stats.items():
                points = data.get("points", 0)
                if points > 0:  # فقط من لديهم نقاط
                    users_points.append((user_id, points))

            # ترتيب من الأعلى للأقل نقاطاً
            users_points.sort(key=lambda x: x[1], reverse=True)
            top_users = users_points[:10]  # أخذ أعلى 10 أشخاص

            if not top_users:
                await message.channel.send("📊 لم يحصل أي شخص على نقاط ألعاب حتى الآن!")
                return

            desc = ""
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

            for index, (uid, pts) in enumerate(top_users):
                member = message.guild.get_member(int(uid))
                name = member.mention if member else f"مستخدم مغادر ({uid})_id"
                medal = medals[index] if index < len(medals) else f"**{index+1}.**"
                desc += f"{medal} {name} ⟵ **{pts}** نقطة\n"

            embed = discord.Embed(
                title="🏆 | لوحة الشرف وأكثر الأعضاء تفاعلاً",
                description=desc,
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"طلب بواسطة: {message.author.display_name}")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TopCommand(bot))
