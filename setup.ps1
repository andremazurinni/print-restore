<#
Установка Canon LBP-1120 на Windows 10/11 x64 / Canon LBP-1120 setup for Windows 10/11 x64
Запускать ОБЯЗАТЕЛЬНО от администратора / Must be run as administrator
#>

param(
    [switch]$UsePython,    # запасной режим: порты на Python-скрипты из source\ (нужен Python 3.10+)
    [switch]$SelfDestruct, # для удалённых сеансов (AnyDesk): после успешной установки сама
                            # распакованная папка установщика удаляется безвозвратно (не в
                            # Корзину) - НЕ для обычной розничной установки с Авито, там файлы
                            # (uninstall.ps1, Counter.cmd) нужны клиенту потом
    [string]$Lang = "",    # ru / en: язык, выбранный в мастере Inno; если не задан - окно выбора языка (ручной запуск)
    [string]$Models = "",  # PID моделей через запятую (например "262B,260A"), для которых делать очереди и пробную
                            # печать. Пусто = все подключённые (как раньше). Задаёт мастер установки (Inno).
    [string]$Role = "",    # client / helper: метка помощника для статистики установок (см. stats.ps1)
    [string]$Name = "",    # имя помощника (только при Role=helper)
    [switch]$NoStats,      # клиент отказался от отправки статистики установки
    [switch]$Silent,       # тихая установка (/SILENT из мастера): никаких вопросов пользователю, при проблеме - ошибка и код выхода
    [switch]$NoTest,       # не печатать пробную страницу в конце установки (мастер предлагает её отдельной галочкой на последней странице)
    [switch]$TestOnly      # только пробная печать для уже установленного драйвера (запускает мастер, если галочка на последней странице отмечена)
)

