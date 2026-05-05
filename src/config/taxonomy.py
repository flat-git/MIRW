"""制造现场损失分类体系。"""

# 通用损失类别（用于标准化分类）
STANDARD_LOSS_CATEGORIES = [
    "Equipment",
    "Material",
    "Quality",
    "Changeover",
    "Process",
    "Planning",
    "Operator",
    "Inspection",
    "Unknown",
]

# IE 视角损失类别
IE_LOSS_CATEGORIES = [
    "Equipment Failure",
    "Changeover Delay",
    "Material Shortage",
    "Minor Stop",
    "Speed Loss",
    "Waiting",
    "Operator Delay",
    "Planning Issue",
]

# 质量视角损失类别
QUALITY_LOSS_CATEGORIES = [
    "Defect",
    "Rework",
    "Scrap",
    "Inspection Delay",
    "First Article Failure",
    "Parameter Adjustment",
    "Process Deviation",
    "Customer Complaint",
]

# PCBA / SMT demo 类别
PCBA_SMT_CATEGORIES = [
    "AOI NG",
    "Nozzle Issue",
    "Feeder Issue",
    "Recipe Error",
    "First Article Delay",
    "Solder Defect",
    "Component Mismatch",
    "Test Fixture Issue",
]

# 改善项状态
ACTION_STATUSES = ["Open", "In Progress", "Closed"]

# 问题类型
ISSUE_TYPES = [
    "Equipment",
    "Quality",
    "Process",
    "Material",
    "Planning",
    "Operator",
]
