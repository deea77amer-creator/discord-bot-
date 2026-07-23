import discord
from discord.ext import commands

# آيديهات القناتين المسموح فيها استخدام الأمر
ALLOWED_CHANNEL_IDS = [1528917497246515221, 1528588181371490344]

async def setup_commands(bot):
    @bot.command(name="اوامر")
    async def help_command(ctx):
        # منع تكرار الرد إذا تم استدعاء الأمر من نفس الحدث أكثر من مرة
        if ctx.author.bot:
            return

        if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
            await ctx.send(f"عذراً {ctx.author.mention}، لا يمكنك استخدام هذا الأمر إلا في قنوات المتاجر المخصصة.", delete_after=5)
            return
            
        embed = discord.Embed(
            title="📜 قائمة أوامر البوت الشاملة",
            description="جميع الأوامر المتاحة حالياً (تتحدث تلقائياً):",
            color=discord.Color.blue()
        )
        
        # جلب جميع الأوامر المسجلة في البوت ديناميكياً (المتجر، الألعاب، وغيرها)
        commands_list = []
        for command in bot.commands:
            # تجاهل الأوامر المخفية أو الأوامر النظامية
            if not command.hidden:
                desc = command.help or "أمر متاح في السيرفر"
                commands_list.append(f"• **`!{command.name}`** : {desc}")
        
        if commands_list:
            embed.add_field(name="✨ الأوامر المتوفرة", value="\n".join(commands_list), inline=False)
        else:
            embed.description = "لا توجد أوامر مسجلة حالياً."
            
        embed.set_footer(text=f"مطلوب بواسطة {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