$ErrorActionPreference = "Stop"
# Журнал установки ведёт сам скрипт (UTF-8 с BOM): вывод встроенных программ Windows (pnputil и др.) идёт в кодировке CP866, наши
# сообщения - в UTF-8, и при перенаправлении из cmd в одном файле получалась смесь, нечитаемая в блокноте. Транскрипт приводит всё к одной.
# Старый журнал стираем: дозапись в файл без BOM идёт в ASCII и русские буквы превращаются в "?". Дозапись нужна только -TestOnly (файл уже в UTF-8).
try {
    $installLogPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'install_output.log'
    if (-not $TestOnly) { Remove-Item -LiteralPath $installLogPath -Force -ErrorAction SilentlyContinue }
    Start-Transcript -Path $installLogPath -Append -Force | Out-Null
} catch { }
$wantModels =@($Models -split '[,;\s]+' | Where-Object { $_ } | ForEach-Object { $_.ToUpper() })
function Want($modelPid) { return (($wantModels.Count -eq 0) -or ($wantModels -contains $modelPid.ToUpper())) }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
# Статистика установок (stats.ps1). Любая ошибка здесь не должна ломать установку.
$statsCfg = $null
try { . (Join-Path $here 'stats.ps1'); $statsCfg = Get-StatsConfig -Role $Role -Name $Name -NoStats:$NoStats -Here $here } catch { $statsCfg = $null }
if ($TestOnly) { $statsCfg = $null }   # отдельная пробная печать статистику не отправляет: результат установки уже учтён
if ($PSVersionTable.PSVersion.Major -lt 3) {
    Write-Host "ERROR: PowerShell 3.0+ is required (Windows 8.1 or newer). / Нужен PowerShell 3.0+ (Windows 8.1 или новее)." -ForegroundColor Red
    exit 1
}

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
        exe_missing       = "Не найден capt_print.exe рядом с setup.ps1 (возможно, его удалил или заблокировал антивирус). Что делать: 1) распакуй архив заново (лучше добавить папку в исключения антивируса); 2) либо поставь Python 3.10+ (python.org, галочка Add to PATH) и запусти: .\setup.ps1 -UsePython. См. раздел 'Если печать не работает' в README."
        exe_missing_fallback = "capt_print.exe не найден (возможно, его удалил антивирус) - продолжаю в режиме Python: скрипты из папки source. Подробнее - в README, раздел 'Если печать не работает'."
        source_missing    = "Не найден файл {0} рядом с setup.ps1 - распакуй архив целиком."
        installing_ppd    = "Устанавливаю драйвер с окном настроек качества"
        ppd_installed     = "Драйвер 'Canon LBP-1120 (CAPT)' установлен: настройки качества - в 'Настройка печати' -> 'Дополнительно'"
        ppd_skipped_oldps = "Драйвер с окном настроек пропущен: для него нужен PowerShell 5+ (на Windows 8.1 его нет). Принтер работает с обычным драйвером, без окна настроек. Чтобы окно настроек появилось на Windows 8.1, установите обновление Microsoft Windows Management Framework 5.1 (WMF 5.1) и запустите установку ещё раз."
        ppd_failed        = "Драйвер с окном настроек не установился - принтер работает с обычным драйвером, но без окна настроек. Причины и повтор: ppd_driver\install_ppd_driver.ps1, лог C:\ProgramData\CaptPrinter\ppd_install.log"
        one_printer       = "В Ctrl+P доступен принтер 'Canon LBP-1120' (чёткий текст и таблицы; полутона, разрешение 600/300 dpi, плотность и другое - в 'Настройка печати' -> 'Дополнительно')."
        extra_queues_step = "Подключено два и более принтеров LBP-1120: создаю отдельную очередь для каждого (выбор в окне печати)"
        extra_queue_ok    = "Очередь '{0}' (серийный номер {1}) создана"
        extra_queue_fail  = "Очередь для принтера {0} не создана: {1}. Основная очередь 'Canon LBP-1120' работает (печатает на первый найденный принтер)."
        settings_hint     = "Сброс настроек к умолчанию: ppd_driver\Reset_print_settings.cmd"
        counter_hint      = "Счётчик листов картриджа (показ и сброс при замене): C:\Program Files\CaptPrinter\Counter.cmd"
        selfdestruct_scheduled = "Папка установщика будет удалена с этого компьютера через несколько секунд (режим удалённой установки)."
        run_as_admin      = "Запусти от имени администратора!"
        checking_python   = "Проверяю Python"
        installing_pkgs   = "Устанавливаю Python-библиотеки"
        done              = "Готово"
        copying_scripts   = "Копирую скрипты в C:\Program Files\CaptPrinter"
        copied            = "Скопировано"
        checking_gs       = "Проверяю Ghostscript"
        already_installed = "Уже установлен: {0}"
        downloading_gs    = "  Скачиваю Ghostscript..."
        installed         = "Установлено"
        checking_redmon   = "Проверяю Redmon"
        already_installed2= "Уже установлен"
        downloading_rm    = "  Скачиваю Redmon..."
        cert_setup        = "Настраиваю сертификат WinUSB"
        cert_created      = "Сертификат создан"
        cert_exists       = "Сертификат уже есть"
        cert_trusted      = "Сертификат доверенный"
        installing_driver = "Устанавливаю WinUSB-драйвер"
        driver_installed  = "Драйвер установлен"
        creating_printers = "Создаю принтеры"
        spooler_restarted = "Спулер перезапущен"
        printers_ready    = "Принтеры готовы"
        complete          = "=== УСТАНОВКА ЗАВЕРШЕНА ==="
        hash_ok           = "Хэш подтверждён: {0}"
        hash_mismatch     = "Хэш файла не совпадает с ожидаемым! Ожидали {0}, получили {1}. Файл удалён, установка прервана - возможна подмена или обновление версии на сайте источника."
        sig_ok            = "Подлинная подпись издателя подтверждена: {0}"
        dl_manual_title   = "Print Restore - {0}"
        dl_manual_text    = "Не удалось скачать {0} автоматически (нет интернета или сайт недоступен).`n`nМожно открыть официальную страницу загрузки, скачать файл самостоятельно и выбрать его здесь. Или проверьте интернет и нажмите «Повторить»."
        dl_hint_gs        = "ВАЖНО: на странице нужна строка «Ghostscript 10.08.0 for Windows (64 bit)» (или более новая версия), ссылка «Ghostscript AGPL Release». Версия для 32 бит не подойдёт."
        dl_hint_rm        = "ВАЖНО: нужен файл redmon19.zip (RedMon 1.9), ссылка «redmon19.zip» на странице."
        dl_btn_open       = "Открыть страницу загрузки"
        dl_btn_pick       = "Выбрать файл..."
        dl_btn_retry      = "Повторить"
        dl_btn_cancel     = "Отмена"
        dl_pick_title     = "Выберите файл: {0}"
        dl_unverified_text = "Этот файл не совпал с ожидаемым и не имеет подлинной подписи издателя ({0}).`n`nЕсли вы скачали его с официальной страницы, можно продолжить. Продолжить установку с этим файлом?"
        dl_unverified_continue = "Файл не подтверждён, продолжаю по вашему решению (хэш {0})."
        dl_unsigned_text  = "Этот файл не подходит: у настоящего установщика {0} есть цифровая подпись «{1}», а у этого файла её нет.`n`nСкачайте {0} с официальной страницы (кнопка «Открыть страницу загрузки») и выберите скачанный файл ещё раз."
        dl_unsigned_refused = "Выбранный файл {0} без подписи издателя - не запускаю (хэш {1})."
        dl_manual_cancelled = "Скачивание {0} отменено пользователем."
        dl_silent_fail    = "Не удалось скачать {0}. В тихом режиме вопросов пользователю нет."
        gs_not_installed  = "Ghostscript не установился (окно установщика закрыто или установка отменена)."
        rm_not_installed  = "Redmon не установился (окно установщика закрыто или установка отменена)."
        python_not_found  = "Python не найден в PATH. Установи Python 3.x с python.org (галочка 'Add python.exe to PATH' на первом экране инсталлятора) и запусти setup.ps1 заново."
        python_exe_empty  = "Не удалось определить путь к python.exe (пустой результат). Проверь, что 'python' запускается из этого же PowerShell, и запусти setup.ps1 заново."
        driver_verify_failed = "pnputil не подтвердил установку драйвера (код {0}). Проверь вывод команды 'pnputil /enum-drivers' вручную."
        printers_verify_failed = "После установки не найден принтер '{0}' через Get-Printer. Создание принтера могло не пройти - проверь 'Устройства и принтеры' вручную или см. README (резервный путь через мастер Windows)."
        wpp_enabled       = "Включён «Режим защищённой печати Windows» (Windows protected print mode): с ним сторонний монитор портов Redmon не устанавливается и печать невозможна. Выключите его: Параметры -> Bluetooth и устройства -> Принтеры и сканеры -> Режим защищённой печати Windows -> Отключить. Затем запустите установку снова."
        wpp_warning       = "Обнаружена современная сборка Windows 11 (24H2+). Если включён Windows Protected Print Mode (Параметры -> Bluetooth и устройства -> Принтеры и сканеры), сторонний монитор портов Redmon не будет работать - принтер будет виден в Ctrl+P, но задания не будут печататься. При проблемах с печатью после установки проверь и при необходимости выключи этот режим."
        spooler_restart_warn = "Сейчас будет перезапущена служба печати (Spooler) - активные задания печати с ДРУГИХ принтеров на этом ПК будут прерваны."
        cert_expired      = "Найденный сертификат просрочен ({0}), создаю новый."
        cert_root_removed = "Сертификат убран из LocalMachine\Root (был нужен только на момент проверки подписи pnputil выше)"
        install_test_step  = "Печатаю пробную страницу"
        install_test_sent  = "Пробная страница отправлена на печать"
        install_test_failed = "Пробную страницу напечатать не удалось - см. C:\ProgramData\CaptPrinter\capt_redmon.log. Проверьте принтер и попробуйте распечатать любой документ (Ctrl+P, очередь Canon LBP-1120), либо см. README."
        install_test_title = "Canon LBP-1120 - проверка"
        install_test_question = "Дождитесь окончания печати (около 30 секунд на каждый принтер). Пробная страница напечаталась успешно и выглядит нормально?"
        install_test_result_yes = "Подтверждено: пробная печать успешна"
        install_test_result_no  = "Пользователь отметил: пробная печать НЕ успешна - проверьте README, раздел 'Если печать не работает', или оставьте заявку на Авито."
        install_test_no_hint    = "Проверьте, что принтер включён и USB-кабель подключён, затем попробуйте распечатать любой документ: откройте его и нажмите Ctrl+P, выберите принтер 'Canon LBP-1120'. Если не поможет - см. README, раздел 'Если печать не работает'."
        printer_wait_title      = "Canon LBP-1120 - подключите принтер"
        printer_wait_text       = "Подключите принтер Canon LBP-1120 к компьютеру USB-кабелем и включите его.`n`nУстановка продолжится автоматически, как только принтер будет обнаружен."
        printer_wait_skip       = "Установить без принтера"
        printer_wait_cancel     = "Отмена"
        printer_found           = "Принтер обнаружен"
        printer_absent_continue = "Принтер не подключён - устанавливаю без него (пробная печать будет пропущена)"
        printer_absent_hint     = "Принтер не был подключён, поэтому пробная печать пропущена. Драйвер установлен. Подключите принтер USB-кабелем, включите его и напечатайте любой документ: Ctrl+P, принтер 'Canon LBP-1120'."
        printer_absent_log      = "Принтер не был подключён при установке - пробная печать пропущена"
        install_cancelled       = "Установка отменена пользователем: принтер не подключён."
    }
    en = @{
        exe_missing       = "capt_print.exe was not found next to setup.ps1 (maybe an antivirus removed or blocked it). What to do: 1) extract the archive again (better add the folder to the antivirus exclusions); 2) or install Python 3.10+ (python.org, check Add to PATH) and run: .\setup.ps1 -UsePython. See the 'If printing does not work' section of the README."
        exe_missing_fallback = "capt_print.exe was not found (maybe removed by an antivirus) - continuing in Python mode: scripts from the source folder. See the 'If printing does not work' section of the README."
        source_missing    = "File {0} was not found next to setup.ps1 - extract the whole archive."
        installing_ppd    = "Installing the driver with the quality settings dialog"
        ppd_installed     = "Driver 'Canon LBP-1120 (CAPT)' installed: quality options are under Printing Preferences -> Advanced"
        ppd_skipped_oldps = "The driver with the settings dialog was skipped: it needs PowerShell 5+ (not available on Windows 8.1). The printer works with the standard driver, without the settings dialog. To get the settings dialog on Windows 8.1, install the Microsoft update Windows Management Framework 5.1 (WMF 5.1) and run setup again."
        ppd_failed        = "The driver with the settings dialog was not installed - the printer works with the standard driver, without the settings dialog. Reasons and retry: ppd_driver\install_ppd_driver.ps1, log C:\ProgramData\CaptPrinter\ppd_install.log"
        one_printer       = "The 'Canon LBP-1120' printer is available in Ctrl+P (crisp text and tables; halftoning, 600/300 dpi resolution, toner density and more are under Printing Preferences -> Advanced)."
        extra_queues_step = "Two or more LBP-1120 printers are connected: creating a separate queue for each (choose it in the print dialog)"
        extra_queue_ok    = "Queue '{0}' (serial number {1}) created"
        extra_queue_fail  = "The queue for printer {0} was not created: {1}. The main queue 'Canon LBP-1120' works (prints to the first printer found)."
        settings_hint     = "Reset settings to defaults: ppd_driver\Reset_print_settings.cmd"
        counter_hint      = "Cartridge sheet counter (view and reset after a change): C:\Program Files\CaptPrinter\Counter.cmd"
        selfdestruct_scheduled = "The installer folder will be deleted from this computer in a few seconds (remote-install mode)."
        run_as_admin      = "Run as administrator!"
        checking_python   = "Checking Python"
        installing_pkgs   = "Installing Python packages"
        done              = "Done"
        copying_scripts   = "Copying scripts to C:\Program Files\CaptPrinter"
        copied            = "Copied"
        checking_gs       = "Checking Ghostscript"
        already_installed = "Already installed: {0}"
        downloading_gs    = "  Downloading Ghostscript..."
        installed         = "Installed"
        checking_redmon   = "Checking Redmon"
        already_installed2= "Already installed"
        downloading_rm    = "  Downloading Redmon..."
        cert_setup        = "Setting up WinUSB certificate"
        cert_created      = "Certificate created"
        cert_exists       = "Certificate exists"
        cert_trusted      = "Certificate trusted"
        installing_driver = "Installing WinUSB driver"
        driver_installed  = "Driver installed"
        creating_printers = "Creating printers"
        spooler_restarted = "Spooler restarted"
        printers_ready    = "Printers ready"
        complete          = "=== INSTALLATION COMPLETE ==="
        hash_ok           = "Hash verified: {0}"
        hash_mismatch     = "File hash does not match the expected one! Expected {0}, got {1}. File deleted, setup aborted - possible tampering or a new version on the source site."
        sig_ok            = "Genuine publisher signature verified: {0}"
        dl_manual_title   = "Print Restore - {0}"
        dl_manual_text    = "Could not download {0} automatically (no internet or the site is unavailable).`n`nYou can open the official download page, download the file yourself and choose it here. Or check your internet and press Retry."
        dl_hint_gs        = "IMPORTANT: on the page choose the row 'Ghostscript 10.08.0 for Windows (64 bit)' (or a newer version), link 'Ghostscript AGPL Release'. The 32-bit version will not work."
        dl_hint_rm        = "IMPORTANT: you need the file redmon19.zip (RedMon 1.9), the 'redmon19.zip' link on the page."
        dl_btn_open       = "Open download page"
        dl_btn_pick       = "Choose file..."
        dl_btn_retry      = "Retry"
        dl_btn_cancel     = "Cancel"
        dl_pick_title     = "Choose the file: {0}"
        dl_unverified_text = "This file does not match the expected one and has no genuine publisher signature ({0}).`n`nIf you downloaded it from the official page, you can continue. Continue the installation with this file?"
        dl_unverified_continue = "File not verified, continuing at your decision (hash {0})."
        dl_unsigned_text  = "This file cannot be used: the genuine {0} installer carries the digital signature ""{1}"", and this file does not.`n`nDownload {0} from the official page (the ""Open download page"" button) and select the downloaded file again."
        dl_unsigned_refused = "The selected {0} file has no publisher signature - not running it (hash {1})."
        dl_manual_cancelled = "Download of {0} cancelled by the user."
        dl_silent_fail    = "Could not download {0}. There are no prompts in silent mode."
        gs_not_installed  = "Ghostscript was not installed (the installer window was closed or setup was cancelled)."
        rm_not_installed  = "Redmon was not installed (the installer window was closed or setup was cancelled)."
        python_not_found  = "Python not found in PATH. Install Python 3.x from python.org (check 'Add python.exe to PATH' on the installer's first screen) and re-run setup.ps1."
        python_exe_empty  = "Could not determine the path to python.exe (empty result). Make sure 'python' runs from this same PowerShell, then re-run setup.ps1."
        driver_verify_failed = "pnputil did not confirm the driver was installed (code {0}). Check the output of 'pnputil /enum-drivers' manually."
        printers_verify_failed = "Printer '{0}' was not found via Get-Printer after setup. Printer creation may have failed - check 'Devices and Printers' manually or see the README (fallback via the Windows wizard)."
        wpp_enabled       = "Windows protected print mode is on: the third-party Redmon port monitor cannot be installed with it, so printing is impossible. Turn it off: Settings -> Bluetooth & devices -> Printers & scanners -> Windows protected print mode -> Turn off. Then run the installation again."
        wpp_warning       = "A recent Windows 11 build (24H2+) was detected. If Windows Protected Print Mode is enabled (Settings -> Bluetooth & devices -> Printers & scanners), the third-party Redmon port monitor will not work - the printer will show up in Ctrl+P but jobs won't print. If printing fails after setup, check and if needed disable this mode."
        spooler_restart_warn = "The Print Spooler service is about to restart - active print jobs from OTHER printers on this PC will be interrupted."
        cert_expired      = "The certificate found has expired ({0}), creating a new one."
        cert_root_removed = "Certificate removed from LocalMachine\Root (only needed while pnputil verified the signature above)"
        install_test_step  = "Printing a test page"
        install_test_sent  = "Test page sent to the printer"
        install_test_failed = "Could not print the test page - see C:\ProgramData\CaptPrinter\capt_redmon.log. You can retry manually, see the README."
        install_test_title = "Canon LBP-1120 - check"
        install_test_question = "Wait for printing to finish (about 30 seconds per printer). Did the test page print successfully and look correct?"
        install_test_result_yes = "Confirmed: test print successful"
        install_test_result_no  = "User marked: test print NOT successful - check the README 'If printing does not work' section, or leave a request on Avito."
        install_test_no_hint    = "Check that the printer is turned on and the USB cable is connected, then try printing any document: open it and press Ctrl+P, pick the 'Canon LBP-1120' printer. If that does not help, see the README, 'If printing does not work' section."
        printer_wait_title      = "Canon LBP-1120 - connect the printer"
        printer_wait_text       = "Connect the Canon LBP-1120 to this computer with a USB cable and turn it on.`n`nSetup will continue automatically as soon as the printer is detected."
        printer_wait_skip       = "Install without printer"
        printer_wait_cancel     = "Cancel"
        printer_found           = "Printer detected"
        printer_absent_continue = "Printer not connected - installing without it (the test print will be skipped)"
        printer_absent_hint     = "The printer was not connected, so the test print was skipped. The driver is installed. Connect the printer with a USB cable, turn it on and print any document: Ctrl+P, printer 'Canon LBP-1120'."
        printer_absent_log      = "Printer was not connected during setup - test print skipped"
        install_cancelled       = "Setup cancelled by the user: printer not connected."
    }
}[$Lang]

