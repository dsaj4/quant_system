import {
  ApiOutlined,
  AreaChartOutlined,
  AuditOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  DownOutlined,
  FileSearchOutlined,
  FundProjectionScreenOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  StockOutlined,
  UpOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfigProvider,
  Form,
  Input,
  InputNumber,
  Layout,
  Menu,
  Progress,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useEffect, useState } from 'react'
import {
  fetchOperationLogs,
  fetchProfile,
  fetchInstruments,
  fetchDataImportTasks,
  fetchBacktests,
  fetchMarketBars,
  fetchMarketDataCompleteness,
  fetchMarketDataSchedules,
  fetchPaperRuns,
  fetchPortfolios,
  fetchShareLinks,
  fetchSnapshots,
  fetchStrategies,
  fetchStrategyParameterSets,
  createBacktest,
  createInstrument,
  createMarketDataSchedule,
  createPaperRun,
  createPortfolio,
  createShareLink,
  createStrategyParameterSet,
  fetchPublicMarketData,
  importCsvMarketData,
  publishSnapshot,
  revokeSnapshot,
  revokeShareLink,
  runMarketDataSchedule,
  disableMarketDataSchedule,
  type BacktestInput,
  type BacktestRun,
  type Bar,
  type CsvImportInput,
  type DataImportTask,
  type DataCompleteness,
  login,
  type Instrument,
  type InstrumentInput,
  type MarketDataSchedule,
  type MarketDataScheduleInput,
  type OperationLog,
  type PaperRun,
  type PaperRunInput,
  type Portfolio,
  type PublishedSnapshot,
  type PublicFetchInput,
  type ShareLink,
  type SnapshotPublishInput,
  type StrategyParameter,
  type StrategyParameterSet,
  type StrategyTemplate,
  type UserProfile,
} from './api/client'
import { CommandRail, type CommandRailItem } from './components/CommandRail'
import { CopyLinkButton } from './components/CopyLinkButton'
import { AuditSection } from './sections/AuditSection'
import { BacktestSection } from './sections/BacktestSection'
import { DataSection } from './sections/DataSection'
import { OverviewSection } from './sections/OverviewSection'
import { PaperSection } from './sections/PaperSection'
import { PublicationSection } from './sections/PublicationSection'
import { StrategySection } from './sections/StrategySection'
import './App.css'

const { Header, Sider, Content } = Layout
const { Text, Title } = Typography

const modules = [
  { key: 'portfolios', icon: <StockOutlined />, label: '组合管理' },
  { key: 'data', icon: <DatabaseOutlined />, label: '行情数据' },
  { key: 'strategies', icon: <DeploymentUnitOutlined />, label: '策略配置' },
  { key: 'backtests', icon: <BarChartOutlined />, label: '回测任务' },
  { key: 'paper', icon: <PlayCircleOutlined />, label: '模拟运行' },
  { key: 'snapshots', icon: <FundProjectionScreenOutlined />, label: '展示快照' },
  { key: 'links', icon: <LinkOutlined />, label: '分享链接' },
  { key: 'logs', icon: <AuditOutlined />, label: '操作日志' },
]

void modules

const researchModules = [
  { key: 'overview', icon: <AreaChartOutlined />, label: '演示总览' },
  { key: 'data', icon: <DatabaseOutlined />, label: '行情数据' },
  { key: 'strategy', icon: <DeploymentUnitOutlined />, label: '策略参数' },
  { key: 'backtest', icon: <BarChartOutlined />, label: '回测复核' },
  { key: 'publication', icon: <FundProjectionScreenOutlined />, label: '报告发布' },
  { key: 'paper', icon: <PlayCircleOutlined />, label: '模拟记录' },
  { key: 'audit', icon: <AuditOutlined />, label: '审计边界' },
]

const commandRailItems: CommandRailItem[] = [
  { key: 'instrument', label: '标的', icon: <StockOutlined />, section: 'data' },
  { key: 'market-data', label: '行情', icon: <DatabaseOutlined />, section: 'data' },
  { key: 'quality', label: '质量', icon: <CheckCircleOutlined />, section: 'data' },
  { key: 'parameters', label: '参数', icon: <DeploymentUnitOutlined />, section: 'strategy' },
  { key: 'backtest', label: '回测', icon: <BarChartOutlined />, section: 'backtest' },
  { key: 'review', label: '复核', icon: <FileSearchOutlined />, section: 'backtest' },
  { key: 'snapshot', label: '快照', icon: <FundProjectionScreenOutlined />, section: 'publication' },
  { key: 'share', label: '分享', icon: <LinkOutlined />, section: 'publication' },
  { key: 'paper', label: '模拟', icon: <PlayCircleOutlined />, section: 'paper' },
]

function formatPercent(value: number | undefined): string {
  return `${((value ?? 0) * 100).toFixed(2)}%`
}

function formatNumber(value: number | undefined): string {
  return (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function formatDateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : '-'
}

function formatRatio(value: number | null | undefined): string {
  return value === null || value === undefined ? '-' : `${(value * 100).toFixed(2)}%`
}

function formatRequestParams(value: Record<string, unknown> | undefined): string {
  if (!value || !Object.keys(value).length) {
    return '-'
  }
  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry || '-')}`)
    .join(' / ')
}

const providerOptions = [
  { label: 'Tushare Pro', value: 'tushare' },
  { label: 'JQData', value: 'jqdata', disabled: true },
  { label: 'AkShare', value: 'akshare' },
  { label: 'BaoStock', value: 'baostock', disabled: true },
]

const frequencyOptions = [
  { label: '日线 1d', value: '1d' },
  { label: '1分钟', value: '1m' },
  { label: '5分钟', value: '5m' },
  { label: '15分钟', value: '15m' },
  { label: '30分钟', value: '30m' },
  { label: '60分钟', value: '60m' },
]

const adjustOptions = [
  { label: '不复权', value: '' },
  { label: '前复权 qfq', value: 'qfq' },
  { label: '后复权 hfq', value: 'hfq' },
]

const statusText: Record<string, string> = {
  Checking: '检查中',
  Connected: '已连接',
  Offline: '离线',
  pending: '待处理',
  running: '运行中',
  succeeded: '成功',
  failed: '失败',
  executed: '已执行',
  blocked_by_ma_filter: '均线过滤',
  skipped_no_available_cash_or_position: '资金/仓位不足',
  published: '已发布',
  revoked: '已撤销',
  draft: '草稿',
  active: '启用',
  disabled: '停用',
  empty: '无数据',
  warning: '有缺口',
  ok: '正常',
  unchecked: '未检查',
  unknown_frequency: '未知周期',
  buy: '买入',
  sell: '卖出',
  hold: '持有',
}

const operationActionText: Record<string, string> = {
  'auth.admin.seeded': '初始化管理员',
  'auth.login.failed': '登录失败',
  'auth.login.success': '登录成功',
  'instrument.create': '新增标的',
  'portfolio.create': '新增组合',
  'market_data.import_csv.failed': 'CSV导入失败',
  'market_data.import_csv.succeeded': 'CSV导入成功',
  'market_data.fetch_public.failed': '公开行情拉取失败',
  'market_data.fetch_public.succeeded': '公开行情拉取成功',
  'market_data.schedule.create': '创建行情计划',
  'market_data.schedule.disable': '停用行情计划',
  'market_data.schedule.run.failed': '行情计划执行失败',
  'market_data.schedule.run.succeeded': '行情计划执行成功',
  'strategy_parameter_set.create': '保存策略参数',
  'backtest.create.failed': '回测创建失败',
  'backtest.create.succeeded': '回测创建成功',
  'paper_run.create.failed': '模拟运行失败',
  'paper_run.create.succeeded': '模拟运行成功',
  'snapshot.publish': '发布展示快照',
  'snapshot.revoke': '撤销展示快照',
  'share_link.create': '创建分享链接',
  'share_link.revoke': '撤销分享链接',
}

const targetTypeText: Record<string, string> = {
  auth: '认证',
  user: '用户',
  instrument: '标的',
  portfolio: '组合',
  market_data: '行情数据',
  market_data_schedule: '行情计划',
  strategy_parameter_set: '策略参数',
  backtest: '回测',
  paper_run: '模拟运行',
  snapshot: '展示快照',
  share_link: '分享链接',
}

const strategyNameText: Record<string, string> = {
  'A-share T0 VWAP Channel Strategy': 'A股日内VWAP通道做T策略',
  'Rolling T / Grid Strategy': '滚动做T / 网格策略',
}

const strategyDescriptionText: Record<string, string> = {
  'A-share base-position T0 strategy using intraday VWAP standard-deviation channels, 100-share lots, T+1 sellable-position constraints, and separate buy/sell transaction costs.':
    '面向A股底仓的日内做T策略，使用VWAP标准差通道、100股整手、T+1可卖额度和买卖双边成本生成信号。',
  'Rule-based rolling T strategy for a fixed stock or portfolio. It uses grid thresholds and an optional moving-average filter.':
    '面向固定股票或组合的规则型滚动做T策略，使用网格阈值和可选均线过滤器生成信号。',
}

const parameterLabelText: Record<string, string> = {
  'Grid Percent': '网格触发幅度',
  'Base Position Percent': '底仓比例',
  'Trade Position Percent': '单次交易仓位',
  'Enable MA Filter': '启用均线过滤',
  'MA Window': '均线窗口',
  'Channel K': '通道倍数',
  'Channel Window': '通道窗口',
  'T Fraction': '单次T仓比例',
  'Min Lot': '最小交易单位',
  'Stop Open Time': '停止开仓时间',
  'Force Close Time': '强制处理时间',
  'Buy Fee Rate': '买入费率',
  'Sell Fee Rate': '卖出费率',
}

const parameterDescriptionText: Record<string, string> = {
  'Price movement percentage that triggers a grid buy/sell signal.': '触发网格买入/卖出信号的价格波动百分比。',
  'Baseline position percentage kept for rolling T operations.': '滚动做T过程中保留的基础仓位比例。',
  'Position percentage used by each grid trade.': '每次网格交易使用的仓位比例。',
  'Enable moving-average trend filter before generating signals.': '生成信号前是否启用均线趋势过滤。',
  'Moving-average window used when the filter is enabled.': '启用均线过滤时使用的均线周期。',
  'Initial base position percentage of cash. ETF trend state can be reflected by choosing 10, 40, or 70.':
    '用于建立底仓的资金比例，可用10/40/70表达弱势、中性、强势状态。',
  'Standard-deviation multiplier for VWAP support and resistance channels.': 'VWAP支撑/压力通道使用的标准差倍数。',
  'Rolling window used for intraday close-price standard deviation.': '计算日内收盘价滚动标准差的窗口长度。',
  'Fraction of the base position used for one T0 leg before lot-size rounding.': '单次做T使用的底仓比例，成交前会按整手向下取整。',
  'Minimum tradable share lot. A-share stocks usually use 100.': '最小可交易股数，A股通常为100股。',
  'Time after which the strategy stops opening new T0 positions.': '超过该时间后不再新开做T仓位。',
  'Time after which open T0 legs are force-closed when possible.': '超过该时间后尽可能处理未平的T仓。',
  'Buy-side transaction cost rate.': '买入侧交易成本费率。',
  'Sell-side transaction cost rate including stamp duty.': '卖出侧交易成本费率，包含印花税口径。',
}

const dataMessageText: Record<string, string> = {
  'No bars found for selected instrument and frequency.': '当前标的和周期没有找到K线数据。',
  'Data continuity looks usable for the selected frequency.': '当前周期的数据连续性可用于回测。',
  'Frequency is not mapped to an expected interval; continuity gaps were not evaluated.': '当前周期未映射到预期时间间隔，未评估数据缺口。',
  'CSV import succeeded': 'CSV导入成功',
  'akshare is not installed; use CSV import or install akshare for public data fetch':
    '未安装 akshare；请使用CSV导入，或安装 akshare 后拉取公开行情。',
}

const displayText: Record<string, string> = {
  'Core A-share Basket': '核心A股组合',
  'Fixed demo portfolio for V1 backtests.': '用于V1回测的固定演示组合。',
  'Kweichow Moutai': '贵州茅台',
  'Rolling T / Grid Strategy default': '滚动做T / 网格策略默认参数',
  'Strategy Report #1': '策略展示报告 #1',
  'Client Display Verification Report': '客户展示验证报告',
  'Backtest results are simulated and do not represent real-money trading.': '回测结果为模拟结果，不代表真实资金交易表现。',
  stock: '股票',
  user: '用户',
}

function tStatus(status: string | null | undefined): string {
  return status ? statusText[status] ?? status : '-'
}

function taskStatusColor(status: string | null | undefined): string {
  if (status === 'succeeded') {
    return 'green'
  }
  if (status === 'failed') {
    return 'red'
  }
  if (status === 'running') {
    return 'processing'
  }
  if (status === 'pending') {
    return 'gold'
  }
  return 'default'
}

function tAction(action: string): string {
  return operationActionText[action] ?? action
}

function tTargetType(targetType: string): string {
  return targetTypeText[targetType] ?? targetType
}

function tStrategyName(name: string): string {
  return strategyNameText[name] ?? name
}

function tStrategyDescription(description: string): string {
  return strategyDescriptionText[description] ?? description
}

function tParameterLabel(label: string): string {
  return parameterLabelText[label] ?? label
}

function tParameterDescription(description: string): string {
  return parameterDescriptionText[description] ?? description
}

function tDataMessage(message: string | null | undefined): string {
  if (!message) {
    return '回测前请先检查所选标的的数据完整性。'
  }
  const gapMatch = message.match(/^Detected (\d+) interval gap\(s\) before running backtests\.$/)
  if (gapMatch) {
    return `检测到 ${gapMatch[1]} 个周期缺口，建议回测前先补齐数据。`
  }
  return dataMessageText[message] ?? message
}

function tDisplayText(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const testStockMatch = value.match(/^(.+) test stock$/)
  if (testStockMatch) {
    return `${testStockMatch[1]} 测试股票`
  }
  const strategyReportMatch = value.match(/^Strategy Report #(\d+)$/)
  if (strategyReportMatch) {
    return `策略展示报告 #${strategyReportMatch[1]}`
  }
  const legacyGarbledReportMatch = value.match(/^\?+ #(\d+)$/)
  if (legacyGarbledReportMatch) {
    return `策略展示报告 #${legacyGarbledReportMatch[1]}`
  }
  return displayText[value] ?? value
}

