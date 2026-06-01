import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

type Point = {
  timestamp: string
  value: number
}

type Candle = {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

type TradeMarker = {
  timestamp: string
  side: string
  price: number
}

type SnapshotPayload = {
  title: string
  strategy_id: string
  strategy_version: string
  backtest_config: Record<string, unknown>
  metrics: {
    cumulative_return?: number
    max_drawdown?: number
    win_rate?: number
    trade_count?: number
    profit_loss_ratio?: number
    bar_count?: number
  }
  result_payload: {
    equity_curve?: Point[]
    benchmark_curve?: Point[]
    drawdown_curve?: Point[]
    candles?: Candle[]
    trade_markers?: TradeMarker[]
    position_curve?: Point[]
    trade_table?: Array<Record<string, unknown>>
    risk_disclosure?: string
  }
  generated_at: string
  publisher: string
  risk_disclosure?: string
}

type PublicSnapshot = {
  id: number
  title: string
  version: number
  payload: SnapshotPayload
  published_at: string | null
}

function getShareToken(): string {
  const params = new URLSearchParams(window.location.search)
  const queryToken = params.get('token')
  if (queryToken) {
    return queryToken
  }
  const pathParts = window.location.pathname.split('/').filter(Boolean)
  return pathParts[pathParts.length - 1] ?? ''
}

function formatPercent(value?: number): string {
  if (typeof value !== 'number') {
    return '-'
  }
  return `${(value * 100).toFixed(2)}%`
}

function formatNumber(value?: number): string {
  if (typeof value !== 'number') {
    return '-'
  }
  return String(value)
}

function buildLinePath(points: Point[], width: number, height: number): string {
  if (!points.length) {
    return ''
  }
  const values = points.map((point) => point.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const range = maxValue - minValue || 1
  return points
    .map((point, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * width
      const y = height - ((point.value - minValue) / range) * height
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function latestValue(points: Point[] = []): number | undefined {
  return points[points.length - 1]?.value
}

function App() {
  const token = useMemo(() => getShareToken(), [])
  const [snapshot, setSnapshot] = useState<PublicSnapshot | null>(null)
  const [loading, setLoading] = useState(() => Boolean(token))
  const [error, setError] = useState(() => (token ? '' : 'Missing share token.'))

  useEffect(() => {
    if (!token) {
      return
    }

    fetch(`${API_BASE_URL}/public/snapshots/${token}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Snapshot request failed: ${response.status}`)
        }
        return response.json() as Promise<PublicSnapshot>
      })
      .then(setSnapshot)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : 'Snapshot request failed.')
      })
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return <main className="state-page">Loading published strategy snapshot...</main>
  }

  if (error || !snapshot) {
    return (
      <main className="state-page">
        <h1>Snapshot unavailable</h1>
        <p>{error || 'The report link is invalid or has been revoked.'}</p>
      </main>
    )
  }

  const payload = snapshot.payload
  const result = payload.result_payload
  const metrics = payload.metrics
  const equityCurve = result.equity_curve ?? []
  const benchmarkCurve = result.benchmark_curve ?? []
  const drawdownCurve = result.drawdown_curve ?? []
  const positionCurve = result.position_curve ?? []
  const candles = result.candles ?? []
  const trades = result.trade_table ?? []
  const markers = result.trade_markers ?? []
  const equityPath = buildLinePath(equityCurve, 760, 260)
  const benchmarkPath = buildLinePath(benchmarkCurve, 760, 260)
  const positionPath = buildLinePath(positionCurve, 360, 180)

  const metricCards = [
    { label: 'Cumulative Return', value: formatPercent(metrics.cumulative_return) },
    { label: 'Max Drawdown', value: formatPercent(metrics.max_drawdown) },
    { label: 'Win Rate', value: formatPercent(metrics.win_rate) },
    { label: 'Trade Count', value: formatNumber(metrics.trade_count) },
    { label: 'Profit/Loss Ratio', value: formatNumber(metrics.profit_loss_ratio) },
    { label: 'Bar Count', value: formatNumber(metrics.bar_count) },
  ]

  return (
    <main className="report-page">
      <section className="report-hero">
        <div>
          <span className="eyebrow">Published Strategy Snapshot</span>
          <h1>{snapshot.title}</h1>
          <p>
            This read-only report is generated from an immutable backend snapshot. It presents reviewed backtest
            results only and does not connect to live trading.
          </p>
        </div>
        <dl className="snapshot-meta">
          <div>
            <dt>Strategy</dt>
            <dd>{payload.strategy_id}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>v{snapshot.version}</dd>
          </div>
          <div>
            <dt>Frequency</dt>
            <dd>{String(payload.backtest_config.frequency ?? '-')}</dd>
          </div>
          <div>
            <dt>Published At</dt>
            <dd>{snapshot.published_at ? new Date(snapshot.published_at).toLocaleString() : '-'}</dd>
          </div>
        </dl>
      </section>

      <section className="metric-strip">
        {metricCards.map((metric) => (
          <article key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="chart-grid">
        <article className="panel wide">
          <header>
            <h2>Equity Curve vs Benchmark</h2>
            <span>Latest equity {latestValue(equityCurve)?.toFixed(2) ?? '-'}</span>
          </header>
          <div className="line-chart">
            <svg viewBox="0 0 760 260" role="img" aria-label="strategy equity curve">
              {benchmarkPath ? <path className="benchmark-line" d={benchmarkPath} /> : null}
              {equityPath ? <path className="strategy-line" d={equityPath} /> : null}
            </svg>
          </div>
        </article>

        <article className="panel">
          <header>
            <h2>Drawdown</h2>
            <span>Risk observation</span>
          </header>
          <div className="drawdown-bars">
            {drawdownCurve.map((point) => (
              <i key={point.timestamp} style={{ height: `${Math.max(Math.abs(point.value) * 100, 2)}%` }} />
            ))}
          </div>
        </article>

        <article className="panel">
          <header>
            <h2>Position Curve</h2>
            <span>Backend snapshot values</span>
          </header>
          <div className="position-chart">
            <svg viewBox="0 0 360 180" role="img" aria-label="position curve">
              {positionPath ? <path className="position-line" d={positionPath} /> : null}
            </svg>
          </div>
        </article>

        <article className="panel wide">
          <header>
            <h2>Candles and Trade Markers</h2>
            <span>{markers.length} markers</span>
          </header>
          <div className="candles">
            {candles.map((candle, index) => (
              <i
                key={`${candle.timestamp}-${index}`}
                className={candle.close >= candle.open ? 'up' : 'down'}
                style={{ height: `${Math.max(Math.abs(candle.close - candle.open) * 40, 20)}px` }}
                title={`${candle.timestamp} close ${candle.close}`}
              />
            ))}
            {markers.slice(0, 6).map((marker, index) => (
              <b
                className={marker.side === 'buy' ? 'buy-marker' : 'sell-marker'}
                key={`${marker.timestamp}-${marker.side}`}
                style={{ left: `${18 + index * 11}%` }}
              >
                {marker.side === 'buy' ? 'B' : 'S'}
              </b>
            ))}
          </div>
        </article>
      </section>

      <section className="panel trade-panel">
        <header>
          <h2>Trade Details</h2>
          <span>Simulated trades saved in the immutable snapshot</span>
        </header>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Price</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, index) => (
              <tr key={index}>
                <td>{String(trade.timestamp ?? '-')}</td>
                <td>{String(trade.side ?? '-')}</td>
                <td>{String(trade.price ?? '-')}</td>
                <td>{String(trade.change_percent ?? '-')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="risk-note">
        <h2>Strategy Description and Risk Disclosure</h2>
        <p>
          {payload.risk_disclosure ??
            result.risk_disclosure ??
            'Backtest results are simulated and do not represent real-money trading.'}
        </p>
      </section>
    </main>
  )
}

export default App
