import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type AuditSectionProps = {
  logs: ReactNode
  boundaries: ReactNode
}

export function AuditSection({ logs, boundaries }: AuditSectionProps) {
  return (
    <SectionShell
      eyebrow="Audit"
      title="系统审计与边界"
      description="复用现有操作日志和边界说明，不新增健康/schema API 调用。"
    >
      {boundaries}
      {logs}
    </SectionShell>
  )
}
