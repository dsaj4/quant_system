import * as echarts from 'echarts'
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
  pnl_percent?: number
  reason?: string
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
  calendar_source?: string | null
  expected_trading_days?: number | null
  missing_trading_days?: string[]
  warnings?: string[]
}

type ReportSummary = {
  performance_summary?: string
  risk_summary?: string
  method_summary?: string
}

type DataSummary = {
  data_source?: string
  provider?: string
  frequency?: string
  adjust?: string | null
  bar_count?: number
  period_start?: string | null
  period_end?: string | null
}

type RiskMetrics = {
  max_drawdown?: number
  annualized_volatility?: number
  sharpe_ratio?: number
  calmar_ratio?: number
  return_drawdown_ratio?: number
}

type TradeSummary = {
  trade_count?: number
  buy_count?: number
  sell_count?: number
  win_rate?: number
  average_win?: number
  average_loss?: number
  profit_loss_ratio?: number
  first_trade_at?: string | null
  last_trade_at?: string | null
}

type TechnicalIndicators = {
  ma?: Record<string, Point[] | number[] | undefined>
  macd?: {
    dif?: Point[] | number[]
    dea?: Point[] | number[]
    hist?: Point[] | number[]
  }
}

type SignalSummary = {
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

type SnapshotPayload = {
  title: string
  strategy_id: string
  strategy_version: string
  backtest_config?: Record<string, unknown>
  report_metadata?: ReportMetadata
  report_summary?: ReportSummary
  data_summary?: DataSummary
  risk_metrics?: RiskMetrics
  trade_summary?: TradeSummary
  assumptions?: ReportAssumptions
  data_quality?: DataQuality
  technical_indicators?: TechnicalIndicators
  signal_summary?: SignalSummary
  metrics: {
    cumulative_return?: number
    annualized_return?: number
    max_drawdown?: number
    win_rate?: number
    trade_count?: number
    profit_loss_ratio?: number
    sharpe_ratio?: number
    annualized_volatility?: number
    calmar_ratio?: number
    return_drawdown_ratio?: number
    average_win?: number
    average_loss?: number
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
    technical_indicators?: TechnicalIndicators
    signal_summary?: SignalSummary
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

type Tone = 'positive' | 'negative' | 'warning' | 'neutral'

type TooltipItem = {
  seriesName?: string
  dataIndex?: number
}

type BarColorParam = {
  data?: unknown
}

function normalizePayload(payload: SnapshotPayload, fallbackTitle: string): SnapshotPayload {
  return {
    ...payload,
    title: payload.title ?? fallbackTitle,
    strategy_id: payload.strategy_id ?? 'unknown',
    strategy_version: payload.strategy_version ?? '-',
    backtest_config: payload.backtest_config ?? {},
    metrics: payload.metrics ?? {},
    result_payload: payload.result_payload ?? {},
    generated_at: payload.generated_at ?? '',
    publisher: payload.publisher ?? '',
  }
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

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function formatPercent(value?: number, digits = 2): string {
  if (!isFiniteNumber(value)) {
    return '-'
  }
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(digits)}%`
}

function formatRatio(value?: number): string {
  if (!isFiniteNumber(value)) {
    return '-'
  }
  return value.toFixed(2)
}

function formatNumber(value?: number, digits = 2): string {
  if (!isFiniteNumber(value)) {
    return '-'
  }
  return value.toLocaleString('zh-CN', { maximumFractionDigits: digits })
}

function formatMoney(value?: number): string {
  if (!isFiniteNumber(value)) {
    return '-'
  }
  return value.toLocaleString('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  })
}

function formatDate(value?: string | null): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 10)
  }
  return date.toLocaleDateString('zh-CN')
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', { hour12: false })
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
    return '本报告基于历史数据回测生成，不代表真实资金交易记录，也不构成收益承诺。'
  }
  if (value.includes('Backtest results are simulated')) {
    return '回测结果为模拟结果，不代表真实资金交易，也不代表未来收益。'
  }
  return value
}

function targetLabel(payload: SnapshotPayload): string {
  const metadata = payload.report_metadata
  if (metadata?.target_label) {
    return metadata.target_label
  }
  const config = payload.backtest_config ?? {}
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
  return payload.backtest_config?.portfolio_id ? '固定组合' : '单一标的'
}

function frequencyLabel(payload: SnapshotPayload): string {
  return String(payload.report_metadata?.frequency ?? payload.assumptions?.frequency ?? payload.backtest_config?.frequency ?? '-')
}

function tradeValue(trade: Record<string, unknown>, key: string): string {
  const value = trade[key]
  if (typeof value === 'number') {
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 4 })
  }
  return typeof value === 'string' ? value : '-'
}

function sideLabel(side: unknown): string {
  if (side === 'buy' || side === 'open_long') {
    return '买入'
  }
  if (side === 'sell' || side === 'close_long') {
    return '卖出'
  }
  return typeof side === 'string' ? side : '-'
}

function signalLabel(signal?: string): string {
  if (!signal || signal === 'hold') {
    return '观望'
  }
  return sideLabel(signal)
}

function decisionLabel(decision?: string): string {
  switch (decision) {
    case 'executed':
      return '已执行'
    case 'blocked_by_ma_filter':
      return '被均线过滤'
    case 'skipped_no_available_cash_or_position':
      return '资金或仓位不足'
    case 'hold':
      return '未触发'
    default:
      return decision || '-'
  }
}

function sideTone(side: unknown): 'buy' | 'sell' {
  return side === 'buy' || side === 'open_long' ? 'buy' : 'sell'
}

function dateKey(timestamp: string): string {
  return timestamp.includes('T') || timestamp.includes(' ')
    ? timestamp.slice(0, 16).replace('T', ' ')
    : timestamp
}

function normalizePositionValue(value: number): number {
  return Math.abs(value) <= 1 ? value * 100 : value
}

function volumeBarColor(params: BarColorParam): string {
  const data = Array.isArray(params.data) ? params.data : []
  return Number(data[2]) > 0 ? '#f97316' : '#3b82f6'
}

function macdBarColor(params: BarColorParam): string {
  return Number(params.data) >= 0 ? '#f97316' : '#3b82f6'
}

function EmptyData({ label }: { label: string }) {
  return (
    <div className="empty-data">
      <strong>暂无{label}</strong>
      <span>当前快照没有提供该图表所需的数据。</span>
    </div>
  )
}

function useEchart(
  ref: React.RefObject<HTMLDivElement | null>,
  optionFactory: () => echarts.EChartsOption | null,
  deps: React.DependencyList,
) {
  useEffect(() => {
    if (!ref.current) {
      return
    }
    const option = optionFactory()
    if (!option) {
      return
    }

    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' })
    chart.setOption(option)

    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

function metricTone(value?: number, negativeIsGood = false): Tone {
  if (!isFiniteNumber(value)) {
    return 'neutral'
  }
  if (value === 0) {
    return 'neutral'
  }
  const good = negativeIsGood ? value < 0 : value > 0
  return good ? 'positive' : 'negative'
}

function ReportHero({ snapshot }: { snapshot: PublicSnapshot }) {
  const payload = normalizePayload(snapshot.payload, snapshot.title)
  const metadata = payload.report_metadata
  const warnings = metadata?.warnings ?? []
  const period = metadata?.backtest_period
  const generatedAt = metadata?.generated_at ?? payload.generated_at
  const publishedAt = snapshot.published_at
  const title = snapshot.title || payload.title || '策略展示报告'

  return (
    <section className="report-hero">
      <div className="hero-copy">
        <div className="report-kicker">
          <span>已发布快照</span>
          <span>只读客户报告</span>
          <span>版本 {snapshot.version}</span>
        </div>
        <h1>{title}</h1>
        <p>
          本报告展示 {targetLabel(payload)} 在 {frequencyLabel(payload)} 周期下的历史回测表现。
          数据来自已发布的不可变快照，页面仅用于策略效果说明，不连接实盘交易，也不构成投资收益承诺。
        </p>
      </div>

      <div className="hero-metrics">
        <div className="hero-return">
          <span>累计收益</span>
          <strong>{formatPercent(payload.metrics.cumulative_return)}</strong>
          <em>最大回撤 {formatPercent(payload.metrics.max_drawdown)}</em>
        </div>
        <div className="hero-ledger">
          <div>
            <span>评估对象</span>
            <strong>{scopeLabel(payload)} · {targetLabel(payload)}</strong>
          </div>
          <div>
            <span>回测区间</span>
            <strong>{formatDate(period?.start)} 至 {formatDate(period?.end)}</strong>
          </div>
          <div>
            <span>生成时间</span>
            <strong>{formatDateTime(generatedAt)}</strong>
          </div>
          <div>
            <span>发布状态</span>
            <strong>{publishedAt ? `已发布 ${formatDateTime(publishedAt)}` : '未记录发布时间'}</strong>
          </div>
        </div>
      </div>

      {(warnings.length > 0 || payload.data_quality?.sample_warning) && (
        <div className="hero-warning">
          <strong>解读提示</strong>
          <span>
            {warnings[0] ?? '样本数量偏少，收益和回撤可能不能充分反映完整市场环境。'}
          </span>
        </div>
      )}
    </section>
  )
}

function MetricStrip({ payload }: { payload: SnapshotPayload }) {
  const metrics = payload.metrics
  const riskMetrics = payload.risk_metrics ?? {}
  const items: Array<{ label: string; value: string; hint: string; tone: Tone }> = [
    {
      label: '累计收益',
      value: formatPercent(metrics.cumulative_return),
      hint: '策略期末收益',
      tone: metricTone(metrics.cumulative_return),
    },
    {
      label: '年化收益',
      value: formatPercent(metrics.annualized_return),
      hint: '按回测区间折算',
      tone: metricTone(metrics.annualized_return),
    },
    {
      label: '最大回撤',
      value: formatPercent(metrics.max_drawdown),
      hint: '风险暴露峰值',
      tone: 'negative',
    },
    {
      label: '胜率',
      value: formatPercent(metrics.win_rate),
      hint: '盈利交易占比',
      tone: metricTone(metrics.win_rate),
    },
    {
      label: '盈亏比',
      value: formatRatio(metrics.profit_loss_ratio),
      hint: '平均盈利/平均亏损',
      tone: metricTone((metrics.profit_loss_ratio ?? 0) - 1),
    },
    {
      label: '夏普比率',
      value: formatRatio(metrics.sharpe_ratio ?? riskMetrics.sharpe_ratio),
      hint: '年化收益/波动',
      tone: metricTone(metrics.sharpe_ratio ?? riskMetrics.sharpe_ratio),
    },
    {
      label: '交易次数',
      value: formatNumber(metrics.trade_count, 0),
      hint: `${formatNumber(metrics.bar_count ?? payload.data_quality?.bar_count, 0)} 根样本 K 线`,
      tone: payload.data_quality?.sample_warning ? 'warning' : 'neutral',
    },
  ]

  return (
    <section className="metric-strip" aria-label="核心指标">
      {items.map((item) => (
        <article className={`metric-card ${item.tone}`} key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <em>{item.hint}</em>
        </article>
      ))}
    </section>
  )
}

function ReportSummaryPanel({ payload }: { payload: SnapshotPayload }) {
  const summary = payload.report_summary
  const data = payload.data_summary
  const risk = payload.risk_metrics ?? {}
  const trade = payload.trade_summary
  const metrics = payload.metrics
  const cards = [
    {
      label: '表现解读',
      value:
        summary?.performance_summary ??
        `${targetLabel(payload)} 累计收益 ${formatPercent(metrics.cumulative_return)}，最大回撤 ${formatPercent(metrics.max_drawdown)}。`,
    },
    {
      label: '风险解读',
      value:
        summary?.risk_summary ??
        `年化波动 ${formatPercent(metrics.annualized_volatility ?? risk.annualized_volatility)}，Calmar ${formatRatio(metrics.calmar_ratio ?? risk.calmar_ratio)}。`,
    },
    {
      label: '方法说明',
      value:
        summary?.method_summary ??
        `周期 ${frequencyLabel(payload)}，复权 ${data?.adjust || '未指定'}，数据源 ${data?.provider ?? payload.assumptions?.data_source ?? '已存储K线'}。`,
    },
  ]
  const facts = [
    ['数据源', data?.provider ?? payload.assumptions?.data_source ?? '已存储K线'],
    ['复权', data?.adjust || '未指定'],
    ['样本', `${formatNumber(data?.bar_count ?? payload.data_quality?.bar_count ?? metrics.bar_count, 0)} 根K线`],
    ['交易', `${formatNumber(trade?.trade_count ?? metrics.trade_count, 0)} 笔 · 买 ${formatNumber(trade?.buy_count, 0)} / 卖 ${formatNumber(trade?.sell_count, 0)}`],
    ['波动率', formatPercent(metrics.annualized_volatility ?? risk.annualized_volatility)],
    ['收益回撤比', formatRatio(metrics.return_drawdown_ratio ?? risk.return_drawdown_ratio)],
  ]

  return (
    <section className="summary-panel">
      <div className="summary-copy">
        {cards.map((item) => (
          <article key={item.label}>
            <span className="section-label">{item.label}</span>
            <p>{item.value}</p>
          </article>
        ))}
      </div>
      <div className="summary-facts">
        {facts.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
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

  useEchart(
    chartRef,
    () => {
      if (!equityCurve.length) {
        return null
      }
      const dates = equityCurve.map((point) => dateKey(point.timestamp))
      return {
        animationDuration: 650,
        color: ['#0f766e', '#475569', '#dc2626'],
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          borderColor: '#334155',
          textStyle: { color: '#f8fafc' },
        },
        legend: {
          top: 0,
          right: 4,
          itemWidth: 18,
          itemHeight: 8,
          textStyle: { color: '#475569' },
        },
        grid: { left: 54, right: 46, top: 42, bottom: 36 },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: dates,
          axisLabel: { color: '#64748b' },
          axisLine: { lineStyle: { color: '#cbd5e1' } },
          axisTick: { show: false },
        },
        yAxis: [
          {
            type: 'value',
            scale: true,
            axisLabel: { color: '#64748b' },
            splitLine: { lineStyle: { color: '#e2e8f0' } },
          },
          {
            type: 'value',
            axisLabel: { color: '#64748b', formatter: (value: number) => `${(value * 100).toFixed(0)}%` },
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
            name: '基准走势',
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
            areaStyle: { opacity: 0.1 },
            data: drawdownCurve.map((point) => point.value),
          },
        ],
      }
    },
    [benchmarkCurve, drawdownCurve, equityCurve],
  )

  if (!equityCurve.length) {
    return <EmptyData label="收益曲线" />
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
    <section className="panel wide overview-panel">
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

function extractIndicatorSeries(
  source: TechnicalIndicators | undefined,
  key: string,
  dates: string[],
): Array<number | null> {
  const value = source?.ma?.[key]
  if (!Array.isArray(value)) {
    return []
  }
  return dates.map((_, index) => {
    const item = value[index]
    if (typeof item === 'number') {
      return item
    }
    return isFiniteNumber(item?.value) ? item.value : null
  })
}

function extractMacdSeries(
  source: TechnicalIndicators | undefined,
  key: 'dif' | 'dea' | 'hist',
  dates: string[],
): Array<number | null> {
  const value = source?.macd?.[key]
  if (!Array.isArray(value)) {
    return []
  }
  return dates.map((_, index) => {
    const item = value[index]
    if (typeof item === 'number') {
      return item
    }
    return isFiniteNumber(item?.value) ? item.value : null
  })
}

function calculateMA(candles: Candle[], period: number): Array<number | null> {
  return candles.map((_, index) => {
    if (index < period - 1) {
      return null
    }
    const window = candles.slice(index - period + 1, index + 1)
    const total = window.reduce((sum, candle) => sum + candle.close, 0)
    return Number((total / period).toFixed(3))
  })
}

function ema(values: number[], period: number): number[] {
  const alpha = 2 / (period + 1)
  return values.reduce<number[]>((acc, value, index) => {
    acc[index] = index === 0 ? value : value * alpha + acc[index - 1] * (1 - alpha)
    return acc
  }, [])
}

function calculateMACD(candles: Candle[]) {
  const closes = candles.map((candle) => candle.close)
  const ema12 = ema(closes, 12)
  const ema26 = ema(closes, 26)
  const dif = closes.map((_, index) => ema12[index] - ema26[index])
  const dea = ema(dif, 9)
  const hist = dif.map((value, index) => (value - dea[index]) * 2)
  return {
    dif: dif.map((value) => Number(value.toFixed(4))),
    dea: dea.map((value) => Number(value.toFixed(4))),
    hist: hist.map((value) => Number(value.toFixed(4))),
  }
}

function KlineEvidenceChart({
  candles,
  markers,
  indicators,
}: {
  candles: Candle[]
  markers: TradeMarker[]
  indicators?: TechnicalIndicators
}) {
  const chartRef = useRef<HTMLDivElement | null>(null)

  useEchart(
    chartRef,
    () => {
      if (!candles.length) {
        return null
      }

      const dates = candles.map((candle) => dateKey(candle.timestamp))
      const ohlc = candles.map((candle) => [candle.open, candle.close, candle.low, candle.high])
      const volume = candles.map((candle, index) => [
        index,
        candle.volume,
        candle.close >= candle.open ? 1 : -1,
      ])
      const sourceIndicators = indicators
      const ma5 = extractIndicatorSeries(sourceIndicators, 'ma5', dates)
      const ma20 = extractIndicatorSeries(sourceIndicators, 'ma20', dates)
      const ma60 = extractIndicatorSeries(sourceIndicators, 'ma60', dates)
      const macdFromPayload = {
        dif: extractMacdSeries(sourceIndicators, 'dif', dates),
        dea: extractMacdSeries(sourceIndicators, 'dea', dates),
        hist: extractMacdSeries(sourceIndicators, 'hist', dates),
      }
      const macdFallback = calculateMACD(candles)
      const buyMarkers = markers
        .filter((marker) => sideTone(marker.side) === 'buy')
        .map((marker) => [dateKey(marker.timestamp), marker.price, marker.reason ?? '买入'])
      const sellMarkers = markers
        .filter((marker) => sideTone(marker.side) === 'sell')
        .map((marker) => [dateKey(marker.timestamp), marker.price, marker.reason ?? '卖出'])

      return {
        animationDuration: 500,
        backgroundColor: 'transparent',
        color: ['#f97316', '#facc15', '#38bdf8', '#a78bfa', '#3b82f6', '#10b981', '#ef4444'],
        axisPointer: {
          link: [{ xAxisIndex: 'all' }],
          label: { backgroundColor: '#0f172a' },
        },
        legend: {
          top: 8,
          right: 20,
          itemWidth: 18,
          itemHeight: 8,
          textStyle: { color: '#cbd5e1' },
          data: ['K线', 'MA5', 'MA20', 'MA60', '成交量', 'MACD'],
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(2, 6, 23, 0.95)',
          borderColor: '#334155',
          textStyle: { color: '#e2e8f0' },
          formatter: (params: unknown) => {
            const list: TooltipItem[] = Array.isArray(params) ? params : []
            const candleParam = list.find((item) => item.seriesName === 'K线')
            const index = candleParam?.dataIndex ?? 0
            const candle = candles[index]
            if (!candle) {
              return ''
            }
            const rows = [
              `<b>${dates[index]}</b>`,
              `开盘 ${formatNumber(candle.open)} / 收盘 ${formatNumber(candle.close)}`,
              `最高 ${formatNumber(candle.high)} / 最低 ${formatNumber(candle.low)}`,
              `成交量 ${formatNumber(candle.volume, 0)}`,
            ]
            markers
              .filter((marker) => dateKey(marker.timestamp) === dates[index])
              .forEach((marker) => rows.push(`${sideLabel(marker.side)} ${formatNumber(marker.price)} ${marker.reason ?? ''}`))
            return rows.join('<br/>')
          },
        },
        grid: [
          { left: 64, right: 48, top: 48, height: '54%' },
          { left: 64, right: 48, top: '66%', height: '12%' },
          { left: 64, right: 48, top: '81%', height: '12%' },
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            boundaryGap: true,
            axisLine: { lineStyle: { color: '#334155' } },
            axisLabel: { color: '#94a3b8' },
            axisTick: { show: false },
          },
          {
            type: 'category',
            gridIndex: 1,
            data: dates,
            boundaryGap: true,
            axisLine: { lineStyle: { color: '#334155' } },
            axisLabel: { show: false },
            axisTick: { show: false },
          },
          {
            type: 'category',
            gridIndex: 2,
            data: dates,
            boundaryGap: true,
            axisLine: { lineStyle: { color: '#334155' } },
            axisLabel: { color: '#94a3b8' },
            axisTick: { show: false },
          },
        ],
        yAxis: [
          {
            scale: true,
            splitArea: { show: false },
            axisLabel: { color: '#94a3b8' },
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
          },
          {
            scale: true,
            gridIndex: 1,
            axisLabel: { color: '#64748b' },
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
          },
          {
            scale: true,
            gridIndex: 2,
            axisLabel: { color: '#64748b' },
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
          },
        ],
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0, 1, 2],
            start: Math.max(0, 100 - Math.min(70, 12000 / candles.length)),
            end: 100,
          },
          {
            type: 'slider',
            xAxisIndex: [0, 1, 2],
            bottom: 4,
            height: 22,
            borderColor: '#334155',
            fillerColor: 'rgba(37, 99, 235, 0.24)',
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            dataBackground: {
              lineStyle: { color: '#2563eb' },
              areaStyle: { color: 'rgba(37, 99, 235, 0.16)' },
            },
            selectedDataBackground: {
              lineStyle: { color: '#38bdf8' },
              areaStyle: { color: 'rgba(56, 189, 248, 0.22)' },
            },
            textStyle: { color: '#94a3b8' },
          },
        ],
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
              color: '#f97316',
              color0: '#3b82f6',
              borderColor: '#fb923c',
              borderColor0: '#60a5fa',
            },
          },
          {
            name: 'MA5',
            type: 'line',
            data: ma5.length ? ma5 : calculateMA(candles, 5),
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 1.4, color: '#facc15' },
          },
          {
            name: 'MA20',
            type: 'line',
            data: ma20.length ? ma20 : calculateMA(candles, 20),
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 1.4, color: '#38bdf8' },
          },
          {
            name: 'MA60',
            type: 'line',
            data: ma60.length ? ma60 : calculateMA(candles, 60),
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 1.2, color: '#a78bfa' },
          },
          {
            name: '买入',
            type: 'scatter',
            data: buyMarkers,
            symbol: 'triangle',
            symbolSize: 13,
            itemStyle: { color: '#22c55e', borderColor: '#dcfce7', borderWidth: 1 },
            tooltip: { show: false },
          },
          {
            name: '卖出',
            type: 'scatter',
            data: sellMarkers,
            symbol: 'triangle',
            symbolRotate: 180,
            symbolSize: 13,
            itemStyle: { color: '#ef4444', borderColor: '#fee2e2', borderWidth: 1 },
            tooltip: { show: false },
          },
          {
            name: '成交量',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: volume,
            itemStyle: {
              color: volumeBarColor,
              opacity: 0.78,
            },
          },
          {
            name: 'MACD',
            type: 'bar',
            xAxisIndex: 2,
            yAxisIndex: 2,
            data: macdFromPayload.hist.length ? macdFromPayload.hist : macdFallback.hist,
            itemStyle: {
              color: macdBarColor,
              opacity: 0.82,
            },
          },
          {
            name: 'DIF',
            type: 'line',
            xAxisIndex: 2,
            yAxisIndex: 2,
            data: macdFromPayload.dif.length ? macdFromPayload.dif : macdFallback.dif,
            symbol: 'none',
            lineStyle: { width: 1.2, color: '#facc15' },
          },
          {
            name: 'DEA',
            type: 'line',
            xAxisIndex: 2,
            yAxisIndex: 2,
            data: macdFromPayload.dea.length ? macdFromPayload.dea : macdFallback.dea,
            symbol: 'none',
            lineStyle: { width: 1.2, color: '#38bdf8' },
          },
        ],
      }
    },
    [candles, indicators, markers],
  )

  if (!candles.length) {
    return <EmptyData label="K线数据" />
  }

  return <div className="kline-canvas" ref={chartRef} />
}

function CandlePanel({ payload }: { payload: SnapshotPayload }) {
  const candles = payload.result_payload.candles ?? []
  const markers = payload.result_payload.trade_markers ?? []
  const indicators = payload.result_payload.technical_indicators ?? payload.technical_indicators
  const first = candles[0]
  const last = candles[candles.length - 1]

  return (
    <section className="panel wide kline-panel">
      <header>
        <div>
          <span className="section-label dark">交易证据图</span>
          <h2>K线、均线、成交量与买卖点</h2>
        </div>
        <strong>
          {formatNumber(candles.length, 0)} 根K线 · {formatNumber(markers.length, 0)} 个交易标记
        </strong>
      </header>
      <KlineEvidenceChart candles={candles} markers={markers} indicators={indicators} />
      <div className="kline-footnote">
        <span>区间：{formatDate(first?.timestamp)} 至 {formatDate(last?.timestamp)}</span>
        <span>橙色代表上涨，蓝色代表下跌；买卖点来自已发布快照。</span>
      </div>
    </section>
  )
}

function PositionChart({ points }: { points: Point[] }) {
  const chartRef = useRef<HTMLDivElement | null>(null)

  useEchart(
    chartRef,
    () => {
      if (!points.length) {
        return null
      }
      return {
        animationDuration: 450,
        color: ['#2563eb'],
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          borderColor: '#334155',
          textStyle: { color: '#f8fafc' },
        },
        grid: { left: 44, right: 18, top: 18, bottom: 32 },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: points.map((point) => dateKey(point.timestamp)),
          axisLabel: { color: '#64748b' },
          axisLine: { lineStyle: { color: '#cbd5e1' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#64748b', formatter: (value: number) => `${value.toFixed(0)}%` },
          splitLine: { lineStyle: { color: '#e2e8f0' } },
        },
        series: [
          {
            name: '仓位',
            type: 'line',
            step: 'middle',
            symbol: 'none',
            areaStyle: { opacity: 0.12 },
            lineStyle: { width: 3 },
            data: points.map((point) => normalizePositionValue(point.value)),
          },
        ],
      }
    },
    [points],
  )

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
        <strong>{formatNumber(points.length, 0)} 个点</strong>
      </header>
      <PositionChart points={points} />
    </section>
  )
}

function DrawdownSummary({ payload }: { payload: SnapshotPayload }) {
  const status = payload.data_quality?.status
  const metrics = payload.metrics
  const risk = payload.risk_metrics ?? {}
  return (
    <section className="panel risk-panel">
      <header>
        <div>
          <span className="section-label">风险摘要</span>
          <h2>最大回撤</h2>
        </div>
        <strong>{status === 'warning' ? '需谨慎解读' : '已记录'}</strong>
      </header>
      <div className="risk-stat">
        <strong>{formatPercent(metrics.max_drawdown ?? risk.max_drawdown)}</strong>
        <span>
          年化波动 {formatPercent(metrics.annualized_volatility ?? risk.annualized_volatility)}，
          Calmar {formatRatio(metrics.calmar_ratio ?? risk.calmar_ratio)}。
          若样本过短或覆盖市场阶段单一，实际风险可能被低估。
        </span>
      </div>
    </section>
  )
}

function TradeTable({
  trades,
  summary,
  signal,
}: {
  trades: Array<Record<string, unknown>>
  summary?: TradeSummary
  signal?: SignalSummary
}) {
  return (
    <section className="panel trade-panel wide">
      <header>
        <div>
          <span className="section-label">交易明细</span>
          <h2>模拟交易记录</h2>
        </div>
        <strong>
          {formatNumber(summary?.trade_count ?? trades.length, 0)} 笔 · 胜率 {formatPercent(summary?.win_rate)}
        </strong>
      </header>
      <div className="trade-summary-row">
        <span>买入 {formatNumber(summary?.buy_count, 0)}</span>
        <span>卖出 {formatNumber(summary?.sell_count, 0)}</span>
        <span>平均盈利 {formatPercent(summary?.average_win)}</span>
        <span>平均亏损 {formatPercent(summary?.average_loss)}</span>
        <span>盈亏比 {formatRatio(summary?.profit_loss_ratio)}</span>
      </div>
      {signal ? (
        <div className="signal-summary-row">
          <div>
            <span>最新信号</span>
            <strong>{signalLabel(signal.latest_signal)}</strong>
          </div>
          <div>
            <span>信号决策</span>
            <strong>{decisionLabel(signal.latest_decision)}</strong>
          </div>
          <div>
            <span>执行/拦截</span>
            <strong>
              {formatNumber(signal.executed_signal_count, 0)} / {formatNumber(signal.blocked_signal_count, 0)}
            </strong>
          </div>
          <div>
            <span>规则参数</span>
            <strong>
              网格 {formatNumber(signal.grid_percent, 2)}% · 均线
              {signal.ma_filter_enabled ? `${formatNumber(signal.ma_window, 0)}日` : '关闭'}
            </strong>
          </div>
          <p>{signal.latest_reason ?? '当前快照未记录信号说明。'}</p>
        </div>
      ) : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>方向</th>
              <th>价格</th>
              <th>变化</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            {trades.length ? (
              trades.map((trade, index) => (
                <tr key={index}>
                  <td>{tradeValue(trade, 'timestamp')}</td>
                  <td>
                    <span className={`side-pill ${sideTone(trade.side)}`}>{sideLabel(trade.side)}</span>
                  </td>
                  <td>{tradeValue(trade, 'price')}</td>
                  <td>{tradeValue(trade, 'change_percent')}%</td>
                  <td>{tradeValue(trade, 'reason')}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>当前快照暂无模拟交易记录。</td>
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
    ['成交模型', assumptions.execution_model ?? 'V1规则回测模型'],
    ['手续费', formatBoolean(assumptions.fees_included)],
    ['滑点', formatBoolean(assumptions.slippage_included)],
    ['基准说明', assumptions.benchmark_method ?? '未记录'],
  ]

  return (
    <section className="panel assumptions-panel wide">
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
              <dd>{formatMoney(metadata?.initial_cash)}</dd>
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
  const qualityWarnings = quality?.warnings ?? []
  const missingSections = payload.report_metadata?.missing_sections ?? []
  const disclosure = normalizeRiskDisclosure(payload.risk_disclosure ?? payload.result_payload.risk_disclosure)
  const risks = [
    '本报告展示的是历史回测结果，并非实盘交易记录。',
    '历史表现不代表未来收益，策略可能在不同市场环境下失效。',
    quality?.message ?? '数据质量说明未完整记录，需结合样本区间和K线数量谨慎解读。',
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
        {qualityWarnings.map((warning) => (
          <article className="warning-note" key={warning}>{warning}</article>
        ))}
        {quality?.missing_trading_days?.length ? (
          <article className="warning-note">缺失交易日：{quality.missing_trading_days.slice(0, 8).join('、')}</article>
        ) : null}
        {missingSections.map((section) => (
          <article className="warning-note" key={section}>快照缺少：{section}</article>
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

  const payload = normalizePayload(snapshot.payload, snapshot.title)
  const result = payload.result_payload

  return (
    <main className="report-page">
      <ReportHero snapshot={snapshot} />
      <MetricStrip payload={payload} />
      <ReportSummaryPanel payload={payload} />
      <div className="analysis-grid">
        <EquityPanel payload={payload} />
        <CandlePanel payload={payload} />
        <PositionPanel points={result.position_curve ?? []} />
        <DrawdownSummary payload={payload} />
        <TradeTable
          trades={result.trade_table ?? []}
          summary={payload.trade_summary}
          signal={payload.signal_summary ?? result.signal_summary}
        />
        <AssumptionsPanel payload={payload} />
      </div>
      <RiskDisclosure payload={payload} />
    </main>
  )
}

export default App
