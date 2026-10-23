<#
Деинсталляция Canon LBP-1120 / Canon LBP-1120 uninstall
Запускать ОБЯЗАТЕЛЬНО от администратора / Must be run as administrator

По умолчанию удаляет всё, что наше (принтеры, порты, WinUSB-драйвер, сертификат,
C:\Program Files\CaptPrinter\, пункт меню, журналы). Ghostscript и Redmon удаляются ТОЛЬКО
если их поставил наш установщик (метка installed_by_us_*.flag в C:\ProgramData\CaptPrinter)
и (для Redmon) нет чужих портов. Флаг -Full удаляет их независимо от метки.

By default removes everything that is ours (printers, ports, WinUSB driver, certificate,
C:\Program Files\CaptPrinter\, context menu entry, logs). Ghostscript and Redmon are removed ONLY
if our installer put them there (installed_by_us_*.flag in C:\ProgramData\CaptPrinter)
and (Redmon) there are no foreign ports. -Full removes them regardless of the flag.
#>

param(
    [switch]$Full,
    [string]$Lang = ""   # ru / en: если задан, окно выбора языка не показывается (тихое удаление из Inno)
)

$ErrorActionPreference = "Stop"

function Select-Language {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Canon LBP-1120"
    $form.Size = New-Object System.Drawing.Size(340, 150)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true

    $label = New-Object System.Windows.Forms.Label
    $label.Text = "Choose language / Выберите язык"
    $label.AutoSize = $true
    $label.Location = New-Object System.Drawing.Point(30, 20)
    $form.Controls.Add($label)

    $btnRu = New-Object System.Windows.Forms.Button
    $btnRu.Text = "Русский"
    $btnRu.Size = New-Object System.Drawing.Size(110, 32)
    $btnRu.Location = New-Object System.Drawing.Point(40, 60)
    $btnRu.DialogResult = [System.Windows.Forms.DialogResult]::Yes
    $form.Controls.Add($btnRu)

    $btnEn = New-Object System.Windows.Forms.Button
    $btnEn.Text = "English"
    $btnEn.Size = New-Object System.Drawing.Size(110, 32)
    $btnEn.Location = New-Object System.Drawing.Point(170, 60)
    $btnEn.DialogResult = [System.Windows.Forms.DialogResult]::No
    $form.Controls.Add($btnEn)

    $form.AcceptButton = $btnRu
    $result = $form.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::No) { return "en" }
    return "ru"
}

if ($Lang -ne "ru" -and $Lang -ne "en") { $Lang = Select-Language }

