## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 模块八文档（文档作者） | Phase 1 手工直写 OpenSearch 模式存在四个核心痛点：① 新表需人工跑 `emit_browsepaths.py` 注册；② 源数据更新后 DataHub UI 不自动刷新；③ `direct_es_bulk.py` 绕过 GMS，OpenSearch 和 MySQL 数据短暂不一致；④ 5 系统 × N 张表，手工模式无法支撑长期运营 |
| 运维工程师 | 当有新增 Parquet 文件时，需要人工介入触发元数据同步，响应时效差，无法做到分钟级自动发现 |
| 数据分析师 | 通过 DataHub UI 查找资产时，偶尔发现元数据与实际数据不一致（ES vs GMS），信任度下降 |
| 模块八文档（架构规划） | Phase 2 需要 Kafka 事件流驱动的自动化同步能力，作为模块九（自动血缘采集）和模块十（定时质量监控）的基础设施 |

## Ideas

- [ ] 想法 1：**datahub-actions Kafka Consumer 配置** — 配置 `datahub-actions.yml`，消费 `MetadataChangeLog_v4` Topic，将变更事件同步至 GMS MySQL 和 OpenSearch，实现分钟级自动同步
- [ ] 想法 2：**Delta-Lake Ingestion Connector** — 配置 `delta-lake` source → `datahub-rest` sink 的 ingestion recipe，实现 Parquet 文件落地后自动被发现和注册
- [ ] 想法 3：**REST API 直连 GMS 模式** — 提供不依赖 Kafka 的备选路径：通过 GMS REST API 写入元数据，适用于开发/测试环境或无 Kafka 集群的场景
- [ ] 想法 4：**datahub-quickstart.yml 完整栈** — 编写包含 GMS + MySQL + Kafka + OpenSearch + datahub-actions 的完整 docker-compose 配置，降低本地演示门槛
- [ ] 想法 5：**module8.ipynb 教学 notebook** — 编写 Phase 2 架构演示 notebook，展示痛点故事、架构解析、Kafka 事件流配置和 REST API 示例代码
- [ ] 想法 6：**增量 CDC 事件验证脚本** — 提供一个小工具脚本，模拟 Parquet 文件更新并验证 Kafka 事件是否正确触发 DataHub UI 刷新

## Value

> ⚠️ **经验证，已排除以下陈旧想法**：
> - `MetadataChangeLog_v4`：已被废弃，datahub-actions 当前消费 `MetadataChangeLog_Versioned_v1` 和 `MetadataChangeLog_Timeseries_v1`（来源：DeepWiki datahub-project/datahub）

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ | 备注 |
|------|----------------|----------|-------------------|------|
| 1（datahub-actions 配置） | 可维护性、可观测性、自动化 | 消除人工触发环节，元数据变更延迟从「小时级人工」降为「分钟级自动」；事件驱动架构可审计、可回放 | ✅ 是 | 需使用正确 topic 名称 `MetadataChangeLog_Versioned_v1`，非 Module8.md 中所写 `MetadataChangeLog_v4` |
| 2（Delta-Lake ingestion） | 可扩展性、自动化 | 新增 Parquet 文件无需人工注册，实现真正的「数据即资产」自助发现 | ✅ 是 | `delta-lake` source + `datahub-rest` sink 已在官方文档中记录（docs.datahub.com/docs/generated/ingestion/sources/delta-lake） |
| 3（REST API 直连模式） | 可维护性、成本 | 为无 Kafka 环境的团队提供等价能力，降低迁移和学习成本；开发/测试时无需启动完整 Kafka 栈 | ✅ 是 | GMS REST API 写入方式已验证可行 |
| 4（datahub-quickstart.yml） | 可维护性、用户体验 | 一行命令启动完整 DataHub 栈，新成员 onboarding 时间从「1-2 天」降为「分钟级」；也是 CI 环境的基础 | ⚠️ 修正 | 官方推荐方式为 `datahub docker quickstart` CLI 命令（非手工编写 yml）；compose 文件地址：`docker/quickstart/docker-compose.quickstart-profile.yml` |
| 5（module8.ipynb notebook） | 可维护性、用户体验 | 沉淀 Phase 2 架构知识，团队成员可交互式学习；文档即测试，确保架构设计与实现一致 | ✅ 是 | |
| 6（CDC 事件验证脚本） | 可观测性、用户体验 | 提供端到端验证能力，快速定位「Parquet 更新 → DataHub UI 刷新」链路故障 | ❌ 否 | 可作为 tasks 实现细节，非独立变更 |

---

## Plan

### 立即实现

- **Idea 编号**：Ideas 1, 2, 3, 5（Idea 4 修正方向）
- **初步方案**：
  - `datahub-actions.yml`：配置 Kafka Consumer，消费 `MetadataChangeLog_Versioned_v1`（已修正，非废弃的 v4），将变更事件同步至 GMS 和 OpenSearch
  - `delta-lake-ingestion.yaml`：参考 Module8.md § 2.2 的 ingestion recipe 结构，填入实际 lakehouse 路径
  - `module8.ipynb`：按 § 3 的教学 notebook 结构，code cell ≤ 15 行，重点展示架构而非跑通 Kafka
  - `datahub-quickstart.yml` 修正：不在本地编写 yml，而是引用 `datahub docker quickstart` 命令，或将 `docker/quickstart/docker-compose.quickstart-profile.yml` 复制到项目中作为参考
  - REST API 示例代码：作为 notebook 中的一个 code cell 存在
- **触发条件**：Module8.md § 5 明确列出这些为 Phase 2 待完成项，属于规划内工作

### 等待观察

- **Idea 编号**：无
- **说明**：所有 ideas 均已在 Module8.md 中明确规划，属于已确认需求，无需等待更多反馈

## 变更产出

基于以上 brainstorming，建议创建 Change Proposal `module8-dh-production-access`，对应 Module8.md § 5 的 Phase 2 待办项。后续 artifact 按 pdca-workflow 推进：proposal → specs → design → tasks。
