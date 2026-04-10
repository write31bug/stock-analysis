# 股票技术分析工具 - 方案二（修订版）：Vue 3 Web 可视化

> 基于 stock-analysis v1.8.0 CLI 项目 | Vue 3 + FastAPI 前后端分离
> 日期: 2026-04-09

---

## 一、项目目标

在方案一（CLI 工具）基础上，添加 Vue 3 Web 界面，实现：

- **K 线图 + 技术指标图表**（MA/MACD/RSI/KDJ/布林带/成交量）
- **交互式自选股仪表盘**（评分排名、趋势分布、一键分析）
- **单股深度分析页**（评分详情、支撑压力位、摘要）
- **历史分析记录**（SQLite 存储，可回溯对比）

---

## 二、技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| **前端框架** | Vue 3 + TypeScript | 你熟悉，Composition API |
| **UI 组件库** | Naive UI | 纯 Vue 3，中文友好，表格/表单/卡片组件丰富 |
| **图表库** | ECharts 5 | K 线图原生支持（`candlestick`），中文生态最好 |
| **构建工具** | Vite | Vue 3 标配，HMR 快 |
| **状态管理** | Pinia | Vue 3 官方推荐 |
| **HTTP 客户端** | Axios | 你熟悉 |
| **后端框架** | FastAPI | 异步高性能，自动生成 OpenAPI 文档 |
| **数据库** | SQLite + SQLAlchemy | 轻量，SQLAlchemy 做 ORM |
| **数据源** | 复用 CLI 的 fetcher/indicators/scorer | 零重复开发 |

---

## 三、架构图

```
┌──────────────────────────────────────────────────┐
│                    浏览器                         │
│  ┌────────────────────────────────────────────┐  │
│  │  Vue 3 + Naive UI + ECharts               │  │
│  │  ┌─────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │ 仪表盘   │ │ 个股分析  │ │ 历史记录   │  │  │
│  │  └─────────┘ └──────────┘ └────────────┘  │  │
│  │         Pinia Store (状态管理)              │  │
│  └──────────────────┬─────────────────────────┘  │
│                     │ Axios                      │
├─────────────────────┼────────────────────────────┤
│                     ▼                            │
│  ┌────────────────────────────────────────────┐  │
│  │  FastAPI 后端                              │  │
│  │  /api/analyze/{code}      单股分析         │  │
│  │  /api/batch                批量分析         │  │
│  │  /api/watchlist            自选股 CRUD      │  │
│  │  /api/history              历史记录 CRUD    │  │
│  │  /api/score-trend/{code}   评分趋势         │  │
│  └──────────────────┬─────────────────────────┘  │
│                     │                            │
│  ┌──────────────────┼─────────────────────────┐  │
│  │  复用 CLI 模块                                │  │
│  │  fetcher.py / indicators.py / scorer.py     │  │
│  │  analyzer.py / support.py / config.py       │  │
│  └──────────────────┬─────────────────────────┘  │
│                     │                            │
│              ┌──────┴──────┐                     │
│              │   SQLite    │                     │
│              │  历史记录    │                     │
│              └─────────────┘                     │
└──────────────────────────────────────────────────┘
```

---

## 四、目标项目结构

```
stock-analysis/
├── pyproject.toml                  # 新增 [web] 可选依赖
├── ...（方案一现有文件不变）
│
├── backend/                         # FastAPI 后端
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口 + 路由注册
│   ├── routers/
│   │   ├── analyze.py              # /api/analyze, /api/batch
│   │   ├── watchlist.py            # /api/watchlist CRUD
│   │   └── history.py              # /api/history CRUD + 评分趋势
│   ├── models.py                   # SQLAlchemy ORM 模型
│   ├── database.py                 # SQLite 连接 + 初始化
│   └── schemas.py                  # Pydantic 请求/响应模型
│
├── frontend/                        # Vue 3 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts                 # Vue 入口
│       ├── App.vue                 # 根组件 + 路由
│       ├── router/
│       │   └── index.ts            # Vue Router 配置
│       ├── stores/
│       │   ├── watchlist.ts        # 自选股状态
│       │   └── analysis.ts         # 分析结果状态
│       ├── api/
│       │   └── index.ts            # Axios 封装 + API 调用
│       ├── views/
│       │   ├── Dashboard.vue       # 仪表盘页
│       │   ├── Analysis.vue        # 个股分析页
│       │   └── History.vue         # 历史记录页
│       ├── components/
│       │   ├── CandlestickChart.vue    # K 线图（ECharts）
│       │   ├── IndicatorCharts.vue     # 技术指标子图
│       │   ├── ScoreCard.vue           # 评分卡片
│       │   ├── ScoreBreakdown.vue      # 评分明细
│       │   ├── TrendPieChart.vue       # 趋势分布饼图
        │   ├── ScoreDistChart.vue       # 评分分布柱状图
        │   ├── WatchlistPanel.vue      # 自选股侧边栏
│       │   └── StockSearch.vue         # 股票搜索输入框
│       ├── composables/
│       │   └── useAnalysis.ts      # 分析逻辑 composable
│       └── types/
│           └── index.ts            # TypeScript 类型定义
│
└── tests/
    ├── ...（现有测试不变）
    └── test_api/                   # API 集成测试（可选）
```