$S = @{
    ru = @{
        run_as_admin      = "Запусти от имени администратора!"
        stopping_hung     = "Останавливаю зависшие процессы печати"
        stopped_python    = "Остановлен python (PID {0})"
        done              = "Готово"
        clearing_queues   = "Очищаю очереди печати"
        removing_printers = "Удаляю принтеры"
        printer_removed   = "'{0}' удалён (или уже отсутствовал)"
        removing_ports    = "Удаляю Redmon-порты"
        port_removed      = "Порт {0} удалён из реестра"
        port_absent       = "Порта {0} уже нет"
        removing_menu     = "Удаляю пункт контекстного меню 'Печать через LBP1120'"
        menu_removed      = "Пункт меню удалён"
        menu_absent       = "Пункта меню уже нет"
        removing_scripts  = "Удаляю скрипты из C:\Program Files\CaptPrinter\"
        folder_removed    = "Папка удалена"
        folder_absent     = "Папки уже нет"
        removing_usb      = "Удаляю WinUSB-драйвер и сертификат"
        removing_shared   = "Проверяю общие компоненты (Ghostscript, Redmon)"
        gs_kept           = "Ghostscript оставлен (поставлен не нашим установщиком)"
        gs_leftover       = "Не удалось удалить файлы Ghostscript (заняты другой программой), папка: {0}. Удалите вручную или после перезагрузки."
        redmon_kept       = "Redmon оставлен (поставлен не нашим установщиком или есть чужие порты)"
        removing_logs     = "Удаляю журналы"
        spooler_skipped   = "Перезапуск спулера пропущен: в других очередях есть задания печати. Порты исчезнут после перезагрузки."
        gs_removed        = "Ghostscript удалён"
        gs_not_found      = "Деинсталлятор Ghostscript не найден, пропускаю"
        redmon_removed    = "Redmon-монитор удалён из реестра"
        driver_found      = "Найден WinUSB-драйвер в системе - удали вручную через 'pnputil /delete-driver oemXX.inf' (см. номер в списке 'pnputil /enum-drivers')"
        driver_removed_legacy = "WinUSB-драйвер удалён из системы ({0})"
        cert_removed_cu   = "Сертификат удалён из CurrentUser\My"
        cert_removed_lm   = "Сертификат удалён из LocalMachine\Root"
        cert_removed_tp   = "Сертификат удалён из LocalMachine\TrustedPublisher"
        restarting_spooler= "Перезапускаю спулер"
        spooler_restarted = "Спулер перезапущен"
        complete          = "=== ДЕИНСТАЛЛЯЦИЯ ЗАВЕРШЕНА ==="
        full_done         = "Удалено всё, включая системные компоненты (Ghostscript/Redmon/сертификат)."
        partial_done1     = "Удалены принтер, порт и файлы C:\Program Files\CaptPrinter\."
        partial_done2     = "WinUSB-драйвер и сертификат удалены. Ghostscript/Redmon удалены, только если их поставили мы."
        partial_done3     = "Принудительно удалить и их: .\uninstall.ps1 -Full"
        reinstall_hint    = "Теперь можно запустить .\setup.ps1 для чистой переустановки."
    }
    en = @{
        run_as_admin      = "Run as administrator!"
        stopping_hung     = "Stopping hung print processes"
        stopped_python    = "Stopped python (PID {0})"
        done              = "Done"
        clearing_queues   = "Clearing print queues"
        removing_printers = "Removing printers"
        printer_removed   = "'{0}' removed (or was already absent)"
        removing_ports    = "Removing Redmon ports"
        port_removed      = "Port {0} removed from registry"
        port_absent       = "Port {0} already absent"
        removing_menu     = "Removing 'Print via LBP1120' context menu entry"
        menu_removed      = "Menu entry removed"
        menu_absent       = "Menu entry already absent"
        removing_scripts  = "Removing scripts from C:\Program Files\CaptPrinter\"
        folder_removed    = "Folder removed"
        folder_absent     = "Folder already absent"
        removing_usb      = "Removing WinUSB driver and certificate"
        removing_shared   = "Checking shared components (Ghostscript, Redmon)"
        gs_kept           = "Ghostscript kept (not installed by our installer)"
        gs_leftover       = "Could not remove Ghostscript files (in use by another program), folder: {0}. Remove manually or after a reboot."
        redmon_kept       = "Redmon kept (not installed by our installer, or foreign ports exist)"
        removing_logs     = "Removing logs"
        spooler_skipped   = "Spooler restart skipped: other queues have print jobs. Ports will disappear after a reboot."
        gs_removed        = "Ghostscript removed"
        gs_not_found      = "Ghostscript uninstaller not found, skipping"
        redmon_removed    = "Redmon monitor removed from registry"
        driver_found      = "WinUSB driver found in the system - remove manually via 'pnputil /delete-driver oemXX.inf' (see the number in 'pnputil /enum-drivers')"
        driver_removed_legacy = "WinUSB driver removed from the system ({0})"
        cert_removed_cu   = "Certificate removed from CurrentUser\My"
        cert_removed_lm   = "Certificate removed from LocalMachine\Root"
        cert_removed_tp   = "Certificate removed from LocalMachine\TrustedPublisher"
        restarting_spooler= "Restarting spooler"
        spooler_restarted = "Spooler restarted"
        complete          = "=== UNINSTALL COMPLETE ==="
        full_done         = "Everything removed, including system components (Ghostscript/Redmon/certificate)."
        partial_done1     = "Printer, port and C:\Program Files\CaptPrinter\ files removed."
        partial_done2     = "WinUSB driver and certificate removed. Ghostscript/Redmon removed only if we installed them."
        partial_done3     = "To force-remove those too: .\uninstall.ps1 -Full"
        reinstall_hint    = "You can now run .\setup.ps1 for a clean reinstall."
    }
}[$Lang]

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "  OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  WARNING: $msg" -ForegroundColor Yellow }

