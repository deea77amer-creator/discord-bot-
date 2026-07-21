import motor.motor_asyncio
from bot.config import MONGO_URI, DATABASE_NAME

# إنشاء عميل الاتصال الخاص بـ MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

async def get_database():
    """إرجاع كائن قاعدة البيانات للاستخدام في باقي الملفات"""
    return db
