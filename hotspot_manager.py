"""
مدير الهوتسبوت المتقدم مع ميزات إضافية
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from mikrotik_api_client import MikroTikAPIClient
from card_generator import HotspotCardGenerator
from database import DatabaseManager
from models import HotspotUser, HotspotCard

logger = logging.getLogger(__name__)

class HotspotManager:
    """مدير الهوتسبوت المتقدم"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.card_generator = HotspotCardGenerator()
    
    async def handle_generate_cards_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالج توليد الكروت"""
        await query.edit_message_text(
            "🎫 توليد كروت هوتسبوت جديدة\n\n"
            "يرجى إدخال معايير الكروت بالتنسيق التالي:\n"
            "العدد:البادئة:البروفايل:البيانات_MB:الوقت_ساعة:الأيام\n\n"
            "مثال:\n"
            "10:user:default:1024:24:30\n\n"
            "هذا سينشئ 10 كروت بادئة 'user' مع 1GB بيانات و 24 ساعة لمدة 30 يوم"
        )
        
        context.user_data['waiting_for_card_params'] = True
    
    async def handle_card_generation_params(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة معايير توليد الكروت"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        try:
            # تحليل المعايير
            parts = text.split(':')
            if len(parts) != 6:
                await update.message.reply_text(
                    "❌ تنسيق خاطئ. يرجى استخدام:\n"
                    "العدد:البادئة:البروفايل:البيانات_MB:الوقت_ساعة:الأيام"
                )
                return
            
            count = int(parts[0])
            prefix = parts[1]
            profile = parts[2]
            data_quota_mb = int(parts[3])
            time_quota_hours = int(parts[4])
            validity_days = int(parts[5])
            
            # التحقق من القيود
            if count <= 0 or count > 100:
                await update.message.reply_text("❌ عدد الكروت يجب أن يكون بين 1 و 100")
                return
            
            if data_quota_mb < 0:
                await update.message.reply_text("❌ حصة البيانات يجب أن تكون أكبر من أو تساوي 0")
                return
            
            if time_quota_hours < 0:
                await update.message.reply_text("❌ حصة الوقت يجب أن تكون أكبر من أو تساوي 0")
                return
            
            if validity_days <= 0:
                await update.message.reply_text("❌ مدة الصلاحية يجب أن تكون أكبر من 0")
                return
            
            # عرض رسالة المعالجة
            processing_msg = await update.message.reply_text("⏳ جاري توليد الكروت...")
            
            # توليد الكروت
            cards = self.card_generator.generate_cards(
                count=count,
                prefix=prefix,
                profile=profile,
                data_quota_mb=data_quota_mb,
                time_quota_hours=time_quota_hours,
                validity_days=validity_days
            )
            
            # حفظ الكروت في قاعدة البيانات
            cards_data = []
            for card in cards:
                cards_data.append({
                    'username': card.username,
                    'password': card.password,
                    'profile': card.profile,
                    'data_quota': card.data_quota,
                    'time_quota': card.time_quota,
                    'validity_days': card.validity_days
                })
            
            self.db.save_hotspot_cards(user_id, cards_data)
            
            # إنشاء ملف PDF
            pdf_data = self.card_generator.create_multiple_cards_pdf(cards)
            
            # إنشاء ملخص نصي
            summary = self.card_generator.create_card_summary_text(cards)
            
            # إرسال الملخص
            keyboard = [
                [
                    InlineKeyboardButton("📤 إضافة للميكروتك", callback_data=f"add_cards_to_mikrotik:{len(cards)}"),
                    InlineKeyboardButton("📋 عرض التفاصيل", callback_data="show_card_details")
                ],
                [
                    InlineKeyboardButton("🔙 العودة", callback_data="hotspot_cards")
                ]
            ]
            
            await processing_msg.edit_text(
                summary,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # إرسال ملف PDF
            await update.message.reply_document(
                document=pdf_data,
                filename=f"hotspot_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                caption=f"📄 ملف PDF يحتوي على {count} كرت هوتسبوت"
            )
            
            # حفظ الكروت في سياق المستخدم للاستخدام اللاحق
            context.user_data['generated_cards'] = cards
            
            self.db.log_operation(user_id, "generate_cards", f"توليد {count} كرت", True)
            
        except ValueError as e:
            await update.message.reply_text(f"❌ خطأ في القيم المدخلة: {e}")
        except Exception as e:
            logger.error(f"خطأ في توليد الكروت: {e}")
            await update.message.reply_text(f"❌ خطأ في توليد الكروت: {e}")
            self.db.log_operation(user_id, "generate_cards", f"فشل في توليد الكروت: {e}", False)
        
        # إزالة حالة انتظار معايير الكروت
        context.user_data.pop('waiting_for_card_params', None)
    
    async def handle_add_cards_to_mikrotik(self, query, context: ContextTypes.DEFAULT_TYPE):
        """إضافة الكروت المولدة إلى الميكروتك"""
        user_id = query.from_user.id
        
        # الحصول على الكروت المولدة
        cards = context.user_data.get('generated_cards', [])
        if not cards:
            await query.edit_message_text("❌ لا توجد كروت مولدة للإضافة")
            return
        
        # الحصول على اتصال الميكروتك
        from telegram_handlers import TelegramHandlers
        handlers = context.bot_data.get('handlers')
        if not handlers:
            await query.edit_message_text("❌ خطأ في النظام")
            return
        
        client = handlers.get_user_connection(user_id)
        if not client or not client.is_connected():
            await query.edit_message_text("❌ غير متصل بالميكروتك. يرجى تسجيل الدخول أولاً.")
            return
        
        # عرض رسالة المعالجة
        await query.edit_message_text(f"⏳ جاري إضافة {len(cards)} كرت إلى الميكروتك...")
        
        # تحويل الكروت إلى مستخدمي هوتسبوت
        users = self.card_generator.convert_cards_to_hotspot_users(cards)
        
        # إضافة المستخدمين
        success_count = 0
        failed_users = []
        
        for user in users:
            if client.add_hotspot_user(user):
                success_count += 1
            else:
                failed_users.append(user.name)
        
        # إنشاء رسالة النتيجة
        if success_count == len(users):
            message = f"✅ تم إضافة جميع الكروت بنجاح ({success_count}/{len(users)})"
            self.db.log_operation(user_id, "add_cards", f"إضافة {success_count} كرت بنجاح", True)
        else:
            message = f"⚠️ تم إضافة {success_count} من {len(users)} كرت\n\n"
            if failed_users:
                message += f"فشل في إضافة: {', '.join(failed_users[:5])}"
                if len(failed_users) > 5:
                    message += f" و {len(failed_users) - 5} آخرين"
            
            self.db.log_operation(user_id, "add_cards", 
                                f"إضافة {success_count}/{len(users)} كرت", 
                                success_count > 0)
        
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="hotspot_cards")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_saved_cards_callback(self, query):
        """عرض الكروت المحفوظة"""
        user_id = query.from_user.id
        saved_cards = self.db.get_user_hotspot_cards(user_id, 20)
        
        if not saved_cards:
            message = "📋 الكروت المحفوظة\n\n❌ لا توجد كروت محفوظة"
        else:
            message = f"📋 الكروت المحفوظة (آخر {len(saved_cards)} كرت)\n\n"
            
            for i, card in enumerate(saved_cards[:10], 1):
                created_date = card['created_at'][:10]  # تاريخ الإنشاء فقط
                message += f"{i}. 👤 {card['username']} | 🔑 {card['password']}\n"
                message += f"   📊 {card['data_quota']} | ⏰ {card['time_quota']}\n"
                message += f"   📅 {created_date}\n\n"
            
            if len(saved_cards) > 10:
                message += f"... و {len(saved_cards) - 10} كرت إضافي"
        
        keyboard = [
            [
                InlineKeyboardButton("📤 تصدير PDF", callback_data="export_saved_cards"),
                InlineKeyboardButton("🗑️ مسح الكروت", callback_data="clear_saved_cards")
            ],
            [
                InlineKeyboardButton("🔙 العودة", callback_data="hotspot_cards")
            ]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_hotspot_add_user(self, query, context: ContextTypes.DEFAULT_TYPE):
        """إضافة مستخدم هوتسبوت يدوياً"""
        await query.edit_message_text(
            "➕ إضافة مستخدم هوتسبوت\n\n"
            "يرجى إدخال بيانات المستخدم بالتنسيق التالي:\n"
            "اسم_المستخدم:كلمة_المرور:البروفايل:البيانات_MB:الوقت_ساعة\n\n"
            "مثال:\n"
            "ahmed123:pass123:default:2048:48\n\n"
            "هذا سينشئ مستخدم 'ahmed123' مع 2GB بيانات و 48 ساعة"
        )
        
        context.user_data['waiting_for_user_data'] = True
    
    async def handle_user_addition_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات إضافة المستخدم"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        try:
            # تحليل البيانات
            parts = text.split(':')
            if len(parts) != 5:
                await update.message.reply_text(
                    "❌ تنسيق خاطئ. يرجى استخدام:\n"
                    "اسم_المستخدم:كلمة_المرور:البروفايل:البيانات_MB:الوقت_ساعة"
                )
                return
            
            username = parts[0]
            password = parts[1]
            profile = parts[2]
            data_quota_mb = int(parts[3])
            time_quota_hours = int(parts[4])
            
            # التحقق من صحة البيانات
            if not username or not password:
                await update.message.reply_text("❌ اسم المستخدم وكلمة المرور مطلوبان")
                return
            
            if data_quota_mb < 0 or time_quota_hours < 0:
                await update.message.reply_text("❌ القيم يجب أن تكون أكبر من أو تساوي 0")
                return
            
            # الحصول على اتصال الميكروتك
            from telegram_handlers import TelegramHandlers
            handlers = context.bot_data.get('handlers')
            if not handlers:
                await update.message.reply_text("❌ خطأ في النظام")
                return
            
            client = handlers.get_user_connection(user_id)
            if not client or not client.is_connected():
                await update.message.reply_text("❌ غير متصل بالميكروتك. يرجى تسجيل الدخول أولاً.")
                return
            
            # إنشاء مستخدم الهوتسبوت
            data_limit = f"{data_quota_mb}M" if data_quota_mb > 0 else ""
            time_limit = f"{time_quota_hours}h" if time_quota_hours > 0 else ""
            
            hotspot_user = HotspotUser(
                name=username,
                password=password,
                profile=profile,
                limit_bytes_total=data_limit,
                limit_uptime=time_limit,
                comment=f"Added manually on {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            # إضافة المستخدم
            processing_msg = await update.message.reply_text("⏳ جاري إضافة المستخدم...")
            
            if client.add_hotspot_user(hotspot_user):
                await processing_msg.edit_text(
                    f"✅ تم إضافة المستخدم بنجاح\n\n"
                    f"👤 اسم المستخدم: {username}\n"
                    f"🔑 كلمة المرور: {password}\n"
                    f"📊 البروفايل: {profile}\n"
                    f"💾 حصة البيانات: {data_quota_mb} MB\n"
                    f"⏰ حصة الوقت: {time_quota_hours} ساعة"
                )
                
                self.db.log_operation(user_id, "add_user", f"إضافة مستخدم {username}", True)
            else:
                await processing_msg.edit_text(f"❌ فشل في إضافة المستخدم {username}")
                self.db.log_operation(user_id, "add_user", f"فشل في إضافة مستخدم {username}", False)
            
        except ValueError as e:
            await update.message.reply_text(f"❌ خطأ في القيم المدخلة: {e}")
        except Exception as e:
            logger.error(f"خطأ في إضافة المستخدم: {e}")
            await update.message.reply_text(f"❌ خطأ في إضافة المستخدم: {e}")
            self.db.log_operation(user_id, "add_user", f"خطأ في إضافة المستخدم: {e}", False)
        
        # إزالة حالة انتظار بيانات المستخدم
        context.user_data.pop('waiting_for_user_data', None)
    
    async def handle_hotspot_search(self, query, context: ContextTypes.DEFAULT_TYPE):
        """البحث عن مستخدم هوتسبوت"""
        await query.edit_message_text(
            "🔍 البحث عن مستخدم هوتسبوت\n\n"
            "يرجى إدخال اسم المستخدم للبحث عنه:"
        )
        
        context.user_data['waiting_for_search_query'] = True
    
    async def handle_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استعلام البحث"""
        user_id = update.effective_user.id
        search_term = update.message.text.strip()
        
        if not search_term:
            await update.message.reply_text("❌ يرجى إدخال اسم المستخدم للبحث")
            return
        
        # الحصول على اتصال الميكروتك
        from telegram_handlers import TelegramHandlers
        handlers = context.bot_data.get('handlers')
        if not handlers:
            await update.message.reply_text("❌ خطأ في النظام")
            return
        
        client = handlers.get_user_connection(user_id)
        if not client or not client.is_connected():
            await update.message.reply_text("❌ غير متصل بالميكروتك. يرجى تسجيل الدخول أولاً.")
            return
        
        # البحث في المستخدمين
        processing_msg = await update.message.reply_text("🔍 جاري البحث...")
        
        all_users = client.get_hotspot_users()
        active_users = client.get_hotspot_active_users()
        
        # البحث عن المستخدمين المطابقين
        matching_users = [user for user in all_users if search_term.lower() in user.name.lower()]
        
        if not matching_users:
            await processing_msg.edit_text(f"❌ لم يتم العثور على مستخدمين يحتوون على '{search_term}'")
        else:
            message = f"🔍 نتائج البحث عن '{search_term}' ({len(matching_users)} نتيجة)\n\n"
            
            for i, user in enumerate(matching_users[:10], 1):
                # فحص إذا كان المستخدم نشطاً
                is_active = any(active.name == user.name for active in active_users)
                status = "🟢 نشط" if is_active else ("🔴 معطل" if user.disabled else "⚪ غير متصل")
                
                message += f"{i}. 👤 {user.name}\n"
                message += f"   🔑 كلمة المرور: {user.password}\n"
                message += f"   📊 البروفايل: {user.profile}\n"
                message += f"   🔘 الحالة: {status}\n"
                
                if user.limit_bytes_total:
                    message += f"   💾 حصة البيانات: {user.limit_bytes_total}\n"
                if user.limit_uptime:
                    message += f"   ⏰ حصة الوقت: {user.limit_uptime}\n"
                
                message += "\n"
            
            if len(matching_users) > 10:
                message += f"... و {len(matching_users) - 10} نتيجة إضافية"
            
            await processing_msg.edit_text(message)
        
        self.db.log_operation(user_id, "search_user", f"البحث عن '{search_term}' - {len(matching_users)} نتيجة", True)
        
        # إزالة حالة انتظار استعلام البحث
        context.user_data.pop('waiting_for_search_query', None)