$script:StatsStep = 'detect'       # текущий этап для статистики: detect copy port driver queue ppd test done
$script:StatsIssueStep = ''        # этап, на котором было предупреждение (установка прошла, но шаг не удался)
$script:StatsIssueCode = 0
# Этап установки: для статистики и для полосы хода в мастере (мастер раз в секунду читает progress.txt: copy, gs, redmon, driver, queue, ppd, done).
function Write-Progress-Key($key) { if (-not $TestOnly) { try { [System.IO.File]::WriteAllText((Join-Path $here 'progress.txt'), $key) } catch { } } }
function Step($msg, $statsKey = '') { if ($statsKey) { $script:StatsStep = $statsKey; Write-Progress-Key $statsKey }; Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "  OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  WARNING: $msg" -ForegroundColor Yellow }

# Статистика установок (см. stats.ps1): любой сбой здесь молча игнорируется и установку не ломает.
function Get-StatsPids {
    if (-not $printerPresent) { return @() }
    if ($wantModels.Count -gt 0) { return @($wantModels) }
    try {
        return @(Get-CimInstance -ClassName Win32_PnPEntity -Filter "PNPDeviceID LIKE 'USB\\VID_04A9&PID_%'" -ErrorAction Stop |
            ForEach-Object { if ($_.PNPDeviceID -match 'PID_([0-9A-F]{4})') { $Matches[1] } } | Sort-Object -Unique)
    } catch { return @() }
}
function Send-Stats($result, $code = 0, $step = '') {
    try {
        if (-not $statsCfg) { return }
        if (-not $step) { $step = $script:StatsStep }
        Send-StatsReport -Cfg $statsCfg -Result $result -Step $step -Code ([int]$code) -Pids @(Get-StatsPids) -DriverVer $DRIVER_VERSION
    } catch { }
}

# Коды выхода (мастер по ним пишет понятную причину): 1 - общая ошибка, 10 - Ghostscript, 11 - Redmon.
$EXIT_GS = 10
$EXIT_REDMON = 11
$EXIT_WPP = 12      # включён режим защищённой печати Windows 11 - Redmon невозможен
function Fail($msg, $exitCode = 1) { Write-Host "  ERROR: $msg" -ForegroundColor Red; Send-Stats 'error' $(if ($exitCode -ne 1) { $exitCode } elseif ($LASTEXITCODE) { $LASTEXITCODE } else { 1 }); exit $exitCode }
# Необработанная ошибка скрипта: тоже сообщаем (этап и код 1), потом ошибка идёт дальше как раньше.
trap { Send-Stats 'error' 1; break }

# Официальные источники + ожидаемые хэши (SHA256), чтобы даже при компрометации
# канала передачи скрипт не поставил подменённый файл. Если Ghostscript/Redmon
# выпустят новую версию и хэш перестанет совпадать - обновите версию в URL и
# хэш ниже вручную, после самостоятельной проверки на официальном сайте.
$GS_SHA256     = "52A91B8BF09298788D7A57B9206127026C23EACD75405F0A131E26DC381DCE50"
$REDMON_SHA256 = "5E652BFD5FC31CB74E87F02A177762BAEB5F9DF5D72D91C3F3D3CCB73B8D920D"

# Версия драйвера для отчёта статистики (Send-Stats). Старая отправка в Telegram-бот удалена (аудит F8).
$DRIVER_VERSION     = "55"

