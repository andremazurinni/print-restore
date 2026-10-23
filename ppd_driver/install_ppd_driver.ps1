# Installs the "Canon LBP-1120 (CAPT)" PostScript driver package (custom PPD with
# quality options) and switches the existing Canon LBP-1120 print queues to it.
# Run:  right click -> "Run with PowerShell"   (asks for administrator rights itself)
# Roll back to the old driver:  install_ppd_driver.ps1 -Rollback
# -Silent: no "Press Enter" prompt (used by setup.ps1)
# ASCII only (Windows PowerShell 5.1 reads scripts as ANSI).
param([switch]$Rollback, [switch]$Silent)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage) } catch {}
$driverName = "Canon LBP-1120 (CAPT)"
$oldDriver  = "MS Publisher Imagesetter"
$queues     = @("Canon LBP-1120", "Canon LBP-1120 (sharp text)")
# per-printer queues "Canon LBP-1120 (SERIAL)" (created by setup.ps1 when two printers are connected) use the same driver
foreach ($pr in @(Get-Printer -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'Canon LBP-1120 (*)' -or $_.Name -like 'Canon LBP-810*' })) {
    if ($queues -notcontains $pr.Name) { $queues += $pr.Name }
}
$here       = Split-Path -Parent $MyInvocation.MyCommand.Path
# Windows 8.1 and older (pre-Windows 10 1607): pnputil only has the old syntax
# (-i -a / -d / -f -d), no /add-driver /delete-driver /install /uninstall /force.
# Found 08.10.2026: this step was always skipped on Windows 8.1 before (PS<5 gate
# in setup.ps1), so the pnputil syntax mismatch here was never exercised until WMF
# 5.1 was installed and PS5.1 unlocked the step - then pnputil dumped its own usage
# text instead of installing (modern flags not recognized), "driver package was not
# accepted by pnputil".
$legacyPnputil = [System.Environment]::OSVersion.Version.Build -lt 14393

# ---- self-elevation ----
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Administrator rights are required, asking Windows..."
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    if ($Rollback) { $argList += " -Rollback" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList -Wait
    exit
}

$logDir = Join-Path $env:ProgramData "CaptPrinter"
New-Item -ItemType Directory -Force $logDir | Out-Null
Start-Transcript -Path (Join-Path $logDir "ppd_install.log") -Append | Out-Null

function Done($ok, $msg) {
    if ($ok) { Write-Host "OK: $msg" -ForegroundColor Green } else { Write-Host "FAILED: $msg" -ForegroundColor Red }
    Stop-Transcript | Out-Null
    if (-not $Silent) { Read-Host "Press Enter to close" }
    if ($ok) { exit 0 } else { exit 1 }
}

