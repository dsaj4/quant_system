import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type PaperSectionProps = {
  paper: ReactNode
}

export function PaperSection({ paper }: PaperSectionProps) {
  return (
    <SectionShell
      eyebrow="Paper"
      title="模拟运行记录"
      description="以审计记录口吻展示 paper run 的状态流转、信号、模拟成交和失败原因，不表达实盘交易。"
    >
      {paper}
    </SectionShell>
  )
}
