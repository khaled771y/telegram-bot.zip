# دليل التثبيت والإعداد المفصل 📋

دليل شامل لتثبيت وإعداد بوت تليجرام لإدارة الميكروتك.

## 📋 المتطلبات الأساسية

### متطلبات النظام
- **نظام التشغيل**: Linux (Ubuntu 18.04+), Windows 10+, macOS 10.14+
- **Python**: الإصدار 3.8 أو أحدث
- **الذاكرة**: 512 MB RAM كحد أدنى
- **التخزين**: 100 MB مساحة فارغة
- **الشبكة**: اتصال إنترنت مستقر

### متطلبات الميكروتك
- **RouterOS**: الإصدار 6.0 أو أحدث
- **API**: يجب تفعيل خدمة API
- **المستخدم**: حساب مستخدم بصلاحيات كاملة أو محددة
- **الشبكة**: إمكانية الوصول للراوتر عبر الشبكة

## 🔧 التثبيت خطوة بخطوة

### الخطوة 1: تحضير البيئة

#### على Ubuntu/Debian
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python و pip
sudo apt install python3 python3-pip python3-venv -y

# تثبيت أدوات إضافية
sudo apt install git curl wget unzip -y
```

#### على CentOS/RHEL
```bash
# تحديث النظام
sudo yum update -y

# تثبيت Python و pip
sudo yum install python3 python3-pip -y

# تثبيت أدوات إضافية
sudo yum install git curl wget unzip -y
```

#### على Windows
1. حمّل Python من [python.org](https://python.org)
2. تأكد من تحديد "Add Python to PATH" أثناء التثبيت
3. افتح Command Prompt كمشرف
4. تحقق من التثبيت:
   ```cmd
   python --version
   pip --version
   ```

#### على macOS
```bash
# تثبيت Homebrew (إذا لم يكن مثبتاً)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# تثبيت Python
brew install python3

# تحقق من التثبيت
python3 --version
pip3 --version
```

### الخطوة 2: تحميل وإعداد المشروع

```bash
# إنشاء مجلد للمشروع
mkdir ~/mikrotik-telegram-bot
cd ~/mikrotik-telegram-bot

# استخراج الملف المضغوط (إذا كان متوفراً)
unzip MikroTikTelegramBot.zip
cd MikroTikTelegramBot

# أو نسخ الملفات يدوياً إذا كانت منفصلة
```

### الخطوة 3: إنشاء البيئة الافتراضية

```bash
# إنشاء البيئة الافتراضية
python3 -m venv venv

# تفعيل البيئة الافتراضية
# على Linux/macOS:
source venv/bin/activate

# على Windows:
venv\Scripts\activate

# يجب أن ترى (venv) في بداية سطر الأوامر
```

### الخطوة 4: تثبيت المتطلبات

```bash
# تحديث pip
pip install --upgrade pip

# تثبيت المكتبات المطلوبة
pip install -r requirements.txt

# التحقق من التثبيت
pip list
```

إذا واجهت مشاكل في التثبيت، جرب:
```bash
# تثبيت المكتبات واحدة تلو الأخرى
pip install python-telegram-bot==22.2
pip install RouterOS-api==0.21.0
pip install reportlab==4.4.2
pip install fpdf2==2.8.3
pip install cryptography==45.0.5
pip install pillow>=9.0.0
```

## 🤖 إعداد بوت تليجرام

### الخطوة 1: إنشاء البوت

1. **افتح تليجرام** وابحث عن `@BotFather`
2. **ابدأ محادثة** مع BotFather
3. **أرسل الأمر** `/newbot`
4. **اختر اسماً** للبوت (مثل: "مدير الميكروتك الخاص بي")
5. **اختر اسم مستخدم** للبوت (يجب أن ينتهي بـ `bot`)
6. **احفظ التوكن** الذي ستحصل عليه

### الخطوة 2: تخصيص البوت (اختياري)

```bash
# إعداد وصف البوت
/setdescription
# ثم أرسل: "بوت لإدارة أجهزة الميكروتك عن بُعد"

# إعداد أوامر البوت
/setcommands
# ثم أرسل:
start - بدء التفاعل مع البوت
login - تسجيل الدخول للميكروتك
help - عرض المساعدة

