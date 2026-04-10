<p align="center">
  <h1 align="center">Stock Analysis — 股票技术分析系统</h1>
</p>

<p align="center">
  <a href="https://github.com/your-repo/stock-analysis/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/your-repo/stock-analysis/ci.yml?branch=main&style=flat-square" alt="CI">
  </a>
  <a href="https://pypi.org/project/stock-analysis/">
    <img src="https://img.shields.io/badge/version-1.11.0-blue?style=flat-square" alt="Version">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8+-green?style=flat-square" alt="Python">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="License">
  </a>
</p>

<p align="center">
  <b>基于多维度技术指标的股票/基金智能分析工具，支持 CLI 命令行与 Web 可视化界面</b>
</p>

---

## 功能特性

- **CLI 命令行分析** — 快速终端分析，支持表格/JSON 多种输出格式
- **Web 可视化界面** — Vue 3 + FastAPI 前后端分离架构
- **多市场支持** — A 股 / 港股 / 美股 / ETF / 开放式基金
- **9 维度技术指标评分** — 6 主指标 (MA / MACD / RSI / KDJ / BOLL / Volume) + 3 辅指标 (OBV / CCI / WR)
- **K 线图 + 技术指标图表** — 基于 ECharts 的交互式可视化
- **自选股分组管理** — 添加、删除、批量分析、自动分组、Excel 导入
- **持仓数据管理** — Excel 导入持仓、增量更新、盈亏展示
- **价格预警通知** — 自定义预警条件，实时监控
- **历史记录 + 评分趋势** — 追踪分析历史，观察评分变化
- **数据导出 CSV** — 一键导出分析结果
- **定时采集服务** — 可配置间隔自动分析自选股
- **系统日志面板** — 实时查看 WARNING/ERROR 日志
- **安全加固** — API Key 认证、CORS 白名单、请求参数验证、文件上传限制、全局异常处理

## 项目结构

```
stock-analysis/
├── pyproject.toml              # 项目配置与依赖管理
├── start.sh                    # 一键启动脚本（后端 + 前端）
├── .env                        # 环境变量配置
├── config/
│   └── config.example.json     # 配置文件示例
├── docs/                       # 项目文档
├── src/stock_analysis/         # CLI 核心库
│   ├── cli.py                  # 命令行入口 (argparse)
│   ├── analyzer.py             # 分析引擎
│   ├── fetcher.py              # 数据获取（新浪/akshare/yfinance）
│   ├── indicators.py           # 技术指标计算
│   ├── scorer.py               # 多维度评分系统
│   ├── output.py               # 输出格式化（表格/JSON）
│   ├── config.py               # 配置文件管理
│   ├── constants.py            # 常量与评分阈值
│   ├── dependencies.py         # 依赖可用性检查
│   └── support.py              # 支撑压力位识别
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口与路由注册
│   ├── database.py             # 数据库连接（SQLite/MySQL）
│   ├── models.py               # SQLAlchemy 模型
│   ├── schemas.py              # Pydantic 数据模式
│   ├── scheduler.py            # 定时采集调度器
│   ├── log_handler.py          # 数据库日志处理器
│   ├── services/               # 公共服务模块
│   │   ├── analysis_service.py # 分析服务
│   │   ├── auth_service.py     # API Key 认证服务
│   │   └── config_service.py   # 配置管理服务（数据库存储）
│   └── routers/
│       ├── analyze.py          # 分析接口
│       ├── watchlist.py        # 自选股管理接口
│       ├── portfolio.py        # 持仓数据接口
│       ├── history.py          # 历史记录接口
│       ├── alerts.py           # 价格预警接口
│       ├── export.py           # 数据导出接口
│       ├── log.py              # 系统日志接口
│       └── settings.py         # 系统设置接口
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── views/              # 页面组件
│       │   ├── Dashboard.vue   # 仪表盘
│       │   ├── Analysis.vue    # 个股分析
│       │   ├── History.vue     # 历史记录
│       │   └── Alerts.vue      # 价格预警
│       ├── components/         # 通用组件
│       │   ├── CandlestickChart.vue    # K 线图
│       │   ├── IndicatorCharts.vue     # 技术指标图表
│       │   └── SystemLogs.vue          # 系统日志面板
│       ├── stores/             # Pinia 状态管理
│       ├── api/                # API 请求封装
│       ├── utils/              # 工具函数
│       ├── router/             # 路由配置
│       └── types/              # TypeScript 类型定义
└── tests/                      # 测试用例（181 个）
```

## 快速开始

### 环境要求

- **Python** 3.8+
- **Node.js** 18+（仅 Web 界面需要）

### 安装

#### 方式一：仅 CLI 工具

