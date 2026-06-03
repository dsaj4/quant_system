import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type BacktestSectionProps = {
  runner: ReactNode
  review: ReactNode
}

export function BacktestSection({ runner, review }: BacktestSectionProps) {
  return (
    <SectionShell
      eyebrow="Backtest"
      title="回测与复核"
      description="左侧发起和选择最近回测，右侧复核收益、回撤、信号和交易明细，再进入发布准备。"
    >
      <div className="section-grid review-layout">
        {runner}
        {review}
      </div>
    </SectionShell>
  )
}
