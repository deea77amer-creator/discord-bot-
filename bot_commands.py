import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # حدث الاستماع لكلمة "اوامر" بدون بادئة
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.strip() == "اوامر":
            embed = discord.Embed(
                title="📜 قائمة أوامر البوت الشاملة",
                description="مرحباً بك! إليك جميع أوامر الألعاب، الإدارة، والمزادات المتاحة:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎮 أوامر الألعاب",
                value="`!لعبة` - ابدأ لعبة جديدة أو استعرض الألعاب المتاحة.\n`!حظ` - جرب حظك اليومي واكسب نقاط.\n`!رصيد` - لعرض رصيدك الحالي من النقاط.",
                inline=False
            )
            
            embed.add_field(
                name="🔨 أوامر المزادات",
                value="`!مزاد [السلعة] [السعر]` - لبدء مزاد جديد على سلعة.\n`!زايد [المبلغ]` - للمزايدة على السلعة الحالية.\n`!إنهاء` - لإنهاء المزاد الحالي وإعلان الفائز.",
                inline=False
            )
            
            embed.add_field(
                name="🛡️ أوامر الإدارة",
                value="`!طرد @العضو` - لطرد عضو من السيرفر.\n`!بان @العضو` - لحظر عضو من السيرفر.\n`!مسح [العدد]` - لحذف عدد معين من الرسائل.",
                inline=False
            )
            
            embed.set_footer(text="تم تطوير البوت خصيصاً لك | جميع الحقوق محفوظة")
            await message.channel.send(embed=embed)

    # الأوامر الاعتيادية الباقية
    @commands.command(name="مسح")
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(ctx, amount: int = 5):
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"تم مسح {amount} رسالة بنجاح! 🗑️", delete_after=3)

    @commands.command(name="رصيد")
    async def check_balance(ctx):
        await ctx.send(f"يا {ctx.author.mention}, رصيدك الحالي محفوظ في قاعدة البيانات وصالك تمام! 💰")

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
