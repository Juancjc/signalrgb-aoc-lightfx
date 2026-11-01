"""Icone na bandeja do Windows para a ponte AOC Light FX.

Roda a ponte (aoc_lightfx_bridge.py) em segundo plano e mostra um icone com a
cor atual. Pelo menu do icone da para:
  - desligar/religar os LEDs do monitor;
  - ligar/desligar a abertura junto com o Windows;
  - fechar o G-Menu, que disputa o barramento DDC e atrapalha o SignalRGB
    (pode ficar automatico, verificando a cada poucos segundos);
  - abrir o log e sair.

Usa so a API do Windows via ctypes, sem dependencias externas.
"""
import ctypes
import json
import os
import sys
import threading
import time
import winreg
from ctypes import wintypes as wt

import aoc_lightfx_bridge as bridge

APP_NAME = "AOC Light FX"
CONFIG_FILE = os.path.join(bridge.BASE_DIR, "config.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
OLD_STARTUP_LNK = "AOC Light FX Ponte.lnk"  # criado por versoes antigas do instalar_inicializacao.bat
GMENU_EXES = {"g-menu.exe", "g_menu.exe"}
GMENU_CHECK_INTERVAL = 5.0
RECEIVING_TIMEOUT = 3.0  # segundos sem pacote para considerar o SignalRGB parado

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

WM_NULL, WM_DESTROY, WM_CLOSE, WM_TIMER = 0x0000, 0x0002, 0x0010, 0x0113
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
WM_TRAY = 0x8000 + 1  # WM_APP + 1
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10
MF_STRING, MF_GRAYED, MF_CHECKED, MF_SEPARATOR = 0x0, 0x1, 0x8, 0x800
TPM_RIGHTBUTTON, TPM_NONOTIFY, TPM_RETURNCMD = 0x2, 0x80, 0x100
MB_ICONWARNING = 0x30
SM_CXSMICON = 49
TH32CS_SNAPPROCESS = 0x2
PROCESS_TERMINATE = 0x1

CMD_STARTUP, CMD_AUTO_GMENU, CMD_KILL_GMENU, CMD_LOG, CMD_EXIT, CMD_LEDS_OFF = range(1, 7)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
        ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT), ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
        ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
        ("hbmMask", wt.HBITMAP), ("hbmColor", wt.HBITMAP),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [
    wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID,
]
user32.CreateWindowExW.restype = wt.HWND
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreatePopupMenu.restype = wt.HMENU
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
user32.TrackPopupMenu.argtypes = [
    wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.LPVOID,
]
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_size_t, wt.UINT, wt.LPVOID]
user32.SetTimer.restype = ctypes.c_size_t
user32.DestroyWindow.argtypes = [wt.HWND]
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.CreateIconIndirect.restype = wt.HICON
user32.DestroyIcon.argtypes = [wt.HICON]
user32.MessageBoxW.argtypes = [wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.UINT]
shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
gdi32.CreateDIBSection.argtypes = [
    wt.HDC, ctypes.c_void_p, wt.UINT, ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD,
]
gdi32.CreateDIBSection.restype = wt.HBITMAP
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT, ctypes.c_void_p]
gdi32.CreateBitmap.restype = wt.HBITMAP
gdi32.DeleteObject.argtypes = [wt.HANDLE]
kernel32.GetModuleHandleW.restype = wt.HMODULE
kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
kernel32.CloseHandle.argtypes = [wt.HANDLE]


# --- configuracao ---------------------------------------------------------

def load_config():
    cfg = {"fechar_gmenu": True, "leds_desligados": False}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError as e:
        bridge.log(f"Nao foi possivel salvar {CONFIG_FILE}: {e}")


# --- iniciar com o Windows ------------------------------------------------

def _startup_command():
    if getattr(sys, "frozen", False):  # versao instalada (.exe)
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'


def _old_startup_lnk():
    startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.join(startup, OLD_STARTUP_LNK)


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return os.path.exists(_old_startup_lnk())


def set_startup(enabled):
    # remove o atalho antigo para nao abrir duas vezes
    try:
        os.remove(_old_startup_lnk())
    except OSError:
        pass
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    bridge.log(f"Iniciar com o Windows: {'ligado' if enabled else 'desligado'}")


