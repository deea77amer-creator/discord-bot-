import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        target_channel_id = 1528588181371490344

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

        elif text in ["العاب", "!العاب", "/العاب"]:
            if message.channel.id != target_channel_id:
                return await message.channel.send(f"❌ عذراً، ألعاب السيرفر مخصصة فقط في القناة المحددة!", delete_after=5)
            
            embed = discord.Embed(
                title="🎮 ألعاب وسوق السيرفر",
                description="إليك جميع الألعاب والأنظمة التفاعلية المتوفرة في القناة المخصصة:",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="⚔️ التحديات والمنافسة",
                value="• **تحدي النرد:** `نرد @الشخص المبلغ`\n• **التحدي التفاعلي:** `تحدي @الشخص المبلغ`",
                inline=False
            )
            embed.add_field(
                name="🎰 الألعاب الفردية",
                value="• **لعبة الحظ:** `حظ` أو `روليت` (تتكلف 20 نقطة)",
                inline=False
            )
            embed.add_field(
                name="🛒 السوق والمخزون",
                value="• **الأسعار:** `اسعار`\n• **الشراء:** `شراء`\n• **البيع:** `بيع`\n• **الحقيبة:** `ممتلكات`",
                inline=False
            )
            await message.channel.send(embed=embed)

        # أمر إعطاء النقاط (خاص بمالك السيرفر فقط)
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
            
            from __main__ import add_points, get_user_data
            guild_id = message.guild.id
            new_tot = add_points(guild_id, target_user.id, amount)
            await message.channel.send(f"✅ تم إضافة **{amount}** نقطة بنجاح إلى {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
