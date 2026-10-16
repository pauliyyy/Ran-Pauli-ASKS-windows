# Synthetic public playbook dispatch fixture

These entries are regression input only. They are never installed as personal memory,
represent no real work records, and do not replace operational playbooks.

---
## 班子会提案

**触发词**：「班子会提案」

测试工作区：projects/科研副主任工作区。使用 workspace proposal。
不触发会议纪要摄入。

---
## 系会汇报

**触发词**：「系会」「系会汇报」

测试工作区：projects/科研副主任工作区/系会汇报。
状态为待汇报、已汇报；使用 workspace_state.py item。
不使用班子会 `proposal` 状态。不触发会议纪要摄入。

---
## 修改摄入后端

**触发词**：「将ingest的后端模型改为agent」「把 ingest 后端模型切换为 api」「将摄入的后端模型设为 agent」「修改摄入后端」

这是普通运行参数设置，不是建设任务。设置 `.env` 的 `INGEST_BACKEND`。

---
## 修改查询后端

**触发词**：「query backend是否也做了同样的处理」「把 query 后端模型切换为 agent」「将查询的后端模型设为 api」「修改查询后端」

这是普通运行参数设置，不是建设任务。设置 `.env` 的 `QUERY_BACKEND`。
private 查询仍受独立查询边界约束。

---
## 智能口试指令

**触发词**：「/oral」「继续口试」

仅测试入口链接：operations/ORAL_EXAM_AGENT.md；oral receive；最终回复。
