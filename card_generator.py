"""
مولد كروت الهوتسبوت مع إنشاء ملفات PDF
"""

import logging
import random
import string
from typing import List, Dict, Any
from datetime import datetime, timedelta
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models import HotspotCard, HotspotUser

logger = logging.getLogger(__name__)

class HotspotCardGenerator:
    """مولد كروت الهوتسبوت"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_arabic_fonts()
        self.setup_custom_styles()
    
    def setup_arabic_fonts(self):
        """إعداد الخطوط العربية"""
        try:
            # محاولة تسجيل خط عربي (يمكن تخصيصه حسب الخطوط المتاحة)
            # pdfmetrics.registerFont(TTFont('Arabic', 'path/to/arabic/font.ttf'))
            pass
        except:
            # استخدام الخط الافتراضي إذا لم يكن الخط العربي متاحاً
            logger.warning("لم يتم العثور على خط عربي، سيتم استخدام الخط الافتراضي")
    
    def setup_custom_styles(self):
        """إعداد أنماط مخصصة"""
        self.card_title_style = ParagraphStyle(
            'CardTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        self.card_content_style = ParagraphStyle(
            'CardContent',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            rightIndent=5,
            leftIndent=5
        )
        
        self.card_value_style = ParagraphStyle(
            'CardValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.darkgreen,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
    
    def generate_username(self, prefix: str = "user", length: int = 6) -> str:
        """توليد اسم مستخدم عشوائي"""
        suffix = ''.join(random.choices(string.digits, k=length))
        return f"{prefix}{suffix}"
    
    def generate_password(self, length: int = 8) -> str:
        """توليد كلمة مرور عشوائية"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    
    def format_data_quota(self, quota_mb: int) -> str:
        """تنسيق حصة البيانات"""
        if quota_mb == 0:
            return "غير محدود"
        elif quota_mb < 1024:
            return f"{quota_mb} MB"
        else:
            return f"{quota_mb / 1024:.1f} GB"
    
    def format_time_quota(self, quota_hours: int) -> str:
        """تنسيق حصة الوقت"""
        if quota_hours == 0:
            return "غير محدود"
        elif quota_hours < 24:
            return f"{quota_hours} ساعة"
        else:
            days = quota_hours // 24
            hours = quota_hours % 24
            if hours == 0:
                return f"{days} يوم"
            else:
                return f"{days} يوم و {hours} ساعة"
    
    def generate_cards(self, count: int, prefix: str = "user", profile: str = "default",
                      data_quota_mb: int = 1024, time_quota_hours: int = 24,
                      validity_days: int = 30) -> List[HotspotCard]:
        """توليد مجموعة من كروت الهوتسبوت"""
        cards = []
        
        for i in range(count):
            username = self.generate_username(prefix)
            password = self.generate_password()
            
            card = HotspotCard(
                username=username,
                password=password,
                profile=profile,
                data_quota=self.format_data_quota(data_quota_mb),
                time_quota=self.format_time_quota(time_quota_hours),
                validity_days=validity_days
            )
            
            cards.append(card)
        
        logger.info(f"تم توليد {count} كرت هوتسبوت")
        return cards
    
    def create_card_table_data(self, card: HotspotCard) -> List[List[str]]:
        """إنشاء بيانات جدول الكرت"""
        return [
            ["اسم المستخدم:", card.username],
            ["كلمة المرور:", card.password],
            ["البروفايل:", card.profile],
            ["حصة البيانات:", card.data_quota],
            ["حصة الوقت:", card.time_quota],
            ["صالح لمدة:", f"{card.validity_days} يوم"],
            ["تاريخ الإنشاء:", card.created_at.strftime("%Y-%m-%d")]
        ]
    
    def create_single_card_pdf(self, card: HotspotCard) -> bytes:
        """إنشاء PDF لكرت واحد"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                               topMargin=20*mm, bottomMargin=20*mm)
        
        story = []
        
        # عنوان الكرت
        title = Paragraph("كرت هوتسبوت", self.card_title_style)
        story.append(title)
        story.append(Spacer(1, 10*mm))
        
        # بيانات الكرت في جدول
        data = self.create_card_table_data(card)
        table = Table(data, colWidths=[40*mm, 60*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 10*mm))
        
        # معلومات إضافية
        info_text = """
        تعليمات الاستخدام:
        1. اتصل بشبكة الواي فاي
        2. افتح المتصفح وانتقل إلى أي موقع
        3. أدخل اسم المستخدم وكلمة المرور
        4. استمتع بالإنترنت!
        
        ملاحظة: هذا الكرت صالح لمدة محددة وحصة بيانات محددة.
        """
        
        info_para = Paragraph(info_text, self.card_content_style)
        story.append(info_para)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def create_multiple_cards_pdf(self, cards: List[HotspotCard], cards_per_page: int = 4) -> bytes:
        """إنشاء PDF لعدة كروت"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm,
                               topMargin=15*mm, bottomMargin=15*mm)
        
        story = []
        
        # عنوان الصفحة
        title = Paragraph(f"كروت الهوتسبوت - {len(cards)} كرت", self.card_title_style)
        story.append(title)
        story.append(Spacer(1, 5*mm))
        
        # تاريخ الإنشاء
        date_text = f"تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        date_para = Paragraph(date_text, self.card_content_style)
        story.append(date_para)
        story.append(Spacer(1, 10*mm))
        
        # إنشاء جدول للكروت
        for i in range(0, len(cards), cards_per_page):
            page_cards = cards[i:i + cards_per_page]
            
            # إنشاء بيانات الجدول للصفحة الحالية
            table_data = []
            headers = ["#", "اسم المستخدم", "كلمة المرور", "البروفايل", "حصة البيانات", "حصة الوقت"]
            table_data.append(headers)
            
            for j, card in enumerate(page_cards, i + 1):
                row = [
                    str(j),
                    card.username,
                    card.password,
                    card.profile,
                    card.data_quota,
                    card.time_quota
                ]
                table_data.append(row)
            
            # إنشاء الجدول
            table = Table(table_data, colWidths=[10*mm, 30*mm, 25*mm, 25*mm, 25*mm, 25*mm])
            table.setStyle(TableStyle([
                # تنسيق الرأس
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                
                # تنسيق البيانات
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                
                # تنسيق عام
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                
                # تلوين الصفوف بالتناوب
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            story.append(table)
            
            # إضافة فاصل بين الصفحات
            if i + cards_per_page < len(cards):
                story.append(Spacer(1, 15*mm))
        
        # معلومات إضافية في نهاية المستند
        footer_text = f"""
        إجمالي الكروت: {len(cards)}
        تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        تعليمات الاستخدام:
        • كل كرت صالح للاستخدام لمرة واحدة فقط
        • يجب استخدام الكرت خلال فترة الصلاحية المحددة
        • حصة البيانات والوقت محددة لكل كرت
        """
        
        story.append(Spacer(1, 10*mm))
        footer_para = Paragraph(footer_text, self.card_content_style)
        story.append(footer_para)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def create_card_summary_text(self, cards: List[HotspotCard]) -> str:
        """إنشاء ملخص نصي للكروت"""
        if not cards:
            return "لا توجد كروت لعرضها"
        
        summary = f"📋 ملخص الكروت المولدة ({len(cards)} كرت)\n"
        summary += f"📅 تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for i, card in enumerate(cards[:10], 1):  # عرض أول 10 كروت فقط
            summary += f"{i}. 👤 {card.username} | 🔑 {card.password}\n"
            summary += f"   📊 {card.data_quota} | ⏰ {card.time_quota}\n\n"
        
        if len(cards) > 10:
            summary += f"... و {len(cards) - 10} كرت إضافي\n\n"
        
        summary += "💡 تم إنشاء ملف PDF يحتوي على جميع الكروت"
        
        return summary
    
    def convert_cards_to_hotspot_users(self, cards: List[HotspotCard]) -> List[HotspotUser]:
        """تحويل الكروت إلى مستخدمي هوتسبوت"""
        users = []
        
        for card in cards:
            # تحويل حصة البيانات إلى تنسيق الميكروتك
            data_limit = ""
            if "MB" in card.data_quota and card.data_quota != "غير محدود":
                mb_value = int(card.data_quota.split()[0])
                data_limit = f"{mb_value}M"
            elif "GB" in card.data_quota:
                gb_value = float(card.data_quota.split()[0])
                data_limit = f"{int(gb_value * 1024)}M"
            
            # تحويل حصة الوقت إلى تنسيق الميكروتك
            time_limit = ""
            if "ساعة" in card.time_quota and card.time_quota != "غير محدود":
                if "يوم" in card.time_quota:
                    # تحليل "X يوم و Y ساعة"
                    parts = card.time_quota.split()
                    days = int(parts[0])
                    hours = int(parts[3]) if len(parts) > 3 else 0
                    total_hours = days * 24 + hours
                else:
                    # تحليل "X ساعة"
                    total_hours = int(card.time_quota.split()[0])
                
                time_limit = f"{total_hours}h"
            elif "يوم" in card.time_quota and "ساعة" not in card.time_quota:
                days = int(card.time_quota.split()[0])
                time_limit = f"{days * 24}h"
            
            user = HotspotUser(
                name=card.username,
                password=card.password,
                profile=card.profile,
                limit_bytes_total=data_limit,
                limit_uptime=time_limit,
                comment=f"Generated on {card.created_at.strftime('%Y-%m-%d')}"
            )
            
            users.append(user)
        
        return users