# إعداد صورة للبوت
/setuserpic
# ثم أرسل صورة مناسبة
```

## ⚙️ تكوين البوت

### الخطوة 1: إعداد ملف التكوين

```bash
# انسخ ملف التكوين النموذجي
cp config.py.example config.py

# أو أنشئ الملف يدوياً
nano config.py
```

### الخطوة 2: تعديل الإعدادات

أضف المحتوى التالي إلى `config.py`:

```python
"""
إعدادات بوت تليجرام لإدارة الميكروتك
"""

import os
from cryptography.fernet import Fernet

# توكن البوت من BotFather
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع التوكن هنا

# مفتاح التشفير (سيتم إنشاؤه تلقائياً إذا لم يكن موجوداً)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())

# معرفات المشرفين (اختياري)
ADMIN_USER_IDS = [
    123456789,  # ضع معرف تليجرام الخاص بك هنا
    # يمكن إضافة المزيد من المعرفات
]

# إعدادات قاعدة البيانات
DATABASE_PATH = "mikrotik_bot.db"

# إعدادات السجلات
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

# إعدادات الميكروتك الافتراضية
DEFAULT_MIKROTIK_PORT = 8728
DEFAULT_MIKROTIK_TIMEOUT = 10

# إعدادات الكروت
MAX_CARDS_PER_GENERATION = 100
DEFAULT_CARD_VALIDITY_DAYS = 30

# إعدادات الأمان
MAX_LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT_HOURS = 24
```

### الخطوة 3: الحصول على معرف تليجرام الخاص بك

1. ابحث عن `@userinfobot` في تليجرام
2. أرسل `/start`
3. احفظ الرقم الذي يظهر كـ "Id"
4. أضفه إلى `ADMIN_USER_IDS` في ملف التكوين

## 🔧 إعداد الميكروتك

### تفعيل API

#### عبر Winbox
1. افتح Winbox واتصل بالراوتر
2. اذهب إلى `IP` → `Services`
3. ابحث عن `api` في القائمة
4. انقر نقراً مزدوجاً عليه
5. تأكد من أن `Enabled` محدد
6. يمكن تغيير المنفذ إذا أردت (افتراضي: 8728)

#### عبر Terminal
```bash
# الاتصال بالراوتر عبر SSH أو Terminal
ssh admin@192.168.1.1

# تفعيل API
/ip service enable api

# تعيين منفذ مخصص (اختياري)
/ip service set api port=8728

# التحقق من الحالة
/ip service print where name=api
```

### إنشاء مستخدم للـ API (اختياري)

```bash
# إنشاء مجموعة مخصصة للـ API
/user group add name=api-users policy=api,read,write,policy,test,password,sensitive,romon

# إنشاء مستخدم للـ API
/user add name=apiuser password=strong_password group=api-users

# أو استخدام مستخدم موجود مع صلاحيات كاملة
/user add name=botuser password=bot_password group=full
```

### إعدادات الجدار الناري

إذا كان لديك جدار ناري مفعل:

```bash
# السماح بالوصول لـ API من شبكة محددة
/ip firewall filter add chain=input protocol=tcp dst-port=8728 src-address=192.168.1.0/24 action=accept

# أو السماح من عنوان IP محدد
/ip firewall filter add chain=input protocol=tcp dst-port=8728 src-address=192.168.1.100 action=accept
```

## 🚀 تشغيل البوت

### التشغيل العادي

```bash
# تأكد من تفعيل البيئة الافتراضية
source venv/bin/activate

# تشغيل البوت
python main.py
```

### التشغيل في الخلفية (Linux/macOS)

```bash
# استخدام nohup
nohup python main.py > bot.log 2>&1 &

# أو استخدام screen
screen -S mikrotik-bot
python main.py
# اضغط Ctrl+A ثم D للخروج من screen

# للعودة إلى screen
screen -r mikrotik-bot
```

### التشغيل كخدمة (Linux)

إنشاء ملف خدمة systemd:

```bash
sudo nano /etc/systemd/system/mikrotik-bot.service
```

أضف المحتوى التالي:

```ini
[Unit]
Description=MikroTik Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mikrotik-telegram-bot/MikroTikTelegramBot
Environment=PATH=/home/ubuntu/mikrotik-telegram-bot/MikroTikTelegramBot/venv/bin
ExecStart=/home/ubuntu/mikrotik-telegram-bot/MikroTikTelegramBot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