function chartPoints(series: Array<{ value: number }> = [], width = 360, height = 120): string {
  if (!series.length) {
    return ''
  }

  const padding = 12
  const values = series.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return series
    .map((point, index) => {
      const x = padding + (index / Math.max(series.length - 1, 1)) * (width - padding * 2)
      const y = padding + ((max - point.value) / range) * (height - padding * 2)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

function tradeValue(trade: Record<string, unknown>, key: string): string {
  const value = trade[key]
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  return typeof value === 'string' ? value : '-'
}

function strategyTemplateRank(strategy: StrategyTemplate): number {
  if (strategy.strategy_id === 'a_share_t0_vwap') {
    return 0
  }
  if (strategy.strategy_id === 'rolling_t_grid') {
    return 1
  }
  return 10
}

function formatStrategyConfigParameters(parameterSet: StrategyParameterSet): string {
  const parameters = parameterSet.parameters
  if (parameterSet.strategy_id === 'a_share_t0_vwap') {
    return [
      `底仓 ${parameters.base_position_percent ?? '-'}%`,
      `K=${parameters.channel_k ?? '-'}`,
      `窗口 ${parameters.channel_window ?? '-'}`,
      `整手 ${parameters.min_lot ?? '-'}`,
    ].join(' / ')
  }
  if (parameterSet.strategy_id === 'rolling_t_grid') {
    return [
      `网格 ${parameters.grid_percent ?? '-'}%`,
      `底仓 ${parameters.base_position_percent ?? '-'}%`,
      `均线 ${parameters.enable_ma_filter ? '开' : '关'}`,
    ].join(' / ')
  }
  return Object.entries(parameters)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(' / ')
}

function App() {
  const [strategies, setStrategies] = useState<StrategyTemplate[]>([])
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [bars, setBars] = useState<Bar[]>([])
  const [dataCompleteness, setDataCompleteness] = useState<DataCompleteness | null>(null)
  const [backtests, setBacktests] = useState<BacktestRun[]>([])
  const [paperRuns, setPaperRuns] = useState<PaperRun[]>([])
  const [dataImportTasks, setDataImportTasks] = useState<DataImportTask[]>([])
  const [marketDataSchedules, setMarketDataSchedules] = useState<MarketDataSchedule[]>([])
  const [snapshots, setSnapshots] = useState<PublishedSnapshot[]>([])
  const [shareLinks, setShareLinks] = useState<ShareLink[]>([])
  const [latestShareToken, setLatestShareToken] = useState('')
  const [activeSection, setActiveSection] = useState('overview')
  const [metricsCollapsed, setMetricsCollapsed] = useState(false)
  const [backtestQuickFocus, setBacktestQuickFocus] = useState(false)
  const [selectedBacktestId, setSelectedBacktestId] = useState<number | null>(null)
  const [selectedStrategyTemplateId, setSelectedStrategyTemplateId] = useState('')
  const [strategyParameterSets, setStrategyParameterSets] = useState<StrategyParameterSet[]>([])
  const [operationLogs, setOperationLogs] = useState<OperationLog[]>([])
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null)
  const [token, setToken] = useState(() => localStorage.getItem('quant_admin_token') ?? '')
  const [apiStatus, setApiStatus] = useState('Checking')
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [instrumentForm] = Form.useForm<InstrumentInput>()
  const [portfolioForm] = Form.useForm<{ name: string; description: string; instrument_id: number; weight: number }>()
  const [marketDataForm] = Form.useForm<CsvImportInput>()
  const [publicFetchForm] = Form.useForm<PublicFetchInput>()
  const [scheduleForm] = Form.useForm<MarketDataScheduleInput>()
  const [strategyParameterForm] = Form.useForm<Record<string, number | boolean | string>>()
  const [backtestForm] = Form.useForm<BacktestInput>()
  const [paperRunForm] = Form.useForm<PaperRunInput>()
  const [snapshotForm] = Form.useForm<SnapshotPublishInput>()
  const [instrumentSaving, setInstrumentSaving] = useState(false)
  const [portfolioSaving, setPortfolioSaving] = useState(false)
  const [marketDataImporting, setMarketDataImporting] = useState(false)
  const [publicDataFetching, setPublicDataFetching] = useState(false)
  const [dataCompletenessChecking, setDataCompletenessChecking] = useState(false)
  const [scheduleSaving, setScheduleSaving] = useState(false)
  const [scheduleActionId, setScheduleActionId] = useState<number | null>(null)
  const [strategyParameterSaving, setStrategyParameterSaving] = useState(false)
  const [backtestRunning, setBacktestRunning] = useState(false)
  const [paperRunStarting, setPaperRunStarting] = useState(false)
  const [snapshotPublishing, setSnapshotPublishing] = useState(false)
  const [snapshotRevokingId, setSnapshotRevokingId] = useState<number | null>(null)
  const [shareLinkCreatingId, setShareLinkCreatingId] = useState<number | null>(null)
  const [shareLinkRevokingId, setShareLinkRevokingId] = useState<number | null>(null)
  const [marketDataError, setMarketDataError] = useState('')
  const [strategyParameterError, setStrategyParameterError] = useState('')
  const [backtestError, setBacktestError] = useState('')
  const [paperRunError, setPaperRunError] = useState('')
  const [snapshotError, setSnapshotError] = useState('')
  const [shareLinkError, setShareLinkError] = useState('')

  const refreshAdminData = (accessToken: string) => {
    Promise.all([
      fetchStrategies(),
      fetchProfile(accessToken),
      fetchOperationLogs(accessToken),
      fetchInstruments(accessToken),
      fetchPortfolios(accessToken),
      fetchDataImportTasks(accessToken),
      fetchMarketDataSchedules(accessToken),
      fetchStrategyParameterSets(accessToken),
      fetchBacktests(accessToken),
      fetchPaperRuns(accessToken),
      fetchSnapshots(accessToken),
      fetchShareLinks(accessToken),
    ])
      .then(([
        strategyPayload,
        profilePayload,
        logPayload,
        instrumentPayload,
        portfolioPayload,
        importTaskPayload,
        schedulePayload,
        strategyParameterSetPayload,
        backtestPayload,
        paperRunPayload,
        snapshotPayload,
        shareLinkPayload,
      ]) => {
        setStrategies(strategyPayload)
        setCurrentUser(profilePayload)
        setOperationLogs(logPayload)
        setInstruments(instrumentPayload)
        setPortfolios(portfolioPayload)
        setDataImportTasks(importTaskPayload)
        setMarketDataSchedules(schedulePayload)
        setStrategyParameterSets(strategyParameterSetPayload)
        setBacktests(backtestPayload)
        setSelectedBacktestId((current) => current ?? backtestPayload[0]?.id ?? null)
        setPaperRuns(paperRunPayload)
        setSnapshots(snapshotPayload)
        setShareLinks(shareLinkPayload)
        setApiStatus('Connected')

        const firstInstrument = instrumentPayload[0]
        if (firstInstrument) {
          fetchMarketBars(accessToken, firstInstrument.id).then(setBars).catch(() => setBars([]))
          fetchMarketDataCompleteness(accessToken, firstInstrument.id).then(setDataCompleteness).catch(() => setDataCompleteness(null))
        } else {
          setBars([])
          setDataCompleteness(null)
        }
      })
      .catch(() => {
        setApiStatus('Offline')
        setCurrentUser(null)
        setOperationLogs([])
        setInstruments([])
        setPortfolios([])
        setBars([])
        setDataCompleteness(null)
        setDataImportTasks([])
        setMarketDataSchedules([])
        setStrategyParameterSets([])
        setBacktests([])
        setSelectedBacktestId(null)
        setPaperRuns([])
        setSnapshots([])
        setShareLinks([])
      })
  }

  useEffect(() => {
    if (token) {
      refreshAdminData(token)
    } else {
      fetchStrategies()
        .then((payload) => {
          setStrategies(payload)
          setApiStatus('Connected')
        })
        .catch(() => setApiStatus('Offline'))
    }
  }, [token])

  useEffect(() => {
    if (instruments[0] && !portfolioForm.getFieldValue('instrument_id')) {
      portfolioForm.setFieldValue('instrument_id', instruments[0].id)
    }
    if (instruments[0] && !marketDataForm.getFieldValue('instrument_id')) {
      marketDataForm.setFieldValue('instrument_id', instruments[0].id)
    }
    if (instruments[0] && !publicFetchForm.getFieldValue('instrument_id')) {
      publicFetchForm.setFieldValue('instrument_id', instruments[0].id)
    }
    if (instruments[0] && !scheduleForm.getFieldValue('instrument_id')) {
      scheduleForm.setFieldValue('instrument_id', instruments[0].id)
    }
    if (instruments[0] && !backtestForm.getFieldValue('instrument_id')) {
      backtestForm.setFieldValue('instrument_id', instruments[0].id)
    }
    if (instruments[0] && !paperRunForm.getFieldValue('instrument_id')) {
      paperRunForm.setFieldValue('instrument_id', instruments[0].id)
    }
  }, [backtestForm, instruments, marketDataForm, paperRunForm, portfolioForm, publicFetchForm, scheduleForm])

  useEffect(() => {
    if (strategyParameterSets[0] && !backtestForm.getFieldValue('parameter_set_id')) {
      backtestForm.setFieldValue('parameter_set_id', strategyParameterSets[0].id)
    }
    if (strategyParameterSets[0] && !paperRunForm.getFieldValue('parameter_set_id')) {
      paperRunForm.setFieldValue('parameter_set_id', strategyParameterSets[0].id)
    }
  }, [backtestForm, paperRunForm, strategyParameterSets])

  useEffect(() => {
    if (backtests[0] && !snapshotForm.getFieldValue('backtest_run_id')) {
      snapshotForm.setFieldsValue({
        backtest_run_id: backtests[0].id,
        title: `策略展示报告 #${backtests[0].id}`,
      })
    }
  }, [backtests, snapshotForm])

  useEffect(() => {
    if (!strategies.length) {
      return
    }

    const firstStrategy = [...strategies].sort(
      (left, right) => strategyTemplateRank(left) - strategyTemplateRank(right),
    )[0]
    if (!selectedStrategyTemplateId || !strategies.some((strategy) => strategy.strategy_id === selectedStrategyTemplateId)) {
      setSelectedStrategyTemplateId(firstStrategy.strategy_id)
    }
  }, [selectedStrategyTemplateId, strategies])

  useEffect(() => {
    const selectedStrategy =
      strategies.find((strategy) => strategy.strategy_id === selectedStrategyTemplateId) ??
      [...strategies].sort((left, right) => strategyTemplateRank(left) - strategyTemplateRank(right))[0]
    if (!currentUser || !selectedStrategy) {
      return
    }

    const defaultValues = Object.fromEntries(
      selectedStrategy.parameters.map((parameter) => [parameter.name, parameter.default]),
    )
    strategyParameterForm.resetFields()
    strategyParameterForm.setFieldsValue({
      name: `${tStrategyName(selectedStrategy.display_name)} 配置`,
      strategy_id: selectedStrategy.strategy_id,
      ...defaultValues,
    })
  }, [currentUser, selectedStrategyTemplateId, strategies, strategyParameterForm])

  const handleLogin = (values: { username: string; password: string }) => {
    setLoginLoading(true)
    setLoginError('')
    login(values.username, values.password)
      .then((payload) => {
        localStorage.setItem('quant_admin_token', payload.access_token)
        setToken(payload.access_token)
      })
      .catch(() => setLoginError('用户名或密码错误。本地种子账号可使用 admin / admin。'))
      .finally(() => setLoginLoading(false))
  }

  const handleLogout = () => {
    localStorage.removeItem('quant_admin_token')
    setToken('')
    setCurrentUser(null)
    setOperationLogs([])
    setInstruments([])
    setPortfolios([])
    setBars([])
    setDataCompleteness(null)
    setDataImportTasks([])
    setMarketDataSchedules([])
    setStrategyParameterSets([])
    setBacktests([])
    setSelectedBacktestId(null)
    setPaperRuns([])
    setSnapshots([])
    setShareLinks([])
  }

  const handleCreateInstrument = (values: InstrumentInput) => {
    if (!token) {
      return
    }

    setInstrumentSaving(true)
    createInstrument(token, values)
      .then(() => {
        instrumentForm.resetFields()
        refreshAdminData(token)
      })
      .finally(() => setInstrumentSaving(false))
  }

  const handleCreatePortfolio = (values: { name: string; description: string; instrument_id: number; weight: number }) => {
    if (!token) {
      return
    }

    setPortfolioSaving(true)
    createPortfolio(token, {
      name: values.name,
      description: values.description,
      positions: [{ instrument_id: Number(values.instrument_id), weight: Number(values.weight) }],
    })
      .then(() => {
        portfolioForm.resetFields()
        refreshAdminData(token)
      })
      .finally(() => setPortfolioSaving(false))
  }

  const handleImportMarketData = (values: CsvImportInput) => {
    if (!token) {
      return
    }

    setMarketDataImporting(true)
    setMarketDataError('')
    importCsvMarketData(token, {
      ...values,
      instrument_id: Number(values.instrument_id),
      frequency: values.frequency || '5m',
      source: values.source || 'csv',
    })
      .then(() => {
        const instrumentId = Number(values.instrument_id)
        return Promise.all([
          fetchMarketBars(token, instrumentId, values.frequency || '5m'),
          fetchMarketDataCompleteness(token, instrumentId, values.frequency || '5m'),
          fetchDataImportTasks(token),
          fetchOperationLogs(token),
        ])
      })
      .then(([barPayload, completenessPayload, importTaskPayload, logPayload]) => {
        setBars(barPayload)
        setDataCompleteness(completenessPayload)
        setDataImportTasks(importTaskPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'CSV导入失败'))
      .finally(() => setMarketDataImporting(false))
  }

  const handleFetchPublicMarketData = (values: PublicFetchInput) => {
    if (!token) {
      return
    }

    setPublicDataFetching(true)
    setMarketDataError('')
    fetchPublicMarketData(token, {
      ...values,
      instrument_id: Number(values.instrument_id),
      provider: values.provider || 'tushare',
      frequency: values.frequency || '1d',
      adjust: values.adjust ?? 'qfq',
    })
      .then(() => {
        const instrumentId = Number(values.instrument_id)
        const frequency = values.frequency || '1d'
        const adjust = values.adjust ?? 'qfq'
        return Promise.all([
          fetchMarketBars(token, instrumentId, frequency, adjust),
          fetchMarketDataCompleteness(token, instrumentId, frequency, adjust),
          fetchDataImportTasks(token),
          fetchOperationLogs(token),
        ])
      })
      .then(([barPayload, completenessPayload, importTaskPayload, logPayload]) => {
        setBars(barPayload)
        setDataCompleteness(completenessPayload)
        setDataImportTasks(importTaskPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : '公开行情拉取失败'))
      .finally(() => setPublicDataFetching(false))
  }

  const handleCreateMarketDataSchedule = (values: MarketDataScheduleInput) => {
    if (!token) {
      return
    }

    setScheduleSaving(true)
    setMarketDataError('')
    createMarketDataSchedule(token, {
      ...values,
      instrument_id: Number(values.instrument_id),
      interval_minutes: Number(values.interval_minutes || 60),
      provider: values.provider || 'tushare',
      frequency: values.frequency || '1d',
      adjust: values.adjust ?? 'qfq',
    })
      .then(() => Promise.all([fetchMarketDataSchedules(token), fetchOperationLogs(token)]))
      .then(([schedulePayload, logPayload]) => {
        setMarketDataSchedules(schedulePayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : '行情计划保存失败'))
      .finally(() => setScheduleSaving(false))
  }

  const handleCheckDataCompleteness = () => {
    if (!token) {
      return
    }

    const instrumentId = Number(marketDataForm.getFieldValue('instrument_id') || instruments[0]?.id)
    const frequency = String(marketDataForm.getFieldValue('frequency') || '5m')
    if (!instrumentId) {
      return
    }

    setDataCompletenessChecking(true)
    setMarketDataError('')
    fetchMarketDataCompleteness(token, instrumentId, frequency)
      .then(setDataCompleteness)
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : '数据完整性检查失败'))
      .finally(() => setDataCompletenessChecking(false))
  }

  const handleRunMarketDataSchedule = (scheduleId: number) => {
    if (!token) {
      return
    }

    setScheduleActionId(scheduleId)
    setMarketDataError('')
    runMarketDataSchedule(token, scheduleId)
      .then(() => Promise.all([fetchMarketDataSchedules(token), fetchDataImportTasks(token), fetchOperationLogs(token)]))
      .then(([schedulePayload, taskPayload, logPayload]) => {
        setMarketDataSchedules(schedulePayload)
        setDataImportTasks(taskPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : '行情计划执行失败'))
      .finally(() => setScheduleActionId(null))
  }

  const handleDisableMarketDataSchedule = (scheduleId: number) => {
    if (!token) {
      return
    }

    setScheduleActionId(scheduleId)
    setMarketDataError('')
    disableMarketDataSchedule(token, scheduleId)
      .then(() => Promise.all([fetchMarketDataSchedules(token), fetchOperationLogs(token)]))
      .then(([schedulePayload, logPayload]) => {
        setMarketDataSchedules(schedulePayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : '行情计划停用失败'))
      .finally(() => setScheduleActionId(null))
  }

  const renderStrategyParameterInput = (parameter: StrategyParameter) => {
    if (parameter.type === 'boolean') {
      return <Switch />
    }
    if (parameter.type === 'select') {
      return <Select options={parameter.options.map((option) => ({ label: option, value: option }))} />
    }
    return <InputNumber min={parameter.min_value ?? undefined} max={parameter.max_value ?? undefined} />
  }

  const handleCreateStrategyParameterSet = (values: Record<string, number | boolean | string>) => {
    const strategy =
      strategies.find((item) => item.strategy_id === selectedStrategyTemplateId) ??
      [...strategies].sort((left, right) => strategyTemplateRank(left) - strategyTemplateRank(right))[0]
    if (!token || !strategy) {
      return
    }

    const parameters = Object.fromEntries(
      strategy.parameters.map((parameter) => [parameter.name, values[parameter.name] ?? parameter.default]),
    )

    setStrategyParameterSaving(true)
    setStrategyParameterError('')
    createStrategyParameterSet(token, {
      strategy_id: strategy.strategy_id,
      name: String(values.name || `${tStrategyName(strategy.display_name)} 配置`),
      parameters,
    })
      .then(() => Promise.all([fetchStrategyParameterSets(token), fetchOperationLogs(token)]))
      .then(([parameterSetPayload, logPayload]) => {
        setStrategyParameterSets(parameterSetPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setStrategyParameterError(error instanceof Error ? error.message : '策略配置保存失败'))
      .finally(() => setStrategyParameterSaving(false))
  }

  const handleCreateBacktest = (values: BacktestInput) => {
    if (!token) {
      return
    }

    const portfolioId = Number(values.portfolio_id || 0)
    const backtestScope = portfolioId
      ? { portfolio_id: portfolioId }
      : { instrument_id: Number(values.instrument_id) }

    setBacktestRunning(true)
    setBacktestError('')
    createBacktest(token, {
      ...backtestScope,
      frequency: values.frequency || '5m',
      parameter_set_id: Number(values.parameter_set_id),
      initial_cash: Number(values.initial_cash || 100000),
    })
      .then(() => Promise.all([fetchBacktests(token), fetchOperationLogs(token)]))
      .then(([backtestPayload, logPayload]) => {
        setBacktests(backtestPayload)
        setSelectedBacktestId(backtestPayload[0]?.id ?? null)
        setOperationLogs(logPayload)
      })
      .catch((error) => setBacktestError(error instanceof Error ? error.message : '回测执行失败'))
      .finally(() => setBacktestRunning(false))
  }

  const handleCreatePaperRun = (values: PaperRunInput) => {
    if (!token) {
      return
    }

    setPaperRunStarting(true)
    setPaperRunError('')
    createPaperRun(token, {
      instrument_id: Number(values.instrument_id),
      frequency: values.frequency || '5m',
      parameter_set_id: Number(values.parameter_set_id),
      initial_cash: Number(values.initial_cash || 100000),
    })
      .then(() => Promise.all([fetchPaperRuns(token), fetchOperationLogs(token)]))
      .then(([paperRunPayload, logPayload]) => {
        setPaperRuns(paperRunPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => {
        setPaperRunError(error instanceof Error ? error.message : '模拟运行失败')
        return Promise.all([fetchPaperRuns(token), fetchOperationLogs(token)]).then(([paperRunPayload, logPayload]) => {
          setPaperRuns(paperRunPayload)
          setOperationLogs(logPayload)
        })
      })
      .finally(() => setPaperRunStarting(false))
  }

  const handlePublishSnapshot = (values: SnapshotPublishInput) => {
    if (!token) {
      return
    }

    setSnapshotPublishing(true)
    setSnapshotError('')
    setLatestShareToken('')
    publishSnapshot(token, {
      backtest_run_id: Number(values.backtest_run_id),
      title: values.title || `策略展示报告 #${values.backtest_run_id}`,
    })
      .then((payload) => {
        setLatestShareToken(payload.share_token)
        return Promise.all([fetchSnapshots(token), fetchOperationLogs(token)])
      })
      .then(([snapshotPayload, logPayload]) => {
        setSnapshots(snapshotPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setSnapshotError(error instanceof Error ? error.message : '快照发布失败'))
      .finally(() => setSnapshotPublishing(false))
  }

  const handleCreateShareLink = (snapshotId: number) => {
    if (!token) {
      return
    }

    setShareLinkCreatingId(snapshotId)
    setShareLinkError('')
    setLatestShareToken('')
    createShareLink(token, snapshotId)
      .then((payload) => {
        setLatestShareToken(payload.share_token)
        return Promise.all([fetchShareLinks(token), fetchOperationLogs(token)])
      })
      .then(([shareLinkPayload, logPayload]) => {
        setShareLinks(shareLinkPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setShareLinkError(error instanceof Error ? error.message : '分享链接创建失败'))
      .finally(() => setShareLinkCreatingId(null))
  }

  const handleRevokeShareLink = (shareLinkId: number) => {
    if (!token) {
      return
    }

    setShareLinkRevokingId(shareLinkId)
    setShareLinkError('')
    revokeShareLink(token, shareLinkId)
      .then(() => Promise.all([fetchShareLinks(token), fetchOperationLogs(token)]))
      .then(([shareLinkPayload, logPayload]) => {
        setShareLinks(shareLinkPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setShareLinkError(error instanceof Error ? error.message : '分享链接撤销失败'))
      .finally(() => setShareLinkRevokingId(null))
  }

  const handleRevokeSnapshot = (snapshotId: number) => {
    if (!token) {
      return
    }

    setSnapshotRevokingId(snapshotId)
    setSnapshotError('')
    revokeSnapshot(token, snapshotId)
      .then(() => Promise.all([fetchSnapshots(token), fetchShareLinks(token), fetchOperationLogs(token)]))
      .then(([snapshotPayload, shareLinkPayload, logPayload]) => {
        setSnapshots(snapshotPayload)
        setShareLinks(shareLinkPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setSnapshotError(error instanceof Error ? error.message : '快照撤销失败'))
      .finally(() => setSnapshotRevokingId(null))
  }

  const handleQuickBacktest = () => {
    setActiveSection('backtest')
    setBacktestQuickFocus(true)
    window.setTimeout(() => {
      document.querySelector('.quick-backtest-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 0)
    window.setTimeout(() => setBacktestQuickFocus(false), 1800)
  }

  const orderedStrategies = [...strategies].sort(
    (left, right) => strategyTemplateRank(left) - strategyTemplateRank(right),
  )
  const selectedStrategyTemplate =
    orderedStrategies.find((strategy) => strategy.strategy_id === selectedStrategyTemplateId) ?? orderedStrategies[0]
  const selectedBacktest = backtests.find((backtest) => backtest.id === selectedBacktestId) ?? backtests[0] ?? null
  const selectedTrades = selectedBacktest?.result_payload.trade_table ?? []
  const selectedEquity = selectedBacktest?.result_payload.equity_curve ?? []
  const selectedDrawdown = selectedBacktest?.result_payload.drawdown_curve ?? []
  const selectedPosition = selectedBacktest?.result_payload.position_curve ?? []
  const selectedSignal = selectedBacktest?.result_payload.signal_summary


  const instrumentPanel = (
              <Card title="标的管理">
                <Form
                  form={instrumentForm}
                  layout="inline"
                  initialValues={{ symbol: '600519', exchange: 'SH', name: '贵州茅台', asset_type: 'stock' }}
                  onFinish={handleCreateInstrument}
                  className="instrument-form"
                >
                  <Form.Item name="symbol" rules={[{ required: true }]}><Input placeholder="证券代码" /></Form.Item>
                  <Form.Item name="exchange" rules={[{ required: true }]}><Input placeholder="交易所" /></Form.Item>
                  <Form.Item name="name" rules={[{ required: true }]}><Input placeholder="标的名称" /></Form.Item>
                  <Form.Item name="asset_type" rules={[{ required: true }]}><Input placeholder="资产类型" /></Form.Item>
                  <Button type="primary" htmlType="submit" loading={instrumentSaving}>新增标的</Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: '证券代码', dataIndex: 'symbol', width: 110 },
                    { title: '交易所', dataIndex: 'exchange', width: 110 },
                    { title: '名称', dataIndex: 'name', render: (name: string) => tDisplayText(name) },
                    { title: '类型', dataIndex: 'asset_type', width: 100, render: (assetType: string) => tDisplayText(assetType) },
                  ]}
                  dataSource={instruments.map((instrument) => ({ ...instrument, key: instrument.id }))}
                />
              </Card>
  )

  const portfolioPanel = (
              <Card title="固定组合管理">
                <Form
                  form={portfolioForm}
                  layout="inline"
                  initialValues={{
                    name: '核心A股组合',
                    description: '用于V1回测的固定演示组合。',
                    instrument_id: instruments[0]?.id,
                    weight: 1,
                  }}
                  onFinish={handleCreatePortfolio}
                  className="instrument-form"
                >
                  <Form.Item name="name" rules={[{ required: true }]}><Input placeholder="组合名称" /></Form.Item>
                  <Form.Item name="description"><Input placeholder="组合说明" /></Form.Item>
                  <Form.Item name="instrument_id" rules={[{ required: true }]}>
                    <Input placeholder="标的ID" />
                  </Form.Item>
                  <Form.Item name="weight" rules={[{ required: true }]}><Input placeholder="权重" type="number" /></Form.Item>
                  <Button type="primary" htmlType="submit" loading={portfolioSaving} disabled={!instruments.length}>
                    新增组合
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: '组合', dataIndex: 'name', render: (name: string) => tDisplayText(name) },
                    { title: '说明', dataIndex: 'description', render: (description: string) => tDisplayText(description) },
                    {
                      title: '持仓数',
                      dataIndex: 'positions',
                      width: 120,
                      render: (positions: Portfolio['positions']) => positions.length,
                    },
                    {
                      title: '首个持仓',
                      dataIndex: 'positions',
                      width: 160,
                      render: (positions: Portfolio['positions']) => {
                        const first = positions[0]?.instrument
                        return first ? `${first.symbol}.${first.exchange}` : '-'
                      },
                    },
                  ]}
                  dataSource={portfolios.map((portfolio) => ({ ...portfolio, key: portfolio.id }))}
                />
              </Card>
  )

  const marketDataPanel = (
              <Card title="行情数据管理">
                {marketDataError ? <Alert type="error" showIcon title={marketDataError} className="form-alert" /> : null}
                <Form
                  form={marketDataForm}
                  layout="vertical"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    frequency: '5m',
                    source: 'csv',
                    csv_text:
                      'timestamp,open,high,low,close,volume\n2026-01-02 09:35:00,10,10.5,9.8,10.2,1000\n2026-01-02 09:40:00,10.2,10.8,10.1,10.7,1200',
                  }}
                  onFinish={handleImportMarketData}
                >
                  <div className="market-data-grid">
                    <Form.Item name="instrument_id" label="标的ID" rules={[{ required: true }]}>
                      <Input placeholder="标的ID" />
                    </Form.Item>
                    <Form.Item name="frequency" label="周期" rules={[{ required: true }]}>
                      <Input placeholder="5m" />
                    </Form.Item>
                    <Form.Item name="source" label="来源" rules={[{ required: true }]}>
                      <Input placeholder="csv" />
                    </Form.Item>
                  </div>
                  <Form.Item name="csv_text" label="CSV K线" rules={[{ required: true }]}>
                    <Input.TextArea rows={5} />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={marketDataImporting} disabled={!instruments.length}>
                    导入CSV K线
                  </Button>
                </Form>
                <Form
                  form={publicFetchForm}
                  layout="vertical"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    provider: 'tushare',
                    frequency: '1d',
                    start_date: '2024-01-01',
                    end_date: '2026-05-29',
                    adjust: 'qfq',
                  }}
                  onFinish={handleFetchPublicMarketData}
                  className="public-fetch-form"
                >
                  <div className="market-data-grid">
                    <Form.Item name="instrument_id" label="标的ID" rules={[{ required: true }]}>
                      <Input placeholder="标的ID" />
                    </Form.Item>
                    <Form.Item name="provider" label="数据源" rules={[{ required: true }]}>
                      <Select options={providerOptions} />
                    </Form.Item>
                    <Form.Item name="frequency" label="周期" rules={[{ required: true }]}>
                      <Select options={frequencyOptions} />
                    </Form.Item>
                  </div>
                  <div className="market-data-grid">
                    <Form.Item name="start_date" label="开始时间" rules={[{ required: true }]}>
                      <Input placeholder="2024-01-01" />
                    </Form.Item>
                    <Form.Item name="end_date" label="结束时间" rules={[{ required: true }]}>
                      <Input placeholder="2026-05-29" />
                    </Form.Item>
                    <Form.Item name="adjust" label="复权">
                      <Select options={adjustOptions} />
                    </Form.Item>
                  </div>
                  <Button type="primary" htmlType="submit" loading={publicDataFetching} disabled={!instruments.length}>
                    拉取公开K线
                  </Button>
                </Form>
                <div className="data-quality-panel">
                  <div>
                    <Text strong>数据完整性</Text>
                    <Text type="secondary">{tDataMessage(dataCompleteness?.message)}</Text>
                  </div>
                  <Space wrap>
                    <Tag
                      color={
                        dataCompleteness?.status === 'ok'
                          ? 'green'
                          : dataCompleteness?.status === 'warning'
                            ? 'orange'
                            : dataCompleteness?.status === 'empty'
                              ? 'red'
                              : 'default'
                      }
                    >
                      {tStatus(dataCompleteness?.status ?? 'unchecked')}
                    </Tag>
                    <Text>K线数：{dataCompleteness?.bar_count ?? '-'}</Text>
                    <Text>完整率：{formatRatio(dataCompleteness?.completeness_ratio)}</Text>
                    <Text>缺失：{dataCompleteness?.missing_bar_count ?? '-'}</Text>
                    <Text>缺口：{dataCompleteness?.gap_count ?? '-'}</Text>
                    <Text>最大缺口：{dataCompleteness?.largest_gap_minutes ?? '-'} 分钟</Text>
                    <Text>交易日：{dataCompleteness?.expected_trading_days ?? '-'}</Text>
                    <Text>缺失交易日：{dataCompleteness?.missing_trading_days?.slice(0, 3).join(', ') || '-'}</Text>
                    <Text>最早：{formatDateTime(dataCompleteness?.first_timestamp)}</Text>
                    <Text>最新：{formatDateTime(dataCompleteness?.last_timestamp)}</Text>
                  </Space>
                  {dataCompleteness?.warnings?.length ? (
                    <Alert
                      type="warning"
                      showIcon
                      className="form-alert"
                      title={dataCompleteness.warnings.join('；')}
                    />
                  ) : null}
                  <Button onClick={handleCheckDataCompleteness} loading={dataCompletenessChecking} disabled={!instruments.length}>
                    检查完整性
                  </Button>
                </div>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    {
                      title: '时间',
                      dataIndex: 'timestamp',
                      width: 190,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                    { title: '开盘', dataIndex: 'open', width: 90 },
                    { title: '最高', dataIndex: 'high', width: 90 },
                    { title: '最低', dataIndex: 'low', width: 90 },
                    { title: '收盘', dataIndex: 'close', width: 90 },
                    { title: '成交量', dataIndex: 'volume', width: 110 },
                  ]}
                  dataSource={bars.map((bar) => ({ ...bar, key: bar.id }))}
                />
              </Card>
  )

  const importTasksPanel = (
              <Card title="数据导入任务">
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: '标的', dataIndex: 'instrument_id', width: 90 },
                    { title: '来源', dataIndex: 'source', width: 90 },
                    { title: '周期', dataIndex: 'frequency', width: 90 },
                    { title: '复权', dataIndex: 'adjust', width: 90, render: (adjust: string) => adjust || '不复权' },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'succeeded' ? 'green' : status === 'failed' ? 'red' : 'blue'}>{tStatus(status)}</Tag>,
                    },
                    { title: '新增行', dataIndex: 'rows_imported', width: 100 },
                    { title: '更新行', dataIndex: 'rows_updated', width: 100 },
                    {
                      title: '请求参数',
                      dataIndex: 'request_params',
                      width: 240,
                      render: (params: DataImportTask['request_params']) => formatRequestParams(params),
                    },
                    { title: '消息', dataIndex: 'message', render: (message: string) => tDataMessage(message) },
                  ]}
                  dataSource={dataImportTasks.map((task) => ({ ...task, key: task.id }))}
                />
              </Card>
  )

  const schedulesPanel = (
              <Card title="行情数据计划">
                <Form
                  form={scheduleForm}
                  layout="vertical"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    provider: 'tushare',
                    frequency: '1d',
                    start_date: '2024-01-01',
                    end_date: '2026-05-29',
                    adjust: 'qfq',
                    interval_minutes: 60,
                  }}
                  onFinish={handleCreateMarketDataSchedule}
                >
                  <div className="market-data-grid">
                    <Form.Item name="instrument_id" label="标的ID" rules={[{ required: true }]}>
                      <Input placeholder="标的ID" />
                    </Form.Item>
                    <Form.Item name="provider" label="数据源" rules={[{ required: true }]}>
                      <Select options={providerOptions} />
                    </Form.Item>
                    <Form.Item name="frequency" label="周期" rules={[{ required: true }]}>
                      <Select options={frequencyOptions} />
                    </Form.Item>
                  </div>
                  <div className="market-data-grid">
                    <Form.Item name="interval_minutes" label="间隔分钟" rules={[{ required: true }]}>
                      <InputNumber min={1} max={1440} />
                    </Form.Item>
                    <Form.Item name="start_date" label="开始时间" rules={[{ required: true }]}>
                      <Input placeholder="2024-01-01" />
                    </Form.Item>
                    <Form.Item name="end_date" label="结束时间" rules={[{ required: true }]}>
                      <Input placeholder="2026-05-29" />
                    </Form.Item>
                  </div>
                  <div className="market-data-grid">
                    <Form.Item name="adjust" label="复权">
                      <Select options={adjustOptions} />
                    </Form.Item>
                  </div>
                  <Button type="primary" htmlType="submit" loading={scheduleSaving} disabled={!instruments.length}>
                    新增计划
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '标的', dataIndex: 'instrument_id', width: 100 },
                    { title: '数据源', dataIndex: 'provider', width: 100 },
                    { title: '周期', dataIndex: 'frequency', width: 100 },
                    { title: '复权', dataIndex: 'adjust', width: 90, render: (adjust: string) => adjust || '不复权' },
                    { title: '间隔', dataIndex: 'interval_minutes', width: 100, render: (value: number) => `${value} 分钟` },
                    {
                      title: '状态',
                      dataIndex: 'is_active',
                      width: 100,
                      render: (active: boolean) => <Tag color={active ? 'green' : 'default'}>{active ? '启用' : '停用'}</Tag>,
                    },
                    {
                      title: '上次执行',
                      dataIndex: 'last_message',
                      width: 260,
                      render: (message: string) => <span className="table-message-cell">{tDataMessage(message)}</span>,
                    },
                    {
                      title: '操作',
                      dataIndex: 'id',
                      width: 190,
                      render: (scheduleId: number, schedule: MarketDataSchedule) => (
                        <Space>
                          <Button
                            size="small"
                            onClick={() => handleRunMarketDataSchedule(scheduleId)}
                            loading={scheduleActionId === scheduleId}
                            disabled={!schedule.is_active}
                          >
                            立即执行
                          </Button>
                          <Button
                            size="small"
                            onClick={() => handleDisableMarketDataSchedule(scheduleId)}
                            disabled={!schedule.is_active}
                          >
                            停用
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  scroll={{ x: 980 }}
                  dataSource={marketDataSchedules.map((schedule) => ({ ...schedule, key: schedule.id }))}
                />
              </Card>
  )

  const strategyPanel = (
              <Card title="策略模板管理">
                {strategyParameterError ? <Alert type="error" showIcon title={strategyParameterError} className="form-alert" /> : null}
                {selectedStrategyTemplate ? (
                  <>
                    <div className="strategy-template-list">
                      {orderedStrategies.map((strategy, index) => {
                        const isSelected = strategy.strategy_id === selectedStrategyTemplate.strategy_id
                        return (
                          <button
                            type="button"
                            key={strategy.strategy_id}
                            className={`strategy-template-card${isSelected ? ' selected' : ''}`}
                            onClick={() => setSelectedStrategyTemplateId(strategy.strategy_id)}
                          >
                            <Space orientation="vertical" size={6} align="start">
                              <Space wrap>
                                <Tag color={index === 0 ? 'blue' : 'default'}>{index === 0 ? '第一模板' : '策略模板'}</Tag>
                                <Tag color="geekblue">{strategy.strategy_id}</Tag>
                              </Space>
                              <Text strong>{tStrategyName(strategy.display_name)}</Text>
                              <Text type="secondary">{tStrategyDescription(strategy.description)}</Text>
                              <Space wrap>
                                {strategy.supported_frequencies.map((frequency) => (
                                  <Tag color={frequency === '5m' ? 'blue' : 'default'} key={frequency}>
                                    {frequency}
                                  </Tag>
                                ))}
                              </Space>
                            </Space>
                          </button>
                        )
                      })}
                    </div>
                    <Space orientation="vertical" size={4} className="strategy-summary">
                      <Text strong>编辑策略配置</Text>
                      <Text type="secondary">
                        策略模板是前端配套的可变参策略；策略配置是基于当前模板保存的一套确定参数。
                      </Text>
                    </Space>
                    <Form
                      form={strategyParameterForm}
                      layout="vertical"
                      onFinish={handleCreateStrategyParameterSet}
                      className="strategy-parameter-form"
                    >
                      <Form.Item name="name" label="参数集名称" rules={[{ required: true }]}>
                        <Input placeholder="策略配置名称" />
                      </Form.Item>
                      <Form.Item name="strategy_id" hidden>
                        <Input />
                      </Form.Item>
                      <div className="strategy-parameter-grid">
                        {selectedStrategyTemplate.parameters.map((parameter) => (
                          <Form.Item
                            key={parameter.name}
                            name={parameter.name}
                            label={tParameterLabel(parameter.label)}
                            valuePropName={parameter.type === 'boolean' ? 'checked' : 'value'}
                            extra={tParameterDescription(parameter.description)}
                          >
                            {renderStrategyParameterInput(parameter)}
                          </Form.Item>
                        ))}
                      </div>
                      <Button type="primary" htmlType="submit" loading={strategyParameterSaving}>
                        保存策略配置
                      </Button>
                    </Form>
                  </>
                ) : (
                  <Text type="secondary">正在加载策略元数据</Text>
                )}
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: '名称', dataIndex: 'name', render: (name: string) => tDisplayText(name) },
                    { title: '策略模板', dataIndex: 'strategy_id', width: 190 },
                    {
                      title: '关键参数',
                      width: 360,
                      render: (_: unknown, record: StrategyParameterSet) => formatStrategyConfigParameters(record),
                    },
                  ]}
                  dataSource={strategyParameterSets.map((parameterSet) => ({ ...parameterSet, key: parameterSet.id }))}
                />
              </Card>
  )

  const backtestRunnerPanel = (
              <Card className={backtestQuickFocus ? 'quick-backtest-panel quick-focus' : 'quick-backtest-panel'} title="回测任务管理">
                {backtestError ? <Alert type="error" showIcon title={backtestError} className="form-alert" /> : null}
                <Form
                  form={backtestForm}
                  layout="inline"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    frequency: '5m',
                    parameter_set_id: strategyParameterSets[0]?.id,
                    initial_cash: 100000,
                  }}
                  onFinish={handleCreateBacktest}
                  className="instrument-form"
                >
                  <Form.Item name="instrument_id">
                    <Input placeholder="标的ID" />
                  </Form.Item>
                  <Form.Item name="portfolio_id">
                    <Input placeholder="组合ID" />
                  </Form.Item>
                  <Form.Item name="frequency" rules={[{ required: true }]}>
                    <Input placeholder="5m" />
                  </Form.Item>
                  <Form.Item name="parameter_set_id" rules={[{ required: true }]}>
                    <Input placeholder="参数集ID" />
                  </Form.Item>
                  <Form.Item name="initial_cash" rules={[{ required: true }]}>
                    <InputNumber min={1} placeholder="初始资金" />
                  </Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={backtestRunning}
                    disabled={(!instruments.length && !portfolios.length) || !strategyParameterSets.length}
                  >
                    运行回测
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '策略', dataIndex: 'strategy_id', width: 150 },
                    {
                      title: '范围',
                      dataIndex: 'config',
                      width: 150,
                      render: (config: BacktestRun['config']) =>
                        config.scope === 'portfolio'
                          ? `组合 #${config.portfolio_id ?? '-'}`
                          : `标的 #${config.instrument_id ?? '-'}`,
                    },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'succeeded' ? 'green' : 'red'}>{tStatus(status)}</Tag>,
                    },
                    {
                      title: '收益率',
                      dataIndex: 'metrics',
                      width: 110,
                      render: (metrics: BacktestRun['metrics']) => `${(((metrics.cumulative_return ?? 0) as number) * 100).toFixed(2)}%`,
                    },
                    {
                      title: '最大回撤',
                      dataIndex: 'metrics',
                      width: 110,
                      render: (metrics: BacktestRun['metrics']) => `${(((metrics.max_drawdown ?? 0) as number) * 100).toFixed(2)}%`,
                    },
                    {
                      title: '交易数',
                      dataIndex: 'metrics',
                      width: 90,
                      render: (metrics: BacktestRun['metrics']) => metrics.trade_count ?? 0,
                    },
                    {
                      title: '信号',
                      dataIndex: 'result_payload',
                      width: 180,
                      render: (payload: BacktestRun['result_payload']) => {
                        const signal = payload.signal_summary
                        if (!signal) {
                          return '-'
                        }
                        return (
                          <Space size={4} wrap>
                            <Tag color={signal.latest_signal === 'buy' ? 'green' : 'volcano'}>
                              {tStatus(signal.latest_signal)}
                            </Tag>
                            <Text type="secondary">
                              执行 {signal.executed_signal_count ?? 0} / 拦截 {signal.blocked_signal_count ?? 0}
                            </Text>
                          </Space>
                        )
                      },
                    },
                    {
                      title: '权益点数',
                      dataIndex: 'result_payload',
                      width: 130,
                      render: (payload: BacktestRun['result_payload']) => payload.equity_curve?.length ?? 0,
                    },
                    {
                      title: '复核',
                      dataIndex: 'id',
                      width: 100,
                      render: (backtestId: number) => (
                        <Button size="small" onClick={() => setSelectedBacktestId(backtestId)}>
                          查看
                        </Button>
                      ),
                    },
                  ]}
                  scroll={{ x: 1120 }}
                  dataSource={backtests.map((backtest) => ({
                    ...backtest,
                    key: backtest.id,
                    className: selectedBacktest?.id === backtest.id ? 'selected-row' : '',
                  }))}
                />
              </Card>
  )

  const backtestReviewPanel = (
              <Card
                title={
                  <Space>
                    <AreaChartOutlined />
                    回测结果复核
                  </Space>
                }
              >
                {selectedBacktest ? (
                  <Space orientation="vertical" size={16} className="review-panel">
                    <div className="review-header">
                      <Space wrap>
                        <Tag color="blue">回测 #{selectedBacktest.id}</Tag>
                        <Tag color={selectedBacktest.status === 'succeeded' ? 'green' : 'red'}>
                          {tStatus(selectedBacktest.status)}
                        </Tag>
                        <Text type="secondary">{selectedBacktest.strategy_id}</Text>
                      </Space>
                      <Button
                        size="small"
                        onClick={() =>
                          snapshotForm.setFieldsValue({
                            backtest_run_id: selectedBacktest.id,
                            title: `策略展示报告 #${selectedBacktest.id}`,
                          })
                        }
                      >
                        用于快照
                      </Button>
                    </div>
                    <div className="review-metrics">
                      <div>
                        <Text type="secondary">累计收益</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.cumulative_return)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">最大回撤</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.max_drawdown)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">胜率</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.win_rate)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">交易数</Text>
                        <strong>{selectedBacktest.metrics.trade_count ?? 0}</strong>
                      </div>
                      <div>
                        <Text type="secondary">盈亏比</Text>
                        <strong>{formatNumber(selectedBacktest.metrics.profit_loss_ratio)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">最新信号</Text>
                        <strong>{tStatus(selectedSignal?.latest_signal)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">执行/拦截</Text>
                        <strong>
                          {selectedSignal?.executed_signal_count ?? 0} / {selectedSignal?.blocked_signal_count ?? 0}
                        </strong>
                      </div>
                    </div>
                    {selectedSignal ? (
                      <Alert
                        type="info"
                        showIcon
                        title={`信号决策：${tStatus(selectedSignal.latest_decision)}`}
                        description={selectedSignal.latest_reason ?? '当前回测未记录信号解释。'}
                      />
                    ) : null}
                    <div className="review-chart-grid">
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>权益曲线</Text>
                          <Text type="secondary">{selectedEquity.length} 个点</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="权益曲线">
                          <polyline points={chartPoints(selectedEquity)} />
                        </svg>
                      </div>
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>回撤曲线</Text>
                          <Text type="secondary">{selectedDrawdown.length} 个点</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="回撤曲线">
                          <polyline points={chartPoints(selectedDrawdown)} />
                        </svg>
                      </div>
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>仓位曲线</Text>
                          <Text type="secondary">{selectedPosition.length} 个点</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="仓位曲线">
                          <polyline points={chartPoints(selectedPosition)} />
                        </svg>
                      </div>
                    </div>
                    <Table
                      size="small"
                      pagination={{ pageSize: 4 }}
                      columns={[
                        {
                          title: '时间',
                          dataIndex: 'timestamp',
                          width: 190,
                          render: (value: string) => new Date(value).toLocaleString(),
                        },
                        {
                          title: '方向',
                          dataIndex: 'side',
                          width: 90,
                          render: (side: string) => <Tag color={side === 'buy' ? 'green' : 'volcano'}>{tStatus(side)}</Tag>,
                        },
                        { title: '价格', dataIndex: 'price', width: 100, render: (_: unknown, trade: Record<string, unknown>) => tradeValue(trade, 'price') },
                        {
                          title: '涨跌幅',
                          dataIndex: 'change_percent',
                          width: 120,
                          render: (_: unknown, trade: Record<string, unknown>) => `${tradeValue(trade, 'change_percent')}%`,
                        },
                      ]}
                      dataSource={selectedTrades.map((trade, index) => ({ ...trade, key: index }))}
                    />
                    <Text type="secondary">
                      {tDisplayText(
                        selectedBacktest.result_payload.risk_disclosure ??
                          'Backtest results are simulated and do not represent real-money trading.',
                      )}
                    </Text>
                  </Space>
                ) : (
                  <Text type="secondary">请先运行回测，再复核指标、曲线和交易明细后发布。</Text>
                )}
              </Card>
  )

  const paperPanel = (
              <Card title="模拟运行管理">
                {paperRunError ? <Alert type="error" showIcon title={paperRunError} className="form-alert" /> : null}
                <Form
                  form={paperRunForm}
                  layout="inline"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    frequency: '5m',
                    parameter_set_id: strategyParameterSets[0]?.id,
                    initial_cash: 100000,
                  }}
                  onFinish={handleCreatePaperRun}
                  className="instrument-form"
                >
                  <Form.Item name="instrument_id" rules={[{ required: true }]}>
                    <Input placeholder="标的ID" />
                  </Form.Item>
                  <Form.Item name="frequency" rules={[{ required: true }]}>
                    <Input placeholder="5m" />
                  </Form.Item>
                  <Form.Item name="parameter_set_id" rules={[{ required: true }]}>
                    <Input placeholder="参数集ID" />
                  </Form.Item>
                  <Form.Item name="initial_cash" rules={[{ required: true }]}>
                    <InputNumber min={1} placeholder="初始资金" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={paperRunStarting} disabled={!instruments.length || !strategyParameterSets.length}>
                    运行模拟
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '策略', dataIndex: 'strategy_id', width: 150 },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={taskStatusColor(status)}>{tStatus(status)}</Tag>,
                    },
                    {
                      title: '最新权益',
                      dataIndex: 'latest_equity',
                      width: 130,
                      render: (value: number) => value.toFixed(2),
                    },
                    {
                      title: '最新信号',
                      dataIndex: 'config',
                      width: 130,
                      render: (config: PaperRun['config']) => tStatus(config.metrics?.latest_signal ?? 'hold'),
                    },
                    {
                      title: '决策',
                      dataIndex: 'config',
                      width: 130,
                      render: (config: PaperRun['config']) =>
                        tStatus(config.metrics?.latest_decision ?? config.paper_summary?.latest_decision ?? 'hold'),
                    },
                    {
                      title: '仓位',
                      dataIndex: 'config',
                      width: 110,
                      render: (config: PaperRun['config']) => `${config.metrics?.latest_position_percent ?? 0}%`,
                    },
                    {
                      title: '交易数',
                      dataIndex: 'config',
                      width: 90,
                      render: (config: PaperRun['config']) => config.metrics?.trade_count ?? 0,
                    },
                    {
                      title: '模拟成交',
                      dataIndex: 'config',
                      width: 110,
                      render: (config: PaperRun['config']) =>
                        config.paper_trades?.length ?? config.metrics?.simulated_trade_count ?? 0,
                    },
                    {
                      title: '失败原因',
                      width: 220,
                      render: (_: unknown, record: PaperRun) =>
                        record.status === 'failed' ? record.config.error?.message ?? record.message : '-',
                    },
                    {
                      title: '结束时间',
                      dataIndex: 'finished_at',
                      width: 180,
                      render: (value: string | null | undefined) => formatDateTime(value),
                    },
                  ]}
                  expandable={{
                    expandedRowRender: (record: PaperRun) => (
                      <div className="paper-run-detail">
                        <div>
                          <Text strong>状态流转</Text>
                          <Space wrap size={6}>
                            {(record.config.state_history ?? []).map((entry, index) => (
                              <Tag color={taskStatusColor(entry.status)} key={`${entry.status}-${entry.at ?? index}`}>
                                {tStatus(entry.status)} · {formatDateTime(entry.at)}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                        <div>
                          <Text strong>信号说明</Text>
                          <Text type="secondary">
                            {record.config.paper_summary?.latest_reason ??
                              record.config.error?.message ??
                              '当前模拟运行未记录信号说明。'}
                          </Text>
                        </div>
                        <div>
                          <Text strong>监控数据</Text>
                          <Text type="secondary">
                            K线 {record.config.data_snapshot?.bar_count ?? 0} 根 · 信号{' '}
                            {record.config.paper_signals?.length ?? record.config.metrics?.signal_count ?? 0} 个 · 模拟成交{' '}
                            {record.config.paper_trades?.length ?? record.config.metrics?.simulated_trade_count ?? 0} 笔
                          </Text>
                        </div>
                      </div>
                    ),
                  }}
                  dataSource={paperRuns.map((paperRun) => ({ ...paperRun, key: paperRun.id }))}
                />
              </Card>
  )

  const snapshotsPanel = (
              <Card title="快照发布">
                {snapshotError ? <Alert type="error" showIcon title={snapshotError} className="form-alert" /> : null}
                {latestShareToken ? (
                  <Alert
                    type="success"
                    showIcon
                    className="form-alert"
                    title="客户报告链接已生成"
                    description={<CopyLinkButton token={latestShareToken} />}
                  />
                ) : null}
                <Form
                  form={snapshotForm}
                  layout="inline"
                  initialValues={{
                    backtest_run_id: backtests[0]?.id,
                    title: backtests[0] ? `策略展示报告 #${backtests[0].id}` : '滚动做T策略报告',
                  }}
                  onFinish={handlePublishSnapshot}
                  className="instrument-form"
                >
                  <Form.Item name="backtest_run_id" rules={[{ required: true }]}>
                    <Input placeholder="回测任务ID" />
                  </Form.Item>
                  <Form.Item name="title" rules={[{ required: true }]}>
                    <Input placeholder="快照标题" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={snapshotPublishing} disabled={!backtests.length}>
                    发布快照
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '标题', dataIndex: 'title', render: (title: string) => tDisplayText(title) },
                    { title: '回测', dataIndex: 'backtest_run_id', width: 100 },
                    { title: '版本', dataIndex: 'version', width: 90 },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'published' ? 'green' : 'red'}>{tStatus(status)}</Tag>,
                    },
                    {
                      title: '操作',
                      dataIndex: 'id',
                      width: 120,
                      render: (snapshotId: number, snapshot: PublishedSnapshot) => (
                        <Button
                          size="small"
                          onClick={() => handleRevokeSnapshot(snapshotId)}
                          loading={snapshotRevokingId === snapshotId}
                          disabled={snapshot.status !== 'published'}
                        >
                          撤销
                        </Button>
                      ),
                    },
                  ]}
                  dataSource={snapshots.map((snapshot) => ({ ...snapshot, key: snapshot.id }))}
                />
              </Card>
  )

  const shareLinksPanel = (
              <Card title="客户分享链接管理">
                {shareLinkError ? <Alert type="error" showIcon title={shareLinkError} className="form-alert" /> : null}
                {latestShareToken ? (
                  <Alert
                    type="success"
                    showIcon
                    className="form-alert"
                    title="新分享链接已就绪"
                    description={<CopyLinkButton token={latestShareToken} />}
                  />
                ) : null}
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: '链接ID', dataIndex: 'id', width: 80 },
                    { title: '快照', dataIndex: 'snapshot_id', width: 100 },
                    { title: '标题', dataIndex: 'snapshot_title', render: (title: string) => tDisplayText(title) },
                    {
                      title: '快照状态',
                      dataIndex: 'snapshot_status',
                      width: 140,
                      render: (status: string) => <Tag color={status === 'published' ? 'green' : 'red'}>{tStatus(status)}</Tag>,
                    },
                    {
                      title: '链接状态',
                      dataIndex: 'is_active',
                      width: 120,
                      render: (isActive: boolean) => <Tag color={isActive ? 'green' : 'default'}>{isActive ? '有效' : '已撤销'}</Tag>,
                    },
                    {
                      title: '创建时间',
                      dataIndex: 'created_at',
                      width: 190,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                    {
                      title: '操作',
                      dataIndex: 'id',
                      width: 250,
                      render: (shareLinkId: number, shareLink: ShareLink) => (
                        <Space>
                          <Button
                            size="small"
                            icon={<LinkOutlined />}
                            onClick={() => handleCreateShareLink(shareLink.snapshot_id)}
                            loading={shareLinkCreatingId === shareLink.snapshot_id}
                            disabled={shareLink.snapshot_status !== 'published'}
                          >
                            新建链接
                          </Button>
                          <Button
                            size="small"
                            onClick={() => handleRevokeShareLink(shareLinkId)}
                            loading={shareLinkRevokingId === shareLinkId}
                            disabled={!shareLink.is_active}
                          >
                            撤销链接
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  dataSource={shareLinks.map((shareLink) => ({ ...shareLink, key: shareLink.id }))}
                />
              </Card>
  )

  const keyStatusPanel = (
              <Card title="关键步骤状态">
                <div className="overview-status-list">
                  <div>
                    <Text type="secondary">数据准备</Text>
                    <Tag color={dataCompleteness?.status === 'ok' ? 'green' : dataCompleteness?.status === 'warning' ? 'orange' : 'default'}>
                      {tStatus(dataCompleteness?.status ?? 'unchecked')}
                    </Tag>
                    <strong>{dataCompleteness?.bar_count ?? bars.length} 条K线</strong>
                  </div>
                  <div>
                    <Text type="secondary">参数配置</Text>
                    <Tag color={strategyParameterSets.length ? 'green' : 'gold'}>{strategyParameterSets.length ? '已就绪' : '待配置'}</Tag>
                    <strong>{strategyParameterSets.length} 套参数</strong>
                  </div>
                  <div>
                    <Text type="secondary">回测复核</Text>
                    <Tag color={selectedBacktest?.status === 'succeeded' ? 'green' : selectedBacktest ? 'red' : 'default'}>
                      {selectedBacktest ? tStatus(selectedBacktest.status) : '待运行'}
                    </Tag>
                    <strong>{selectedBacktest ? `#${selectedBacktest.id} · ${formatPercent(selectedBacktest.metrics.cumulative_return)}` : '暂无回测'}</strong>
                  </div>
                  <div>
                    <Text type="secondary">报告发布</Text>
                    <Tag color={snapshots[0]?.status === 'published' ? 'green' : 'default'}>{snapshots[0] ? tStatus(snapshots[0].status) : '待发布'}</Tag>
                    <strong>{shareLinks.filter((link) => link.is_active).length} 个有效链接</strong>
                  </div>
                  <div>
                    <Text type="secondary">模拟运行</Text>
                    <Tag color={paperRuns[0]?.status === 'succeeded' ? 'green' : paperRuns[0]?.status === 'failed' ? 'red' : 'default'}>
                      {paperRuns[0] ? tStatus(paperRuns[0].status) : '待运行'}
                    </Tag>
                    <strong>{paperRuns[0] ? `权益 ${formatNumber(paperRuns[0].latest_equity)}` : '暂无记录'}</strong>
                  </div>
                </div>
              </Card>
  )

  const keyDataPanel = (
              <Card title="重点数据">
                <div className="overview-data-grid">
                  <div>
                    <Text type="secondary">标的 / 组合</Text>
                    <strong>{instruments.length} / {portfolios.length}</strong>
                  </div>
                  <div>
                    <Text type="secondary">导入任务</Text>
                    <strong>{dataImportTasks.length}</strong>
                  </div>
                  <div>
                    <Text type="secondary">行情计划</Text>
                    <strong>{marketDataSchedules.filter((schedule) => schedule.is_active).length} 启用</strong>
                  </div>
                  <div>
                    <Text type="secondary">回测任务</Text>
                    <strong>{backtests.length}</strong>
                  </div>
                  <div>
                    <Text type="secondary">最新回撤</Text>
                    <strong>{selectedBacktest ? formatPercent(selectedBacktest.metrics.max_drawdown) : '-'}</strong>
                  </div>
                  <div>
                    <Text type="secondary">快照 / 分享</Text>
                    <strong>{snapshots.length} / {shareLinks.filter((link) => link.is_active).length}</strong>
                  </div>
                </div>
              </Card>
  )

  const boundariesPanel = (
              <Card
                title={
                  <Space>
                    <AreaChartOutlined />
                    系统边界
                  </Space>
                }
              >
                <div className="boundary-list">
                  <Tag color="blue">V1 不接入实盘交易</Tag>
                  <Tag color="purple">前端不承载策略逻辑</Tag>
                  <Tag color="cyan">已发布快照不可变更</Tag>
                  <Tag color="geekblue">vn.py 保持为底层参考</Tag>
                </div>
              </Card>
  )

  const logsPanel = (
              <Card title="操作日志">
                <Table
                  size="small"
                  pagination={{ pageSize: 6 }}
                  columns={[
                    { title: '动作', dataIndex: 'action', render: (action: string) => tAction(action) },
                    { title: '操作人', dataIndex: 'actor', width: 110 },
                    { title: '对象', dataIndex: 'target_type', width: 120, render: (targetType: string) => tTargetType(targetType) },
                    {
                      title: '创建时间',
                      dataIndex: 'created_at',
                      width: 210,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                  ]}
                  dataSource={operationLogs.map((log) => ({ ...log, key: log.id }))}
                />
              </Card>
  )

  const loginPanel = (
    <main className="login-shell">
      <Card className="login-card">
        <Space orientation="vertical" size={18}>
          <div className="login-brand">
            <ApiOutlined />
            <div>
              <Title level={3}>量化系统管理端</Title>
              <Text type="secondary">登录后管理策略、回测、展示快照和审计日志。</Text>
            </div>
          </div>
          {loginError ? <Alert type="error" showIcon title={loginError} /> : null}
          <Form
            layout="vertical"
            initialValues={{ username: 'admin', password: 'admin' }}
            onFinish={handleLogin}
          >
            <Form.Item label="用户名" name="username" rules={[{ required: true }]}>
              <Input autoComplete="username" />
            </Form.Item>
            <Form.Item label="密码" name="password" rules={[{ required: true }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loginLoading} block>
              登录
            </Button>
          </Form>
        </Space>
      </Card>
    </main>
  )

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#2563eb',
          borderRadius: 6,
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
      }}
    >
      {!currentUser ? (
        loginPanel
      ) : (
      <Layout className="admin-shell">
        <Sider width={232} className="admin-sider">
          <div className="brand">
            <ApiOutlined />
            <div>
              <strong>量化系统</strong>
              <span>管理控制台</span>
            </div>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[activeSection]}
            items={researchModules}
            onClick={({ key }) => setActiveSection(String(key))}
          />
        </Sider>
        <Layout>
          <Header className="admin-header">
            <div>
              <Title level={4}>量化策略管理台</Title>
              <Text type="secondary">管理规则策略的研究、回测、模拟运行、发布和审计。</Text>
            </div>
            <Space>
              <Badge status={apiStatus === 'Connected' ? 'success' : 'processing'} text={`API ${tStatus(apiStatus)}`} />
              <Tag color="blue">管理员：{currentUser.username}</Tag>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleQuickBacktest}
                disabled={!instruments.length || !strategyParameterSets.length}
              >
                快速新建回测
              </Button>
              <Button onClick={handleLogout}>退出登录</Button>
            </Space>
          </Header>
          <Content className="admin-content">
            <CommandRail items={commandRailItems} activeSection={activeSection} onSelect={setActiveSection} />
            <section className={metricsCollapsed ? 'metric-strip collapsed' : 'metric-strip'}>
              <Button
                className="metric-collapse-button"
                size="small"
                icon={metricsCollapsed ? <DownOutlined /> : <UpOutlined />}
                onClick={() => setMetricsCollapsed((collapsed) => !collapsed)}
              >
                {metricsCollapsed ? '展开概览' : '收起'}
              </Button>
              {!metricsCollapsed ? (
              <div className="metric-grid">
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">已管理标的</Text>
                  <Title level={2}>{instruments.length}</Title>
                  <Text>{instruments[0] ? `${instruments[0].symbol}.${instruments[0].exchange}` : '请先在下方创建第一只股票'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">固定组合</Text>
                  <Title level={2}>{portfolios.length}</Title>
                  <Text>{portfolios[0] ? tDisplayText(portfolios[0].name) : '添加标的后创建组合'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">策略模板</Text>
                  <Title level={2}>{strategies.length}</Title>
                  <Text>
                    {strategyParameterSets.length
                      ? `已保存 ${strategyParameterSets.length} 套策略配置`
                      : orderedStrategies[0] ? `第一模板：${tStrategyName(orderedStrategies[0].display_name)}` : '正在加载策略注册表'}
                  </Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">已发布快照</Text>
                  <Title level={2}>{snapshots.length}</Title>
                  <Text>{snapshots[0] ? `最新状态：${tStatus(snapshots[0].status)}` : '请发布已复核的回测'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">有效分享链接</Text>
                  <Title level={2}>{shareLinks.filter((link) => link.is_active).length}</Title>
                  <Text>{shareLinks[0] ? `最新快照 #${shareLinks[0].snapshot_id}` : '请创建客户展示链接'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">模拟运行</Text>
                  <Title level={2}>{paperRuns.length}</Title>
                  <Text>{paperRuns[0] ? `最新权益 ${paperRuns[0].latest_equity.toFixed(2)}` : '请发起一次手动模拟'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">已导入K线</Text>
                  <Title level={2}>{bars.length}</Title>
                  <Text>{bars[0] ? `${bars[0].frequency} 最新收盘 ${bars[bars.length - 1]?.close}` : '请导入CSV行情数据'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">V1 进度</Text>
                  <Progress percent={64} size="small" />
                  <Text>手动模拟运行已接通</Text>
                </Space>
              </Card>
              </div>
              ) : null}
            </section>

            <section className="workspace">
              <div hidden={activeSection !== 'overview'}>
                <OverviewSection keyStatus={keyStatusPanel} keyData={keyDataPanel} />
              </div>
              <div hidden={activeSection !== 'data'}>
                <DataSection
                  instruments={instrumentPanel}
                  portfolios={portfolioPanel}
                  marketData={marketDataPanel}
                  importTasks={importTasksPanel}
                  schedules={schedulesPanel}
                />
              </div>
              <div hidden={activeSection !== 'strategy'}>
                <StrategySection editor={strategyPanel} />
              </div>
              <div hidden={activeSection !== 'backtest'}>
                <BacktestSection runner={backtestRunnerPanel} review={backtestReviewPanel} />
              </div>
              <div hidden={activeSection !== 'publication'}>
                <PublicationSection snapshots={snapshotsPanel} links={shareLinksPanel} />
              </div>
              <div hidden={activeSection !== 'paper'}>
                <PaperSection paper={paperPanel} />
              </div>
              <div hidden={activeSection !== 'audit'}>
                <AuditSection logs={logsPanel} boundaries={boundariesPanel} />
              </div>
            </section>
          </Content>
        </Layout>
      </Layout>
      )}
    </ConfigProvider>
  )
}

export default App
