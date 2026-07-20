import discord
from discord.ext import commands
import random
import asyncio

# قائمة الألعاب الـ 26 كاملة والجاهزة للتفاعل
GAMES_LIST = [
    {"name": "النرد السريع", "cmd": "نرد @الشخص المبلغ", "desc": "تحدي نرد برهان نقاط"},
    {"name": "التحدي التفاعلي", "cmd": "تحدي @الشخص المبلغ", "desc": "اختيار وتحدي مباشر بين لاعبين"},
    {"name": "لعبة الحظ أو الروليت", "cmd": "حظ / روليت", "desc": "مغامرة بالحظ لربح أو خسارة النقاط"},
    {"name": "حجرة ورقة مقص", "cmd": "rps", "desc": "لعبة الكلاسيكية الشهيرة"},
    {"name": "تخمين الرقم", "cmd": "تخمين", "desc": "ابحث عن الرقم الصحيح السري"},
    {"name": "رياضيات سريعة", "cmd": "حساب", "desc": "اختبار سرعة البديهة والرياضيات"},
    {"name": "تخمين العواصم", "cmd": "عاصمة", "desc": "اختبار معلوماتك الجغرافية"},
    {"name": "معاني الكلمات", "cmd": "معنى", "desc": "تحدي المفردات واللغة"},
    {"name": "فك الشفرة", "cmd": "شفرة", "desc": "فك الحروف المبعثرة"},
    {"name": "اكتشاف الخطأ", "cmd": "خطأ", "desc": "ابحث عن الكلمة الشاذة"},
    {"name": "تحدي الذاكرة", "cmd": "ذاكرة", "desc": "اختبر قوة حفظك وتذكرك"},
    {"name": "ترتيب الحروف", "cmd": "ترتيب", "desc": "رتب الحروف لتكون كلمة صحيحة"},
    {"name": "أقوال مشهورة", "cmd": "مقولة", "desc": "اعرف قائل الحكمة أو المقولة"},
    {"name": "تحدي الألوان", "cmd": "لون", "desc": "ركز في الألوان والخدع البصرية"},
    {"name": "سباق السيارات", "cmd": "سباق", "desc": "حلبة سرعة افتراضية"},
    {"name": "حرب الأساطير", "cmd": "أسطورة", "desc": "مواجهة ملحمية فردية"},
    {"name": "بناء القلعة", "cmd": "قلعة", "desc": "تجميع موارد وبناء حصنك"},
    {"name": "صيد الكنز", "cmd": "كنز", "desc": "ابحث عن الصندوق المفقود"},
    {"name": "معركة البوصة", "cmd": "بوصة", "desc": "تحدي التكتيك السريع"},
    {"name": "تحدي الفضاء", "cmd": "فضاء", "desc": "رحلة استكشاف كواكب ومخاطر"},
    {"name": "روليت الحظ الكبرى", "cmd": "روليت كبرى", "desc": "مضاعفة النقاط الخطرة"},
    {"name": "سؤال وذكاء", "cmd": "سؤال", "desc": "أسئلة عامة وثقافية سريعة"},
    {"name": "تحدي السرعة الكلاسيكي", "cmd": "سرعة", "desc": "من يكتب الكلمة أولاً"},
    {"name": "سلسلة الكلمات", "cmd": "سلسلة", "desc": "أكمل الكلمة بالحرف الأخير"},
    {"name": "تجميع الكنز الخفي", "cmd": "كنز خفي", "desc": "ألغاز متسلسلة للجوائز"},
    {"name": "حرب الكلمات المشتعلة", "cmd": "حرب", "desc": "تحدي جماعي حماسي"}
]

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        target_channel_id = 1528588181371490344

        # 1. قائمة الأوامر العامة
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
            embed.set_footer(text="جميع الأوامر تعمل مباشرة في القناة المخصصة!")
            await message.channel.send(embed=embed)

        # 2. قائمة الـ 26 لعبة والأنظمة التفاعلية (مقيدة بالقناة المخصصة)
        elif text in ["العاب", "!العاب", "/العاب"]:
            if message.channel.id != target_channel_id:
                return await message.channel.send(f"❌ عذراً، ألعاب السيرفر مخصصة فقط في القناة المحددة!", delete_after=5)
            
            embed = discord.Embed(
                title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة)",
                description="إليك قائمة الألعاب والمسابقات المتوفرة في السيرفر:",
                color=discord.Color.gold()
            )
            
            # تقسيم الـ 26 لعبة في خانتين لترتيب المظهر وعدم تجاوز حدود الديسكورد
            part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
            part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
            
            embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
            embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
            embed.set_footer(text="استمتع بالتحديات واجمع النقاط!")
            await message.channel.send(embed=embed)

        # 3. أمر إعطاء النقاط (خاص بمالك السيرفر فقط)
        elif text.startswith("نقاط ") or text.startswith("!نقاط "):
            if message.author.id != message.guild.owner_id:
                return await message.channel.send("❌ هذا الأمر مخصص لمالك السيرفر فقط!", delete_after=5)
            
            parts = message.content.strip().split()
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح: `نقاط @الشخص المبلغ`", delete_after=5)
            
            target_user = message.mentions[0]
            try:
                amount = int(parts[2])
            except ValueError:
                return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ.", delete_after=5)
            
            from __main__ import add_points
            guild_id = message.guild.id
            new_tot = add_points(guild_id, target_user.id, amount)
            await message.channel.send(f"✅ تم إضافة **{amount}** نقطة بنجاح إلى {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
