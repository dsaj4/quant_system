import * as echarts from 'echarts'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts'
import { useEffect, useMemo, useRef, useState } from 'react'
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

type ReportMetadata = {
  strategy_id?: string
  strategy_version?: string
  scope?: string
  scope_label?: string
  target_label?: string
  frequency?: string
  initial_cash?: number
  backtest_period?: {
    start?: string | null
    end?: string | null
  }
  generated_at?: string
  publisher?: string
  warnings?: string[]
  missing_sections?: string[]
}

type ReportAssumptions = {
  data_source?: string
  execution_model?: string
  fees_included?: boolean
  slippage_included?: boolean
  benchmark_method?: string
  frequency?: string
  live_trading?: boolean
}

type DataQuality = {
  status?: string
  bar_count?: number
  sample_warning?: boolean
  message?: string
}

type SnapshotPayload = {
  title: string
  strategy_id: string
  strategy_version: string
  backtest_config: Record<string, unknown>
  report_metadata?: ReportMetadata
  assumptions?: ReportAssumptions
  data_quality?: DataQuality
  metrics: {
    cumulative_return?: number
    max_drawdown?: number
    win_rate?: number
    trade_count?: number
    profit_loss_ratio?: number
    bar_count?: number
  }
  result_payload: {
    strategy_id?: string
    parameters?: Record<string, number | boolean | string>
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
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString()
}

function formatBoolean(value?: boolean): string {
  if (value === true) {
    return '已计入'
  }
  if (value === false) {
    return '未计入'
  }
  return '未记录'
}

function normalizeRiskDisclosure(value?: string): string {
  if (!value) {
    return '回测结果为模拟结果，不代表实盘交易收益。'
  }
  if (value.includes('Backtest results are simulated')) {
    return '回测结果为模拟结果，不代表真实资金交易，也不代表未来收益。'
  }
  return value
}

function chartTime(timestamp: string): Time {
  const parsed = Date.parse(timestamp)
  return Math.floor((Number.isNaN(parsed) ? Date.now() : parsed) / 1000) as Time
}

function tradeValue(trade: Record<string, unknown>, key: string): string {
  const value = trade[key]
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  return typeof value === 'string' ? value : '-'
}

function sideLabel(side: unknown): string {
  if (side === 'buy') {
    return '买入'
  }
  if (side === 'sell') {
    return '卖出'
  }
  return typeof side === 'string' ? side : '-'
}

function targetLabel(payload: SnapshotPayload): string {
  const metadata = payload.report_metadata
  if (metadata?.target_label) {
    return metadata.target_label
  }
  const config = payload.backtest_config
  if (typeof config.portfolio_name === 'string') {
    return config.portfolio_name
  }
  if (typeof config.instrument_symbol === 'string') {
    return config.instrument_symbol
  }
  if (typeof config.portfolio_id === 'number') {
    return `固定组合 #${config.portfolio_id}`
  }
  if (typeof config.instrument_id === 'number') {
    return `标的 #${config.instrument_id}`
  }
  return '未记录标的'
}

function scopeLabel(payload: SnapshotPayload): string {
  const metadata = payload.report_metadata
  if (metadata?.scope_label) {
    return metadata.scope_label
  }
  return payload.backtest_config.portfolio_id ? '固定组合' : '单支股票'
}

function frequencyLabel(payload: SnapshotPayload): string {
  return String(payload.report_metadata?.frequency ?? payload.backtest_config.frequency ?? '-')
}

function EmptyData({ label }: { label: string }) {
  return (
    <div className="empty-data">
      <strong>暂无{label}</strong>
      <span>当前快照没有提供该图表所需的数据。</span>
    </div>
  )
}

function ReportHero({ snapshot }: { snapshot: PublicSnapshot }) {
  const payload = snapshot.payload
  const metadata = payload.report_metadata
  const warnings = metadata?.warnings ?? []
  const period = metadata?.backtest_period
  const generatedAt = metadata?.generated_at ?? payload.generated_at

  return (
    <section className="report-hero">
      <div className="hero-main">
        <div className="report-kicker">
          <span>已审核策略快照</span>
          <span>只读报告</span>
        </div>
        <h1>{snapshot.title}</h1>
        <p>
          本报告基于后端已发布的不可变快照生成，展示 {targetLabel(payload)} 的
          {frequencyLabel(payload)} 历史回测结果。页面仅用于策略效果说明，不连接实盘交易，也不构成收益承诺。
        </p>
        <div className="hero-answer-grid">
          <div>
            <span>策略类型</span>
            <strong>{payload.strategy_id}</strong>
          </div>
          <div>
            <span>评估对象</span>
            <strong>{scopeLabel(payload)} · {targetLabel(payload)}</strong>
          </div>
          <div>
            <span>回测区间</span>
            <strong>{formatDateTime(period?.start)} 至 {formatDateTime(period?.end)}</strong>
          </div>
          <div>
            <span>主要结果</span>
            <strong>{formatPercent(payload.metrics.cumulative_return)} / 回撤 {formatPercent(payload.metrics.max_drawdown)}</strong>
          </div>
        </div>
      </div>
      <aside className="snapshot-ledger">
        <div>
          <span>快照版本</span>
          <strong>v{snapshot.version}</strong>
        </div>
        <div>
          <span>发布时间</span>
          <strong>{formatDateTime(snapshot.published_at)}</strong>
        </div>
        <div>
          <span>生成时间</span>
          <strong>{formatDateTime(generatedAt)}</strong>
        </div>
        <div>
          <span>发布人</span>
          <strong>{metadata?.publisher ?? payload.publisher ?? '-'}</strong>
        </div>
        {warnings.length ? (
          <div className="hero-warning">
            <span>提示</span>
            <strong>{warnings[0]}</strong>
          </div>
        ) : null}
      </aside>
    </section>
  )
}

function MetricStrip({ payload }: { payload: SnapshotPayload }) {
  const metrics = payload.metrics
  const items = [
    { label: '累计收益', value: formatPercent(metrics.cumulative_return), tone: 'positive' },
    { label: '最大回撤', value: formatPercent(metrics.max_drawdown), tone: 'risk' },
    { label: '胜率', value: formatPercent(metrics.win_rate), tone: 'neutral' },
    { label: '交易次数', value: formatNumber(metrics.trade_count), tone: 'neutral' },
    { label: '盈亏比', value: formatNumber(metrics.profit_loss_ratio), tone: 'neutral' },
    { label: '样本K线', value: formatNumber(metrics.bar_count), tone: payload.data_quality?.sample_warning ? 'warning' : 'neutral' },
  ]

  return (
    <section className="metric-strip" aria-label="核心指标">
      {items.map((item) => (
        <article className={`metric-card ${item.tone}`} key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </section>
  )
}

function CurveChart({
  equityCurve,
  benchmarkCurve,
  drawdownCurve,
}: {
  equityCurve: Point[]
  benchmarkCurve: Point[]
  drawdownCurve: Point[]
}) {
  const chartRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!chartRef.current || !equityCurve.length) {
      return
    }

    const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    chart.setOption({
      animationDuration: 450,
      color: ['#0f6b5f', '#475569', '#b42318'],
      tooltip: { trigger: 'axis' },
      legend: { top: 2, right: 8, textStyle: { color: '#4b5563' } },
      grid: { left: 54, right: 42, top: 44, bottom: 38 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: equityCurve.map((point) => point.timestamp),
        axisLabel: { color: '#6b7280' },
        axisLine: { lineStyle: { color: '#d6dde7' } },
      },
      yAxis: [
        {
          type: 'value',
          scale: true,
          axisLabel: { color: '#6b7280' },
          splitLine: { lineStyle: { color: '#e8edf3' } },
        },
        {
          type: 'value',
          axisLabel: { color: '#6b7280', formatter: (value: number) => `${(value * 100).toFixed(0)}%` },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '策略权益',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 3 },
          areaStyle: { opacity: 0.08 },
          data: equityCurve.map((point) => point.value),
        },
        {
          name: '基准',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, type: 'dashed' },
          data: benchmarkCurve.map((point) => point.value),
        },
        {
          name: '回撤',
          type: 'line',
          yAxisIndex: 1,
          symbol: 'none',
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.08 },
          data: drawdownCurve.map((point) => point.value),
        },
      ],
    })

    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [benchmarkCurve, drawdownCurve, equityCurve])

  if (!equityCurve.length) {
    return <EmptyData label="权益曲线" />
  }

  return <div className="echart-canvas" ref={chartRef} />
}

