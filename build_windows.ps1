# Compatibility launcher; build scripts live under scripts/.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts\build_windows.ps1') @args
