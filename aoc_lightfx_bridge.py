"""Ponte UDP -> DDC/CI para o Light FX do monitor AOC.

O plugin do SignalRGB envia, para 127.0.0.1:21330, pacotes:
    'A' 'O' 'C' fgR fgG fgB bgR bgG bgB intensidade
e esta ponte grava no monitor somente os canais que mudaram.
"""
import os
import socket
import sys
import time

import aoc_lightfx as fx

HOST, PORT = "127.0.0.1", 21330
CHECK_INTERVAL = 15.0  # segundos entre verificacoes de modo (OSD/power-cycle podem resetar)
VERIFY_INTERVAL = 0.3
CODES =(fx.FG_R, fx.FG_G, fx.FG_B, fx.BG_R, fx.BG_G, fx.BG_B)


# pasta do programa: a do .exe quando instalado (PyInstaller), senao a deste script
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "ponte.log")

# estado atual, lido pelo icone da bandeja (aoc_lightfx_tray.py)
status = {"monitor": None, "cor": None, "ultimo_pacote": 0.0}


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def connect():
    while True:
        try:
            mon = fx.AocLightFx(write_delay=0.03)
            log(f"Monitor encontrado: {mon.monitor_name}")
            status["monitor"] = mon.monitor_name
            return mon
        except Exception as e:  # monitor desligado, driver reiniciando etc.
            status["monitor"] = None
            log(f"Aguardando monitor: {e}")
            time.sleep(5)


def open_socket():
    """Abre a porta UDP; falha com OSError se outra ponte ja estiver rodando."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    log(f"Escutando em udp://{HOST}:{PORT}")
    return sock


def main(sock=None):
    if sock is None:
        sock = open_socket()

    mon = connect()
    sent = {}            # codigo -> valor ja gravado no monitor
    intensity = None
    target = None
    last_check = 0.0
    last_verify = 0.0
    verify_idx = 0

    while True:
        # espera ate 20 ms por um pacote e depois esvazia a fila sem bloquear,
        # ficando so com o mais recente
        sock.settimeout(0.02)
        try:
            while True:
                data, _ = sock.recvfrom(64)
                if len(data) >= 10 and data[:3] == b"AOC":
                    if target is None:
                        log(f"Recebendo cores do SignalRGB: {list(data[3:10])}")
                    target = data[3:10]
                    status["cor"] = tuple(target[:3])
                    status["ultimo_pacote"] = time.time()
                sock.setblocking(False)
        except (socket.timeout, BlockingIOError):
            pass
        except OSError:
            pass

        now = time.time()
        try:
            if target is None:
                continue

            want_intensity = min(target[6], 3)
            if intensity != want_intensity or now - last_check > CHECK_INTERVAL:
                pattern = mon.get(fx.PATTERN)
                if intensity != want_intensity or not pattern or pattern[0] != fx.PATTERN_USER:
                    mon.prepare_user_color(want_intensity)
                    intensity = want_intensity
                    sent.clear()
                    log(f"Modo Static/cor personalizada ativado (intensidade {intensity})")
                last_check = now

            pending = False
            for code, value in zip(CODES, target[:6]):
                scaled = mon._scale(value)
                if sent.get(code) != scaled:
                    if not mon.set(code, scaled):
                        raise OSError("falha na escrita I2C")
                    sent[code] = scaled
                    pending = True
                    break  # um canal por volta, para sempre pegar a cor mais recente

            # Ocioso: rele um canal por vez; escritas DDC podem se perder se outro
            # programa (ex.: G-Menu) usar o barramento ao mesmo tempo.
            if not pending and now - last_verify > VERIFY_INTERVAL:
                code = CODES[verify_idx]
                verify_idx = (verify_idx + 1) % len(CODES)
                current = mon.get(code)
                if current and current[0] != sent.get(code):
                    sent.pop(code, None)
                last_verify = now
        except Exception as e:
            log(f"Erro: {e}; reconectando")
            time.sleep(2)
            mon = connect()
            sent.clear()
            intensity = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
