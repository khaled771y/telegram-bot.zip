"""
وحدة قاعدة البيانات لبوت تليجرام الميكروتك
"""

import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
import base64

from models import MikroTikDevice, UserSession

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_path: str = "mikrotik_bot.db", encryption_key: str = None):
        self.db_path = db_path
        self.encryption_key = encryption_key
        
        # إنشاء مفتاح التشفير إذا لم يكن موجوداً
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
        
        self.cipher = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        self.init_database()
    
    def init_database(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # جدول المستخدمين
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        telegram_user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_authorized BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # جدول أجهزة الميكروتك
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mikrotik_devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_user_id INTEGER,
                        device_name TEXT,
                        ip_address TEXT,
                        port INTEGER,
                        username TEXT,
                        password_encrypted TEXT,
                        use_ssl BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_user_id)
                    )
                ''')
                
                # جدول الجلسات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        telegram_user_id INTEGER PRIMARY KEY,
                        current_device_id INTEGER,
                        is_authenticated BOOLEAN DEFAULT FALSE,
                        session_data TEXT,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_user_id),
                        FOREIGN KEY (current_device_id) REFERENCES mikrotik_devices (id)
                    )
                ''')
                
                # جدول كروت الهوتسبوت المولدة
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS hotspot_cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_user_id INTEGER,
                        username TEXT,
                        password TEXT,
                        profile TEXT,
                        data_quota TEXT,
                        time_quota TEXT,
                        validity_days INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_user_id)
                    )
                ''')
                
                # جدول سجل العمليات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS operation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_user_id INTEGER,
                        operation_type TEXT,
                        operation_details TEXT,
                        success BOOLEAN,
                        error_message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_user_id)
                    )
                ''')
                
                conn.commit()
                logger.info("تم تهيئة قاعدة البيانات بنجاح")
                
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
            raise
    
    def encrypt_password(self, password: str) -> str:
        """تشفير كلمة المرور"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """فك تشفير كلمة المرور"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()
    
    def add_user(self, telegram_user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None) -> bool:
        """إضافة مستخدم جديد"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (telegram_user_id, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (telegram_user_id, username, first_name, last_name, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إضافة المستخدم {telegram_user_id}: {e}")
            return False
    
    def get_user(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات المستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE telegram_user_id = ?', (telegram_user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"خطأ في الحصول على المستخدم {telegram_user_id}: {e}")
            return None
    
    def authorize_user(self, telegram_user_id: int) -> bool:
        """تفويض المستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET is_authorized = TRUE 
                    WHERE telegram_user_id = ?
                ''', (telegram_user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تفويض المستخدم {telegram_user_id}: {e}")
            return False
    
    def is_user_authorized(self, telegram_user_id: int) -> bool:
        """فحص تفويض المستخدم"""
        user = self.get_user(telegram_user_id)
        return user and user.get('is_authorized', False)
    
    def add_mikrotik_device(self, telegram_user_id: int, device: MikroTikDevice, 
                           device_name: str = None) -> Optional[int]:
        """إضافة جهاز ميكروتك"""
        try:
            encrypted_password = self.encrypt_password(device.password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO mikrotik_devices 
                    (telegram_user_id, device_name, ip_address, port, username, 
                     password_encrypted, use_ssl)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (telegram_user_id, device_name or f"{device.ip}:{device.port}",
                      device.ip, device.port, device.username, encrypted_password, device.use_ssl))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطأ في إضافة جهاز الميكروتك: {e}")
            return None
    
    def get_mikrotik_device(self, device_id: int) -> Optional[MikroTikDevice]:
        """الحصول على جهاز ميكروتك"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM mikrotik_devices WHERE id = ?', (device_id,))
                row = cursor.fetchone()
                
                if row:
                    decrypted_password = self.decrypt_password(row['password_encrypted'])
                    return MikroTikDevice(
                        ip=row['ip_address'],
                        port=row['port'],
                        username=row['username'],
                        password=decrypted_password,
                        use_ssl=row['use_ssl']
                    )
                return None
        except Exception as e:
            logger.error(f"خطأ في الحصول على جهاز الميكروتك {device_id}: {e}")
            return None
    
    def get_user_devices(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        """الحصول على أجهزة المستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, device_name, ip_address, port, username, use_ssl, is_active
                    FROM mikrotik_devices 
                    WHERE telegram_user_id = ? AND is_active = TRUE
                    ORDER BY created_at DESC
                ''', (telegram_user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على أجهزة المستخدم {telegram_user_id}: {e}")
            return []
    
    def create_user_session(self, telegram_user_id: int, device_id: int = None) -> bool:
        """إنشاء جلسة مستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_sessions 
                    (telegram_user_id, current_device_id, is_authenticated, last_activity)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_user_id, device_id, device_id is not None, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إنشاء جلسة المستخدم {telegram_user_id}: {e}")
            return False
    
    def get_user_session(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على جلسة المستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM user_sessions WHERE telegram_user_id = ?', (telegram_user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"خطأ في الحصول على جلسة المستخدم {telegram_user_id}: {e}")
            return None
    
    def update_user_activity(self, telegram_user_id: int) -> bool:
        """تحديث نشاط المستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_activity = ? WHERE telegram_user_id = ?
                ''', (datetime.now(), telegram_user_id))
                cursor.execute('''
                    UPDATE user_sessions SET last_activity = ? WHERE telegram_user_id = ?
                ''', (datetime.now(), telegram_user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث نشاط المستخدم {telegram_user_id}: {e}")
            return False
    
    def save_hotspot_cards(self, telegram_user_id: int, cards: List[Dict[str, Any]]) -> bool:
        """حفظ كروت الهوتسبوت المولدة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for card in cards:
                    cursor.execute('''
                        INSERT INTO hotspot_cards 
                        (telegram_user_id, username, password, profile, data_quota, 
                         time_quota, validity_days)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (telegram_user_id, card['username'], card['password'], 
                          card['profile'], card['data_quota'], card['time_quota'], 
                          card['validity_days']))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في حفظ كروت الهوتسبوت: {e}")
            return False
    
    def get_user_hotspot_cards(self, telegram_user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """الحصول على كروت الهوتسبوت للمستخدم"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM hotspot_cards 
                    WHERE telegram_user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (telegram_user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على كروت الهوتسبوت: {e}")
            return []
    
    def log_operation(self, telegram_user_id: int, operation_type: str, 
                     operation_details: str, success: bool, error_message: str = None) -> bool:
        """تسجيل العملية في السجل"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO operation_logs 
                    (telegram_user_id, operation_type, operation_details, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (telegram_user_id, operation_type, operation_details, success, error_message))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تسجيل العملية: {e}")
            return False
    
    def get_operation_logs(self, telegram_user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """الحصول على سجل العمليات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM operation_logs 
                    WHERE telegram_user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (telegram_user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"خطأ في الحصول على سجل العمليات: {e}")
            return []
    
    def cleanup_old_sessions(self, days: int = 30) -> bool:
        """تنظيف الجلسات القديمة"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE last_activity < datetime('now', '-{} days')
                '''.format(days))
                cursor.execute('''
                    DELETE FROM operation_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days * 2))  # الاحتفاظ بالسجلات لفترة أطول
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تنظيف الجلسات القديمة: {e}")
            return False

