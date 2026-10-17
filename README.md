# ✦ 灵犀 AI 助手（Lingxi）

一个基于 **FastAPI + LangChain** 的 AI 智能助手，融合两类核心能力：**多轮对话智能体** 与 **RAG 知识库问答**，并配套完整的用户认证、流式输出与引用溯源。

---

## 功能特性

### 💬 智能对话
- 基于 LangGraph（`create_react_agent`）的多轮对话智能体。
- 支持工具调用：查询当前时间、记住并持久化用户偏好与个人信息。
- 通过 Redis 持久化检查点实现跨会话记忆，多轮上下文连续。
- 登录后自动注入用户画像，对话更个性化。
- SSE 流式输出，逐字返回，前端实时渲染。

### 📚 知识库问答
- 文档上传：支持 `txt / md / pdf / csv / xlsx`，点击上传，同名自动去重。
- 解析入库：按扩展名分派加载器；表格类数据逐行转自然语言；中文标点优先切分，md 按标题切分。
- 向量检索：阿里云百炼 `text-embedding-v4`（1024 维）向量化，Milvus（HNSW + COSINE）相似度检索，相似度阈值过滤噪声。
- 引用溯源：答案严格基于资料生成，标注 `[1][2][3]` 编号，前端渲染来源卡片。

### 👤 用户系统
- 注册 / 登录，Token 鉴权（`Authorization: Bearer <token>`）。
- PostgreSQL + asyncpg 连接池，JSONB 列自动编解码。

### 🩺 运维支持
- `/api/health` 健康检查：向量库统计、Embedding 连通性与维度、DeepSeek 配置状态。
- `scripts/check_environment.py` 环境自检。
- `scripts/seed_demo_data.py` 一键生成并入库演示数据。

---

## 技术栈

| 层次 | 技术 |
| --- | --- |
| Web 框架 | FastAPI、Uvicorn |
| AI / Agent | LangChain、LangGraph、DeepSeek（`deepseek-v4-flash`） |
| 向量化 | 阿里云百炼 DashScope `text-embedding-v4`（1024 维） |
| 向量数据库 | Milvus（服务器模式 / Milvus Lite 本地模式） |
| 会话记忆 | Redis（LangGraph Checkpointer） |
| 业务数据库 | PostgreSQL（asyncpg 连接池） |
| 流式输出 | SSE（Server-Sent Events） |
| 前端 | 原生 HTML / CSS / JavaScript |

---

## 目录结构

```
├── .env                      # 配置文件
├── main.py                   # 服务入口（FastAPI 应用 + lifespan 初始化）
├── settings.py               # 配置中心
├── requirements.txt          # 依赖清单
├── api/                      # 路由层
│   ├── auth_router.py        #   注册 / 登录
│   ├── agent_chat_router.py  #   智能对话（SSE）
│   ├── rag_chat_router.py    #   RAG 问答（流式 / 非流式）
│   ├── documents.py          #   文档上传 / 列表 / 删除
│   └── health.py             #   健康检查
├── core/                     # 核心逻辑
│   ├── llm.py                #   LLM 工厂
│   ├── embeddings.py         #   Embedding 工厂
│   ├── vector_store.py       #   Milvus 向量库封装
│   ├── rag_chain.py          #   RAG 检索 + 生成链
│   └── manifest.py           #   文档注册表
├── ingestion/                # 文档入库流水线
│   ├── loaders.py            #   多格式加载器
│   ├── splitter.py           #   中文切分器
│   └── pipeline.py           #   入库编排
├── pools/py_pool.py          # PostgreSQL 连接池
├── resp/sse_resp.py          # SSE 响应格式
├── service/user_service.py   # 用户服务
├── tools/user_info.py        # 用户记忆工具
├── static/                   # 前端
├── scripts/                  # 运维脚本
└── data/                     # 数据目录（演示文档 / 向量库 / 上传缓存）
```

---

## 快速开始

### 1. 环境要求
- Python 3.11+
- PostgreSQL、Redis、Milvus（或使用 Milvus Lite 本地模式）

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置
编辑项目根目录的 `.env`：
- `DEEPSEEK_API_KEY` —— DeepSeek 对话模型
- `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` —— 阿里云百炼向量化
- `REDIS_URL` —— Redis（对话记忆）
- `DATABASE_URL` —— PostgreSQL（用户系统）
- `KB_MILVUS_URI` —— Milvus（服务器 `http://host:19530` 或本地 `./data/milvus_kb.db`）

> 使用本地 Milvus Lite 时，把 `KB_MILVUS_URI` 改为 `./data/milvus_kb.db`。

### 4. 初始化数据库表
```sql
CREATE TABLE tb_user (
    uid   SERIAL PRIMARY KEY,
    uname VARCHAR(64) UNIQUE NOT NULL,
    pwd   VARCHAR(128) NOT NULL,
    birth DATE,
    ctime TIMESTAMP DEFAULT now(),
    info  JSONB
);
```

### 5.（可选）生成演示数据
```bash
python scripts/seed_demo_data.py
```

### 6. 启动
```bash
python main.py
# 或
uvicorn main:app --reload --port 8000
```
浏览器访问 `http://localhost:8000`，注册登录后即可使用。

---

## API 一览

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| POST | `/api/register` | 注册 | 否 |
| POST | `/api/login` | 登录，返回 access_token | 否 |
| POST | `/chat` | 智能对话（SSE 流式） | 是 |
| POST | `/api/chat/stream` | RAG 流式问答（含引用来源） | 否 |
| POST | `/api/chat` | RAG 非流式问答 | 否 |
| POST | `/api/documents/upload` | 上传文档入库 | 否 |
| GET | `/api/documents` | 文档列表 | 否 |
| DELETE | `/api/documents/{doc_id}` | 删除文档 | 否 |
| GET | `/api/health` | 健康检查 | 否 |

---

## 设计说明

- **分层架构**：`api`（路由）→ `core`（业务）→ `ingestion`（入库）/ `service`（用户）/ `tools`（工具）/ `pools`（基础设施），职责清晰、易扩展。
- **优雅降级**：PostgreSQL / Redis 初始化失败只记录告警、不阻塞知识库问答；智能体未就绪时对话接口返回友好提示。
- **模型策略**：对话智能体与 RAG 问答采用差异化参数——对话高温度（0.7）并关闭思考链输出、RAG 低温度（0.3）保证严谨，兼顾自由表达与回答稳定。
- **中文场景优化**：中文标点切分、表格数据自然语言化、Windows 文件名乱码修复、Milvus Lite Windows 兼容。

## 待优化事项

- **密码哈希**
- **token持久（重启要重登」根治）**
 -**上传接口加固（加鉴权 + 真正校验大小 + 清洗文件名）**