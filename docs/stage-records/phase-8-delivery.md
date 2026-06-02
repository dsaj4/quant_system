# Phase 8 演示打包与交付治理记录

日期：2026-06-02

阶段：Phase 8 演示打包与交付治理
状态：verified

## 1. 执行范围

本阶段完成 demo 复跑、交付材料和客户讲解口径整理：

- 更新 `docs/demo-runbook.md`，补充根目录启动命令、Alembic 初始化、离线 CSV demo、paper run 验收和演示边界。
- 新增 `docs/demo-checklist.md`，形成演示前后逐项确认清单。
- 新增 `docs/customer-demo-talk-track.md`，整理客户讲解路径、边界和外部审计吸收情况。
- 更新 `docs/project-status-demo-plan-2026-06-02.md`，追加 Phase 0 到 Phase 8 执行后状态。
- 更新长期计划状态表，Phase 8 标记为 verified。

## 2. 修改文件

- `docs/demo-runbook.md`
- `docs/demo-checklist.md`
- `docs/customer-demo-talk-track.md`
- `docs/project-status-demo-plan-2026-06-02.md`
- `docs/plans/2026-06-02-long-term-quant-system-upgrade.md`
- `docs/stage-records/phase-8-delivery.md`

## 3. 完成内容

- runbook 覆盖后端、管理端、展示端启动方式。
- runbook 记录 Tushare 茅台真实数据路径和离线 CSV 兜底路径。
- checklist 覆盖启动、数据、回测报告、paper run、最终验证和客户边界。
- talk track 明确系统是“内部量化工作台 + 客户只读报告”，不是实盘交易或投顾合规系统。
- 外部 JZhu Trading 审计吸收点被整理到客户讲解材料中：TimescaleDB 路线、后端指标、paper run 历史、避免复制宽泛交易终端 UI。

## 4. 验证结果

- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `50 passed`。
- 展示端构建：`cd frontend-display; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 客户报告浏览器复查：报告页包含累计收益、交易明细、风险披露、最新信号摘要；存在 3 个 canvas，K 线 canvas 非空；无应用 console error。
- 管理端浏览器复查：管理端包含回测任务、模拟运行、快照发布；paper run 表含模拟成交、失败原因、状态流转；无 console error。

## 5. 已知说明

- 浏览器中既有报告标签保留了早前像素采样脚本触发的 `getImageData` warning；最终复查无应用 error。
- 文档不保存真实 Tushare token 或分享 token。
- 当前仍不承诺生产 SLA、实盘交易、自动下单或投顾合规能力。

## 6. 停止条件检查

当前未触发停止条件：

- 未要求客户品牌、公司法务或投顾合规口径确认。
- 未制作正式商业合同。
- 未承诺生产 SLA。

## 7. 总结

Phase 0 到 Phase 8 的长期改造目标已完成。当前系统具备可复跑 demo、客户讲解口径、阶段记录、测试矩阵和明确边界。
