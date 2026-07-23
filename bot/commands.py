import discord
from discord.ext import commands

# آيديهات القناتين المسموح فيها استخدام الأمر فقط
ALLOWED_CHANNEL_IDS = [1528917497246515221, 1528588181371490344]

async def setup_commands(bot):
    # إزالة أمر help الافتراضي لمنع أي تداخل
    bot.remove_command('help')

    @bot.command(name="اوامر")
    async def help_command(ctx):
        # التحقق من أن الأمر يُكتب في إحدى القناتين المسموح بهما فقط
        if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
            await ctx.send(f"عذراً {ctx.author.mention}، لا يمكنك استخدام هذا الأمر إلا في قنوات المتاجر المخصصة.", delete_after=5)
            return
            
        embed = discord.Embed(
            title="📜 قائمة الأوامر الشاملة",
            description="جميع الأوامر المتاحة حالياً في السيرفر (تتحدث تلقائياً):",
            color=discord.Color.blue()
        )
        
        # جلب جميع الأوامر المسجلة في البوت ديناميكياً بشكل تلقائي
        commands_set = set()
        for command in bot.commands:
            if not command.hidden and command.name != "help":
                desc = command.help or "أمر متاح في السيرفر"
                commands_set.add(f"• **`!{command.name}`** : {desc}")
        
        if commands_set:
            embed.add_field(name="✨ الأوامر المتوفرة", value="\n".join(commands_set), inline=False)
        else:
            embed.description = "لا توجد أوامر مسجلة حالياً."
            
        embed.set_footer(text=f"مطلوب بواسطة {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
