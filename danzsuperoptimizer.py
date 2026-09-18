"""
DÄNZ OPTIMIZER
System optimizer untuk Windows — RAM optimizer, CPU optimizer, Network booster.
Theme: Black / Mazda Soul Red.

Butuh: Windows 10/11, Python 3.9+, PySide6, psutil.  Jalankan sebagai Administrator.
"""

import sys
import os
import time
import ctypes
import socket
import subprocess
import urllib.request
from ctypes import wintypes

import psutil
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPointF, QRectF, QSize
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath,
                         QFont, QIcon, QPixmap, QCursor)
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QScrollArea, QSizePolicy, QGraphicsDropShadowEffect)

APP_NAME = "DanzSuperOptimizer"
APP_VER = "1.0.0"

# ----------------------------------------------------------------------------
# PALETTE — Black / Mazda Soul Red
# ----------------------------------------------------------------------------
BG        = "#0A0A0B"
PANEL     = "#111113"
PANEL_2   = "#161618"
BORDER    = "#232326"
TEXT      = "#E8E8EA"
TEXT_DIM  = "#87878E"
RED       = "#A6192E"   # Mazda Soul Red
RED_HOT   = "#E01B37"
RED_GLOW  = "#FF3350"
GREEN     = "#2ECC71"
AMBER     = "#E0A21B"

IS_WINDOWS = sys.platform == "win32"


# ============================================================================
#  WINDOWS NATIVE MEMORY API
# ============================================================================
if IS_WINDOWS:
    ntdll    = ctypes.WinDLL("ntdll")
    advapi32 = ctypes.WinDLL("advapi32")
    kernel32 = ctypes.WinDLL("kernel32")
    psapi    = ctypes.WinDLL("psapi")

SystemFileCacheInformation           = 0x15
SystemRegistryQuotaInformation       = 0x25
SystemMemoryListInformation          = 0x50
SystemFileCacheInformationEx         = 0x51
SystemCombinePhysicalMemoryInformation = 0x82

MemoryEmptyWorkingSets             = 2
MemoryFlushModifiedList            = 3
MemoryPurgeStandbyList             = 4
MemoryPurgeLowPriorityStandbyList  = 5

SE_PRIVILEGE_ENABLED = 0x00000002
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


class SYSTEM_FILECACHE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("CurrentSize", ctypes.c_size_t),
        ("PeakSize", ctypes.c_size_t),
        ("PageFaultCount", wintypes.ULONG),
        ("MinimumWorkingSet", ctypes.c_size_t),
        ("MaximumWorkingSet", ctypes.c_size_t),
        ("CurrentSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("PeakSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("TransitionRePurposeCount", wintypes.ULONG),
        ("Flags", wintypes.ULONG),
    ]


class SYSTEM_REGISTRY_QUOTA_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("RegistryQuotaAllowed", wintypes.ULONG),
        ("RegistryQuotaUsed", wintypes.ULONG),
        ("PagedPoolSize", ctypes.c_size_t),
    ]


class MEMORY_COMBINE_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("Handle", ctypes.c_void_p),
        ("PagesCombined", ctypes.c_size_t),
        ("Flags", wintypes.ULONG),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def enable_privilege(name: str) -> bool:
    """Aktifkan privilege token (SeProfileSingleProcess, SeIncreaseQuota, SeDebug)."""
    if not IS_WINDOWS:
        return False
    try:
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                         TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                         ctypes.byref(token)):
            return False
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            kernel32.CloseHandle(token)
            return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                            ctypes.sizeof(tp), None, None)
        err = kernel32.GetLastError()
        kernel32.CloseHandle(token)
        return bool(ok) and err == 0
    except Exception:
        return False


def enable_all_privileges():
    for p in ("SeProfileSingleProcessPrivilege", "SeIncreaseQuotaPrivilege",
              "SeDebugPrivilege"):
        enable_privilege(p)


def available_ram() -> int:
    """Byte RAM tersedia (dipakai untuk menghitung berapa yang dibebaskan)."""
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if IS_WINDOWS and kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return st.ullAvailPhys
    return psutil.virtual_memory().available


def _nt_set(info_class, buf) -> tuple:
    status = ntdll.NtSetSystemInformation(info_class, ctypes.byref(buf),
                                          ctypes.sizeof(buf))
    if status == 0:
        return True, ""
    return False, f"NTSTATUS 0x{status & 0xFFFFFFFF:08X}"


# --- Setiap fungsi di bawah = 1 opsi di panel RAM Optimizer -----------------
def clean_memory_list(cmd):
    if not IS_WINDOWS:
        return False, "Windows only"
    val = ctypes.c_int(cmd)
    status = ntdll.NtSetSystemInformation(SystemMemoryListInformation,
                                          ctypes.byref(val), ctypes.sizeof(val))
    if status == 0:
        return True, ""
    return False, f"NTSTATUS 0x{status & 0xFFFFFFFF:08X}"


def clean_modified_page_list():
    return clean_memory_list(MemoryFlushModifiedList)


def clean_standby_list():
    return clean_memory_list(MemoryPurgeStandbyList)


def clean_standby_list_lowprio():
    return clean_memory_list(MemoryPurgeLowPriorityStandbyList)


def clean_system_file_cache(ex=False):
    if not IS_WINDOWS:
        return False, "Windows only"
    info = SYSTEM_FILECACHE_INFORMATION()
    info.MinimumWorkingSet = ctypes.c_size_t(-1).value
    info.MaximumWorkingSet = ctypes.c_size_t(-1).value
    cls = SystemFileCacheInformationEx if ex else SystemFileCacheInformation
    return _nt_set(cls, info)


