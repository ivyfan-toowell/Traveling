# 架构图片生成提示词

使用内置 imagegen 生成并编辑；图片嵌入 README。

## 生成提示词

Use case: infographic-diagram.
Asset type: a complete raster software architecture diagram for the GitHub README of Traveling travel planner. Create one polished high-resolution landscape image with a white background, crisp readable Chinese typography, simple flat technical blocks, subtle navy/teal/purple/amber color coding, generous whitespace, orthogonal directional arrows, no photographic or decorative scene. This is an engineering diagram: accurate labels and connections are more important than ornament. Aim for 3072x2048 or similarly large landscape resolution. Do not render source code or Mermaid.

Title verbatim: "Traveling"
Subtitle: "项目架构 · LangGraph / LangChain + FastAPI + RAG + MCP"

Arrange four main horizontal tiers with clearly labeled subsystem containers. Tier 1 top full width: user icon "用户" -> "前端 traveling.html" -> "FastAPI · REST / SSE". REST request forward and SSE response back. FastAPI has small endpoint boxes "用户认证 /users", "会话管理 /conversations", "流式聊天 /chat", and "JWT + bcrypt". Show health label "/health" small separate.

Tier 2 central orchestration large container "Agent 编排层".
Main left-center box: "Travel Agent" subtext "Qwen · 单主 Agent + 步骤中间件".
Adjacent box "StepConfigMiddleware" subtext "动态 Prompt / Tools · 前置依赖 · 长期记忆".
Compact numbered sequential flow inside this central main area, precisely eight labels: "1 需求收集" → "2 目的地选择" → "3 交通选择" → "4 住宿选择" → "5 美食选择" → "6 行程生成" → "7 预算汇总" → "8 报告生成". Include a small curved return arrow labeled "状态工具支持回退".
Right portion of orchestration container contains two branches from main Agent:
"目的地 Router" -> "分类与按需并行" -> two boxes "Explore Agent" and "Weather 节点" -> "目的地汇总".
"交通 Coordinator" -> three boxes "Flight Agent", "Train Agent", "Driving Agent" -> "交通方案汇总".
Connect main Travel Agent to destination Router and transport Coordinator. Main Agent also connects directly to RAG tools, MCP tools and memory tools below. Explore connects to RAG tools. Weather node directly connects to 高德天气 API in external service area; do not falsely force it to go through MCP.

Tier 3 three adjacent large containers:
LEFT "RAG 知识检索"
Separate index build line "作者自写 MD · 24 篇" with three small labels "destinations / food / accommodation" -> "UTF-8 文档加载" -> "父子分块 + 相对来源路径" -> "DashScope Embedding" subtext "text-embedding-v2 · 云端 API" -> "Chroma · 子文档向量索引". Note small "首次自动建库 / 内容同步 / 稳定 ID".
Separate query line "RAG Tools" -> "查询优化" -> "Chroma 向量 + BM25" -> "RRF 融合" -> "重排序" -> "父文档映射 + 上下文重排" -> "带来源的上下文". Show Chroma feeds hybrid retrieval. Show "父文档映射 · 内存" fed from parent splitting and connected to mapping. Show "Redis 检索缓存" dashed connection to query processing. RAG tool results return to main and Explore via arrows.
CENTER "业务工具与记忆"
"状态流转工具", "日期工具", "长期记忆工具" three boxes. Long-term memory connects below to Postgres Store.
RIGHT "MCP 外部能力"
"MCPClientManager" subtext "langchain-mcp-adapters" -> "自建 stdio 服务" containing "Weather Server", "Search Server"; and -> "远程 HTTP MCP" containing "高德地图", "12306", "VariFlight", "AIGOHOTEL". Underneath small service boxes "高德天气 API" and "Tavily Search API" connected respectively to local Weather Server and Search Server. Flight Agent connects logically to VariFlight, Train Agent to 12306, Driving Agent to 高德地图, by thin grouped lines, avoiding excessive crossings. Label "密钥与网络依赖".
Tier 4 bottom full width "持久化与运行环境":
"PostgreSQL + pgvector" with three subblocks "SQLAlchemy · 用户 / 会话 / 消息", "LangGraph Checkpointer · 对话状态", "LangGraph Store · 用户偏好 / 旅行记录".
"Redis · RAG 缓存".
"本地 data/vectorstore · Chroma", "data/documents · 原始 MD".
"Qwen / DashScope · 云端模型" supplies main and subagents, query optimization and reranking; use dotted links or a clear note to avoid line clutter.
"Docker Compose" subtext "postgres → init-db → backend；redis 健康检查" with smaller ".env · 配置与密钥（不提交）".
"Loguru 日志 · LangSmith 可选追踪".
Connect API to SQLAlchemy storage, main Agent to Checkpointer, memory tools to Store, RAG cache to Redis. Make clear pgvector is installed but RAG vector retrieval uses Chroma, not PostgreSQL. Chroma has local persistence.
Footer small legend "实线：调用 / 数据流    虚线：缓存 / 配置 / 模型依赖" and note "MD 随仓库提供 · 向量库本地生成 · 云端模型与实时服务需自行配置密钥".

Constraints: all these component names must be spelled accurately. Use the actual architecture only. Do not add Kubernetes, queues, payment, booking execution, automatic reservations, OpenAI API, vector knowledge ingestion from web, or imaginary microservices. Prioritize a clear useful overall structure over connecting every arrow to every small box. Main headings large; every label readable when opened full size. No watermark.

## 准确性修订提示词

Use case: precise-object-edit. Edit the attached raster architecture diagram, preserving the crisp layout, overall composition, colors, all other labels, and module positions.
Make only these engineering accuracy corrections:
1. In the upper-right agent area, remove the small vertical arrow from Explore Agent down to Weather 节点 and remove the arrow from Weather 节点 down to Flight Agent. Explore and Weather are sibling branches of the destination Router and do NOT invoke each other or Flight. Leave Router -> Explore and Router -> Weather and their result connections to 目的地汇总. Draw a clearly routed thin connection from Weather 节点 to the orange 高德天气 API box in the MCP area, traveling down the right side of the diagram without passing through any agent or MCPClientManager box. This Weather node directly calls the weather API.
2. In the remote HTTP MCP service boxes, ensure exact subtitles: 高德地图（地图/路线）, 12306（火车信息）, VariFlight（航班信息）, AIGOHOTEL（酒店信息）. Currently the train/flight subtitles are mismatched; fix them.
3. Section numbering must be sequential: 1 用户与 API 接入层, 2 Agent 编排层, 3 RAG 知识检索, 4 业务工具与记忆, 5 MCP 外部能力, 6 持久化与运行环境. Put 5 in the purple MCP section badge and change the final persistent section badge from 4 to 6.
4. In RAG indexing, Chroma connects to the query box Chroma 向量 + BM25 (vector candidate retrieval), not to 带来源的上下文. Remove the vertical arrow between the Chroma 子文档向量索引 box and 带来源的上下文. The retrieved context comes from 父文档映射 + 上下文重排. Draw a small thin connecting line from the Chroma index box to Chroma 向量 + BM25 routed within RAG area, keeping labels unobstructed.
Do not add or remove any other components. No extra footer. Output one polished image at the same landscape aspect ratio.


## 品牌命名修订

使用内置 imagegen 编辑：将图片主标题改为 Traveling，前端文件名改为 traveling.html，其余模块、文字和连线保持原样。