try {
    if ($Rollback) {
        foreach ($q in $queues) {
            if (Get-Printer -Name $q -ErrorAction SilentlyContinue) {
                Set-Printer -Name $q -DriverName $oldDriver
                Write-Host "Queue '$q' -> $oldDriver"
            }
        }
        Remove-PrinterDriver -Name $driverName -ErrorAction SilentlyContinue
        foreach ($d in @(Get-WindowsDriver -Online -All | Where-Object { $_.OriginalFileName -like "*lbp1120ps.inf" })) {
            if ($legacyPnputil) { & pnputil -f -d $d.Driver | Out-Null }
            else { & pnputil /delete-driver $d.Driver /uninstall /force | Out-Null }
        }
        Done $true "queues switched back to '$oldDriver', the CAPT driver package removed"
    }

    # at least one of our queues must exist (only "Canon LBP-810" when the user installed just the LBP-810)
    if (@($queues | Where-Object { Get-Printer -Name $_ -ErrorAction SilentlyContinue }).Count -eq 0) {
        Done $false "no Canon print queue found - run setup.ps1 first"
    }

    # ---- signing certificate (the same one setup.ps1 uses for the USB driver) ----
    $subject = "CN=LBP1120 WinUSB Driver"
    $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $subject -and $_.NotAfter -gt (Get-Date) } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -CertStoreLocation "Cert:\CurrentUser\My" -KeyUsage DigitalSignature -FriendlyName "LBP1120 Signing" -NotAfter (Get-Date).AddYears(10)
        Write-Host "Created signing certificate"
    }
    $certFile = Join-Path $env:TEMP "lbp1120_cert.cer"
    Export-Certificate -Cert $cert -FilePath $certFile -Force | Out-Null
    Import-Certificate -FilePath $certFile -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
    Import-Certificate -FilePath $certFile -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null

    # ---- build a signed package in a temp folder ----
    $work = Join-Path $env:TEMP "lbp1120_ppd_pkg"
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force $work | Out-Null
    Copy-Item (Join-Path $here "LBP1120PS.inf") $work
    Copy-Item (Join-Path $here "LBP1120.PPD") $work
    $catTmp = Join-Path $env:TEMP "LBP1120PS.cat"
    Remove-Item $catTmp -Force -ErrorAction SilentlyContinue
    New-FileCatalog -Path $work -CatalogFilePath $catTmp -CatalogVersion 2.0 | Out-Null
    Move-Item $catTmp (Join-Path $work "LBP1120PS.cat") -Force
    $sig = Set-AuthenticodeSignature -FilePath (Join-Path $work "LBP1120PS.cat") -Certificate $cert -HashAlgorithm SHA256
    Write-Host "Catalog signature status: $($sig.Status)"

    # ---- update: switch the queues to the old driver so that the old package can be replaced ----
    foreach ($q in $queues) {
        $pr = Get-Printer -Name $q -ErrorAction SilentlyContinue
        if ($pr -and $pr.DriverName -eq $driverName) {
            Set-Printer -Name $q -DriverName $oldDriver
            Write-Host "Queue '$q' -> $oldDriver (temporarily)"
        }
    }
    Remove-PrinterDriver -Name $driverName -ErrorAction SilentlyContinue

    # ---- install into the driver store ----
    # remove an earlier copy of this package (e.g. a failed attempt with another version)
    foreach ($d in @(Get-WindowsDriver -Online -All | Where-Object { $_.OriginalFileName -like "*lbp1120ps.inf" })) {
        Write-Host "Removing the earlier package $($d.Driver)"
        if ($legacyPnputil) { & pnputil -f -d $d.Driver | Out-Null }
        else { & pnputil /delete-driver $d.Driver /uninstall /force | Out-Null }
    }
    if ($legacyPnputil) { $out = & pnputil -i -a (Join-Path $work "LBP1120PS.inf") 2>&1 }
    else { $out = & pnputil /add-driver (Join-Path $work "LBP1120PS.inf") /install 2>&1 }
    $out | ForEach-Object { Write-Host $_ }
    # pnputil exit codes are unreliable (259 etc.): verify the package is really present
    $present = @(Get-WindowsDriver -Online -All | Where-Object { $_.OriginalFileName -like "*lbp1120ps.inf" })
    if ($present.Count -eq 0) {
        Done $false "the driver package was not accepted by pnputil (see the messages above and $logDir\ppd_install.log)"
    }
    Write-Host "Package in the driver store: $($present[0].Driver)"

    # ---- register the printer driver and switch the queues ----
    if (-not (Get-PrinterDriver -Name $driverName -ErrorAction SilentlyContinue)) {
        Add-PrinterDriver -Name $driverName
    }
    if (-not (Get-PrinterDriver -Name $driverName -ErrorAction SilentlyContinue)) {
        Done $false "Add-PrinterDriver did not register '$driverName'"
    }
    foreach ($q in $queues) {
        if (Get-Printer -Name $q -ErrorAction SilentlyContinue) {
            Set-Printer -Name $q -DriverName $driverName
            Write-Host "Queue '$q' -> $driverName"
        }
    }
    Remove-Item "Cert:\LocalMachine\Root\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
    Done $true "installed. Open Printing Preferences of the Canon LBP-1120 queue: the quality options are under the Advanced button."
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Done $false $_.Exception.Message
}
