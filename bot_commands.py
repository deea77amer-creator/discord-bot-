import os
import discord
from discord.ext import commands

# إعداد البوت والبادئة (Prefix)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم {bot.user}")

# أمر عرض جميع الأوامر بكتابة كلمة "اوامر"
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # التحقق إذا كانت رسالة المستخدم تطابق كلمة "اوامر" تماماً
    if message.content.strip() == "اوامر":
        embed = discord.Embed(
            title="📜 قائمة أوامر البوت الشاملة",
            description="مرحباً بك! إليك جميع أوامر الألعاب، الإدارة، والمزادات المتاحة:",
            color=discord.Color.blue()
        )
        
        # قسم الألعاب
        embed.add_field(
            name="🎮 أوامر الألعاب",
            value=(
                "`!لعبة` - ابدأ لعبة جديدة أو استعرض الألعاب المتاحة.\n"
                "`!حظ` - جرب حظك اليومي واكسب نقاط.\n"
                "`!رصيد` - لعرض رصيدك الحالي من النقاط."
            ),
            inline=False
        )
        
        # قسم المزادات
        embed.add_field(
            name="🔨 أوامر المزادات",
            value=(
                "`!مزاد [السلعة] [السعر]` - لبدء مزاد جديد على سلعة.\n"
                "`!زايد [المبلغ]` - للمزايدة على السلعة الحالية.\n"
                "`!إنهاء` - لإنهاء المزاد الحالي وإعلان الفائز."
            ),
            inline=False
        )
        
        # قسم الإدارة
        embed.add_field(
            name="🛡️ أوامر الإدارة",
            value=(
                "`!طرد @العضو` - لطرد عضو من السيرفر (يتطلب صلاحيات).\n"
                "`!بان @العضو` - لحظر عضو من السيرفر (يتطلب صلاحيات).\n"
                "`!مسح [العدد]` - لحذف عدد معين من الرسائل."
            ),
            inline=False
        )
        
        embed.set_footer(text="تم تطوير البوت خصيصاً لك | جميع الحقوق محفوظة")
        await message.channel.send(embed=embed)
        return

    # السماح بقراءة الأوامر الأخرى العادية
    await bot.process_commands(message)

# أمثلة لأوامر الإدارة والألعاب البسيطة
@bot.command(name="مسح")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"تم مسح {amount} رسالة بنجاح! 🗑️", delete_after=3)

@bot.command(name="رصيد")
async def check_balance(ctx):
    await ctx.send(f"يا {ctx.author.mention}, رصيدك الحالي محفوظ في قاعدة البيانات وصالك تمام! 💰")

# تشغيل البوت باستخدام التوكن من البيئة
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("خطأ: التوكن غير موجود")
