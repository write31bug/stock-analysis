# Vue 3 Web 可视化 - 开发计划

> 基于 stock-analysis v1.8.0 | 方案二实施计划
> 日期: 2026-04-09

---

## 总览

| 阶段 | 内容 | 交付物 | 预估 |
|------|------|--------|------|
| **P1** | 后端 API | 6 个文件，Swagger 可访问 | Step 1-2 |
| **P2** | 前端骨架 | 路由/状态/API 层就绪 | Step 3-4 |
| **P3** | 个股分析页 | K 线图 + 指标 + 评分 | Step 5-9 |
| **P4** | 仪表盘页 | 自选股 + 排名 + 饼图 | Step 10-12 |
| **P5** | 历史记录页 | 表格 + 评分趋势图 | Step 13-14 |
| **P6** | 联调优化 | 前后端联调 + 错误处理 | Step 15-16 |

---

## P1: 后端 API（Step 1-2）

### Step 1: 项目初始化 + 依赖

**输入**: 现有 CLI 项目
**输出**: 后端目录结构 + 依赖安装成功

- [ ] 创建 `backend/` 目录结构
  ```
  backend/
  ├── __init__.py
  ├── main.py
  ├── database.py
  ├── models.py
  ├── schemas.py
  └── routers/
      ├── __init__.py
      ├── analyze.py
      ├── watchlist.py
      └── history.py
  ```
- [ ] `pyproject.toml` 新增 `[web]` 可选依赖
  ```toml
  [project.optional-dependencies]
  web = ["fastapi>=0.110", "uvicorn[standard]>=0.29", "sqlalchemy>=2.0"]
  ```
- [ ] `pip install -e ".[full,web]"` 安装成功
- [ ] **验收**: `python -c "import fastapi; import sqlalchemy"` 无报错

### Step 2: 数据库 + 基础框架

**输入**: Step 1 的目录结构
**输出**: SQLite 数据库可读写，FastAPI 空应用可启动

- [ ] `backend/database.py` — SQLite 连接 + `init_db()` 建表
- [ ] `backend/models.py` — `AnalysisRecord` ORM 模型（含复合唯一索引）
- [ ] `backend/main.py` — FastAPI 入口 + CORS + 路由注册 + `startup` 事件建表
- [ ] **验收**: `uvicorn backend.main:app --reload` 启动成功，`/docs` 可访问

---

## P2: 前端骨架（Step 3-4）

### Step 3: Vue 项目初始化

**输入**: 无
**输出**: Vue 3 + TS 项目可运行

- [ ] `npm create vite@latest frontend -- --template vue-ts`
- [ ] 安装依赖:
  ```bash
  npm install naive-ui echarts vue-echarts pinia vue-router@4 axios @vicons/ionicons5
  npm install -D @types/node
  ```
- [ ] `vite.config.ts` 配置代理:
  ```ts
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
  ```
- [ ] **验收**: `npm run dev` 启动成功，`http://localhost:5173` 可访问

### Step 4: 路由 + 状态 + API 层

**输入**: Step 3 的空项目
**输出**: 三个页面路由可切换，API 层可调用

- [ ] `src/router/index.ts` — 三个路由:
  - `/` → Dashboard
  - `/analysis/:code?` → Analysis
  - `/history` → History
- [ ] `src/api/index.ts` — Axios 封装:
  - baseURL: `/api`
  - 响应拦截器（统一错误处理）
  - 接口函数: `analyze()`, `batchAnalyze()`, `getBatchStatus()`, `watchlist CRUD`, `history CRUD`
- [ ] `src/stores/watchlist.ts` — Pinia store（自选股列表 + 操作方法）
- [ ] `src/stores/analysis.ts` — Pinia store（分析结果 + 加载状态）
- [ ] `src/types/index.ts` — TypeScript 类型定义（AnalysisResult, OHLCV, IndicatorSeries 等）
- [ ] 三个页面创建空组件（`<template>` + 占位文字）
- [ ] **验收**: 浏览器切换三个路由，无报错

---

## P3: 个股分析页（Step 5-9）

### Step 5: 后端分析接口

**输入**: P1 的后端框架
**输出**: `/api/analyze/{code}` 返回完整数据（含 ohlcv 时序）

- [ ] `backend/schemas.py` — Pydantic 响应模型:
  - `OHLCVItem`（date/open/high/low/close/volume）
  - `SeriesPoint`（date/value）
  - `AnalyzeResponse`（含 ohlcv + indicator_series）
