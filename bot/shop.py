from bot.database import get_database
from bot.points import get_user_points, remove_points

async def get_shop_items():
    """جلب قائمة الأغراض المعروضة في المتجر"""
    db = await get_database()
    cursor = db.shop_items.find()
    return await cursor.to_list(length=100)

async def buy_item(user_id: int, item_id: str) -> dict:
    """شراء غراض من المتجر وإضافته لممتلكات المستخدم"""
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
