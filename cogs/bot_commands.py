import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        text = message.content.strip().lower()

        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر",
                description="مرحباً بك! إليك الأوامر المتاحة في البوت:",
                color=discord.Color.blue()
            )
            
            commands_list = []
            for command in self.bot.commands:
                if not command.hidden:
                    commands_list.append(f"`!{command.name}`")
            
            if commands_list:
                embed.add_field(
                    name="⚙️ الأوامر المسجلة برمجياً",
                    value=", ".join(commands_list),
                    inline=False
                )
            
            embed.set_footer(text="تم تحديث القائمة تلقائياً | تطوير خاص لك")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
