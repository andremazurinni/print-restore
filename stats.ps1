# stats.ps1 - obezlichennyi uchet ustanovok Print Restore (anonymous install statistics).
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI.
# Dot-sourced by setup.ps1 inside try/catch: nothing here may break the installation.
# NOTE: the real API key is not published. Put your own key into $script:StatsKey before building, or leave the placeholder (statistics will simply not be sent).

$script:StatsUrl    = 'https://stat.tat-paket.ru'   # Worker print-restore-stats (also reachable at print-restore-stats.andre-mazurinni.workers.dev)
$script:StatsKey    = 'PUT_YOUR_API_KEY_HERE'
$script:StatsSubKey = 'SOFTWARE\PrintRestore'

# Stable GUID of this computer's installation (created once, kept in HKLM, 64-bit view:
# the 32-bit Inno wizard may start a 32-bit PowerShell, which would otherwise use WOW6432Node).
function Get-StatsInstallId {
    $guidRe = '^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$'
    try {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey('LocalMachine', 'Registry64')
        $key  = $base.CreateSubKey($script:StatsSubKey)
        $id   = [string]$key.GetValue('InstallId', '')
        if ($id -notmatch $guidRe) {
            $id = [guid]::NewGuid().ToString()
            $key.SetValue('InstallId', $id)
        }
        $key.Close(); $base.Close()
        return $id.ToLower()
    } catch {
        # registry unavailable (no admin rights): one id per run, report still works
        if (-not $script:StatsFallbackId) { $script:StatsFallbackId = [guid]::NewGuid().ToString() }
        return $script:StatsFallbackId
    }
}

# Who is installing and is reporting on.
#   Role/Name: command line (/ROLE, /NAME in the wizard) first, then stats.ini next to the installer.
#   stats.ini (UTF-8):  role=helper  /  name=Ivan
#   Helpers always report (no checkbox); clients report unless -NoStats.
function Get-StatsConfig {
    param([string]$Role = '', [string]$Name = '', [switch]$NoStats, [string]$Here = '')
    $ini = @{}
    try {
        $iniPath = Join-Path $Here 'stats.ini'
        if (Test-Path $iniPath) {
            foreach ($line in (Get-Content -LiteralPath $iniPath -Encoding UTF8)) {
                if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.*?)\s*$') { $ini[$Matches[1].ToLower()] = $Matches[2] }
            }
        }
    } catch {}
    if (-not $Role) { $Role = [string]$ini['role'] }
    if (-not $Name) { $Name = [string]$ini['name'] }
    $isHelper = ($Role.Trim().ToLower() -eq 'helper')
    $cleanName = ''
    if ($isHelper) {
        $cleanName = ([string]$Name) -replace '[^\p{L}\p{N} ._-]', ''
        if ($cleanName.Length -gt 32) { $cleanName = $cleanName.Substring(0, 32) }
        $cleanName = $cleanName.Trim()
    }
    return @{
        Role    = $(if ($isHelper) { 'helper' } else { 'client' })
        Name    = $cleanName
        Enabled = ($isHelper -or -not $NoStats)
    }
}

# ---------------------------------------------------------------------------
# Sending. Short timeout, every error swallowed: statistics must never break or stall setup.
# ---------------------------------------------------------------------------
$script:StatsTimeoutSec = 3
$script:StatsPendingMax = 20
$script:StatsPendingPath = Join-Path $env:ProgramData 'CaptPrinter\pending.json'

# PID -> model key for the report. Keep in step with the AddModel table in the installer (.iss)
# and with the MODELS whitelist in stats_worker\worker.js. Value: model key, verified flag.
$script:StatsModels = @{
    '262B' = @('1120', $true)
    '260A' = @('810',  $true)
}

