# 面试展示流程指南

> 制造现场异常复盘与改善闭环工作台
> 3-5 分钟展示，面向 IE / 质量 / 数据分析实习岗

---

## 一句话定位

> 这个项目解决的问题是：**制造现场的停机记录到可复盘、可跟踪的改善材料之间，存在大量人工整理工作。我把这个流程标准化、工具化了。**

---

## 展示流程（5 步）

### 第 1 步：问题背景（30 秒）

**开场白：**

> 制造现场每天都有停机事件——设备故障、换线延迟、来料异常。MES / OEE 系统可以记录这些事件，但从原始记录到形成可复盘的 IE 周报或质量 CAPA，中间需要人工整理原因分类、查找历史相似事件、汇总损失统计、写复盘报告。这整个流程目前基本靠 Excel + 人工经验。
>
> 我这个项目就是把这个缝隙流程工具化。

**要点：** 不要做大而全的系统，只解决一个具体的缝隙问题。

---

### 第 2 步：数据与架构（45 秒）

**展示：**

```
两个真实数据源：
├── Maven Manufacturing Downtime（汽水灌装线，38 批次，61 个停机事件）
└── GoMask Manufacturing Downtime Logs（多设备车间，200 个停机事件，131 台设备）
```

**架构一句话：**

> 原始数据通过适配器统一为 ProductionRun / DowntimeEvent / IssueReview 三个 Pydantic 模型，然后下游所有分析都基于这个统一模型，不依赖具体数据格式。

**展示命令：**

```python
# Maven 数据适配
adapter = MavenDowntimeAdapter()
raw = adapter.load_raw('data/raw/maven')
events = adapter.to_downtime_events(raw)
# → 38 批次，61 个停机事件，校验通过
```

```python
# GoMask 数据适配
adapter = GoMaskDowntimeAdapter()
raw = adapter.load_raw('data/raw/gomask')
events = adapter.to_downtime_events(raw)
# → 200 个停机事件，校验通过
```

**强调点：**
- 用 Pydantic 做 schema 校验，不是裸 dict
- Capability-aware：缺字段就不算，不伪造数据

---

### 第 3 步：确定性分析——Pareto + 损失计算（60 秒）

**直接展示真实结果：**

**Maven 汽水灌装线：**
```
产线效率：72.9%    停机比率：27.1%    总停机：1388 min

Top Loss Pareto：
  Machine adjustment      332 min  24.2%  █████████
  Machine failure         254 min  18.5%  ███████
  Inventory shortage      225 min  16.4%  ██████
  Batch change            160 min  11.7%  ████
  Batch coding error      145 min  10.6%  ████
  ──────────────────────────────────────────
  Top 5 累计占比：81.4%
```

**GoMask 多设备车间：**
```
总停机：13677 min    131 台设备    21 个位置

Top Loss Pareto：
  Equipment        7202 min  52.7%  ████████████████████
  Changeover       5323 min  38.9%  ███████████████
  Unknown           820 min   6.0%  ██
  Operator          332 min   2.4%  █
  ──────────────────────────────────────
  Equipment + Changeover = 91.6%

按设备 Top 1：
  MX-9018   4080 min (29.8%)  6 次   ← 单台设备占近三成
```

**面试要点：**
- 所有数值由 Python 确定性计算，不是 LLM 算的
- 有 Pareto 累计比率，可以辅助判断 "改善到哪个点能覆盖大部分损失"
- Capability-aware：Maven 没有产出字段所以不算 OEE，不强填

---

### 第 4 步：LLM 辅助层——标准化 + 相似检索 + 报告（90 秒）

这是展示重点，分三层讲。

#### 4a. 异常备注标准化（DeepSeek v4-flash）

> 原始停机原因写的是 "mechanical"、"electrical" 这种粗分类，我要用 LLM 把它标准化到统一损失类别，同时提取 evidence_text 做可追溯。

**展示实测结果：**

| 原始备注 | 标准类别 | 置信度 | evidence |
|----------|----------|--------|----------|
| Main drive belt slipped off spindle during morning shift. | Equipment | 0.95 | Main drive belt slipped off spindle |
| Voltage drop detected; automatic shutdown triggered. | Equipment | 0.95 | Voltage drop detected |
| Forgot to reset machine after maintenance break. | Operator | 0.95 | Forgot to reset machine after maintenance break |

**强调点：**
- 用 flash 模型，便宜快速
- evidence_text 必须是原文子串，系统自动校验——防止 LLM 编造
- confidence < 0.65 自动标记 needs_review

#### 4b. 相似事件检索（Embedding + Reranker）

> 很多异常是重复发生的。我想查 "电机过热" 的时候，能把历史上所有类似事件找出来。

**展示实测结果：**

```
查询："Motor overheated and caused a shutdown"
  → Top 1: Motor overheated                      (rerank=0.9991)
  → Top 2: Motor overheating, safety cutoff.     (rerank=0.9988)
  → Top 3: Motor overheated due to blocked vent. (rerank=0.9987)
```

