@echo off
rem Opcional: cria um atalho na pasta Inicializar para a ponte AOC Light FX abrir junto com o Windows
powershell -NoProfile -Command "$pyw = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'; $lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'AOC Light FX Ponte.lnk'; $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); $s.TargetPath = $pyw; $s.Arguments = '\"%~dp0aoc_lightfx_bridge.py\"'; $s.WorkingDirectory = '%~dp0'; $s.Save(); Write-Host 'Atalho criado:' $lnk"
pause
