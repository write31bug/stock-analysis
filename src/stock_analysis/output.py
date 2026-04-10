"""输出格式化和文件保存"""

import io
import json
import logging
import sys
from typing import Dict

from .constants import ASCII_REPLACE_MAP

logger = logging.getLogger("stock_analysis.output")


# ============================================================
# 表格输出函数
# ============================================================


def _print_table(result: Dict, batch_mode: bool = False, ascii_mode: bool = False) -> None:
    """以人类可读的表格格式输出分析结果"""
    if batch_mode:
        _print_batch_table(result, ascii_mode=ascii_mode)
    else:
        _print_single_table(result, ascii_mode=ascii_mode)


def _print_single_table(d: Dict, ascii_mode: bool = False) -> None:
    """输出单个分析结果的表格"""
    if "error" in d:
        print(f"  [X] {d.get('stock_info', {}).get('code', '?')}: {d['error']}")
        return

    def _t(text: str) -> str:
        """ASCII 模式下替换中文为英文标签"""
        if not ascii_mode:
            return text
        for cn, en in ASCII_REPLACE_MAP.items():
            text = text.replace(cn, en)
        return text

    si = d["stock_info"]
    ti = d["technical_indicators"]
    an = d["analysis"]
    kl = d["key_levels"]
    W = 60  # 表格内容宽度

    type_label = _t("基金") if si.get("asset_type") == "fund" else _t("股票")
    title_text = f"{si.get('name', si['code'])} ({si['code']})  {type_label}  {si.get('market', '')}"
    print(f"+{'-'*W}+")
    print(f"| {_pad(title_text, W)}|")
    print(f"+{'-'*W}+")

    price = si.get("current_price", 0)
    change = si.get("change_pct", 0)
    direction = "^" if change >= 0 else "v"
    price_text = f"{direction} {price}  ({change:+.2f}%)  {_t('更新')}: {si.get('update_time', '')}"
    print(f"| {_pad(price_text, W)}|")

    print(f"+{'-'*W}+")
    score_text = f"{_t('评分')}: {an['score']}  {_t('趋势')}: {_t(an['trend'])}"
    print(f"| {_pad(score_text, W)}|")
    print(f"| {_pad(_t('建议') + ': ' + _t(an['recommendation']), W)}|")
    print(f"+{'-'*W}+")

    # 技术指标
    ma = ti.get("ma", {})
    macd = ti.get("macd", {})
    rsi = ti.get("rsi", {})
    boll = ti.get("bollinger", {})
    kdj = ti.get("kdj", {})
    atr = ti.get("atr", {})
    vol = ti.get("volume_analysis", {})

    ma_text = f"MA:  5={_f(ma.get('MA5'))}  10={_f(ma.get('MA10'))}  20={_f(ma.get('MA20'))}  60={_f(ma.get('MA60'))}"
    print(f"| {_pad(ma_text, W)}|")
    macd_text = (
        f"MACD: DIF={_f(macd.get('DIF'))} DEA={_f(macd.get('DEA'))} 柱={_f(macd.get('MACD'))} {macd.get('signal', '')}"
    )
    print(f"| {_pad(macd_text, W)}|")
    if macd.get("divergence") and macd["divergence"] != "无":
        div_text = f"       [!] {macd['divergence']}"
        print(f"| {_pad(div_text, W)}|")
    rsi_text = f"RSI:  6={_f(rsi.get('RSI6'))}  12={_f(rsi.get('RSI12'))}  24={_f(rsi.get('RSI24'))}"
    print(f"| {_pad(rsi_text, W)}|")
    kdj_text = f"KDJ:  K={_f(kdj.get('K'))}  D={_f(kdj.get('D'))}  J={_f(kdj.get('J'))}  {kdj.get('signal', '')}"
    print(f"| {_pad(kdj_text, W)}|")
    boll_text = f"BOLL: 上={_f(boll.get('upper'))} 中={_f(boll.get('middle'))} 下={_f(boll.get('lower'))}  {boll.get('position', '')}"
    print(f"| {_pad(boll_text, W)}|")
    if boll.get("squeeze"):
        print(f"| {_pad('       [!] ' + _t('布林带收窄，注意变盘'), W)}|")
    if atr.get("ATR"):
        atr_text = f"ATR:  {atr['ATR']:.2f} ({atr['ATR_percent']:.2f}%)"
        print(f"| {_pad(atr_text, W)}|")
    if vol.get("volume_ratio"):
        vol_text = f"{_t('量比')}: {vol['volume_ratio']}  {_t(vol.get('volume_signal', ''))}"
        print(f"| {_pad(vol_text, W)}|")

    # 支撑压力位
    sup = kl.get("support", [])
    res = kl.get("resistance", [])
    if sup or res:
        print(f"+{'-'*W}+")
        if sup:
            sup_text = ", ".join(str(s) for s in sup[:3])
            print(f"| {_pad(_t('支撑') + ': ' + sup_text, W)}|")
        if res:
            res_text = ", ".join(str(r) for r in res[:3])
            print(f"| {_pad(_t('压力') + ': ' + res_text, W)}|")

    print(f"+{'-'*W}+")
    print(f"| {_pad(_t(an.get('summary', '')), W)}|")
    print(f"+{'-'*W}+")