def clean_modified_file_cache():
    ok, err = clean_system_file_cache(ex=True)
    if not ok:
        ok, err = clean_system_file_cache(ex=False)
    return ok, err


def clean_registry_cache():
    if not IS_WINDOWS:
        return False, "Windows only"
    info = SYSTEM_REGISTRY_QUOTA_INFORMATION()
    info.RegistryQuotaAllowed = 0
    info.RegistryQuotaUsed = 0
    info.PagedPoolSize = ctypes.c_size_t(-1).value
    return _nt_set(SystemRegistryQuotaInformation, info)


def clean_combine_memory_lists():
    if not IS_WINDOWS:
        return False, "Windows only"
    info = MEMORY_COMBINE_INFORMATION_EX()
    info.Handle = None
    info.PagesCombined = 0
    info.Flags = 0
    return _nt_set(SystemCombinePhysicalMemoryInformation, info)


def clean_working_sets():
    """Kosongkan working set semua proses (native dulu, fallback per-proses)."""
    ok, err = clean_memory_list(MemoryEmptyWorkingSets)
    trimmed = 0
    for p in psutil.process_iter(["pid"]):
        pid = p.info["pid"]
        if pid <= 4:
            continue
        try:
            h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                                     False, pid)
            if h:
                if psapi.EmptyWorkingSet(h):
                    trimmed += 1
                kernel32.CloseHandle(h)
        except Exception:
            pass
    if ok or trimmed:
        return True, ""
    return False, err or "no access"


RAM_OPTIONS = [
    ("modified_file_cache", "Modified file cache",            clean_modified_file_cache),
    ("modified_page_list",  "Modified page list",             clean_modified_page_list),
    ("standby_list",        "Standby list",                   clean_standby_list),
    ("standby_lowprio",     "Standby list (without priority)", clean_standby_list_lowprio),
    ("registry_cache",      "Registry cache (Win 8.1+)",      clean_registry_cache),
    ("combine_lists",       "Combine memory lists (Win 10+)", clean_combine_memory_lists),
    ("working_set",         "Working set",                    clean_working_sets),
    ("system_file_cache",   "System file cache",              clean_system_file_cache),
]


# ============================================================================
#  PROCESS MANAGER — daftar aplikasi background + end task yang aman
# ============================================================================
PROTECTED_NAMES = {
    "system", "system idle process", "registry", "memory compression", "smss.exe",
    "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "lsaiso.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
    "spoolsv.exe", "conhost.exe", "dllhost.exe", "sihost.exe", "ctfmon.exe",
    "taskhostw.exe", "runtimebroker.exe", "searchhost.exe", "searchindexer.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe",
    "applicationframehost.exe", "lockapp.exe", "systemsettings.exe", "audiodg.exe",
    "wmiprvse.exe", "wudfhost.exe", "taskmgr.exe", "msmpeng.exe", "nissrv.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe", "smartscreen.exe",
    "useroobebroker.exe", "wudfrd.exe", "backgroundtaskhost.exe", "sppsvc.exe",
    "winstore.app.exe", "csrss", "idle",
}

PROTECTED_USERS = {"NT AUTHORITY\\SYSTEM", "NT AUTHORITY\\LOCAL SERVICE",
                   "NT AUTHORITY\\NETWORK SERVICE"}

WINDIR = os.environ.get("SystemRoot", r"C:\Windows").lower()
SELF_PID = os.getpid()


def is_protected(proc_info) -> bool:
    name = (proc_info.get("name") or "").lower()
    if name in PROTECTED_NAMES:
        return True
    pid = proc_info.get("pid", 0)
    if pid <= 4 or pid == SELF_PID:
        return True
    exe = (proc_info.get("exe") or "").lower()
    if exe.startswith(WINDIR):
        return True
    user = (proc_info.get("username") or "")
    if user.upper() in PROTECTED_USERS:
        return True
    return False


def list_user_processes():
    """Kumpulkan proses milik user (aplikasi), digabung per nama."""
    groups = {}
    for p in psutil.process_iter(["pid", "name", "exe", "username", "memory_info"]):
        try:
            info = p.info
            if is_protected(info):
                continue
            name = info.get("name") or f"pid {info['pid']}"
            mem = info["memory_info"].rss if info.get("memory_info") else 0
            g = groups.setdefault(name, {"name": name, "pids": [], "mem": 0,
                                         "exe": info.get("exe") or ""})
            g["pids"].append(info["pid"])
            g["mem"] += mem
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    out = list(groups.values())
    out.sort(key=lambda g: g["mem"], reverse=True)
    return out


def end_group(pids):
    """Terminate lalu kill kalau bandel. Return jumlah proses yang mati."""
    killed = 0
    procs = []
    for pid in pids:
        try:
            procs.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            pass
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    gone, alive = psutil.wait_procs(procs, timeout=2)
    killed += len(gone)
    for p in alive:
        try:
            p.kill()
            killed += 1
        except Exception:
            pass
    return killed


# ============================================================================
#  WORKERS
# ============================================================================
class RamWorker(QThread):
    finished_ok = Signal(float, list, list)   # freed_bytes, done[], failed[]

    def __init__(self, keys):
        super().__init__()
        self.keys = keys

    def run(self):
        enable_all_privileges()
        before = available_ram()
        done, failed = [], []
        for key, label, fn in RAM_OPTIONS:
            if key not in self.keys:
                continue
            try:
                ok, err = fn()
            except Exception as e:
                ok, err = False, str(e)
            (done if ok else failed).append(label if ok else f"{label} ({err})")
            time.sleep(0.05)
        time.sleep(0.6)
        after = available_ram()
        self.finished_ok.emit(max(0, after - before), done, failed)


class CpuWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(int, int)   # apps, processes

    def run(self):
        enable_privilege("SeDebugPrivilege")
        groups = list_user_processes()
        apps = 0
        total = 0
        for g in groups:
            self.progress.emit(g["name"])
            n = end_group(g["pids"])
            if n:
                apps += 1
                total += n
            time.sleep(0.06)
        # Turunkan prioritas sisa proses ringan agar CPU lega
        time.sleep(0.4)
        self.finished_ok.emit(apps, total)


class SpeedTestWorker(QThread):
    stage = Signal(str)
    result = Signal(float, float, float)   # ping ms, down Mbps, up Mbps
    failed = Signal(str)

    DOWN_URL = "https://speed.cloudflare.com/__down?bytes=25000000"
    UP_URL = "https://speed.cloudflare.com/__up"

    def run(self):
        try:
            self.stage.emit("PING")
            ping = self._ping()
            self.stage.emit("DOWNLOAD")
            down = self._download()
            self.stage.emit("UPLOAD")
            up = self._upload()
            self.result.emit(ping, down, up)
        except Exception as e:
            self.failed.emit(str(e))

    def _ping(self):
        samples = []
        for _ in range(5):
            t = time.perf_counter()
            try:
                s = socket.create_connection(("1.1.1.1", 443), timeout=3)
                s.close()
                samples.append((time.perf_counter() - t) * 1000)
            except Exception:
                pass
        return sum(samples) / len(samples) if samples else -1

    def _download(self):
        req = urllib.request.Request(self.DOWN_URL, headers={"User-Agent": APP_NAME})
        start = time.perf_counter()
        total = 0
        with urllib.request.urlopen(req, timeout=20) as r:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if time.perf_counter() - start > 10:
                    break
        dur = max(0.001, time.perf_counter() - start)
        return (total * 8) / dur / 1_000_000

    def _upload(self):
        payload = os.urandom(5_000_000)
        req = urllib.request.Request(self.UP_URL, data=payload,
                                     headers={"Content-Type": "application/octet-stream",
                                              "User-Agent": APP_NAME})
        start = time.perf_counter()
        try:
            urllib.request.urlopen(req, timeout=25).read()
        except Exception:
            pass
        dur = max(0.001, time.perf_counter() - start)
        return (len(payload) * 8) / dur / 1_000_000


class BoosterWorker(QThread):
    """Network refresh: flush DNS + ARP + reset koneksi idle. Bukan penambah bandwidth."""
    stage = Signal(str)
    finished_ok = Signal(list)

    STEPS = [
        ("Flush DNS cache", ["ipconfig", "/flushdns"]),
        ("Register DNS", ["ipconfig", "/registerdns"]),
        ("Flush ARP table", ["netsh", "interface", "ip", "delete", "arpcache"]),
        ("Reset Winsock stats", ["netsh", "winsock", "show", "catalog"]),
        ("Re-prioritize TCP", ["netsh", "int", "tcp", "show", "global"]),
    ]

    def run(self):
        log = []
        flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
        for label, cmd in self.STEPS:
            self.stage.emit(label)
            try:
                subprocess.run(cmd, capture_output=True, timeout=10,
                               creationflags=flags)
                log.append(f"OK   {label}")
            except Exception as e:
                log.append(f"SKIP {label} ({e.__class__.__name__})")
            time.sleep(0.5)
        self.finished_ok.emit(log)


# ============================================================================
#  WIDGETS
# ============================================================================
class Card(QFrame):
    def __init__(self, title, badge=""):
        super().__init__()
        self.setObjectName("card")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(16, 12, 16, 14)
        self.v.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        bar = QFrame()
        bar.setFixedSize(3, 14)
        bar.setStyleSheet(f"background:{RED_HOT}; border-radius:1px;")
        head.addWidget(bar)
        lbl = QLabel(title)
        lbl.setObjectName("cardTitle")
        head.addWidget(lbl)
        head.addStretch()
        self.badge = QLabel(badge)
        self.badge.setObjectName("cardBadge")
        head.addWidget(self.badge)
        self.v.addLayout(head)

    def body(self, layout):
        self.v.addLayout(layout)


class Graph(QWidget):
    """Grafik garis real-time dengan gradient fill."""

    def __init__(self, color=RED_HOT, maxlen=90, unit="%", auto_scale=False):
        super().__init__()
        self.color = QColor(color)
        self.data = [0.0] * maxlen
        self.maxlen = maxlen
        self.unit = unit
        self.auto_scale = auto_scale
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def push(self, v):
        self.data.append(float(v))
        if len(self.data) > self.maxlen:
            self.data.pop(0)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(PANEL_2))

        # grid
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        for i in range(1, 4):
            y = h * i / 4
            p.drawLine(0, int(y), w, int(y))
        for i in range(1, 6):
            x = w * i / 6
            p.drawLine(int(x), 0, int(x), h)

        top = 100.0
        if self.auto_scale:
            top = max(10.0, max(self.data) * 1.25)

        pts = []
        n = len(self.data)
        for i, v in enumerate(self.data):
            x = w * i / max(1, n - 1)
            y = h - (min(v, top) / top) * (h - 6) - 3
            pts.append(QPointF(x, y))

        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)

        fill = QPainterPath(path)
        fill.lineTo(w, h)
        fill.lineTo(0, h)
        fill.closeSubpath()

        g = QLinearGradient(0, 0, 0, h)
        c1 = QColor(self.color); c1.setAlpha(110)
        c2 = QColor(self.color); c2.setAlpha(0)
        g.setColorAt(0, c1)
        g.setColorAt(1, c2)
        p.fillPath(fill, QBrush(g))

        p.setPen(QPen(self.color, 2))
        p.drawPath(path)

        # titik terakhir
        p.setBrush(QBrush(self.color))
        p.setPen(QPen(QColor(BG), 2))
        p.drawEllipse(pts[-1], 4, 4)
        p.end()