---

## 五、API 设计

### 5.1 分析接口

```
GET  /api/analyze/{code}?market=auto&asset_type=stock&days=60
POST /api/batch
     Body: { "codes": ["600519", "159934:fund"], "market": "auto" }
```

**响应格式**（复用 CLI 的 analyze() 返回值，新增时序数据）：
```json
{
  "stock_info": { "code": "600519", "name": "贵州茅台", ... },
  "technical_indicators": { "ma": {...}, "macd": {...}, ... },
  "key_levels": { "support": [...], "resistance": [...], ... },
  "analysis": { "score": 72, "trend": "上涨趋势", ... },
  "ohlcv": [
    { "date": "2026-04-01", "open": 1670, "high": 1690, "low": 1665, "close": 1685, "volume": 50000 },
    ...
  ],
  "indicator_series": {
    "MA5":  [{ "date": "2026-04-01", "value": 1680 }, ...],
    "MA10": [{ "date": "2026-04-01", "value": 1670 }, ...],
    "MA20": [{ "date": "2026-04-01", "value": 1660 }, ...],
    "MA60": [{ "date": "2026-04-01", "value": 1650 }, ...],
    "DIF":  [{ "date": "2026-04-01", "value": 2.3 }, ...],
    "DEA":  [{ "date": "2026-04-01", "value": 1.8 }, ...],
    "MACD": [{ "date": "2026-04-01", "value": 0.5 }, ...],
    "RSI6": [{ "date": "2026-04-01", "value": 55.2 }, ...],
    "RSI12":[{ "date": "2026-04-01", "value": 52.1 }, ...],
    "RSI24":[{ "date": "2026-04-01", "value": 50.3 }, ...],
    "K":    [{ "date": "2026-04-01", "value": 65.0 }, ...],
    "D":    [{ "date": "2026-04-01", "value": 60.0 }, ...],
    "J":    [{ "date": "2026-04-01", "value": 75.0 }, ...],
    "BOLL_UPPER": [{ "date": "2026-04-01", "value": 1720 }, ...],
    "BOLL_MIDDLE":[{ "date": "2026-04-01", "value": 1680 }, ...],
    "BOLL_LOWER": [{ "date": "2026-04-01", "value": 1640 }, ...]
  }
}
```

> **说明**：`ohlcv` 和 `indicator_series` 是前端 K 线图和技术指标子图所需的时序数据，由后端从 DataFrame 中提取。CLI 原始返回值中的 `technical_indicators`（仅最新值）保持不变，新增字段不影响 CLI 兼容性。

### 5.2 批量分析接口（异步任务 + 进度查询）

50 只股票批量分析需要 30-60 秒，采用"提交任务 + 轮询进度"模式：

```
POST /api/batch
     Body: { "codes": ["600519", "159934:fund"], "market": "auto" }
     Response: { "task_id": "abc123", "status": "running", "total": 50 }

GET  /api/batch/{task_id}
     Response: { "task_id": "abc123", "status": "running", "progress": 15, "total": 50, "results": [...] }
     # status: "running" | "completed"
     # completed 时 results 包含全部结果
```

后端使用 `threading.Lock` + 内存字典存储任务状态，无需额外消息队列。

### 5.3 自选股接口

```
GET    /api/watchlist              # 获取自选股列表
POST   /api/watchlist              # 添加 { "code": "600519", "name": "贵州茅台" }
DELETE /api/watchlist/{code}       # 删除
```

### 5.4 历史记录接口

```
GET    /api/history?code=&start=&end=&trend=&page=1&size=20
GET    /api/score-trend/{code}?days=30
DELETE /api/history/{id}
DELETE /api/history                # 清空
```

---

## 六、前端页面设计

### 6.1 页面 1：仪表盘（/）