function EquityPanel({ payload }: { payload: SnapshotPayload }) {
  const result = payload.result_payload
  const equityCurve = result.equity_curve ?? []
  const benchmarkCurve = result.benchmark_curve ?? []
  const drawdownCurve = result.drawdown_curve ?? []
  const latestEquity = equityCurve[equityCurve.length - 1]?.value

  return (
    <section className="panel wide">
      <header>
        <div>
          <span className="section-label">收益与风险总览</span>
          <h2>策略权益、基准与回撤</h2>
        </div>
        <strong>期末权益 {formatNumber(latestEquity)}</strong>
      </header>
      <CurveChart equityCurve={equityCurve} benchmarkCurve={benchmarkCurve} drawdownCurve={drawdownCurve} />
    </section>
  )
}

function PositionChart({ points }: { points: Point[] }) {
  const chartRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!chartRef.current || !points.length) {
      return
    }

    const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    chart.setOption({
      animationDuration: 350,
      color: ['#1d4ed8'],
      tooltip: { trigger: 'axis' },
      grid: { left: 44, right: 18, top: 20, bottom: 34 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: points.map((point) => point.timestamp),
        axisLabel: { color: '#6b7280' },
        axisLine: { lineStyle: { color: '#d6dde7' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#6b7280', formatter: (value: number) => `${value}%` },
        splitLine: { lineStyle: { color: '#e8edf3' } },
      },
      series: [
        {
          name: '仓位',
          type: 'line',
          step: 'middle',
          symbol: 'none',
          areaStyle: { opacity: 0.1 },
          lineStyle: { width: 3 },
          data: points.map((point) => point.value),
        },
      ],
    })

    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [points])

  if (!points.length) {
    return <EmptyData label="仓位曲线" />
  }

  return <div className="position-echart" ref={chartRef} />
}

