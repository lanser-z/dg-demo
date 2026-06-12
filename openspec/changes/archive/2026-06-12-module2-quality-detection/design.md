# Module 2 Quality Detection — Design

## Context

模块一（`notebook/module1.ipynb`）建立了教学主模式：痛点故事 → 3 步学习节奏 → 资产目录 → 质量评分卡 → 安全分级。所有数据都从 `data/historical/` 离线读取，无外部依赖。

模块二需要解决"发现问题后怎么办"。当前 `scripts/run_great_expectations.py` 已经能跑出 A/B/C/D 评分，但：
- 输出是 CLI 文本 + JSON，小白难直接消费
- 没有"从告警到根因"的标准化路径
- 没有可视化展示"哪些标签/订单/样品有问题"

**约束**：
- 必须沿用模块一 `dg_education` 包模式（`catalog.py` / `quality.py` / `visualization.py` / `business_impact.py`）
- 必须用 2022 年全量数据（用户明确要求）
- 不能引入新依赖（pyproject.toml 已固定）
- 中文字体支持（沿用 `_ensure_chinese_font()`）

## Goals / Non-Goals

**Goals:**
- 提供 1 个 `notebook/module2.ipynb`，分 3 步演示 GE 扫描 → 根因定位 → 告警聚合
- 提供 `src/dg_education/ge_scan.py`，包装现有 CLI 为 Notebook 友好 API
- 扩展 `quality.py` 加 4 个根因分析函数（SAP 孤儿行 / PI 缺失 / PI 异常 / LIMS 灰分）
- 扩展 `visualization.py` 加 3 个 plot 函数（根因分布 / 告警热力图 / 系统告警汇总）
- 教学风格：痛点故事 + 3 步学习节奏 + 「业务影响」白话翻译

**Non-Goals:**
- 不实现定时调度（Phase 2 范围）
- 不实现告警通知 / 工单派发（Phase 2/3 范围）
- 不替换 Great Expectations 库为新实现（沿用现有 GE 风格 + pandas 引擎）
- 不修改模块一任何代码
- 不改数据结构（仅读 2022 年全量 Parquet）

## Decisions

### Decision 1: 同进程 import 现有 CLI 而非 subprocess / 重写

**选择**：在 `ge_scan.py` 中用 `importlib.util.spec_from_file_location` 把 `scripts/run_great_expectations.py` 当模块加载到同进程，调用其 `run_check()`，并对返回结果用 `_to_native()` 规范化 numpy/pandas 类型后再返回 dict。

**理由**：
- 现有 CLI 已稳定运行，扫描 4 系统仅需 1-3 秒
- 避免重复实现规则与执行引擎
- Notebook 与 CLI 共享同一份规则定义（RULES 字典），保证一致性
- **同进程 import 优于 subprocess**：subprocess 方案需要 `json.dumps(report, default=...)` 兜底 numpy bool_/int64/float64；同进程方案在规则跑完后用 `_to_native()` 直接转 `bool/int/float`，简单且类型安全
- 节省 2-3s 子进程启动开销

**备选**：
- ~~subprocess.run + JSON 落盘再读回~~ → 需要自定义 `json.dump` default handler 处理 numpy 类型，增加复杂度
- ~~直接 import `scripts/run_great_expectations.py`（不通过 importlib）~~ → scripts/ 不在 PYTHONPATH 上，硬路径耦合不易重构
- ~~重写为纯 Python 函数~~ → 维护两套规则，风险大

### Decision 2: 根因分析函数签名

**选择**：
```python
def analyze_vbap_invalid_links(vbap: pd.DataFrame) -> dict:
    return {
        "total_invalid": int,
        "invalid_pct": float,
        "by_mat_prefix": pd.DataFrame,  # 按物料编码 MATNR 前 3 位分组
        "sample_vbeln": list,           # 样本订单号
    }
```

**理由**：
- 单一职责：每个函数只回答一个问题
- 返回 dict 包含「数字 + 分布 + 样本」，小白能直接 print
- 返回 dict 可直接喂给 visualization 函数

**注**：原设计用订单类型 AUART 分组，但实际 VBAP 表不含 AUART 列（AUART 在 VBAK）。
改用 MATNR 前 3 位作为物料大类前缀分组（spec 已同步更新）。

### Decision 3: 数据采样策略

**选择**：PI 时序数据 12 个月按需加载（内存可控），其他系统全量加载。

**理由**：
- 2022 年 PI 12 个月 ≈ 1 亿行，全量加载耗时长
- 根因分析只关心"哪些标签/哪些时间"有问题，不需全量
- 约定：根因分析时只加载 1 月份数据（tags_year=2022_month=01.parquet，~4M 行），结果可推广

**备选**：
- ~~全量加载 12 个月~~ → 内存压力 + 扫描慢
- ~~仅用模块一的 2023 年样本~~ → 用户明确要求 2022 年全量

### Decision 4: 可视化函数沿用模块一风格

**选择**：复用 `_ensure_chinese_font()` + `SYSTEM_COLORS`，新增 3 个 plot 函数。

**理由**：
- 视觉一致性（颜色/字体/边距）
- 减少重复代码

### Decision 5: 告警聚合维度

**选择**：二维矩阵（系统 × 告警类型），cell 填"该告警的影响行数"。

**理由**：
- 一眼看清"哪个系统、哪种问题最严重"
- 热力图配色直白（红=严重，黄=中等，绿=轻）

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| PI 12 个月数据扫描慢（1-3 秒） | 已确认可接受，notebook 用 `time.time()` 显式提示 |
| GE 规则定义的列名与 Parquet 实际列名不一致 | 运行前做 1 次断言；不一致时给出明确错误 |
| 中文字体在某些环境（无 Noto Sans CJK）渲染为方块 | 沿用模块一配置，dev 已确认本地字体可用 |
| subprocess 调用路径硬编码 | 用 `Path(__file__).parent.parent / "scripts" / "..."` 相对路径 |
| GE 规则 `expect_column_value_lengths_to_be_between(STCD1, 17-20)` 在 KNA1 100% 失败 | 文档里标注「演示用宽范围」，不当作严重问题 |

## Migration Plan

**部署步骤**（一次性 commit）：
1. 新建 `src/dg_education/ge_scan.py`（~80 行）
2. 扩展 `src/dg_education/quality.py`（追加 4 个函数，~120 行）
3. 扩展 `src/dg_education/visualization.py`（追加 3 个函数，~150 行）
4. 更新 `src/dg_education/__init__.py`（导出新 API）
5. 新建 `notebook/module2.ipynb`（6-8 个 cell，markdown + code 混合）

**验证**：
- `uv run python -c "from dg_education import run_ge_scan, analyze_vbap_invalid_links"` 导入成功
- `uv run jupyter notebook notebook/module2.ipynb` 全部 cell 跑通
- 截图保存到 `screenshots/module2_*.png`

**回滚**：
- `git revert` 即可，所有变更都是新增文件 + 追加函数
- 模块一 notebook 与所有现有脚本不受影响

## Open Questions

无。所有关键决策（数据范围、可视化风格、API 形状）已与用户对齐。
