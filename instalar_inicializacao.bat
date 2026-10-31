@echo off
rem Opcional: faz a ponte AOC Light FX (com o icone na bandeja) abrir junto com o Windows.
rem Tambem da para ligar/desligar isso pelo menu do icone.
cd /d "%~dp0"
python -c "import aoc_lightfx_tray as t; t.set_startup(True); print('Pronto: a ponte vai abrir junto com o Windows.')"
pause
