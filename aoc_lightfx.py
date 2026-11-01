"""Controle do Light FX de monitores AOC (AGON) via DDC/CI usando I2C da NVAPI.

Protocolo extraído do G-Menu (DDCHelperLib / Zeasn.DDC.Lib):
    I2C 0x37:  51 86 03 F8 E1 <codigo> <valor_hi> <valor_lo> <checksum>
    checksum = 0x6E XOR todos os bytes anteriores
"""
import ctypes
import time
from ctypes import POINTER, Structure, byref, c_int, c_ubyte, c_uint32, c_void_p

LIGHTFX = 0x60          # 0 desligado, 1 baixo, 2 medio, 3 forte
LIGHTFX_MODE = 0x61     # indice na lista de modos (ver MODE_LISTS)
PATTERN = 0x62          # 4 = definido pelo usuario
FG_R, FG_G, FG_B = 0x63, 0x64, 0x65
BG_R, BG_G, BG_B = 0x66, 0x67, 0x68

PATTERN_USER = 4

# Intervalo minimo entre escritas DDC. Medido no AG323FWG3R3: com 100 ms ou menos o
# monitor descarta uma escrita sim, outra nao (a NVAPI responde sucesso mesmo assim);
# com 110 ms nenhuma se perde.
WRITE_DELAY = 0.12
# Depois de trocar intensidade/modo/padrao o monitor fica ocupado mais tempo
# (escrita no 0x61 logo apos o 0x60 se perde com 0,12 s; com 0,3 s pega).
SETTLE_DELAY = 0.4

# Efeitos que o plugin pode pedir (o codigo e o indice nesta lista).
EFFECTS = ["Static", "SimpleShift", "GradientShift", "SimpleFilling", "1WayFilling", "2WayFilling",
           "Breathing", "MotionPoint", "Zoom", "Discolor", "WaterWave", "Flashing"]

# Lista de modos do monitor, escolhida pelo maximo do codigo 0x61
# (enums LightFXMode_C/D/E/F/10 do G-Menu; o valor e a posicao na lista).
_LIST_C = ["Static", "SimpleShift", "GradientShift", "SimpleFilling", "1WayFilling", "2WayFilling",
           "Breathing", "MotionPoint", "Zoom", "Discolor", "WaterWave", "Flashing", "Demo"]
_LIST_E = ["Audio1", "Audio2", "Static", "DarkPointSweep", "GradientShift", "Spread_Fill", "DripFill",
           "SpreadingDripFill", "Breathing", "LightPointSweep", "Zoom", "Rainbow", "Wave", "Flashing", "Demo"]
MODE_LISTS = {
    12: _LIST_C,
    13: ["Audio"] + _LIST_C,
    14: _LIST_E,
    15: ["LOL"] + _LIST_E,
    16: ["CS"] + _LIST_E,
}
# Nas listas novas alguns efeitos mudaram de nome; usa o equivalente mais proximo.
_EQUIVALENT = {"SimpleShift": "DarkPointSweep", "SimpleFilling": "Spread_Fill", "1WayFilling": "DripFill",
               "2WayFilling": "SpreadingDripFill", "MotionPoint": "LightPointSweep", "Discolor": "GradientShift",
               "WaterWave": "Wave"}


def mode_index(mode_max, effect=0):
    """Indice do registro 0x61 para o efeito pedido, ou o do Static se nao existir."""
    modes = MODE_LISTS.get(mode_max, _LIST_C)
    name = EFFECTS[effect] if 0 <= effect < len(EFFECTS) else "Static"
    for candidate in (name, _EQUIVALENT.get(name), "Static"):
        if candidate in modes:
            return modes.index(candidate)
    return 0

_NVAPI_INITIALIZE = 0x0150E828
_NVAPI_ENUM_PHYSICAL_GPUS = 0xE5AC921F
_NVAPI_GET_CONNECTED_DISPLAY_IDS = 0x0078DBA2
_NVAPI_I2C_WRITE = 0xE812EB07
_NVAPI_I2C_READ = 0x2FDE12C5
_NVAPI_GET_DISPLAY_ID_BY_NAME = 0xAE457190


class _NvI2cInfoV3(Structure):
    _fields_ = [
        ("version", c_uint32),
        ("displayMask", c_uint32),
        ("bIsDDCPort", c_ubyte),
        ("i2cDevAddress", c_ubyte),
        ("pbI2cRegAddress", POINTER(c_ubyte)),
        ("regAddrSize", c_uint32),
        ("pbData", POINTER(c_ubyte)),
        ("cbSize", c_uint32),
        ("i2cSpeed", c_uint32),
        ("i2cSpeedKhz", c_uint32),
        ("portId", c_ubyte),
        ("bIsPortIdSet", c_uint32),
    ]


