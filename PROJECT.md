# 灵犀 StreamMind — 多智能体直播运营系统

> 版本 4.0.0 | Python 3.12 | FastAPI + Pydantic + DeepSeek LLM

---

## 一、项目概述

"灵犀 StreamMind" 是一个**多智能体 AI 直播运营仿真系统**，模拟短视频/直播平台（如抖音直播）中内容分发、用户画像演化、直播间实时运营的完整链路。系统通过三个独立 AI Agent 协同工作，为直播主播提供实时决策卡片（话题建议+洞察分析+口播过渡语），辅助主播应对观众偏好漂移和冷场危机。

### 核心仿真场景

```
视频内容池 → 视频打标 → 用户观看行为 → 用户画像演化 → 直播间观众漂移 → AI决策卡片生成
```

---

## 二、技术栈

| 层级 | 技术选型 |
|------|---------|
| **语言** | Python 3.12 |
| **Web 框架** | FastAPI + Uvicorn (ASGI) |
| **数据模型** | Pydantic v2 |
| **异步运行时** | Python asyncio |
| **大模型接入** | OpenAI 兼容 API (默认 DeepSeek Chat) |
| **前端** | TailwindCSS (CDN) + ECharts 5.5 (CDN) + 原生 JavaScript |
| **实时通信** | Server-Sent Events (SSE) + RESTful API |
| **浏览器 API** | Web Audio API（麦克风冷场检测）、MediaRecorder API（高光片段录制）、getUserMedia（摄像头） |

---

## 三、系统架构

```
┌────────────────────────────────────────────────────────────────┐
│                      前端仪表盘 (3 页面)                         │
│   index.html (直播总控)  users.html (用户画像)  videos.html (视频) │
│              TailwindCSS + ECharts + 原生 JS                     │
└───────────────────────────┬────────────────────────────────────┘
                            │ HTTP REST + SSE 事件流
┌───────────────────────────▼────────────────────────────────────┐
│                      API 路由层 (routes/)                        │
│  video_routes.py (视频CRUD+打标)  user_routes.py (用户+画像更新)   │
│  live_routes.py (直播控制+SSE卡片流+冷场触发)                      │
│  依赖注入: setup() 注入数据加载器 → 解耦路由与数据层                │
└───────┬──────────────────┬──────────────────┬──────────────────┘
        │                  │                  │
┌───────▼──────┐  ┌────────▼───────┐  ┌──────▼──────────────────┐
│  Agent 1     │  │  Agent 2       │  │  Agent 3                 │
│ VideoTagger  │  │ UserPersona    │  │  LiveHostAgent           │
│ 视频智能打标  │  │ 用户画像EMA更新 │  │  决策卡片生成器            │
│ mock/LLM双模 │  │ α=0.6 β=0.4   │  │  initial/drift/cold 三卡 │
└──────────────┘  └────────────────┘  └──────────────────────────┘
        │                  │                  │
┌───────▼──────────────────▼──────────────────▼──────────────────┐
│                    服务层 (services/)                            │
│  live_service.py: 直播状态机 · 在线用户轮转 · 漂移检测 · 冷场监控   │
│                   · 人气峰值追踪 · 观众历史记录                    │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                     数据层 (main.py)                             │
│  MockDataGenerator → 100 视频 + 100 用户 + 100×100 行为记录       │
│  全局数据懒加载: _load_videos() / _load_users() / _load_behaviors() │
│  tags_cache 内存缓存 (无数据库)                                    │
└────────────────────────────────────────────────────────────────┘
```

---

## 四、目录结构

```
D:\ByteDance_V2\
├── main.py                     # FastAPI 应用入口、全局数据加载、根路由
├── config.py                   # 全局配置：12维标签、LLM参数、漂移阈值、EMA常量
├── models.py                   # Pydantic 数据模型（VideoMeta/UserProfile/TagResult 等）
├── data_generator.py           # 模拟数据生成器（视频/用户/行为）
├── agents/                     # 多智能体模块
│   ├── video_tagger.py         # Agent 1：视频智能打标
│   ├── user_persona.py         # Agent 2：用户画像 EMA 更新
│   └── live_host.py            # Agent 3：直播决策卡片生成器
├── routes/                     # API 路由层
│   ├── video_routes.py         # 视频 CRUD + 打标 + 批量打标
│   ├── user_routes.py          # 用户画像 + 行为查询 + 画像批量更新
│   └── live_routes.py          # 直播控制 + SSE 卡片流 + 在线用户 + 冷场触发
├── services/                   # 业务逻辑层
│   └── live_service.py         # 直播间状态机（轮转循环/漂移检测/峰值追踪）
├── index.html                  # 前端：直播总控台（摄像头/卡片流/观众Top5/高光片段）
├── users.html                  # 前端：用户画像分析（100用户12维向量+行为指标）
└── videos.html                 # 前端：视频打标结果（帧描述/标签/12维潜在向量）
```

