# 前端交互与展示优化 Agent 工作规范

日期：2026-06-02
适用范围：下一位专门优化 `frontend-admin/` 和 `frontend-display/` 的 agent
目标：在不扩大后端业务范围的前提下，提升客户 demo 第一眼观感、操作流畅度和报告可解释性。

## 接手前先读

1. `docs/project-status-demo-plan-2026-06-02.md`
2. `docs/customer-demo-talk-track.md`
3. `docs/demo-runbook.md`
4. `docs/demo-checklist.md`
5. `docs/database-roadmap.md`
6. `docs/stage-records/phase-8-delivery.md`

重点源码：

- `frontend-display/src/App.tsx`
- `frontend-display/src/App.css`
- `frontend-display/src/index.css`
- `frontend-admin/src/App.tsx`
- `frontend-admin/src/App.css`
- `frontend-admin/src/api/client.ts`
- `backend/app/api/snapshots.py`
- `backend/app/api/backtests.py`
- `backend/app/api/paper_runs.py`

## 工作定位

这次不是重新设计产品，也不是扩后端能力。核心任务是把已经打通的量化系统展示得更成熟、更顺、更像可以给客户演示的投研工作台。

```text
已有后端能力
  -> 更清楚的前端信息层级
  -> 更顺的管理端操作路径
  -> 更稳的客户报告展示
  -> 浏览器验证和交付说明
```

## 必须遵守的边界

- 不接真实券商，不做自动下单。
- 不把 paper run 描述成实盘交易。
- 不新增付费数据源调用，不把 JQData/BaoStock 标记为已可用。
- 不在前端、文档或日志里写入真实 token、密钥、私有分享链接。
- 不切换默认数据库，不做破坏性 migration。
- 不修改后端业务规则，除非先写修改草案并获得人工批准。
- 老 snapshot 必须继续可打开，展示端要对缺失字段有兜底。

## 推荐使用的技能

- `frontend-skill-router`：用于前端 UI/UX 优化任务分流。
- `browser:control-in-app-browser`：用于本地页面桌面/移动验证和截图。
- `beginner-code-logic-reader`：用于解释现有页面和 API 如何串联。
- `grill-me`：用于在正式改动前对齐细节和验收标准。

## 工作流

每一轮正式改动都走：

```text
系统分析
  -> 修改草案
  -> 人工批准
  -> 正式修改
  -> 验证
  -> 记录结果
```

若用户直接要求“正式修改”，也要先用一小段详细规范对齐本轮范围，再实施。不要把视觉优化顺手扩成后端重构。

## 优先级

### P0：客户展示端

目标：让客户第一眼看到的是“成熟投研报告”，不是“工程调试页面”。

重点：

- 报告首屏突出策略、标的、区间、数据源、复权、核心结论。
- 负收益和回撤要有专业解释，不回避结果。
- 指标区分主要指标和辅助指标，避免所有数字同权重。
- K 线、权益曲线、回撤、仓位、信号摘要布局清楚。
- 交易明细默认不要撑长整页，可摘要、滚动、折叠或只突出关键交易。
- 风险披露和数据质量要容易看到，但不喧宾夺主。
- token 错误、加载中、无数据、旧快照字段缺失都要有稳定页面状态。

### P1：管理端演示工作流

目标：让演示人员顺着一个自然路径完成操作。

推荐路径：

```text
选择/创建标的
  -> 拉取行情
  -> 查看数据任务和质量
  -> 选择策略参数
  -> 跑回测
  -> 发布快照
  -> 复制分享链接
  -> 查看 paper run 状态
```

重点：

- Tushare 作为默认主源展示，AkShare 作为兜底，JQData/BaoStock 显示为预留或未配置。
- provider、frequency、adjust、任务状态、失败原因要清楚。
- 创建回测、发布快照、复制链接要有明确反馈。
- 长表格需要搜索、筛选、分页或固定滚动区域。
- 操作按钮要区分主动作和次动作，避免演示时找不到下一步。

### P2：跨端可靠性

目标：减少 demo 现场风险。

检查项：

- 桌面宽度、投屏宽度、移动宽度都不重叠、不溢出。
- 图表 canvas 非空，尺寸稳定，切换宽度后仍能正常渲染。
- 控制台没有应用级 error。
- API 失败时页面能显示原因。
- build 通过：`frontend-display` 和 `frontend-admin`。

## 设计约束

- 管理端应偏工作台风格：信息密度高、层级清楚、少装饰。
- 展示端应偏客户报告风格：可读、可信、能解释真实结果。
- 不做营销 landing page，第一屏直接服务实际使用。
- 不把卡片套卡片；页面分区应清晰，不要堆叠装饰容器。
- 不使用大面积单一色系或过度渐变背景。
- 文本不能和图表、按钮、表格重叠。
- 按钮文字要能在移动端容器内放下，必要时换行或缩短。
- 图标优先使用现有依赖：管理端已有 `@ant-design/icons`，不要随意新增图标库。
- 图表继续使用现有 `echarts` 和 `lightweight-charts`，不要无故换库。

## 建议验收

至少执行：

- `cd frontend-display; npm.cmd run build`
- `cd frontend-admin; npm.cmd run build`
- 用浏览器打开当前本地展示端报告，检查桌面和移动宽度。
- 用浏览器打开管理端，检查数据、回测、快照、paper run 关键区域。
- 检查 console error。
- 如改动影响 API 类型，运行后端相关测试或至少说明未运行原因。

## 交付格式

完成后请说明：

- 本轮优化了哪些页面和流程。
- 对客户 demo 第一眼效果有什么帮助。
- 哪些旧快照或失败状态已兼容。
- 验证命令和浏览器检查结果。
- 仍保留哪些展示风险。

不要在最终答复中暴露真实密钥、token 或私有报告链接。
