## Why

业务分析师和部门负责人需要临时取数做分析，每次都要走 IT 排期（3~5 天等待），各部门用 Excel 自己拼报表导致口径不一致、互相质疑数据准确性。现有 DWD 清洗层解决了数据质量问题，但业务人员仍然无法直接获取聚合结果，必须依赖技术人员写 SQL。本模块通过构建 DWA 汇总宽表，让业务人员可以直接查询预聚合结果，将取数等待时间从「天」级降至「秒」级，同时消除部门间手工 Excel 的口径不一致问题。

> 触发时机：模块四（DWD 清洗层）已交付，DWD 层数据已落 Delta Lake，具备构建 DWA 的前置条件。

---

## What Changes

1. **新增 DWA 层汇总宽表（3 张）**
   - `dwa_sales_daily`：日销售汇总（来源：SAP VBAK）
   - `dwa_tag_alarm`：传感器告警 Top20 排名（来源：PI tags）
   - `dwa_coal_quality`：月度煤质汇总报告（来源：LIMS samples）
   - 所有宽表写入 Delta Lake（`data/lakehouse/dwa/`）

2. **新增教学 notebook**
   - `notebook/module5.ipynb`：5 步骤教学（痛点故事 → 构建宽表 → 3 个即席查询 → 4 场景验证 → 诚实声明）
   - 每个 code cell ≤15 行，调用 `build_dwa_models.py` 中的函数，不内联大段 SQL

3. **新增实施文档**
   - `docs/Module5.md`：实施步骤、故障排查、快速命令汇总

4. **注册 DWA 表到 DataHub**
   - 3 张 DWA 表已在 `scripts/emit_via_rest_emitter.py` 中注册，无需重复操作

---

## Capabilities

### New Capabilities

- `dwa-sales-daily`: 日销售汇总宽表，按 ERDAT 分组聚合订单数/客户数/总金额，支持销售趋势分析
- `dwa-tag-alarm`: 传感器告警汇总宽表，按 tag 分组统计高频告警点位，支持维护优先级决策
- `dwa-coal-quality`: 月度煤质汇总宽表，按矿井×月份聚合灰分/挥发分/硫分/发热量，支持产销定价参考
- `module5-teaching-notebook`: 模块五教学 notebook（`notebook/module5.ipynb`），5 步骤演示 DWA 构建与即席查询
- `module5-documentation`: 模块五实施文档（`docs/Module5.md`），含执行流程、故障排查、快速命令

### Modified Capabilities

（无。现有规范无需求变更。）

---

## Impact

| 受影响项 | 说明 |
|---------|------|
| `scripts/build_dwa_models.py` | 已有实现，补充完整文档字符串和错误处理 |
| `notebook/module5.ipynb` | 新建（基于 `module1.ipynb` ~ `module4.ipynb` 的 notebook 风格） |
| `docs/Module5.md` | 新建（基于 `Module1.md` ~ `Module4.md` 的文档风格） |
| `data/lakehouse/dwa/` | 新增 3 张 Delta Lake 宽表目录 |
| DataHub | 3 张 DWA 表已注册，无需额外操作 |
| 无破坏性变更 | 现有模块 1~4 不受影响 |

**回滚计划**：删除 `notebook/module5.ipynb`、`docs/Module5.md`，清空 `data/lakehouse/dwa/` 下 3 张表目录即可回滚，不影响 ODS/DWD 层数据。
