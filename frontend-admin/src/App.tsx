import {
  ApiOutlined,
  AreaChartOutlined,
  AuditOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FundProjectionScreenOutlined,
  LineChartOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
  StockOutlined,
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
import { useEffect, useState } from 'react'
import {
  fetchOperationLogs,
  fetchProfile,
  fetchInstruments,
  fetchDataImportTasks,
  fetchBacktests,
  fetchMarketBars,
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
import './App.css'

const { Header, Sider, Content } = Layout
const { Text, Title } = Typography
const DISPLAY_BASE_URL = import.meta.env.VITE_DISPLAY_BASE_URL ?? 'http://127.0.0.1:5184'

const modules = [
  { key: 'portfolios', icon: <StockOutlined />, label: 'Portfolios' },
  { key: 'data', icon: <DatabaseOutlined />, label: 'Market Data' },
  { key: 'strategies', icon: <DeploymentUnitOutlined />, label: 'Strategies' },
  { key: 'backtests', icon: <BarChartOutlined />, label: 'Backtests' },
  { key: 'paper', icon: <PlayCircleOutlined />, label: 'Paper Runs' },
  { key: 'snapshots', icon: <FundProjectionScreenOutlined />, label: 'Snapshots' },
  { key: 'links', icon: <LinkOutlined />, label: 'Share Links' },
  { key: 'logs', icon: <AuditOutlined />, label: 'Logs' },
]

const tasks = [
  { key: 1, name: 'CSI 300 grid backtest', type: 'Backtest', status: 'Pending', updatedAt: '2026-06-01 10:30' },
  { key: 2, name: '600519.SH 5m data sync', type: 'Data', status: 'Succeeded', updatedAt: '2026-06-01 09:42' },
  { key: 3, name: 'rolling_t_grid paper run', type: 'Paper', status: 'Running', updatedAt: '2026-06-01 09:30' },
]

function clientReportUrl(shareToken: string): string {
  return `${DISPLAY_BASE_URL.replace(/\/$/, '')}/?token=${encodeURIComponent(shareToken)}`
}

function formatPercent(value: number | undefined): string {
  return `${((value ?? 0) * 100).toFixed(2)}%`
}

function formatNumber(value: number | undefined): string {
  return (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
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

function App() {
  const [strategies, setStrategies] = useState<StrategyTemplate[]>([])
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [bars, setBars] = useState<Bar[]>([])
  const [backtests, setBacktests] = useState<BacktestRun[]>([])
  const [paperRuns, setPaperRuns] = useState<PaperRun[]>([])
  const [dataImportTasks, setDataImportTasks] = useState<DataImportTask[]>([])
  const [marketDataSchedules, setMarketDataSchedules] = useState<MarketDataSchedule[]>([])
  const [snapshots, setSnapshots] = useState<PublishedSnapshot[]>([])
  const [shareLinks, setShareLinks] = useState<ShareLink[]>([])
  const [latestShareToken, setLatestShareToken] = useState('')
  const [selectedBacktestId, setSelectedBacktestId] = useState<number | null>(null)
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
        } else {
          setBars([])
        }
      })
      .catch(() => {
        setApiStatus('Offline')
        setCurrentUser(null)
        setOperationLogs([])
        setInstruments([])
        setPortfolios([])
        setBars([])
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
        title: `Strategy Report #${backtests[0].id}`,
      })
    }
  }, [backtests, snapshotForm])

  useEffect(() => {
    const firstStrategy = strategies[0]
    if (!currentUser || !firstStrategy) {
      return
    }

    const defaultValues = Object.fromEntries(
      firstStrategy.parameters.map((parameter) => [parameter.name, parameter.default]),
    )
    strategyParameterForm.setFieldsValue({
      name: `${firstStrategy.display_name} default`,
      strategy_id: firstStrategy.strategy_id,
      ...defaultValues,
    })
  }, [currentUser, strategies, strategyParameterForm])

  const handleLogin = (values: { username: string; password: string }) => {
    setLoginLoading(true)
    setLoginError('')
    login(values.username, values.password)
      .then((payload) => {
        localStorage.setItem('quant_admin_token', payload.access_token)
        setToken(payload.access_token)
      })
      .catch(() => setLoginError('Invalid username or password. Use admin / admin for the local seed account.'))
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
          fetchDataImportTasks(token),
          fetchOperationLogs(token),
        ])
      })
      .then(([barPayload, importTaskPayload, logPayload]) => {
        setBars(barPayload)
        setDataImportTasks(importTaskPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'CSV import failed'))
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
      frequency: values.frequency || '5m',
      adjust: values.adjust || '',
    })
      .then(() => {
        const instrumentId = Number(values.instrument_id)
        return Promise.all([
          fetchMarketBars(token, instrumentId, values.frequency || '5m'),
          fetchDataImportTasks(token),
          fetchOperationLogs(token),
        ])
      })
      .then(([barPayload, importTaskPayload, logPayload]) => {
        setBars(barPayload)
        setDataImportTasks(importTaskPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'Public data fetch failed'))
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
      frequency: values.frequency || '5m',
      adjust: values.adjust || '',
    })
      .then(() => Promise.all([fetchMarketDataSchedules(token), fetchOperationLogs(token)]))
      .then(([schedulePayload, logPayload]) => {
        setMarketDataSchedules(schedulePayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'Schedule save failed'))
      .finally(() => setScheduleSaving(false))
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
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'Schedule run failed'))
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
      .catch((error) => setMarketDataError(error instanceof Error ? error.message : 'Schedule disable failed'))
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
    if (!token || !strategies[0]) {
      return
    }

    const strategy = strategies[0]
    const parameters = Object.fromEntries(
      strategy.parameters.map((parameter) => [parameter.name, values[parameter.name] ?? parameter.default]),
    )

    setStrategyParameterSaving(true)
    setStrategyParameterError('')
    createStrategyParameterSet(token, {
      strategy_id: strategy.strategy_id,
      name: String(values.name || `${strategy.display_name} config`),
      parameters,
    })
      .then(() => Promise.all([fetchStrategyParameterSets(token), fetchOperationLogs(token)]))
      .then(([parameterSetPayload, logPayload]) => {
        setStrategyParameterSets(parameterSetPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setStrategyParameterError(error instanceof Error ? error.message : 'Strategy config save failed'))
      .finally(() => setStrategyParameterSaving(false))
  }

  const handleCreateBacktest = (values: BacktestInput) => {
    if (!token) {
      return
    }

    setBacktestRunning(true)
    setBacktestError('')
    createBacktest(token, {
      instrument_id: Number(values.instrument_id),
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
      .catch((error) => setBacktestError(error instanceof Error ? error.message : 'Backtest failed'))
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
      .catch((error) => setPaperRunError(error instanceof Error ? error.message : 'Paper simulation failed'))
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
      title: values.title || `Strategy Report #${values.backtest_run_id}`,
    })
      .then((payload) => {
        setLatestShareToken(payload.share_token)
        return Promise.all([fetchSnapshots(token), fetchOperationLogs(token)])
      })
      .then(([snapshotPayload, logPayload]) => {
        setSnapshots(snapshotPayload)
        setOperationLogs(logPayload)
      })
      .catch((error) => setSnapshotError(error instanceof Error ? error.message : 'Snapshot publish failed'))
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
      .catch((error) => setShareLinkError(error instanceof Error ? error.message : 'Share link create failed'))
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
      .catch((error) => setShareLinkError(error instanceof Error ? error.message : 'Share link revoke failed'))
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
      .catch((error) => setSnapshotError(error instanceof Error ? error.message : 'Snapshot revoke failed'))
      .finally(() => setSnapshotRevokingId(null))
  }

  const selectedBacktest = backtests.find((backtest) => backtest.id === selectedBacktestId) ?? backtests[0] ?? null
  const selectedTrades = selectedBacktest?.result_payload.trade_table ?? []
  const selectedEquity = selectedBacktest?.result_payload.equity_curve ?? []
  const selectedDrawdown = selectedBacktest?.result_payload.drawdown_curve ?? []
  const selectedPosition = selectedBacktest?.result_payload.position_curve ?? []

  const loginPanel = (
    <main className="login-shell">
      <Card className="login-card">
        <Space orientation="vertical" size={18}>
          <div className="login-brand">
            <ApiOutlined />
            <div>
              <Title level={3}>Quant System Admin</Title>
              <Text type="secondary">Sign in to manage strategies, backtests, snapshots, and audit logs.</Text>
            </div>
          </div>
          {loginError ? <Alert type="error" showIcon title={loginError} /> : null}
          <Form
            layout="vertical"
            initialValues={{ username: 'admin', password: 'admin' }}
            onFinish={handleLogin}
          >
            <Form.Item label="Username" name="username" rules={[{ required: true }]}>
              <Input autoComplete="username" />
            </Form.Item>
            <Form.Item label="Password" name="password" rules={[{ required: true }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loginLoading} block>
              Sign In
            </Button>
          </Form>
        </Space>
      </Card>
    </main>
  )

  return (
    <ConfigProvider
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
              <strong>Quant System</strong>
              <span>Admin Console</span>
            </div>
          </div>
          <Menu mode="inline" defaultSelectedKeys={['backtests']} items={modules} />
        </Sider>
        <Layout>
          <Header className="admin-header">
            <div>
              <Title level={4}>Quant Strategy Admin</Title>
              <Text type="secondary">Research, backtest, simulate, publish, and audit rule-based strategies.</Text>
            </div>
            <Space>
              <Badge status={apiStatus === 'Connected' ? 'success' : 'processing'} text={`API ${apiStatus}`} />
              <Tag color="blue">Admin: {currentUser.username}</Tag>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => backtestForm.submit()}
                disabled={!instruments.length || !strategyParameterSets.length}
              >
                New Backtest
              </Button>
              <Button onClick={handleLogout}>Sign Out</Button>
            </Space>
          </Header>
          <Content className="admin-content">
            <section className="metric-grid">
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Managed Instruments</Text>
                  <Title level={2}>{instruments.length}</Title>
                  <Text>{instruments[0] ? `${instruments[0].symbol}.${instruments[0].exchange}` : 'Create the first stock below'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Fixed Portfolios</Text>
                  <Title level={2}>{portfolios.length}</Title>
                  <Text>{portfolios[0]?.name ?? 'Create a basket after adding instruments'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Strategy Templates</Text>
                  <Title level={2}>{strategies.length}</Title>
                  <Text>
                    {strategyParameterSets.length
                      ? `${strategyParameterSets.length} saved parameter sets`
                      : strategies[0]?.display_name ?? 'Loading strategy registry'}
                  </Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Published Snapshots</Text>
                  <Title level={2}>{snapshots.length}</Title>
                  <Text>{snapshots[0] ? `Latest ${snapshots[0].status}` : 'Publish a reviewed backtest'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Active Share Links</Text>
                  <Title level={2}>{shareLinks.filter((link) => link.is_active).length}</Title>
                  <Text>{shareLinks[0] ? `Latest snapshot #${shareLinks[0].snapshot_id}` : 'Create a client link'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Paper Runs</Text>
                  <Title level={2}>{paperRuns.length}</Title>
                  <Text>{paperRuns[0] ? `Latest equity ${paperRuns[0].latest_equity.toFixed(2)}` : 'Run a manual simulation'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">Imported Bars</Text>
                  <Title level={2}>{bars.length}</Title>
                  <Text>{bars[0] ? `${bars[0].frequency} latest ${bars[bars.length - 1]?.close}` : 'Import CSV market data'}</Text>
                </Space>
              </Card>
              <Card>
                <Space orientation="vertical" size={4}>
                  <Text type="secondary">V1 Progress</Text>
                  <Progress percent={64} size="small" />
                  <Text>Manual paper simulation connected</Text>
                </Space>
              </Card>
            </section>

            <section className="workspace">
              <Card title="Instrument Management">
                <Form
                  form={instrumentForm}
                  layout="inline"
                  initialValues={{ symbol: '600519', exchange: 'SH', name: 'Kweichow Moutai', asset_type: 'stock' }}
                  onFinish={handleCreateInstrument}
                  className="instrument-form"
                >
                  <Form.Item name="symbol" rules={[{ required: true }]}><Input placeholder="Symbol" /></Form.Item>
                  <Form.Item name="exchange" rules={[{ required: true }]}><Input placeholder="Exchange" /></Form.Item>
                  <Form.Item name="name" rules={[{ required: true }]}><Input placeholder="Name" /></Form.Item>
                  <Form.Item name="asset_type" rules={[{ required: true }]}><Input placeholder="Asset Type" /></Form.Item>
                  <Button type="primary" htmlType="submit" loading={instrumentSaving}>Add Instrument</Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'Symbol', dataIndex: 'symbol', width: 110 },
                    { title: 'Exchange', dataIndex: 'exchange', width: 110 },
                    { title: 'Name', dataIndex: 'name' },
                    { title: 'Type', dataIndex: 'asset_type', width: 100 },
                  ]}
                  dataSource={instruments.map((instrument) => ({ ...instrument, key: instrument.id }))}
                />
              </Card>

              <Card title="Fixed Portfolio Management">
                <Form
                  form={portfolioForm}
                  layout="inline"
                  initialValues={{
                    name: 'Core A-share Basket',
                    description: 'Fixed demo portfolio for V1 backtests.',
                    instrument_id: instruments[0]?.id,
                    weight: 1,
                  }}
                  onFinish={handleCreatePortfolio}
                  className="instrument-form"
                >
                  <Form.Item name="name" rules={[{ required: true }]}><Input placeholder="Portfolio Name" /></Form.Item>
                  <Form.Item name="description"><Input placeholder="Description" /></Form.Item>
                  <Form.Item name="instrument_id" rules={[{ required: true }]}>
                    <Input placeholder="Instrument ID" />
                  </Form.Item>
                  <Form.Item name="weight" rules={[{ required: true }]}><Input placeholder="Weight" type="number" /></Form.Item>
                  <Button type="primary" htmlType="submit" loading={portfolioSaving} disabled={!instruments.length}>
                    Add Portfolio
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'Portfolio', dataIndex: 'name' },
                    { title: 'Description', dataIndex: 'description' },
                    {
                      title: 'Positions',
                      dataIndex: 'positions',
                      width: 120,
                      render: (positions: Portfolio['positions']) => positions.length,
                    },
                    {
                      title: 'First Holding',
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

              <Card title="Market Data Management">
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
                    <Form.Item name="instrument_id" label="Instrument ID" rules={[{ required: true }]}>
                      <Input placeholder="Instrument ID" />
                    </Form.Item>
                    <Form.Item name="frequency" label="Frequency" rules={[{ required: true }]}>
                      <Input placeholder="5m" />
                    </Form.Item>
                    <Form.Item name="source" label="Source" rules={[{ required: true }]}>
                      <Input placeholder="csv" />
                    </Form.Item>
                  </div>
                  <Form.Item name="csv_text" label="CSV Bars" rules={[{ required: true }]}>
                    <Input.TextArea rows={5} />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={marketDataImporting} disabled={!instruments.length}>
                    Import CSV Bars
                  </Button>
                </Form>
                <Form
                  form={publicFetchForm}
                  layout="vertical"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    frequency: '5m',
                    start_date: '2026-01-02 09:30:00',
                    end_date: '2026-01-02 15:00:00',
                    adjust: '',
                  }}
                  onFinish={handleFetchPublicMarketData}
                  className="public-fetch-form"
                >
                  <div className="market-data-grid">
                    <Form.Item name="instrument_id" label="Instrument ID" rules={[{ required: true }]}>
                      <Input placeholder="Instrument ID" />
                    </Form.Item>
                    <Form.Item name="frequency" label="Frequency" rules={[{ required: true }]}>
                      <Input placeholder="5m" />
                    </Form.Item>
                    <Form.Item name="adjust" label="Adjust">
                      <Input placeholder="none / qfq / hfq" />
                    </Form.Item>
                  </div>
                  <div className="market-data-grid">
                    <Form.Item name="start_date" label="Start" rules={[{ required: true }]}>
                      <Input placeholder="2026-01-02 09:30:00" />
                    </Form.Item>
                    <Form.Item name="end_date" label="End" rules={[{ required: true }]}>
                      <Input placeholder="2026-01-02 15:00:00" />
                    </Form.Item>
                    <Form.Item label="Source">
                      <Input value="akshare" disabled />
                    </Form.Item>
                  </div>
                  <Button type="primary" htmlType="submit" loading={publicDataFetching} disabled={!instruments.length}>
                    Fetch Public Bars
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    {
                      title: 'Time',
                      dataIndex: 'timestamp',
                      width: 190,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                    { title: 'Open', dataIndex: 'open', width: 90 },
                    { title: 'High', dataIndex: 'high', width: 90 },
                    { title: 'Low', dataIndex: 'low', width: 90 },
                    { title: 'Close', dataIndex: 'close', width: 90 },
                    { title: 'Volume', dataIndex: 'volume', width: 110 },
                  ]}
                  dataSource={bars.map((bar) => ({ ...bar, key: bar.id }))}
                />
              </Card>

              <Card title="Data Import Tasks">
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'Source', dataIndex: 'source', width: 90 },
                    {
                      title: 'Status',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'succeeded' ? 'green' : status === 'failed' ? 'red' : 'blue'}>{status}</Tag>,
                    },
                    { title: 'Imported', dataIndex: 'rows_imported', width: 100 },
                    { title: 'Updated', dataIndex: 'rows_updated', width: 100 },
                    { title: 'Message', dataIndex: 'message' },
                  ]}
                  dataSource={dataImportTasks.map((task) => ({ ...task, key: task.id }))}
                />
              </Card>

              <Card title="Market Data Schedules">
                <Form
                  form={scheduleForm}
                  layout="vertical"
                  initialValues={{
                    instrument_id: instruments[0]?.id,
                    frequency: '5m',
                    start_date: '2026-01-02 09:30:00',
                    end_date: '2026-01-02 15:00:00',
                    adjust: '',
                    interval_minutes: 60,
                  }}
                  onFinish={handleCreateMarketDataSchedule}
                >
                  <div className="market-data-grid">
                    <Form.Item name="instrument_id" label="Instrument ID" rules={[{ required: true }]}>
                      <Input placeholder="Instrument ID" />
                    </Form.Item>
                    <Form.Item name="frequency" label="Frequency" rules={[{ required: true }]}>
                      <Input placeholder="5m" />
                    </Form.Item>
                    <Form.Item name="interval_minutes" label="Interval Minutes" rules={[{ required: true }]}>
                      <InputNumber min={1} max={1440} />
                    </Form.Item>
                  </div>
                  <div className="market-data-grid">
                    <Form.Item name="start_date" label="Start" rules={[{ required: true }]}>
                      <Input placeholder="2026-01-02 09:30:00" />
                    </Form.Item>
                    <Form.Item name="end_date" label="End" rules={[{ required: true }]}>
                      <Input placeholder="2026-01-02 15:00:00" />
                    </Form.Item>
                    <Form.Item name="adjust" label="Adjust">
                      <Input placeholder="none / qfq / hfq" />
                    </Form.Item>
                  </div>
                  <Button type="primary" htmlType="submit" loading={scheduleSaving} disabled={!instruments.length}>
                    Add Schedule
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: 'Instrument', dataIndex: 'instrument_id', width: 100 },
                    { title: 'Frequency', dataIndex: 'frequency', width: 100 },
                    { title: 'Every', dataIndex: 'interval_minutes', width: 100, render: (value: number) => `${value} min` },
                    {
                      title: 'Status',
                      dataIndex: 'is_active',
                      width: 100,
                      render: (active: boolean) => <Tag color={active ? 'green' : 'default'}>{active ? 'active' : 'disabled'}</Tag>,
                    },
                    { title: 'Last Run', dataIndex: 'last_message' },
                    {
                      title: 'Action',
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
                            Run Now
                          </Button>
                          <Button
                            size="small"
                            onClick={() => handleDisableMarketDataSchedule(scheduleId)}
                            disabled={!schedule.is_active}
                          >
                            Disable
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  dataSource={marketDataSchedules.map((schedule) => ({ ...schedule, key: schedule.id }))}
                />
              </Card>

              <Card title="Strategy Template Management">
                {strategyParameterError ? <Alert type="error" showIcon title={strategyParameterError} className="form-alert" /> : null}
                {strategies[0] ? (
                  <>
                    <Space orientation="vertical" size={4} className="strategy-summary">
                      <Text strong>{strategies[0].display_name}</Text>
                      <Text type="secondary">{strategies[0].description}</Text>
                      <Space wrap>
                        {strategies[0].supported_frequencies.map((frequency) => (
                          <Tag color={frequency === '5m' ? 'blue' : 'default'} key={frequency}>
                            {frequency}
                          </Tag>
                        ))}
                      </Space>
                    </Space>
                    <Form
                      form={strategyParameterForm}
                      layout="vertical"
                      onFinish={handleCreateStrategyParameterSet}
                      className="strategy-parameter-form"
                    >
                      <Form.Item name="name" label="Parameter Set Name" rules={[{ required: true }]}>
                        <Input placeholder="Parameter set name" />
                      </Form.Item>
                      <div className="strategy-parameter-grid">
                        {strategies[0].parameters.map((parameter) => (
                          <Form.Item
                            key={parameter.name}
                            name={parameter.name}
                            label={parameter.label}
                            valuePropName={parameter.type === 'boolean' ? 'checked' : 'value'}
                            extra={parameter.description}
                          >
                            {renderStrategyParameterInput(parameter)}
                          </Form.Item>
                        ))}
                      </div>
                      <Button type="primary" htmlType="submit" loading={strategyParameterSaving}>
                        Save Strategy Config
                      </Button>
                    </Form>
                  </>
                ) : (
                  <Text type="secondary">Loading strategy metadata</Text>
                )}
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'Name', dataIndex: 'name' },
                    { title: 'Strategy', dataIndex: 'strategy_id', width: 150 },
                    {
                      title: 'Grid %',
                      dataIndex: 'parameters',
                      width: 100,
                      render: (parameters: StrategyParameterSet['parameters']) => parameters.grid_percent,
                    },
                    {
                      title: 'MA Filter',
                      dataIndex: 'parameters',
                      width: 110,
                      render: (parameters: StrategyParameterSet['parameters']) => (
                        <Tag color={parameters.enable_ma_filter ? 'green' : 'default'}>
                          {parameters.enable_ma_filter ? 'on' : 'off'}
                        </Tag>
                      ),
                    },
                  ]}
                  dataSource={strategyParameterSets.map((parameterSet) => ({ ...parameterSet, key: parameterSet.id }))}
                />
              </Card>

              <Card title="Backtest Task Management">
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
                  <Form.Item name="instrument_id" rules={[{ required: true }]}>
                    <Input placeholder="Instrument ID" />
                  </Form.Item>
                  <Form.Item name="frequency" rules={[{ required: true }]}>
                    <Input placeholder="5m" />
                  </Form.Item>
                  <Form.Item name="parameter_set_id" rules={[{ required: true }]}>
                    <Input placeholder="Parameter Set ID" />
                  </Form.Item>
                  <Form.Item name="initial_cash" rules={[{ required: true }]}>
                    <InputNumber min={1} placeholder="Initial Cash" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={backtestRunning} disabled={!instruments.length || !strategyParameterSets.length}>
                    Run Backtest
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: 'Strategy', dataIndex: 'strategy_id', width: 150 },
                    {
                      title: 'Status',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'succeeded' ? 'green' : 'red'}>{status}</Tag>,
                    },
                    {
                      title: 'Return',
                      dataIndex: 'metrics',
                      width: 110,
                      render: (metrics: BacktestRun['metrics']) => `${(((metrics.cumulative_return ?? 0) as number) * 100).toFixed(2)}%`,
                    },
                    {
                      title: 'Max DD',
                      dataIndex: 'metrics',
                      width: 110,
                      render: (metrics: BacktestRun['metrics']) => `${(((metrics.max_drawdown ?? 0) as number) * 100).toFixed(2)}%`,
                    },
                    {
                      title: 'Trades',
                      dataIndex: 'metrics',
                      width: 90,
                      render: (metrics: BacktestRun['metrics']) => metrics.trade_count ?? 0,
                    },
                    {
                      title: 'Equity Points',
                      dataIndex: 'result_payload',
                      width: 130,
                      render: (payload: BacktestRun['result_payload']) => payload.equity_curve?.length ?? 0,
                    },
                    {
                      title: 'Review',
                      dataIndex: 'id',
                      width: 100,
                      render: (backtestId: number) => (
                        <Button size="small" onClick={() => setSelectedBacktestId(backtestId)}>
                          Review
                        </Button>
                      ),
                    },
                  ]}
                  dataSource={backtests.map((backtest) => ({
                    ...backtest,
                    key: backtest.id,
                    className: selectedBacktest?.id === backtest.id ? 'selected-row' : '',
                  }))}
                />
              </Card>

              <Card
                title={
                  <Space>
                    <AreaChartOutlined />
                    Backtest Result Review
                  </Space>
                }
              >
                {selectedBacktest ? (
                  <Space orientation="vertical" size={16} className="review-panel">
                    <div className="review-header">
                      <Space wrap>
                        <Tag color="blue">Backtest #{selectedBacktest.id}</Tag>
                        <Tag color={selectedBacktest.status === 'succeeded' ? 'green' : 'red'}>
                          {selectedBacktest.status}
                        </Tag>
                        <Text type="secondary">{selectedBacktest.strategy_id}</Text>
                      </Space>
                      <Button
                        size="small"
                        onClick={() =>
                          snapshotForm.setFieldsValue({
                            backtest_run_id: selectedBacktest.id,
                            title: `Strategy Report #${selectedBacktest.id}`,
                          })
                        }
                      >
                        Use For Snapshot
                      </Button>
                    </div>
                    <div className="review-metrics">
                      <div>
                        <Text type="secondary">Cumulative Return</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.cumulative_return)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">Max Drawdown</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.max_drawdown)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">Win Rate</Text>
                        <strong>{formatPercent(selectedBacktest.metrics.win_rate)}</strong>
                      </div>
                      <div>
                        <Text type="secondary">Trades</Text>
                        <strong>{selectedBacktest.metrics.trade_count ?? 0}</strong>
                      </div>
                      <div>
                        <Text type="secondary">P/L Ratio</Text>
                        <strong>{formatNumber(selectedBacktest.metrics.profit_loss_ratio)}</strong>
                      </div>
                    </div>
                    <div className="review-chart-grid">
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>Equity Curve</Text>
                          <Text type="secondary">{selectedEquity.length} points</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="Equity curve">
                          <polyline points={chartPoints(selectedEquity)} />
                        </svg>
                      </div>
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>Drawdown Curve</Text>
                          <Text type="secondary">{selectedDrawdown.length} points</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="Drawdown curve">
                          <polyline points={chartPoints(selectedDrawdown)} />
                        </svg>
                      </div>
                      <div className="review-chart-panel">
                        <div>
                          <Text strong>Position Curve</Text>
                          <Text type="secondary">{selectedPosition.length} points</Text>
                        </div>
                        <svg viewBox="0 0 360 120" role="img" aria-label="Position curve">
                          <polyline points={chartPoints(selectedPosition)} />
                        </svg>
                      </div>
                    </div>
                    <Table
                      size="small"
                      pagination={{ pageSize: 4 }}
                      columns={[
                        {
                          title: 'Time',
                          dataIndex: 'timestamp',
                          width: 190,
                          render: (value: string) => new Date(value).toLocaleString(),
                        },
                        {
                          title: 'Side',
                          dataIndex: 'side',
                          width: 90,
                          render: (side: string) => <Tag color={side === 'buy' ? 'green' : 'volcano'}>{side}</Tag>,
                        },
                        { title: 'Price', dataIndex: 'price', width: 100, render: (_: unknown, trade: Record<string, unknown>) => tradeValue(trade, 'price') },
                        {
                          title: 'Change %',
                          dataIndex: 'change_percent',
                          width: 120,
                          render: (_: unknown, trade: Record<string, unknown>) => `${tradeValue(trade, 'change_percent')}%`,
                        },
                      ]}
                      dataSource={selectedTrades.map((trade, index) => ({ ...trade, key: index }))}
                    />
                    <Text type="secondary">
                      {selectedBacktest.result_payload.risk_disclosure ??
                        'Backtest results are simulated and do not represent real-money trading.'}
                    </Text>
                  </Space>
                ) : (
                  <Text type="secondary">Run a backtest to review metrics, curves, and trades before publishing.</Text>
                )}
              </Card>

              <Card title="Paper Simulation Management">
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
                    <Input placeholder="Instrument ID" />
                  </Form.Item>
                  <Form.Item name="frequency" rules={[{ required: true }]}>
                    <Input placeholder="5m" />
                  </Form.Item>
                  <Form.Item name="parameter_set_id" rules={[{ required: true }]}>
                    <Input placeholder="Parameter Set ID" />
                  </Form.Item>
                  <Form.Item name="initial_cash" rules={[{ required: true }]}>
                    <InputNumber min={1} placeholder="Initial Cash" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={paperRunStarting} disabled={!instruments.length || !strategyParameterSets.length}>
                    Run Paper Simulation
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: 'Strategy', dataIndex: 'strategy_id', width: 150 },
                    {
                      title: 'Status',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'succeeded' ? 'green' : 'red'}>{status}</Tag>,
                    },
                    {
                      title: 'Latest Equity',
                      dataIndex: 'latest_equity',
                      width: 130,
                      render: (value: number) => value.toFixed(2),
                    },
                    {
                      title: 'Latest Signal',
                      dataIndex: 'config',
                      width: 130,
                      render: (config: PaperRun['config']) => config.metrics?.latest_signal ?? 'hold',
                    },
                    {
                      title: 'Position',
                      dataIndex: 'config',
                      width: 110,
                      render: (config: PaperRun['config']) => `${config.metrics?.latest_position_percent ?? 0}%`,
                    },
                    {
                      title: 'Trades',
                      dataIndex: 'config',
                      width: 90,
                      render: (config: PaperRun['config']) => config.metrics?.trade_count ?? 0,
                    },
                  ]}
                  dataSource={paperRuns.map((paperRun) => ({ ...paperRun, key: paperRun.id }))}
                />
              </Card>

              <Card title="Snapshot Publishing">
                {snapshotError ? <Alert type="error" showIcon title={snapshotError} className="form-alert" /> : null}
                {latestShareToken ? (
                  <Alert
                    type="success"
                    showIcon
                    className="form-alert"
                    title="Client report link generated"
                    description={clientReportUrl(latestShareToken)}
                  />
                ) : null}
                <Form
                  form={snapshotForm}
                  layout="inline"
                  initialValues={{
                    backtest_run_id: backtests[0]?.id,
                    title: backtests[0] ? `Strategy Report #${backtests[0].id}` : 'Rolling T Strategy Report',
                  }}
                  onFinish={handlePublishSnapshot}
                  className="instrument-form"
                >
                  <Form.Item name="backtest_run_id" rules={[{ required: true }]}>
                    <Input placeholder="Backtest Run ID" />
                  </Form.Item>
                  <Form.Item name="title" rules={[{ required: true }]}>
                    <Input placeholder="Snapshot Title" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={snapshotPublishing} disabled={!backtests.length}>
                    Publish Snapshot
                  </Button>
                </Form>
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: 'Title', dataIndex: 'title' },
                    { title: 'Backtest', dataIndex: 'backtest_run_id', width: 100 },
                    { title: 'Version', dataIndex: 'version', width: 90 },
                    {
                      title: 'Status',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => <Tag color={status === 'published' ? 'green' : 'red'}>{status}</Tag>,
                    },
                    {
                      title: 'Action',
                      dataIndex: 'id',
                      width: 120,
                      render: (snapshotId: number, snapshot: PublishedSnapshot) => (
                        <Button
                          size="small"
                          onClick={() => handleRevokeSnapshot(snapshotId)}
                          loading={snapshotRevokingId === snapshotId}
                          disabled={snapshot.status !== 'published'}
                        >
                          Revoke
                        </Button>
                      ),
                    },
                  ]}
                  dataSource={snapshots.map((snapshot) => ({ ...snapshot, key: snapshot.id }))}
                />
              </Card>

              <Card title="Client Share Link Management">
                {shareLinkError ? <Alert type="error" showIcon title={shareLinkError} className="form-alert" /> : null}
                {latestShareToken ? (
                  <Alert
                    type="success"
                    showIcon
                    className="form-alert"
                    title="New share link ready"
                    description={clientReportUrl(latestShareToken)}
                  />
                ) : null}
                <Table
                  size="small"
                  pagination={{ pageSize: 5 }}
                  columns={[
                    { title: 'Link ID', dataIndex: 'id', width: 80 },
                    { title: 'Snapshot', dataIndex: 'snapshot_id', width: 100 },
                    { title: 'Title', dataIndex: 'snapshot_title' },
                    {
                      title: 'Snapshot Status',
                      dataIndex: 'snapshot_status',
                      width: 140,
                      render: (status: string) => <Tag color={status === 'published' ? 'green' : 'red'}>{status}</Tag>,
                    },
                    {
                      title: 'Link Status',
                      dataIndex: 'is_active',
                      width: 120,
                      render: (isActive: boolean) => <Tag color={isActive ? 'green' : 'default'}>{isActive ? 'active' : 'revoked'}</Tag>,
                    },
                    {
                      title: 'Created At',
                      dataIndex: 'created_at',
                      width: 190,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                    {
                      title: 'Action',
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
                            New Link
                          </Button>
                          <Button
                            size="small"
                            onClick={() => handleRevokeShareLink(shareLinkId)}
                            loading={shareLinkRevokingId === shareLinkId}
                            disabled={!shareLink.is_active}
                          >
                            Revoke Link
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  dataSource={shareLinks.map((shareLink) => ({ ...shareLink, key: shareLink.id }))}
                />
              </Card>

              <Card
                title={
                  <Space>
                    <LineChartOutlined />
                    V1 Main Workflow
                  </Space>
                }
              >
                <div className="pipeline">
                  {['Import Data', 'Set Strategy', 'Run Backtest', 'Review Result', 'Publish Snapshot', 'Client Report'].map(
                    (item) => (
                      <div className="pipeline-step" key={item}>
                        <SafetyCertificateOutlined />
                        <span>{item}</span>
                      </div>
                    ),
                  )}
                </div>
              </Card>

              <Card title="Recent Tasks">
                <Table
                  size="small"
                  pagination={false}
                  columns={[
                    { title: 'Task', dataIndex: 'name' },
                    { title: 'Type', dataIndex: 'type', width: 100 },
                    {
                      title: 'Status',
                      dataIndex: 'status',
                      width: 110,
                      render: (status: string) => {
                        const color = status === 'Succeeded' ? 'green' : status === 'Running' ? 'blue' : 'default'
                        return <Tag color={color}>{status}</Tag>
                      },
                    },
                    { title: 'Updated At', dataIndex: 'updatedAt', width: 180 },
                  ]}
                  dataSource={tasks}
                />
              </Card>

              <Card
                title={
                  <Space>
                    <AreaChartOutlined />
                    System Boundaries
                  </Space>
                }
              >
                <div className="boundary-list">
                  <Tag color="blue">No live trading in V1</Tag>
                  <Tag color="purple">No strategy logic in frontend</Tag>
                  <Tag color="cyan">Published snapshots are immutable</Tag>
                  <Tag color="geekblue">vn.py remains a lower-level reference</Tag>
                </div>
              </Card>

              <Card title="Operation Logs">
                <Table
                  size="small"
                  pagination={{ pageSize: 6 }}
                  columns={[
                    { title: 'Action', dataIndex: 'action' },
                    { title: 'Actor', dataIndex: 'actor', width: 110 },
                    { title: 'Target', dataIndex: 'target_type', width: 120 },
                    {
                      title: 'Created At',
                      dataIndex: 'created_at',
                      width: 210,
                      render: (value: string) => new Date(value).toLocaleString(),
                    },
                  ]}
                  dataSource={operationLogs.map((log) => ({ ...log, key: log.id }))}
                />
              </Card>
            </section>
          </Content>
        </Layout>
      </Layout>
      )}
    </ConfigProvider>
  )
}

export default App
