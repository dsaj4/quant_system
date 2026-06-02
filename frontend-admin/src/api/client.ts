const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

export type StrategyTemplate = {
  strategy_id: string
  display_name: string
  description: string
  version: string
  supported_scopes: string[]
  supported_frequencies: string[]
  parameters: StrategyParameter[]
  output_contract: string[]
}

export type StrategyParameter = {
  name: string
  label: string
  type: 'number' | 'integer' | 'boolean' | 'select'
  default: number | boolean | string
  description: string
  min_value: number | null
  max_value: number | null
  options: string[]
}

export type LoginResponse = {
  access_token: string
  token_type: string
}

export type UserProfile = {
  id: number
  username: string
}

export type OperationLog = {
  id: number
  actor: string
  action: string
  target_type: string
  target_id: string
  detail: Record<string, unknown>
  created_at: string
}

export type Instrument = {
  id: number
  symbol: string
  exchange: string
  name: string
  asset_type: string
  created_at: string
}

export type InstrumentInput = {
  symbol: string
  exchange: string
  name: string
  asset_type: string
}

export type PortfolioPosition = {
  instrument: Instrument
  weight: number
}

export type Portfolio = {
  id: number
  name: string
  description: string
  positions: PortfolioPosition[]
  created_at: string
}

export type PortfolioInput = {
  name: string
  description: string
  positions: Array<{ instrument_id: number; weight: number }>
}