class _NvGpuDisplayIds(Structure):
    _fields_ = [
        ("version", c_uint32),
        ("connectorType", c_uint32),
        ("displayId", c_uint32),
        ("flags", c_uint32),
    ]


class NvApi:
    def __init__(self):
        self._dll = ctypes.WinDLL("nvapi64.dll")
        query = self._dll.nvapi_QueryInterface
        query.restype = c_void_p
        query.argtypes = [c_uint32]

        def fn(fid, *argtypes):
            ptr = query(fid)
            if not ptr:
                raise OSError(f"NVAPI funcao 0x{fid:08X} indisponivel")
            return ctypes.CFUNCTYPE(c_int, *argtypes)(ptr)

        fn(_NVAPI_INITIALIZE)()
        self._enum_gpus = fn(_NVAPI_ENUM_PHYSICAL_GPUS, POINTER(c_void_p * 64), POINTER(c_uint32))
        self._get_display_ids = fn(_NVAPI_GET_CONNECTED_DISPLAY_IDS, c_void_p, c_void_p, POINTER(c_uint32), c_uint32)
        self._i2c_write = fn(_NVAPI_I2C_WRITE, c_void_p, POINTER(_NvI2cInfoV3))
        self._i2c_read = fn(_NVAPI_I2C_READ, c_void_p, POINTER(_NvI2cInfoV3))
        self._id_by_name = fn(_NVAPI_GET_DISPLAY_ID_BY_NAME, ctypes.c_char_p, POINTER(c_uint32))

    def display_id_by_name(self, gdi_name):
        disp = c_uint32(0)
        if self._id_by_name(gdi_name.encode("ascii"), byref(disp)) != 0:
            return None
        return disp.value

    def gpus(self):
        handles = (c_void_p * 64)()
        count = c_uint32(0)
        if self._enum_gpus(byref(handles), byref(count)) != 0:
            return []
        return [handles[i] for i in range(count.value)]

    def display_ids(self, gpu):
        count = c_uint32(0)
        if self._get_display_ids(gpu, None, byref(count), 0) != 0 or count.value == 0:
            return []
        arr = (_NvGpuDisplayIds * count.value)()
        for item in arr:
            item.version = ctypes.sizeof(_NvGpuDisplayIds) | (3 << 16)
        if self._get_display_ids(gpu, arr, byref(count), 0) != 0:
            return []
        return [arr[i].displayId for i in range(count.value)]

    def _info(self, display_id, addr, reg, data):
        info = _NvI2cInfoV3()
        info.version = ctypes.sizeof(_NvI2cInfoV3) | (3 << 16)
        info.displayMask = display_id
        info.bIsDDCPort = 1
        info.i2cDevAddress = addr
        info.pbI2cRegAddress = ctypes.cast(reg, POINTER(c_ubyte))
        info.regAddrSize = len(reg)
        info.pbData = ctypes.cast(data, POINTER(c_ubyte))
        info.cbSize = len(data)
        info.i2cSpeed = 0xFFFF
        return info

    def i2c_write(self, gpu, display_id, addr, reg, payload):
        reg_buf = (c_ubyte * len(reg))(*reg)
        data_buf = (c_ubyte * len(payload))(*payload)
        info = self._info(display_id, addr, reg_buf, data_buf)
        return self._i2c_write(gpu, byref(info))

    def i2c_read(self, gpu, display_id, addr, reg, size):
        reg_buf = (c_ubyte * len(reg))(*reg)
        data_buf = (c_ubyte * size)()
        info = self._info(display_id, addr, reg_buf, data_buf)
        status = self._i2c_read(gpu, byref(info))
        return status, bytes(data_buf)