```bash
git clone https://github.com/your-repo/stock-analysis.git
cd stock-analysis
pip install -e ".[full]"
stock-analyze 600519
```

#### 方式二：Web 可视化界面

```bash
git clone https://github.com/your-repo/stock-analysis.git
cd stock-analysis
pip install -e ".[full,web]"
cd frontend && npm install && cd ..
bash start.sh
```

启动后访问：
- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## CLI 使用

### 基本用法

```bash
stock-analyze <代码> [选项]
```

### 常用参数

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `stock_code` | — | 股票/基金代码 | 必填（或使用 `--batch`） |
| `--market` | `-m` | 市场类型：`auto` / `ashare` / `hkstock` / `usstock` | `auto` |
| `--type` | `-t` | 资产类型：`stock` / `fund` | `stock` |
| `--days` | `-d` | 历史数据天数 | `60` |
| `--batch` | `-b` | 批量分析，逗号分隔，支持 `code:type` 格式 | — |
| `--json` | `-j` | JSON 格式输出 | — |
| `--pretty` | `-p` | 格式化 JSON（需配合 `--json`） | — |
| `--table` | `-T` | 终端表格输出（默认模式） | — |
| `--output` | `-o` | 输出到文件（如 `result.json`） | — |
| `--ascii` | — | ASCII 模式，避免中文乱码（需配合 `--json`） | — |
| `--test` | — | 离线测试模式（使用模拟数据） | — |
| `--check` | — | 环境自检（检查依赖和数据源连通性） | — |
| `--watchlist` | `-w` | 使用自选股列表进行分析 | — |
| `--add` | — | 添加到自选股列表（如 `600519` 或 `159934:fund`） | — |
| `--remove` | — | 从自选股列表删除 | — |
| `--list` | — | 查看当前自选股列表 | — |
| `--verbose` | — | 详细输出（显示 INFO 级别日志） | — |
| `--quiet` | — | 静默模式（仅输出错误） | — |
| `--version` | `-v` | 显示版本号 | — |

### 示例

```bash
# A 股自动识别
stock-analyze 600519

# 指定市场 — 港股
stock-analyze 00700 -m hkstock

# 指定市场 — 美股
stock-analyze AAPL -m usstock

# ETF 基金
stock-analyze 159934 -t fund

# 开放式基金
stock-analyze 001316 -t fund

# 批量分析
stock-analyze -b 600036,600900

# 混合类型批量分析
stock-analyze -b 001316:fund,600036:stock

# 使用自选股列表批量分析
stock-analyze --watchlist

# 添加到自选股列表
stock-analyze --add 600519
stock-analyze --add 159934:fund

# 查看自选股列表
stock-analyze --list

# JSON 格式输出（美化）
stock-analyze 600519 --json --pretty

# 输出到文件
stock-analyze 600519 --json --pretty -o result.json

# ASCII 模式（适合无中文支持的终端）
stock-analyze 600519 --json --ascii

# 离线测试模式
stock-analyze 600519 --test

# 环境自检
stock-analyze --check

# 指定历史数据天数
stock-analyze 600519 -d 120
```

## Web 界面

### 页面说明

| 页面 | 路由 | 功能 |
|------|------|------|
| **仪表盘** | `/` | 自选股管理、批量分析、趋势分布总览 |
| **个股分析** | `/analysis/:code` | K 线图、技术指标图表、多维度评分面板 |
| **历史记录** | `/history` | 分析历史列表、评分趋势追踪 |
| **价格预警** | `/alerts` | 预警规则管理、条件检查与通知 |

### API 文档

启动后端服务后，访问以下地址查看交互式 API 文档：

- **Swagger UI**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc

### API 路由概览

| 路由前缀 | 模块 | 说明 |
|----------|------|------|
| `/api/v1/analyze` | `analyze.py` | 实时股票分析（单股/批量） |
| `/api/v1/watchlist` | `watchlist.py` | 自选股增删改查、分组管理（写操作需要API Key） |
| `/api/v1/portfolio` | `portfolio.py` | 持仓数据管理、Excel 导入（写操作需要API Key） |
| `/api/v1/history` | `history.py` | 历史记录查询、评分趋势 |
| `/api/v1/alerts` | `alerts.py` | 价格预警管理（写操作需要API Key） |
| `/api/v1/export` | `export.py` | 数据导出 CSV |
| `/api/v1/logs` | `log.py` | 系统日志查询 |
| `/api/v1/settings` | `settings.py` | 采集间隔配置（需要API Key） |
| `/api/v1/scheduler` | `main.py` | 定时采集状态、手动刷新（需要API Key） |
| `/api/v1/health` | `main.py` | 健康检查 |

