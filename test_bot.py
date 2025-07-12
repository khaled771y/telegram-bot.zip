"""
اختبار وظائف البوت الأساسية
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# إضافة مجلد المشروع إلى المسار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from models import MikroTikDevice, HotspotUser, HotspotCard
from card_generator import HotspotCardGenerator
from mikrotik_api_client import MikroTikAPIClient

class TestDatabaseManager(unittest.TestCase):
    """اختبار مدير قاعدة البيانات"""
    
    def setUp(self):
        """إعداد الاختبار"""
        self.db = DatabaseManager(":memory:")  # استخدام قاعدة بيانات في الذاكرة للاختبار
        self.db.init_database()  # تهيئة الجداول
    
    def test_add_user(self):
        """اختبار إضافة مستخدم"""
        result = self.db.add_user(12345, "testuser", "Test", "User")
        self.assertTrue(result)
        
        user = self.db.get_user(12345)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
    
    def test_user_authorization(self):
        """اختبار تفويض المستخدم"""
        self.db.add_user(12345, "testuser")
        
        # المستخدم غير مفوض في البداية
        self.assertFalse(self.db.is_user_authorized(12345))
        
        # تفويض المستخدم
        self.db.authorize_user(12345)
        self.assertTrue(self.db.is_user_authorized(12345))
    
    def test_mikrotik_device_operations(self):
        """اختبار عمليات جهاز الميكروتك"""
        self.db.add_user(12345, "testuser")
        
        device = MikroTikDevice("192.168.1.1", 8728, "admin", "password")
        device_id = self.db.add_mikrotik_device(12345, device, "Test Router")
        
        self.assertIsNotNone(device_id)
        
        # استرجاع الجهاز
        retrieved_device = self.db.get_mikrotik_device(device_id)
        self.assertIsNotNone(retrieved_device)
        self.assertEqual(retrieved_device.ip, "192.168.1.1")
        self.assertEqual(retrieved_device.username, "admin")
        self.assertEqual(retrieved_device.password, "password")

class TestHotspotCardGenerator(unittest.TestCase):
    """اختبار مولد كروت الهوتسبوت"""
    
    def setUp(self):
        """إعداد الاختبار"""
        self.generator = HotspotCardGenerator()
    
    def test_generate_username(self):
        """اختبار توليد اسم المستخدم"""
        username = self.generator.generate_username("test", 6)
        self.assertTrue(username.startswith("test"))
        self.assertEqual(len(username), 10)  # test + 6 digits
    
    def test_generate_password(self):
        """اختبار توليد كلمة المرور"""
        password = self.generator.generate_password(8)
        self.assertEqual(len(password), 8)
        self.assertTrue(password.isalnum())
    
    def test_format_data_quota(self):
        """اختبار تنسيق حصة البيانات"""
        self.assertEqual(self.generator.format_data_quota(0), "غير محدود")
        self.assertEqual(self.generator.format_data_quota(512), "512 MB")
        self.assertEqual(self.generator.format_data_quota(1024), "1.0 GB")
        self.assertEqual(self.generator.format_data_quota(2048), "2.0 GB")
    
    def test_format_time_quota(self):
        """اختبار تنسيق حصة الوقت"""
        self.assertEqual(self.generator.format_time_quota(0), "غير محدود")
        self.assertEqual(self.generator.format_time_quota(12), "12 ساعة")
        self.assertEqual(self.generator.format_time_quota(24), "1 يوم")
        self.assertEqual(self.generator.format_time_quota(36), "1 يوم و 12 ساعة")
    
    def test_generate_cards(self):
        """اختبار توليد الكروت"""
        cards = self.generator.generate_cards(5, "user", "default", 1024, 24, 30)
        
        self.assertEqual(len(cards), 5)
        
        for card in cards:
            self.assertIsInstance(card, HotspotCard)
            self.assertTrue(card.username.startswith("user"))
            self.assertEqual(len(card.password), 8)
            self.assertEqual(card.profile, "default")
            self.assertEqual(card.data_quota, "1.0 GB")
            self.assertEqual(card.time_quota, "1 يوم")
            self.assertEqual(card.validity_days, 30)
    
    def test_create_single_card_pdf(self):
        """اختبار إنشاء PDF لكرت واحد"""
        card = HotspotCard("testuser", "testpass", "default", "1.0 GB", "1 يوم", 30)
        pdf_data = self.generator.create_single_card_pdf(card)
        
        self.assertIsInstance(pdf_data, bytes)
        self.assertTrue(len(pdf_data) > 0)
        # التحقق من أن البيانات تبدأ بـ PDF header
        self.assertTrue(pdf_data.startswith(b'%PDF'))
    
    def test_convert_cards_to_hotspot_users(self):
        """اختبار تحويل الكروت إلى مستخدمي هوتسبوت"""
        cards = self.generator.generate_cards(3, "user", "default", 1024, 24, 30)
        users = self.generator.convert_cards_to_hotspot_users(cards)
        
        self.assertEqual(len(users), 3)
        
        for i, user in enumerate(users):
            self.assertIsInstance(user, HotspotUser)
            self.assertEqual(user.name, cards[i].username)
            self.assertEqual(user.password, cards[i].password)
            self.assertEqual(user.profile, cards[i].profile)
            self.assertEqual(user.limit_bytes_total, "1024M")
            self.assertEqual(user.limit_uptime, "24h")

class TestMikroTikAPIClient(unittest.TestCase):
    """اختبار عميل API الميكروتك"""
    
    def setUp(self):
        """إعداد الاختبار"""
        self.device = MikroTikDevice("192.168.1.1", 8728, "admin", "password")
        self.client = MikroTikAPIClient(self.device)
    
    @patch('routeros_api.RouterOsApiPool')
    def test_connect_success(self, mock_pool):
        """اختبار الاتصال الناجح"""
        # إعداد المحاكي
        mock_api = Mock()
        mock_api.get_resource.return_value.get.return_value = [{'name': 'test'}]
        mock_pool.return_value.get_api.return_value = mock_api
        
        result = self.client.connect()
        self.assertTrue(result)
        self.assertTrue(self.client.is_connected())
    
    @patch('routeros_api.RouterOsApiPool')
    def test_connect_failure(self, mock_pool):
        """اختبار فشل الاتصال"""
        # إعداد المحاكي لرفع استثناء
        mock_pool.side_effect = Exception("Connection failed")
        
        result = self.client.connect()
        self.assertFalse(result)
        self.assertFalse(self.client.is_connected())

def run_basic_tests():
    """تشغيل الاختبارات الأساسية"""
    print("🧪 بدء تشغيل الاختبارات الأساسية...")
    
    # اختبار قاعدة البيانات
    print("\n📊 اختبار قاعدة البيانات...")
    try:
        db = DatabaseManager(":memory:")
        print("✅ تم إنشاء قاعدة البيانات بنجاح")
        
        # اختبار إضافة مستخدم
        result = db.add_user(12345, "testuser", "Test", "User")
        if result:
            print("✅ تم إضافة المستخدم بنجاح")
        else:
            print("❌ فشل في إضافة المستخدم")
        
        # اختبار استرجاع المستخدم
        user = db.get_user(12345)
        if user and user['username'] == "testuser":
            print("✅ تم استرجاع المستخدم بنجاح")
        else:
            print("❌ فشل في استرجاع المستخدم")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات: {e}")
    
    # اختبار مولد الكروت
    print("\n🎫 اختبار مولد كروت الهوتسبوت...")
    try:
        generator = HotspotCardGenerator()
        print("✅ تم إنشاء مولد الكروت بنجاح")
        
        # اختبار توليد الكروت
        cards = generator.generate_cards(3, "test", "default", 1024, 24, 30)
        if len(cards) == 3:
            print("✅ تم توليد الكروت بنجاح")
            
            # اختبار إنشاء PDF
            pdf_data = generator.create_multiple_cards_pdf(cards)
            if pdf_data and len(pdf_data) > 0:
                print("✅ تم إنشاء ملف PDF بنجاح")
            else:
                print("❌ فشل في إنشاء ملف PDF")
        else:
            print("❌ فشل في توليد الكروت")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار مولد الكروت: {e}")
    
    # اختبار عميل API
    print("\n🔌 اختبار عميل API الميكروتك...")
    try:
        device = MikroTikDevice("192.168.1.1", 8728, "admin", "password")
        client = MikroTikAPIClient(device)
        print("✅ تم إنشاء عميل API بنجاح")
        
        # ملاحظة: لا يمكن اختبار الاتصال الفعلي بدون جهاز ميكروتك
        print("ℹ️ اختبار الاتصال يتطلب جهاز ميكروتك فعلي")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار عميل API: {e}")
    
    print("\n🎉 انتهت الاختبارات الأساسية")

if __name__ == "__main__":
    # تشغيل الاختبارات الأساسية
    run_basic_tests()
    
    print("\n" + "="*50)
    print("🧪 تشغيل اختبارات unittest...")
    
    # تشغيل اختبارات unittest
    unittest.main(verbosity=2, exit=False)

