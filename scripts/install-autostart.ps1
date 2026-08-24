param(
    [switch]$Remove
)

$AppName = "FRIDAY"
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$Root = Split-Path -Parent $PSScriptRoot
$StartScript = Join-Path $Root "scripts\launch-friday.vbs"

if ($Remove) {
    Remove-ItemProperty -Path $RunKey -Name $AppName -ErrorAction SilentlyContinue
    Write-Host "Autostart removed for $AppName"
    exit 0
}

if (-not (Test-Path $StartScript)) {
    Write-Error "Start script not found: $StartScript"
    exit 1
}

Set-ItemProperty -Path $RunKey -Name $AppName -Value "`"$env:SystemRoot\System32\wscript.exe`" `"$StartScript`""
Write-Host "Autostart enabled for $AppName"
Write-Host "Entry: wscript.exe `"$StartScript`""
