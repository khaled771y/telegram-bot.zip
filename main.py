"""
البوت الرئيسي لإدارة الميكروتك عبر تليجرام
"""

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TELEGRAM_BOT_TOKEN, ENCRYPTION_KEY
from database import DatabaseManager
from telegram_handlers import TelegramHandlers
from hotspot_manager import HotspotManager
from network_tools import NetworkTools

# إعداد نظام السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MikroTikTelegramBot:
    """البوت الرئيسي لإدارة الميكروتك"""

    def __init__(self):
        # التحقق من توكن البوت
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("يرجى تعيين TELEGRAM_BOT_TOKEN في متغيرات البيئة أو ملف config.py")

        # تهيئة قاعدة البيانات
        self.db = DatabaseManager(encryption_key=ENCRYPTION_KEY)

        # تهيئة المعالجات
        self.handlers = TelegramHandlers(self.db)

        # إنشاء التطبيق
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # تسجيل المعالجات
        self.register_handlers()

    def register_handlers(self):
        """تسجيل معالجات الأوامر والرسائل"""
        self.application.add_handler(CommandHandler("start", self.handlers.start_command))
        self.application.add_handler(CommandHandler("login", self.handlers.login_command))
        self.application.add_handler(CallbackQueryHandler(self.handlers.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))

        # حفظ مرجع للمعالجات
        self.application.bot_data["handlers"] = self.handlers

    async def error_handler(self, update, context):
        """معالج الأخطاء"""
        logger.error(f"خطأ في البوت: {context.error}")

        if update and update.effective_user:
            user_id = update.effective_user.id
            self.db.log_operation(user_id, "error", str(context.error), False)

            try:
                if update.message:
                    await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
                elif update.callback_query:
                    await update.callback_query.edit_message_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
            except Exception as e:
                logger.warning(f"فشل في إرسال رسالة الخطأ: {e}")

    def run(self):
        """تشغيل البوت"""
        logger.info("🚀 بدء تشغيل بوت إدارة الميكروتك...")
        self.application.add_error_handler(self.error_handler)
        self.application.run_polling(allowed_updates=["message", "callback_query"])


def main():
    """الدالة الرئيسية"""
    try:
        bot = MikroTikTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        raise


if __name__ == "__main__":
    main()
