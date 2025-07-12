"""
عميل API للتفاعل مع أجهزة MikroTik RouterOS
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

try:
    import routeros_api
except ImportError:
    print("يرجى تثبيت مكتبة RouterOS-api: pip install RouterOS-api")
    raise

from models import (
    MikroTikDevice, SystemInfo, NetworkInterface, HotspotUser,
    NetworkDevice, PingResult, TracerouteResult, DiagnosticResult, SystemHealth
)

logger = logging.getLogger(__name__)

class MikroTikAPIClient:
    """عميل API للتفاعل مع الميكروتك"""
    
    def __init__(self, device: MikroTikDevice):
        self.device = device
        self.connection = None
        self.api = None
        
    def connect(self) -> bool:
        """الاتصال بجهاز الميكروتك"""
        try:
            self.connection = routeros_api.RouterOsApiPool(
                host=self.device.ip,
                username=self.device.username,
                password=self.device.password,
                port=self.device.port,
                use_ssl=self.device.use_ssl,
                ssl_verify=False,
                ssl_verify_hostname=False
            )
            self.api = self.connection.get_api()
            
            # اختبار الاتصال
            self.api.get_resource('/system/identity').get()
            logger.info(f"تم الاتصال بنجاح بـ {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"فشل في الاتصال بـ {self.device}: {e}")
            return False
    
    def disconnect(self):
        """قطع الاتصال"""
        if self.connection:
            self.connection.disconnect()
            self.connection = None
            self.api = None
    
    def is_connected(self) -> bool:
        """فحص حالة الاتصال"""
        return self.api is not None
    
    def get_system_info(self) -> Optional[SystemInfo]:
        """الحصول على معلومات النظام"""
        if not self.is_connected():
            return None
        
        try:
            # معلومات الموارد
            resource = self.api.get_resource('/system/resource').get()[0]
            
            # معلومات الهوية
            identity = self.api.get_resource('/system/identity').get()[0]
            
            # معلومات الإصدار
            version_info = self.api.get_resource('/system/routerboard').get()[0]
            
            # تحويل البيانات
            cpu_load = float(resource.get('cpu-load', '0').replace('%', ''))
            voltage = float(resource.get('voltage', '0').replace('V', ''))
            temperature = int(resource.get('cpu-temperature', '0').replace('C', ''))
            
            # تحويل الذاكرة من bytes إلى MB
            total_memory = int(resource.get('total-memory', '0'))
            free_memory = int(resource.get('free-memory', '0'))
            
            return SystemInfo(
                cpu_load=cpu_load,
                voltage=voltage,
                temperature=temperature,
                uptime=resource.get('uptime', ''),
                memory_usage=((total_memory - free_memory) / total_memory * 100) if total_memory > 0 else 0,
                memory_total=total_memory,
                memory_free=free_memory,
                board_name=resource.get('board-name', ''),
                version=resource.get('version', ''),
                architecture=resource.get('architecture-name', ''),
                build_time=resource.get('build-time', '')
            )
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات النظام: {e}")
            return None
    
    def get_interfaces(self) -> List[NetworkInterface]:
        """الحصول على قائمة الواجهات"""
        if not self.is_connected():
            return []
        
        try:
            interfaces = self.api.get_resource('/interface').get()
            result = []
            
            for iface in interfaces:
                # الحصول على إحصائيات الواجهة
                try:
                    stats = self.api.get_resource('/interface').call('monitor-traffic', {
                        'interface': iface['name'],
                        'duration': '1'
                    })[0]
                except:
                    stats = {}
                
                result.append(NetworkInterface(
                    name=iface.get('name', ''),
                    type=iface.get('type', ''),
                    running=iface.get('running') == 'true',
                    disabled=iface.get('disabled') == 'true',
                    rx_bytes=int(stats.get('rx-bytes', 0)),
                    tx_bytes=int(stats.get('tx-bytes', 0)),
                    rx_packets=int(stats.get('rx-packets', 0)),
                    tx_packets=int(stats.get('tx-packets', 0)),
                    rx_errors=int(stats.get('rx-errors', 0)),
                    tx_errors=int(stats.get('tx-errors', 0))
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على الواجهات: {e}")
            return []
    
    def get_hotspot_active_users(self) -> List[HotspotUser]:
        """الحصول على المستخدمين النشطين في الهوتسبوت"""
        if not self.is_connected():
            return []
        
        try:
            active_users = self.api.get_resource('/ip/hotspot/active').get()
            result = []
            
            for user in active_users:
                result.append(HotspotUser(
                    name=user.get('user', ''),
                    password='',  # لا يتم عرض كلمة المرور في الجلسات النشطة
                    profile=user.get('server', ''),
                    ip_address=user.get('address', ''),
                    mac_address=user.get('mac-address', ''),
                    uptime=user.get('uptime', ''),
                    bytes_in=int(user.get('bytes-in', 0)),
                    bytes_out=int(user.get('bytes-out', 0)),
                    packets_in=int(user.get('packets-in', 0)),
                    packets_out=int(user.get('packets-out', 0))
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على المستخدمين النشطين: {e}")
            return []
    
    def get_hotspot_users(self) -> List[HotspotUser]:
        """الحصول على جميع مستخدمي الهوتسبوت"""
        if not self.is_connected():
            return []
        
        try:
            users = self.api.get_resource('/ip/hotspot/user').get()
            result = []
            
            for user in users:
                result.append(HotspotUser(
                    name=user.get('name', ''),
                    password=user.get('password', ''),
                    profile=user.get('profile', 'default'),
                    server=user.get('server', 'all'),
                    disabled=user.get('disabled') == 'true',
                    comment=user.get('comment', ''),
                    limit_uptime=user.get('limit-uptime', ''),
                    limit_bytes_in=user.get('limit-bytes-in', ''),
                    limit_bytes_out=user.get('limit-bytes-out', ''),
                    limit_bytes_total=user.get('limit-bytes-total', '')
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على مستخدمي الهوتسبوت: {e}")
            return []
    
    def add_hotspot_user(self, user: HotspotUser) -> bool:
        """إضافة مستخدم هوتسبوت جديد"""
        if not self.is_connected():
            return False
        
        try:
            user_data = {
                'name': user.name,
                'password': user.password,
                'profile': user.profile,
                'server': user.server,
                'disabled': 'yes' if user.disabled else 'no',
                'comment': user.comment
            }
            
            # إضافة القيود إذا كانت محددة
            if user.limit_uptime:
                user_data['limit-uptime'] = user.limit_uptime
            if user.limit_bytes_in:
                user_data['limit-bytes-in'] = user.limit_bytes_in
            if user.limit_bytes_out:
                user_data['limit-bytes-out'] = user.limit_bytes_out
            if user.limit_bytes_total:
                user_data['limit-bytes-total'] = user.limit_bytes_total
            
            self.api.get_resource('/ip/hotspot/user').add(**user_data)
            logger.info(f"تم إضافة المستخدم {user.name} بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المستخدم {user.name}: {e}")
            return False
    
    def remove_hotspot_user(self, username: str) -> bool:
        """حذف مستخدم هوتسبوت"""
        if not self.is_connected():
            return False
        
        try:
            users = self.api.get_resource('/ip/hotspot/user').get(name=username)
            if users:
                user_id = users[0]['id']
                self.api.get_resource('/ip/hotspot/user').remove(user_id)
                logger.info(f"تم حذف المستخدم {username} بنجاح")
                return True
            else:
                logger.warning(f"المستخدم {username} غير موجود")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في حذف المستخدم {username}: {e}")
            return False
    
    def ping(self, target: str, count: int = 4) -> Optional[PingResult]:
        """تنفيذ اختبار Ping"""
        if not self.is_connected():
            return None
        
        try:
            result = self.api.get_resource('/ping').call('ping', {
                'address': target,
                'count': str(count)
            })
            
            # تحليل النتائج
            packets_sent = count
            packets_received = len([r for r in result if 'time' in r])
            packet_loss = ((packets_sent - packets_received) / packets_sent) * 100
            
            times = [float(r['time'].replace('ms', '')) for r in result if 'time' in r]
            
            if times:
                min_time = min(times)
                max_time = max(times)
                avg_time = sum(times) / len(times)
            else:
                min_time = max_time = avg_time = 0
            
            # تنسيق المخرجات
            output_lines = [f"PING {target}:"]
            for i, r in enumerate(result):
                if 'time' in r:
                    output_lines.append(f"Reply from {target}: time={r['time']}")
                else:
                    output_lines.append(f"Request timeout for icmp_seq {i+1}")
            
            output_lines.append(f"\n--- {target} ping statistics ---")
            output_lines.append(f"{packets_sent} packets transmitted, {packets_received} received, {packet_loss:.1f}% packet loss")
            if times:
                output_lines.append(f"round-trip min/avg/max = {min_time:.1f}/{avg_time:.1f}/{max_time:.1f} ms")
            
            return PingResult(
                target=target,
                packets_sent=packets_sent,
                packets_received=packets_received,
                packet_loss=packet_loss,
                min_time=min_time,
                max_time=max_time,
                avg_time=avg_time,
                output='\n'.join(output_lines)
            )
            
        except Exception as e:
            logger.error(f"خطأ في اختبار Ping لـ {target}: {e}")
            return None
    
    def traceroute(self, target: str, max_hops: int = 30) -> Optional[TracerouteResult]:
        """تنفيذ تتبع المسار"""
        if not self.is_connected():
            return None
        
        try:
            # تنفيذ traceroute (قد يختلف حسب إصدار RouterOS)
            result = self.api.get_resource('/tool/traceroute').call('traceroute', {
                'address': target,
                'count': '1'
            })
            
            hops = []
            output_lines = [f"traceroute to {target}, {max_hops} hops max"]
            
            for i, hop in enumerate(result):
                hop_info = {
                    'hop': i + 1,
                    'address': hop.get('address', '*'),
                    'time': hop.get('time', 'timeout')
                }
                hops.append(hop_info)
                
                if hop_info['address'] != '*':
                    output_lines.append(f"{hop_info['hop']:2d}  {hop_info['address']}  {hop_info['time']}")
                else:
                    output_lines.append(f"{hop_info['hop']:2d}  * * *")
            
            return TracerouteResult(
                target=target,
                hops=hops,
                output='\n'.join(output_lines)
            )
            
        except Exception as e:
            logger.error(f"خطأ في تتبع المسار لـ {target}: {e}")
            return None
    
    def discover_devices(self, network: str = "192.168.88.0/24") -> List[NetworkDevice]:
        """اكتشاف الأجهزة في الشبكة"""
        if not self.is_connected():
            return []
        
        try:
            # استخدام neighbor discovery إذا كان متاحاً
            neighbors = self.api.get_resource('/ip/neighbor').get()
            devices = []
            
            for neighbor in neighbors:
                device = NetworkDevice(
                    ip_address=neighbor.get('address', ''),
                    mac_address=neighbor.get('mac-address', ''),
                    hostname=neighbor.get('identity', ''),
                    vendor=neighbor.get('platform', ''),
                    is_reachable=True
                )
                devices.append(device)
            
            return devices
            
        except Exception as e:
            logger.error(f"خطأ في اكتشاف الأجهزة: {e}")
            return []
    
    def reboot_system(self) -> bool:
        """إعادة تشغيل النظام"""
        if not self.is_connected():
            return False
        
        try:
            self.api.get_resource('/system').call('reboot')
            logger.info("تم إرسال أمر إعادة التشغيل")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إعادة التشغيل: {e}")
            return False
    
    def get_system_health(self) -> Optional[SystemHealth]:
        """فحص صحة النظام"""
        if not self.is_connected():
            return None
        
        try:
            system_info = self.get_system_info()
            interfaces = self.get_interfaces()
            
            if not system_info:
                return None
            
            # فحص المعالج
            if system_info.cpu_load >= 80:
                cpu_status = DiagnosticResult("CPU", "error", f"استخدام عالي للمعالج: {system_info.cpu_load}%")
            elif system_info.cpu_load >= 60:
                cpu_status = DiagnosticResult("CPU", "warning", f"استخدام متوسط للمعالج: {system_info.cpu_load}%")
            else:
                cpu_status = DiagnosticResult("CPU", "success", f"استخدام طبيعي للمعالج: {system_info.cpu_load}%")
            
            # فحص الذاكرة
            memory_percent = system_info.memory_usage_percent
            if memory_percent >= 85:
                memory_status = DiagnosticResult("Memory", "error", f"استخدام عالي للذاكرة: {memory_percent}%")
            elif memory_percent >= 70:
                memory_status = DiagnosticResult("Memory", "warning", f"استخدام متوسط للذاكرة: {memory_percent}%")
            else:
                memory_status = DiagnosticResult("Memory", "success", f"استخدام طبيعي للذاكرة: {memory_percent}%")
            
            # فحص الواجهات
            running_interfaces = len([i for i in interfaces if i.running and not i.disabled])
            total_interfaces = len(interfaces)
            
            if running_interfaces < total_interfaces * 0.5:
                interface_status = DiagnosticResult("Interfaces", "error", f"عدد قليل من الواجهات نشطة: {running_interfaces}/{total_interfaces}")
            elif running_interfaces < total_interfaces * 0.8:
                interface_status = DiagnosticResult("Interfaces", "warning", f"بعض الواجهات غير نشطة: {running_interfaces}/{total_interfaces}")
            else:
                interface_status = DiagnosticResult("Interfaces", "success", f"جميع الواجهات تعمل بشكل طبيعي: {running_interfaces}/{total_interfaces}")
            
            # تحديد الحالة العامة
            statuses = [cpu_status.status, memory_status.status, interface_status.status]
            if "error" in statuses:
                overall_status = "error"
            elif "warning" in statuses:
                overall_status = "warning"
            else:
                overall_status = "success"
            
            # التوصيات
            recommendations = []
            if cpu_status.status != "success":
                recommendations.append("مراجعة العمليات النشطة وتحديث RouterOS")
            if memory_status.status != "success":
                recommendations.append("مسح سجلات النظام وإعادة تشغيل الخدمات")
            if interface_status.status != "success":
                recommendations.append("فحص الكابلات وإعدادات الواجهات")
            
            return SystemHealth(
                cpu_status=cpu_status,
                memory_status=memory_status,
                interface_status=interface_status,
                overall_status=overall_status,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"خطأ في فحص صحة النظام: {e}")
            return None

