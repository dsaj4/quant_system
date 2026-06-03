const DISPLAY_BASE_URL = import.meta.env.VITE_DISPLAY_BASE_URL ?? 'http://127.0.0.1:5184'

export function clientReportUrl(shareToken: string): string {
  return `${DISPLAY_BASE_URL.replace(/\/$/, '')}/?token=${encodeURIComponent(shareToken)}`
}

export function formatPercent(value: number | null | undefined): string {
  return `${((value ?? 0) * 100).toFixed(2)}%`
}

export function formatNumber(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export function formatDateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : '-'
}

export function formatRatio(value: number | null | undefined): string {
  return value === null || value === undefined ? '-' : `${(value * 100).toFixed(2)}%`
}

export function formatRequestParams(value: Record<string, unknown> | undefined): string {
  if (!value || !Object.keys(value).length) {
    return '-'
  }
  return Object.entries(value)
    .map(([key, entry]) => `${key}: ${String(entry || '-')}`)
    .join(' / ')
}

export function chartPoints(series: Array<{ value: number }> = [], width = 360, height = 120): string {
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

export function tradeValue(trade: Record<string, unknown>, key: string): string {
  const value = trade[key]
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  return typeof value === 'string' ? value : '-'
}
