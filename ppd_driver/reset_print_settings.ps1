# Resets the print settings (Resolution, Halftoning, Toner Density, Toner Saver,
# Automatic Image Refinement, Brightness, Contrast, paper size, ...) of the Canon LBP-1120
# queues to the driver defaults: both the per-user settings and the system-wide printer
# defaults (Windows Settings -> Printing preferences stores them there).
# Asks for administrator rights itself. ASCII only (Windows PowerShell 5.1 reads scripts as ANSI).
$ErrorActionPreference = "Stop"
$driverName = "Canon LBP-1120 (CAPT)"
$oldDriver  = "MS Publisher Imagesetter"
$queues     = @("Canon LBP-1120", "Canon LBP-1120 (sharp text)")

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Wait
    exit
}

$key = "HKCU:\Printers\DevModePerUser"
$done = @()
try {
    foreach ($q in $queues) {
        $pr = Get-Printer -Name $q -ErrorAction SilentlyContinue
        if (-not $pr) { continue }
        # 1) per-user settings
        if (Test-Path $key) {
            if (Get-ItemProperty -Path $key -Name $q -ErrorAction SilentlyContinue) {
                Remove-ItemProperty -Path $key -Name $q
            }
        }
        # 2) system-wide defaults: switching the driver and back restores the driver defaults
        if ($pr.DriverName -eq $driverName) {
            Set-Printer -Name $q -DriverName $oldDriver
            Set-Printer -Name $q -DriverName $driverName
        }
        $done += $q
    }
    if ($done.Count) {
        Write-Host "Reset to defaults:" -ForegroundColor Green
        $done | ForEach-Object { Write-Host "  $_" }
        Write-Host "Close open print dialogs and open them again to see the default values."
    } else {
        Write-Host "Canon LBP-1120 queues not found." -ForegroundColor Yellow
    }
}
catch {
    Write-Host ("FAILED: " + $_.Exception.Message) -ForegroundColor Red
}
Start-Sleep -Seconds 4
