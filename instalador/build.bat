@echo off
rem Gera o instalador instalador\Output\AOC-LightFX-Setup-x.y.z.exe
rem Requer Python 3.8+ e Inno Setup 6 (winget install JRSoftware.InnoSetup)
setlocal
cd /d "%~dp0.."

python -m pip install --quiet --upgrade pyinstaller pillow || goto :erro
python instalador\gerar_icone.py || goto :erro
python -m PyInstaller --noconfirm --clean --windowed --name "AOC Light FX" --icon instalador\icone.ico aoc_lightfx_tray.py || goto :erro

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo Inno Setup 6 nao encontrado. & goto :erro)
"%ISCC%" instalador\AOC_LightFX.iss || goto :erro

echo.
echo Instalador pronto na pasta instalador\Output
pause
exit /b 0

:erro
echo Falha ao gerar o instalador.
pause
exit /b 1
