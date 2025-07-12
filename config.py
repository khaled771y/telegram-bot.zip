"""
ملف الإعدادات لبوت تليجرام الميكروتك
"""

import os
from typing import List

# إعدادات بوت تليجراTELEGRAM_BOT_TOKEN = "7671245623:AAHi_Qi5vfQ7EWJ1IaQTzXgiZaRdd7KlmwY"

# إعدادات قاعدة البيانات
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///mikrotik_bot.db')

# إعدادات الأمان
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'your-secret-encryption-key-here')

# قائمة المستخدمين المسموح لهم (معرفات تليجرام)
# اتركها فارغة للسماح لجميع المستخدمين
ALLOWED_USERS: List[int] = []

# إعدادات الميكروتك الافتراضية
DEFAULT_MIKROTIK_PORT = 8728
DEFAULT_MIKROTIK_SSL_PORT = 8729

# إعدادات طباعة الكروت
CARDS_PER_PAGE = 8
CARDS_PER_ROW = 2

# إعدادات التشخيص
PING_COUNT = 4
TRACEROUTE_MAX_HOPS = 30

# رسائل البوت
MESSAGES = {
    'welcome': """
🔧 مرحباً بك في بوت إدارة الميكروتك!

هذا البوت يساعدك في إدارة جهاز الميكروتك الخاص بك عن بُعد.

الميزات المتاحة:
📊 عرض معلومات النظام
🔥 إدارة الهوتسبوت
🎫 طباعة كروت الهوتسبوت
🔍 تشخيص المشاكل
🌐 أدوات الشبكة
🔄 إعادة تشغيل الجهاز

للبدء، استخدم الأمر /login لتسجيل الدخول إلى جهاز الميكروتك.
    """,
    
    'login_prompt': """
🔐 تسجيل الدخول إلى الميكروتك

يرجى إدخال بيانات الاتصال بالتنسيق التالي:
IP:PORT:USERNAME:PASSWORD

مثال:
192.168.88.1:8728:admin:mypassword

أو للاتصال الآمن (SSL):
192.168.88.1:8729:admin:mypassword:ssl
    """,
    
    'login_success': '✅ تم تسجيل الدخول بنجاح!',
    'login_failed': '❌ فشل في تسجيل الدخول. تحقق من البيانات المدخلة.',
    'not_logged_in': '⚠️ يجب تسجيل الدخول أولاً. استخدم الأمر /login',
    'unauthorized': '🚫 غير مسموح لك باستخدام هذا البوت.',
    'error': '❌ حدث خطأ: {}',
    'processing': '⏳ جاري المعالجة...',
    'done': '✅ تم بنجاح!',
}

# قوالب الرسائل
TEMPLATES = {
    'system_info': """
📊 معلومات النظام

🖥️ المعالج: {cpu_load}%
⚡ الفولط: {voltage}V
🌡️ الحرارة: {temperature}°C
⏰ مدة التشغيل: {uptime}
💾 الذاكرة: {memory_usage}%

📡 الشبكة:
⬇️ التحميل: {download_speed} م/ثا
⬆️ الرفع: {upload_speed} م/ثا

🔧 معلومات الجهاز:
📱 الموديل: {board_name}
🔢 الإصدار: {version}
🕐 وقت الشبكة: {network_time}
    """,
    
    'hotspot_user': """
👤 مستخدم الهوتسبوت

🆔 الاسم: {name}
🔑 كلمة المرور: {password}
📊 البروفايل: {profile}
🌐 عنوان IP: {ip_address}
📱 عنوان MAC: {mac_address}
⏰ وقت الاتصال: {uptime}
📈 البيانات المستخدمة: {bytes_used}
📉 البيانات المتبقية: {bytes_remaining}
⏱️ الوقت المتبقي: {time_remaining}
    """,
    
    'hotspot_card': """
🎫 كرت هوتسبوت

👤 اسم المستخدم: {username}
🔑 كلمة المرور: {password}
📊 حصة البيانات: {data_quota}
⏰ حصة الوقت: {time_quota}
📅 صالح لمدة: {validity_days} يوم
    """
}

