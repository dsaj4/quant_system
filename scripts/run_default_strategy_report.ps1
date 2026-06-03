param(
    [string]$ApiBase = "http://127.0.0.1:8000/api",
    [string]$DisplayBase = "http://127.0.0.1:5184",
    [string]$Symbol = "600519",
    [string]$Exchange = "SH",
    [string]$Name = "贵州茅台",
    [string]$Frequency = "1d",
    [string]$Adjust = "qfq",
    [string]$Provider = "tushare",
    [string]$StartDate = "2024-01-01",
    [string]$EndDate = "2026-05-29",
    [switch]$OpenReport,
    [switch]$ForceFetch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Invoke-JsonPost {
    param(
        [string]$Uri,
        [object]$Body,
        [hashtable]$Headers = @{}
    )

    $json = $Body | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Uri $Uri -Method Post -Headers $Headers -ContentType "application/json" -Body $json
}

function Get-DateValue {
    param([object]$Value)
    if (-not $Value) {
        return $null
    }
    return ([datetime]$Value).Date
}

function Test-BarCoverage {
    param(
        [array]$Bars,
        [string]$RequiredStart,
        [string]$RequiredEnd
    )

    if (-not $Bars -or $Bars.Count -lt 30) {
        return $false
    }

    $start = [datetime]$RequiredStart
    $end = [datetime]$RequiredEnd
    $first = Get-DateValue -Value $Bars[0].timestamp
    $last = Get-DateValue -Value $Bars[$Bars.Count - 1].timestamp
    return ($first -le $start.AddDays(14) -and $last -ge $end.AddDays(-14))
}

function Save-PublicSnapshot {
    param(
        [string]$ShareToken,
        [int]$SnapshotId
    )

    $snapshotRoot = Join-Path $root "data\client-report-snapshots"
    New-Item -ItemType Directory -Force -Path $snapshotRoot | Out-Null

    $publicSnapshot = Invoke-RestMethod -Uri "$ApiBase/public/snapshots/$ShareToken" -Method Get
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $baseName = "snapshot-$SnapshotId-$timestamp"
    $jsonPath = Join-Path $snapshotRoot "$baseName.json"
    $htmlPath = Join-Path $snapshotRoot "$baseName.html"
    $latestPath = Join-Path $snapshotRoot "latest-client-report.json"

    $publicSnapshot | ConvertTo-Json -Depth 80 | Set-Content -Path $jsonPath -Encoding UTF8
    $payload = $publicSnapshot.payload
    $metrics = $payload.metrics
    $metadata = $payload.report_metadata
    $quality = $payload.data_quality
    $title = if ($publicSnapshot.title) { $publicSnapshot.title } else { "Client Report Snapshot" }
    $instrument = if ($metadata.instrument) { $metadata.instrument } else { "" }
    $frequency = if ($metadata.frequency) { $metadata.frequency } else { "" }
    $adjust = if ($metadata.adjust) { $metadata.adjust } else { "" }
    $barCount = if ($metrics.bar_count -ne $null) { $metrics.bar_count } else { "" }
    $cumulativeReturn = if ($metrics.cumulative_return -ne $null) { "{0:P2}" -f [double]$metrics.cumulative_return } else { "" }
    $maxDrawdown = if ($metrics.max_drawdown -ne $null) { "{0:P2}" -f [double]$metrics.max_drawdown } else { "" }
    $winRate = if ($metrics.win_rate -ne $null) { "{0:P2}" -f [double]$metrics.win_rate } else { "" }
    $tradeCount = if ($metrics.trade_count -ne $null) { $metrics.trade_count } else { "" }
    $qualityStatus = if ($quality.status) { $quality.status } else { "" }
    $qualityMessage = if ($quality.message) { $quality.message } else { "" }
    $publicJson = $publicSnapshot | ConvertTo-Json -Depth 80
    $html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>$([System.Security.SecurityElement]::Escape([string]$title))</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f5f7fb; }
    main { max-width: 960px; margin: 0 auto; padding: 32px 20px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .muted { color: #667085; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 24px 0; }
    .card { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
    .label { color: #667085; font-size: 13px; margin-bottom: 6px; }
    .value { font-size: 20px; font-weight: 700; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #101828; color: #f9fafb; border-radius: 8px; padding: 16px; }
  </style>
</head>
<body>
  <main>
    <h1>$([System.Security.SecurityElement]::Escape([string]$title))</h1>
    <p class="muted">Saved local client report snapshot. Share token is not persisted.</p>
    <section class="grid">
      <div class="card"><div class="label">Instrument</div><div class="value">$([System.Security.SecurityElement]::Escape([string]$instrument))</div></div>
      <div class="card"><div class="label">Frequency / Adjust</div><div class="value">$([System.Security.SecurityElement]::Escape([string]"$frequency / $adjust"))</div></div>
      <div class="card"><div class="label">Bars</div><div class="value">$([System.Security.SecurityElement]::Escape([string]$barCount))</div></div>
      <div class="card"><div class="label">Cumulative Return</div><div class="value">$([System.Security.SecurityElement]::Escape([string]$cumulativeReturn))</div></div>
      <div class="card"><div class="label">Max Drawdown</div><div class="value">$([System.Security.SecurityElement]::Escape([string]$maxDrawdown))</div></div>
      <div class="card"><div class="label">Win Rate / Trades</div><div class="value">$([System.Security.SecurityElement]::Escape([string]"$winRate / $tradeCount"))</div></div>
    </section>
    <section class="card">
      <div class="label">Data Quality</div>
      <div class="value">$([System.Security.SecurityElement]::Escape([string]$qualityStatus))</div>
      <p>$([System.Security.SecurityElement]::Escape([string]$qualityMessage))</p>
    </section>
    <h2>Public Snapshot JSON</h2>
    <pre>$([System.Security.SecurityElement]::Escape($publicJson))</pre>
  </main>
</body>
</html>
"@
    Set-Content -Path $htmlPath -Value $html -Encoding UTF8

    [pscustomobject]@{
        saved_at = (Get-Date).ToUniversalTime().ToString("o")
        snapshot_id = $SnapshotId
        json_path = $jsonPath
        html_path = $htmlPath
        token_persisted = $false
    } | ConvertTo-Json -Depth 8 | Set-Content -Path $latestPath -Encoding UTF8

    return [pscustomobject]@{
        json_path = $jsonPath
        html_path = $htmlPath
    }
}

Write-Host "[run] Default strategy report: $Provider / $Symbol.$Exchange / $Frequency / $Adjust / $StartDate -> $EndDate" -ForegroundColor Cyan

$health = Invoke-RestMethod -Uri "$ApiBase/health" -Method Get
Write-Host "[health] status=$($health.status), database=$($health.database), primary_provider=$($health.public_data.primary_provider.name), configured=$($health.public_data.primary_provider.is_configured)"

$login = Invoke-JsonPost -Uri "$ApiBase/auth/login" -Body @{ username = "admin"; password = "admin" }
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$instruments = @((Invoke-RestMethod -Uri "$ApiBase/instruments" -Headers $headers) | ForEach-Object { $_ })
$instrument = @($instruments | Where-Object { $_.symbol -eq $Symbol -and $_.exchange -eq $Exchange } | Select-Object -First 1)[0]
if (-not $instrument) {
    $instrument = Invoke-JsonPost -Uri "$ApiBase/instruments" -Headers $headers -Body @{
        symbol = $Symbol
        exchange = $Exchange
        name = $Name
        asset_type = "stock"
    }
    Write-Host "[instrument] Created $Symbol.$Exchange id=$($instrument.id)."
} else {
    Write-Host "[instrument] Reusing $Symbol.$Exchange id=$($instrument.id)."
}

$dataSourceCalls = 0
$fetchTask = $null
$bars = @((Invoke-RestMethod -Uri "$ApiBase/market-data/bars?instrument_id=$($instrument.id)&frequency=$Frequency&adjust=$Adjust&limit=1000" -Headers $headers) | ForEach-Object { $_ })
$hasCoverage = Test-BarCoverage -Bars $bars -RequiredStart $StartDate -RequiredEnd $EndDate

if ($ForceFetch -or -not $hasCoverage) {
    $dataSourceCalls += 1
    $fetchTask = Invoke-JsonPost -Uri "$ApiBase/market-data/fetch-public" -Headers $headers -Body @{
        instrument_id = [int]$instrument.id
        provider = $Provider
        frequency = $Frequency
        start_date = $StartDate
        end_date = $EndDate
        adjust = $Adjust
    }
    Write-Host "[data] Fetch task id=$($fetchTask.id), imported=$($fetchTask.rows_imported), updated=$($fetchTask.rows_updated)."
    $bars = @((Invoke-RestMethod -Uri "$ApiBase/market-data/bars?instrument_id=$($instrument.id)&frequency=$Frequency&adjust=$Adjust&limit=1000" -Headers $headers) | ForEach-Object { $_ })
} else {
    Write-Host "[data] Reusing existing bars; no external provider call was needed."
}

$quality = Invoke-RestMethod -Uri "$ApiBase/market-data/completeness?instrument_id=$($instrument.id)&frequency=$Frequency&adjust=$Adjust" -Headers $headers
Write-Host "[quality] status=$($quality.status), bars=$($quality.bar_count), range=$($quality.first_timestamp) -> $($quality.last_timestamp)"

$parameterSets = @((Invoke-RestMethod -Uri "$ApiBase/strategy-parameter-sets" -Headers $headers) | ForEach-Object { $_ })
$parameterSet = @($parameterSets | Where-Object { $_.strategy_id -eq "rolling_t_grid" } | Select-Object -First 1)[0]
if (-not $parameterSet) {
    $parameterSet = Invoke-JsonPost -Uri "$ApiBase/strategy-parameter-sets" -Headers $headers -Body @{
        strategy_id = "rolling_t_grid"
        name = "Default rolling T grid"
        parameters = @{}
    }
    Write-Host "[strategy] Created default parameter set id=$($parameterSet.id)."
} else {
    Write-Host "[strategy] Reusing parameter set id=$($parameterSet.id), name=$($parameterSet.name)."
}

$backtest = Invoke-JsonPost -Uri "$ApiBase/backtests" -Headers $headers -Body @{
    instrument_id = [int]$instrument.id
    frequency = $Frequency
    adjust = $Adjust
    parameter_set_id = [int]$parameterSet.id
    initial_cash = 100000
}

$snapshotTitle = "Moutai Default Strategy Report #$($backtest.id)"
$published = Invoke-JsonPost -Uri "$ApiBase/snapshots/publish" -Headers $headers -Body @{
    backtest_run_id = [int]$backtest.id
    title = $snapshotTitle
}

$snapshotId = [int]$published.snapshot.id
$shareToken = $published.share_token
$reportUrl = "$DisplayBase/?token=$shareToken"
$savedSnapshot = Save-PublicSnapshot -ShareToken $shareToken -SnapshotId $snapshotId

$metrics = $backtest.metrics
$firstBar = if ($bars.Count -gt 0) { $bars[0].timestamp } else { $null }
$lastBar = if ($bars.Count -gt 0) { $bars[$bars.Count - 1].timestamp } else { $null }
$costEstimate = [pscustomobject]@{
    provider = $Provider
    external_data_calls = $dataSourceCalls
    market_data_fetch_calls = $dataSourceCalls
    completeness_calendar_calls = 0
    note = if ($dataSourceCalls -eq 0) { "Reused local bars; no new external data provider call." } else { "Added 1 $Provider market-data API call; no trading-calendar API call." }
}

$runRoot = Join-Path $root "data\strategy-run-reports"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$runPath = Join-Path $runRoot ("default-run-{0}-backtest-{1}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"), $backtest.id)

[pscustomobject]@{
    saved_at = (Get-Date).ToUniversalTime().ToString("o")
    instrument = "$Symbol.$Exchange"
    provider = $Provider
    frequency = $Frequency
    adjust = $Adjust
    requested_range = @{ start = $StartDate; end = $EndDate }
    observed_range = @{ first_bar = $firstBar; last_bar = $lastBar; bar_count = $quality.bar_count }
    import_task = if ($fetchTask) { @{ id = $fetchTask.id; rows_imported = $fetchTask.rows_imported; rows_updated = $fetchTask.rows_updated; status = $fetchTask.status } } else { $null }
    backtest_id = $backtest.id
    snapshot_id = $snapshotId
    metrics = $metrics
    data_quality = $quality
    cost_estimate = $costEstimate
    public_snapshot_json = $savedSnapshot.json_path
    public_snapshot_html = $savedSnapshot.html_path
    token_persisted = $false
} | ConvertTo-Json -Depth 80 | Set-Content -Path $runPath -Encoding UTF8

Write-Host ""
Write-Host "[result] backtest_id=$($backtest.id), snapshot_id=$snapshotId" -ForegroundColor Green
Write-Host ("[metrics] cumulative_return={0:P2}, max_drawdown={1:P2}, win_rate={2:P2}, trade_count={3}" -f [double]$metrics.cumulative_return, [double]$metrics.max_drawdown, [double]$metrics.win_rate, $metrics.trade_count)
Write-Host "[save] public snapshot json: $($savedSnapshot.json_path)"
Write-Host "[save] public snapshot html: $($savedSnapshot.html_path)"
Write-Host "[save] run summary: $runPath"
Write-Host "[cost] provider=$Provider, external_data_calls=$($costEstimate.external_data_calls), note=$($costEstimate.note)" -ForegroundColor Cyan
Write-Host "[url] client report URL: $reportUrl"

if ($OpenReport) {
    Start-Process $reportUrl
}
