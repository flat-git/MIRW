"""数据下载辅助脚本。

Maven Manufacturing Downtime 和 Kaggle OEE 数据需要手动下载。
本脚本提供下载指引和目录准备功能。
"""

from pathlib import Path
import shutil

from src.config.settings import settings


MAVEN_KAGGLE_DATASET = "mavenmanufacturing/manufacturing-downtime-data"
KAGGLE_OEE_DATASETS = [
    "paresh2022/oee-and-downtime-data",
    "saurabhbadole/manufacturing-oee-data",
]


def prepare_directories():
    """确保所有数据目录存在。"""
    dirs = [
        settings.data_dir / "raw" / "maven",
        settings.data_dir / "raw" / "kaggle_oee",
        settings.data_dir / "processed",
        settings.data_dir / "sample",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("数据目录已创建。")


def check_data_files() -> dict:
    """检查数据文件是否已就绪。"""
    result = {}

    maven_dir = settings.data_dir / "raw" / "maven"
    maven_files = list(maven_dir.glob("*.csv")) + list(maven_dir.glob("*.xlsx"))
    result["maven"] = {
        "ready": len(maven_files) > 0,
        "files": [f.name for f in maven_files],
    }

    kaggle_dir = settings.data_dir / "raw" / "kaggle_oee"
    kaggle_files = list(kaggle_dir.glob("*.csv")) + list(kaggle_dir.glob("*.xlsx"))
    result["kaggle_oee"] = {
        "ready": len(kaggle_files) > 0,
        "files": [f.name for f in kaggle_files],
    }

    return result


def print_download_instructions():
    """打印数据下载指引。"""
    instructions = """
========================================
数据下载指引
========================================

1. Maven Manufacturing Downtime 数据
   来源: Kaggle - mavenmanufacturing/manufacturing-downtime-data
   下载方式:
     a) 使用 kaggle CLI:
        kaggle datasets download -d mavenmanufacturing/manufacturing-downtime-data
        unzip manufacturing-downtime-data.zip -d data/raw/maven/
     b) 手动下载:
        访问 https://www.kaggle.com/datasets/mavenmanufacturing/manufacturing-downtime-data
        下载后解压到 data/raw/maven/ 目录

2. Kaggle OEE / Downtime 数据
   来源: Kaggle - 可选以下数据集之一
   - paresh2022/oee-and-downtime-data
   - saurabhbadole/manufacturing-oee-data
   下载方式:
     a) 使用 kaggle CLI:
        kaggle datasets download -d paresh2022/oee-and-downtime-data
        unzip oee-and-downtime-data.zip -d data/raw/kaggle_oee/
     b) 手动下载后解压到 data/raw/kaggle_oee/ 目录

3. 合成数据 (已就绪)
   - data/sample/synthetic_abnormal_notes.csv
   - data/sample/synthetic_action_items.csv
   - data/sample/generic_excel_mapping.yaml

========================================
"""
    print(instructions)


if __name__ == "__main__":
    prepare_directories()
    print_download_instructions()
    status = check_data_files()
    print("\n当前数据状态:")
    for source, info in status.items():
        state = "已就绪" if info["ready"] else "未下载"
        print(f"  {source}: {state}")
        if info["files"]:
            for f in info["files"]:
                print(f"    - {f}")
