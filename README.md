# 制造现场异常复盘与改善闭环工作台

**Manufacturing Issue Review & Action Tracking Workbench**

## 项目背景

本项目面向 **IE 工程师 / 生产运营 / 质量工程师**，用于连接 OEE/停机事件/生产异常记录与 IE 改善复盘/质量异常 CAPA 草稿/周会报告。

成熟系统可以记录停机、产量、质量异常，但从"原始事件记录"到"可复盘、可分类、可跟踪、可汇报的改善材料"之间，仍然存在大量人工整理工作。本项目的目标是把这段人工整理流程标准化、工具化。

## 数据源说明

| 数据源 | 来源 | 用途 |
|--------|------|------|
| Maven Manufacturing Downtime | Maven Analytics（真实数据） | 汽水灌装线批次生产 + 停机事件分析 |
| GoMask Manufacturing Downtime Logs | GoMask（真实数据） | 200 条制造设备停机日志，含英文异常描述文本 |
| 合成异常备注 | `data/sample/synthetic_abnormal_notes.csv` | 演示文本标准化、相似检索流程 |
| 合成改善项 | `data/sample/synthetic_action_items.csv` | 演示改善闭环跟踪 |

### Maven 数据结构

原始数据为 Excel 文件（4 个 sheet）：

- **Line productivity** — 38 个批次：Date, Product, Batch, Operator, Start Time, End Time
- **Products** — 产品表：OR-600 (Orange), LE-600 (Lemon lime), CO-600 (Cola), 等
- **Downtime factors** — 12 类停机原因编码（Emergency stop, Batch change, Machine failure, 等）
- **Line downtime** — 每个批次 × 每类原因的停机分钟数（宽表）

### GoMask 数据结构

CSV 文件，200 条停机事件，16 个字段：

- `downtime_id` — 唯一事件 ID
- `machine_id` / `machine_name` — 设备标识（131 台设备，67 种名称）
- `location` — 位置（21 个：Assembly Line A/B/C, Welding Bay, Cutting Room, 等）
- `downtime_start` / `downtime_end` / `duration_minutes` — 停机时间
- `downtime_type` — 5 类停机原因（mechanical, electrical, operator_error, scheduled_maintenance, other）
- `cause_description` — 异常描述文本（**支持 LLM 标准化和相似检索**）
- `resolution_actions` / `parts_replaced` — 处理措施（**支持改善项跟踪**）
- `production_impact` — 影响描述（如 "24 units delayed, 48 min lost"）
- `resolved_by` / `reported_by` — 人员信息

### 两个数据源能力对比

| 能力 | Maven | GoMask |
|------|-------|--------|
| 停机 Pareto 分析 | ✅ | ✅ |
| IE 损失复盘 | ✅ | ✅ |
| 按产品维度分析 | ✅ | ❌ 无产品字段 |
| 按操作员维度分析 | ✅ | ❌ 非标准化 |
| 按设备维度分析 | ❌ 无设备字段 | ✅ |
| 按位置维度分析 | ❌ | ✅ |
| Availability 计算 | ✅ | ❌ 无计划时间 |
| 相似事件检索 | ❌ 无备注文本 | ✅ 有 cause_description |
| 改善措施跟踪 | ❌ | ✅ 有 resolution_actions |
| 完整 OEE | ❌ | ❌ |

### 合成数据说明

> `synthetic_abnormal_notes.csv` 和 `synthetic_action_items.csv` 为 **demo synthetic data**，
> 不是企业真实生产数据，只用于演示异常文本标准化、相似事件检索和报告生成流程。

## API 配置

### LLM：DeepSeek API，双模型策略

| 模型 | 用途 | 调用函数 |
|------|------|---------|
| `deepseek-v4-flash` | 轻量任务：异常备注标准化、关键词分类 | `call_llm_flash()` |
| `deepseek-v4-pro` | 复杂任务：IE 周报、CAPA、5Why 草稿生成 | `call_llm_pro()` |

### Embedding + Reranker：SiliconFlow API