try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
# Проверка файла: сначала хэш SHA-256; если не совпал - подлинная цифровая подпись нужного издателя (Authenticode).
# Так новая версия Ghostscript с официального сайта подходит без правки хэша в скрипте. $sigName пустой = только хэш.
# $sigName = точное название организации (поле O= сертификата), а не любое имя, в котором встречается это слово (аудит F4).
function Test-DownloadedFile($path, $expectedSha256, $sigName) {
    $actual = (Get-FileHash -Path $path -Algorithm SHA256).Hash
    if ($actual -eq $expectedSha256) { return @{ ok = $true; how = 'hash'; actual = $actual; signer = '' } }
    if ($sigName) {
        try {
            $sig = Get-AuthenticodeSignature -FilePath $path
            $org = [regex]::Escape($sigName)
            if ($sig.Status -eq 'Valid' -and $sig.SignerCertificate -and
                $sig.SignerCertificate.Subject -match "(^|,\s*)O=(`"$org`"|$org)(\s*,|$)") {
                return @{ ok = $true; how = 'signature'; actual = $actual; signer = $sig.SignerCertificate.Subject }
            }
        } catch { }
    }
    return @{ ok = $false; how = ''; actual = $actual; signer = '' }
}

# Скачивание по очереди с каждого адреса: три попытки на адрес. Без индикатора прогресса: в Windows PowerShell 5.1 он замедляет
# скачивание больших файлов (Ghostscript ~50 МБ) в разы, а при скрытом запуске из мастера выглядит как зависание.
function Save-FromUrls($urls, $destPath) {
    $oldProgress = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    $downloaded = $false
    foreach ($url in @($urls)) {
        for ($try = 1; $try -le 3 -and -not $downloaded; $try++) {
            try {
                Invoke-WebRequest -Uri $url -OutFile $destPath -UserAgent "Mozilla/5.0" -TimeoutSec 300 -UseBasicParsing
                $downloaded = $true
            } catch {
                Warn ("download attempt $try/3: " + $_.Exception.Message)
                Remove-Item $destPath -Force -ErrorAction SilentlyContinue
                if ($try -lt 3) { Start-Sleep -Seconds 5 }
            }
        }
        if ($downloaded) { break }
    }
    $ProgressPreference = $oldProgress
    return $downloaded
}

# Вопрос с невидимым владельцем TopMost: установка идёт скрыто из мастера Inno, обычное окно оказалось бы за мастером.
function Show-DlgBox($text, $title, $buttons, $icon) {
    Add-Type -AssemblyName System.Windows.Forms
    $owner = New-Object System.Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.StartPosition = "CenterScreen"
    $owner.Size = New-Object System.Drawing.Size(1, 1)
    $owner.Opacity = 0
    $owner.Show()
    $owner.Activate()
    try { return [System.Windows.Forms.MessageBox]::Show($owner, $text, $title, $buttons, $icon) }
    finally { $owner.Close(); $owner.Dispose() }
}

# Окно, когда автоматическое скачивание не удалось: открыть официальную страницу, выбрать скачанный файл, повторить, отмена.
# Результат: @{ result = 'pick' | 'retry' | 'cancel'; path = путь к выбранному файлу }
function Show-ManualDownloadDialog($name, $pageUrl, $filter, $hint) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $state = @{ result = 'cancel'; path = '' }

    $form = New-Object System.Windows.Forms.Form
    $form.Text = ($S.dl_manual_title -f $name)
    $form.Size = New-Object System.Drawing.Size(520, 330)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true

    $label = New-Object System.Windows.Forms.Label
    $label.Text = ($S.dl_manual_text -f $name) + "`n`n" + $hint
    $label.Size = New-Object System.Drawing.Size(470, 180)
    $label.Location = New-Object System.Drawing.Point(20, 15)
    $form.Controls.Add($label)

    $btnOpen = New-Object System.Windows.Forms.Button
    $btnOpen.Text = $S.dl_btn_open
    $btnOpen.Size = New-Object System.Drawing.Size(225, 32)
    $btnOpen.Location = New-Object System.Drawing.Point(20, 205)
    $btnOpen.Add_Click({ try { Start-Process $pageUrl } catch { } }.GetNewClosure())
    $form.Controls.Add($btnOpen)

    $btnPick = New-Object System.Windows.Forms.Button
    $btnPick.Text = $S.dl_btn_pick
    $btnPick.Size = New-Object System.Drawing.Size(225, 32)
    $btnPick.Location = New-Object System.Drawing.Point(265, 205)
    $btnPick.Add_Click({
        $dlg = New-Object System.Windows.Forms.OpenFileDialog
        $dlg.Filter = $filter
        $dlg.Title = ($S.dl_pick_title -f $name)
        if ($dlg.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
            $state.result = 'pick'; $state.path = $dlg.FileName; $form.Close()
        }
    }.GetNewClosure())
    $form.Controls.Add($btnPick)

    $btnRetry = New-Object System.Windows.Forms.Button
    $btnRetry.Text = $S.dl_btn_retry
    $btnRetry.Size = New-Object System.Drawing.Size(225, 32)
    $btnRetry.Location = New-Object System.Drawing.Point(20, 250)
    $btnRetry.Add_Click({ $state.result = 'retry'; $form.Close() }.GetNewClosure())
    $form.Controls.Add($btnRetry)

    $btnCancel = New-Object System.Windows.Forms.Button
    $btnCancel.Text = $S.dl_btn_cancel
    $btnCancel.Size = New-Object System.Drawing.Size(225, 32)
    $btnCancel.Location = New-Object System.Drawing.Point(265, 250)
    $btnCancel.Add_Click({ $state.result = 'cancel'; $form.Close() }.GetNewClosure())
    $form.Controls.Add($btnCancel)

    [void]$form.ShowDialog()
    return $state
}

# Получить файл (Ghostscript, Redmon): скачать по адресам из списка; если не вышло - окно с выбором файла вручную.
# Возвращает путь к проверенному файлу. $script:UserPickedFile = $true, если файл выбран пользователем (его нельзя удалять).
# Файл скачан автоматически, но не совпал и без подписи - ошибка (возможна подмена). Выбран вручную и не совпал: если нужна
# подпись ($sigName, Ghostscript) - отказ и снова окно выбора; без подписи (Redmon) - предупреждение с выбором "продолжить".
# Тихий режим (-Silent): окон нет, при неудаче ошибка с кодом $failCode.
function Get-VerifiedFile($name, $urls, $expectedSha256, $destPath, $failCode, $pageUrl, $filter, $sigName, $hint = '') {
    $script:UserPickedFile = $false
    while ($true) {
        if (Save-FromUrls $urls $destPath) {
            $chk = Test-DownloadedFile $destPath $expectedSha256 $sigName
            if ($chk.ok) {
                if ($chk.how -eq 'signature') { Ok ($S.sig_ok -f $chk.signer) } else { Ok ($S.hash_ok -f $chk.actual) }
                return $destPath
            }
            Remove-Item $destPath -Force -ErrorAction SilentlyContinue
            Fail ($S.hash_mismatch -f $expectedSha256, $chk.actual) $failCode
        }
        if ($Silent) { Fail ($S.dl_silent_fail -f $name) $failCode }
        while ($true) {
            $r = Show-ManualDownloadDialog $name $pageUrl $filter $hint
            if ($r.result -eq 'cancel') { Fail ($S.dl_manual_cancelled -f $name) $failCode }
            if ($r.result -eq 'retry') { break }
            $chk = Test-DownloadedFile $r.path $expectedSha256 $sigName
            if ($chk.ok) {
                if ($chk.how -eq 'signature') { Ok ($S.sig_ok -f $chk.signer) } else { Ok ($S.hash_ok -f $chk.actual) }
                $script:UserPickedFile = $true
                return $r.path
            }
            # Файл с обязательной подписью издателя (Ghostscript): без неё не запускаем, даже по согласию (аудит F3).
            # У официальных сборок подпись есть всегда, так что это либо не тот файл, либо подделка.
            if ($sigName) {
                Warn ($S.dl_unsigned_refused -f $name, $chk.actual)
                [void](Show-DlgBox ($S.dl_unsigned_text -f $name, $sigName) ($S.dl_manual_title -f $name) `
                    ([System.Windows.Forms.MessageBoxButtons]::OK) ([System.Windows.Forms.MessageBoxIcon]::Error))
                continue
            }
            $ans = Show-DlgBox ($S.dl_unverified_text -f $name) ($S.dl_manual_title -f $name) `
                ([System.Windows.Forms.MessageBoxButtons]::YesNo) ([System.Windows.Forms.MessageBoxIcon]::Warning)
            if ($ans -eq [System.Windows.Forms.DialogResult]::Yes) {
                Warn ($S.dl_unverified_continue -f $chk.actual)
                $script:UserPickedFile = $true
                return $r.path
            }
        }
    }
}

# Мастер Inno запускает этот скрипт скрыто, поэтому окна дочерних установщиков (Redmon, а при сбое тихого режима и
# Ghostscript) открывались бы ПОЗАДИ окна мастера и установка молча ждала бы нажатия. Ждём процесс и держим его окно поверх всех.
try {
    Add-Type -Namespace LbpWin -Name U -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);' -ErrorAction Stop
} catch { }
function Wait-ChildInstaller($proc) {
    while (-not $proc.HasExited) {
        try {
            $proc.Refresh()
            if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
                [LbpWin.U]::SetWindowPos($proc.MainWindowHandle, [IntPtr](-1), 0, 0, 0, 0, 0x0043) | Out-Null
                [LbpWin.U]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
            }
        } catch { }
        Start-Sleep -Milliseconds 700
    }
}

# Check admin
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host $S.run_as_admin -ForegroundColor Red
    exit 1
}

# Принтер подключён? Достаточно VID/PID - Windows перечисляет USB-устройство и без нашего драйвера.
# Win32_PnPEntity есть и на Windows 8.1 (в отличие от Get-PnpDevice). Если сама проверка не сработала -
# считаем, что принтер есть (установку не блокируем).
function Test-PrinterPresent {
    try {
        $found = @(Get-CimInstance -ClassName Win32_PnPEntity -Filter "PNPDeviceID LIKE 'USB\\VID_04A9&PID_262B%' OR PNPDeviceID LIKE 'USB\\VID_04A9&PID_260A%'" -ErrorAction Stop)
        return ($found.Count -gt 0)
    } catch { return $true }
}

# Окно ожидания: само закрывается, когда принтер появился (опрос раз в 2 с).
# Результат: "found" / "skip" (установить без принтера) / "cancel".
function Wait-ForPrinter {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $state = @{ result = "cancel" }   # общий объект: замыкания меняют его, а не копию переменной

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $S.printer_wait_title
    $form.Size = New-Object System.Drawing.Size(440, 220)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true

    $label = New-Object System.Windows.Forms.Label
    $label.Text = $S.printer_wait_text
    $label.Size = New-Object System.Drawing.Size(390, 90)
    $label.Location = New-Object System.Drawing.Point(20, 20)
    $form.Controls.Add($label)

    $btnSkip = New-Object System.Windows.Forms.Button
    $btnSkip.Text = $S.printer_wait_skip
    $btnSkip.Size = New-Object System.Drawing.Size(190, 32)
    $btnSkip.Location = New-Object System.Drawing.Point(20, 130)
    $btnSkip.Add_Click({ $state.result = "skip"; $form.Close() }.GetNewClosure())
    $form.Controls.Add($btnSkip)

    $btnCancel = New-Object System.Windows.Forms.Button
    $btnCancel.Text = $S.printer_wait_cancel
    $btnCancel.Size = New-Object System.Drawing.Size(110, 32)
    $btnCancel.Location = New-Object System.Drawing.Point(300, 130)
    $btnCancel.Add_Click({ $state.result = "cancel"; $form.Close() }.GetNewClosure())
    $form.Controls.Add($btnCancel)

    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 2000
    $timer.Add_Tick({
        if (Test-PrinterPresent) { $state.result = "found"; $form.Close() }
    }.GetNewClosure())
    $timer.Start()
    $form.Add_FormClosed({ $timer.Stop() }.GetNewClosure())

    [void]$form.ShowDialog()
    $timer.Dispose()
    return $state.result
}

# Пробная печать (и вопрос "напечаталось?"). Вызывается либо в конце установки (если не указан -NoTest), либо отдельно (-TestOnly):
# мастер ставит в setup.ps1 -NoTest, а на последней странице предлагает галочку "Напечатать тестовую страницу", которая запускает -TestOnly.
function Invoke-InstallTest {
Step $S.install_test_step 'test'
if (-not $printerPresent) {
    Warn $S.printer_absent_hint
    try {
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $($S.printer_absent_log)" | Out-File -FilePath (Join-Path $dataDir "install_result.log") -Append -Encoding utf8
    } catch { }
} else {
$has1120 = $false
try { $has1120 = (@(Get-CimInstance -ClassName Win32_PnPEntity -Filter "PNPDeviceID LIKE 'USB\\VID_04A9&PID_262B%'" -ErrorAction Stop).Count -gt 0) } catch { $has1120 = ($serials810.Count -eq 0) }
if (-not (Want "262B")) { $has1120 = $false }
$testRuns = @()
if ($has1120) { $testRuns += ,@() }
foreach ($serial in $serials810) { $testRuns += ,@("--printer", $serial, "--model", "810") }
# Печать запускаем БЕЗ ожидания (страницы идут на принтеры одновременно), сразу показываем вопрос "напечаталось?" - пока пользователь
# смотрит на принтеры, - и только после ответа проверяем коды возврата. capt_print.exe - оконное приложение: оператор "&" не ждёт его
# и $LASTEXITCODE остаётся от прошлой команды (отсюда были ложные "не удалось"), поэтому используем Start-Process -PassThru.
$testProcs = @()
foreach ($extra in $testRuns) {
    try {
        if ($pythonMode) {
            $testProcs += Start-Process -FilePath $exeFull -ArgumentList (@(('"' + "$targetDir\capt_print_redmon.py" + '"'), '--install-test') + $extra) -PassThru -WindowStyle Hidden
        } else {
            $testProcs += Start-Process -FilePath $exeFull -ArgumentList (@('--install-test') + $extra) -PassThru -WindowStyle Hidden
        }
    } catch {
        Warn ($S.install_test_failed + " (" + $_.Exception.Message + ")")
        if (-not $script:StatsIssueStep) { $script:StatsIssueStep = 'test'; $script:StatsIssueCode = 1 }
    }
    Start-Sleep -Seconds 2
}

# Диалог "напечаталось?" (план п.7): пока только локально - ответ пишется в журнал
# рядом с остальными логами, без сервера и без Telegram-бота (решение 08.10.2026,
# отправку на сервер делаем отдельным шагом позже, если понадобится).
# Окно показывается с невидимым владельцем TopMost: установка идёт скрыто из мастера Inno, и без этого
# вопрос иногда оказывался ЗА окном мастера, а установка молча ждала ответа.
function Show-TopMostBox($text, $title, $buttons, $icon) {
    $owner = New-Object System.Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.StartPosition = "CenterScreen"
    $owner.Size = New-Object System.Drawing.Size(1, 1)
    $owner.Opacity = 0
    $owner.Show()
    $owner.Activate()
    try { return [System.Windows.Forms.MessageBox]::Show($owner, $text, $title, $buttons, $icon) }
    finally { $owner.Close(); $owner.Dispose() }
}
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $resultDlg = Show-TopMostBox $S.install_test_question $S.install_test_title `
        ([System.Windows.Forms.MessageBoxButtons]::YesNo) ([System.Windows.Forms.MessageBoxIcon]::Question)
    $resultLine = if ($resultDlg -eq [System.Windows.Forms.DialogResult]::Yes) { $S.install_test_result_yes } else { $S.install_test_result_no }
    $resultPath = Join-Path $dataDir "install_result.log"
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $resultLine" | Out-File -FilePath $resultPath -Append -Encoding utf8
    if ($resultDlg -ne [System.Windows.Forms.DialogResult]::Yes) {
        Show-TopMostBox $S.install_test_no_hint $S.install_test_title `
            ([System.Windows.Forms.MessageBoxButtons]::OK) ([System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    }
} catch {
    Warn ("install_result dialog: " + $_.Exception.Message)
}
# После ответа пользователя: дожидаемся конца печати и проверяем коды возврата.
foreach ($tp in $testProcs) {
    try {
        $tp.WaitForExit()
        if ($tp.ExitCode -eq 0) {
            Ok $S.install_test_sent
        } else {
            Warn $S.install_test_failed
            if (-not $script:StatsIssueStep) { $script:StatsIssueStep = 'test'; $script:StatsIssueCode = $tp.ExitCode }
        }
    } catch {
        Warn ($S.install_test_failed + " (" + $_.Exception.Message + ")")
        if (-not $script:StatsIssueStep) { $script:StatsIssueStep = 'test'; $script:StatsIssueCode = 1 }
    }
}
}
}

# Режим -TestOnly: только пробная печать для уже установленного драйвера (запускается мастером с последней страницы).
if ($TestOnly) {
    $printerPresent = Test-PrinterPresent
    $pfDir = if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }
    $targetDir = Join-Path $pfDir "CaptPrinter"
    $dataDir = Join-Path $env:ProgramData "CaptPrinter"
    $exeFull = Join-Path $targetDir "capt_print.exe"
    $pythonMode = $false
    if (-not (Test-Path $exeFull)) {
        if ((Test-Path (Join-Path $targetDir "capt_print_redmon.py")) -and (Get-Command python -ErrorAction SilentlyContinue)) {
            $pythonMode = $true
            $exeFull = (& python -c "import sys; print(sys.executable)").Trim()
        } else {
            Write-Host "ERROR: $exeFull not found"
            exit 1
        }
    }
    $serials810 = @()
    try {
        $serials810 = @(Get-CimInstance -ClassName Win32_PnPEntity -Filter "PNPDeviceID LIKE 'USB\\VID_04A9&PID_260A%'" -ErrorAction Stop |
            ForEach-Object { ($_.PNPDeviceID -split '\\')[-1] } | Sort-Object -Unique)
    } catch { }
    if (-not (Want "260A")) { $serials810 = @() }
    Invoke-InstallTest
    exit 0
}

# Режим защищённой печати Windows 11: с ним Redmon не ставится (AddMonitor отказывает), поэтому останавливаемся сразу,
# до скачивания Ghostscript, и говорим, как его выключить. Переключатель в Параметрах пишет этот параметр (проверено 23.10 на 26300).
$wpp = (Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\WPP' -ErrorAction SilentlyContinue).WindowsProtectedPrintMode
if ($wpp -eq 1 -and -not $TestOnly) { Fail $S.wpp_enabled $EXIT_WPP }

$printerPresent = Test-PrinterPresent
if (-not $printerPresent) {
    switch (Wait-ForPrinter) {
        "found"  { $printerPresent = $true; Ok $S.printer_found }
        "skip"   { Warn $S.printer_absent_continue }
        default  { Write-Host $S.install_cancelled -ForegroundColor Red; Send-Stats 'error' 1223 'detect'; exit 1 }   # 1223 = отмена пользователем
    }
} else {
    Ok $S.printer_found
}

Step $S.copying_scripts 'copy'
# C:\Program Files\CaptPrinter (64-bit): обычный пользователь не может подменить exe, который Redmon запускает от системы.
# Изменяемые данные (лог, настройки, счётчик) лежат в C:\ProgramData\CaptPrinter. $env:ProgramW6432 - даже если PowerShell 32-битный.
$pfDir = if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }
$targetDir = Join-Path $pfDir "CaptPrinter"
New-Item -ItemType Directory -Force -Path $targetDir > $null
# Папка данных (лог, настройки, счётчик листов): в неё пишут задания разных пользователей Windows -
# даём группе Users право изменения (иначе счётчик/лог другого пользователя не обновятся).
$dataDir = Join-Path $env:ProgramData "CaptPrinter"
New-Item -ItemType Directory -Force -Path $dataDir > $null
& icacls $dataDir /grant "*S-1-5-32-545:(OI)(CI)M" /T /C > $null 2>&1
$pythonMode = [bool]$UsePython
if (-not $pythonMode -and -not (Test-Path "$here\capt_print.exe")) {
    # exe нет (например, удалён антивирусом): запасной путь - Python-скрипты из source\, если Python установлен
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Warn $S.exe_missing_fallback
        $pythonMode = $true
    } else {
        Fail $S.exe_missing
    }
}
if ($pythonMode) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail $S.python_not_found }
    Ok (& python --version 2>&1)
    Step $S.installing_pkgs 'copy'
    # Пакеты должны совпадать с тем, что реально импортирует код: PDF рендерит pypdfium2
    # (перешли с PyMuPDF 06.10.2026), иначе Python-режим падает на 'import pypdfium2'.
    & python -m pip install --quiet pyusb libusb-package pypdfium2 pillow windows-toasts
    # Исходники лежат в корне пакета рядом с setup.ps1 (папки source\ нет - единственная
    # поддерживаемая копия, см. capt_print.spec). Это запасной путь на случай, когда
    # capt_print.exe удалён антивирусом, а Python установлен.
    foreach ($f in @("capt_print2.py", "capt_print_pdf.py", "capt_print_redmon.py", "capt_counter.py")) {
        if (-not (Test-Path "$here\$f")) { Fail ($S.source_missing -f $f) }
        Copy-Item "$here\$f" "$targetDir\" -Force
    }
    $pythonExe = (& python -c "import sys; print(sys.executable)").Trim()
    if (-not $pythonExe) { Fail $S.python_exe_empty }
    $portCommand = $pythonExe
    $portArgsPrefix = '"' + "$targetDir\capt_print_redmon.py" + '" '
} else {
    Copy-Item "$here\capt_print.exe" "$targetDir\" -Force
    $portCommand = "$targetDir\capt_print.exe"
    $portArgsPrefix = ""
}
# Путь программы в команде порта Redmon лучше без пробелов (как Redmon разбирает пробел в пути, документация не гарантирует):
# берём короткое имя 8.3 (C:\PROGRA~1\...); если коротких имён нет - полный путь в кавычках.
$exeFull = $portCommand   # полный путь - для адреса captcounter:// (там своя пара кавычек)
if ($portCommand -match '\s') {
    $shortCmd = $null
    try { $shortCmd = (New-Object -ComObject Scripting.FileSystemObject).GetFile($portCommand).ShortPath } catch {}
    if ($shortCmd -and $shortCmd -notmatch '\s') { $portCommand = $shortCmd } else { $portCommand = '"' + $portCommand + '"' }
}
Write-Host ("Port command: " + $portCommand)
foreach ($f in @("printer_counter.ps1", "Counter.cmd", "Counter_810.cmd", "install_test_page.pdf", "install_test_page_810.pdf", "install_test_page_en.pdf", "install_test_page_810_en.pdf")) {
    if (Test-Path "$here\$f") { Copy-Item "$here\$f" "$targetDir\" -Force }
}
[System.IO.File]::WriteAllText("$targetDir\lang.txt", [string]$Lang, [System.Text.Encoding]::ASCII)
Ok $S.copied

# Кнопка "Картридж заменён - обнулить" в уведомлении о ресурсе картриджа открывает captcounter://reset -
# регистрируем этот адрес за программой драйвера (HKLM: работает для всех пользователей).
try {
    $protoKey = "HKLM:\SOFTWARE\Classes\captcounter"
    New-Item -Path "$protoKey\shell\open\command" -Force > $null
    Set-ItemProperty -Path $protoKey -Name "(default)" -Value "URL:Canon LBP-1120 cartridge counter"
    New-ItemProperty -Path $protoKey -Name "URL Protocol" -Value "" -PropertyType String -Force > $null
    Set-ItemProperty -Path "$protoKey\shell\open\command" -Name "(default)" -Value ('"' + $exeFull + '" ' + $portArgsPrefix + '--counter-reset "%1"')
} catch { Warn ("captcounter: " + $_.Exception.Message) }

Step $S.checking_gs 'gs'
$gsFound = Get-ChildItem "C:\Program Files\gs\gs*\bin\gswin64c.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($gsFound) {
    Ok ($S.already_installed -f $gsFound.FullName)
} else {
    # Официальный адрес один: страница ghostscript.com сама отправляет на GitHub-релиз Artifex. Если он недоступен - окно ручного выбора файла.
    $gsUrls = @("https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10080/gs10080w64.exe")
    $gsPath = "$env:TEMP\gs.exe"
    Write-Host $S.downloading_gs
    $gsFile = Get-VerifiedFile -name 'Ghostscript' -urls $gsUrls -expectedSha256 $GS_SHA256 -destPath $gsPath -failCode $EXIT_GS `
        -pageUrl 'https://ghostscript.com/releases/gsdnld.html' -filter 'Ghostscript (*.exe)|*.exe' -sigName 'Artifex Software, Inc.' -hint $S.dl_hint_gs
    $gsUserFile = $script:UserPickedFile
    $gsProc = Start-Process -FilePath $gsFile -ArgumentList "/S" -PassThru
    Wait-ChildInstaller $gsProc
    if (-not $gsUserFile) { Remove-Item $gsPath -Force -ErrorAction SilentlyContinue }   # файл, выбранный пользователем, не трогаем
    Start-Sleep -Seconds 2
    if (-not (Get-ChildItem "C:\Program Files\gs\gs*\bin\gswin64c.exe" -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        Fail $S.gs_not_installed $EXIT_GS   # окно установщика Ghostscript закрыли или отменили - не делаем вид, что всё в порядке
    }
    # метка "Ghostscript поставлен нашим установщиком": по ней uninstall.ps1 знает, что его можно снять
    try { Set-Content -Path (Join-Path $dataDir "installed_by_us_gs.flag") -Value "1" -ErrorAction Stop } catch { }
    Ok $S.installed
}

$osBuild = [System.Environment]::OSVersion.Version.Build
if ($osBuild -ge 26100) {
    Warn $S.wpp_warning
}

Step $S.checking_redmon 'redmon'
if (Test-Path "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Redirected Port") {
    Ok $S.already_installed2
} else {
    $rmUrls = @("https://www.ghostgum.com.au/download/redmon19.zip")
    $rmPath = "$env:TEMP\redmon.zip"
    # Redmon лежит прямо в пакете установщика (redmon19.zip, GPL, 443 КБ): интернет не нужен. Хэш проверяется как и у скачанного файла.
    # Нет файла или хэш не совпал (например, удалён антивирусом) - прежний путь: скачать, а если не вышло - выбрать вручную.
    $rmBundled = Join-Path $here 'redmon19.zip'
    if ((Test-Path $rmBundled) -and ((Get-FileHash -Path $rmBundled -Algorithm SHA256).Hash -eq $REDMON_SHA256)) {
        $rmFile = $rmBundled
        $rmUserFile = $true   # файл пакета не удаляем (ставит только флаг "не трогать")
        Ok ($S.hash_ok -f $REDMON_SHA256)
    } else {
        Write-Host $S.downloading_rm
        $rmFile = Get-VerifiedFile -name 'Redmon' -urls $rmUrls -expectedSha256 $REDMON_SHA256 -destPath $rmPath -failCode $EXIT_REDMON `
            -pageUrl 'https://www.ghostgum.com.au/software/redmon.htm' -filter 'RedMon (*.zip)|*.zip' -sigName '' -hint $S.dl_hint_rm
        $rmUserFile = $script:UserPickedFile
    }
    $rmDir = "$env:TEMP\redmon_ex"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $rmDir) { Remove-Item $rmDir -Recurse -Force }
    [System.IO.Compression.ZipFile]::ExtractToDirectory($rmFile, $rmDir)
    if (-not $rmUserFile) { Remove-Item $rmPath -Force -ErrorAction SilentlyContinue }
    Push-Location $rmDir
    # Любой параметр командной строки = тихий режим setup.c Redmon 1.9 (без вопроса «Do you want to install...» и окна «установлено»).
    # Раньше вопрос не замечали: на тестовых ВМ Redmon уже стоял. Успех проверяется ниже по ключу «Redirected Port».
    $rmProc = Start-Process -FilePath ".\setup64.exe" -ArgumentList "/S" -PassThru
    Wait-ChildInstaller $rmProc
    Pop-Location
    Remove-Item $rmDir -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    if (-not (Test-Path "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Redirected Port")) {
        Fail $S.rm_not_installed $EXIT_REDMON   # окно установщика Redmon закрыли или отменили
    }
    # метка "Redmon поставлен нашим установщиком" (см. выше про Ghostscript)
    try { Set-Content -Path (Join-Path $dataDir "installed_by_us_redmon.flag") -Value "1" -ErrorAction Stop } catch { }
    Ok $S.installed
}

Step $S.cert_setup 'driver'
$certSubject = "CN=LBP1120 WinUSB Driver"
$cert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $certSubject } | Select-Object -First 1
if ($cert -and $cert.NotAfter -lt (Get-Date)) {
    Warn ($S.cert_expired -f $cert.NotAfter)
    Remove-Item $cert.PSPath -Force -ErrorAction SilentlyContinue
    $cert = $null
}
if (-not $cert) {
    if ((Get-Command New-SelfSignedCertificate -ErrorAction SilentlyContinue) -and (Get-Command New-SelfSignedCertificate).Parameters.ContainsKey("Type")) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $certSubject -CertStoreLocation "Cert:\CurrentUser\My" -KeyUsage DigitalSignature -FriendlyName "LBP1120 Signing" -NotAfter (Get-Date).AddYears(10)
    } else {
        # Windows 8.1 / PowerShell 4: у New-SelfSignedCertificate нет -Type, делаем самоподписанный сертификат через certreq
        $infPath = "$env:TEMP\lbp_cert.inf"
        $cerPath = "$env:TEMP\lbp_cert_new.cer"
        $inf = @(
            '[Version]', 'Signature="$Windows NT$"', '',
            '[NewRequest]', "Subject = `"$certSubject`"", 'KeyLength = 2048', 'KeySpec = 2', 'KeyUsage = 0x80',
            'Exportable = FALSE', 'MachineKeySet = FALSE', 'RequestType = Cert', 'HashAlgorithm = SHA256',
            'ValidityPeriod = Years', 'ValidityPeriodUnits = 10', 'FriendlyName = "LBP1120 Signing"', '',
            '[EnhancedKeyUsageExtension]', 'OID = 1.3.6.1.5.5.7.3.3'
        )
        Set-Content -Path $infPath -Value $inf -Encoding ascii
        Remove-Item $cerPath -Force -ErrorAction SilentlyContinue
        & certreq.exe -new -f $infPath $cerPath > $null
        Remove-Item $infPath -Force -ErrorAction SilentlyContinue
        $cert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $certSubject } | Select-Object -First 1
        if (-not $cert) { throw "Не удалось создать сертификат через certreq" }
    }
    Ok $S.cert_created
} else {
    Ok $S.cert_exists
}

$certFile = "$env:TEMP\cert.cer"
Export-Certificate -Cert $cert -FilePath $certFile -Force > $null
# certutil, not Import-Certificate: on some Windows 11 builds Import-Certificate gets
# Access is denied (0x80070005) on Cert:\LocalMachine\TrustedPublisher even when elevated -
# found 08.10.2026 on a fresh Windows 11 24H2 VM, certutil (native, elevation-aware) works.
& certutil.exe -f -addstore Root $certFile > $null
if ($LASTEXITCODE -ne 0) { throw "certutil -addstore Root failed (exit $LASTEXITCODE)" }
& certutil.exe -f -addstore TrustedPublisher $certFile > $null
if ($LASTEXITCODE -ne 0) { throw "certutil -addstore TrustedPublisher failed (exit $LASTEXITCODE)" }
Ok $S.cert_trusted

Step $S.installing_driver 'driver'
# Копируем во временную папку перед подписью - не мутируем файлы дистрибутива
# (позволяет запускать setup.ps1 с read-only носителя, например с флешки).
$driverTmpDir = "$env:TEMP\LBP1120_usb_driver_sign"
Remove-Item $driverTmpDir -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item "$here\usb_driver" $driverTmpDir -Recurse -Force
$infPath = "$driverTmpDir\Canon_CAPT_USB_Printer.inf"
$catPath = "$driverTmpDir\Canon_CAPT_USB_Printer.cat"
Set-AuthenticodeSignature -FilePath $catPath -Certificate $cert -HashAlgorithm SHA256 -Force > $null
$legacyPnputil = [System.Environment]::OSVersion.Version.Build -lt 14393
if ($legacyPnputil) {
    # Windows 8.1 и старше (до Win10 1607): у pnputil старый синтаксис (-i -a / -e), ключей /add-driver нет
    pnputil -i -a $infPath > $null
} else {
    pnputil /add-driver $infPath /install > $null
}
# ВАЖНО: pnputil часто возвращает ненулевой код (например 259 = ERROR_NO_MORE_ITEMS),
# даже когда пакет успешно установлен/уже был установлен - код возврата не надёжен.
# Проверяем реальное наличие пакета в системе через /enum-drivers, как это уже
# сделано в uninstall.ps1.
if ($legacyPnputil) {
    # старый pnputil -e не показывает имя исходного inf, ищем по поставщику пакета (libwdi)
    $driverPresent = pnputil -e | Select-String -Pattern "libwdi" -Quiet
} else {
    $driverPresent = pnputil /enum-drivers | Select-String -Pattern "canon_capt_usb_printer\.inf" -Quiet
}
if (-not $driverPresent) {
    Fail ($S.driver_verify_failed -f $LASTEXITCODE)
}
Remove-Item $driverTmpDir -Recurse -Force -ErrorAction SilentlyContinue

# LBP-810 (USB PID_260A): отдельный пакет WinUSB, ставится всегда - принтер можно подключить позже.
# Пакет 1120 не затрагивается; ошибка здесь для установки 1120 не критична.
if (Test-Path "$here\usb_driver_810") {
    try {
        $tmp810 = "$env:TEMP\LBP810_usb_driver_sign"
        Remove-Item $tmp810 -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item "$here\usb_driver_810" $tmp810 -Recurse -Force
        Set-AuthenticodeSignature -FilePath "$tmp810\Canon_CAPT_USB_Printer_810.cat" -Certificate $cert -HashAlgorithm SHA256 -Force > $null
        if ($legacyPnputil) { pnputil -i -a "$tmp810\Canon_CAPT_USB_Printer_810.inf" > $null }
        else { pnputil /add-driver "$tmp810\Canon_CAPT_USB_Printer_810.inf" /install > $null }
        Remove-Item $tmp810 -Recurse -Force -ErrorAction SilentlyContinue
        Ok "LBP-810 WinUSB driver"
    } catch { Warn ("LBP-810 driver: " + $_.Exception.Message) }
}

# Сертификат нужен в LocalMachine\Root ТОЛЬКО в момент проверки подписи самим
# pnputil (только что выше) - дальше пакет уже лежит в DriverStore и работает
# независимо от него. Держать самоподписанный корневой сертификат в системе
# постоянно - лишнее ослабление цепочки доверия (снижает планку для ЛЮБОГО
# ПО, подписанного тем же ключом, если он утечёт). Проверено эмпирически
# 23.09.2026: печать и переподключение USB работают без записи в Root.
# TrustedPublisher и сам сертификат в CurrentUser\My оставляем - на будущих
# запусках setup.ps1 сертификат переиспользуется для подписи (иначе каждый
# повторный запуск плодил бы новый oemXX.inf пакет в системе).
Remove-Item "Cert:\LocalMachine\Root\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
Ok $S.driver_installed
Ok $S.cert_root_removed

Step $S.creating_printers 'queue'
$portsKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Redirected Port\Ports"

# One printer, one Redmon port; the dithering mode is an argument of that port
# ("smart" - picks the mode per page area: crisp for text and lines, smooth for photos and
# gradients; a mode chosen by hand in the print dialog, Halftoning, overrides it).
# Основная очередь "Canon LBP-1120" создаётся, только если выбран LBP-1120. Если выбран один LBP-810, пустышки в списке принтеров не будет.
$printers = @()
if (Want "262B") {
    $printers = @(
        @{ Name = "Canon LBP-1120"; Port = "RPT1:"; Mode = "smart" }
    )
}

foreach ($p in $printers) {
    $key = "$portsKey\$($p.Port)"
    $portArgs = $portArgsPrefix + "--dithering " + $p.Mode
    New-Item -Path $key -Force > $null
    Set-ItemProperty -Path $key -Name "Command" -Value $portCommand
    Set-ItemProperty -Path $key -Name "Arguments" -Value $portArgs
    Set-ItemProperty -Path $key -Name "Output" -Value 0 -Type DWord
    Set-ItemProperty -Path $key -Name "ShowWindow" -Value 0 -Type DWord
    Set-ItemProperty -Path $key -Name "RunUser" -Value 1 -Type DWord
}

Warn $S.spooler_restart_warn
Restart-Service -Name Spooler -Force
Start-Sleep -Seconds 2
Ok $S.spooler_restarted

try {
    # Windows 8.1: с -InfPath драйвер не находится (0x80070705), из хранилища добавляется без него
    Add-PrinterDriver -Name "MS Publisher Imagesetter" -ErrorAction Stop > $null
} catch {
    try {
        Add-PrinterDriver -Name "MS Publisher Imagesetter" -InfPath "C:\Windows\inf\ntprint.inf" -ErrorAction Stop > $null
    } catch {
        Warn "Add-PrinterDriver: $($_.Exception.Message)"
    }
}
foreach ($p in $printers) {
    try {
        Add-Printer -Name $p.Name -DriverName "MS Publisher Imagesetter" -PortName $p.Port -ErrorAction Stop > $null
    } catch {
        Warn "Add-Printer: $($_.Exception.Message)"
    }
}
foreach ($p in $printers) {
    if (-not (Get-Printer -Name $p.Name -ErrorAction SilentlyContinue)) {
        Fail ($S.printers_verify_failed -f $p.Name)
    }
}
Ok $S.printers_ready

function Invoke-PpdStep {
    Step $S.installing_ppd 'ppd'
    $ppdScript = "$here\ppd_driver\install_ppd_driver.ps1"
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        # New-FileCatalog (подпись пакета) есть только в PowerShell 5+; на Windows 8.1 шаг пропускаем
        Warn $S.ppd_skipped_oldps
    } elseif (Test-Path $ppdScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ppdScript -Silent
        if ($LASTEXITCODE -eq 0) {
            Ok $S.ppd_installed
        } else {
            Warn $S.ppd_failed
            if (-not $script:StatsIssueStep) { $script:StatsIssueStep = 'ppd'; $script:StatsIssueCode = $LASTEXITCODE }
        }
    } else {
        Warn $S.ppd_failed
        if (-not $script:StatsIssueStep) { $script:StatsIssueStep = 'ppd'; $script:StatsIssueCode = 2 }
    }
}
if (Want "262B") { Invoke-PpdStep }

