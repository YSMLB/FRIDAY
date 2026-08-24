$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Vbs = Join-Path $PSScriptRoot "launch-friday.vbs"
$Link = Join-Path ([Environment]::GetFolderPath("Desktop")) "FRIDAY.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$Sc = $Wsh.CreateShortcut($Link)
$Sc.TargetPath = "$env:SystemRoot\System32\wscript.exe"
$Sc.Arguments = "`"$Vbs`""
$Sc.WorkingDirectory = $Root
$Sc.WindowStyle = 7
$Sc.Description = "FRIDAY desktop assistant"
$Ico = Join-Path $Root "apps\desktop\public\icon.ico"
if (Test-Path $Ico) { $Sc.IconLocation = $Ico }
$Sc.Save()
Write-Host "Shortcut: $Link"
