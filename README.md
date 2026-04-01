# AI Paper Daily

本地自动化 AI 论文每日总结（单页仪表盘 + 本地存储 + 10:00 自动触发 + 失败重试 + 桌面通知）。

## 功能
- 数据源可插拔：arXiv / Semantic Scholar / Hugging Face Papers（可扩展）
- 综合评分：引用、热度、讨论度、时效性
- 每日最多 10 篇
- 每篇输出中文：一句话结论、研究背景、问题定义、研究方法、效果与结果、方法亮点、局限、其他信息、入选理由
- 每篇独立导图：网页可展开/收起 + 每篇单独导出 `.xmind` / `.json`
- 失败自动重试 1 次，仍失败触发 macOS 桌面通知

## 部署到公网（推荐 Render）
适合不懂部署的情况：Render 提供网页服务和数据库，域名由平台自动分配。

### 需要知道的概念
- **域名**：访问地址。平台会给你一个默认地址（不需要自己买域名）。
- **数据库**：多人访问时用 Postgres，比本地 SQLite 稳定。

### Render 部署步骤（概览）
1. 把仓库推到 GitHub
2. 在 Render 新建 Web Service（Python）
3. 新建 Render Postgres，并把 `DATABASE_URL` 注入到 Web Service 环境变量
4. 新建 Render Cron Job，命令：`python -m app.main run-once`

> Render 的 Cron Job 通常使用 UTC 时间。北京时间 10:00 对应 UTC 02:00。

## 快速开始
```bash
cd ai-paper-daily
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

可选：在 `.env` 填 `SEMANTIC_SCHOLAR_API_KEY`，可显著降低 `429` 限流概率。

### 手动跑一次
```bash
python -m app.main run-once
```

### 启动网页
```bash
python -m app.main web
# 默认 http://127.0.0.1:8000
```

## 定时任务（macOS launchd）
1. 替换 `launchd/com.aipaper.daily.plist` 中的绝对路径
2. 加载任务：
```bash
launchctl unload ~/Library/LaunchAgents/com.aipaper.daily.plist 2>/dev/null || true
cp launchd/com.aipaper.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aipaper.daily.plist
```

## 目录
- `app/` 核心代码
- `outputs/daily/` 每日 JSON 输出
- `outputs/xmind/` 每日 XMind 文件
- `data/papers.db` SQLite
- `launchd/` 定时任务模板