class Gauge(QWidget):
    """Ring gauge persentase."""

    def __init__(self, label):
        super().__init__()
        self.label = label
        self.value = 0.0
        self.sub = ""
        self.setFixedSize(112, 112)

    def set_value(self, v, sub=""):
        self.value = v
        self.sub = sub
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(9, 9, self.width() - 18, self.height() - 18)

        track = QPen(QColor(38, 38, 42), 9)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track)
        p.drawArc(rect, 225 * 16, -270 * 16)

        col = QColor(RED_HOT) if self.value < 85 else QColor(RED_GLOW)
        arc = QPen(col, 9)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc)
        p.drawArc(rect, 225 * 16, int(-270 * 16 * self.value / 100))

        p.setPen(QColor(TEXT))
        f = QFont("Segoe UI", 19, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(self.rect().adjusted(0, -10, 0, -10),
                   Qt.AlignmentFlag.AlignCenter, f"{self.value:.0f}%")

        p.setPen(QColor(TEXT_DIM))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(self.rect().adjusted(0, 26, 0, 26),
                   Qt.AlignmentFlag.AlignCenter, self.sub or self.label)
        p.end()


class BlackOverlay(QWidget):
    """Layar hitam full-screen saat CPU optimize berjalan."""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setStyleSheet("background:#000000;")
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(16)

        t = QLabel("CPU OPTIMIZE")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"color:{RED_HOT}; font-size:38px; font-weight:800;"
                        "letter-spacing:10px;")
        v.addWidget(t)

        self.status = QLabel("Menutup aplikasi background…")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(f"color:{TEXT_DIM}; font-size:13px;"
                                  "letter-spacing:2px;")
        v.addWidget(self.status)

        self.dots = QLabel("")
        self.dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dots.setStyleSheet(f"color:{RED}; font-size:20px; letter-spacing:6px;")
        v.addWidget(self.dots)

        self._i = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(220)

    def _tick(self):
        self._i = (self._i + 1) % 8
        self.dots.setText("▮" * self._i + "▯" * (8 - self._i))

    def set_status(self, s):
        self.status.setText(s)

    def keyPressEvent(self, e):
        pass  # jangan bisa ditutup sembarangan


