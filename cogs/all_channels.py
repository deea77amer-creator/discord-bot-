import discord
from discord.ext import commands
import json
import os

class AllChannelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "config.json"

    # دالة لقراءة الإعدادات من الملف
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except:
                    return {}
        return {}

    # دالة لحفظ الإعدادات في الملف (تمنع ضياع البيانات وقت الريستارت)
    def save_config(self, data):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # أمر عام ومرن لتحديد أي قناة مستقبلاً (يدعم الترحيب، الألعاب، السجلات، الخ...)
    @commands.command(name="تحديد")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_type: str, channel: discord.TextChannel = None):
        """
        طريقة الاستخدام:
        !تحديد السجلات #قناة-السجلات
        !تحديد الالعاب #قناة-العاب
        !تحديد الترحيب #ترحيب
        """
        if channel is None:
            channel = ctx.channel

        # توحيد اسم النوع بصيغة صغيرة
        key = channel_type.lower()
        
        config = self.load_config()
        config[key] = channel.id
        self.save_config(config)

        await ctx.send(f"✅ تم حفظ وتحديد قناة **({channel_type})** بنجاح: {channel.mention}\n(جرب تسوي ريستارت للبوت وتتأكد أن الحفظ باقي محفوظ!)")

    # أمر لعرض كل القنوات المحفوظة للتأكد منها
    @commands.command(name="قنواتي")
    @commands.has_permissions(administrator=True)
    async def show_all_channels(self, ctx):
        config = self.load_config()
        if not config:
            await ctx.send("❌ لم يتم حفظ أي قناة حتى الآن.")
            return

        embed = discord.Embed(
            title="📌 القنوات المحفوظة في النظام",
            color=discord.Color.green()
        )
        
        for key, ch_id in config.items():
            ch = self.bot.get_channel(ch_id)
            ch_mention = ch.mention if ch else f"قناة محذوفة (ID: {ch_id})"
            embed.add_field(name=f"• النوع: {key}", value=ch_mention, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AllChannelsCog(bot))
