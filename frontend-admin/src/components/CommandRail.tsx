import { Button, Tooltip } from 'antd'
import type { ReactNode } from 'react'

export type CommandRailItem = {
  key: string
  label: string
  icon: ReactNode
  section: string
}

type CommandRailProps = {
  items: CommandRailItem[]
  activeSection: string
  onSelect: (section: string) => void
}

export function CommandRail({ items, activeSection, onSelect }: CommandRailProps) {
  return (
    <nav className="command-rail" aria-label="演示工作流">
      {items.map((item, index) => (
        <Tooltip title={item.label} key={item.key}>
          <Button
            className={item.section === activeSection ? 'command-step active' : 'command-step'}
            icon={item.icon}
            onClick={() => onSelect(item.section)}
          >
            <span>{index + 1}</span>
            {item.label}
          </Button>
        </Tooltip>
      ))}
    </nav>
  )
}
