param(
  [string]$ApiBase = "http://127.0.0.1:8000/api",
  [string]$Username = "admin",
  [string]$Password = "admin",
  [string]$AnalysisDate = "2026-06-03"
)

$ErrorActionPreference = "Stop"

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [string]$Token = ""
  )

  $headers = @{}
  if ($Token) {
    $headers["Authorization"] = "Bearer $Token"
  }

  $parameters = @{
    Method = $Method
    Uri = "$ApiBase$Path"
    Headers = $headers
    ContentType = "application/json"
  }
  if ($null -ne $Body) {
    $parameters["Body"] = ($Body | ConvertTo-Json -Depth 12)
  }
  Invoke-RestMethod @parameters
}

function Require-EnvKey {
  param([string]$Name)
  if (-not [Environment]::GetEnvironmentVariable($Name)) {
    $envPath = Join-Path (Get-Location) ".env"
    if (Test-Path $envPath) {
      $line = Get-Content -Path $envPath -Encoding UTF8 | Where-Object { $_ -match "^$Name\s*=" } | Select-Object -First 1
      if ($line) {
        $value = ($line -split "=", 2)[1].Trim()
        [Environment]::SetEnvironmentVariable($Name, $value, "Process")
      }
    }
  }
  if (-not [Environment]::GetEnvironmentVariable($Name)) {
    throw "$Name is not configured. Set it in the process environment or .env before running the smoke test."
  }
}

Require-EnvKey "DEEPSEEK_API_KEY"
Require-EnvKey "ALPHA_VANTAGE_API_KEY"

$config = Invoke-Api -Method "GET" -Path "/health"
Write-Host "Backend health:" $config.database

$login = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{ username = $Username; password = $Password }
$token = $login.access_token

$narrativeConfig = Invoke-Api -Method "GET" -Path "/narratives/config" -Token $token
if (-not $narrativeConfig.configured) {
  throw "TradingAgents narrative provider is not configured. Check QUANT_TRADING_AGENTS_* settings."
}
Write-Host "Narrative provider configured:" $narrativeConfig.llm_provider $narrativeConfig.model
Write-Host "Selected analysts:" ($narrativeConfig.selected_analysts -join ",")

$instruments = Invoke-Api -Method "GET" -Path "/instruments" -Token $token
$instrument = $instruments | Where-Object { $_.symbol -eq "600519" -and $_.exchange -eq "SH" } | Select-Object -First 1
if (-not $instrument) {
  $instrument = Invoke-Api -Method "POST" -Path "/instruments" -Token $token -Body @{
    symbol = "600519"
    exchange = "SH"
    name = "贵州茅台 TradingAgents Smoke"
    asset_type = "stock"
  }
}

$parameterSets = Invoke-Api -Method "GET" -Path "/strategy-parameter-sets" -Token $token
$parameterSet = $parameterSets | Where-Object { $_.strategy_id -eq "rolling_t_grid" -and $_.name -eq "TradingAgents smoke config" } | Select-Object -First 1
if (-not $parameterSet) {
  $parameterSet = Invoke-Api -Method "POST" -Path "/strategy-parameter-sets" -Token $token -Body @{
    strategy_id = "rolling_t_grid"
    name = "TradingAgents smoke config"
    parameters = @{
      grid_percent = 1.0
      base_position_percent = 50.0
      trade_position_percent = 10.0
      enable_ma_filter = $false
      fee_rate = 0.0
      slippage_bps = 0.0
    }
  }
}

$csv = @"
timestamp,open,high,low,close,volume
2026-01-02 09:35:00,1700,1710,1688,1702,1200
2026-01-02 09:40:00,1702,1720,1698,1718,1300
2026-01-02 09:45:00,1718,1735,1710,1730,1500
2026-01-02 09:50:00,1730,1732,1705,1712,1400
"@

Invoke-Api -Method "POST" -Path "/market-data/import-csv" -Token $token -Body @{
  instrument_id = $instrument.id
  frequency = "5m"
  source = "csv"
  csv_text = $csv
} | Out-Null

$backtest = Invoke-Api -Method "POST" -Path "/backtests" -Token $token -Body @{
  instrument_id = $instrument.id
  frequency = "5m"
  parameter_set_id = $parameterSet.id
  initial_cash = 100000
}
Write-Host "Backtest:" $backtest.id $backtest.status

$narrative = Invoke-Api -Method "POST" -Path "/narratives/generate" -Token $token -Body @{
  backtest_run_id = $backtest.id
  analysis_date = $AnalysisDate
  is_smoke_test = $true
}
Write-Host "Narrative run accepted:" $narrative.id $narrative.status

for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 10
  $current = Invoke-Api -Method "GET" -Path "/narratives/backtests/$($backtest.id)" -Token $token
  Write-Host "Poll" ($i + 1) ":" $current.status
  if ($current.status -in @("succeeded", "degraded", "failed", "reviewed")) {
    Write-Host "Narrative run id:" $current.id
    Write-Host "Status:" $current.status
    Write-Host "Smoke/test:" $current.is_smoke_test
    Write-Host "Provider model:" $current.provider_model
    Write-Host "Can review:" ($current.status -in @("succeeded", "degraded"))
    if ($current.status -eq "failed") {
      throw "TradingAgents smoke failed: $($current.error_message)"
    }
    exit 0
  }
}

throw "TradingAgents smoke did not finish within the polling window."
