from bot.database import get_database

async def get_user_points(user_id: int) -> int:
    """جلب رصيد المستخدم من النقاط"""
    db = await get_database()
    user = await db.users.find_one({"user_id": user_id})
    return user.get("points", 0) if user else 0

async def add_points(user_id: int, amount: int):
    """إضافة نقاط للمستخدم"""
    db = await get_database()
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"points": amount}},
        upsert=True
    )

async def remove_points(user_id: int, amount: int) -> bool:
    """خصم نقاط من المستخدم (يعود بـ False إذا كان رصيده لا يكفي)"""
    current_points = await get_user_points(user_id)
    if current_points < amount:
        return False
    
    db = await get_database()
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"points": -amount}}
    )
    return True

async def transfer_points(sender_id: int, receiver_id: int, amount: int) -> bool:
    """تحويل نقاط من لاعب لآخر"""
    if amount <= 0 or sender_id == receiver_id:
        return False
    
    success = await remove_points(sender_id, amount)
    if success:
        await add_points(receiver_id, amount)
        return True
    return False

async def get_top_users(limit: int = 10):
    """جلب قائمة بأكثر اللاعبين امتلاكاً للنقاط (التوب)"""
    db = await get_database()
    cursor = db.users.find().sort("points", -1).limit(limit)
    return await cursor.to_list(length=limit)
