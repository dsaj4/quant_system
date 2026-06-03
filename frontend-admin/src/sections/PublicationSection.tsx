import type { ReactNode } from 'react'
import { SectionShell } from '../components/SectionShell'

type PublicationSectionProps = {
  narrative: ReactNode
  snapshots: ReactNode
  links: ReactNode
}

export function PublicationSection({ narrative, snapshots, links }: PublicationSectionProps) {
  return (
    <SectionShell
      eyebrow="Publication"
      title="客户报告发布"
      description="快照发布和分享链接合并为一条客户报告流水线，最新 token 只在创建后临时显示。"
    >
      <div className="section-grid">
        {narrative}
        <div className="section-grid two-columns">
          {snapshots}
          {links}
        </div>
      </div>
    </SectionShell>
  )
}
