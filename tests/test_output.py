"""output.py 输出格式化模块测试"""

import io
import json
import sys

import pytest

from stock_analysis.analyzer import StockAnalyzer
from stock_analysis.output import (
    _dw,
    _f,
    _pad,
    format_json,
    print_table,
    save_output,
)


@pytest.fixture
def single_result():
    """单只分析的模拟结果"""
    analyzer = StockAnalyzer()
    return analyzer.analyze_with_mock_data("600519")


@pytest.fixture
def batch_result():
    """批量分析的模拟结果"""
    analyzer = StockAnalyzer()
    return analyzer.analyze_batch(["600519", "000001"], test=True)


class TestFormatJson:
    """format_json 函数测试"""

    def test_format_json_normal(self, single_result):
        """正常 JSON 输出"""
        text = format_json(single_result, pretty=False)
        data = json.loads(text)
        assert "stock_info" in data
        assert "analysis" in data

    def test_format_json_pretty(self, single_result):
        """美化 JSON 输出包含缩进"""
        text = format_json(single_result, pretty=True)
        assert "\n" in text
        data = json.loads(text)
        assert data["analysis"]["score"] == single_result["analysis"]["score"]

    def test_format_json_ascii(self, single_result):
        """ASCII 模式替换中文"""
        text = format_json(single_result, pretty=False, ascii_mode=True)
        # 应不包含中文趋势词
        assert "强势上涨" not in text
        assert "震荡整理" not in text
        # 应包含英文标签
        assert "STRONG_UP" in text or "UP" in text or "SIDEWAYS" in text or "DOWN" in text


class TestSaveOutput:
    """save_output 函数测试"""

    def test_save_output_json(self, single_result, tmp_path):
        """保存 JSON 到文件"""
        filepath = tmp_path / "result.json"
        save_output(single_result, str(filepath), mode="json", pretty=True)
        content = filepath.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "stock_info" in data

    def test_save_output_table(self, single_result, tmp_path):
        """保存表格到文件"""
        filepath = tmp_path / "result.txt"
        save_output(single_result, str(filepath), mode="table")
        content = filepath.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_save_output_table_batch(self, batch_result, tmp_path):
        """批量表格模式保存"""
        filepath = tmp_path / "batch.txt"
        save_output(batch_result, str(filepath), mode="table", batch_mode=True)
        content = filepath.read_text(encoding="utf-8")
        assert len(content) > 0


class TestPrintTable:
    """print_table 函数测试"""

    def test_print_table_single(self, single_result):
        """单只分析表格输出不崩溃"""
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_table(single_result, batch_mode=False)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert len(output) > 0

    def test_print_table_batch(self, batch_result):
        """批量分析表格输出不崩溃"""
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_table(batch_result, batch_mode=True)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert len(output) > 0

    def test_print_table_ascii(self, single_result):
        """ASCII 模式表格输出"""
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_table(single_result, batch_mode=False, ascii_mode=True)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        assert len(output) > 0


class TestHelperFunctions:
    """内部辅助函数测试"""

    def test_f_format_value_none(self):
        """_f(None) 返回 --"""
        assert _f(None) == "--"

    def test_f_format_value_number(self):
        """_f(数字) 返回格式化字符串"""
        result = _f(3.14159)
        assert "3.14" in result

    def test_f_format_value_zero(self):
        """_f(0) 返回 0.00"""
        assert _f(0) == "0.00"

    def test_dw_display_width_ascii(self):
        """_dw() ASCII 字符宽度为 1"""
        assert _dw("abc") == 3

    def test_dw_display_width_chinese(self):
        """_dw() 中文字符宽度为 2"""
        width = _dw("中文")
        assert width == 4

    def test_dw_display_width_mixed(self):
        """_dw() 混合字符宽度正确"""
        width = _dw("a中b文c")
        assert width == 7  # 3 ASCII + 4 CJK

    def test_pad_function(self):
        """_pad() 填充到指定显示宽度"""
        result = _pad("ab", 6)
        assert _dw(result) == 6
