import logging
from typing import Dict, Any
from datetime import datetime
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from config import MESSAGES, TEMPLATES, ALLOWED_USERS
from database import DatabaseManager
from mikrotik_api_client import MikroTikAPIClient
from models import MikroTikDevice

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """معالجات أوامر تليجرام"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.active_connections: Dict[int, MikroTikAPIClient] = {}
    
    def is_user_authorized(self, user_id: int) -> bool:
        """فحص تفويض المستخدم"""
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            return False
        return self.db.is_user_authorized(user_id) or not ALLOWED_USERS
    
    def get_user_connection(self, user_id: int) -> MikroTikAPIClient:
        """الحصول على اتصال المستخدم بالميكروتك"""
        return self.active_connections.get(user_id)
    
    def create_main_keyboard(self) -> InlineKeyboardMarkup:
        """إنشاء لوحة المفاتيح الرئيسية بتصميم أنيق"""
        keyboard = [
            [
                InlineKeyboardButton("📊 معلومات النظام", callback_data="system_info"),
                InlineKeyboardButton("🔥 إدارة الهوتسبوت", callback_data="hotspot_menu")
            ],
            [
                InlineKeyboardButton("🎫 كروت الهوتسبوت", callback_data="hotspot_cards"),
                InlineKeyboardButton("🔍 تشخيص المشاكل", callback_data="troubleshoot")
            ],
            [
                InlineKeyboardButton("🌐 اكتشاف الأجهزة", callback_data="discover_devices"),
                InlineKeyboardButton("🔄 إعادة تشغيل الراوتر", callback_data="reboot_confirm")
            ],
            [
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
                InlineKeyboardButton("📋 سجل العمليات", callback_data="operation_logs")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_hotspot_keyboard(self) -> InlineKeyboardMarkup:
        """إنشاء لوحة مفاتيح الهوتسبوت بتصميم أنيق"""
        keyboard = [
            [
                InlineKeyboardButton("👥 المستخدمون النشطون", callback_data="hotspot_active"),
                InlineKeyboardButton("📋 جميع المستخدمين", callback_data="hotspot_all")
            ],
            [
                InlineKeyboardButton("➕ إضافة مستخدم جديد", callback_data="hotspot_add"),
                InlineKeyboardButton("🔎 البحث عن مستخدم", callback_data="hotspot_search")
            ],
            [
                InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_hotspot_cards_keyboard(self) -> InlineKeyboardMarkup:
        """إنشاء لوحة مفاتيح كروت الهوتسبوت"""
        keyboard = [
            [
                InlineKeyboardButton("🎫 توليد كروت جديدة", callback_data="generate_cards"),
                InlineKeyboardButton("🗂️ عرض الكروت المحفوظة", callback_data="saved_cards")
            ],
            [
                InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_troubleshoot_keyboard(self) -> InlineKeyboardMarkup:
        """إنشاء لوحة مفاتيح تشخيص المشاكل"""
        keyboard = [
            [
                InlineKeyboardButton("🩺 فحص صحة النظام", callback_data="system_health_check"),
                InlineKeyboardButton("🏓 اختبار Ping", callback_data="ping_test")
            ],
            [
                InlineKeyboardButton("🛤️ تتبع المسار (Traceroute)", callback_data="traceroute_test"),
                InlineKeyboardButton("⚡ اختبار السرعة", callback_data="speed_test")
            ],
            [
                InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # إضافة المستخدم إلى قاعدة البيانات
        self.db.add_user(user_id, user.username, user.first_name, user.last_name)
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return
        
        # تفويض المستخدم تلقائياً إذا لم تكن هناك قيود
        if not ALLOWED_USERS:
            self.db.authorize_user(user_id)
        
        await update.message.reply_text(
            MESSAGES["welcome"],
            reply_markup=self.create_main_keyboard()
        )
        
        self.db.log_operation(user_id, "start", "بدء استخدام البوت", True)
    
    async def login_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /login"""
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return
        
        await update.message.reply_text(MESSAGES["login_prompt"])
        
        # تعيين حالة انتظار بيانات تسجيل الدخول
        context.user_data["waiting_for_login"] = True
    
    async def handle_login_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات تسجيل الدخول"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # تحليل بيانات الاتصال
        parts = text.split(":")
        if len(parts) < 4:
            await update.message.reply_text(
                "❌ تنسيق خاطئ. يرجى استخدام التنسيق:\nIP:PORT:USERNAME:PASSWORD"
            )
            return
        
        ip = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ المنفذ يجب أن يكون رقماً")
            return
        
        username = parts[2]
        password = parts[3]
        use_ssl = len(parts) > 4 and parts[4].lower() == "ssl"
        
        # إنشاء جهاز الميكروتك
        device = MikroTikDevice(ip, port, username, password, use_ssl)
        
        # محاولة الاتصال
        processing_msg = await update.message.reply_text(MESSAGES["processing"])
        
        client = MikroTikAPIClient(device)
        if client.connect():
            # حفظ الجهاز في قاعدة البيانات
            device_id = self.db.add_mikrotik_device(user_id, device)
            
            if device_id:
                # إنشاء جلسة المستخدم
                self.db.create_user_session(user_id, device_id)
                
                # حفظ الاتصال النشط
                self.active_connections[user_id] = client
                
                await processing_msg.edit_text(
                    MESSAGES["login_success"],
                    reply_markup=self.create_main_keyboard()
                )
                
                self.db.log_operation(user_id, "login", f"تسجيل دخول ناجح إلى {device}", True)
            else:
                client.disconnect()
                await processing_msg.edit_text("❌ خطأ في حفظ بيانات الجهاز")
        else:
            await processing_msg.edit_text(MESSAGES["login_failed"])
            self.db.log_operation(user_id, "login", f"فشل تسجيل الدخول إلى {device}", False)
        
        # إزالة حالة انتظار تسجيل الدخول
        context.user_data.pop("waiting_for_login", None)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الاستعلامات المرجعية (Callback Queries)"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        if not self.is_user_authorized(user_id):
            await query.answer(MESSAGES["unauthorized"])
            return
        
        # تحديث نشاط المستخدم
        self.db.update_user_activity(user_id)
        
        await query.answer()
        
        # توجيه الاستعلام حسب النوع
        if data == "main_menu":
            await self.show_main_menu(query)
        elif data == "system_info":
            await self.show_system_info(query)
        elif data == "hotspot_menu":
            await self.show_hotspot_menu(query)
        elif data == "hotspot_active":
            await self.show_hotspot_active_users(query)
        elif data == "hotspot_all":
            await self.show_hotspot_all_users(query)
        elif data == "hotspot_cards":
            await self.show_hotspot_cards_menu(query)
        elif data == "troubleshoot":
            await self.show_troubleshoot_menu(query)
        elif data == "discover_devices":
            await self.discover_devices(query)
        elif data == "reboot_confirm":
            await self.show_reboot_confirmation(query)
        elif data == "reboot_execute":
            await self.execute_reboot(query)
        elif data == "settings":
            await self.show_settings(query)
        elif data == "operation_logs":
            await self.show_operation_logs(query)
        elif data == "generate_cards":
            await self.prompt_generate_cards(query, context)
        elif data == "saved_cards":
            await self.show_saved_cards(query)
        elif data == "system_health_check":
            await self.show_system_health_check(query)
        elif data == "ping_test":
            await self.prompt_ping_test(query, context)
        elif data == "traceroute_test":
            await self.prompt_traceroute_test(query, context)
        elif data == "speed_test":
            await self.prompt_speed_test(query, context)
        else:
            await query.edit_message_text("❌ أمر غير معروف")
    
    async def show_main_menu(self, query):
        """عرض القائمة الرئيسية"""
        await query.edit_message_text(
            "🏠 القائمة الرئيسية\n\nاختر الخدمة المطلوبة:",
            reply_markup=self.create_main_keyboard()
        )
    
    async def show_system_info(self, query):
        """عرض معلومات النظام"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        system_info = client.get_system_info()
        if not system_info:
            await query.edit_message_text("❌ فشل في الحصول على معلومات النظام")
            return
        
        # الحصول على معلومات الشبكة
        interfaces = client.get_interfaces()
        total_rx = sum(iface.rx_mb for iface in interfaces if iface.running)
        total_tx = sum(iface.tx_mb for iface in interfaces if iface.running)
        
        # تنسيق الرسالة
        message = TEMPLATES["system_info"].format(
            cpu_load=system_info.cpu_load,
            voltage=system_info.voltage,
            temperature=system_info.temperature,
            uptime=system_info.uptime,
            memory_usage=system_info.memory_usage_percent,
            download_speed=f"{total_rx:.1f}",
            upload_speed=f"{total_tx:.1f}",
            board_name=system_info.board_name,
            version=system_info.version,
            network_time=datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        )
        
        keyboard = [[InlineKeyboardButton("🔄 تحديث البيانات", callback_data="system_info"),
                    InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "system_info", "عرض معلومات النظام", True)
    
    async def show_hotspot_menu(self, query):
        """عرض قائمة الهوتسبوت"""
        await query.edit_message_text(
            "🔥 إدارة الهوتسبوت\n\nاختر العملية المطلوبة:",
            reply_markup=self.create_hotspot_keyboard()
        )
    
    async def show_hotspot_active_users(self, query):
        """عرض المستخدمين النشطين في الهوتسبوت"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        active_users = client.get_hotspot_active_users()
        
        if not active_users:
            message = "👥 المستخدمون النشطون\n\n❌ لا يوجد مستخدمون نشطون حالياً"
        else:
            message = f"👥 المستخدمون النشطون ({len(active_users)})\n\n"
            
            for i, user in enumerate(active_users[:10], 1):  # عرض أول 10 مستخدمين
                total_mb = (user.bytes_in + user.bytes_out) / (1024 * 1024) if user.bytes_in and user.bytes_out else 0
                message += f"{i}. 👤 {user.name}\n"
                message += f"   📍 IP: {user.ip_address}\n"
                message += f"   ⏰ الوقت: {user.uptime}\n"
                message += f"   📊 البيانات: {total_mb:.1f} MB\n\n"
            
            if len(active_users) > 10:
                message += f"... و {len(active_users) - 10} مستخدمين آخرين"
        
        keyboard = [[InlineKeyboardButton("🔄 تحديث القائمة", callback_data="hotspot_active"),
                    InlineKeyboardButton("🔙 العودة لقائمة الهوتسبوت", callback_data="hotspot_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "hotspot_active", f"عرض {len(active_users)} مستخدم نشط", True)
    
    async def show_hotspot_all_users(self, query):
        """عرض جميع مستخدمي الهوتسبوت"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        all_users = client.get_hotspot_users()
        
        if not all_users:
            message = "📋 جميع مستخدمي الهوتسبوت\n\n❌ لا يوجد مستخدمون مسجلون"
        else:
            message = f"📋 جميع مستخدمي الهوتسبوت ({len(all_users)})\n\n"
            
            for i, user in enumerate(all_users[:15], 1):  # عرض أول 15 مستخدم
                status = "🟢 نشط" if user.is_active else ("🔴 معطل" if user.disabled else "⚪ غير متصل")
                message += f"{i}. 👤 {user.name}\n"
                message += f"   📊 البروفايل: {user.profile}\n"
                message += f"   🔘 الحالة: {status}\n\n"
            
            if len(all_users) > 15:
                message += f"... و {len(all_users) - 15} مستخدمين آخرين"
        
        keyboard = [[InlineKeyboardButton("🔄 تحديث القائمة", callback_data="hotspot_all"),
                    InlineKeyboardButton("🔙 العودة لقائمة الهوتسبوت", callback_data="hotspot_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "hotspot_all", f"عرض {len(all_users)} مستخدم", True)
    
    async def show_reboot_confirmation(self, query):
        """عرض تأكيد إعادة التشغيل"""
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، أعد التشغيل الآن", callback_data="reboot_execute"),
                InlineKeyboardButton("❌ إلغاء العملية", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(
            "⚠️ تأكيد إعادة تشغيل الراوتر\n\n"
            "هل أنت متأكد من رغبتك في إعادة تشغيل جهاز الميكروتك؟\n"
            "سيؤدي هذا إلى قطع جميع الاتصالات مؤقتاً.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def execute_reboot(self, query):
        """تنفيذ إعادة التشغيل"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        if client.reboot_system():
            await query.edit_message_text(
                "✅ تم إرسال أمر إعادة التشغيل بنجاح!\n\n"
                "سيتم إعادة تشغيل الجهاز خلال ثوانٍ قليلة.\n"
                "قد تحتاج إلى تسجيل الدخول مرة أخرى بعد إعادة التشغيل."
            )
            
            # قطع الاتصال
            client.disconnect()
            self.active_connections.pop(user_id, None)
            
            self.db.log_operation(user_id, "reboot", "إعادة تشغيل الجهاز", True)
        else:
            await query.edit_message_text("❌ فشل في إعادة تشغيل الجهاز. يرجى المحاولة مرة أخرى.")
            self.db.log_operation(user_id, "reboot", "فشل في إعادة تشغيل الجهاز", False)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية"""
        user_id = update.effective_user.id
        
        if not self.is_user_authorized(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return
        
        # فحص إذا كان المستخدم في انتظار بيانات تسجيل الدخول
        if context.user_data.get("waiting_for_login"):
            await self.handle_login_data(update, context)
            return
        
        # رسالة افتراضية للرسائل غير المعروفة
        await update.message.reply_text(
            "لم أفهم هذا الأمر. 🧐 يرجى استخدام الأزرار أو الأمر /start لعرض القائمة الرئيسية.",
            reply_markup=self.create_main_keyboard()
        )
    
    async def show_settings(self, query):
        """عرض الإعدادات"""
        user_id = query.from_user.id
        devices = self.db.get_user_devices(user_id)
        
        message = "⚙️ الإعدادات\n\n"
        message += f"👤 معرف المستخدم: {user_id}\n"
        message += f"🔧 عدد الأجهزة المحفوظة: {len(devices)}\n\n"
        
        if devices:
            message += "📱 الأجهزة المحفوظة:\n"
            for device in devices:
                status = "🟢 متصل" if user_id in self.active_connections else "🔴 غير متصل"
                message += f"• {device["device_name"]} ({device["ip_address"]}:{device["port"]}) - {status}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_operation_logs(self, query):
        """عرض سجل العمليات"""
        user_id = query.from_user.id
        logs = self.db.get_operation_logs(user_id, 10)
        
        if not logs:
            message = "📋 سجل العمليات\n\n❌ لا يوجد عمليات مسجلة حتى الآن."
        else:
            message = f"📋 سجل العمليات (آخر {len(logs)} عمليات)\n\n"
            
            for log in logs:
                status = "✅" if log["success"] else "❌"
                timestamp = log["timestamp"][:19]  # إزالة الميكروثواني
                message += f"{status} {log["operation_type"]}\n"
                message += f"   📅 {timestamp}\n"
                message += f"   📝 {log["operation_details"]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def discover_devices(self, query):
        """اكتشاف الأجهزة في الشبكة"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        # عرض رسالة المعالجة
        await query.edit_message_text("🔍 جاري اكتشاف الأجهزة في الشبكة... قد يستغرق الأمر بعض الوقت.")
        
        devices = client.discover_devices()
        
        if not devices:
            message = "🌐 اكتشاف الأجهزة\n\n❌ لم يتم العثور على أجهزة في الشبكة."
        else:
            message = f"🌐 الأجهزة المكتشفة ({len(devices)})\n\n"
            
            for i, device in enumerate(devices[:10], 1):
                message += f"{i}. 📱 {device.hostname or 'جهاز غير معروف'}\n"
                message += f"   📍 IP: {device.ip_address}\n"
                if device.mac_address:
                    message += f"   🔗 MAC: {device.mac_address}\n"
                if device.vendor:
                    message += f"   🏭 الشركة: {device.vendor}\n"
                message += "\n"
            
            if len(devices) > 10:
                message += f"... و {len(devices) - 10} أجهزة أخرى"
        
        keyboard = [[InlineKeyboardButton("🔄 إعادة المسح", callback_data="discover_devices"),
                    InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "discover", f"اكتشاف {len(devices)} جهاز", True)
    
    async def show_hotspot_cards_menu(self, query):
        """عرض قائمة كروت الهوتسبوت"""
        await query.edit_message_text(
            "🎫 إدارة كروت الهوتسبوت\n\nاختر العملية المطلوبة:",
            reply_markup=self.create_hotspot_cards_keyboard()
        )
    
    async def show_troubleshoot_menu(self, query):
        """عرض قائمة تشخيص المشاكل"""
        await query.edit_message_text(
            "🔍 تشخيص المشاكل وأدوات الشبكة\n\nاختر أداة التشخيص:",
            reply_markup=self.create_troubleshoot_keyboard()
        )

    async def show_system_health_check(self, query):
        """إجراء فحص صحة النظام وعرض النتائج"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        await query.edit_message_text("🩺 جاري فحص صحة النظام... يرجى الانتظار.")
        
        health = client.get_system_health()
        
        if not health:
            await query.edit_message_text("❌ فشل في فحص صحة النظام. يرجى التأكد من اتصال الراوتر.")
            return
        
        status_icon = {"success": "✅", "warning": "⚠️", "error": "❌"}
        overall_icon = status_icon.get(health.overall_status, "❓")
        
        message = f"🩺 تقرير صحة النظام\n\n"
        message += f"{overall_icon} الحالة العامة: **{health.overall_status.upper()}**\n\n"
        
        message += f"{status_icon.get(health.cpu_status.status, '❓')} المعالج: {health.cpu_status.message}\n"
        message += f"{status_icon.get(health.memory_status.status, '❓')} الذاكرة: {health.memory_status.message}\n"
        message += f"{status_icon.get(health.interface_status.status, '❓')} الواجهات: {health.interface_status.message}\n\n"
        
        if health.recommendations:
            message += "💡 التوصيات:\n"
            for rec in health.recommendations:
                message += f"• {rec}\n"
        
        keyboard = [[InlineKeyboardButton("🔄 إعادة الفحص", callback_data="system_health_check"),
                    InlineKeyboardButton("🔙 العودة لقائمة التشخيص", callback_data="troubleshoot")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "system_health_check", "فحص صحة النظام", True)

    async def prompt_ping_test(self, query, context):
        """طلب عنوان IP أو اسم المضيف لاختبار Ping"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        await query.edit_message_text("🏓 اختبار Ping\n\nيرجى إدخال عنوان IP أو اسم المضيف الذي ترغب في اختباره:")
        context.user_data["waiting_for_ping_target"] = True

    async def handle_ping_test_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات اختبار Ping وتنفيذ الاختبار"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        client = self.get_user_connection(user_id)

        if not client or not client.is_connected():
            await update.message.reply_text(MESSAGES["not_logged_in"])
            context.user_data.pop("waiting_for_ping_target", None)
            return

        await update.message.reply_text(f"🏓 جاري اختبار Ping لـ {target}... يرجى الانتظار.")
        
        ping_results = client.ping_test(target)

        if not ping_results:
            message = f"❌ فشل اختبار Ping لـ {target}. يرجى التحقق من العنوان أو الاتصال."
        else:
            message = f"🏓 نتائج اختبار Ping لـ {target}:\n\n"
            message += f"• الحزم المرسلة: {ping_results.sent}\n"
            message += f"• الحزم المستلمة: {ping_results.received}\n"
            message += f"• الحزم المفقودة: {ping_results.lost}\n"
            if ping_results.avg_rtt:
                message += f"• متوسط زمن الاستجابة: {ping_results.avg_rtt}ms\n"
            if ping_results.min_rtt:
                message += f"• أدنى زمن استجابة: {ping_results.min_rtt}ms\n"
            if ping_results.max_rtt:
                message += f"• أقصى زمن استجابة: {ping_results.max_rtt}ms\n"

        keyboard = [[InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="ping_test"),
                    InlineKeyboardButton("🔙 العودة لقائمة التشخيص", callback_data="troubleshoot")]]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "ping_test", f"اختبار Ping لـ {target}", True)
        context.user_data.pop("waiting_for_ping_target", None)

    async def prompt_traceroute_test(self, query, context):
        """طلب عنوان IP أو اسم المضيف لاختبار Traceroute"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        await query.edit_message_text("🛤️ تتبع المسار (Traceroute)\n\nيرجى إدخال عنوان IP أو اسم المضيف الذي ترغب في تتبع مساره:")
        context.user_data["waiting_for_traceroute_target"] = True

    async def handle_traceroute_test_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات اختبار Traceroute وتنفيذ الاختبار"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        client = self.get_user_connection(user_id)

        if not client or not client.is_connected():
            await update.message.reply_text(MESSAGES["not_logged_in"])
            context.user_data.pop("waiting_for_traceroute_target", None)
            return

        await update.message.reply_text(f"🛤️ جاري تتبع المسار لـ {target}... قد يستغرق الأمر بعض الوقت.")
        
        traceroute_results = client.traceroute_test(target)

        if not traceroute_results:
            message = f"❌ فشل تتبع المسار لـ {target}. يرجى التحقق من العنوان أو الاتصال."
        else:
            message = f"🛤️ نتائج تتبع المسار لـ {target}:\n\n"
            for hop in traceroute_results:
                message += f"• {hop.hop_number}. {hop.address} ({hop.rtt}ms)\n"

        keyboard = [[InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="traceroute_test"),
                    InlineKeyboardButton("🔙 العودة لقائمة التشخيص", callback_data="troubleshoot")]]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "traceroute_test", f"تتبع المسار لـ {target}", True)
        context.user_data.pop("waiting_for_traceroute_target", None)

    async def prompt_speed_test(self, query, context):
        """طلب واجهة لاختبار السرعة"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        interfaces = client.get_interfaces()
        if not interfaces:
            await query.edit_message_text("❌ لا توجد واجهات متاحة لاختبار السرعة.")
            return

        keyboard_buttons = []
        for iface in interfaces:
            keyboard_buttons.append([InlineKeyboardButton(iface.name, callback_data=f"speed_test_iface:{iface.name}")])
        keyboard_buttons.append([InlineKeyboardButton("🔙 العودة لقائمة التشخيص", callback_data="troubleshoot")])

        await query.edit_message_text("⚡ اختبار السرعة\n\nيرجى اختيار الواجهة التي ترغب في اختبار سرعتها:",
                                      reply_markup=InlineKeyboardMarkup(keyboard_buttons))
        context.user_data["waiting_for_speed_test_iface"] = True

    async def handle_speed_test_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات اختبار السرعة وتنفيذ الاختبار"""
        user_id = update.effective_user.id
        callback_data = update.callback_query.data
        interface_name = callback_data.split(":")[1]
        client = self.get_user_connection(user_id)

        if not client or not client.is_connected():
            await update.callback_query.edit_message_text(MESSAGES["not_logged_in"])
            context.user_data.pop("waiting_for_speed_test_iface", None)
            return

        await update.callback_query.edit_message_text(f"⚡ جاري اختبار السرعة للواجهة {interface_name}... يرجى الانتظار.")
        
        speed_results = client.speed_test(interface_name)

        if not speed_results:
            message = f"❌ فشل اختبار السرعة للواجهة {interface_name}. يرجى التحقق من الواجهة أو الاتصال."
        else:
            message = f"⚡ نتائج اختبار السرعة للواجهة {interface_name}:\n\n"
            message += f"• التحميل: {speed_results.download_speed_mbps:.2f} Mbps\n"
            message += f"• الرفع: {speed_results.upload_speed_mbps:.2f} Mbps\n"

        keyboard = [[InlineKeyboardButton("🔄 إعادة الاختبار", callback_data=f"speed_test_iface:{interface_name}"),
                    InlineKeyboardButton("🔙 العودة لقائمة التشخيص", callback_data="troubleshoot")]]
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "speed_test", f"اختبار السرعة للواجهة {interface_name}", True)
        context.user_data.pop("waiting_for_speed_test_iface", None)

    async def prompt_generate_cards(self, query, context):
        """طلب تفاصيل توليد الكروت"""
        user_id = query.from_user.id
        client = self.get_user_connection(user_id)
        
        if not client or not client.is_connected():
            await query.edit_message_text(MESSAGES["not_logged_in"])
            return
        
        await query.edit_message_text("🎫 توليد كروت هوتسبوت جديدة\n\nيرجى إدخال التفاصيل بالتنسيق التالي:\nالعدد:البيانات:الوقت:الصلاحية\n\nمثال:\n10:1GB:1H:7 (10 كروت، 1 جيجابايت، ساعة واحدة، صالحة لمدة 7 أيام)\n\nالبيانات: يمكن أن تكون 1GB, 500MB, unlimited\nالوقت: يمكن أن يكون 1H, 30M, unlimited\nالصلاحية: عدد الأيام (مثال: 7, 30, 365)")
        context.user_data["waiting_for_card_details"] = True

    async def handle_generate_cards_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات توليد الكروت وتنفيذ العملية"""
        user_id = update.effective_user.id
        details = update.message.text.strip()
        client = self.get_user_connection(user_id)

        if not client or not client.is_connected():
            await update.message.reply_text(MESSAGES["not_logged_in"])
            context.user_data.pop("waiting_for_card_details", None)
            return

        parts = details.split(":")
        if len(parts) != 4:
            await update.message.reply_text("❌ تنسيق خاطئ. يرجى استخدام التنسيق:\nالعدد:البيانات:الوقت:الصلاحية")
            return

        try:
            count = int(parts[0])
            data_quota = parts[1]
            time_quota = parts[2]
            validity_days = int(parts[3])
        except ValueError:
            await update.message.reply_text("❌ بيانات غير صالحة. يرجى التحقق من الأرقام.")
            return

        await update.message.reply_text(f"🎫 جاري توليد {count} كرت هوتسبوت... يرجى الانتظار.")
        
        generated_cards = client.generate_hotspot_cards(count, data_quota, time_quota, validity_days)

        if not generated_cards:
            message = "❌ فشل في توليد الكروت. يرجى التحقق من إعدادات الميكروتك."
        else:
            message = f"✅ تم توليد {len(generated_cards)} كرت بنجاح!\n\n"
            for i, card in enumerate(generated_cards[:5], 1):
                message += f"{i}. 👤 {card.username} | 🔑 {card.password}\n"
            if len(generated_cards) > 5:
                message += f"... و {len(generated_cards) - 5} كروت أخرى.\n"
            message += "\nيمكنك عرض جميع الكروت المولدة في قائمة 'الكروت المحفوظة'."

        keyboard = [[InlineKeyboardButton("🗂️ عرض الكروت المحفوظة", callback_data="saved_cards"),
                    InlineKeyboardButton("🔙 العودة لقائمة الكروت", callback_data="hotspot_cards")]]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "generate_cards", f"توليد {count} كرت هوتسبوت", True)
        context.user_data.pop("waiting_for_card_details", None)

    async def show_saved_cards(self, query):
        """عرض الكروت المحفوظة"""
        user_id = query.from_user.id
        saved_cards = self.db.get_saved_hotspot_cards(user_id)

        if not saved_cards:
            message = "🗂️ الكروت المحفوظة\n\n❌ لا توجد كروت هوتسبوت محفوظة حتى الآن."
        else:
            message = f"🗂️ الكروت المحفوظة ({len(saved_cards)})\n\n"
            for i, card in enumerate(saved_cards[:10], 1):
                message += f"{i}. 👤 {card.username} | 🔑 {card.password} | 📊 {card.data_quota} | ⏰ {card.time_quota}\n"
            if len(saved_cards) > 10:
                message += f"... و {len(saved_cards) - 10} كروت أخرى.\n"
            message += "\nيمكنك طباعة هذه الكروت باستخدام خيار 'طباعة الكروت'."

        keyboard = [[InlineKeyboardButton("🔄 تحديث القائمة", callback_data="saved_cards"),
                    InlineKeyboardButton("🔙 العودة لقائمة الكروت", callback_data="hotspot_cards")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "show_saved_cards", "عرض الكروت المحفوظة", True)