# Returns $true when the report is DONE: accepted (200) or permanently rejected (400/401/413 ... no point
# in retrying). Returns $false only when a retry later makes sense: no network, timeout, 5xx, 429.
function Send-StatsJson([string]$Json) {
    try {
        try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072 } catch {}  # TLS 1.2 (Win 8.1 / PS 4)
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Json)
        $r = Invoke-WebRequest -Uri $script:StatsUrl -Method Post -Body $bytes -ContentType 'application/json' `
              -Headers @{ 'X-Key' = $script:StatsKey } -UseBasicParsing -TimeoutSec $script:StatsTimeoutSec
        return $true
    } catch {
        $code = 0
        try { if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode } } catch {}
        if ($code -ge 400 -and $code -lt 500 -and $code -ne 429) { return $true }
        return $false
    }
}

function Read-StatsPending {
    try {
        if (Test-Path -LiteralPath $script:StatsPendingPath) {
            $raw = Get-Content -LiteralPath $script:StatsPendingPath -Raw -Encoding UTF8
            $arr = $raw | ConvertFrom-Json
            return @(foreach ($x in $arr) { if ($x) { $x } })   # PS 5.1 returns a JSON array as ONE object; foreach unrolls it
        }
    } catch {}
    return @()
}

function Write-StatsPending($Items) {
    try {
        $Items = @($Items)
        if ($Items.Count -eq 0) {
            if (Test-Path -LiteralPath $script:StatsPendingPath) { Remove-Item -LiteralPath $script:StatsPendingPath -Force }
            return
        }
        if ($Items.Count -gt $script:StatsPendingMax) { $Items = @($Items | Select-Object -Last $script:StatsPendingMax) }
        $dir = Split-Path -Parent $script:StatsPendingPath
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        $json = ConvertTo-Json -InputObject $Items -Compress -Depth 5
        [System.IO.File]::WriteAllText($script:StatsPendingPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    } catch {}
}

# Re-send reports saved earlier (no network at that time). The server de-duplicates by install_id.
function Send-StatsPending {
    try {
        $left = @()
        $items = @(Read-StatsPending)
        for ($i = 0; $i -lt $items.Count; $i++) {
            if (-not (Send-StatsJson (ConvertTo-Json -InputObject $items[$i] -Compress -Depth 5))) {
                $left = @($items[$i..($items.Count - 1)])   # network still down: keep this and the rest
                break
            }
        }
        Write-StatsPending $left
    } catch {}
}

# Build and send one report. $Cfg = Get-StatsConfig result; no-op when $Cfg is $null or disabled.
#   $Result 'ok'|'error'; $Step one of: detect copy port driver queue ppd test done; $Code integer (0 = none)
#   $Pids   PIDs of the printers set up (array of 4-hex strings); $DriverVer e.g. '55'
function Send-StatsReport {
    param($Cfg, [string]$Result, [string]$Step, [int]$Code = 0, [string[]]$Pids = @(), [string]$DriverVer = '0')
    try {
        if (-not $Cfg -or -not $Cfg.Enabled) { return }
        $models = @(); $pidList = @(); $verified = $true
        foreach ($p in $Pids) {
            $p = ([string]$p).ToUpper()
            if ($script:StatsModels.ContainsKey($p)) {
                $m = $script:StatsModels[$p]
                if ($models -notcontains $m[0]) { $models += $m[0] }
                if (-not $m[1]) { $verified = $false }
                if ($pidList -notcontains $p) { $pidList += $p }
            }
        }
        if ($models.Count -eq 0) { $models = @('none') }
        $verDigits = ([string]$DriverVer) -replace '[^0-9.]', ''
        if (-not $verDigits) { $verDigits = '0' }
        $rep = [ordered]@{
            install_id = (Get-StatsInstallId)
            role       = $Cfg.Role
            models     = $models
            verified   = $verified
            driver_ver = $verDigits
            win_build  = [string][System.Environment]::OSVersion.Version.Build
            result     = $Result
            step       = $Step
            code       = $Code
        }
        if ($pidList.Count -gt 0)              { $rep['pids'] = $pidList }
        if ($Cfg.Role -eq 'helper' -and $Cfg.Name) { $rep['name'] = $Cfg.Name }
        $json = ConvertTo-Json -InputObject $rep -Compress -Depth 5
        if (Send-StatsJson $json) {
            Send-StatsPending                         # network works: flush old unsent reports
        } else {
            # one pending report per install_id: the server keeps only the latest one anyway
            $others = @(Read-StatsPending | Where-Object { $_.install_id -ne $rep['install_id'] })
            Write-StatsPending ($others + @([pscustomobject]$rep))
        }
    } catch {}
}