# Check admin
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host $S.run_as_admin -ForegroundColor Red
    exit 1
}

Step $S.stopping_hung
# наш capt_print.exe (его запускает Redmon на каждое задание) может остаться в памяти и держать файлы программы
Get-Process -Name capt_print -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# зависший powershell от прошлой установки (setup.ps1 / install_ppd_driver.ps1 из нашей папки) держит файлы: останавливаем
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'CaptPrinter_Setup.*(setup|install_ppd_driver)\.ps1' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 500
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmdline -match "capt_print") {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Ok ($S.stopped_python -f $_.Id)
    }
}
Ok $S.done

$printerNames = @("Canon LBP-1120", "Canon LBP-1120 (sharp text)")
$portNames = @("RPT1:", "RPT2:")
# дополнительные очереди "Canon LBP-1120 (СЕРИЙНЫЙ)", которые setup.ps1 создаёт при двух принтерах, и их порты
foreach ($pr in @(Get-Printer -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'Canon LBP-1120 (*)' -or $_.Name -like 'Canon LBP-1120 - *' -or $_.Name -like 'Canon LBP-810*' })) {
    if ($printerNames -notcontains $pr.Name) { $printerNames += $pr.Name }
    if ($pr.PortName -and ($portNames -notcontains $pr.PortName)) { $portNames += $pr.PortName }
}

Step $S.clearing_queues
foreach ($name in $printerNames) {
    $printer = Get-Printer -Name $name -ErrorAction SilentlyContinue
    if ($printer) {
        Get-PrintJob -PrinterObject $printer -ErrorAction SilentlyContinue | Remove-PrintJob -ErrorAction SilentlyContinue
    }
}
Ok $S.done

Step $S.removing_printers
foreach ($name in $printerNames) {
    Remove-Printer -Name $name -ErrorAction SilentlyContinue
    Ok ($S.printer_removed -f $name)
}

# Драйвер с окном настроек качества ("Canon LBP-1120 (CAPT)", ppd_driver\): после
# удаления очередей его можно снять - пакет и регистрацию (тихо, ошибки не критичны).
Remove-PrinterDriver -Name "Canon LBP-1120 (CAPT)" -ErrorAction SilentlyContinue
try {
    foreach ($d in @(Get-WindowsDriver -Online -All | Where-Object { $_.OriginalFileName -like "*lbp1120ps.inf" })) {
        & pnputil /delete-driver $d.Driver /uninstall /force | Out-Null
    }
} catch { }

Step $S.removing_ports
foreach ($port in $portNames) {
    $portPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Redirected Port\Ports\$port"
    if (Test-Path $portPath) {
        Remove-Item $portPath -Recurse -Force
        Ok ($S.port_removed -f $port)
    } else {
        Ok ($S.port_absent -f $port)
    }
}

Step $S.removing_menu
# HKLM - текущее расположение (setup.ps1 v17+); HKCU - оставлено для очистки
# следов установок до этого исправления.
$menuKeys = @(
    "HKLM:\Software\Classes\SystemFileAssociations\image\shell\PrintLBP1120",
    "HKCU:\Software\Classes\SystemFileAssociations\image\shell\PrintLBP1120"
)
$menuFound = $false
foreach ($menuKey in $menuKeys) {
    if (Test-Path $menuKey) {
        Remove-Item $menuKey -Recurse -Force
        $menuFound = $true
    }
}
if ($menuFound) { Ok $S.menu_removed } else { Ok $S.menu_absent }

Remove-Item "HKLM:\SOFTWARE\Classes\captcounter" -Recurse -Force -ErrorAction SilentlyContinue

