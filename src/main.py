#!/usr/bin/env python3
"""
BookFab 平台监控机器人主程序
"""
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from loguru import logger

from feishu_bot import FeishuBot
from platform_monitor import PlatformMonitorManager, format_updates_for_feishu


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    # 尝试多个路径
    paths = [
        config_path,
        Path("config/config.yaml"),
        Path("../config/config.yaml"),
    ]

    for path in paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    raise FileNotFoundError("找不到配置文件 config/config.yaml")


def setup_logging():
    """设置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def run_daily_push():
    """执行每日推送"""
    logger.info("=" * 50)
    logger.info("开始执行平台监控推送任务")
    logger.info("=" * 50)

    try:
        # 加载配置
        config = load_config()

        # 初始化飞书机器人
        bot = FeishuBot(
            webhook_url=config["feishu"]["webhook_url"],
            secret=config["feishu"].get("secret")
        )

        # 初始化平台监控
        manager = PlatformMonitorManager.create_from_config(config)

        # 检查更新
        logger.info("开始检查各平台更新...")
        updates = manager.check_all_updates()

        # 获取状态正常的平台
        no_updates = manager.get_platforms_without_updates(updates)

        # 格式化更新数据
        formatted_updates = format_updates_for_feishu(updates)

        # 判断是否@所有人（高优先级更新时）
        has_high_priority = any(
            u["priority"] == "high" for u in formatted_updates
        )
        at_all = has_high_priority and config.get("message", {}).get("at_all_on_high_priority", True)

        # 发送消息
        today = datetime.now().strftime("%Y-%m-%d")

        if formatted_updates or config.get("message", {}).get("show_no_update", False):
            result = bot.send_platform_update_card(
                date=today,
                updates=formatted_updates,
                no_updates=no_updates if config.get("message", {}).get("show_no_update", False) else None,
                at_all=at_all
            )

            if result:
                logger.success(f"推送成功！共 {len(formatted_updates)} 个更新")
            else:
                logger.error("推送失败")
                return False
        else:
            logger.info("今日无更新，跳过推送")

        return True

    except Exception as e:
        logger.exception(f"推送任务执行失败: {e}")
        return False


def main():
    """主函数"""
    setup_logging()

    # 检查是否在 GitHub Actions 环境
    if os.environ.get("GITHUB_ACTIONS"):
        logger.info("运行在 GitHub Actions 环境")

    # 执行推送
    success = run_daily_push()

    # 根据结果退出
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
