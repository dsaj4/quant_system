import { Tag } from 'antd'
import type { PresetColorType, PresetStatusColorType } from 'antd/es/_util/colors'
import { taskStatusColor, tStatus } from '../utils/labels'

type StatusTagProps = {
  status: string | null | undefined
  color?: PresetColorType | PresetStatusColorType
}

export function StatusTag({ status, color }: StatusTagProps) {
  return <Tag color={color ?? taskStatusColor(status)}>{tStatus(status)}</Tag>
}