---

## 五、三大 AI Agent 详解

### Agent 1 — VideoTaggingAgent（视频智能打标）

- **文件**: `agents/video_tagger.py`
- **输入**: 视频元数据（帧描述 + 作者标签）
- **输出**: `TagResult`（领域标签 + 12维潜在向量 + 置信度 + 推理）
- **双模式运行**:
  - **mock 模式**: 关键词匹配 + 高斯噪声生成潜在向量，确定性可复现
  - **openai 模式**: 调用 DeepSeek LLM 返回 JSON 标签和向量，失败时自动回退 mock
- **批量打标**: 支持并发控制（`asyncio.Semaphore`，默认并发8），异步批量处理

### Agent 2 — UserPersonaAgent（用户画像 EMA 更新）

- **文件**: `agents/user_persona.py`
- **核心算法**: **指数移动平均（EMA）**
  ```
  新向量 = 旧向量 × β + 视频向量 × 交互权重 × α
  α = 0.6 (新信息权重)  β = 0.4 (历史惯性)
  ```
- **交互权重公式**（加权融合五种行为信号）:
  ```
  weight = watch_ratio/100 × 0.40    # 观看完成率
         + is_liked × 0.20           # 点赞
         + is_favorited × 0.30       # 收藏
         + is_followed × 0.05        # 关注
         + is_commented × 0.05       # 评论
  ```
- **输出**: `PersonaUpdateResult`（新/旧向量、偏移量 L2 距离、主导维度、交互次数）

### Agent 3 — LiveHostAgent（决策卡片生成器）

- **文件**: `agents/live_host.py`
- **三种卡片类型**:

| 类型 | 触发条件 | 用途 |
|------|---------|------|
| `initial` | 直播开始 | 开场话题 + 第一波产品方向 |
| `drift` | 观众偏好漂移 | 话题切换建议 (Top5 变更 / 欧氏距离超阈值) |
| `cold` | 麦克风冷场 >10s | 救场卡片 (抽奖/问答/秒杀) |

- **卡片结构**: `{topic, reason, script}` — 话题建议 / 一句话洞察 / 自然口播过渡语（50字内）
- **双模式**: mock模式（模板库+变量替换） / openai模式（DeepSeek实时生成）

---

## 六、直播间核心机制

### 6.1 在线用户轮转循环

- **文件**: `services/live_service.py:_rotation_loop`
- 每 N 秒（默认 15s，可配置）重新随机选取 10~50 名用户进入直播间
- 在线用户向量叠加高斯噪声（μ=0, σ=0.05），模拟兴趣偏好自然波动
- 每次轮转重新聚合偏好并执行漂移检测

### 6.2 观众偏好漂移检测

- **双重检测机制**:
  1. **向量偏移**: 当前聚合向量与基线向量的 **欧氏距离** ≥ 阈值（默认 0.05）
  2. **Top5 变更**: 当前 Top5 偏好类别与基线 Top5 存在差异（集合运算）
- 漂移触发后自动更新基线（新基线 = 当前向量），并设置 `pending_card_type = "drift"`

### 6.3 主导维度聚合算法

- 不使用向量平均，而是统计在线用户 **主导维度**（每人向量最大值索引）的计数
- 排序后得到 Top5 偏好分布（含百分比），更容易触发 >70% 的分布集中度

### 6.4 冷场救援

- 前端通过 Web Audio API 监测麦克风音量，连续静音 >10 秒
- 前端调用 `POST /api/live/cold-field` 触发 `pending_card_type = "cold"`
- Agent 3 生成救场卡片（互动抽奖 / 弹幕问答 / 限时秒杀）

### 6.5 人气峰值追踪

- 每次轮转检测时更新巅峰时刻记录（时间/人数/Top5/轮次）
- 前端 ECharts 折线图展示在线人数历史曲线 + 峰值标记

---

## 七、12 维内容分类体系

