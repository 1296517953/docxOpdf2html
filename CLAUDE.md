# CLAUDE.md

## 项目概述

htmlGENERATOR —— 把 PDF / DOCX 转换为自包含 HTML 文件（已封存）。
- CLI 入口: `main.py`
- GUI 入口: `gui_app.py`
- 转换器: `converter/` (base → pdf_converter / docx_converter)
- 测试: `test_all.py`

## grill-me 模式

本项目启用 grill-me 模式。以下场景触发：

- 新功能设计 / 实现方案
- 架构决策（选型、分层、模块拆分）
- 重构方案设计
- 非 trivial 的 bug 修复策略
- 性能优化方案
- 接口 / API 设计
- 数据模型设计

触发后：一次一个问题，附带推荐答案，遍历决策树直到关键决策点全部覆盖。
能用代码库回答的问题，探索代码库而非询问用户。

以下情况不触发：
- 日常问答、解释概念、阅读代码、简单编辑
- 单行修改、typo 修复、简单的查询
- 用户明确给出具体指令要求直接执行
