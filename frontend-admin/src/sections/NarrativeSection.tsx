import { Alert, Button, Card, Collapse, DatePicker, Descriptions, Input, Space, Switch, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import type { BacktestRun, NarrativeConfig, NarrativeModule, NarrativePayload, NarrativeRun } from '../api/client'

const { Text, Title } = Typography
const { TextArea } = Input

type NarrativeSectionProps = {
  selectedBacktest: BacktestRun | null
  config: NarrativeConfig | null
  narrative: NarrativeRun | null
  loading: boolean
  actionLoading: boolean
  error: string
  onRefresh: () => void
  onGenerate: (analysisDate: string) => void
  onSaveDraft: (payload: NarrativePayload) => void
  onAcknowledgeDegraded: () => void
  onApprove: () => void
  onWithdraw: () => void
  onRegenerate: (analysisDate: string) => void
}

function isNarrativePayload(payload: NarrativeRun['ai_draft_payload'] | null | undefined): payload is NarrativePayload {
  return Boolean(payload && 'modules' in payload && Array.isArray(payload.modules))
}

function statusColor(status: string | undefined): string {
  if (status === 'reviewed' || status === 'succeeded') {
    return 'green'
  }
  if (status === 'degraded') {
    return 'orange'
  }
  if (status === 'failed') {
    return 'red'
  }
  if (status === 'running' || status === 'pending') {
    return 'processing'
  }
  return 'default'
}

function statusText(status: string | undefined): string {
  const labels: Record<string, string> = {
    pending: '待生成',
    running: '生成中',
    succeeded: '待审核',
    degraded: '降级待确认',
    failed: '失败',
    reviewed: '已审核',
  }
  return status ? labels[status] ?? status : '未生成'
}

function ratingText(value: string | undefined): string {
  const labels: Record<string, string> = {
    positive: '积极',
    neutral: '中性',
    cautious: '谨慎',
  }
  return value ? labels[value] ?? value : '-'
}

function formatJson(value: unknown): string {
  if (!value || (typeof value === 'object' && !Object.keys(value).length)) {
    return '{}'
  }
  return JSON.stringify(value, null, 2)
}

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function updateModule(modules: NarrativeModule[], index: number, patch: Partial<NarrativeModule>): NarrativeModule[] {
  return modules.map((module, moduleIndex) => (moduleIndex === index ? { ...module, ...patch } : module))
}

export function NarrativeSection({
  selectedBacktest,
  config,
  narrative,
  loading,
  actionLoading,
  error,
  onRefresh,
  onGenerate,
  onSaveDraft,
  onAcknowledgeDegraded,
  onApprove,
  onWithdraw,
  onRegenerate,
}: NarrativeSectionProps) {
  const [analysisDate, setAnalysisDate] = useState(dayjs())
  const [draft, setDraft] = useState<NarrativePayload | null>(null)

  useEffect(() => {
    if (isNarrativePayload(narrative?.ai_draft_payload)) {
      setDraft(structuredClone(narrative.ai_draft_payload))
    } else {
      setDraft(null)
    }
  }, [narrative])

  const canGenerate = Boolean(selectedBacktest?.status === 'succeeded' && config?.configured)
  const readOnly = narrative?.status === 'reviewed'
  const canApprove = Boolean(narrative && (narrative.status === 'succeeded' || narrative.status === 'degraded') && draft)
  const needsDegradedAck = narrative?.status === 'degraded' && !narrative.degraded_acknowledged_at
  const currentPayload = draft
  const generationDisabledText = !selectedBacktest
    ? '请选择一条已成功回测。'
    : selectedBacktest.status !== 'succeeded'
      ? '仅成功回测可生成投研叙事。'
      : !config?.configured
        ? 'AI 投研未配置。'
        : ''

  const summaryItems = useMemo(
    () => [
      { label: '配置状态', value: config?.configured ? '已配置' : '未配置' },
      { label: '模型', value: config?.model || '-' },
      { label: '回测', value: selectedBacktest ? `#${selectedBacktest.id}` : '-' },
      { label: '评级', value: ratingText(narrative?.quant_rating) },
      { label: '状态', value: statusText(narrative?.status) },
      { label: '更新时间', value: narrative?.updated_at ? new Date(narrative.updated_at).toLocaleString() : '-' },
    ],
    [config, narrative, selectedBacktest],
  )

  return (
    <Card
      title={
        <Space wrap>
          <span>AI 投研叙事审核</span>
          <Tag color={statusColor(narrative?.status)}>{statusText(narrative?.status)}</Tag>
          {narrative?.provider_conflict ? <Tag color="volcano">结论冲突</Tag> : null}
          {narrative?.is_smoke_test ? <Tag color="purple">测试</Tag> : null}
        </Space>
      }
      extra={
        <Button size="small" onClick={onRefresh} loading={loading}>
          刷新
        </Button>
      }
    >
      <Space orientation="vertical" size={16} className="narrative-workspace">
        {error ? <Alert type="error" showIcon title={error} /> : null}
        {generationDisabledText ? <Alert type="warning" showIcon title={generationDisabledText} /> : null}
        <div className="narrative-toolbar">
          <DatePicker value={analysisDate} onChange={(value) => value && setAnalysisDate(value)} allowClear={false} />
          <Button
            type="primary"
            disabled={!canGenerate}
            loading={actionLoading && !narrative}
            onClick={() => onGenerate(analysisDate.format('YYYY-MM-DD'))}
          >
            生成叙事
          </Button>
          <Button
            disabled={!narrative || !canGenerate}
            loading={actionLoading && Boolean(narrative)}
            onClick={() => onRegenerate(analysisDate.format('YYYY-MM-DD'))}
          >
            重新生成
          </Button>
        </div>
        <Descriptions size="small" bordered column={{ xs: 1, sm: 2, lg: 3 }}>
          {summaryItems.map((item) => (
            <Descriptions.Item label={item.label} key={item.label}>
              {item.value}
            </Descriptions.Item>
          ))}
        </Descriptions>
        {narrative?.status === 'failed' ? <Alert type="error" showIcon title={narrative.error_message} /> : null}
        {narrative?.status === 'degraded' ? (
          <Alert
            type="warning"
            showIcon
            title="降级生成需确认"
            description={(narrative.degraded_reasons || []).join(' / ') || '外部数据源部分不可用。'}
            action={
              <Button size="small" onClick={onAcknowledgeDegraded} disabled={!needsDegradedAck} loading={actionLoading}>
                确认
              </Button>
            }
          />
        ) : null}
        {narrative ? (
          <div className="narrative-audit-grid">
            <div>
              <Text type="secondary">原始建议</Text>
              <strong>{narrative.provider_raw_suggestion || '-'}</strong>
            </div>
            <div>
              <Text type="secondary">覆盖范围</Text>
              <strong>{formatJson(narrative.coverage_summary)}</strong>
            </div>
          </div>
        ) : null}
        {narrative ? (
          <Collapse
            size="small"
            items={[
              {
                key: 'input',
                label: '生成输入摘要',
                children: <pre className="narrative-json">{formatJson(narrative.input_summary)}</pre>,
              },
              {
                key: 'provider',
                label: 'Provider 结构化摘要',
                children: <pre className="narrative-json">{formatJson(narrative.provider_structured_summary)}</pre>,
              },
            ]}
          />
        ) : null}
        {currentPayload ? (
          <div className="narrative-modules">
            <div className="narrative-modules-header">
              <div>
                <Title level={5}>客户展示模块</Title>
                <Text type="secondary">字段为结构化文本，审核后固化进客户快照。</Text>
              </div>
              <Space>
                <Button disabled={readOnly || !draft} onClick={() => draft && onSaveDraft(draft)} loading={actionLoading}>
                  保存草稿
                </Button>
                <Button type="primary" disabled={!canApprove || needsDegradedAck} onClick={onApprove} loading={actionLoading}>
                  审核通过
                </Button>
                <Button disabled={!readOnly} onClick={onWithdraw} loading={actionLoading}>
                  撤回审核
                </Button>
              </Space>
            </div>
            <Collapse
              size="small"
              defaultActiveKey={currentPayload.modules.filter((module) => module.default_expanded).map((module) => module.key)}
              items={currentPayload.modules.map((module, index) => ({
                key: module.key,
                label: (
                  <Space wrap>
                    <span>{module.title}</span>
                    {!module.visible ? <Tag>隐藏</Tag> : null}
                    {module.default_expanded ? <Tag color="blue">默认展开</Tag> : null}
                  </Space>
                ),
                children: (
                  <Space orientation="vertical" size={10} className="narrative-module-editor">
                    <div className="narrative-switch-row">
                      <Space>
                        <Switch
                          checked={module.visible}
                          disabled={readOnly}
                          onChange={(checked) =>
                            setDraft({ ...currentPayload, modules: updateModule(currentPayload.modules, index, { visible: checked }) })
                          }
                        />
                        <Text>客户可见</Text>
                      </Space>
                      <Space>
                        <Switch
                          checked={module.default_expanded}
                          disabled={readOnly}
                          onChange={(checked) =>
                            setDraft({
                              ...currentPayload,
                              modules: updateModule(currentPayload.modules, index, { default_expanded: checked }),
                            })
                          }
                        />
                        <Text>默认展开</Text>
                      </Space>
                    </div>
                    <TextArea
                      value={module.summary}
                      disabled={readOnly}
                      autoSize={{ minRows: 2, maxRows: 4 }}
                      onChange={(event) =>
                        setDraft({
                          ...currentPayload,
                          modules: updateModule(currentPayload.modules, index, { summary: event.target.value }),
                        })
                      }
                    />
                    <TextArea
                      value={module.paragraphs.join('\n')}
                      disabled={readOnly}
                      autoSize={{ minRows: 3, maxRows: 6 }}
                      onChange={(event) =>
                        setDraft({
                          ...currentPayload,
                          modules: updateModule(currentPayload.modules, index, { paragraphs: splitLines(event.target.value) }),
                        })
                      }
                    />
                    <TextArea
                      value={module.bullets.join('\n')}
                      disabled={readOnly}
                      autoSize={{ minRows: 2, maxRows: 5 }}
                      onChange={(event) =>
                        setDraft({
                          ...currentPayload,
                          modules: updateModule(currentPayload.modules, index, { bullets: splitLines(event.target.value) }),
                        })
                      }
                    />
                  </Space>
                ),
              }))}
            />
          </div>
        ) : (
          <Text type="secondary">尚无可编辑叙事草稿。</Text>
        )}
      </Space>
    </Card>
  )
}
