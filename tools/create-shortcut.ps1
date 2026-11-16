<#
.SYNOPSIS
Creates a SurroSim desktop shortcut for the current user.

.DESCRIPTION
Points a shortcut at start-desktop.bat in the repository root. Use -StartMenu
to place it in the Start Menu instead of the desktop.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File tools\create-shortcut.ps1
powershell -ExecutionPolicy Bypass -File tools\create-shortcut.ps1 -StartMenu
#>
param(
    [switch]$StartMenu
)

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$target = Join-Path $root "start-desktop.bat"

if (-not (Test-Path $target)) {
    Write-Error "Launcher not found at $target"
    exit 1
}

if ($StartMenu) {
    $programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $linkPath = Join-Path $programs "SurroSim.lnk"
} else {
    $linkPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "SurroSim.lnk"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $root
$shortcut.Description = "SurroSim desktop workbench"
$shortcut.Save()

Write-Host "Shortcut created: $linkPath"