- [ ] `backend/routers/analyze.py`:
  - `GET /api/analyze/{code}` — 单股分析
    - `asyncio.to_thread(analyzer.analyze, ...)` 包装
    - 从 DataFrame 提取 ohlcv 列表
    - 从 DataFrame 提取 indicator_series（MA/DIF/DEA/MACD/RSI/KDJ/BOLL）
    - 追加到 result 返回
  - `POST /api/batch` — 提交批量任务（返回 task_id）
  - `GET /api/batch/{task_id}` — 查询批量进度
- [ ] **验收**: `curl /api/analyze/600519` 返回 JSON 含 `ohlcv` 和 `indicator_series`

### Step 6: 后端自选股 + 历史记录接口

**输入**: Step 2 的数据库
**输出**: 自选股和历史记录 CRUD 可用

- [ ] `backend/routers/watchlist.py`:
  - `GET /api/watchlist` — 从 config.json 读取
  - `POST /api/watchlist` — 添加
  - `DELETE /api/watchlist/{code}` — 删除
- [ ] `backend/routers/history.py`:
  - `POST /api/history` — 保存分析记录
  - `GET /api/history` — 分页查询（支持 code/trend/date 筛选）
  - `GET /api/score-trend/{code}` — 评分趋势数据
  - `DELETE /api/history/{id}` — 删除单条
  - `DELETE /api/history` — 清空
- [ ] **验收**: Swagger 中测试所有接口返回正确

### Step 7: K 线图组件

**输入**: Step 5 的 API 数据
**输出**: ECharts K 线图可渲染

- [ ] `src/components/CandlestickChart.vue`:
  - Props: `ohlcv: OHLCVItem[]`, `maSeries: Record<string, SeriesPoint[]>`, `supportLevels: number[]`, `resistanceLevels: number[]`
  - ECharts 配置:
    - `candlestick` 系列（OHLCV）
    - `line` 系列（MA5/10/20/60 叠加，不同颜色）
    - `bar` 系列（成交量，涨红跌绿）
    - `markLine`（支撑位/压力位水平虚线）
    - `dataZoom`（底部缩放条）
  - 响应式宽度 `autoresize`
- [ ] **验收**: 传入模拟数据，K 线图正确渲染

### Step 8: 技术指标子图组件

**输入**: Step 5 的 API 数据
**输出**: 4 个指标子图可渲染

- [ ] `src/components/IndicatorCharts.vue`:
  - Props: `indicatorSeries`, `rsiData`, `kdjData`, `bollData`
  - 2x2 grid 布局（`n-grid`）:
    - MACD: DIF 线 + DEA 线 + MACD 柱（红绿）
    - RSI: RSI6/12/24 三线 + 超买(70)/超卖(30) 区域
    - KDJ: K/D/J 三线 + 超买(80)/超卖(20) 区域
    - 布林带: 上/中/下轨 + 价格线 + 填充区域
- [ ] **验收**: 传入模拟数据，4 个子图正确渲染

### Step 9: 个股分析页组装

**输入**: Step 7-8 的组件
**输出**: 完整的个股分析页

- [ ] `src/components/StockSearch.vue` — 搜索输入框:
  - `n-input` + `n-select`（市场选择）
  - 回车/点击触发分析
  - URL 参数同步（`/analysis/600519`）
- [ ] `src/components/ScoreCard.vue` — 总评分卡片:
  - `n-statistic` 大数字显示评分
  - 颜色: ≥75 绿 / 40-74 灰 / <40 红
  - 趋势标签 + 建议文字
- [ ] `src/components/ScoreBreakdown.vue` — 6 维度评分:
  - `n-progress` 进度条（正分绿色，负分红色）
  - 维度: 均线/MACD/RSI/布林带/KDJ/成交量
- [ ] `src/views/Analysis.vue` — 页面组装:
  - 顶部: StockSearch + 评分概览
  - 中部: CandlestickChart
  - 下部: IndicatorCharts (2x2)
  - 底部: ScoreBreakdown + 分析摘要（n-card）
  - 加载状态: `n-spin` / `n-skeleton`
  - 保存按钮: 调用 `POST /api/history`
- [ ] **验收**: 输入 600519，展示完整 K 线图 + 指标 + 评分

---

## P4: 仪表盘页（Step 10-12）

### Step 10: 自选股管理组件

**输入**: Step 6 的 API
**输出**: 自选股侧边栏可增删

- [ ] `src/components/WatchlistPanel.vue`:
  - Props: `watchlist`, `selectedCode`
  - 列表展示（代码 + 名称 + 评分）
  - 点击跳转到 `/analysis/{code}`
  - 添加/删除按钮
  - 批量分析按钮（调用 `POST /api/batch` + 轮询进度）
  - 进度条 `n-progress`
