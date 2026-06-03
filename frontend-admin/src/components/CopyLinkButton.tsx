import { CopyOutlined, ExportOutlined } from '@ant-design/icons'
import { Button, Space, Typography, message } from 'antd'
import { clientReportUrl } from '../utils/format'

const { Text } = Typography

type CopyLinkButtonProps = {
  token: string
}

export function CopyLinkButton({ token }: CopyLinkButtonProps) {
  if (!token) {
    return null
  }

  const url = clientReportUrl(token)

  const copy = () => {
    navigator.clipboard
      ?.writeText(url)
      .then(() => message.success('客户报告链接已复制'))
      .catch(() => message.warning('当前浏览器不允许自动复制，请手动复制链接'))
  }

  return (
    <div className="latest-link">
      <Text type="secondary" ellipsis>
        {url}
      </Text>
      <Space>
        <Button size="small" icon={<CopyOutlined />} onClick={copy}>
          复制
        </Button>
        <Button size="small" icon={<ExportOutlined />} href={url} target="_blank" rel="noreferrer">
          打开
        </Button>
      </Space>
    </div>
  )
}
