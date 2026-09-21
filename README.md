# 订单 Agent 学习项目

这个项目包含一个 FastAPI + SQLModel 订单服务，以及通过 DeepSeek 工具调用访问该服务的命令行 Agent。当前是学习项目，订单保存在本地 SQLite 数据库中。

## 运行

在项目目录安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动订单服务：

```powershell
python -m uvicorn sqlmodel_server:app --reload
```

打开 <http://127.0.0.1:8000/docs>，可以用 Swagger 创建和查询订单。首次启动时，服务会自动创建 `orders_sqlmodel.db`；数据库文件不会提交到仓库。运行 Agent 前，请先用 Swagger 创建至少一条订单。

另开一个终端，把 `.env.example` 复制为 `.env`，将其中的占位符换成自己的 DeepSeek API Key，然后运行：

```powershell
Copy-Item .env.example .env
python deepseek_client.py
```

Agent 目前支持查询单笔订单、按条件列出订单，以及经人工确认后修改订单状态。输入 `q` 或 `退出` 结束对话。

## 文件

| 路径 | 用途 |
| --- | --- |
| `sqlmodel_server.py` | 订单 API 和数据库操作 |
| `deepseek_client.py` | DeepSeek Agent、工具定义和命令行对话 |

`.env`、数据库、缓存和日志是本地文件，不应提交。请不要把真实 API Key 写进代码或提交到仓库。
