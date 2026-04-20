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

必要配置：
- 在 `.env` 中填写至少一个可用的 LLM provider，例如 `DOUBAO_API_KEY` + `DOUBAO_MODEL`
- `SEMANTIC_SCHOLAR_API_KEY` 可选，但能显著降低限流概率
- `DEDUPE_DAYS` 默认为 `7`，表示默认去重最近 7 天重复论文

## 本地使用
### 手动生成一次日报
```bash
python -m app.main run-once
```

### 启动网页服务
```bash
python -m app.main web
# 默认 http://127.0.0.1:8000
```

### 一键生成并打开网页
```bash
./scripts/force_refresh_open.sh
```

这个命令会：
- 先执行一次日报生成
- 确保本地网页服务可访问
- 自动打开当天页面，并带上当天日期参数，避免打开到错误日期或旧缓存

## 定时任务（macOS launchd）
项目包含两个 launchd 任务：
- `com.aipaper.daily.plist`：每天 10:00 生成日报
- `com.aipaper.web.plist`：保持本地网页服务常驻

加载方式：
```bash
launchctl unload ~/Library/LaunchAgents/com.aipaper.web.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.aipaper.daily.plist 2>/dev/null || true
cp launchd/com.aipaper.web.plist ~/Library/LaunchAgents/
cp launchd/com.aipaper.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aipaper.web.plist
launchctl load ~/Library/LaunchAgents/com.aipaper.daily.plist
```

## 常见问题
### 早上自动打开的页面为空
优先看日志：
```bash
tail -n 80 logs/daily-$(date +%Y%m%d).log
```

常见原因：
- 抓取源失败，导致当天没有论文数据
- LLM provider 未配置或调用失败

从当前实现开始，如果没有可用 LLM 或所有 LLM 都失败，任务会直接失败，不会再写入模板内容。

### 手动点通知打开的页面和自动打开不一致
当前已统一成按 URL 中的 `date` 参数打开当天页面。自动打开、点击通知、手动刷新都应指向同一天数据。

### 怎样确认今天的数据是否真的生成成功
```bash
cat logs/status.json
```

### 如何避免最近几天重复推到同一篇论文
在 `.env` 调整：
```bash
DEDUPE_DAYS=7
```
数值越大，跨天去重越严格。

## 目录
- `app/` 核心代码
- `outputs/daily/` 每日 JSON 输出
- `outputs/xmind/` 每日 XMind 文件
- `data/papers.db` SQLite
- `launchd/` 定时任务模板