**技术方案：**
- Qwen3-Embedding-4B (SiliconFlow API) 生成 1024 维向量
- 余弦相似度粗筛 top 15
- Qwen3-Reranker-4B 精排 top 3
- 两阶段检索，不依赖本地大模型

#### 4c. IE 周报生成（DeepSeek v4-pro）

> 把确定性计算结果 + 异常备注丢给 LLM，生成结构化复盘报告。

**展示生成结果（节选）：**

```markdown
## 2. Top Loss 分析
| 损失类别 | 停机分钟 | 占比 |
|----------|----------|------|
| Machine adjustment | 332.0 | 24.2% |
| Machine failure | 254.0 | 18.5% |
| Inventory shortage | 225.0 | 16.4% |

## 6. 待人工确认事项
1. 确认 Machine adjustment 候选根因：调整程序不标准、换型后首件验证耗时...
2. 确认 Machine failure 候选根因：设备老化、备件不足...
```

**强调点：**
- 数值全部由 Python 计算后传入，LLM 只负责文本整理
- 所有根因写成 "候选根因"，系统自动检测
- 缺 "待人工确认" 标记 → report_checker 自动拦截

---

### 第 5 步：闭环与工程判断（30 秒）

**收尾：**

> 最后强调一下这个项目的工程边界：
>
> 1. LLM 不做数值计算——所有 Pareto、效率、停机比率都是 Python 算的
> 2. LLM 不做根因判定——只输出 "候选根因"，必须人工确认
> 3. 每一步都有校验——evidence 子串校验、report_checker 自动检测
> 4. Capability-aware——缺字段就不算，不伪造数据凑指标
>
> 这个项目的核心价值不在于用了 LLM，而在于**把确定性计算和 AI 辅助的边界画清楚了**。

---

## 面试官可能追问 & 回答

### Q1: 为什么不做自动根因判定？

> 因为制造现场的根因判定需要结合设备状态、工艺参数、人员经验等上下文，这些信息不在停机日志里。LLM 做根因判定会编造不存在的设备编号或人员，这在工程上是不可接受的。所以我只让 LLM 做文本整理，根因留给 IE/质量工程师判断。

### Q2: Embedding 相似检索的准确率如何？

> 在 GoMask 200 条英文数据上，motor/belt/operator 三类查询 Top 3 全部命中同类型事件。两阶段检索（embedding 粗筛 + reranker 精排）比单用 embedding 准确率更高。200 条数据用 API 调用 5.6 秒完成索引构建，不需要本地 GPU。

### Q3: 如果数据没有产出字段怎么算 OEE？

> 不算。系统是 capability-aware 的——缺 good_output 就不出 Quality，缺 ideal_cycle_time 就不出 Performance。Maven 数据没有产出字段，所以 OEE 页面只展示 Availability，不伪造 Quality 和 Performance。这比强行凑一个假 OEE 数值要诚实。

### Q4: 这个项目和 MES / QMS 有什么区别？

> MES 负责记录停机事件，QMS 负责管理 CAPA 流程。但两者之间的 "从记录到复盘材料" 这段整理工作，目前没有系统覆盖。这个项目就做这个缝隙：把原始事件 → 标准化 → 分析 → 报告，连成一个自动化流程。

### Q5: 为什么用 DeepSeek 不用 GPT？

> 成本考虑。DeepSeek v4-flash 做标准化，v4-pro 做报告生成，价格比 GPT-4o 低很多。而且 DeepSeek API 兼容 OpenAI 格式，用 litellm 切换很方便。实际测试下来 flash 模型做英文标准化准确率足够（5/5 全部正确分类，置信度 0.9-0.95）。

---

## 项目技术栈速记

```
Python 3.11 / Pydantic / pandas / Plotly / Streamlit
DeepSeek v4-flash (标准化) + v4-pro (报告)
Qwen3-Embedding-4B (向量检索) + Qwen3-Reranker-4B (重排)
SiliconFlow API / litellm
```

---

## 文件位置速记

```
Maven 数据：data/raw/maven/Manufacturing_Line_Productivity.xlsx
GoMask 数据：data/raw/gomask/manufacturing-machine-downtime-logs.csv
合成备注：  data/sample/synthetic_abnormal_notes.csv
改善项：    data/sample/synthetic_action_items.csv
测试：      tests/ (61 passed, 6 skipped)
启动：      streamlit run src/app/streamlit_app.py
```

---

## 简历写法

### 项目标题

```
制造现场异常复盘与改善闭环工作台 | Python / Streamlit / Pydantic / LLM
```

### 项目描述（三条）

- 设计统一制造异常事件模型，将 Maven Excel 和 GoMask CSV 转换为标准 ProductionRun / DowntimeEvent / IssueReview，支持字段能力检测和 schema 校验。
- 实现停机损失、产线效率、Pareto 累计占比、重复异常统计等确定性分析，避免在缺少产出/良品字段时伪造 OEE。
- 接入 LLM 做异常备注标准化、相似事件检索和 IE/CAPA 报告草稿生成，并加入 evidence 子串校验、候选根因/人工确认检查。
