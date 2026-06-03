import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type OverviewSectionProps = {
  keyStatus: ReactNode
  keyData: ReactNode
}

export function OverviewSection({ keyStatus, keyData }: OverviewSectionProps) {
  return (
    <SectionShell
      eyebrow="Overview"
      title="重点状态"
      description="聚焦演示路径里的关键步骤状态和可直接判断进度的核心数据。"
    >
      <div className="section-grid two-columns">
        {keyStatus}
        {keyData}
      </div>
    </SectionShell>
  )
}