### API Key 认证

当设置了 `API_KEY` 环境变量后，所有写操作接口需要在请求头中添加：

```bash
X-API-Key: your-api-key-here
```

未设置 `API_KEY` 时，API Key 认证会被跳过。

## 开发

### 运行测试

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov
```

CI 中要求测试覆盖率不低于 50%，测试在 Python 3.8 ~ 3.12 全版本矩阵下运行。

### 代码质量

**Python 后端：**

```bash
ruff check src/stock_analysis backend/ tests/
black --check src/stock_analysis backend/ tests/
isort --check-only src/stock_analysis backend/ tests/
```

**前端：**

```bash
cd frontend
npm run check    # TypeScript 类型检查 + ESLint + Prettier
npm run lint     # ESLint 检查
npm run format   # Prettier 格式化
```

### Pre-commit Hooks

项目配置了 pre-commit hooks，在提交时自动运行代码检查和格式化：

```bash
pip install pre-commit
pre-commit install
```

包含以下 hooks：
- **ruff** — Python 代码检查与自动修复
- **black** — Python 代码格式化
- **isort** — Python import 排序
- **Prettier** — 前端代码格式化
- **通用检查** — 尾部空白、文件末尾换行、YAML/JSON 语法、大文件检测

### 配置管理

配置系统已从文件迁移到数据库存储，提供更好的可扩展性和多进程安全。

#### 环境变量配置（基础配置）

创建 `.env` 文件并配置以下环境变量：

```bash
# 数据库配置（默认使用 SQLite，可选 MySQL）
# DATABASE_URL="mysql+mysqlconnector://user:password@localhost:3306/stock_analysis"

# CORS 白名单（多个地址用逗号分隔）
CORS_ORIGINS="http://localhost:5173"

# API Key 认证（可选，未设置时跳过认证）
# API_KEY="your-api-key-here"
```

#### 应用配置（数据库存储）

应用配置（自选股列表、默认参数、采集间隔等）现在存储在数据库的 `config` 表中。

**向后兼容性：**
- 首次启动时，系统会自动从旧的 `config/config.json` 文件迁移配置到数据库
- 迁移完成后，旧配置文件将不再被使用

**配置项说明：**

| 配置键 | 说明 | 默认值 |
|--------|------|--------|
| `watchlist` | 自选股列表，支持 "code" 或 "code:type" 格式 | `[]` |
| `defaults.market` | 默认市场：auto / ashare / hkstock / usstock | `auto` |
| `defaults.days` | 默认历史数据天数 | `60` |
| `defaults.asset_type` | 默认资产类型：stock / fund | `stock` |
| `collect_interval` | 定时采集间隔（分钟） | `3` |

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python, FastAPI, SQLAlchemy, pandas, numpy |
| **前端** | Vue 3, TypeScript, Naive UI, ECharts, Pinia |
| **数据源** | 新浪财经, akshare, yfinance, 天天基金 |
| **测试** | pytest, pytest-cov, pytest-mock, FastAPI TestClient |
| **CI** | GitHub Actions (Python 3.8-3.12 + Node.js 20) |
| **代码质量** | ruff, black, isort, ESLint, Prettier, vue-tsc |

## 评分体系

系统采用 **6+3 维度**技术指标评分机制：

### 主指标（权重较高）

| 指标 | 说明 |
|------|------|
| **MA** (均线) | 均线多头/空头排列、金叉/死叉信号 |
| **MACD** | DIF/DEA 交叉、柱状图方向、零轴位置 |
| **RSI** (相对强弱) | 超买/超卖区间、背离信号 |
| **KDJ** (随机指标) | K/D/J 三线交叉、超买超卖 |
| **BOLL** (布林带) | 轨道位置、带宽收窄/扩张 |
| **Volume** (成交量) | 量价配合、放量/缩量判断 |

### 辅指标（补充参考）

| 指标 | 说明 |
|------|------|
| **OBV** (能量潮) | 量能趋势、量价背离 |
| **CCI** (顺势指标) | 趋势强度、异常波动 |
| **WR** (威廉指标) | 超买超卖判断、市场情绪 |

### 综合评级

| 评分区间 | 评级 | 含义 |
|----------|------|------|
| >= 75 | 强势上涨 | 多指标共振偏多 |
| 60 ~ 74 | 上涨趋势 | 技术面偏多，短期趋势向上 |
| 40 ~ 59 | 震荡整理 | 技术面中性，方向不明确 |
| 25 ~ 39 | 下跌趋势 | 技术面偏空，短期趋势向下 |
| < 25 | 强势下跌 | 多指标共振偏空 |

## License

[MIT](LICENSE)
