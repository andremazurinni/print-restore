# Canon LBP-1120: sheet counter / Счётчик листов Canon LBP-1120.
# Shows how many sheets were printed and how much of the cartridge is used; resets after a cartridge change.
#   printer_counter.ps1               show, then offer to reset (asks Enter / R)
#   printer_counter.ps1 -Reset        reset without asking (new cartridge installed)
#   printer_counter.ps1 -Rated 3000   set the cartridge rated life in sheets (default 2500, Canon EP-22)
#   printer_counter.ps1 -Since 700    set "sheets since cartridge change" (e.g. when the cartridge is already half used)
#   printer_counter.ps1 -Lang ru|en   force the message language (default: Windows UI language)
#   printer_counter.ps1 -Path file    use another counter file (testing)
# The counter is written by the driver to C:\ProgramData\CaptPrinter\counter.json (only jobs printed
# through this driver are counted; the toner estimate is approximate).
param(
    [switch]$Reset,
    [int]$Rated = 0,
    [int]$Since = -1,
    [string]$Lang = "",
    [string]$Model = "1120",   # 810 - счётчик LBP-810 (counter_810.json)
    [string]$Path = ""
)
if (-not $Path) { $Path = Join-Path $env:ProgramData ("CaptPrinter\" + $(if ($Model -eq "810") { "counter_810.json" } else { "counter.json" })) }
$ModelName = if ($Model -eq "810") { "Canon LBP-810" } else { "Canon LBP-1120" }
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$ru = if ($Lang) { $Lang -like "ru*" } else { (Get-UICulture).Name -like "ru*" }
function T($r, $e) { if ($ru) { $r } else { $e } }

function Read-Counter {
    if (-not (Test-Path $Path)) { return $null }
    try { return (Get-Content -Raw -Encoding UTF8 $Path | ConvertFrom-Json) } catch { return $null }
}
function Save-Counter($c) {
    $json = $c | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($Path, $json, (New-Object Text.UTF8Encoding($false)))
}
function Show-Counter($c) {
    $rated = [int]$c.rated_pages; if ($rated -le 0) { $rated = 2500 }
    $since = [int]$c.since_cartridge
    $pct = [math]::Round($since * 100.0 / $rated, 1)
    $filled = [math]::Min(30, [math]::Floor($pct * 30 / 100))
    $bar = ("#" * $filled) + ("." * (30 - $filled))
    Write-Host ""
    Write-Host (T "  ${ModelName}: счётчик листов" "  ${ModelName}: sheet counter") -ForegroundColor Cyan
    Write-Host ("  " + (T "Всего напечатано листов:      " "Total sheets printed:          ") + $c.total)
    Write-Host ("  " + (T "С замены картриджа:           " "Since cartridge change:        ") + $since + (T " из ~" " of ~") + $rated + "  ($pct%)")
    Write-Host ("  [$bar]")
    Write-Host ("  " + (T "Картридж установлен с:       " "Cartridge installed:           ") + $c.cartridge_started)
    if ($c.last_print) { Write-Host ("  " + (T "Последняя печать:            " "Last print:                    ") + $c.last_print) }
    if ($c.by_size) {
        $parts = @(); $c.by_size.PSObject.Properties | ForEach-Object { $parts += ("{0}: {1}" -f $_.Name, $_.Value) }
        if ($parts.Count) { Write-Host ("  " + (T "По размерам:                 " "By size:                      ") + ($parts -join ", ")) }
    }
    if ($c.history -and @($c.history).Count) {
        Write-Host ""
        Write-Host ("  " + (T "Прошлые картриджи (листов):" "Previous cartridges (sheets):")) -ForegroundColor DarkGray
        @($c.history) | ForEach-Object { Write-Host ("    {0}  ->  {1}: {2}" -f $_.from, $_.to, $_.sheets) -ForegroundColor DarkGray }
    }
    if ($pct -ge 100) { Write-Host ("`n  " + (T "Ресурс картриджа выработан - пора менять." "Rated life reached - time to replace the cartridge.")) -ForegroundColor Red }
    elseif ($pct -ge 80) { Write-Host ("`n  " + (T "Картридж скоро закончится - подготовьте новый." "The cartridge is running out - get a new one ready.")) -ForegroundColor Yellow }
    Write-Host ""
}
function Do-Reset($c) {
    if (-not $c.history) { $c | Add-Member -NotePropertyName history -NotePropertyValue @() -Force }
    $entry = [ordered]@{ from = $c.cartridge_started; to = (Get-Date -Format "yyyy-MM-dd HH:mm:ss"); sheets = [int]$c.since_cartridge; rated_pages = [int]$c.rated_pages }
    $c.history = @($c.history) + @([pscustomobject]$entry)
    $c.since_cartridge = 0
    $c.cartridge_started = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $c.notified = @()
    Save-Counter $c
    Write-Host (T "  Готово: счётчик картриджа обнулён (всего листов сохранён)." "  Done: the cartridge counter was reset (the total is kept).") -ForegroundColor Green
}

try {
    $c = Read-Counter
    if (-not $c) {
        Write-Host (T "  Счётчик ещё не создан: напечатайте любую страницу на $ModelName." "  No counter yet: print any page on the $ModelName.") -ForegroundColor Yellow
        if (-not $Reset -and $Rated -le 0) { Read-Host (T "Enter - закрыть" "Press Enter to close") | Out-Null }
        exit 0
    }
    if ($Rated -gt 0) {
        $c.rated_pages = $Rated
        Save-Counter $c
        Write-Host ((T "  Ресурс картриджа задан: " "  Cartridge rated life set: ") + $Rated + (T " листов." " sheets.")) -ForegroundColor Green
    }
    if ($Since -ge 0) {
        $c.since_cartridge = $Since
        $c.notified = @(@(80, 95, 100) | Where-Object { $Since * 100.0 / [int]$c.rated_pages -ge $_ })
        Save-Counter $c
        Write-Host ((T "  Листов с замены картриджа задано: " "  Sheets since cartridge change set: ") + $Since) -ForegroundColor Green
    }
    if ($Reset) { Do-Reset $c; exit 0 }
    Show-Counter $c
    if ($Rated -le 0 -and $Since -lt 0) {
        $ans = Read-Host (T "Enter - закрыть, R - картридж заменён (обнулить счётчик)" "Enter - close, R - cartridge replaced (reset the counter)")
        if ($ans -match '^[RrКк]') { Do-Reset $c; Start-Sleep 2 }
    }
}
catch {
    Write-Host ("FAILED: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host (T "Если нет прав на запись в C:\ProgramData\CaptPrinter - запустите от имени администратора." "If writing to C:\ProgramData\CaptPrinter is denied, run as administrator.")
    Start-Sleep 5
    exit 1
}