Step $S.removing_scripts
$pfDir = if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }
$removedAny = $false
# новая папка (v46+) и прежняя C:\CaptPrinter (v44 и старше)
foreach ($d in @((Join-Path $pfDir "CaptPrinter"), "C:\CaptPrinter")) {
    if (Test-Path $d) {
        Remove-Item $d -Recurse -Force -ErrorAction SilentlyContinue
        $removedAny = $true
    }
}
if ($removedAny) { Ok $S.folder_removed } else { Ok $S.folder_absent }

$dataDir = Join-Path $env:ProgramData "CaptPrinter"
$gsFlag = Join-Path $dataDir "installed_by_us_gs.flag"
$rmFlag = Join-Path $dataDir "installed_by_us_redmon.flag"

# WinUSB-драйвер и сертификат - всегда наши, удаляем всегда.
Step $S.removing_usb
if ([System.Environment]::OSVersion.Version.Build -lt 14393) {
    # Windows 8.1 и старше: у pnputil старый синтаксис (-e / -d). Пакет нашего WinUSB-драйвера
    # отличаем по поставщику libwdi (старый pnputil -e не показывает имя исходного inf).
    try {
        $lastOem = $null
        foreach ($line in @(pnputil -e)) {
            if ($line -match '(oem\d+\.inf)') { $lastOem = $Matches[1] }
            elseif ($line -match 'libwdi' -and $lastOem) {
                & pnputil -d $lastOem -f | Out-Null
                Ok ($S.driver_removed_legacy -f $lastOem)
                $lastOem = $null
            }
        }
    } catch { Warn $S.driver_found }
} else {
    # Get-WindowsDriver не зависит от языка вывода pnputil: ищем пакеты LBP-1120 и LBP-810 по имени исходного inf
    try {
        foreach ($d in @(Get-WindowsDriver -Online -All | Where-Object { $_.OriginalFileName -like "*canon_capt_usb_printer*.inf" })) {
            & pnputil /delete-driver $d.Driver /uninstall /force | Out-Null
            Ok ($S.driver_removed_legacy -f $d.Driver)
        }
    } catch { Warn $S.driver_found }
}

$cert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq "CN=LBP1120 WinUSB Driver" }
if ($cert) {
    Remove-Item $cert.PSPath -Force -ErrorAction SilentlyContinue
    Ok $S.cert_removed_cu
}
$certRoot = Get-ChildItem Cert:\LocalMachine\Root -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq "CN=LBP1120 WinUSB Driver" }
if ($certRoot) {
    Remove-Item $certRoot.PSPath -Force -ErrorAction SilentlyContinue
    Ok $S.cert_removed_lm
}
$certTP = Get-ChildItem Cert:\LocalMachine\TrustedPublisher -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq "CN=LBP1120 WinUSB Driver" }
if ($certTP) {
    Remove-Item $certTP.PSPath -Force -ErrorAction SilentlyContinue
    Ok $S.cert_removed_tp
}

# Ghostscript и Redmon общие: могут использоваться другими программами. Снимаем только то, что поставили мы
# (метка), и Redmon - только если в нём не осталось чужих портов. -Full снимает независимо от метки.
Step $S.removing_shared
if ((Test-Path $gsFlag) -or $Full) {
    $gsUninstall = Get-ChildItem "C:\Program Files\gs\*\uninstgs.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gsUninstall) {
        $gsDir = Split-Path $gsUninstall.FullName -Parent
        # процессы Ghostscript держат gsdll64.dll: без их остановки файл остаётся после удаления
        Get-Process -Name gswin64c, gswin64, gsdll64 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Process -FilePath $gsUninstall.FullName -ArgumentList "/S" -Wait -ErrorAction SilentlyContinue
        # NSIS-деинсталлятор копирует себя во временную папку и возвращает управление сразу: ждём завершения его копии
        for ($i = 0; $i -lt 60; $i++) {
            $nsu = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -like "*~nsu*" })
            if ($nsu.Count -eq 0) { break }
            Start-Sleep -Seconds 1
        }
        # остатки (файл, который деинсталлятор не смог убрать): несколько попыток удалить папку версии
        for ($i = 0; $i -lt 5 -and (Test-Path $gsDir); $i++) {
            Remove-Item $gsDir -Recurse -Force -ErrorAction SilentlyContinue
            if (Test-Path $gsDir) { Start-Sleep -Seconds 2 }
        }
        $gsParent = Split-Path $gsDir -Parent
        if ((Test-Path $gsParent) -and -not (Get-ChildItem $gsParent -Force -ErrorAction SilentlyContinue)) {
            Remove-Item $gsParent -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $gsDir) { Warn ($S.gs_leftover -f $gsDir) } else { Ok $S.gs_removed }
    } else {
        Warn $S.gs_not_found
    }
} else {
    Ok $S.gs_kept
}

$rmKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Redirected Port"
$foreignPorts = @(Get-ChildItem "$rmKey\Ports" -ErrorAction SilentlyContinue)
if (Test-Path $rmKey) {
    if (((Test-Path $rmFlag) -and $foreignPorts.Count -eq 0) -or $Full) {
        Remove-Item $rmKey -Recurse -Force -ErrorAction SilentlyContinue
        Ok $S.redmon_removed
    } else {
        Ok $S.redmon_kept
    }
}

# Журналы (capt_redmon.log, install_result.log и т.п.) и метки. settings.ini и counter.json остаются:
# это настройки и счётчик пользователя, они пригодятся при переустановке.
Step $S.removing_logs
Get-ChildItem $dataDir -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item $gsFlag, $rmFlag -Force -ErrorAction SilentlyContinue
# Неотправленный отчёт статистики установки больше не нужен. install_id в реестре (HKLM\SOFTWARE\PrintRestore) остаётся
# сознательно: при переустановке тот же компьютер считается один раз.
Remove-Item (Join-Path $dataDir "pending.json") -Force -ErrorAction SilentlyContinue
if ((Test-Path $dataDir) -and -not (Get-ChildItem $dataDir -Force -ErrorAction SilentlyContinue)) {
    Remove-Item $dataDir -Force -ErrorAction SilentlyContinue
}
Ok $S.done

# Папка установки Inno (там лежит и этот скрипт): файлы могут на несколько секунд задерживаться антивирусом, который проверяет
# свежие .ps1. Пробуем удалить всё, кроме самого скрипта, с повторами; остальное (и сам скрипт) уберёт Inno после завершения.
$selfDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($selfDir -match 'CaptPrinter_Setup') {
    for ($i = 0; $i -lt 10; $i++) {
        Get-ChildItem $selfDir -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notin @('uninstall.ps1', 'Uninstall.cmd') -and $_.Name -notlike 'unins*' } |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        $left = @(Get-ChildItem $selfDir -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notin @('uninstall.ps1', 'Uninstall.cmd') -and $_.Name -notlike 'unins*' })
        if ($left.Count -eq 0) { break }
        Start-Sleep -Seconds 1
    }
}

Step $S.restarting_spooler
# Перезапуск спулера оборвал бы чужие задания печати: если в других очередях они есть - не перезапускаем.
$foreignJobs = 0
foreach ($pr in @(Get-Printer -ErrorAction SilentlyContinue)) {
    if ($printerNames -notcontains $pr.Name) {
        $foreignJobs += @(Get-PrintJob -PrinterObject $pr -ErrorAction SilentlyContinue).Count
    }
}
if ($foreignJobs -gt 0) {
    Warn $S.spooler_skipped
} else {
    Restart-Service -Name Spooler -Force
    Start-Sleep -Seconds 2
    Ok $S.spooler_restarted
}

Write-Host ""
Write-Host $S.complete -ForegroundColor Green
if ($Full) {
    Write-Host $S.full_done
} else {
    Write-Host $S.partial_done1
    Write-Host $S.partial_done2
    Write-Host $S.partial_done3
}
Write-Host ""
Write-Host $S.reinstall_hint
Write-Host ""