function PositionPanel({ points }: { points: Point[] }) {
  return (
    <section className="panel">
      <header>
        <div>
          <span className="section-label">仓位观察</span>
          <h2>仓位变化</h2>
        </div>
        <strong>{points.length} 个点</strong>
      </header>
      <PositionChart points={points} />
    </section>
  )
}

function DrawdownSummary({ payload }: { payload: SnapshotPayload }) {
  return (
    <section className="panel risk-panel">
      <header>
        <div>
          <span className="section-label">风险摘要</span>
          <h2>最大回撤</h2>
        </div>
        <strong>{payload.data_quality?.status === 'warning' ? '需谨慎解读' : '已记录'}</strong>
      </header>
      <div className="risk-stat">
        <strong>{formatPercent(payload.metrics.max_drawdown)}</strong>
        <span>该值来自已发布快照中的回撤曲线。样本过短时，回撤可能低估真实波动。</span>
      </div>
    </section>
  )
}

function CandleChart({ candles, markers }: { candles: Candle[]; markers: TradeMarker[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current || !candles.length) {
      return
    }

    const chartOptions = {
      autoSize: true,
      height: 350,
      layout: {
        attributionLogo: false,
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#4b5563',
      },
      grid: {
        vertLines: { color: '#eef2f7' },
        horzLines: { color: '#eef2f7' },
      },
      rightPriceScale: { borderColor: '#d6dde7' },
      timeScale: { borderColor: '#d6dde7' },
      crosshair: { mode: 1 },
    }
    const chart: IChartApi = createChart(
      containerRef.current,
      chartOptions as Parameters<typeof createChart>[1],
    )
    const series: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: '#b42318',
      downColor: '#0f6b5f',
      borderUpColor: '#b42318',
      borderDownColor: '#0f6b5f',
      wickUpColor: '#b42318',
      wickDownColor: '#0f6b5f',
    })

    series.setData(
      candles.map((candle) => ({
        time: chartTime(candle.timestamp),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )

    createSeriesMarkers(
      series,
      markers.map(
        (marker): SeriesMarker<Time> => ({
          time: chartTime(marker.timestamp),
          position: marker.side === 'buy' ? 'belowBar' : 'aboveBar',
          color: marker.side === 'buy' ? '#0f6b5f' : '#b42318',
          shape: marker.side === 'buy' ? 'arrowUp' : 'arrowDown',
          text: `${sideLabel(marker.side)} ${marker.price}`,
        }),
      ),
    )
    chart.timeScale().fitContent()

    return () => {
      chart.remove()
    }
  }, [candles, markers])

  if (!candles.length) {
    return <EmptyData label="K线数据" />
  }

  return <div className="candle-chart" ref={containerRef} />
}

function CandlePanel({ candles, markers }: { candles: Candle[]; markers: TradeMarker[] }) {
  return (
    <section className="panel wide">
      <header>
        <div>
          <span className="section-label">交易证据</span>
          <h2>K线与买卖标记</h2>
        </div>
        <strong>{markers.length} 个交易标记</strong>
      </header>
      <CandleChart candles={candles} markers={markers} />
    </section>
  )
}