# Два и более принтера LBP-1120 на одном ПК (редкий случай): кроме основной очереди - отдельная очередь на каждый
# принтер (аргумент порта --printer СЕРИЙНЫЙ), принтер выбирается в окне печати. Нужен Get-PnpDevice (Windows 10+);
# на более старых системах и при одном принтере шаг пропускается. Ошибки не критичны: основная очередь уже работает.
try {
    $serials = @()
    if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) {
        $serials = @(Get-PnpDevice -PresentOnly -ErrorAction Stop |
            Where-Object { $_.InstanceId -like 'USB\VID_04A9&PID_262B\*' } |
            ForEach-Object { ($_.InstanceId -split '\\')[-1] } | Sort-Object -Unique)
    }
    if ($serials.Count -ge 2 -and (Want "262B")) {
        Step $S.extra_queues_step 'queue'
        $queueDriver = "MS Publisher Imagesetter"
        if (Get-PrinterDriver -Name "Canon LBP-1120 (CAPT)" -ErrorAction SilentlyContinue) { $queueDriver = "Canon LBP-1120 (CAPT)" }
        $extra = @()
        $nextPort = 2
        foreach ($serial in $serials) {
            $qName = "Canon LBP-1120 ($serial)"
            $existing = Get-Printer -Name $qName -ErrorAction SilentlyContinue
            if ($existing) {
                $qPort = $existing.PortName
            } else {
                while (Test-Path "$portsKey\RPT${nextPort}:") { $nextPort++ }
                $qPort = "RPT${nextPort}:"
                $nextPort++
            }
            $key = "$portsKey\$qPort"
            New-Item -Path $key -Force > $null
            Set-ItemProperty -Path $key -Name "Command" -Value $portCommand
            Set-ItemProperty -Path $key -Name "Arguments" -Value ($portArgsPrefix + "--dithering smart --printer " + $serial)
            Set-ItemProperty -Path $key -Name "Output" -Value 0 -Type DWord
            Set-ItemProperty -Path $key -Name "ShowWindow" -Value 0 -Type DWord
            Set-ItemProperty -Path $key -Name "RunUser" -Value 1 -Type DWord
            $extra += @{ Name = $qName; Port = $qPort; Serial = $serial; Exists = [bool]$existing }
        }
        Restart-Service -Name Spooler -Force
        Start-Sleep -Seconds 3
        foreach ($q in $extra) {
            try {
                if (-not $q.Exists) {
                    Add-Printer -Name $q.Name -DriverName $queueDriver -PortName $q.Port -ErrorAction Stop > $null
                }
                try { Set-Printer -Name $q.Name -Comment ("Serial: " + $q.Serial) -ErrorAction Stop } catch { }
                Ok ($S.extra_queue_ok -f $q.Name, $q.Serial)
            } catch {
                Warn ($S.extra_queue_fail -f $q.Serial, $_.Exception.Message)
            }
        }
    }
} catch {
    Warn ($S.extra_queue_fail -f "?", $_.Exception.Message)
}

