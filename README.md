# BookFab 平台监控飞书机器人

每天早上10点自动推送各大内容平台的客户端新版本和新加密发布信息。

## 监控平台列表 (14个)

### 高优先级
- FANZA - 成人漫画/小说/写真
- Audiobooks.com - 有声书
- DMM Books - 漫画/小说/写真/杂志
- Piccoma - 漫画/条漫
- Audible - 有声书
- Kobo - 电子书

### 中优先级
- BookLive - 漫画/小说/轻小说/杂志
- ChirpBooks - 有声书
- 楽天マガジン - 杂志期刊
- Cモア (Cmoa) - 漫画/小说
- BookWalker - 漫画/轻小说
- ebookJapan - 漫画/小说
- Readly - 杂志期刊

### 低优先级
- AudiobookJP - 有声书

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置飞书机器人

在 `config/config.yaml` 中配置：
- 飞书机器人的 Webhook URL
- 监控平台列表
- 推送时间设置

### 3. 运行

```bash
# 手动运行一次测试
python src/main.py

# 启动定时任务
python src/scheduler.py
```

## 部署方式

### 方式一：本地/服务器定时运行

使用 `scheduler.py` 启动守护进程，每天自动推送。

### 方式二：GitHub Actions (推荐)

使用 `.github/workflows/daily-push.yml` 配置定时任务，无需维护服务器。

### 方式三：Docker 部署

```bash
docker build -t bookfab-monitor .
docker run -d --name bookfab-monitor bookfab-monitor
```

## 数据来源

目前支持两种数据源：
1. **模拟数据** - 用于测试演示
2. **实际API** - 需要对接各平台的版本检测API

## 消息格式

推送消息包含：
- 📱 客户端新版本发布
- 🔐 新加密方式检测
- ⚠️ 异常告警
- 📊 平台状态汇总
