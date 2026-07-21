import discord
from discord.ext import commands
from bot.points import get_user_points, get_top_users, transfer_points
from bot.shop import get_shop_items, buy_item
from bot.inventory import get_user_inventory
from bot.views import ShopView

async def setup_commands(bot):
    
    @bot.command(name="رصيدي", aliases=["points", "balance"])
    async def balance_cmd(ctx):
        points = await get_user_points(ctx.author.id)
        embed = discord.Embed(title="💰 رصيد النقاط", description=f"رصيدك الحالي هو: **{points}** نقطة", color=discord.Color.gold())
        await ctx.send(embed=embed)

    @bot.command(name="توب", aliases=["leaderboard", "top"])
    async def top_cmd(ctx):
        top_list = await get_top_users(10)
        desc = ""
        for index, user in enumerate(top_list, start=1):
            user_obj = bot.get_user(user.get("user_id"))
            name = user_obj.name if user_obj else f"مستخدم {user.get('user_id')}"
            desc += f"**#{index}** | {name} ⟷ **{user.get('points', 0)}** نقطة\n"
        
        if not desc:
            desc = "لا يوجد لاعبون في القائمة بعد."
            
        embed = discord.Embed(title="🏆 لوحة الشرف (Top 10)", description=desc, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @bot.command(name="المتجر", aliases=["shop"])
    async def shop_cmd(ctx):
        items = await get_shop_items()
        if not items:
            await ctx.send("المتجر فارغ حالياً!")
            return
            
        embed = discord.Embed(title="🛒 متجر البوت", description="اختر الغرض الذي تريد شراءه من الأزرار بالأسفل:", color=discord.Color.green())
        for item in items:
            embed.add_field(name=item.get("name", "غرض"), value=جملة الوصف السعر: {item.get('price', 0)} نقطة, inline=False)
            
        view = ShopView(items)
        await ctx.send(embed=embed, view=view)

    @bot.command(name="ممتلكاتي", aliases=["inventory", "inv"])
    async def inventory_cmd(ctx):
        inv = await get_user_inventory(ctx.author.id)
        if not inv:
            await ctx.send("حقيبتك فارغة تماماً!")
            return
            
        desc = "\n".join([f"• {item}" for item in inv])
        embed = discord.Embed(title="🎒 ممتلكاتك", description=desc, color=discord.Color.purple())
        await ctx.send(embed=embed)
