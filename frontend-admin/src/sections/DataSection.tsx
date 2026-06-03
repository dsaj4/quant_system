import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type DataSectionProps = {
  instruments: ReactNode
  portfolios: ReactNode
  marketData: ReactNode
  importTasks: ReactNode
  schedules: ReactNode
}

export function DataSection({ instruments, portfolios, marketData, importTasks, schedules }: DataSectionProps) {
  return (
    <SectionShell
      eyebrow="Data"
      title="行情数据工作台"
      description="以公开行情拉取为主，CSV 作为离线兜底；标的、组合、质量、任务和计划放在同一条数据证据链里。"
    >
      <div className="section-grid two-columns">
        {instruments}
        {portfolios}
      </div>
      {marketData}
      <div className="section-grid two-columns">
        {importTasks}
        {schedules}
      </div>
    </SectionShell>
  )
}
