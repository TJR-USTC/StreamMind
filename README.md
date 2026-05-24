# StreamMind — 多智能体直播运营系统

> 版本 4.0.0 | Python 3.12 | FastAPI + Pydantic + DeepSeek LLM

模拟短视频/直播平台中内容分发、用户画像演化、直播间实时运营的完整链路。通过三个独立 AI Agent 协同工作，为主播提供实时决策卡片。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（二选一）
# 方式一：设置环境变量
export LLM_API_KEY="sk-xxxx"
# 方式二：复制 .env.example 为 .env 并填入密钥
cp .env.example .env

# 3. 启动服务（二选一）
python main.py
# 或
uvicorn main:app --reload --port 8000
```

启动后访问：
- **直播总控台**：[http://localhost:8000](http://localhost:8000) 或打开 `index.html`
- **用户画像页**：打开 `users.html`
- **视频管理页**：打开 `videos.html`

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | —（必填） | LLM API 密钥，支持 DeepSeek / OpenAI |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `deepseek-chat` | LLM 模型名称 |

## 核心功能

### 三大 AI Agent

| Agent | 文件 | 功能 |
|-------|------|------|
| **VideoTaggingAgent** | `agents/video_tagger.py` | 视频智能打标：输入帧描述，输出领域标签 + 12维潜在向量。支持 mock/LLM 双模式，失败自动回退 |
| **UserPersonaAgent** | `agents/user_persona.py` | 用户画像 EMA 更新：基于观看/点赞/收藏/关注/评论行为，指数移动平均更新 12 维兴趣向量 |
| **LiveHostAgent** | `agents/live_host.py` | 决策卡片生成器：生成开场话题 / 漂移切换建议 / 冷场救场卡片 |

### 直播间机制

- **观众轮转**：每 15 秒随机选取 10-50 名在线用户，加入高斯噪声模拟兴趣波动
- **漂移检测**：双重检测（欧氏距离 + Top5 变更），自动触发话题切换卡片
- **冷场救援**：前端 Web Audio API 检测麦克风静音 >10s，自动生成救场卡片
- **峰值追踪**：记录在线人数历史曲线 + 巅峰时刻

### 12 维内容分类

知识干货 | 游戏娱乐 | 美食探店 | 科技数码 | 户外旅行 | 萌宠日常 | 情感心理 | 穿搭美妆 | 运动健身 | 影视八卦 | 职场提升 | 家居生活

## API 接口

| 模块 | 路径 | 说明 |
|------|------|------|
| **系统** | `GET /` | 系统概览 |
| | `GET /api/health` | 健康检查 |
| | `GET /api/stats` | 数据统计 |
| | `GET /api/behavior/stats` | 行为统计 |
| **视频** | `GET /api/videos` | 视频列表 |
| | `POST /api/videos/tag` | 单视频打标 |
| | `POST /api/videos/tag/batch` | 批量打标 |
| **用户** | `GET /api/users` | 用户列表 |
| | `POST /api/users/{id}/update-persona` | 画像更新 |
| | `POST /api/users/update-all-personas` | 全量画像更新 |
| **直播** | `POST /api/live/start` | 开启直播 |
| | `POST /api/live/stop` | 停止直播 |
| | `GET /api/live/cards/stream` | SSE 实时卡片流 |
| | `POST /api/live/cold-field` | 触发冷场救援 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 / FastAPI / Pydantic v2 / asyncio |
| AI | OpenAI 兼容 API (DeepSeek Chat) |
| 前端 | TailwindCSS / ECharts 5.5 / 原生 JS |
| 实时 | SSE (Server-Sent Events) |
| 浏览器 | Web Audio API / MediaRecorder API / getUserMedia |

## 项目结构

```
├── main.py              # FastAPI 入口
├── config.py            # 全局配置
├── models.py            # Pydantic 数据模型
├── data_generator.py    # 模拟数据生成器
├── agents/              # AI Agent 模块
├── routes/              # API 路由层
├── services/            # 业务逻辑层
├── index.html           # 直播总控台
├── users.html           # 用户画像分析
└── videos.html          # 视频打标管理
```

## License

MIT
