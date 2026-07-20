import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.strip() == "اوامر":
            embed = discord.Embed(
                title="📜 قائمة أوامر البوت التلقائية الشاملة",
                description="مرحباً بك! إليك جميع الأوامر المتاحة حالياً في البوت:",
                color=discord.Color.blue()
            )
            
            # جلب الأوامر المسجلة في البوت تلقائياً
            commands_list = []
            for command in self.bot.commands:
                if not command.hidden:
                    commands_list.append(f"`!{command.name}`")
            
            if commands_list:
                embed.add_field(
                    name="⚙️ الأوامر المتاحة (ببادئة !)",
                    value=", ".join(commands_list),
                    inline=False
                )
            
            # إضافة الأوامر النصية المباشرة (مثل الألعاب وسجل والدخول وغيرها)
            embed.add_field(
                name="🎮 ألعاب وأوامر سريعة (بدون بادئة)",
                value="`عجلة`, `نرد`, `صناديق`, `مقص`, `تخمين`, `حظك`, `تحدي السرعة`, `حساب`, `كنز`, `بلنتي`, `سلة`, `صيد`, `سيارات`, `تعدين`, `مبارزة`\n`دخول`, `خروج`, `سجل`, `نقاطي`, `توب`",
                inline=False
            )
            
            embed.set_footer(text="تم تحديث القائمة تلقائياً | تطوير خاص لك")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
