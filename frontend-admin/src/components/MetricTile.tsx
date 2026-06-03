import { Space, Typography } from 'antd'
import type { ReactNode } from 'react'

const { Text, Title } = Typography

type MetricTileProps = {
  label: string
  value: ReactNode
  detail?: ReactNode
}

export function MetricTile({ label, value, detail }: MetricTileProps) {
  return (
    <div className="metric-tile">
      <Space orientation="vertical" size={4}>
        <Text type="secondary">{label}</Text>
        <Title level={2}>{value}</Title>
        {detail ? <Text>{detail}</Text> : null}
      </Space>
    </div>
  )
}
