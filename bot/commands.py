import discord
from discord.ext import commands

# آيديهات القناتين المسموح فيها استخدام الأمر
ALLOWED_CHANNEL_IDS = [1528917497246515221, 1528588181371490344]

async def setup_commands(bot):
    bot.remove_command('help')

    @bot.command(name="اوامر")
    async def help_command(ctx):
        if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
            await ctx.send(f"عذراً {ctx.author.mention}، لا يمكنك استخدام هذا الأمر إلا في قنوات المتاجر المخصصة.", delete_after=5)
            return
            
        embed = discord.Embed(
            title="📜 قائمة الأوامر المتاحة",
            description="الأوامر الخاصة بالمتجر والأنظمة:",
            color=discord.Color.blue()
        )
        
        # قائمة بالأوامر المحددة التي تريد إظهارها فقط (اكتب أسماء أوامرك هنا بدقة)
        allowed_commands_names = ["اوامر", "شراء", "بيع", "نقاط"] # أضف أي أمر خاص بك هنا
        
        commands_set = set()
        for command in bot.commands:
            # اظهار الأوامر الموجودة في القائمة المخصصة فقط وتجاهل البقية
            if command.name in allowed_commands_names and not command.hidden:
                commands_set.add(f"• **`!{command.name}`**")
        
        if commands_set:
            embed.add_field(name="✨ الأوامر المتوفرة", value="\n".join(commands_set), inline=False)
        else:
            embed.description = "لا توجد أوامر مسجلة حالياً."
            
        embed.set_footer(text=f"مطلوب بواسطة {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
