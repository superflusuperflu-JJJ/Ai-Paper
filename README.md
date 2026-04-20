# AI Paper Daily

AI Paper Daily 是一个本地运行的 AI 论文情报站。它会每天自动抓取高价值论文，按统一标准排序，生成中文结构化解读，并在单页仪表盘中展示当天与历史结果。

这个项目的目标不是“堆很多论文”，而是每天给出一份足够克制、足够好读、适合个人快速浏览的 AI 论文日报。

## 核心能力

- 多来源抓取：`arXiv`、`Semantic Scholar`、`Hugging Face Papers`
- 综合排序：结合引用、讨论热度、趋势热度和时效性
- 每日精选：默认最多 10 篇
- 中文解读：一句话结论、研究背景、问题定义、研究方法、效果与结果、方法亮点、局限、其他信息、入选理由
- 每篇独立导图：网页内可交互查看，同时导出 `.json` 与 `.xmind`
- 本地自动化：macOS `launchd` 每天 10:00 自动执行
- 失败提醒：任务失败后桌面通知提醒
- 严格质量约束：如果没有可用 LLM 或所有 LLM 调用失败，不会写入模板内容

## 适合谁

- 想每天快速了解 AI 论文动态的人
- 不想手动刷多个论文站点的人
- 想把论文摘要、筛选、存档、查看放到一个本地工具里的人

## 快速开始

### 1. 初始化环境

```bash
cd ai-paper-daily
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. 配置 `.env`

至少填写一个可用的 LLM provider。当前最常见的是：

```bash
DOUBAO_API_KEY=你的key
DOUBAO_MODEL=你的模型名
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

常用配置项：

- `DAILY_LIMIT=10`
- `MIN_SCORE=0.10`
- `DEDUPE_DAYS=7`
- `SEMANTIC_SCHOLAR_API_KEY=` 可选，但建议填写，能降低限流概率

## 本地使用

### 手动生成一次日报

```bash
python -m app.main run-once
```

### 启动网页服务

```bash
python -m app.main web
```

默认访问地址：

```text
http://127.0.0.1:8000
```

### 一键生成并打开网页

```bash
./scripts/force_refresh_open.sh
```

这个命令会按顺序完成三件事：

- 执行一次日报生成
- 确保本地网页服务可访问
- 自动打开当天页面，并带上当天日期参数，避免打开到错误日期或浏览器旧缓存

## 自动化运行

项目内置两个 macOS `launchd` 任务：

- `com.aipaper.daily.plist`：每天 10:00 执行一次日报生成
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

## 数据与输出

- `data/papers.db`：本地 SQLite 数据库
- `outputs/daily/`：每天的 JSON 结果
- `outputs/xmind/`：每天导出的 `.xmind`
- `logs/`：任务运行日志、状态信息

## 排序逻辑

综合评分由四部分组成：

```text
综合分 = 0.40 × 引用得分
      + 0.30 × 讨论热度
      + 0.25 × 趋势热度
      + 0.05 × 新鲜度
```

其中：

- 引用得分：引用数归一化
- 讨论热度：平台讨论信号
- 趋势热度：平台趋势信号
- 新鲜度：发布时间越近分越高

## 去重逻辑

项目默认会跳过最近几天已经出现过的标题，避免连续几天重复推送同一篇论文。

```bash
DEDUPE_DAYS=7
```

这个值越大，跨天去重越严格。

## 常见问题

### 早上自动打开的页面为空

先看日志：

```bash
tail -n 80 logs/daily-$(date +%Y%m%d).log
```

常见原因：

- 抓取源当时网络失败
- 上游接口限流或不可用
- LLM provider 未配置或调用失败

### 为什么今天没有内容，但昨天有

如果当天抓取失败，系统不会再用模板内容“假装成功”，而是保留真实状态。这样虽然可能出现空页面，但不会污染当天数据。

### 自动打开的页面和点击通知后打开的页面不一致

当前实现已经统一成按 URL 中的 `date` 参数加载指定日期。自动打开、点击通知、手动刷新应落到同一份当天数据。

### 如何确认今天任务是否成功

```bash
cat logs/status.json
```

### 想立刻重新生成当天结果

```bash
./scripts/force_refresh_open.sh
```

## 部署到公网

如果你后续想把它变成一个任何人都能访问的网站，推荐思路是：

1. 把代码推到 GitHub
2. 部署到 Render / Railway / 自有服务器
3. 使用远程数据库（例如 Postgres）
4. 使用定时任务执行 `python -m app.main run-once`

如果只是个人使用，本地版通常已经足够稳定，而且维护成本最低。
