## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 演示负责人（用户本人） | 镜像已拉取（v1.3.0.1、v1.6.0 都试过），但容器起来后前端"显示不全或出错"；影响演示效果，需要恢复正常 |
| 项目设计者（docs/Step1.md 撰写人） | 之前已经记录了 5 个踩坑并修复，认为基础设施层 100% 完工；当前 yml 与文档有 3 处不一致导致旧 bug 重新出现 |
| 潜在演示受众 | 期望在 DataHub UI 上看到 5 个异构系统、12 张表的资产目录、能在 Browse 路径下钻取 |

**触发场景**：用户启动 `docker compose -f datahub-quickstart.yml up -d` 后，浏览 http://localhost:29002，资产列表/血缘/browse 侧栏加载异常或缺失。

## Ideas

- [x] Idea 1：检查当前 yml 与 `docs/Step1.md` 踩坑记录的一致性，找出回归点
- [x] Idea 2：用 deepwiki / tavily 交叉验证 DataHub 官方对 graph service、quickstart CLI、frontend 依赖链的推荐做法
- [x] Idea 3：评估 Neo4j vs Elasticsearch 作为 graph service 的优劣（结合项目实际数据规模 12 张表/5 边）
- [x] Idea 4：评估官方 `datahub docker quickstart` CLI 与项目当前 `docker compose -f` 方式的关系
- [x] Idea 5：识别可能影响前端 v2 UI 渲染的开关（`THEME_V2_*`、`SHOW_*_REDESIGN`、`LINEAGE_GRAPH_V2`、`SHOW_BROWSE_V2`）
- [ ] Idea 6：评估降级到 DataHub v0.10.x 稳定线的可能性（仅作备选）

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 可维护性、可靠性 | 锁定 3 处 yml 与文档不一致的具体位置（GRAPH_SERVICE_IMPL、frontend depends_on、v2 开关），为修复提供精确靶点 | ✅ 是 |
| 2 | 可信度、可维护性 | 用官方文档和社区报告验证诊断结论，避免基于训练数据猜测；修复方案与上游推荐路径对齐 | ✅ 是 |
| 3 | 性能、可维护性、内存占用 | 确认项目规模（12 数据集、5 血缘边）下 ES 比 Neo4j 更轻量；DataHub 官方对轻量部署**明确推荐** ES；避免引入一个为多跳 Cypher 设计但用不上的容器 | ✅ 是 |
| 4 | 可维护性、工具链一致性 | 确认官方 CLI 是 `wget + docker compose` 的薄包装，可用 `--quickstart-compose-file` 复用项目 yml；现阶段无收益，**保持 `docker compose -f` 不变** | ✅ 是（决策记录） |
| 5 | 可观测性、用户体验 | 识别 v2 重构组件（lineage/browse）对 graph service 的强依赖；graph service 坏时这些组件会渲染失败，表现为"页面不完整" | ✅ 是 |
| 6 | 稳定性 | 退到旧版有破坏性变更风险，且会丢失 v1.6.0 的新能力；当前问题可在 v1.6.0 内修复 | ❌ 否（备选） |

## Plan

### 立即实现

- **Idea 编号**：1 + 2 + 3 + 5 组合方案（修 3 处 yml bug + 切到 ES graph + 跑 RestoreIndices + 上报 12 张表）
- **初步方案**：
  1. 备份当前 `datahub-quickstart.yml` 到 `datahub-quickstart.yml.bak`
  2. 修 yml 三处不一致：
     - GMS 和 system-update 的 `GRAPH_SERVICE_IMPL` 统一为 `elasticsearch`
     - 移除 `neo4j` service（减少容器和卷）
     - frontend-quickstart 增加 `depends_on: datahub-gms-quickstart: service_healthy`
     - 关闭 `LINEAGE_GRAPH_V2`、`SHOW_BROWSE_V2`、`SHOW_NAV_BAR_REDESIGN`（保守起步）
  3. `docker compose -f datahub-quickstart.yml up -d` 启动所有服务，等 healthy
  4. 通过 GMS OpenAPI 触发 `RestoreIndices` job 重建图与搜索索引
  5. 跑 `scripts/direct_es_bulk.py` 上报 12 张表到 OpenSearch
  6. 跑 `scripts/emit_browsepaths.py` 写 browsePath 到 GMS
  7. 跑 `scripts/check_browse.py` 验证 browse 路径正确
  8. 浏览器访问 http://localhost:29002 验证 12 张表可见
- **负责人/角色**：演示负责人（用户本人）执行；Claude 协助
- **预计耗时**：1-1.5 小时
- **关键回滚点**：
  - yml 改动可 `git checkout` 回滚（卷不丢）
  - 容器和卷用 `docker compose -f datahub-quickstart.yml down -v` 整体回滚到干净状态
  - 数据（historical/、incremental/、lakehouse/）完全不动

### 等待观察

- **Idea 编号**：4（官方 CLI 引入）
- **等待原因**：当前 `docker compose -f` 方式工作正常，引入 CLI 无明确收益；保留选项，待多人协作或频繁升级版本时再考虑
- **触发条件**：
  - 需要 `datahub docker nuke` 一键清理
  - 团队规模扩大、需统一部署命令
  - 升级到 v1.7+ 时希望用 `--version` 一键管理

- **Idea 编号**：6（降级到 v0.10.x）
- **等待原因**：当前方案有把握在 v1.6.0 内修复；降级破坏性变更多，仅在 v1.6.0 内方案失败时才考虑
- **触发条件**：
  - v1.6.0 修复尝试连续 2 次失败
  - 上游确认 v1.6.0 有阻塞性 bug

## 变更产出

- **正式 Change Proposal**：`setup-datahub-and-load-data`
  - 范围：修 yml + 切 ES graph + 启动 + 上报数据 + 验证可见
  - 涉及模块：`datahub-quickstart.yml`、`scripts/direct_es_bulk.py`（可能调整端口）、`scripts/emit_browsepaths.py`（可能调整端口）
  - 回滚：yml 改回原状 + `docker compose down -v` 即可，不影响 data/ 目录
  - 不涉及 `data/historical/`、`data/incremental/`、`data/lakehouse/`、`docs/*.md`
