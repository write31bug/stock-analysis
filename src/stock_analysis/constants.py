"""股票技术分析工具 - 常量定义"""

VERSION = "1.9.0"

# A股上海交易所代码前缀
SH_PREFIXES = ("6", "5", "7", "9")

# 基金类型代码规则
ETF_PREFIXES = ("15", "51", "58")
LOF_PREFIXES = ("16",)
# 自动识别的基金前缀（ETF/LOF，高置信度）
AUTO_FUND_PREFIXES = ETF_PREFIXES + LOF_PREFIXES
# 需要显式 -t fund 指定的基金前缀（开放式基金，与股票代码重叠）
EXPLICIT_FUND_PREFIXES = AUTO_FUND_PREFIXES + ("00", "01", "11", "18")

# 评分阈值
SCORE_STRONG_UP = 75
SCORE_UP = 60
SCORE_SIDEWAYS_LOW = 40
SCORE_DOWN = 25

# 布林带位置阈值
BB_LOWER_THRESHOLD = 0.3
BB_UPPER_THRESHOLD = 0.7

# ASCII 模式映射表
ASCII_REPLACE_MAP: dict = {
    # 趋势
    "强势上涨": "STRONG_UP",
    "上涨趋势": "UP",
    "震荡整理": "SIDEWAYS",
    "下跌趋势": "DOWN",
    "强势下跌": "STRONG_DOWN",
    # 信号
    "金叉": "GOLDEN_CROSS",
    "死叉": "DEATH_CROSS",
    "中性": "NEUTRAL",
    # 布林带
    "突破上轨": "ABOVE_UPPER",
    "突破下轨": "BELOW_LOWER",
    "高位": "HIGH",
    "中位": "MID",
    "低位": "LOW",
    # 缺口
    "向上跳空": "GAP_UP",
    "向下跳空": "GAP_DOWN",
    # 其他
    "数据不足": "INSUFFICIENT_DATA",
    "完美多头": "PERFECT_BULL",
    "完美空头": "PERFECT_BEAR",
    # 建议
    "技术面强势，多指标共振偏多": "STRONG_BULLISH",
    "技术面偏多，短期趋势向上": "BULLISH",
    "技术面中性，方向不明确": "NEUTRAL",
    "技术面偏空，短期趋势向下": "BEARISH",
    "技术面弱势，多指标共振偏空": "STRONG_BEARISH",
    # 摘要常用词
    "现价": "PRICE",
    "净值": "NAV",
    "上涨": "UP",
    "下跌": "DOWN",
    "均线多头排列": "MA_BULL",
    "均线空头排列": "MA_BEAR",
    "超买": "OVERBOUGHT",
    "超卖": "OVERSOLD",
    "评分": "SCORE",
    # KDJ/成交量
    "布林收窄": "BOLL_SQUEEZE",
    "显著放量": "VOL_SURGE",
    "放量": "VOL_UP",
    "显著缩量": "VOL_SHRINK",
    "缩量": "VOL_DOWN",
    "多头": "BULL",
    "空头": "BEAR",
}