export type DataImportTask = {
  id: number
  source: string
  instrument_id: number | null
  frequency: string
  adjust: string
  status: string
  message: string
  rows_imported: number
  rows_updated: number
  request_params: Record<string, unknown>
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export type Bar = {
  id: number
  instrument_id: number
  frequency: string
  timestamp: string
  adjust: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  source: string
  data_version: string
}

export type DataCompleteness = {
  instrument_id: number
  frequency: string
  bar_count: number
  first_timestamp: string | null
  last_timestamp: string | null
  expected_interval_minutes: number | null
  expected_bar_count: number | null
  missing_bar_count: number | null
  completeness_ratio: number | null
  gap_count: number
  largest_gap_minutes: number | null
  status: string
  message: string
  calendar_source: string | null
  expected_trading_days: number | null
  missing_trading_days: string[]
  warnings: string[]
}

export type CsvImportInput = {
  instrument_id: number
  frequency: string
  source: string
  csv_text: string
}

export type PublicFetchInput = {
  instrument_id: number
  provider: string
  frequency: string
  start_date: string
  end_date: string
  adjust: string
}

export type MarketDataSchedule = {
  id: number
  instrument_id: number
  provider: string
  frequency: string
  start_date: string
  end_date: string
  adjust: string
  interval_minutes: number
  is_active: boolean
  last_run_at: string | null
  last_status: string | null
  last_message: string
  created_at: string
}

export type MarketDataScheduleInput = {
  instrument_id: number
  provider: string
  frequency: string
  start_date: string
  end_date: string
  adjust: string
  interval_minutes: number
}

export type StrategyParameterSet = {
  id: number
  strategy_id: string
  name: string
  parameters: Record<string, number | boolean | string>
  created_at: string
}

export type StrategyParameterSetInput = {
  strategy_id: string
  name: string
  parameters: Record<string, number | boolean | string>
}

export type BacktestRun = {
  id: number
  strategy_id: string
  parameter_set_id: number | null
  status: string
  config: Record<string, unknown>
  metrics: {
    bar_count?: number
    trade_count?: number
    cumulative_return?: number
    max_drawdown?: number
    win_rate?: number
    profit_loss_ratio?: number
  }
  result_payload: {
    equity_curve?: Array<{ timestamp: string; value: number }>
    benchmark_curve?: Array<{ timestamp: string; value: number }>
    drawdown_curve?: Array<{ timestamp: string; value: number }>
    position_curve?: Array<{ timestamp: string; value: number }>
    candles?: Array<{ timestamp: string; open: number; high: number; low: number; close: number; volume: number }>
    trade_markers?: Array<{ timestamp: string; side: string; price: number }>
    trade_table?: Array<Record<string, unknown>>
    risk_disclosure?: string
    signal_summary?: {
      latest_signal?: string
      latest_decision?: string
      latest_reason?: string
      signal_count?: number
      executed_signal_count?: number
      blocked_signal_count?: number
      grid_percent?: number
      ma_filter_enabled?: boolean
      ma_window?: number
    }
  }
  message: string
  created_at: string
}

export type BacktestInput = {
  instrument_id?: number
  portfolio_id?: number
  frequency: string
  parameter_set_id: number
  initial_cash: number
}

export type PaperRun = {
  id: number
  strategy_id: string
  status: string
  config: {
    instrument_id?: number
    frequency?: string
    parameter_set_id?: number
    initial_cash?: number
    metrics?: {
      trade_count?: number
      latest_signal?: string
      latest_position_percent?: number
    }
    result_payload?: Record<string, unknown>
  }
  latest_equity: number
  message: string
  created_at: string
}

export type PaperRunInput = {
  instrument_id: number
  frequency: string
  parameter_set_id: number
  initial_cash: number
}

export type PublishedSnapshot = {
  id: number
  backtest_run_id: number
  version: number
  status: string
  title: string
  immutable_payload: Record<string, unknown>
  published_at: string | null
  created_at: string
}

export type SnapshotPublishInput = {
  backtest_run_id: number
  title: string
}

export type SnapshotPublishResponse = {
  snapshot: PublishedSnapshot
  share_token: string
}

export type ShareLink = {
  id: number
  snapshot_id: number
  snapshot_title: string
  snapshot_status: string
  is_active: boolean
  expires_at: string | null
  created_at: string
}

export type ShareLinkCreateResponse = {
  share_link: ShareLink
  share_token: string
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail || detail
    } catch {
      // Keep the status-based fallback when the backend does not return JSON.
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function fetchStrategies(): Promise<StrategyTemplate[]> {
  return requestJson<StrategyTemplate[]>('/strategies')
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return requestJson<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function fetchProfile(token: string): Promise<UserProfile> {
  return requestJson<UserProfile>('/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchOperationLogs(token: string): Promise<OperationLog[]> {
  return requestJson<OperationLog[]>('/operation-logs', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchInstruments(token: string): Promise<Instrument[]> {
  return requestJson<Instrument[]>('/instruments', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createInstrument(token: string, input: InstrumentInput): Promise<Instrument> {
  return requestJson<Instrument>('/instruments', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchPortfolios(token: string): Promise<Portfolio[]> {
  return requestJson<Portfolio[]>('/portfolios', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createPortfolio(token: string, input: PortfolioInput): Promise<Portfolio> {
  return requestJson<Portfolio>('/portfolios', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function importCsvMarketData(token: string, input: CsvImportInput): Promise<DataImportTask> {
  return requestJson<DataImportTask>('/market-data/import-csv', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchPublicMarketData(token: string, input: PublicFetchInput): Promise<DataImportTask> {
  return requestJson<DataImportTask>('/market-data/fetch-public', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchMarketBars(
  token: string,
  instrumentId: number,
  frequency = '5m',
  adjust?: string,
): Promise<Bar[]> {
  const params = new URLSearchParams({
    instrument_id: String(instrumentId),
    frequency,
    limit: '20',
  })
  if (adjust !== undefined) {
    params.set('adjust', adjust)
  }
  return requestJson<Bar[]>(`/market-data/bars?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchMarketDataCompleteness(
  token: string,
  instrumentId: number,
  frequency = '5m',
  adjust?: string,
  calendarProvider?: string,
): Promise<DataCompleteness> {
  const params = new URLSearchParams({
    instrument_id: String(instrumentId),
    frequency,
  })
  if (adjust !== undefined) {
    params.set('adjust', adjust)
  }
  if (calendarProvider) {
    params.set('calendar_provider', calendarProvider)
  }
  return requestJson<DataCompleteness>(`/market-data/completeness?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchMarketDataSchedules(token: string): Promise<MarketDataSchedule[]> {
  return requestJson<MarketDataSchedule[]>('/market-data-schedules', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createMarketDataSchedule(
  token: string,
  input: MarketDataScheduleInput,
): Promise<MarketDataSchedule> {
  return requestJson<MarketDataSchedule>('/market-data-schedules', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function runMarketDataSchedule(token: string, scheduleId: number): Promise<void> {
  await requestJson(`/market-data-schedules/${scheduleId}/run-now`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function disableMarketDataSchedule(token: string, scheduleId: number): Promise<MarketDataSchedule> {
  return requestJson<MarketDataSchedule>(`/market-data-schedules/${scheduleId}/disable`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchDataImportTasks(token: string): Promise<DataImportTask[]> {
  return requestJson<DataImportTask[]>('/market-data/import-tasks', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchStrategyParameterSets(token: string): Promise<StrategyParameterSet[]> {
  return requestJson<StrategyParameterSet[]>('/strategy-parameter-sets', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createStrategyParameterSet(
  token: string,
  input: StrategyParameterSetInput,
): Promise<StrategyParameterSet> {
  return requestJson<StrategyParameterSet>('/strategy-parameter-sets', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchBacktests(token: string): Promise<BacktestRun[]> {
  return requestJson<BacktestRun[]>('/backtests', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createBacktest(token: string, input: BacktestInput): Promise<BacktestRun> {
  return requestJson<BacktestRun>('/backtests', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchPaperRuns(token: string): Promise<PaperRun[]> {
  return requestJson<PaperRun[]>('/paper-runs', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createPaperRun(token: string, input: PaperRunInput): Promise<PaperRun> {
  return requestJson<PaperRun>('/paper-runs', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function fetchSnapshots(token: string): Promise<PublishedSnapshot[]> {
  return requestJson<PublishedSnapshot[]>('/snapshots', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function publishSnapshot(token: string, input: SnapshotPublishInput): Promise<SnapshotPublishResponse> {
  return requestJson<SnapshotPublishResponse>('/snapshots/publish', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  })
}

export async function revokeSnapshot(token: string, snapshotId: number): Promise<PublishedSnapshot> {
  return requestJson<PublishedSnapshot>(`/snapshots/${snapshotId}/revoke`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchShareLinks(token: string): Promise<ShareLink[]> {
  return requestJson<ShareLink[]>('/share-links', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function createShareLink(token: string, snapshotId: number): Promise<ShareLinkCreateResponse> {
  return requestJson<ShareLinkCreateResponse>(`/snapshots/${snapshotId}/share-links`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function revokeShareLink(token: string, shareLinkId: number): Promise<ShareLink> {
  return requestJson<ShareLink>(`/share-links/${shareLinkId}/revoke`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
