import discord
from discord import app_commands

ALLOWED_CHANNEL_ID = 1528588181371490344

@app_commands.command(name="الأوامر", description="عرض جميع الأوامر المتاحة في المتجر")
async def help_command(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(f"عذراً، لا يمكنك استخدام هذا الأمر إلا في قناة المتجر المخصصة.", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="📜 قائمة أوامر المتجر",
        description="الأوامر المتاحة حالياً في القناة:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="/المتجر", value="عرض قائمة الأغراض المتاحة في المتجر", inline=False)
    embed.add_field(name="/شراء [معرف_الغرض]", value="شراء غرض من المتجر باستخدام معرفه", inline=False)
    embed.add_field(name="/بيع [معرف_الغرض]", value="بيع غرض تمتلكه واسترداد نقاطه", inline=False)
    
    embed.set_footer(text=f"مطلوب بواسطة {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
