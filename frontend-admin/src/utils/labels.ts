export const providerOptions = [
  { label: 'Tushare Pro', value: 'tushare' },
  { label: 'JQData (预留)', value: 'jqdata', disabled: true },
  { label: 'AkShare', value: 'akshare' },
  { label: 'BaoStock (预留)', value: 'baostock', disabled: true },
]

export const frequencyOptions = [
  { label: '日线 1d', value: '1d' },
  { label: '1分钟', value: '1m' },
  { label: '5分钟', value: '5m' },
  { label: '15分钟', value: '15m' },
  { label: '30分钟', value: '30m' },
  { label: '60分钟', value: '60m' },
]

export const adjustOptions = [
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
  'Rolling T / Grid Strategy': '滚动做T / 网格策略',
}

const strategyDescriptionText: Record<string, string> = {
  'Rule-based rolling T strategy for a fixed stock or portfolio. It uses grid thresholds and an optional moving-average filter.':
    '面向固定股票或组合的规则型滚动做T策略，使用网格阈值和可选均线过滤器生成信号。',
}

const parameterLabelText: Record<string, string> = {
  'Grid Percent': '网格触发幅度',
  'Base Position Percent': '底仓比例',
  'Trade Position Percent': '单次交易仓位',
  'Enable MA Filter': '启用均线过滤',
  'MA Window': '均线窗口',
}

const parameterDescriptionText: Record<string, string> = {
  'Price movement percentage that triggers a grid buy/sell signal.': '触发网格买入/卖出信号的价格波动百分比。',
  'Baseline position percentage kept for rolling T operations.': '滚动做T过程中保留的基础仓位比例。',
  'Position percentage used by each grid trade.': '每次网格交易使用的仓位比例。',
  'Enable moving-average trend filter before generating signals.': '生成信号前是否启用均线趋势过滤。',
  'Moving-average window used when the filter is enabled.': '启用均线过滤时使用的均线周期。',
}

const dataMessageText: Record<string, string> = {
  'No bars found for selected instrument and frequency.': '当前标的和周期没有找到K线数据。',
  'Data continuity looks usable for the selected frequency.': '当前周期的数据连续性可用于回测。',
  'Frequency is not mapped to an expected interval; continuity gaps were not evaluated.':
    '当前周期未映射到预期时间间隔，未评估数据缺口。',
  'CSV import succeeded': 'CSV导入成功',
  'akshare is not installed; use CSV import or install akshare for public data fetch':
    '未安装 AkShare；请使用 CSV 导入，或安装 AkShare 后拉取公开行情。',
}

const displayText: Record<string, string> = {
  'Core A-share Basket': '核心A股组合',
  'Fixed demo portfolio for V1 backtests.': '用于V1回测的固定演示组合。',
  'Kweichow Moutai': '贵州茅台',
  'Rolling T / Grid Strategy default': '滚动做T / 网格策略默认参数',
  'Strategy Report #1': '策略展示报告 #1',
  'Client Display Verification Report': '客户展示验证报告',
  'Backtest results are simulated and do not represent real-money trading.':
    '回测结果为模拟结果，不代表真实资金交易表现。',
  stock: '股票',
  user: '用户',
}

export function tStatus(status: string | null | undefined): string {
  return status ? statusText[status] ?? status : '-'
}

export function taskStatusColor(status: string | null | undefined): string {
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

export function tAction(action: string): string {
  return operationActionText[action] ?? action
}

export function tTargetType(targetType: string): string {
  return targetTypeText[targetType] ?? targetType
}

export function tStrategyName(name: string): string {
  return strategyNameText[name] ?? name
}

export function tStrategyDescription(description: string): string {
  return strategyDescriptionText[description] ?? description
}

export function tParameterLabel(label: string): string {
  return parameterLabelText[label] ?? label
}

export function tParameterDescription(description: string): string {
  return parameterDescriptionText[description] ?? description
}

export function tDataMessage(message: string | null | undefined): string {
  if (!message) {
    return '回测前请先检查所选标的的数据完整性。'
  }
  const gapMatch = message.match(/^Detected (\d+) interval gap\(s\) before running backtests\.$/)
  if (gapMatch) {
    return `检测到 ${gapMatch[1]} 个周期缺口，建议回测前先补齐数据。`
  }
  return dataMessageText[message] ?? message
}

export function tDisplayText(value: string | null | undefined): string {
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
