# 股票技术分析 Web 应用 - Windows 启动指南

## 前置条件

| 工具 | 版本要求 | 下载地址 |
|------|---------|---------|
| Python | >= 3.8 | https://www.python.org/downloads/ |
| Node.js | >= 18 | https://nodejs.org/ |

> 安装 Python 时勾选 **"Add Python to PATH"**

---

## 方式一：双击启动（最简单）

1. 打开命令提示符（cmd）或 PowerShell
2. 进入项目目录：
   ```
   cd stock-analysis
   ```
3. 双击运行 `start.bat`

启动后会自动弹出两个窗口（后端 + 前端），关闭窗口即停止服务。

---

## 方式二：手动启动（推荐调试时用）

### 第 1 步：安装后端依赖

```cmd
cd stock-analysis
pip install -e ".[full,web]"
```

### 第 2 步：安装前端依赖

```cmd
cd frontend
npm install
cd ..
```

### 第 3 步：启动后端（窗口 1）

```cmd
cd stock-analysis
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

看到 `Uvicorn running on http://0.0.0.0:8000` 表示成功。

### 第 4 步：启动前端（窗口 2）

新开一个 cmd 窗口：

```cmd
cd stock-analysis\frontend
npm run dev
```

看到 `Local: http://localhost:5173/` 表示成功。

### 第 5 步：打开浏览器

访问 **http://localhost:5173**

---

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |

---

## 常见问题

### Q: `pip install` 报错权限不足

```cmd
pip install --user -e ".[full,web]"
```

或使用虚拟环境：

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[full,web]"
```

### Q: `python -m uvicorn` 报错找不到模块

```cmd
pip install uvicorn[standard] -q
```

### Q: `npm run dev` 报错 `vite: not found`

```cmd
cd frontend
npm install
npx vite
```

### Q: 前端页面空白 / 接口 404

确认后端已启动且运行在 8000 端口。打开 http://localhost:8000/docs 看能否访问 API 文档。

### Q: 端口被占用

修改端口号：

```cmd
:: 后端改用 8001
python -m uvicorn backend.main:app --port 8001

:: 前端改用 5174
cd frontend
npx vite --port 5174
```

如果改了后端端口，前端也需要同步修改。编辑 `frontend/src/api/index.ts`，将 `baseURL` 改为 `http://localhost:8001`。

---

## 离线测试（无网络环境）

后端启动后，前端分析接口加 `?test=true` 参数即可使用模拟数据：

- 单股分析：http://localhost:8000/api/analyze/600519?test=true
- 一键分析：前端看板的"一键分析全部"按钮默认使用 test 模式