| 序号 | 维度 | 序号 | 维度 | 序号 | 维度 |
|------|------|------|------|------|------|
| 1 | 知识干货 | 5 | 户外旅行 | 9 | 运动健身 |
| 2 | 游戏娱乐 | 6 | 萌宠日常 | 10 | 影视八卦 |
| 3 | 美食探店 | 7 | 情感心理 | 11 | 职场提升 |
| 4 | 科技数码 | 8 | 穿搭美妆 | 12 | 家居生活 |

- 每类对应一组标称向量（对角线主导 + 微小扰动，如 `[0.88, 0.01, ..., 0.01]`）
- 视频和用户均以 12 维归一化向量表示其内容/兴趣分布

---

## 八、API 接口总览

### 视频模块 (`/api/videos`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/videos` | 分页列出视频 |
| `GET` | `/api/videos/{id}` | 获取单个视频详情 |
| `POST` | `/api/videos/tag` | 对单个视频打标 |
| `POST` | `/api/videos/tag/batch` | 批量视频打标 |
| `GET` | `/api/videos/{id}/tags` | 获取已缓存的打标结果 |

### 用户模块 (`/api/users`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/users` | 分页列出用户 |
| `GET` | `/api/users/stats/all` | 所有用户画像+行为特征汇总 |
| `GET` | `/api/users/{id}/behaviors` | 用户行为记录查询 |
| `POST` | `/api/users/{id}/update-persona` | 单用户画像更新 |
| `POST` | `/api/users/update-all-personas` | 全量用户画像批量更新 |

### 直播模块 (`/api/live`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/live/stats` | 直播状态总览 |
| `POST` | `/api/live/start` | 开启直播 |
| `POST` | `/api/live/stop` | 停止直播 |
| `POST` | `/api/live/force-reset` | 强制重置直播状态 |
| `GET` | `/api/live/cards/stream` | **SSE 事件流**：实时推送决策卡片 |
| `GET` | `/api/live/users/online` | 当前在线用户列表 |
| `GET` | `/api/live/clips` | 高光时刻数据 |
| `POST` | `/api/live/cold-field` | 触发冷场救援 |

### 系统模块

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 系统概览（服务名/版本/数据量） |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/stats` | 数据统计（视频/用户/行为分布） |
| `GET` | `/api/behavior/stats` | 行为统计（访问率/互动率/观看分布） |

---

## 九、设计亮点

### 9.1 架构设计
- **依赖注入路由层**: 每个 route 模块通过 `setup(callback)` 接收数据加载器，实现路由与数据源的完全解耦
- **懒加载 + 闭包缓存**: 全局数据通过 `_load_*()` 闭包函数实现单次生成、多次复用
- **服务分离**: 直播核心逻辑独立于路由和 Agent，职责清晰

### 9.2 算法设计
- **EMA 加权更新**: 用户画像采用平滑指数移动平均，避免单次行为过度影响，保持画像稳定性
- **双阈漂移检测**: 欧氏距离 + Top5 集合变化的双重判定，兼顾数值漂移和语义漂移
- **主导维度聚合**: 用维度计数代替向量均值，使 Top5 偏好分布更直观且容易触发集中度变化

### 9.3 工程实践
- **LLM 回退机制**: Agent 调用 LLM 失败时自动降级为 mock 模式，保证系统可用性
- **SSE 实时推送**: 决策卡片通过 SSE 事件流实时推送到前端，延迟低、实现简洁
- **UTF-8 自定义响应**: 覆写 `JSONResponse.render` 确保中文 `ensure_ascii=False`
- **固定随机种子**: `random.Random(42)` 保证模拟数据确定性可复现

### 9.4 前端交互
- **三页面仪表盘**: 直播总控 / 用户分析 / 视频管理，各司其职
- **高光片段录制**: 利用 MediaRecorder API 在卡片触发时自动截取录像片段
- **摄像头实时预览**: 通过 `getUserMedia` 获取摄像头画面模拟真实直播场景

---

## 十、启动方式

```bash
# 方式一：直接启动
python main.py

# 方式二：使用 uvicorn（支持热重载）
uvicorn main:app --reload --port 8000
```

启动后访问:
- **直播总控台**: 直接打开 `index.html`（或 `http://localhost:8000`）
- **用户画像页**: 打开 `users.html`
- **视频管理页**: 打开 `videos.html`

### 环境变量（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | 内置默认值 | LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `deepseek-chat` | LLM 模型名称 |

---

## 十一、依赖项

```
fastapi
uvicorn
pydantic
openai              # 可选，仅 openai 模式需要
```

（项目无 `requirements.txt`，需手动安装。）
