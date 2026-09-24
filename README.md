# 订单 Agent 学习项目

这是一个用于学习企业 Agent 基础流程的订单项目。项目由两部分组成：

- FastAPI + SQLModel 编写的订单服务，数据保存在本地 SQLite 数据库中。
- 调用 DeepSeek 模型的命令行 Agent，由模型选择工具，再通过 HTTP 请求访问订单服务。

## 已实现功能

- 创建、查询、筛选、分页、修改和删除订单。
- Agent 查询单笔订单和订单列表，支持状态、商品名和商品关键词筛选。
- Agent 通过多轮工具调用生成最终回答。
- 修改订单状态前查询原订单，并要求人工输入 `y` 确认。
- 相同状态不会重复写入；用户可以取消操作。
- 后端禁止把“已取消”订单改成其他状态。
- 对工具参数、HTTP 错误和业务结果进行分类处理并记录日志。

订单状态目前只允许：`待发货`、`已发货`、`已取消`。

## 环境要求

- 已安装 Python。本项目当前在 Python 3.13 上验证。
- 拥有可用的 DeepSeek API Key。
- 本机 `8000` 端口可用。订单服务目前只在本机运行。

## 安装与运行

以下命令都在项目目录中执行。

### 1. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 2. 配置 API Key

复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

打开 `.env`，把占位符替换为自己的 DeepSeek API Key：

```text
DEEPSEEK_API_KEY=你的API Key
```

不要把真实 API Key 写进代码或提交到 GitHub。

### 3. 启动订单服务

```powershell
python -m uvicorn sqlmodel_server:app --reload
```

看到 `Application startup complete` 后，打开 Swagger：

<http://127.0.0.1:8000/docs>

首次启动时，程序会自动创建 `orders_sqlmodel.db`。

### 4. 准备测试订单

在 Swagger 中调用 `POST /orders`，例如：

```json
{
  "order_id": "T9001",
  "product": "测试商品",
  "status": "待发货"
}
```

### 5. 启动 Agent

保持订单服务运行，另开一个终端：

```powershell
python deepseek_client.py
```

可以尝试输入：

- `帮我查询 T9001 的订单`
- `帮我查询所有待发货订单`
- `帮我查询商品名称中带“测试”的订单`
- `把 T9001 修改为已发货`

修改状态时，Agent 会展示原状态和目标状态。输入 `y` 执行修改，输入 `n` 取消。输入 `q` 或 `退出` 结束对话。

## 最小验收流程

1. 创建状态为“待发货”的 `T9001`。
2. 查询 `T9001`，确认商品和状态正确。
3. 请求改成“待发货”，确认程序返回无需重复修改。
4. 请求改成“已发货”，在确认步骤输入 `n`，确认数据库没有变化。
5. 再次请求改成“已发货”，输入 `y`，确认修改成功。
6. 把订单改成“已取消”，再尝试改成其他状态，确认后端返回 `403` 并拒绝修改。
7. 测试结束后，可在 Swagger 中调用 `DELETE /orders/T9001` 清理订单。

## 项目文件

| 路径 | 用途 |
| --- | --- |
| `sqlmodel_server.py` | 订单 API、数据库模型、数据库操作和业务规则 |
| `deepseek_client.py` | DeepSeek Agent、工具定义、多轮调用、人工确认和日志 |
| `requirements.txt` | Python 依赖及当前验证版本 |
| `.env.example` | 环境变量格式示例，不含真实密钥 |
| `.gitignore` | 排除密钥、数据库、缓存和日志等本地文件 |

## 当前边界

- 这是本地学习项目，还没有部署到服务器。
- 数据保存在本地 SQLite 中，不适合多人并发的生产环境。
- 对话上下文只保存在当前进程内，程序退出后不会保留。
- 当前没有用户登录、角色权限和操作审计功能。
- 写操作已有人工确认和后端业务规则，但仍属于教学实现。

## 常见问题

- 提示找不到模块：确认 VS Code 使用了正确的 Python 解释器，并重新安装 `requirements.txt`。
- 提示找不到 `DEEPSEEK_API_KEY`：确认项目目录中存在 `.env`，且变量名拼写正确。
- Agent 提示订单服务无法连接：确认 Uvicorn 正在运行，地址为 `http://127.0.0.1:8000`。
- 创建订单返回 `409`：该订单编号已经存在，请更换编号或先删除旧订单。
- 请求返回 `422`：检查请求字段、订单状态取值以及分页参数范围。

`.env`、SQLite 数据库、缓存和日志都是本地文件，不应提交到仓库。