تفعيل وتشغيل الخدمة:

```bash
# إعادة تحميل systemd
sudo systemctl daemon-reload

# تفعيل الخدمة
sudo systemctl enable mikrotik-bot

# تشغيل الخدمة
sudo systemctl start mikrotik-bot

# فحص الحالة
sudo systemctl status mikrotik-bot

# عرض السجلات
sudo journalctl -u mikrotik-bot -f
```

## ✅ اختبار التثبيت

### اختبار البوت

1. **ابحث عن البوت** في تليجرام باستخدام اسم المستخدم
2. **أرسل** `/start`
3. **يجب أن يرد البوت** برسالة ترحيب

### اختبار الاتصال بالميكروتك

1. **أرسل** `/login`
2. **أدخل معلومات الاتصال**:
   ```
   192.168.1.1:8728:admin:password:My Router
   ```
3. **يجب أن يتم الاتصال بنجاح**

### اختبار الميزات

1. **معلومات النظام**: يجب عرض معلومات الراوتر
2. **الهوتسبوت**: يجب عرض المستخدمين النشطين
3. **توليد الكروت**: يجب إنشاء كروت جديدة
4. **أدوات التشخيص**: يجب عمل ping بنجاح

## 🔧 استكشاف الأخطاء

### مشاكل شائعة وحلولها

#### البوت لا يستجيب
```bash
# فحص السجلات
tail -f bot.log

# فحص العمليات
ps aux | grep python

# إعادة تشغيل البوت
pkill -f main.py
python main.py
```

#### خطأ في التوكن
```
telegram.error.InvalidToken: Invalid token
```
**الحل**: تأكد من صحة التوكن في `config.py`

#### فشل الاتصال بالميكروتك
```
فشل في الاتصال بـ 192.168.1.1:8728
```
**الحلول**:
- تحقق من عنوان IP
- تأكد من تفعيل API
- فحص الجدار الناري
- تحقق من اسم المستخدم وكلمة المرور

#### مشاكل في المكتبات
```bash
# إعادة تثبيت المكتبات
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# أو تحديث pip
pip install --upgrade pip setuptools wheel
```

### فحص الاتصال بالميكروتك

```bash
# اختبار ping
ping 192.168.1.1

# اختبار المنفذ
telnet 192.168.1.1 8728

# أو استخدام nmap
nmap -p 8728 192.168.1.1
```

## 🔄 الصيانة والتحديث

### النسخ الاحتياطي

```bash
# نسخ احتياطي لقاعدة البيانات
cp mikrotik_bot.db backup/mikrotik_bot_$(date +%Y%m%d_%H%M%S).db

# نسخ احتياطي للإعدادات
cp config.py backup/config_$(date +%Y%m%d_%H%M%S).py
```

### تحديث المكتبات

```bash
# تحديث جميع المكتبات
pip install --upgrade -r requirements.txt

# أو تحديث مكتبة محددة
pip install --upgrade python-telegram-bot
```

### مراقبة الأداء

```bash
# مراقبة استخدام الموارد
htop

# مراقبة مساحة القرص
df -h

# مراقبة حجم قاعدة البيانات
ls -lh mikrotik_bot.db

# عرض السجلات
tail -f bot.log
```

## 🔒 الأمان

### تأمين الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت جدار ناري
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow from 192.168.1.0/24 to any port 8728

# تغيير كلمة مرور المستخدم
passwd
```

### تأمين البوت

1. **استخدم كلمات مرور قوية** للميكروتك
2. **قم بتشفير قاعدة البيانات** إذا أمكن
3. **راقب السجلات** بانتظام
4. **حدد المستخدمين المصرح لهم** في `ADMIN_USER_IDS`

## 📞 الدعم

إذا واجهت مشاكل:

1. **راجع السجلات**: `tail -f bot.log`
2. **تحقق من الإعدادات**: `config.py`
3. **اختبر الاتصال**: ping و telnet
4. **راجع وثائق الميكروتك**: [help.mikrotik.com](https://help.mikrotik.com)

---

**تم إعداد البوت بنجاح! 🎉**

