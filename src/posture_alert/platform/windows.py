"""Windows 실제 어댑터 (ctypes / winreg). Windows에서만 import된다."""
import ctypes
import winreg
from ctypes import wintypes

from .base import ActivityMonitor

QUNS_ACCEPTS_NOTIFICATIONS = 5
MIC_KEY = (r"Software\Microsoft\Windows\CurrentVersion"
           r"\CapabilityAccessManager\ConsentStore\microphone")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class WindowsMonitor(ActivityMonitor):
    def idle_seconds(self) -> float:
        info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        return (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000

    def fullscreen_or_dnd(self) -> bool:
        # 발표 모드·전체 화면 앱·방해 금지면 ACCEPTS_NOTIFICATIONS(5)가 아님
        state = ctypes.c_int()
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
            return False
        return state.value != QUNS_ACCEPTS_NOTIFICATIONS

    def in_meeting(self) -> bool:
        # 어떤 앱이든 마이크를 쓰는 중이면 LastUsedTimeStop == 0
        return _scan_mic(MIC_KEY)


def _scan_mic(path: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        return False
    with key:
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                return False
            i += 1
            sub_path = path + "\\" + sub
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_path) as k:
                    stop, _ = winreg.QueryValueEx(k, "LastUsedTimeStop")
                    if stop == 0:
                        return True
            except FileNotFoundError:
                if _scan_mic(sub_path):  # NonPackaged 같은 하위 그룹
                    return True
            except OSError:
                continue
