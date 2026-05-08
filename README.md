# 制造现场异常复盘与改善闭环工作台

**Manufacturing Issue Review & Action Tracking Workbench**

## 项目背景

本项目面向 **IE 工程师 / 生产运营 / 质量工程师**，用于连接 OEE/停机事件/生产异常记录与 IE 改善复盘/质量异常 CAPA 草稿/周会报告。

成熟系统可以记录停机、产量、质量异常，但从"原始事件记录"到"可复盘、可分类、可跟踪、可汇报的改善材料"之间，仍然存在大量人工整理工作。本项目的目标是把这段人工整理流程标准化、工具化。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  React + TypeScript + Tailwind (前端)                        │
│  数据源中心 → 损失分析 → 相似检索 → 报告生成 → 改善跟踪     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP /api/*
┌──────────────────────┴──────────────────────────────────────┐
│  FastAPI (后端 API 层)                                       │
│  routers → services → state (内存缓存)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ Python import
┌──────────────────────┴──────────────────────────────────────┐
│  src/ (核心领域逻辑)                                          │
│  adapters / metrics / text / reporting / actions / models    │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│  API 服务                                                     │
│  DeepSeek v4-flash/pro (LLM) + SiliconFlow (Embedding)      │
└─────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 数据导入（含脏数据智能导入）

**内置数据源：**
- Maven Manufacturing Downtime（汽水灌装线，38 批次，61 停机事件）
- GoMask Downtime Logs（多设备车间，200 停机事件，131 台设备）

**智能导入（LLM 辅助，支持任意脏数据）：**
- 上传任意结构的 CSV/Excel（列名不同、含脏值、格式混乱均可）
- LLM 自动识别列名含义（支持中英文混合列名）
- Python 自动清洗脏值（N/A、千分位逗号、单位后缀、混合日期格式）
- 用户确认列映射后导入

支持的脏数据场景：

| 场景 | 示例 | 处理方式 |
|------|------|---------|
| 列名不同 | `停机时长(分钟)` → `downtime_min` | LLM 自动映射 |
| 脏值 | `N/A`, `-`, `无`, `TBD` | Python 正则归一化为 null |
| 千分位逗号 | `1,500` → `1500` | Python 自动处理 |
| 单位后缀 | `80 min` → `80` | Python 正则去除 |
| 混合日期 | `2024/06/04`, `Jun 6 2024` | pandas 多格式解析 |
| 重复行 | 完全重复的行 | 自动去重 |

### 2. 停机损失分析

- 总停机时间、停机比率、产线效率
- Top Loss Pareto（柱状图 + 累计比率折线）
- 按产品/设备/操作员/位置维度分布

### 3. 相似事件检索

- Qwen3-Embedding-4B（1024 维向量）粗筛
- Qwen3-Reranker-4B 精排
- 两阶段检索，输入异常描述即可找到历史相似事件

### 4. 报告生成

- IE 改善复盘周报（DeepSeek v4-pro）
- 质量 CAPA 草稿
- 自动校验：数值引用、证据保留、"候选根因"表述、"待人工确认"标记

### 5. 改善项闭环

- 状态汇总（Open / In Progress / Closed）
- 逾期识别、复发检测
- GoMask 的 resolution_actions 自动派生为改善项

## 数据源能力对比

| 能力 | Maven | GoMask | 智能导入 |
|------|-------|--------|---------|
| 停机 Pareto | ✅ | ✅ | ✅ |
| 相似事件检索 | ❌ 无备注 | ✅ | ✅ 有备注即支持 |
| 改善措施跟踪 | ❌ | ✅ | ❌ |
| 设备维度分析 | ❌ | ✅ | ✅ 有字段即支持 |
| 产品维度分析 | ✅ | ❌ | ✅ 有字段即支持 |
| Availability | ✅ | ❌ | ✅ 有字段即支持 |

## API 配置

### LLM（DeepSeek，双模型）

| 模型 | 用途 |
|------|------|
| `deepseek-v4-flash` | 异常备注标准化、**列名映射** |
| `deepseek-v4-pro` | IE 周报、CAPA、5Why 草稿生成 |

### Embedding + Reranker（SiliconFlow）

| 模型 | 用途 |
|------|------|
| `Qwen/Qwen3-Embedding-4B` | 事件文本向量化（1024 维） |
| `Qwen/Qwen3-Reranker-4B` | 检索结果精排 |

## 如何运行

### 1. 安装依赖

```bash
conda env create -f environment.yml
conda activate mfg-review
```

或使用 pip：

```bash
pip install pandas pydantic pytest python-dotenv pyyaml openpyxl \
            fastapi uvicorn python-multipart \
            litellm requests
```

前端依赖：

```bash
cd frontend && npm install
```

### 2. 配置 API

```bash
cp .env.example .env
# 编辑 .env，填入：
#   LLM_API_KEY — DeepSeek API Key
#   LLM_BASE_URL — DeepSeek API 地址
#   EMBEDDING_API_KEY — SiliconFlow API Key
```

### 3. 数据已就绪

- Maven：`data/raw/maven/Manufacturing_Line_Productivity.xlsx`
- GoMask：`data/raw/gomask/manufacturing-machine-downtime-logs.csv`

### 4. 启动

```bash
# 终端 1：后端
python -m uvicorn backend.app:app --reload

# 终端 2：前端
cd frontend && npm run dev

# 浏览器访问 http://localhost:5173
```

### 5. 运行测试

```bash
pytest
```

## API 端点

### 数据源

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/datasets` | 列出已加载数据集 |
| POST | `/api/datasets/load` | 加载内置数据源 |
| POST | `/api/datasets/analyze` | **智能导入 Step1**：分析文件 → 列画像 + LLM 映射建议 |
| POST | `/api/datasets/import` | **智能导入 Step2**：确认映射 → 清洗 + 导入 |
| POST | `/api/datasets/upload` | 传统上传（YAML 映射） |
| GET | `/api/datasets/{id}` | 数据集详情 + capability |

### 指标

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/datasets/{id}/metrics/summary` | 效率摘要 |
| GET | `/api/datasets/{id}/metrics/pareto` | Top Loss Pareto |
| GET | `/api/datasets/{id}/metrics/downtime?group_by=` | 分组停机 |

### 检索与报告

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/datasets/{id}/search` | 相似事件检索 |
| POST | `/api/datasets/{id}/reports/ie-weekly` | IE 周报生成 |
| POST | `/api/datasets/{id}/reports/capa` | CAPA 草稿生成 |
| GET | `/api/datasets/{id}/actions` | 改善项列表 |
| GET | `/api/datasets/{id}/actions/summary` | 改善项汇总 |

## 测试

```
90 passed, 6 skipped
```

skip 为 embedding 相似检索测试（需设置 `EMBEDDING_API_KEY` + `MIRW_LIVE_EMBEDDING_TESTS=1`）。

测试覆盖：
- Pydantic 模型校验（8 项）
- Maven 适配器（11 项，含真实数据端到端）
- GoMask 适配器（16 项，含真实数据端到端）
- Kaggle 适配器（4 项）
- OEE 计算（4 项）| 效率指标（4 项）| Pareto（6 项）
- 报告 checker（8 项）
- 相似事件检索（6 项）
- **数据画像（14 项）**| **列映射+清洗（12 项）**
- 后端 API（4 项）

## 项目限制

1. 本项目不是商业级 MES/OEE/QMS 系统。
2. Maven 数据来自汽水灌装线，GoMask 数据来自多设备制造车间，不代表所有精密制造场景。
3. 合成异常备注和改善项为 demo synthetic data，不是企业真实数据。
4. LLM 输出只能作为复盘草稿，不能作为最终工程结论。
5. 根因和 CAPA 必须由 IE、质量、设备、工艺负责人确认。
6. 脏数据导入的 LLM 映射建议需要用户确认，系统不会自动执行。
