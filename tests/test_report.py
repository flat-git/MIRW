"""报告生成与 checker 测试。"""

import pytest

from src.reporting.report_checker import (
    check_report,
    _check_metrics_present,
    _check_evidence_present,
    _count_deterministic_phrases,
    _check_confirmation_notice,
)


class TestReportChecker:
    def test_good_report_passes(self):
        """合格的报告应通过检查。"""
        report = """
# IE 改善复盘周报 — 2026-W18

## 1. 本周期生产效率概况
总停机时间：486 min，产线效率：82%。

## 2. Top Loss 分析
1. Equipment: 168 min (34.6%)
2. Material: 92 min (18.9%)

## 3. 重复异常分析
吸嘴堵塞问题反复出现，累计影响 123 分钟。
参考备注：贴片机吸嘴堵塞，抛料率升高，更换吸嘴后恢复。

## 5. 下周复盘重点
建议重点关注设备维护。待人工确认。
"""
        data = {
            "metrics": {"total_downtime_min": 486, "line_efficiency": 0.82},
            "repeated_issues": [
                {"evidence_notes": ["贴片机吸嘴堵塞，抛料率升高，更换吸嘴后恢复。"]}
            ],
        }
        result = check_report(report, data)
        assert result["pass"] is True

    def test_missing_confirmation_fails(self):
        """缺少"待人工确认"标记的报告应不通过。"""
        report = """
总停机时间：486 min。
根本原因已确定为设备老化。
"""
        data = {"metrics": {"total_downtime_min": 486}}
        result = check_report(report, data)
        assert result["contains_human_confirmation_notice"] is False
        assert result["pass"] is False

    def test_deterministic_phrases_detected(self):
        """包含确定性表述的报告应被检测。"""
        report = "根本原因是设备故障，结论是需要更换零件。待人工确认。"
        count = _count_deterministic_phrases(report)
        assert count >= 2

    def test_evidence_check(self):
        """包含原始备注证据的报告应通过。"""
        report = "参考备注：AOI 首件不过，工程师重新调整检测参数"
        data = {
            "repeated_issues": [
                {"evidence_notes": ["AOI 首件不过，工程师重新调整检测参数，等待复判 28 分钟后恢复生产。"]}
            ],
        }
        assert _check_evidence_present(report, data) is True

    def test_metrics_check(self):
        """包含关键数值的报告应通过。"""
        report = "总停机时间 486 分钟"
        data = {"metrics": {"total_downtime_min": 486}}
        assert _check_metrics_present(report, data) is True

    def test_confirmation_notice(self):
        assert _check_confirmation_notice("包含候选根因分析，建议优化") is True
        assert _check_confirmation_notice("确定了根因，不需要进一步调查") is False

    def test_empty_data(self):
        """空数据输入应不会崩溃。"""
        report = "待人工确认的报告。候选原因为设备故障。建议优化。总停机 486 分钟。"
        result = check_report(report, {"metrics": {"total_downtime_min": 486}})
        assert result["pass"] is True

    def test_truly_empty_data(self):
        """完全空数据也不应崩溃。"""
        report = "待人工确认的报告。"
        result = check_report(report, {})
        # 无指标数据但有确认标记
        assert result["contains_human_confirmation_notice"] is True
        assert result["has_required_metrics"] is True  # 无 metrics 则跳过检查
        assert result["has_evidence_notes"] is True  # 无 evidence 则跳过检查
