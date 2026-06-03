import { Typography } from 'antd'
import type { ReactNode } from 'react'

const { Text, Title } = Typography

type SectionShellProps = {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function SectionShell({ eyebrow, title, description, actions, children }: SectionShellProps) {
  return (
    <section className="section-shell">
      <div className="section-heading">
        <div>
          {eyebrow ? <Text className="section-eyebrow">{eyebrow}</Text> : null}
          <Title level={3}>{title}</Title>
          <Text type="secondary">{description}</Text>
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  )
}
