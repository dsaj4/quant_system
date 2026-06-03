import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type StrategySectionProps = {
  editor: ReactNode
}

export function StrategySection({ editor }: StrategySectionProps) {
  return (
    <SectionShell
      eyebrow="Strategy"
      title="策略参数配置"
      description="保留规则型滚动做T/网格策略语义，参数集用于后续回测和模拟运行复用。"
    >
      {editor}
    </SectionShell>
  )
}