# ============================================================================
#  MAIN WINDOW
# ============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1120, 720)
        self.resize(1240, 780)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._drag = None
        self._proc_pids = set()
        self._net_last = psutil.net_io_counters()
        self._overlay = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._title_bar())

        grid = QGridLayout()
        grid.setContentsMargins(14, 12, 14, 14)
        grid.setSpacing(12)

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(self._box4_optimize(), 3)   # BOX 4
        right.addWidget(self._box3_network(), 2)    # BOX 3
        right_w = QWidget()
        right_w.setLayout(right)

        grid.addWidget(self._box1_usage(), 0, 0)    # BOX 1
        grid.addWidget(right_w, 0, 1)
        grid.addWidget(self._box2_processes(), 1, 0, 1, 2)   # BOX 2

        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 4)
        grid.setRowStretch(0, 5)
        grid.setRowStretch(1, 4)
        outer.addLayout(grid)
        outer.addWidget(self._status_bar())

        self.setStyleSheet(STYLE)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick_fast)
        self.timer.start(1000)

        self.timer_proc = QTimer(self)
        self.timer_proc.timeout.connect(self.refresh_processes)
        self.timer_proc.start(3000)

        psutil.cpu_percent(interval=None)
        self.refresh_processes()
        self.tick_fast()

        if not is_admin():
            QTimer.singleShot(400, self.warn_admin)
        else:
            enable_all_privileges()

    # ---------------- title bar ----------------
    def _title_bar(self):
        bar = QFrame()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(46)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 8, 0)
        h.setSpacing(10)

        dot = QLabel("◆")
        dot.setStyleSheet(f"color:{RED_HOT}; font-size:15px;")
        h.addWidget(dot)

        name = QLabel("DANZ SUPER OPTIMIZER")
        name.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:800;"
                           "letter-spacing:3px;")
        h.addWidget(name)

        ver = QLabel(f"v{APP_VER}")
        ver.setStyleSheet(f"color:{TEXT_DIM}; font-size:10px;")
        h.addWidget(ver)

        self.admin_tag = QLabel("ADMIN" if is_admin() else "LIMITED")
        self.admin_tag.setObjectName("tagOk" if is_admin() else "tagWarn")
        h.addWidget(self.admin_tag)

        h.addStretch()

        for txt, slot, oid in (("—", self.showMinimized, "winbtn"),
                               ("▢", self._toggle_max, "winbtn"),
                               ("✕", self.close, "winbtnClose")):
            b = QPushButton(txt)
            b.setObjectName(oid)
            b.setFixedSize(38, 30)
            b.clicked.connect(slot)
            h.addWidget(b)
        return bar

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 46:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    # ---------------- BOX 1 : RAM & CPU usage ----------------
    def _box1_usage(self):
        card = Card("SYSTEM USAGE", "LIVE")
        v = QVBoxLayout()
        v.setSpacing(10)

        gauges = QHBoxLayout()
        gauges.setSpacing(18)
        self.g_ram = Gauge("RAM")
        self.g_cpu = Gauge("CPU")
        gauges.addWidget(self.g_ram)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_ram = QLabel("RAM")
        self.lbl_ram.setObjectName("metricTitle")
        self.lbl_ram_v = QLabel("–")
        self.lbl_ram_v.setObjectName("metricValue")
        self.lbl_cpu = QLabel("CPU")
        self.lbl_cpu.setObjectName("metricTitle")
        self.lbl_cpu_v = QLabel("–")
        self.lbl_cpu_v.setObjectName("metricValue")
        info.addStretch()
        info.addWidget(self.lbl_ram)
        info.addWidget(self.lbl_ram_v)
        info.addSpacing(8)
        info.addWidget(self.lbl_cpu)
        info.addWidget(self.lbl_cpu_v)
        info.addStretch()
        gauges.addLayout(info, 1)
        gauges.addWidget(self.g_cpu)
        v.addLayout(gauges)

        self.graph_ram = Graph(RED_HOT)
        self.graph_cpu = Graph(RED)
        for g, t in ((self.graph_ram, "RAM  %"), (self.graph_cpu, "CPU  %")):
            row = QVBoxLayout()
            row.setSpacing(3)
            lab = QLabel(t)
            lab.setObjectName("graphLabel")
            row.addWidget(lab)
            row.addWidget(g)
            v.addLayout(row)

        card.body(v)
        return card

    # ---------------- BOX 4 : optimize list ----------------
    def _box4_optimize(self):
        card = Card("OPTIMIZER", "READY")
        v = QVBoxLayout()
        v.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scroll")
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 6, 0)
        iv.setSpacing(6)

        head = QLabel("RAM OPTIMIZER")
        head.setObjectName("sectionLabel")
        iv.addWidget(head)

        self.checks = {}
        for key, label, _fn in RAM_OPTIONS:
            cb = QCheckBox(label)
            cb.setChecked(key in ("modified_page_list", "standby_list", "working_set"))
            self.checks[key] = cb
            iv.addWidget(cb)

        row = QHBoxLayout()
        row.setSpacing(8)
        b_sel = QPushButton("OPTIMIZE SELECTED")
        b_sel.setObjectName("btnGhost")
        b_sel.clicked.connect(self.run_ram_selected)
        b_all = QPushButton("OPTIMIZE ALL")
        b_all.setObjectName("btnPrimary")
        b_all.clicked.connect(self.run_ram_all)
        row.addWidget(b_sel)
        row.addWidget(b_all)
        iv.addSpacing(4)
        iv.addLayout(row)

        self.lbl_ram_result = QLabel("Belum ada optimasi dijalankan.")
        self.lbl_ram_result.setObjectName("resultBox")
        self.lbl_ram_result.setWordWrap(True)
        iv.addWidget(self.lbl_ram_result)

        iv.addSpacing(6)
        head2 = QLabel("CPU OPTIMIZER")
        head2.setObjectName("sectionLabel")
        iv.addWidget(head2)
        note = QLabel("Menutup semua aplikasi background. Proses sistem Windows "
                      "tidak disentuh.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        iv.addWidget(note)
        b_cpu = QPushButton("OPTIMIZE CPU")
        b_cpu.setObjectName("btnPrimary")
        b_cpu.clicked.connect(self.run_cpu)
        iv.addWidget(b_cpu)

        iv.addSpacing(6)
        head3 = QLabel("SIGNAL BOOSTER")
        head3.setObjectName("sectionLabel")
        iv.addWidget(head3)
        note2 = QLabel("Flush DNS & ARP cache, refresh koneksi. Tidak menambah "
                       "bandwidth dari ISP.")
        note2.setObjectName("hint")
        note2.setWordWrap(True)
        iv.addWidget(note2)
        b_boost = QPushButton("BOOST SIGNAL")
        b_boost.setObjectName("btnGhost")
        b_boost.clicked.connect(self.run_boost)
        iv.addWidget(b_boost)
        iv.addStretch()

        scroll.setWidget(inner)
        v.addWidget(scroll)
        card.body(v)
        return card

    # ---------------- BOX 3 : network / signal ----------------
    def _box3_network(self):
        card = Card("NETWORK SIGNAL", "LIVE")
        v = QVBoxLayout()
        v.setSpacing(8)

        stats = QHBoxLayout()
        stats.setSpacing(6)
        self.n_ping = self._stat("PING", "– ms")
        self.n_down = self._stat("DOWNLOAD", "– Mbps")
        self.n_up = self._stat("UPLOAD", "– Mbps")
        for wdg in (self.n_ping, self.n_down, self.n_up):
            stats.addWidget(wdg)
        v.addLayout(stats)

        self.graph_net = Graph(RED_GLOW, auto_scale=True)
        self.graph_net.setMinimumHeight(70)
        v.addWidget(self.graph_net)

        lab = QLabel("Live throughput (Mbps)")
        lab.setObjectName("graphLabel")
        v.addWidget(lab)

        self.btn_speed = QPushButton("RUN SPEED TEST")
        self.btn_speed.setObjectName("btnGhost")
        self.btn_speed.clicked.connect(self.run_speedtest)
        v.addWidget(self.btn_speed)

        card.body(v)
        return card

    def _stat(self, title, value):
        f = QFrame()
        f.setObjectName("stat")
        vv = QVBoxLayout(f)
        vv.setContentsMargins(10, 8, 10, 8)
        vv.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("statTitle")
        val = QLabel(value)
        val.setObjectName("statValue")
        vv.addWidget(t)
        vv.addWidget(val)
        f.value_label = val
        return f

    # ---------------- BOX 2 : background apps ----------------
    def _box2_processes(self):
        card = Card("BACKGROUND APPLICATIONS", "0 APPS")
        self.card_proc = card
        v = QVBoxLayout()
        v.setSpacing(8)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["APPLICATION", "PID", "INSTANCES", "MEMORY", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3, 4):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 90)
        self.table.verticalHeader().setDefaultSectionSize(38)
        v.addWidget(self.table)

        row = QHBoxLayout()
        b_ref = QPushButton("REFRESH")
        b_ref.setObjectName("btnGhost")
        b_ref.clicked.connect(self.refresh_processes)
        row.addWidget(b_ref)
        row.addStretch()
        self.lbl_proc_note = QLabel("Proses sistem Windows disembunyikan demi keamanan.")
        self.lbl_proc_note.setObjectName("hint")
        row.addWidget(self.lbl_proc_note)
        v.addLayout(row)

        card.body(v)
        return card

    def _status_bar(self):
        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(28)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        self.status = QLabel("Ready.")
        self.status.setObjectName("statusText")
        h.addWidget(self.status)
        h.addStretch()
        h.addWidget(QLabel(f"<span style='color:{TEXT_DIM};font-size:10px'>"
                           f"DÄNZ · Black / Soul Red</span>"))
        return bar

    # ---------------- updates ----------------
    def tick_fast(self):
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)

        self.g_ram.set_value(vm.percent, "RAM")
        self.g_cpu.set_value(cpu, "CPU")
        self.graph_ram.push(vm.percent)
        self.graph_cpu.push(cpu)

        used = (vm.total - vm.available) / 1024 ** 3
        total = vm.total / 1024 ** 3
        self.lbl_ram_v.setText(f"{used:.2f} / {total:.2f} GB")
        self.lbl_cpu_v.setText(f"{cpu:.0f} %   ·   {psutil.cpu_count()} threads")

        now = psutil.net_io_counters()
        mbps = ((now.bytes_recv - self._net_last.bytes_recv) * 8) / 1_000_000
        self._net_last = now
        self.graph_net.push(mbps)

    def refresh_processes(self):
        groups = list_user_processes()
        self.card_proc.badge.setText(f"{len(groups)} APPS")

        pid_sig = tuple(sorted(g["name"] for g in groups))
        rebuild = pid_sig != tuple(sorted(self._proc_pids))
        self._proc_pids = set(g["name"] for g in groups)

        if rebuild:
            self.table.setRowCount(len(groups))
            for r, g in enumerate(groups):
                self._fill_row(r, g, new=True)
        else:
            for r, g in enumerate(groups):
                if r < self.table.rowCount():
                    self._fill_row(r, g, new=False)

    def _fill_row(self, r, g, new):
        def item(text, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
            it = QTableWidgetItem(text)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it.setTextAlignment(align)
            return it

        mem_gb = g["mem"] / 1024 ** 3
        mem_txt = f"{mem_gb:.2f} GB" if mem_gb >= 1 else f"{g['mem']/1024**2:.0f} MB"

        self.table.setItem(r, 0, item("  " + g["name"]))
        self.table.setItem(r, 1, item(str(g["pids"][0]),
                                      Qt.AlignmentFlag.AlignCenter))
        self.table.setItem(r, 2, item(str(len(g["pids"])),
                                      Qt.AlignmentFlag.AlignCenter))
        self.table.setItem(r, 3, item(mem_txt, Qt.AlignmentFlag.AlignCenter))

        if new or self.table.cellWidget(r, 4) is None:
            btn = QPushButton("END")
            btn.setObjectName("btnEnd")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.table.setCellWidget(r, 4, btn)
        else:
            btn = self.table.cellWidget(r, 4)
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        pids = list(g["pids"])
        name = g["name"]
        btn.clicked.connect(lambda _=False, p=pids, n=name: self.end_app(n, p))

    # ---------------- actions ----------------
    def warn_admin(self):
        m = QMessageBox(self)
        m.setWindowTitle("Butuh hak Administrator")
        m.setIcon(QMessageBox.Icon.Warning)
        m.setText("Aplikasi tidak dijalankan sebagai Administrator.")
        m.setInformativeText("Fungsi pembersihan standby list, file cache, dan end "
                             "task sebagian akan gagal. Tutup dan jalankan ulang "
                             "via klik kanan → Run as administrator.")
        m.setStyleSheet(DIALOG_STYLE)
        m.exec()

    def end_app(self, name, pids):
        m = QMessageBox(self)
        m.setWindowTitle("End Task")
        m.setIcon(QMessageBox.Icon.Question)
        m.setText(f"Tutup paksa {name}?")
        m.setInformativeText(f"{len(pids)} proses akan dihentikan. Pekerjaan yang "
                             "belum disimpan bisa hilang.")
        m.setStandardButtons(QMessageBox.StandardButton.Yes |
                             QMessageBox.StandardButton.No)
        m.setStyleSheet(DIALOG_STYLE)
        if m.exec() != QMessageBox.StandardButton.Yes:
            return
        n = end_group(pids)
        self.status.setText(f"{name}: {n} proses dihentikan.")
        self.refresh_processes()

    def run_ram_all(self):
        self.run_ram([k for k, _, _ in RAM_OPTIONS])

    def run_ram_selected(self):
        keys = [k for k in self.checks if self.checks[k].isChecked()]
        if not keys:
            self.status.setText("Pilih minimal satu opsi RAM optimizer.")
            return
        self.run_ram(keys)

    def run_ram(self, keys):
        self.status.setText("Membersihkan memori…")
        self.lbl_ram_result.setText("Menjalankan " + str(len(keys)) + " rutin…")
        self.ram_worker = RamWorker(keys)
        self.ram_worker.finished_ok.connect(self.on_ram_done)
        self.ram_worker.start()

    def on_ram_done(self, freed, done, failed):
        gb = freed / 1024 ** 3
        mb = freed / 1024 ** 2
        amount = f"{gb:.2f} GB" if gb >= 1 else f"{mb:.0f} MB"
        txt = (f"<b style='color:{RED_GLOW};font-size:15px'>{amount}</b> RAM "
               f"dibebaskan<br><span style='color:{TEXT_DIM}'>Berhasil: "
               f"{len(done)} rutin</span>")
        if failed:
            txt += (f"<br><span style='color:{AMBER}'>Gagal: {len(failed)} "
                    f"(butuh admin)</span>")
        self.lbl_ram_result.setText(txt)
        self.status.setText(f"Selesai — {amount} dibebaskan.")

        m = QMessageBox(self)
        m.setWindowTitle("RAM Optimized")
        m.setIcon(QMessageBox.Icon.Information)
        m.setText(f"{amount} RAM berhasil dibebaskan.")
        detail = "Berhasil:\n• " + "\n• ".join(done) if done else "Tidak ada rutin yang berhasil."
        if failed:
            detail += "\n\nGagal:\n• " + "\n• ".join(failed)
        m.setInformativeText(detail)
        m.setStyleSheet(DIALOG_STYLE)
        m.exec()

    def run_cpu(self):
        groups = list_user_processes()
        names = ", ".join(g["name"] for g in groups[:12])
        more = f" (+{len(groups)-12} lainnya)" if len(groups) > 12 else ""

        m = QMessageBox(self)
        m.setWindowTitle("Peringatan — CPU Optimize")
        m.setIcon(QMessageBox.Icon.Warning)
        m.setText("SEMUA APLIKASI BACKGROUND AKAN DITUTUP.")
        m.setInformativeText(
            "Proses sistem Windows TIDAK akan disentuh, jadi komputer tetap aman.\n\n"
            f"Akan ditutup ({len(groups)} aplikasi):\n{names}{more}\n\n"
            "Simpan pekerjaan Anda dulu. Layar akan menjadi hitam selama proses "
            "berjalan. Lanjutkan?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes |
                             QMessageBox.StandardButton.Cancel)
        m.setDefaultButton(QMessageBox.StandardButton.Cancel)
        m.setStyleSheet(DIALOG_STYLE)
        if m.exec() != QMessageBox.StandardButton.Yes:
            return

        self._overlay = BlackOverlay()
        self._overlay.showFullScreen()
        QApplication.processEvents()

        self.cpu_worker = CpuWorker()
        self.cpu_worker.progress.connect(
            lambda n: self._overlay and self._overlay.set_status(f"Menutup {n}…"))
        self.cpu_worker.finished_ok.connect(self.on_cpu_done)
        self.cpu_worker.start()

    def on_cpu_done(self, apps, procs):
        if self._overlay:
            self._overlay.set_status("Selesai.")
            QTimer.singleShot(700, self._close_overlay)
        self.status.setText(f"CPU optimize: {apps} aplikasi ({procs} proses) ditutup.")
        self.refresh_processes()
        QTimer.singleShot(900, lambda: self._cpu_report(apps, procs))

    def _close_overlay(self):
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def _cpu_report(self, apps, procs):
        m = QMessageBox(self)
        m.setWindowTitle("CPU Optimized")
        m.setIcon(QMessageBox.Icon.Information)
        m.setText(f"{apps} aplikasi background ditutup.")
        m.setInformativeText(f"Total {procs} proses dihentikan. "
                             "Semua layanan Windows tetap berjalan normal.")
        m.setStyleSheet(DIALOG_STYLE)
        m.exec()

    def run_speedtest(self):
        self.btn_speed.setEnabled(False)
        self.btn_speed.setText("TESTING…")
        self.sp = SpeedTestWorker()
        self.sp.stage.connect(lambda s: self.status.setText(f"Speed test: {s}…"))
        self.sp.result.connect(self.on_speed_done)
        self.sp.failed.connect(self.on_speed_fail)
        self.sp.start()

    def on_speed_done(self, ping, down, up):
        self.n_ping.value_label.setText(f"{ping:.0f} ms" if ping > 0 else "n/a")
        self.n_down.value_label.setText(f"{down:.1f} Mbps")
        self.n_up.value_label.setText(f"{up:.1f} Mbps")
        self.btn_speed.setEnabled(True)
        self.btn_speed.setText("RUN SPEED TEST")
        self.status.setText(f"Speed test selesai — ↓{down:.1f} ↑{up:.1f} Mbps")

    def on_speed_fail(self, err):
        self.btn_speed.setEnabled(True)
        self.btn_speed.setText("RUN SPEED TEST")
        self.status.setText(f"Speed test gagal: {err}")

    def run_boost(self):
        self.status.setText("Network refresh berjalan…")
        self.bw = BoosterWorker()
        self.bw.stage.connect(lambda s: self.status.setText(f"Booster: {s}…"))
        self.bw.finished_ok.connect(self.on_boost_done)
        self.bw.start()

    def on_boost_done(self, log):
        self.status.setText("Network refresh selesai.")
        m = QMessageBox(self)
        m.setWindowTitle("Signal Booster")
        m.setIcon(QMessageBox.Icon.Information)
        m.setText("Koneksi sudah di-refresh.")
        m.setInformativeText("\n".join(log) +
                             "\n\nCatatan: ini membersihkan cache DNS/ARP dan "
                             "me-refresh koneksi. Kecepatan maksimum tetap "
                             "ditentukan oleh paket ISP dan kekuatan sinyal.")
        m.setStyleSheet(DIALOG_STYLE)
        m.exec()

    def closeEvent(self, e):
        self._close_overlay()
        e.accept()


# ============================================================================
#  STYLESHEET
# ============================================================================
STYLE = f"""
#root {{ background: {BG}; }}

#titlebar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #141416, stop:1 #0C0C0D);
    border-bottom: 1px solid {BORDER};
}}
#winbtn, #winbtnClose {{
    background: transparent; color: {TEXT_DIM};
    border: none; font-size: 12px; border-radius: 4px;
}}
#winbtn:hover {{ background: #1E1E22; color: {TEXT}; }}
#winbtnClose:hover {{ background: {RED}; color: #FFFFFF; }}

#tagOk {{
    color: {GREEN}; border: 1px solid #1F4030; background: #10231A;
    padding: 2px 8px; border-radius: 9px; font-size: 9px; font-weight: 700;
    letter-spacing: 1px;
}}
#tagWarn {{
    color: {AMBER}; border: 1px solid #40361F; background: #231D10;
    padding: 2px 8px; border-radius: 9px; font-size: 9px; font-weight: 700;
    letter-spacing: 1px;
}}

#card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
#cardTitle {{
    color: {TEXT}; font-size: 11px; font-weight: 800; letter-spacing: 2px;
}}
#cardBadge {{
    color: {RED_HOT}; font-size: 9px; font-weight: 700; letter-spacing: 1px;
    border: 1px solid #37141C; background: #1A0D11;
    padding: 2px 8px; border-radius: 9px;
}}
#sectionLabel {{
    color: {RED_HOT}; font-size: 9.5px; font-weight: 800; letter-spacing: 2px;
    padding-top: 4px;
}}
#graphLabel {{ color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1.5px; }}
#metricTitle {{ color: {TEXT_DIM}; font-size: 9.5px; letter-spacing: 2px; }}
#metricValue {{ color: {TEXT}; font-size: 15px; font-weight: 700; }}
#hint {{ color: #6A6A72; font-size: 9.5px; }}

#resultBox {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 7px;
    padding: 9px; color: {TEXT_DIM}; font-size: 11px;
}}

QCheckBox {{ color: {TEXT}; font-size: 11.5px; spacing: 8px; padding: 2px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #34343A; background: {PANEL_2};
}}
QCheckBox::indicator:hover {{ border: 1px solid {RED}; }}
QCheckBox::indicator:checked {{
    background: {RED_HOT}; border: 1px solid {RED_HOT};
}}

#btnPrimary {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {RED_HOT}, stop:1 {RED});
    color: #FFFFFF; border: none; border-radius: 7px;
    padding: 10px 14px; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;
}}
#btnPrimary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {RED_GLOW}, stop:1 {RED_HOT});
}}
#btnPrimary:pressed {{ background: {RED}; }}

#btnGhost {{
    background: {PANEL_2}; color: {TEXT};
    border: 1px solid #2E2E33; border-radius: 7px;
    padding: 10px 14px; font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px;
}}
#btnGhost:hover {{ border: 1px solid {RED_HOT}; color: {RED_GLOW}; }}
#btnGhost:disabled {{ color: #55555C; border-color: #26262A; }}

#btnEnd {{
    background: transparent; color: {RED_GLOW};
    border: 1px solid #40161F; border-radius: 6px;
    padding: 5px 10px; font-size: 10px; font-weight: 800; letter-spacing: 1px;
    margin: 4px 8px;
}}
#btnEnd:hover {{ background: {RED}; color: #FFFFFF; border-color: {RED}; }}

#stat {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 7px;
}}
#statTitle {{ color: {TEXT_DIM}; font-size: 8.5px; letter-spacing: 1.5px; }}
#statValue {{ color: {TEXT}; font-size: 13px; font-weight: 700; }}

QTableWidget {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
    color: {TEXT}; font-size: 11.5px;
    alternate-background-color: #141416;
    gridline-color: transparent;
}}
QTableWidget::item {{ border-bottom: 1px solid #1B1B1E; padding: 4px; }}
QHeaderView::section {{
    background: {PANEL}; color: {TEXT_DIM};
    border: none; border-bottom: 1px solid {BORDER};
    padding: 8px 6px; font-size: 9px; font-weight: 800; letter-spacing: 1.5px;
}}

#scroll {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #2C2C31; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {RED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

#statusbar {{ background: #0C0C0D; border-top: 1px solid {BORDER}; }}
#statusText {{ color: {TEXT_DIM}; font-size: 10px; }}

QWidget {{ font-family: "Segoe UI", "Inter", sans-serif; }}
"""

DIALOG_STYLE = f"""
QMessageBox {{ background: {PANEL}; }}
QMessageBox QLabel {{ color: {TEXT}; font-size: 12px; }}
QMessageBox QPushButton {{
    background: {PANEL_2}; color: {TEXT}; border: 1px solid #2E2E33;
    border-radius: 6px; padding: 7px 18px; font-size: 11px; font-weight: 700;
    min-width: 76px;
}}
QMessageBox QPushButton:hover {{ border-color: {RED_HOT}; color: {RED_GLOW}; }}
QMessageBox QPushButton:default {{
    background: {RED}; border-color: {RED}; color: #FFFFFF;
}}
"""


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
