$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv-build\Scripts\python.exe')) {
    python -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the build environment.' }
}
$buildPython = Join-Path $PSScriptRoot '.venv-build\Scripts\python.exe'
& $buildPython -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install build tools.' }
& $buildPython -B assets_icon.py
if ($LASTEXITCODE -ne 0) { throw 'Could not generate the application icon.' }
& $buildPython -m PyInstaller --noconfirm --onefile --windowed --name NeonCyberHub --icon assets\neon-hub.ico script.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
Write-Output 'Ready: dist\NeonCyberHub.exe'