| 模型 | 用途 | 维度 |
|------|------|------|
| `Qwen/Qwen3-Embedding-4B` | 事件文本向量化 | 1024 维 |
| `Qwen/Qwen3-Reranker-4B` | 检索结果精排 | — |

两阶段检索流程：Embedding 余弦相似度粗筛（top 15） → Reranker 精排（top 3/5）

LLM 只处理文本层工作，不参与数值计算：

| 环节 | 谁来做 |
|------|--------|
| 数值计算 | Python（确定性） |
| 异常备注标准化 | DeepSeek v4-flash |
| 相似事件检索 | Qwen3-Embedding-4B + Qwen3-Reranker-4B |
| 报告草稿生成 | DeepSeek v4-pro |
| 最终判断 | **人工确认** |

## 系统架构

```
Maven Manufacturing Downtime (Excel) + GoMask Downtime Logs (CSV)
                ↓
统一制造异常事件模型 (ProductionRun / DowntimeEvent / IssueReview)
                ↓
损失计算与 Pareto 分析 (Python 确定性计算)
                ↓
异常文本标准化 (DeepSeek v4-flash) + 相似事件检索 (Qwen3-Embedding + Reranker)
                ↓
改善项闭环跟踪
                ↓
IE 周报 / 质量 CAPA / 5Why 草稿生成 (DeepSeek v4-pro)
```

## Canonical Data Model

三个核心 Pydantic 模型：

- **ProductionRun** — 生产批次记录（product、operator、时间、停机汇总）
- **DowntimeEvent** — 停机/异常事件记录（原因、停机分钟、批次关联）
- **IssueReview** — 复盘与改善项记录（对策、责任人、状态、复发标记）

详见 `src/models/canonical.py`。

## 如何运行

### 1. 安装依赖

```bash
conda env create -f environment.yml
conda activate mfg-review
```

或使用 pip：

```bash
pip install pandas pydantic pytest python-dotenv pyyaml openpyxl plotly streamlit litellm requests
```

### 2. 配置 API

```bash
cp .env.example .env
# 编辑 .env，填入：
#   LLM_API_KEY — DeepSeek API Key
#   EMBEDDING_API_KEY — SiliconFlow API Key
```

### 3. 数据已就绪

Maven 数据文件位于 `data/raw/maven/Manufacturing_Line_Productivity.xlsx`

### 4. 启动应用

```bash
streamlit run src/app/streamlit_app.py
```

### 5. 运行测试

```bash
pytest
```

## 如何替换成自己的 Excel

1. 准备 Excel 文件（含停机事件数据）
2. 编辑 `data/sample/generic_excel_mapping.yaml`，将列名映射到标准字段
3. 在 Streamlit 应用的「数据源管理」页面选择「通用 Excel」
4. 上传 Excel 和 YAML 映射文件

## 测试与验证

```
61 passed, 6 skipped (skip 为无 EMBEDDING_API_KEY 时的预期行为)
```

测试覆盖：
- Pydantic 模型校验（8 项）
- Maven 适配器（含真实数据端到端测试）（11 项）
- GoMask 适配器（含真实数据端到端测试 + impact 解析）（16 项）
- Kaggle 适配器（4 项）
- OEE 计算（4 项）
- 效率指标（4 项）
- Pareto 累计比率（6 项）
- 报告 checker（8 项）
- 相似事件检索（6 项，需设置 EMBEDDING_API_KEY）

## 项目限制

1. 本项目不是商业级 MES/OEE/QMS 系统。
2. Maven 数据来自汽水灌装线，GoMask 数据来自多设备制造车间，不代表所有精密制造场景。
3. Maven 数据不包含班次(Shift)、产出(Output)、良品(Good Output)字段，不支持完整 OEE。
4. GoMask 数据不包含产品、班次、产出字段，不支持 OEE 和产品维度分析。
5. 合成异常备注和改善项为 demo synthetic data，不是企业真实数据。
6. LLM 输出只能作为复盘草稿，不能作为最终工程结论。
7. 根因和 CAPA 必须由 IE、质量、设备、工艺负责人确认。
