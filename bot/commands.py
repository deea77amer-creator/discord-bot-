import discord
from discord.ext import commands

ALLOWED_CHANNEL_ID = 1528917497246515221

async def setup_commands(bot):
    @bot.command(name="اوامر", aliases=["الأوامر", "help", "commands"])
    async def help_command(ctx):
        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            await ctx.send(f"عذراً {ctx.author.mention}، لا يمكنك استخدام هذا الأمر إلا في قناة المتجر المخصصة.", delete_after=5)
            return
            
        embed = discord.Embed(
            title="📜 قائمة أوامر المتجر",
            description="الأوامر المتاحة حالياً في القناة:",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="المتجر", value="عرض قائمة الأغراض المتاحة في المتجر", inline=False)
        embed.add_field(name="شراء [معرف_الغرض]", value="شراء غرض من المتجر باستخدام معرفه", inline=False)
        embed.add_field(name="بيع [معرف_الغرض]", value="بيع غرض تمتلكه واسترداد نقاطه", inline=False)
        
        embed.set_footer(text=f"مطلوب بواسطة {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
