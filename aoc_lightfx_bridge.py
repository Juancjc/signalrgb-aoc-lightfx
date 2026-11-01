"""Ponte UDP -> DDC/CI para o Light FX do monitor AOC.

O plugin do SignalRGB envia, para 127.0.0.1:21330, pacotes:
    'A' 'O' 'C' fgR fgG fgB bgR bgG bgB intensidade [efeito]
e esta ponte grava no monitor somente os canais que mudaram. O efeito e um
indice de aoc_lightfx.EFFECTS; sem ele (plugin antigo) usa o Static.
"""
import os
import socket
import sys
import time

import aoc_lightfx as fx

HOST, PORT = "127.0.0.1", 21330
CHECK_INTERVAL = 15.0  # segundos entre verificacoes de modo (OSD/power-cycle podem resetar)
VERIFY_INTERVAL = 1.0  # cada leitura ocupa o barramento ~0,2 s
# Ordem de gravacao: fundo primeiro, porque e a cor que o Static mostra. Cada
# escrita leva 0,12 s, entao o fundo completo chega em ~0,4 s.
CODES = (fx.BG_R, fx.BG_G, fx.BG_B, fx.FG_R, fx.FG_G, fx.FG_B)


# pasta do programa: a do .exe quando instalado (PyInstaller), senao a deste script
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "ponte.log")

# estado atual, lido pelo icone da bandeja (aoc_lightfx_tray.py)
# "desligado" e escrito pelo icone da bandeja: com ele ligado a ponte apaga os LEDs
# e ignora as cores do SignalRGB ate ser religada
status = {"monitor": None, "cor": None, "ultimo_pacote": 0.0, "desligado": False}


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
            mon = fx.AocLightFx()
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
    effect = None
    mode_seen = None     # valor lido do 0x61 logo apos ativar o efeito
    target = None
    last_check = 0.0
    last_verify = 0.0
    verify_idx = 0
    leds_off = False     # 0x60 = 0 ja confirmado pelo monitor
    next_off_check = 0.0

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
                    target = bytes(data[3:11]) if len(data) >= 11 else bytes(data[3:10]) + b"\x00"
                    status["cor"] = tuple(target[:3])
                    status["ultimo_pacote"] = time.time()
                sock.setblocking(False)
        except (socket.timeout, BlockingIOError):
            pass
        except OSError:
            pass

        now = time.time()
        try:
            if status["desligado"]:
                # apaga e confere de tempos em tempos (o OSD ou um power-cycle podem religar)
                if now >= next_off_check:
                    current = mon.get(fx.LIGHTFX)
                    if (current is not None and current[0] == 0) or mon.turn_off():
                        if not leds_off:
                            log("LEDs desligados")
                        leds_off = True
                        next_off_check = now + CHECK_INTERVAL
                    else:
                        log("Falha ao desligar os LEDs; tentando de novo")
                        next_off_check = now + 2
                    # ao religar, o efeito e as cores sao gravados de novo
                    intensity = effect = None
                    sent.clear()
                continue
            if leds_off:
                leds_off = False
                next_off_check = 0.0
                log("LEDs religados")

            if target is None:
                continue

            want_intensity = min(target[6], 3)
            want_effect = target[7] if target[7] < len(fx.EFFECTS) else 0
            changed = intensity != want_intensity or effect != want_effect
            if changed or now - last_check > CHECK_INTERVAL:
                lost = False
                if not changed:
                    # o OSD ou um power-cycle do monitor podem trocar o modo;
                    # leitura que falhou nao conta, para nao reiniciar a animacao a toa
                    pattern = mon.get(fx.PATTERN)
                    mode = mon.get(fx.LIGHTFX_MODE)
                    lost = ((pattern is not None and pattern[0] != fx.PATTERN_USER)
                            or (mode is not None and mode_seen is not None and mode[0] != mode_seen))
                    if lost:
                        log(f"Monitor saiu do efeito (pattern={pattern}, modo={mode}, antes={mode_seen})")
                if changed or lost:
                    mode_index = mon.prepare_user_color(want_intensity, want_effect)
                    intensity, effect = want_intensity, want_effect
                    sent.clear()
                    # o 0x61 lido nem sempre bate com o indice gravado (no AG323FWG3R3
                    # fica no ultimo modo usado pelo OSD); compara com o que ele responde agora
                    seen = mon.get(fx.LIGHTFX_MODE)
                    mode_seen = seen[0] if seen else None
                    if mode_index is None:
                        mode_seen = -1  # forca nova tentativa na proxima verificacao
                        log("Falha ao ativar o efeito; tentando de novo na proxima verificacao")
                    else:
                        log(f"Efeito {fx.EFFECTS[effect]} ativado (modo {mode_index}, intensidade {intensity})")
                last_check = now

            for code, value in zip(CODES, target[3:6] + target[:3]):
                scaled = mon._scale(value)
                if sent.get(code) != scaled:
                    if not mon.set(code, scaled):
                        raise OSError("falha na escrita I2C")
                    sent[code] = scaled
                    break  # um canal por volta, para sempre pegar a cor mais recente

            # Rele um canal por vez para achar escritas DDC perdidas (outro programa no
            # barramento, monitor ocupado logo apos trocar de modo). Roda mesmo com a cor
            # mudando: se esperasse ficar ocioso, um canal perdido nunca seria corrigido
            # enquanto o SignalRGB anima, e o monitor ficava preso na cor antiga.
            # So no Static: nos efeitos animados a leitura pode atrapalhar a animacao.
            if effect == 0 and now - last_verify > VERIFY_INTERVAL:
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
            intensity = effect = None
            leds_off = False  # confere de novo, o monitor pode ter sido religado
            next_off_check = 0.0


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