# LBP-810: отдельная очередь "Canon LBP-810" на каждый подключённый принтер (порт Redmon с аргументами
# --printer СЕРИЙНЫЙ --model 810). Без серийного номера очередь не создаём: при двух принтерах она могла бы
# выбрать 1120. Если 810 не подключён сейчас - запустите setup.ps1 ещё раз при подключённом принтере.
$serials810 = @()
try {
    $serials810 = @(Get-CimInstance -ClassName Win32_PnPEntity -Filter "PNPDeviceID LIKE 'USB\\VID_04A9&PID_260A%'" -ErrorAction Stop |
        ForEach-Object { ($_.PNPDeviceID -split '\\')[-1] } | Sort-Object -Unique)
} catch { }
if (-not (Want "260A")) { $serials810 = @() }
foreach ($serial in $serials810) {
    try {
        $qName = if ($serials810.Count -gt 1) { "Canon LBP-810 ($serial)" } else { "Canon LBP-810" }
        $existing = Get-Printer -Name $qName -ErrorAction SilentlyContinue
        if ($existing) { $qPort = $existing.PortName }
        else {
            $n = 2
            while (Test-Path "$portsKey\RPT${n}:") { $n++ }
            $qPort = "RPT${n}:"
        }
        $key = "$portsKey\$qPort"
        New-Item -Path $key -Force > $null
        Set-ItemProperty -Path $key -Name "Command" -Value $portCommand
        Set-ItemProperty -Path $key -Name "Arguments" -Value ($portArgsPrefix + "--dithering smart --printer " + $serial + " --model 810")
        Set-ItemProperty -Path $key -Name "Output" -Value 0 -Type DWord
        Set-ItemProperty -Path $key -Name "ShowWindow" -Value 0 -Type DWord
        Set-ItemProperty -Path $key -Name "RunUser" -Value 1 -Type DWord
        Restart-Service -Name Spooler -Force
        Start-Sleep -Seconds 3
        if (-not $existing) {
            $drv = "MS Publisher Imagesetter"
            if (Get-PrinterDriver -Name "Canon LBP-1120 (CAPT)" -ErrorAction SilentlyContinue) { $drv = "Canon LBP-1120 (CAPT)" }
            Add-Printer -Name $qName -DriverName $drv -PortName $qPort -ErrorAction Stop > $null
        }
        try { Set-Printer -Name $qName -Comment ("Serial: " + $serial) -ErrorAction Stop } catch { }
        Ok ("LBP-810: " + $qName + " (" + $serial + ") -> " + $qPort)
    } catch {
        Warn ("LBP-810 queue ($serial): " + $_.Exception.Message)
    }
}

