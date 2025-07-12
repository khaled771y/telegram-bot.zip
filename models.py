"""
نماذج البيانات لبوت تليجرام الميكروتك
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class MikroTikDevice:
    """نموذج جهاز الميكروتك"""
    ip: str
    port: int
    username: str
    password: str
    use_ssl: bool = False
    
    def __str__(self):
        return f"{self.ip}:{self.port}"

@dataclass
class SystemInfo:
    """معلومات النظام"""
    cpu_load: float
    voltage: float
    temperature: int
    uptime: str
    memory_usage: float
    memory_total: int
    memory_free: int
    board_name: str
    version: str
    architecture: str
    build_time: str
    
    @property
    def memory_usage_percent(self) -> int:
        if self.memory_total > 0:
            return int((self.memory_total - self.memory_free) / self.memory_total * 100)
        return 0

@dataclass
class NetworkInterface:
    """واجهة الشبكة"""
    name: str
    type: str
    running: bool
    disabled: bool
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int
    
    @property
    def rx_mb(self) -> float:
        return self.rx_bytes / (1024 * 1024)
    
    @property
    def tx_mb(self) -> float:
        return self.tx_bytes / (1024 * 1024)

@dataclass
class HotspotUser:
    """مستخدم الهوتسبوت"""
    name: str
    password: str
    profile: str = "default"
    server: str = "all"
    disabled: bool = False
    comment: str = ""
    limit_uptime: str = ""
    limit_bytes_in: str = ""
    limit_bytes_out: str = ""
    limit_bytes_total: str = ""
    
    # معلومات الجلسة النشطة (إذا كان متصلاً)
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    uptime: Optional[str] = None
    bytes_in: Optional[int] = None
    bytes_out: Optional[int] = None
    packets_in: Optional[int] = None
    packets_out: Optional[int] = None
    
    @property
    def is_active(self) -> bool:
        return self.ip_address is not None
    
    @property
    def total_bytes_used(self) -> int:
        if self.bytes_in and self.bytes_out:
            return self.bytes_in + self.bytes_out
        return 0

@dataclass
class HotspotCard:
    """كرت هوتسبوت"""
    username: str
    password: str
    profile: str
    data_quota: str
    time_quota: str
    validity_days: int
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class NetworkDevice:
    """جهاز في الشبكة"""
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    response_time: Optional[float] = None
    is_reachable: bool = False

@dataclass
class PingResult:
    """نتيجة اختبار Ping"""
    target: str
    packets_sent: int
    packets_received: int
    packet_loss: float
    min_time: float
    max_time: float
    avg_time: float
    output: str

@dataclass
class TracerouteResult:
    """نتيجة تتبع المسار"""
    target: str
    hops: List[dict]
    output: str

@dataclass
class UserSession:
    """جلسة المستخدم"""
    telegram_user_id: int
    mikrotik_device: Optional[MikroTikDevice] = None
    is_authenticated: bool = False
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def update_activity(self):
        self.last_activity = datetime.now()

@dataclass
class DiagnosticResult:
    """نتيجة التشخيص"""
    test_name: str
    status: str  # 'success', 'warning', 'error'
    message: str
    details: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class SystemHealth:
    """صحة النظام"""
    cpu_status: DiagnosticResult
    memory_status: DiagnosticResult
    interface_status: DiagnosticResult
    overall_status: str
    recommendations: List[str]

