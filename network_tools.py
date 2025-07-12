"""
أدوات الشبكة والتشخيص المتقدمة
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from mikrotik_api_client import MikroTikAPIClient
from database import DatabaseManager
from models import PingResult, TracerouteResult, NetworkDevice, SystemHealth

logger = logging.getLogger(__name__)

class NetworkTools:
    """أدوات الشبكة والتشخيص"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def handle_ping_test(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالج اختبار Ping"""
        await query.edit_message_text(
            "🏓 اختبار Ping\n\n"
            "يرجى إدخال عنوان IP أو اسم النطاق للاختبار:\n\n"
            "أمثلة:\n"
            "• 8.8.8.8\n"
            "• google.com\n"
            "• 192.168.1.1"
        )
        
        context.user_data['waiting_for_ping_target'] = True
    
    async def handle_ping_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة هدف اختبار Ping"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        
        if not target:
            await update.message.reply_text("❌ يرجى إدخال عنوان صحيح")
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
        
        # تنفيذ اختبار Ping
        processing_msg = await update.message.reply_text(f"🏓 جاري اختبار Ping لـ {target}...")
        
        ping_result = client.ping(target, count=4)
        
        if ping_result:
            # تنسيق النتيجة
            message = f"🏓 نتيجة اختبار Ping لـ {target}\n\n"
            message += f"📊 الإحصائيات:\n"
            message += f"• الحزم المرسلة: {ping_result.packets_sent}\n"
            message += f"• الحزم المستلمة: {ping_result.packets_received}\n"
            message += f"• نسبة الفقدان: {ping_result.packet_loss:.1f}%\n\n"
            
            if ping_result.packets_received > 0:
                message += f"⏱️ أوقات الاستجابة:\n"
                message += f"• الأدنى: {ping_result.min_time:.1f} ms\n"
                message += f"• المتوسط: {ping_result.avg_time:.1f} ms\n"
                message += f"• الأعلى: {ping_result.max_time:.1f} ms\n\n"
            
            # تحديد حالة الاتصال
            if ping_result.packet_loss == 0:
                status = "✅ ممتاز - لا يوجد فقدان في الحزم"
            elif ping_result.packet_loss < 25:
                status = "⚠️ جيد - فقدان قليل في الحزم"
            elif ping_result.packet_loss < 50:
                status = "🔶 متوسط - فقدان متوسط في الحزم"
            else:
                status = "❌ ضعيف - فقدان عالي في الحزم"
            
            message += f"🔘 حالة الاتصال: {status}"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="ping_test"),
                    InlineKeyboardButton("🛤️ تتبع المسار", callback_data="traceroute_test")
                ],
                [
                    InlineKeyboardButton("🔙 العودة", callback_data="troubleshoot")
                ]
            ]
            
            await processing_msg.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            self.db.log_operation(user_id, "ping_test", f"اختبار Ping لـ {target} - {ping_result.packet_loss}% فقدان", True)
        else:
            await processing_msg.edit_text(f"❌ فشل في اختبار Ping لـ {target}")
            self.db.log_operation(user_id, "ping_test", f"فشل اختبار Ping لـ {target}", False)
        
        # إزالة حالة انتظار هدف Ping
        context.user_data.pop('waiting_for_ping_target', None)
    
    async def handle_traceroute_test(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالج تتبع المسار"""
        await query.edit_message_text(
            "🛤️ تتبع المسار (Traceroute)\n\n"
            "يرجى إدخال عنوان IP أو اسم النطاق لتتبع المسار إليه:\n\n"
            "أمثلة:\n"
            "• 8.8.8.8\n"
            "• google.com\n"
            "• 192.168.1.1"
        )
        
        context.user_data['waiting_for_traceroute_target'] = True
    
    async def handle_traceroute_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة هدف تتبع المسار"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        
        if not target:
            await update.message.reply_text("❌ يرجى إدخال عنوان صحيح")
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
        
        # تنفيذ تتبع المسار
        processing_msg = await update.message.reply_text(f"🛤️ جاري تتبع المسار إلى {target}...")
        
        traceroute_result = client.traceroute(target)
        
        if traceroute_result:
            # تنسيق النتيجة
            message = f"🛤️ تتبع المسار إلى {target}\n\n"
            
            if traceroute_result.hops:
                message += "📍 المحطات:\n"
                for hop in traceroute_result.hops[:15]:  # عرض أول 15 محطة
                    hop_num = hop['hop']
                    address = hop['address']
                    time = hop['time']
                    
                    if address != '*':
                        message += f"{hop_num:2d}. {address} ({time})\n"
                    else:
                        message += f"{hop_num:2d}. * * * (timeout)\n"
                
                if len(traceroute_result.hops) > 15:
                    message += f"... و {len(traceroute_result.hops) - 15} محطة إضافية"
            else:
                message += "❌ لم يتم العثور على مسار إلى الهدف"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 إعادة التتبع", callback_data="traceroute_test"),
                    InlineKeyboardButton("🏓 اختبار Ping", callback_data="ping_test")
                ],
                [
                    InlineKeyboardButton("🔙 العودة", callback_data="troubleshoot")
                ]
            ]
            
            await processing_msg.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            self.db.log_operation(user_id, "traceroute_test", f"تتبع المسار إلى {target} - {len(traceroute_result.hops)} محطة", True)
        else:
            await processing_msg.edit_text(f"❌ فشل في تتبع المسار إلى {target}")
            self.db.log_operation(user_id, "traceroute_test", f"فشل تتبع المسار إلى {target}", False)
        
        # إزالة حالة انتظار هدف Traceroute
        context.user_data.pop('waiting_for_traceroute_target', None)
    
    async def handle_advanced_diagnostics(self, query, context: ContextTypes.DEFAULT_TYPE):
        """تشخيص متقدم للشبكة"""
        user_id = query.from_user.id
        
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
        await query.edit_message_text("🔍 جاري إجراء تشخيص شامل للشبكة...")
        
        # جمع معلومات شاملة
        system_info = client.get_system_info()
        interfaces = client.get_interfaces()
        health = client.get_system_health()
        
        if not system_info or not health:
            await query.edit_message_text("❌ فشل في جمع معلومات التشخيص")
            return
        
        # إنشاء تقرير التشخيص
        message = "🔍 تقرير التشخيص الشامل\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # حالة النظام العامة
        status_icons = {"success": "✅", "warning": "⚠️", "error": "❌"}
        overall_icon = status_icons.get(health.overall_status, "❓")
        message += f"{overall_icon} الحالة العامة: {health.overall_status.upper()}\n\n"
        
        # تفاصيل الأداء
        message += "📊 أداء النظام:\n"
        message += f"• المعالج: {system_info.cpu_load}% ({health.cpu_status.status})\n"
        message += f"• الذاكرة: {system_info.memory_usage_percent}% ({health.memory_status.status})\n"
        message += f"• الحرارة: {system_info.temperature}°C\n"
        message += f"• الفولط: {system_info.voltage}V\n"
        message += f"• مدة التشغيل: {system_info.uptime}\n\n"
        
        # حالة الواجهات
        running_interfaces = [iface for iface in interfaces if iface.running and not iface.disabled]
        total_interfaces = len(interfaces)
        
        message += f"🌐 الواجهات ({len(running_interfaces)}/{total_interfaces} نشطة):\n"
        for iface in running_interfaces[:5]:  # عرض أول 5 واجهات
            rx_mb = iface.rx_mb
            tx_mb = iface.tx_mb
            message += f"• {iface.name}: ⬇️{rx_mb:.1f}MB ⬆️{tx_mb:.1f}MB\n"
        
        if len(running_interfaces) > 5:
            message += f"... و {len(running_interfaces) - 5} واجهة إضافية\n"
        
        message += "\n"
        
        # التوصيات
        if health.recommendations:
            message += "💡 التوصيات:\n"
            for rec in health.recommendations[:3]:  # عرض أول 3 توصيات
                message += f"• {rec}\n"
            
            if len(health.recommendations) > 3:
                message += f"... و {len(health.recommendations) - 3} توصية إضافية\n"
        
        # أزرار الإجراءات
        keyboard = [
            [
                InlineKeyboardButton("🏓 اختبار الاتصال", callback_data="ping_test"),
                InlineKeyboardButton("🛤️ تتبع المسار", callback_data="traceroute_test")
            ],
            [
                InlineKeyboardButton("🌐 اكتشاف الأجهزة", callback_data="discover_devices"),
                InlineKeyboardButton("🔄 إعادة الفحص", callback_data="advanced_diagnostics")
            ],
            [
                InlineKeyboardButton("🔙 العودة", callback_data="troubleshoot")
            ]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "advanced_diagnostics", f"تشخيص شامل - حالة {health.overall_status}", True)
    
    async def handle_interface_monitor(self, query, context: ContextTypes.DEFAULT_TYPE):
        """مراقب الواجهات"""
        user_id = query.from_user.id
        
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
        
        # الحصول على معلومات الواجهات
        await query.edit_message_text("🌐 جاري جمع معلومات الواجهات...")
        
        interfaces = client.get_interfaces()
        
        if not interfaces:
            await query.edit_message_text("❌ فشل في الحصول على معلومات الواجهات")
            return
        
        # تنسيق معلومات الواجهات
        message = f"🌐 مراقب الواجهات ({len(interfaces)} واجهة)\n\n"
        
        for iface in interfaces:
            # تحديد حالة الواجهة
            if iface.disabled:
                status = "🔴 معطلة"
            elif iface.running:
                status = "🟢 نشطة"
            else:
                status = "🟡 غير نشطة"
            
            message += f"📡 {iface.name} ({iface.type})\n"
            message += f"   🔘 الحالة: {status}\n"
            
            if iface.running:
                message += f"   📊 البيانات: ⬇️{iface.rx_mb:.1f}MB ⬆️{iface.tx_mb:.1f}MB\n"
                message += f"   📦 الحزم: ⬇️{iface.rx_packets} ⬆️{iface.tx_packets}\n"
                
                if iface.rx_errors > 0 or iface.tx_errors > 0:
                    message += f"   ⚠️ الأخطاء: ⬇️{iface.rx_errors} ⬆️{iface.tx_errors}\n"
            
            message += "\n"
        
        # إحصائيات عامة
        running_count = len([iface for iface in interfaces if iface.running])
        disabled_count = len([iface for iface in interfaces if iface.disabled])
        
        message += f"📈 الإحصائيات:\n"
        message += f"• الواجهات النشطة: {running_count}\n"
        message += f"• الواجهات المعطلة: {disabled_count}\n"
        message += f"• إجمالي البيانات: ⬇️{sum(iface.rx_mb for iface in interfaces):.1f}MB ⬆️{sum(iface.tx_mb for iface in interfaces):.1f}MB"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 تحديث", callback_data="interface_monitor"),
                InlineKeyboardButton("📊 إحصائيات مفصلة", callback_data="interface_stats")
            ],
            [
                InlineKeyboardButton("🔙 العودة", callback_data="troubleshoot")
            ]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "interface_monitor", f"مراقبة {len(interfaces)} واجهة", True)
    
    async def handle_network_speed_test(self, query, context: ContextTypes.DEFAULT_TYPE):
        """اختبار سرعة الشبكة"""
        user_id = query.from_user.id
        
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
        
        # اختبار سرعة الشبكة عبر ping لعدة خوادم
        await query.edit_message_text("🚀 جاري اختبار سرعة الشبكة...")
        
        test_servers = [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
            ("208.67.222.222", "OpenDNS")
        ]
        
        results = []
        
        for server_ip, server_name in test_servers:
            ping_result = client.ping(server_ip, count=3)
            if ping_result and ping_result.packets_received > 0:
                results.append({
                    'name': server_name,
                    'ip': server_ip,
                    'avg_time': ping_result.avg_time,
                    'packet_loss': ping_result.packet_loss
                })
        
        if not results:
            await query.edit_message_text("❌ فشل في اختبار سرعة الشبكة")
            return
        
        # تنسيق النتائج
        message = "🚀 نتائج اختبار سرعة الشبكة\n\n"
        
        for result in results:
            message += f"🌐 {result['name']} ({result['ip']})\n"
            message += f"   ⏱️ زمن الاستجابة: {result['avg_time']:.1f} ms\n"
            message += f"   📊 فقدان الحزم: {result['packet_loss']:.1f}%\n\n"
        
        # تقييم الأداء
        avg_response_time = sum(r['avg_time'] for r in results) / len(results)
        avg_packet_loss = sum(r['packet_loss'] for r in results) / len(results)
        
        if avg_response_time < 50 and avg_packet_loss == 0:
            performance = "🟢 ممتاز"
        elif avg_response_time < 100 and avg_packet_loss < 5:
            performance = "🟡 جيد"
        elif avg_response_time < 200 and avg_packet_loss < 10:
            performance = "🟠 متوسط"
        else:
            performance = "🔴 ضعيف"
        
        message += f"📈 تقييم الأداء: {performance}\n"
        message += f"⏱️ متوسط زمن الاستجابة: {avg_response_time:.1f} ms\n"
        message += f"📊 متوسط فقدان الحزم: {avg_packet_loss:.1f}%"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="network_speed_test"),
                InlineKeyboardButton("🏓 اختبار مخصص", callback_data="ping_test")
            ],
            [
                InlineKeyboardButton("🔙 العودة", callback_data="troubleshoot")
            ]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.db.log_operation(user_id, "speed_test", f"اختبار السرعة - {performance}", True)