```
┌─────────────────────────────────────────────────┐
│  📊 股票技术分析仪表盘          [批量分析] [设置] │
├──────────────┬──────────────────────────────────┤
│              │  ┌──────────┐ ┌──────────────┐   │
│  自选股列表   │  │ 趋势分布  │ │ 评分分布柱状  │   │
│  ┌──────────┐│  │  饼图     │ │  图           │   │
│  │ 600519   ││  └──────────┘ └──────────────┘   │
│  │ 茅台  72 ││                                  │
│  │ 159934   ││  TOP 5 强势 / BOTTOM 5 弱势      │
│  │ 黄金ETF  ││  ┌──────────────────────────┐   │
│  │ ...      ││  │  n-data-table 评分排名表  │   │
│  │          ││  │  支持排序/筛选/点击跳转   │   │
│  │ [+添加]  ││  └──────────────────────────┘   │
│  └──────────┘│                                  │
├──────────────┴──────────────────────────────────┤
│  上次分析: 2026-04-09 15:00  |  共 50 只       │
└─────────────────────────────────────────────────┘
```

**Vue 组件**：
- `WatchlistPanel` — 侧边栏自选股（n-menu + 拖拽排序）
- `TrendPieChart` — ECharts 饼图（趋势分布）
- `ScoreBreakdown` — 评分排名表（n-data-table，点击行跳转分析页）

### 6.2 页面 2：个股分析（/analysis/:code）

```
┌─────────────────────────────────────────────────┐
│  📈 600519 贵州茅台    评分: 72  上涨趋势       │
│  [60天 ▼]  [实时分析]  [保存记录]                │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │  CandlestickChart (ECharts candlestick) │    │
│  │  MA5/10/20/60 叠加线                    │    │
│  │  支撑位/压力位 markLine                 │    │
│  │  底部成交量柱状图（dataZoom 缩放）       │    │
│  └─────────────────────────────────────────┘    │
│  ┌──────────────┐ ┌──────────────┐             │
│  │  MACD 图     │ │  RSI 图      │             │
│  │  IndicatorCharts (ECharts)      │             │
│  └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐             │
│  │  KDJ 图      │ │  布林带图    │             │
│  └──────────────┘ └──────────────┘             │
├─────────────────────────────────────────────────┤
│  ScoreCard (72)  +  ScoreBreakdown (6 维度)     │
├─────────────────────────────────────────────────┤
│  📝 分析摘要（n-card）                           │
└─────────────────────────────────────────────────┘
```

**Vue 组件**：
- `CandlestickChart` — ECharts K 线图（candlestick + MA + markLine + volume）
- `IndicatorCharts` — 4 个技术指标子图（MACD/RSI/KDJ/BOLL）
- `ScoreCard` — 总评分展示（n-statistic + 颜色）
- `ScoreBreakdown` — 6 维度评分（n-progress + 颜色）
- `StockSearch` — 代码输入 + 市场选择（n-input + n-select）

### 6.3 页面 3：历史记录（/history）

```
┌─────────────────────────────────────────────────┐
│  📅 历史分析记录                                 │
├─────────────────────────────────────────────────┤
│  [代码搜索] [日期范围] [趋势筛选] [清空]          │
├─────────────────────────────────────────────────┤
│  n-data-table (分页/排序/筛选)                   │
│  日期 | 代码 | 名称 | 评分 | 趋势 | 涨跌 | 操作 │
├─────────────────────────────────────────────────┤
│  评分趋势（选中股票后展示）                       │
│  ┌─────────────────────────────────────────┐    │
│  │  ECharts line (评分随时间变化)           │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 七、数据库设计

### 6.1 SQLAlchemy ORM 模型

```python
class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: int              # 主键
    code: str            # 代码
    name: str            # 名称
    market: str          # 市场
    asset_type: str      # stock/fund
    score: int           # 评分
    trend: str           # 趋势
    recommendation: str  # 建议
    current_price: float # 当前价格
    change_pct: float    # 涨跌幅
    summary: str         # 摘要
    indicators_json: str # 技术指标 JSON
    analysis_time: datetime  # 分析时间

    __table_args__ = (
        Index('idx_code_time', 'code', 'analysis_time', unique=True),
    )
```

### 7.2 数据库文件位置

```
~/.stock-analysis/history.db
```

与 CLI 的 `config.json` 放在同一目录，保持一致。

---

## 八、依赖变更

### 8.1 pyproject.toml 新增

```toml
[project.optional-dependencies]
web = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy>=2.0",
]
```

### 8.2 前端依赖

```json
{
  "dependencies": {
    "vue": "^3.5",
    "vue-router": "^4.4",
    "pinia": "^2.2",
    "axios": "^1.7",
    "naive-ui": "^2.40",
    "echarts": "^5.5",
    "vue-echarts": "^7.0",
    "@vicons/ionicons5": "^0.12"
  },
  "devDependencies": {
    "vite": "^6.0",
    "typescript": "^5.6",
    "vue-tsc": "^2.1"
  }
}
```

### 8.3 安装与启动

```bash
# 后端
pip install -e ".[full,web]"
uvicorn backend.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev          # http://localhost:5173

