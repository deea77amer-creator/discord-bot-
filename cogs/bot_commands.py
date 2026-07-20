import discord
from discord.ext import commands

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()

        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر والألعاب",
                description="مرحباً بك! إليك دليل الاستخدام والأوامر المتاحة في السيرفر:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎲 ألعاب التحدي والنرد",
                value="• `نرد @الشخص المبلغ` — لتحدي شخص في النرد برهان نقاط.\n"
                      "• `تحدي @الشخص المبلغ` — لتحدي تفاعلي اختيار لعبة بينك وبينه.\n"
                      "• `حظ` أو `روليت` — لربح النقاط أو خسارتها بالحظ (تكلفة 20 نقطة).",
                inline=False
            )
            
            embed.add_field(
                name="🛒 السوق والممتلكات",
                value="• `اسعار` — لعرض أسعار الأغراض المتغيرة.\n"
                      "• `شراء` — لقائمة متجر الشراء التفاعلي.\n"
                      "• `بيع` — لبيع أغراضك واسترداد النقاط.\n"
                      "• `ممتلكات` أو `حقيبتي` — لعرض محتويات حقيبتك.",
                inline=False
            )

            embed.add_field(
                name="💸 التحويل والنقاط",
                value="• `نقاطي` — لمعرفة رصيدك الحالي من النقاط.\n"
                      "• `تحويل @الشخص نقاط المبلغ` — لتحويل نقاط لشخص آخر.\n"
                      "• `تحويل @الشخص اغراض` — لتحويل أغراض وممتلكات.",
                inline=False
            )
            
            embed.set_footer(text="جميع الأوامر تعمل مباشرة في القنوات المخصصة!")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))