- [ ] **验收**: 添加/删除自选股，点击跳转

### Step 11: 仪表盘图表组件

**输入**: Step 6 的 API
**输出**: 饼图 + 柱状图可渲染

- [ ] `src/components/TrendPieChart.vue`:
  - Props: `trendData: Record<string, number>`
  - ECharts pie: 趋势分布（强势上涨/上涨/震荡/下跌/强势下跌）
  - 颜色: 绿/浅绿/灰/浅红/红
- [ ] `src/components/ScoreDistChart.vue`:
  - Props: `scores: number[]`
  - ECharts bar: 评分区间分布（0-20/20-40/40-60/60-80/80-100）
- [ ] **验收**: 传入模拟数据，图表正确渲染

### Step 12: 仪表盘页组装

**输入**: Step 10-11 的组件
**输出**: 完整的仪表盘页

- [ ] `src/views/Dashboard.vue`:
  - 左侧: WatchlistPanel
  - 右上: TrendPieChart + ScoreDistChart（`n-grid` 2 列）
  - 右下: 评分排名表（`n-data-table`，支持排序）
    - 列: 代码/名称/评分/趋势/涨跌
    - 点击行跳转分析页
  - 顶部: 批量分析按钮 + 上次分析时间
  - 自动加载: 页面挂载时从 `/api/history?limit=50` 读取最近记录
- [ ] **验收**: 仪表盘展示自选股 + 图表 + 排名表

---

## P5: 历史记录页（Step 13-14）

### Step 13: 历史记录表格

**输入**: Step 6 的 API
**输出**: 历史记录可查询/筛选/删除

- [ ] `src/views/History.vue`:
  - 筛选栏: 代码搜索 + 日期范围 + 趋势下拉 + 清空按钮
  - `n-data-table`:
    - 列: 日期/代码/名称/评分/趋势/涨跌/操作
    - 分页: `n-pagination`
    - 排序: 按评分/日期
    - 删除: 行内删除按钮
  - 空状态: `n-empty` 提示
- [ ] **验收**: 历史记录正确展示，筛选/删除功能正常

### Step 14: 评分趋势图

**输入**: Step 6 的 API
**输出**: 选中股票后展示评分折线图

- [ ] 在 History.vue 中添加:
  - 点击表格行时，请求 `GET /api/score-trend/{code}`
  - ECharts line: 评分随时间变化折线图
  - 标注线: 75（强势线）/ 25（弱势线）
  - 区域填充: >75 绿色 / <25 红色
- [ ] **验收**: 点击记录行，下方展示评分趋势折线图

---

## P6: 联调优化（Step 15-16）

### Step 15: 前后端联调

**输入**: P3-P5 的全部功能
**输出**: 完整流程无报错

- [ ] 启动后端 `uvicorn backend.main:app --reload --port 8000`
- [ ] 启动前端 `npm run dev`
- [ ] 完整流程测试:
  1. 仪表盘 → 添加自选股 → 批量分析
  2. 点击自选股 → 个股分析页 → K 线图 + 指标
  3. 保存记录 → 历史记录页 → 查看评分趋势
  4. 删除记录 → 确认删除成功
- [ ] **验收**: 全流程无报错，数据一致

### Step 16: 错误处理 + 优化

**输入**: Step 15 的联调结果
**输出**: 生产可用

- [ ] 加载状态: 所有异步操作加 `n-spin` / `n-skeleton`
- [ ] 错误处理:
  - 网络错误: `n-result` 500 页面
  - 数据为空: `n-empty` 提示
  - API 错误: Axios 拦截器 + `n-notification` 提示
- [ ] 数据延迟提示: 页面底部标注"数据延迟 15-20 分钟"
- [ ] 响应式: 移动端基本可用
- [ ] **验收**: 各种异常场景不崩溃，有友好提示

---

## 里程碑检查点

| # | 检查点 | 验收命令/操作 |
|---|--------|-------------|
| M1 | 后端 API 就绪 | `curl /api/analyze/600519` 返回含 ohlcv 的 JSON |
| M2 | 前端骨架就绪 | `npm run dev` 三个路由可切换 |
| M3 | 个股分析页就绪 | 输入 600519 展示 K 线图 + 指标 + 评分 |
| M4 | 仪表盘就绪 | 自选股 + 批量分析 + 评分排名 |
| M5 | 历史记录就绪 | 保存/查询/删除/评分趋势图 |
| M6 | 联调完成 | 全流程无报错 |