class _DisplayDevice(Structure):
    _fields_ = [
        ("cb", c_uint32),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", c_uint32),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


def _windows_monitors():
    """Lista (\\\\.\\DISPLAYn, MONITOR\\<PNPID>\\...) dos monitores ativos."""
    enum = ctypes.windll.user32.EnumDisplayDevicesW
    result = []
    i = 0
    while True:
        adapter = _DisplayDevice(cb=ctypes.sizeof(_DisplayDevice))
        if not enum(None, i, byref(adapter), 0):
            break
        i += 1
        j = 0
        while True:
            mon = _DisplayDevice(cb=ctypes.sizeof(_DisplayDevice))
            if not enum(adapter.DeviceName, j, byref(mon), 0):
                break
            j += 1
            if mon.StateFlags & 1:  # DISPLAY_DEVICE_ACTIVE
                result.append((adapter.DeviceName, mon.DeviceID))
    return result


class AocLightFx:
    def __init__(self, name_filter="AOC", write_delay=WRITE_DELAY):
        self.nv = NvApi()
        self.write_delay = write_delay
        self._last_access = 0.0
        self.gpu = self.display = None
        self.monitor_name = None
        self.color_max = 100
        for gdi_name, monitor_id in _windows_monitors():
            if name_filter.upper() not in monitor_id.upper():
                continue
            disp = self.nv.display_id_by_name(gdi_name)
            if disp is None:
                continue
            for gpu in self.nv.gpus():
                if disp in self.nv.display_ids(gpu):
                    self.gpu, self.display = gpu, disp
                    self.monitor_name = f"{monitor_id} em {gdi_name}"
                    return
        raise RuntimeError(f"Monitor '{name_filter}' nao encontrado via NVAPI")

    def set(self, code, value):
        frame = [0x51, 0x86, 0x03, 0xF8, 0xE1, code, (value >> 8) & 0xFF, value & 0xFF]
        chk = 0x6E
        for b in frame:
            chk ^= b
        self._pace()
        status = self.nv.i2c_write(self.gpu, self.display, 0x6E, frame[:1], frame[1:] + [chk])
        self._last_access = time.monotonic()
        if code in (LIGHTFX, LIGHTFX_MODE, PATTERN):
            self._last_access += SETTLE_DELAY - self.write_delay
        return status == 0

    def _pace(self):
        """Espera o intervalo minimo desde o ultimo acesso ao barramento (escrita ou leitura)."""
        wait = self.write_delay - (time.monotonic() - self._last_access)
        if wait > 0:
            time.sleep(wait)

    def get_raw(self, code, size=12):
        frame = [0x51, 0x84, 0x01, 0xF8, 0xE1, code]
        chk = 0x6E
        for b in frame:
            chk ^= b
        self._pace()
        self.nv.i2c_write(self.gpu, self.display, 0x6E, frame[:1], frame[1:] + [chk])
        time.sleep(0.05)
        status, data = self.nv.i2c_read(self.gpu, self.display, 0x6F, [], size)
        self._last_access = time.monotonic()
        return status, data

    def get(self, code):
        """Retorna (atual, maximo) ou None. Resposta: 6E 88 02 00 F8 <cod> maxH maxL curH curL chk."""
        for _ in range(3):
            status, d = self.get_raw(code)
            if status == 0 and len(d) >= 10 and d[1] == 0x88 and d[4] == 0xF8 and d[5] == code:
                return (d[8] << 8) | d[9], (d[6] << 8) | d[7]
            time.sleep(0.1)
        return None

    def prepare_user_color(self, intensity=3, effect=0):
        """Liga o Light FX no efeito pedido usando as cores personalizadas.

        Retorna o indice gravado no registro 0x61, ou None se alguma escrita falhou.
        """
        # O indice depende da lista de modos do monitor (G-Menu escolhe pelo maximo do 0x61)
        mode = self.get(LIGHTFX_MODE)
        index = mode_index(mode[1] if mode else 12, effect)
        color = self.get(FG_R)
        self.color_max = color[1] if color and color[1] else 100
        # escritas que o monitor descarta nao dao erro: confere lendo de volta
        for code, value in ((LIGHTFX, intensity), (LIGHTFX_MODE, index), (PATTERN, PATTERN_USER)):
            for _ in range(3):
                self.set(code, value)
                got = self.get(code)
                if got and got[0] == value:
                    break
            else:
                return None
        return index

    def turn_off(self):
        """Desliga o Light FX (0x60 = 0). Retorna True se o monitor confirmou."""
        for _ in range(3):
            self.set(LIGHTFX, 0)
            got = self.get(LIGHTFX)
            if got and got[0] == 0:
                return True
        return False

    def _scale(self, v):
        return round(max(0, min(255, v)) * self.color_max / 255)

    def set_foreground(self, r, g, b):
        r, g, b = (self._scale(v) for v in (r, g, b))
        return self.set(FG_R, r) & self.set(FG_G, g) & self.set(FG_B, b)

    def set_background(self, r, g, b):
        r, g, b = (self._scale(v) for v in (r, g, b))
        return self.set(BG_R, r) & self.set(BG_G, g) & self.set(BG_B, b)


if __name__ == "__main__":
    import sys

    mon = AocLightFx()
    print(f"Monitor: {mon.monitor_name} (displayId 0x{mon.display:08X})")
    if len(sys.argv) >= 4:
        r, g, b = (int(x) for x in sys.argv[1:4])
        print("prepare:", mon.prepare_user_color())
        print("foreground:", mon.set_foreground(r, g, b))
        print("background:", mon.set_background(r, g, b))
