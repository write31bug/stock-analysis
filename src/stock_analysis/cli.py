"""命令行接口"""

import argparse
import logging
import sys

from .analyzer import StockAnalyzer
from .config import CONFIG_FILE, load_config, save_config
from .constants import VERSION
from .dependencies import AKSHARE_AVAILABLE, REQUESTS_AVAILABLE, YFINANCE_AVAILABLE, check_dependencies
from .output import format_json, print_table, save_output

logger = logging.getLogger("stock_analysis.cli")


def run_check() -> None:
    """运行环境自检，检查依赖安装和数据源连通性"""
    print(f"{'='*50}")
    print(f"  股票技术分析工具 v{VERSION} - 环境自检")
    print(f"{'='*50}")

    # 1. 依赖检查
    print("\n  [依赖检查]")
    deps = [
        ("pandas", "数据处理核心", True),
        ("numpy", "数值计算", True),
        ("requests", "HTTP 请求（A 股/基金数据源）", True),
        ("akshare", "A 股/基金备用数据源", False),
        ("yfinance", "港美股数据源", False),
        ("wcwidth", "终端中文对齐", False),
    ]
    all_required = True
    for mod, desc, required in deps:
        try:
            __import__(mod)
            status = "OK"
        except ImportError:
            status = "MISSING"
            if required:
                all_required = False
        tag = "[必需]" if required else "[可选]"
        print(f"    {tag} {mod:<12s} {desc:<30s} [{status}]")

    if not all_required:
        print("\n  [!] 必需依赖缺失，请安装: pip install pandas numpy requests")
        print(f"{'='*50}")
        return

    # 2. 数据源连通性检查
    print("\n  [数据源检查]")

    # 新浪财经
    sina_ok = False
    if REQUESTS_AVAILABLE:
        try:
            import requests as req

            resp = req.get(
                "https://hq.sinajs.cn/list=sh600519",
                headers={"Referer": "https://finance.sina.com.cn"},
                timeout=5,
            )
            sina_ok = resp.status_code == 200 and len(resp.text) > 10
        except Exception:
            pass
    print(f"    新浪财经 (A 股主源)     [{'OK' if sina_ok else 'FAIL'}]")

    # yfinance
    yf_ok = False
    if YFINANCE_AVAILABLE:
        try:
            import yfinance as yf

            t = yf.Ticker("00700.HK")
            data = t.history(period="5d")
            yf_ok = data is not None and len(data) > 0
        except Exception:
            pass
    print(f"    yfinance (港美股主源)   [{'OK' if yf_ok else 'FAIL'}]")

    # akshare
    ak_ok = False
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak

            df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20260101", end_date="20260110")
            ak_ok = df is not None and len(df) > 0
        except Exception:
            pass
    print(f"    akshare (通用备用源)    [{'OK' if ak_ok else 'FAIL'}]")

    # 3. 总结
    print("\n  [总结]")
    checks = [("新浪财经", sina_ok), ("yfinance", yf_ok), ("akshare", ak_ok)]
    ok_count = sum(1 for _, v in checks if v)
    total = len(checks)
    if ok_count == total:
        print(f"    所有数据源正常 ({ok_count}/{total})")
    elif ok_count >= 1:
        print(f"    部分数据源可用 ({ok_count}/{total})，工具可正常使用（自动切换备用源）")
    else:
        print(f"    所有数据源不可用 ({ok_count}/{total})，请检查网络连接")
        print("    可使用 --test 模式进行离线测试")

    print(f"{'='*50}")