function TradeTable({ trades }: { trades: Array<Record<string, unknown>> }) {
  return (
    <section className="panel trade-panel">
      <header>
        <div>
          <span className="section-label">交易明细</span>
          <h2>模拟交易记录</h2>
        </div>
        <strong>{trades.length} 笔</strong>
      </header>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>方向</th>
              <th>价格</th>
              <th>触发变化</th>
            </tr>
          </thead>
          <tbody>
            {trades.length ? (
              trades.map((trade, index) => (
                <tr key={index}>
                  <td>{tradeValue(trade, 'timestamp')}</td>
                  <td>
                    <span className={`side-pill ${trade.side === 'buy' ? 'buy' : 'sell'}`}>{sideLabel(trade.side)}</span>
                  </td>
                  <td>{tradeValue(trade, 'price')}</td>
                  <td>{tradeValue(trade, 'change_percent')}%</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4}>当前快照暂无模拟交易记录。</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function AssumptionsPanel({ payload }: { payload: SnapshotPayload }) {
  const assumptions = payload.assumptions ?? {}
  const parameters = payload.result_payload.parameters ?? {}
  const metadata = payload.report_metadata
  const assumptionRows = [
    ['数据来源', assumptions.data_source ?? '已存储K线'],
    ['成交模型', assumptions.execution_model ?? 'V1简化规则回测'],
    ['手续费', formatBoolean(assumptions.fees_included)],
    ['滑点', formatBoolean(assumptions.slippage_included)],
    ['基准说明', assumptions.benchmark_method ?? '未记录'],
  ]

  return (
    <section className="panel assumptions-panel">
      <header>
        <div>
          <span className="section-label">方法透明度</span>
          <h2>参数与回测假设</h2>
        </div>
        <strong>{frequencyLabel(payload)}</strong>
      </header>
      <div className="assumption-grid">
        <div>
          <h3>报告元数据</h3>
          <dl>
            <div>
              <dt>策略版本</dt>
              <dd>{payload.strategy_version ?? metadata?.strategy_version ?? '-'}</dd>
            </div>
            <div>
              <dt>初始资金</dt>
              <dd>{formatNumber(metadata?.initial_cash)}</dd>
            </div>
            <div>
              <dt>评估对象</dt>
              <dd>{scopeLabel(payload)} · {targetLabel(payload)}</dd>
            </div>
          </dl>
        </div>
        <div>
          <h3>回测假设</h3>
          <dl>
            {assumptionRows.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <h3>策略参数</h3>
          <dl>
            {Object.keys(parameters).length ? (
              Object.entries(parameters).map(([name, value]) => (
                <div key={name}>
                  <dt>{name}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))
            ) : (
              <div>
                <dt>参数</dt>
                <dd>未记录</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </section>
  )
}

function RiskDisclosure({ payload }: { payload: SnapshotPayload }) {
  const quality = payload.data_quality
  const metadataWarnings = payload.report_metadata?.warnings ?? []
  const disclosure = normalizeRiskDisclosure(payload.risk_disclosure ?? payload.result_payload.risk_disclosure)
  const risks = [
    '本报告展示的是历史回测结果，并非实盘交易记录。',
    '历史表现不代表未来收益，策略可能在不同市场环境下失效。',
    quality?.message ?? '数据质量说明未完整记录，需结合样本区间和K线数量审慎解读。',
    `手续费：${formatBoolean(payload.assumptions?.fees_included)}；滑点：${formatBoolean(payload.assumptions?.slippage_included)}。`,
  ]

  return (
    <section className="risk-disclosure">
      <div>
        <span className="section-label">风险披露</span>
        <h2>重要说明与数据质量</h2>
        <p>{disclosure}</p>
      </div>
      <div className="risk-list">
        {risks.map((risk) => (
          <article key={risk}>{risk}</article>
        ))}
        {metadataWarnings.map((warning) => (
          <article className="warning-note" key={warning}>{warning}</article>
        ))}
      </div>
    </section>
  )
}

function App() {
  const token = useMemo(() => getShareToken(), [])
  const [snapshot, setSnapshot] = useState<PublicSnapshot | null>(null)
  const [loading, setLoading] = useState(() => Boolean(token))
  const [error, setError] = useState(() => (token ? '' : '缺少分享 Token。'))

  useEffect(() => {
    if (!token) {
      return
    }

    fetch(`${API_BASE_URL}/public/snapshots/${token}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`快照请求失败：${response.status}`)
        }
        return response.json() as Promise<PublicSnapshot>
      })
      .then(setSnapshot)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : '快照请求失败。')
      })
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return <main className="state-page">正在加载已发布策略快照...</main>
  }

  if (error || !snapshot) {
    return (
      <main className="state-page">
        <h1>报告不可用</h1>
        <p>{error || '该报告链接无效，或快照已被撤回。'}</p>
      </main>
    )
  }

  const payload = snapshot.payload
  const result = payload.result_payload

  return (
    <main className="report-page">
      <ReportHero snapshot={snapshot} />
      <MetricStrip payload={payload} />

      <section className="analysis-grid">
        <EquityPanel payload={payload} />
        <DrawdownSummary payload={payload} />
        <PositionPanel points={result.position_curve ?? []} />
        <CandlePanel candles={result.candles ?? []} markers={result.trade_markers ?? []} />
      </section>

      <TradeTable trades={result.trade_table ?? []} />
      <AssumptionsPanel payload={payload} />
      <RiskDisclosure payload={payload} />
    </main>
  )
}

export default App