def _print_batch_table(d: Dict, ascii_mode: bool = False) -> None:
    """输出批量分析结果的汇总表格"""

    def _t(text: str) -> str:
        if not ascii_mode:
            return text
        for cn, en in ASCII_REPLACE_MAP.items():
            text = text.replace(cn, en)
        return text

    results = d.get("results", [])
    summary = d.get("summary", {})

    print(f"\n{'='*80}")
    print(
        f"  {_t('批量分析汇总')}  {_t('总计')}: {summary.get('total', 0)}  {_t('成功')}: {summary.get('valid', 0)}  "
        f"{_t('失败')}: {summary.get('failed_count', 0)}  {_t('平均评分')}: {summary.get('avg_score', 0)}"
    )
    print(f"{'='*80}")

    # 表头
    print(
        f"  {_t('代码'):<8s} {_t('名称'):<14s} {_t('类型'):<4s} {_t('评分'):>4s} {_t('趋势'):<8s} {_t('涨跌'):>7s} {'MACD':<8s} {'KDJ':<6s} {_t('量能'):<8s} {_t('摘要')}"
    )
    print(f"  {'-'*8} {'-'*14} {'-'*4} {'-'*4} {'-'*8} {'-'*7} {'-'*8} {'-'*6} {'-'*8} {'-'*20}")

    for r in results:
        if "error" in r:
            code = r.get("stock_info", {}).get("code", "?")
            print(f"  {code:<8s} [X] {r['error']}")
            continue

        si = r["stock_info"]
        an = r["analysis"]
        ti = r["technical_indicators"]
        macd = ti.get("macd", {})
        kdj = ti.get("kdj", {})
        vol = ti.get("volume_analysis", {})

        name = si.get("name", "")[:12]
        t = _t("基") if si.get("asset_type") == "fund" else _t("股")
        change = f"{si.get('change_pct', 0):+.2f}%"
        macd_sig = _t(macd.get("signal", ""))
        kdj_sig = _t(kdj.get("signal", "")) if kdj.get("K") else ""
        vol_sig = _t(vol.get("volume_signal", "")) if vol.get("volume_ratio") else ""
        summary_text = _t(an.get("summary", ""))[:30]

        print(
            f"  {si['code']:<8s} {name:<14s} {t:<4s} {an['score']:>4d} {_t(an['trend']):<8s} {change:>7s} {macd_sig:<8s} {kdj_sig:<6s} {vol_sig:<8s} {summary_text}"
        )

    if d.get("failed"):
        print(f"\n  {_t('失败列表')}:")
        for f in d["failed"]:
            print(f"    [X] {f.get('code', '?')}: {f.get('error', '')}")

    print(f"{'='*80}")


def _f(val) -> str:
    """格式化数值，None 显示为 --"""
    if val is None:
        return "--"
    return f"{val:.2f}"


def _dw(text: str) -> int:
    """计算字符串的显示宽度（中文字符占 2 列）"""
    try:
        from wcwidth import wcswidth

        w = wcswidth(text)
        return w if w is not None else len(text)
    except ImportError:
        return len(text)


def _pad(text: str, width: int) -> str:
    """将 text 用空格填充到指定显示宽度"""
    return text + " " * max(0, width - _dw(text))


# ============================================================
# 公开接口（供 CLI 和外部调用）
# ============================================================


def print_table(result: Dict, batch_mode: bool = False, ascii_mode: bool = False) -> None:
    """以人类可读的表格格式输出分析结果（公开接口）"""
    _print_table(result, batch_mode=batch_mode, ascii_mode=ascii_mode)


def format_json(result, pretty: bool = False, ascii_mode: bool = False) -> str:
    """将分析结果格式化为 JSON 字符串。

    Args:
        result: 分析结果字典。
        pretty: 是否美化输出（缩进）。
        ascii_mode: 是否将中文替换为英文标签。

    Returns:
        JSON 字符串。
    """
    indent = 2 if pretty else None
    text = json.dumps(result, ensure_ascii=False, indent=indent)

    if ascii_mode:
        for cn, en in ASCII_REPLACE_MAP.items():
            text = text.replace(cn, en)

    return text


def save_output(
    result, filepath: str, mode: str = "table", pretty: bool = False, ascii_mode: bool = False, batch_mode: bool = False
) -> None:
    """将分析结果保存到文件。

    Args:
        result: 分析结果字典。
        filepath: 输出文件路径。
        mode: 输出模式，"table" 为表格文本，"json" 为 JSON 格式。
        pretty: JSON 模式下是否美化输出。
        ascii_mode: 是否将中文替换为英文标签。
        batch_mode: 表格模式下是否为批量分析输出。
    """
    if mode == "json":
        text = format_json(result, pretty=pretty, ascii_mode=ascii_mode)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
    else:
        # 表格模式：捕获 stdout 输出写入文件
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        _print_table(result, batch_mode=batch_mode, ascii_mode=ascii_mode)
        sys.stdout = old_stdout
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())

    print(f"结果已保存到: {filepath}", file=sys.stderr)
