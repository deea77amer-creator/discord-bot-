from bot.database import get_database
from bot.points import remove_points, add_points
import discord
from discord import app_commands

# معرف القناة المسموح بالعمل فيها
ALLOWED_CHANNEL_ID = 1528588181371490344

async def get_shop_items():
    """جلب قائمة الأغراض المعروضة في المتجر"""
    db = await get_database()
    cursor = db.shop_items.find()
    return await cursor.to_list(length=100)

async def buy_item(user_id: int, item_id: str) -> dict:
    """شراء غرض من المتجر وإضافته لممتلكات المستخدم"""
    db = await get_database()
    
    # البحث عن الغرض في المتجر
    item = await db.shop_items.find_one({"item_id": item_id})
    if not item:
        return {"success": False, "message": "هذا الغرض غير موجود في المتجر!"}
    
    price = item.get("price", 0)
    
    # خصم النقاط عبر نظام النقاط المركزي
    success = await remove_points(user_id, price)
    if not success:
        return {"success": False, "message": "رصيدك غير كافٍ لشراء هذا الغرض!"}
    
    # إضافة الغرض لممتلكات المستخدم
    await db.user_inventory.update_one(
        {"user_id": user_id},
        {"$push": {"items": item_id}},
        upsert=True
    )
    
    return {"success": True, "message": f"تم بنجاح شراء {item.get('name', item_id)} مقابل {price} نقطة!"}


async def sell_item(user_id: int, item_id: str) -> dict:
    """بيع غرض يمتلكه المستخدم وإعادته للمتجر واسترداد جزء من سعره أو سعره كاملاً"""
    db = await get_database()
    
    # التحقق مما إذا كان المستخدم يمتلك هذا الغرض فعلاً
    user_inv = await db.user_inventory.find_one({"user_id": user_id})
    if not user_inv or item_id not in user_inv.get("items", []):
        return {"success": False, "message": "أنت لا تمتلك هذا الغرض لتتمكن من بيعه!"}
    
    # البحث عن الغرض لمعرفة سعره
    item = await db.shop_items.find_one({"item_id": item_id})
    if not item:
        return {"success": False, "message": "هذا الغرض لم يعد متوفراً في المتجر!"}
    
    # يمكنك تعديل نسبة الاسترجاع هنا (مثلاً نصف السعر أو السعر كاملاً، هنا جعلناها كامل السعر حسب نظام الشراء)
    price = item.get("price", 0)
    
    # إزالة الغرض من ممتلكات المستخدم
    await db.user_inventory.update_one(
        {"user_id": user_id},
        {"$pull": {"items": item_id}}
    )
    
    # إضافة النقاط لحساب المستخدم عبر نظام النقاط المركزي
    await add_points(user_id, price)
    
    return {"success": True, "message": f"تم بنجاح بيع {item.get('name', item_id)} واسترداد {price} نقطة!"}


# --- الأوامر الخاصة بالبوت ---

@app_commands.command(name="المتجر", description="عرض قائمة الأغراض المتاحة في المتجر")
async def shop_command(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(f"عذراً، لا يمكنك استخدام هذا الأمر إلا في قناة المتجر المخصصة.", ephemeral=True)
        return
    
    items = await get_shop_items()
    if not items:
        await interaction.response.send_message("المتجر فارغ حالياً!", ephemeral=True)
        return
        
    msg = "**قائمة الأغراض في المتجر:**\n"
    for item in items:
        msg += f"- **{item.get('name', item.get('item_id'))}** | السعر: `{item.get('price', 0)}` نقطة | المعرف: `{item.get('item_id')}`\n"
        
    await interaction.response.send_message(msg)


@app_commands.command(name="شراء", description="شراء غرض من المتجر باستخدام معرفه")
@app_commands.describe(item_id="معرف الغرض المراد شراؤه")
async def buy_command(interaction: discord.Interaction, item_id: str):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(f"عذراً، لا يمكنك استخدام هذا الأمر إلا في قناة المتجر المخصصة.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    result = await buy_item(interaction.user.id, item_id)
    await interaction.followup.send(result["message"], ephemeral=True)


@app_commands.command(name="بيع", description="بيع غرض تمتلكه واسترداد نقاطه")
@app_commands.describe(item_id="معرف الغرض المراد بيعه")
async def sell_command(interaction: discord.Interaction, item_id: str):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(f"عذراً، لا يمكنك استخدام هذا الأمر إلا في قناة المتجر المخصصة.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    result = await sell_item(interaction.user.id, item_id)
    await interaction.followup.send(result["message"], ephemeral=True)