# Только LBP-810: основной очереди 1120 нет, драйверу с окном настроек нужна хотя бы одна очередь - ставим его теперь, когда очередь 810 создана.
if (-not (Want "262B")) { Invoke-PpdStep }

if (-not $NoTest) { Invoke-InstallTest }

# Статистика: установка дошла до конца. Если пробная страница или окно настроек не получились, это тоже видно (error + этап).
Write-Progress-Key 'done'
if ($script:StatsIssueStep) { Send-Stats 'error' $script:StatsIssueCode $script:StatsIssueStep } else { Send-Stats 'ok' 0 'done' }

Write-Host ""
Write-Host $S.complete -ForegroundColor Green
Write-Host $S.one_printer
Write-Host $S.settings_hint
Write-Host $S.counter_hint
Write-Host ""

if ($SelfDestruct) {
    # Удалённая установка (AnyDesk, п.9a плана): распакованную папку установщика НЕ
    # оставляем на диске клиента. Сам скрипт не может удалить папку, из которой выполняется,
    # пока работает - запускаем отдельный отсоединённый процесс, который подождёт пока
    # setup.ps1/Install.cmd закроются, и удалит папку безвозвратно (rmdir, НЕ Корзина).
    try {
        Write-Host $S.selfdestruct_scheduled -ForegroundColor Yellow
        # Install_AnyDesk.cmd ждёт "Press any key" после этого скрипта - его рабочая папка
        # ещё заблокирована, пока окно открыто. Повторяем попытки удаления (до ~10 раз по
        # 2 сек), пока техник не закроет/не нажмёт клавишу в cmd-окне.
        $cleanupArgs = "/c for /l %i in (1,1,10) do (ping 127.0.0.1 -n 3 >nul & rmdir /s /q `"$here`" 2>nul & if not exist `"$here`" exit /b 0)"
        Start-Process -FilePath "cmd.exe" -ArgumentList $cleanupArgs -WindowStyle Hidden
    } catch {
        Warn ("self-destruct: " + $_.Exception.Message)
    }
}
