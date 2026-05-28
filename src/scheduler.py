#!/usr/bin/env python3
"""
定时任务调度器
在本地或服务器上持续运行，每天自动推送
"""
import time
import signal
import sys
from datetime import datetime
from loguru import logger
import yaml
from pathlib import Path

import schedule

from main import run_daily_push, setup_logging


class Scheduler:
    """定时任务调度器"""

    def __init__(self, push_time: str = "10:00"):
        self.push_time = push_time
        self.running = False

        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info("收到退出信号，正在停止调度器...")
        self.running = False

    def _job(self):
        """执行推送任务"""
        logger.info(f"执行定时任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        run_daily_push()

    def start(self):
        """启动调度器"""
        logger.info(f"启动定时调度器，每天 {self.push_time} 推送")

        # 添加定时任务
        schedule.every().day.at(self.push_time).do(self._job)

        self.running = True

        # 主循环
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

        logger.info("调度器已停止")


def load_push_time():
    """从配置加载推送时间"""
    try:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("schedule", {}).get("push_time", "10:00")
    except Exception as e:
        logger.warning(f"加载配置失败，使用默认时间: {e}")
        return "10:00"


def main():
    """主函数"""
    setup_logging()

    # 加载推送时间
    push_time = load_push_time()

    # 创建并启动调度器
    scheduler = Scheduler(push_time=push_time)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
        sys.exit(0)


if __name__ == "__main__":
    main()