def main(argv=None):
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description=f"股票技术分析工具 v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python stock_analysis.py 600519                       # A股自动识别
  python stock_analysis.py 00700 -m hkstock             # 港股
  python stock_analysis.py AAPL -m usstock              # 美股
  python stock_analysis.py 159934 -t fund               # ETF基金
  python stock_analysis.py 001316 -t fund               # 开放式基金
  python stock_analysis.py -b 600036,600900             # 批量分析
  python stock_analysis.py -b 001316:fund,600036:stock  # 混合类型批量
  python stock_analysis.py --watchlist                   # 使用持仓列表分析
  python stock_analysis.py --add 600519                 # 添加到持仓列表
  python stock_analysis.py --add 159934:fund            # 添加基金到持仓列表
  python stock_analysis.py --remove 600519              # 从持仓列表删除
  python stock_analysis.py --list                       # 查看持仓列表
  python stock_analysis.py 600519 --test                # 离线测试
  python stock_analysis.py 600519 --ascii               # ASCII模式
        """,
    )

    parser.add_argument("stock_code", nargs="?", help="股票/基金代码")
    parser.add_argument(
        "--market",
        "-m",
        default="auto",
        choices=["auto", "ashare", "hkstock", "usstock"],
        help="市场 (默认: auto)",
    )
    parser.add_argument(
        "--type",
        "-t",
        default="stock",
        choices=["stock", "fund"],
        help="资产类型 (默认: stock)",
    )
    parser.add_argument("--days", "-d", type=int, default=60, help="历史数据天数 (默认: 60)")
    parser.add_argument("--batch", "-b", help="批量分析，逗号分隔，支持 code:type 格式")
    parser.add_argument("--pretty", "-p", action="store_true", help="格式化JSON输出（需配合 --json）")
    parser.add_argument("--test", action="store_true", help="离线测试模式（模拟数据）")
    parser.add_argument("--ascii", action="store_true", help="ASCII模式（避免中文乱码，需配合 --json）")
    parser.add_argument("--json", "-j", action="store_true", help="JSON输出（默认为终端表格模式）")
    parser.add_argument("--table", "-T", action="store_true", help="终端表格输出（默认模式，可省略）")
    parser.add_argument("--output", "-o", help="输出到文件（如 result.json）")
    parser.add_argument("--check", action="store_true", help="环境自检（检查依赖和数据源）")
    parser.add_argument("--verbose", action="store_true", help="详细输出（显示 INFO 级别日志）")
    parser.add_argument("--quiet", action="store_true", help="静默模式（仅输出错误）")

    # Watchlist 持仓管理
    wl_group = parser.add_mutually_exclusive_group()
    wl_group.add_argument("--watchlist", "-w", action="store_true", help="使用持仓列表进行分析")
    wl_group.add_argument("--add", metavar="CODE[:TYPE]", help="添加到持仓列表（如 600519 或 159934:fund）")
    wl_group.add_argument("--remove", metavar="CODE", help="从持仓列表删除")
    wl_group.add_argument("--list", action="store_true", help="查看当前持仓列表")

    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s v{VERSION}")

    args = parser.parse_args(argv)

    # ---- Watchlist 持仓管理 ----
    if args.list or args.add or args.remove:
        config = load_config()
        watchlist = config.get("watchlist", [])

        if args.list:
            if not watchlist:
                print("  持仓列表为空。使用 --add CODE[:TYPE] 添加。")
            else:
                print(f"  持仓列表 ({len(watchlist)} 项):")
                for i, item in enumerate(watchlist, 1):
                    if isinstance(item, str) and ":" in item:
                        code, typ = item.rsplit(":", 1)
                        label = "基金" if typ == "fund" else "股票"
                        print(f"    {i:>3d}. {code}  [{label}]")
                    else:
                        print(f"    {i:>3d}. {item}")
            print(f"\n  配置文件: {CONFIG_FILE}")
            return

        if args.add:
            entry = args.add.strip()
            if entry in watchlist:
                print(f"  {entry} 已在持仓列表中", file=sys.stderr)
                return
            watchlist.append(entry)
            config["watchlist"] = watchlist
            save_config(config)
            print(f"  已添加: {entry}  (持仓列表: {len(watchlist)} 项)")
            return

        if args.remove:
            code = args.remove.strip()
            # 支持按纯代码删除（忽略 :type 后缀）
            new_list = []
            removed = False
            for item in watchlist:
                item_code = item.rsplit(":", 1)[0] if isinstance(item, str) and ":" in item else item
                if item_code == code:
                    removed = True
                else:
                    new_list.append(item)
            if not removed:
                print(f"  {code} 不在持仓列表中", file=sys.stderr)
                return
            config["watchlist"] = new_list
            save_config(config)
            print(f"  已删除: {code}  (持仓列表: {len(new_list)} 项)")
            return

    # --watchlist: 从配置文件读取持仓列表，等效于 --batch
    if args.watchlist:
        config = load_config()
        watchlist = config.get("watchlist", [])
        if not watchlist:
            print("  持仓列表为空。使用 --add CODE[:TYPE] 添加。", file=sys.stderr)
            sys.exit(1)
        args.batch = ",".join(watchlist)

    # 从配置文件读取默认参数（仅在用户未显式指定时生效）
    config = load_config()
    defaults = config.get("defaults", {})
    # market
    if args.market == "auto" and defaults.get("market") != "auto":
        args.market = defaults["market"]
    # days
    if args.days == 60 and defaults.get("days") != 60:
        args.days = defaults["days"]
    # type
    if args.type == "stock" and defaults.get("asset_type") != "stock":
        args.type = defaults["asset_type"]

    # 参数校验
    if args.batch and args.stock_code:
        print(f"[WARNING] 同时指定了 stock_code ({args.stock_code}) 和 --batch，stock_code 将被忽略", file=sys.stderr)
    if args.json and args.table:
        print("[WARNING] --json 和 --table 同时指定，将使用 --json 输出", file=sys.stderr)

    # 日志级别控制
    if args.verbose:
        logger.setLevel(logging.INFO)
    elif args.quiet:
        logger.setLevel(logging.ERROR)

    # 环境自检
    if args.check:
        run_check()
        return

    analyzer = StockAnalyzer()

    # 执行分析
    if args.batch:
        codes = [c.strip() for c in args.batch.split(",")]
        result = analyzer.analyze_batch(codes, args.market, test=args.test, asset_type=args.type, days=args.days)
    elif not args.stock_code:
        parser.print_help()
        print("\n[ERROR] 请提供股票/基金代码或使用 --batch", file=sys.stderr)
        sys.exit(1)
    elif args.test:
        result = analyzer.analyze_with_mock_data(args.stock_code, args.market, args.type, days=args.days)
    else:
        result = analyzer.analyze(args.stock_code, args.market, args.type, args.days)

    # 输出结果（默认为终端表格模式）
    use_ascii = args.ascii
    if args.json:
        # JSON 输出模式
        text = format_json(result, pretty=args.pretty, ascii_mode=use_ascii)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
                f.write("\n")
            print(f"结果已保存到: {args.output}", file=sys.stderr)
        else:
            print(text)
    else:
        # 默认表格输出模式
        batch_mode = bool(args.batch)
        print_table(result, batch_mode=batch_mode, ascii_mode=use_ascii)
        if args.output:
            save_output(result, args.output, mode="table", ascii_mode=use_ascii, batch_mode=batch_mode)
