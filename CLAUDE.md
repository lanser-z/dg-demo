# CLAUDE.md — A 公司煤炭数据治理 Demo

## Kernel

**项目身份**：A 公司煤炭数据治理 Demo 环境，模拟 5 个异构系统数据，展示数据治理全流程。

**读文档约定**：不得假设 `docs/*.md` 内容已知；具体任务按需 `Read` 对应文件。
**通用兜底**：业务背景与名词术语看 `docs/Background.md`。

**硬约束**：
- 不得修改 `docs/*.md`，除非用户明确要求
- 不得 commit `data/` 目录
- 禁止 `pip`；包管理仅用 `uv`
- 禁止在内存 < 16GB 环境生成历史数据

## Index

| 我想要…… | 看这个文件 |
|---|---|
| 了解项目业务背景与名词术语 | `docs/Background.md` |
| 理解技术架构、选型理由与分层设计 | `docs/Design.md` |
| 理解 ELT vs ETL 选型分析 | `docs/ELTvsETL.md` |
| 跑通 5 分钟演示流程 | `docs/Demo.md` |
| 安装依赖、部署服务 | `docs/Deps.md` |
| 参考 DataHub 接入实战 | `docs/Module1.md` |
| 排查数据生成 / 质量问题 | `src/dg_simulator/base_generator.py` |
| 调整数据生成器配置 | `src/dg_simulator/config.py` |
| 理解增量生成通用逻辑 | `src/dg_simulator/incremental_base.py` |
| 生成历史数据 | `scripts/generate_historical.py` |
| 生成每日增量数据 | `scripts/generate_incremental.py` |
| 资产可视化（演示用） | `scripts/demo_asset_visualization.py` |
| 元数据接入 DataHub | `src/dg_platform/datahub_client.py` |
| 未列出 | 先问 Claude |