# 生产构建
cd frontend && npm run build
# 后端直接 serve 静态文件，或用 Nginx 反代
```

---

## 九、实施步骤

### Step 1: 后端 API（FastAPI）
- 创建 `backend/main.py`（FastAPI 入口 + CORS + `asyncio.to_thread` 包装同步调用）
- 创建 `backend/database.py` + `backend/models.py`（SQLite + ORM + 复合索引）
- 创建 `backend/schemas.py`（Pydantic 模型，含 `ohlcv` / `indicator_series` 时序数据）
- 创建 `backend/routers/analyze.py`（单股/批量分析接口，批量用内存任务字典 + 轮询）
- 创建 `backend/routers/watchlist.py`（自选股 CRUD）
- 创建 `backend/routers/history.py`（历史记录 CRUD + 评分趋势）
- **验收**：Swagger 文档可访问，API 返回正确 JSON（含 ohlcv 时序数据）

> **关键实现**：CLI 的 `StockDataFetcher` 使用同步 `requests`，FastAPI 端点必须用 `asyncio.to_thread()` 包装：
> ```python
> @router.get("/api/analyze/{code}")
> async def analyze(code: str, ...):
>     result = await asyncio.to_thread(analyzer.analyze, code, ...)
>     # 从 DataFrame 提取 ohlcv + indicator_series 追加到 result
>     return result
> ```

### Step 2: 前端项目初始化
- `npm create vite@latest frontend -- --template vue-ts`
- 安装 naive-ui / echarts / vue-echarts / pinia / axios
- 配置路由（Dashboard / Analysis / History）
- 配置 Axios baseURL + 拦截器
- **验收**：三个页面路由可切换，空页面不报错

### Step 3: 个股分析页（核心页面）
- `StockSearch.vue` — 代码输入 + 市场选择
- `CandlestickChart.vue` — K 线图 + MA + 支撑压力位
- `IndicatorCharts.vue` — MACD/RSI/KDJ/BOLL 四个子图
- `ScoreCard.vue` + `ScoreBreakdown.vue` — 评分展示
- `Analysis.vue` — 组装完整页面
- **验收**：输入代码后展示 K 线图 + 指标 + 评分

### Step 4: 仪表盘页
- `WatchlistPanel.vue` — 自选股侧边栏
- `TrendPieChart.vue` — 趋势分布饼图
- `Dashboard.vue` — 概览 + 排名表 + 批量分析
- **验收**：自选股列表 + 一键分析 + 评分排名

### Step 5: 历史记录页
- `History.vue` — 表格 + 筛选 + 评分趋势折线图
- **验收**：保存/查询/删除/评分趋势图

### Step 6: 联调 + 优化
- 前后端联调
- 加载状态（n-spin / n-skeleton）
- 错误处理（n-result 404/500）
- 响应式适配
- **验收**：完整流程无报错

---

## 十、与 Streamlit 方案对比

| 维度 | Streamlit（原方案） | Vue 3 + FastAPI（本方案） |
|------|---------------------|--------------------------|
| 开发速度 | 1-2 天 | 3-5 天 |
| 代码量 | ~500 行 Python | ~1500 行 TS + ~400 行 Python |
| UI 精细度 | 中等（框架控制） | **高（完全自定义）** |
| 交互体验 | 中等（每次交互重跑） | **好（SPA，局部刷新）** |
| 组件生态 | 有限 | **丰富（Naive UI）** |
| 部署 | `streamlit run` 一行 | 前端 build + 后端 uvicorn |
| 扩展性 | 低（受限于 Streamlit） | **高（前后端分离）** |
| 学习成本 | 低（纯 Python） | 中（需要写 TS） |
| 你的熟悉度 | 不熟悉 | **熟悉** |

---

## 十一、注意事项

1. **CORS**：FastAPI 需要配置 `CORSMiddleware` 允许前端跨域
2. **数据缓存**：后端用 `@lru_cache` 或 Redis 缓存分析结果（5 分钟 TTL）
3. **错误处理**：API 返回统一格式 `{ code, message, data }`，前端 Axios 拦截器统一处理
4. **数据延迟**：页面标注"数据延迟 15-20 分钟"
5. **ECharts K 线**：使用 `dataZoom` 组件支持缩放，`markLine` 画支撑压力位
6. **打包部署**：前端 `npm run build` 产出 `dist/`，FastAPI 用 `StaticFiles` 挂载，最终只需一个 uvicorn 进程
