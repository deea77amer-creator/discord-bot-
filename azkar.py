import random
import discord
from discord.ext import commands, tasks

AZKAR_LIST = [
    "✨ **أذكار:** لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.",
    "🌿 **دعاء:** رَبِّ اغْفِرْ لِي وَلِوَالِدَيَّ وَلِمَنْ دَخَلَ بَيْتِيَ مُؤْمِناً.",
    "🌸 **ذكر:** سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ.",
    "🌙 **دعاء:** اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ.",
    "💎 **ذكر:** استغفر الله العظيم واتوب اليه.",
    "🍃 **دعاء:** رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ.",
    "✨ **ذكر:** لا حول ولا قوة إلا بالله العلي العظيم.",
    "🌟 **دعاء:** اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ."
]

class AutoAzkar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.azkar_channel_id = None
        self.send_azkar_loop.start()

    def cog_unload(self):
        self.send_azkar_loop.cancel()

    @commands.command(name="تحديد_اذكار")        
    @commands.has_permissions(administrator=True)
    async def set_azkar_channel(self, ctx):
        self.azkar_channel_id = ctx.channel.id
        await ctx.send(f"✅ تم بنجاح تعيين هذه القناة لإرسال الأدعية والأذكار كل 15 دقيقة.")

    @tasks.loop(minutes=15)
    async def send_azkar_loop(self):
        if not self.azkar_channel_id:
            return
        
        channel = self.bot.get_channel(self.azkar_channel_id)
        if channel:
            chosen = random.choice(AZKAR_LIST)
            await channel.send(f"🕊️ **تذكير إيماني:**\n{chosen}")

    @send_azkar_loop.before_loop
    async def before_azkar_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutoAzkar(bot))
