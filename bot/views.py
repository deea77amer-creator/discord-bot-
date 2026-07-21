import discord
from bot.shop import buy_item

class ShopView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=180)
        for item in items:
            self.add_item(ShopButton(item.get("item_id"), item.get("name", "شراء")))

class ShopButton(discord.ui.Button):
    def __init__(self, item_id: str, label: str):
        super().__init__(style=discord.ButtonStyle.success, label=f"شراء {label}")
        self.item_id = item_id

    async def callback(self, interaction: discord.Interaction):
        # منع خطأ This interaction failed فوراً بالاستجابة التلقائية
        await interaction.response.defer(ephemeral=True)
        
        result = await buy_item(interaction.user.id, self.item_id)
        await interaction.followup.send(result.get("message", "تم بنجاح!"), ephemeral=True)
