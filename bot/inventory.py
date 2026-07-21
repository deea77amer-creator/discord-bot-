from bot.database import get_database

async def get_user_inventory(user_id: int) -> list:
    """جلب قائمة ممتلكات وأغراض المستخدم"""
    db = await get_database()
    user_inv = await db.user_inventory.find_one({"user_id": user_id})
    if not user_inv:
        return []
    return user_inv.get("items", [])