# --- G-Menu -----------------------------------------------------------------

def find_gmenu():
    pids = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == wt.HANDLE(-1).value:
        return pids
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() in GMENU_EXES:
                pids.append(entry.th32ProcessID)
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return pids


def kill_gmenu():
    """Fecha o G-Menu. Retorna (fechados, sem_permissao)."""
    killed = denied = 0
    for pid in find_gmenu():
        handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if handle and kernel32.TerminateProcess(handle, 0):
            killed += 1
        else:
            denied += 1
        if handle:
            kernel32.CloseHandle(handle)
    if killed:
        bridge.log(f"G-Menu fechado ({killed} processo(s))")
    if denied:
        bridge.log(f"Sem permissao para fechar {denied} processo(s) do G-Menu")
    return killed, denied


# --- icone ------------------------------------------------------------------

def make_icon(color):
    """Cria um icone redondo com a cor dada (ou um anel cinza se None/preto)."""
    size = user32.GetSystemMetrics(SM_CXSMICON) or 16
    r, g, b = color if color else (0, 0, 0)
    off = max(r, g, b) < 8
    center = (size - 1) / 2
    radius = size / 2 - 0.5
    border = max(1.0, size / 16)
    pixels = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            d = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            alpha = min(1.0, max(0.0, radius - d + 0.5))
            if alpha <= 0:
                continue
            on_border = d > radius - border
            if off:
                pr, pg, pb = (150, 150, 150)
                if not on_border:
                    alpha *= 0.15
            elif on_border:
                pr, pg, pb = (r * 3 // 5, g * 3 // 5, b * 3 // 5)
            else:
                pr, pg, pb = (r, g, b)
            i = (y * size + x) * 4
            pixels[i:i + 4] = bytes((pb, pg, pr, int(alpha * 255)))

    bmi = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=size,
                           biHeight=-size, biPlanes=1, biBitCount=32)
    bits = ctypes.c_void_p()
    color_bmp = gdi32.CreateDIBSection(None, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    ctypes.memmove(bits, bytes(pixels), len(pixels))
    mask = (ctypes.c_ubyte * (((size + 15) // 16) * 2 * size))()
    mask_bmp = gdi32.CreateBitmap(size, size, 1, 1, mask)
    info = ICONINFO(fIcon=True, hbmMask=mask_bmp, hbmColor=color_bmp)
    icon = user32.CreateIconIndirect(ctypes.byref(info))
    gdi32.DeleteObject(color_bmp)
    gdi32.DeleteObject(mask_bmp)
    return icon


class Tray:
    def __init__(self):
        self.cfg = load_config()
        bridge.status["desligado"] = bool(self.cfg["leds_desligados"])
        self.icon = None
        self.icon_color = "inicial"
        self.tip = ""
        self.msg_taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        self._wndproc = WNDPROC(self._on_message)  # manter referencia viva
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._wndproc, hInstance=hinst, lpszClassName="AocLightFxTray")
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, wc.lpszClassName, APP_NAME, 0, 0, 0, 0, 0,
                                           None, None, hinst, None)
        self._notify(NIM_ADD)
        self.refresh()
        user32.SetTimer(self.hwnd, 1, 1000, None)

    def _nid(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self.hwnd
        nid.uID = 1
        return nid

    def _notify(self, action):
        nid = self._nid()
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.icon or make_icon(None)
        if not self.icon:
            self.icon = nid.hIcon
        nid.szTip = self.tip or APP_NAME
        shell32.Shell_NotifyIconW(action, ctypes.byref(nid))

    def balloon(self, title, text):
        nid = self._nid()
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = title
        nid.szInfo = text
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def status_text(self):
        st = bridge.status
        if not st["monitor"]:
            return "Procurando o monitor AOC..."
        if st["desligado"]:
            return "LEDs desligados"
        if time.time() - st["ultimo_pacote"] > RECEIVING_TIMEOUT:
            return "Aguardando o SignalRGB"
        return "Recebendo cores do SignalRGB"

    def refresh(self):
        st = bridge.status
        receiving = time.time() - st["ultimo_pacote"] <= RECEIVING_TIMEOUT and not st["desligado"]
        color = st["cor"] if receiving else None
        tip = f"{APP_NAME}\n{self.status_text()}"[:127]
        if color == self.icon_color and tip == self.tip:
            return
        old = None
        if color != self.icon_color:
            old, self.icon = self.icon, make_icon(color)
            self.icon_color = color
        self.tip = tip
        self._notify(NIM_MODIFY)
        if old:
            user32.DestroyIcon(old)

    def show_menu(self):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, self.status_text())
        if bridge.status["monitor"]:
            user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, bridge.status["monitor"])
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING | (MF_CHECKED if self.cfg["leds_desligados"] else 0),
                           CMD_LEDS_OFF, "Desligar LEDs")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING | (MF_CHECKED if startup_enabled() else 0),
                           CMD_STARTUP, "Iniciar com o Windows")
        user32.AppendMenuW(menu, MF_STRING | (MF_CHECKED if self.cfg["fechar_gmenu"] else 0),
                           CMD_AUTO_GMENU, "Fechar o G-Menu automaticamente")
        user32.AppendMenuW(menu, MF_STRING, CMD_KILL_GMENU, "Fechar o G-Menu agora")
        user32.AppendMenuW(menu, MF_STRING, CMD_LOG, "Abrir log")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, CMD_EXIT, "Sair")

        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_NONOTIFY | TPM_RETURNCMD,
                                    pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
        self.run_command(cmd)

    def run_command(self, cmd):
        if cmd == CMD_LEDS_OFF:
            self.cfg["leds_desligados"] = not self.cfg["leds_desligados"]
            save_config(self.cfg)
            bridge.status["desligado"] = self.cfg["leds_desligados"]
            self.refresh()
        elif cmd == CMD_STARTUP:
            try:
                set_startup(not startup_enabled())
            except OSError as e:
                self.balloon(APP_NAME, f"Nao foi possivel alterar a inicializacao: {e}")
        elif cmd == CMD_AUTO_GMENU:
            self.cfg["fechar_gmenu"] = not self.cfg["fechar_gmenu"]
            save_config(self.cfg)
            if self.cfg["fechar_gmenu"]:
                kill_gmenu()
        elif cmd == CMD_KILL_GMENU:
            killed, denied = kill_gmenu()
            if denied:
                self.balloon("G-Menu", "Sem permissao para fechar o G-Menu. Feche-o manualmente.")
            elif killed:
                self.balloon("G-Menu", "G-Menu fechado.")
            else:
                self.balloon("G-Menu", "O G-Menu nao estava aberto.")
        elif cmd == CMD_LOG:
            if os.path.exists(bridge.LOG_FILE):
                os.startfile(bridge.LOG_FILE)
        elif cmd == CMD_EXIT:
            user32.DestroyWindow(self.hwnd)

    def _on_message(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY and lparam in (WM_LBUTTONUP, WM_RBUTTONUP):
            self.show_menu()
            return 0
        if msg == WM_TIMER:
            self.refresh()
            return 0
        if msg == self.msg_taskbar_created:  # Explorer reiniciou: recoloca o icone
            self._notify(NIM_ADD)
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid()))
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def loop(self):
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


def run_bridge(sock):
    try:
        bridge.main(sock)
    except Exception as e:
        bridge.log(f"Ponte parou: {e}")


def gmenu_watcher(cfg):
    while True:
        if cfg["fechar_gmenu"]:
            kill_gmenu()
        time.sleep(GMENU_CHECK_INTERVAL)


def main():
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)  # icone nitido em telas com escala
    except (OSError, AttributeError):
        pass
    try:
        sock = bridge.open_socket()
    except OSError:
        user32.MessageBoxW(None, "A ponte do AOC Light FX ja esta rodando.", APP_NAME, MB_ICONWARNING)
        return
    bridge.log("Icone da bandeja iniciado")
    tray = Tray()
    threading.Thread(target=run_bridge, args=(sock,), daemon=True).start()
    threading.Thread(target=gmenu_watcher, args=(tray.cfg,), daemon=True).start()
    tray.loop()
    bridge.log("Encerrado pelo icone da bandeja")


if __name__ == "__main__":
    main()
