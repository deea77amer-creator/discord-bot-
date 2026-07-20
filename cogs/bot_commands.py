import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        text = message.content.strip().lower()

        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة أوامر البوت التلقائية الشاملة",
                description="مرحباً بك! إليك جميع الأوامر المتاحة حالياً في البوت:",
                color=discord.Color.blue()
            )
            
            # جلب الأوامر المسجلة في البوت تلقائياً (Slash Commands أو Prefixed Commands)
            commands_list = []
            for command in self.bot.commands:
                if not command.hidden:
                    commands_list.append(f"`!{command.name}`")
            
            if commands_list:
                embed.add_field(
                    name="⚙️ الأوامر المسجلة برمجياً",
                    value=", ".join(commands_list),
                    inline=False
                )
            
            # إضافة الأوامر النصية التفاعلية المباشرة (تشمل الألعاب، نظام الحضور والانصراف، والنقاط)
            embed.add_field(
                name="🎮 الألعاب والأوامر السريعة (بدون بادئة)",
                value=(
                    "**الألعاب:** `عجلة`, `نرد`, `صناديق`, `مقص`, `تخمين`, `حظك`, `تحدي السرعة`, `حساب`, `كنز`, "
                    "`بلنتي`, `سلة`, `صيد`, `سيارات`, `تعدين`, `مبارزة`, `بولينج`, `طائرة`, `سفينة`, `سهم`, "
                    "`فضاء`, `قبو`, `بوكر`, `فخار`, `تسلق`, `سحر`, `بركان`\n\n"
                    "**المزاد والممتلكات:** `اسعار`, `شراء`, `ممتلكات`, `بيع`\n\n"
                    "**نظام الحضور والنقاط:** `دخول`, `خروج`, `سجل`"
                ),
                inline=False
            )
            
            embed.set_footer(text="تم تحديث القائمة تلقائياً | تطوير خاص لك")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
