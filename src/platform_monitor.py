"""
平台监控模块
负责检测各平台的新版本和新加密发布
"""
import json
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from loguru import logger


class UpdateType(Enum):
    """更新类型"""
    NEW_VERSION = "📱 客户端新版本"
    NEW_ENCRYPTION = "🔐 新加密方式"
    API_CHANGE = "🔧 API接口变更"
    SECURITY_ALERT = "⚠️ 安全告警"


class Priority(Enum):
    """优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PlatformUpdate:
    """平台更新信息"""
    platform: str
    update_type: UpdateType
    details: str
    priority: Priority
    timestamp: datetime
    raw_data: Optional[Dict] = None


class BasePlatformMonitor(ABC):
    """平台监控基类"""

    def __init__(self, name: str, platform_type: str, priority: Priority):
        self.name = name
        self.platform_type = platform_type
        self.priority = priority

    @abstractmethod
    def check_updates(self) -> List[PlatformUpdate]:
        """检查平台更新，返回更新列表"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "platform": self.name,
            "type": self.platform_type,
            "priority": self.priority.value
        }


class MockPlatformMonitor(BasePlatformMonitor):
    """
    模拟平台监控器
    用于演示和测试，随机生成一些更新数据
    """

    # 模拟的更新场景
    MOCK_SCENARIOS = {
        "Audible": [
            (UpdateType.NEW_ENCRYPTION, "检测到 AAXC 加密格式更新", Priority.HIGH),
            (UpdateType.NEW_VERSION, "iOS App v5.12.0 发布", Priority.MEDIUM),
        ],
        "Piccoma": [
            (UpdateType.NEW_VERSION, "Android v3.45.0 发布", Priority.MEDIUM),
            (UpdateType.API_CHANGE, "图片加载接口变更", Priority.HIGH),
        ],
        "Kobo": [
            (UpdateType.NEW_VERSION, "Desktop App v4.8.0 发布", Priority.MEDIUM),
        ],
        "BookWalker": [
            (UpdateType.NEW_ENCRYPTION, "EPUB 加密算法升级", Priority.HIGH),
        ],
        "FANZA": [
            (UpdateType.SECURITY_ALERT, "登录验证流程变更", Priority.HIGH),
        ],
        "DMM Books": [
            (UpdateType.API_CHANGE, "书库 API 响应格式变更", Priority.MEDIUM),
        ],
    }

    def check_updates(self) -> List[PlatformUpdate]:
        """模拟检查更新，随机返回一些更新"""
        updates = []

        # 30% 概率产生更新
        if random.random() < 0.3:
            scenarios = self.MOCK_SCENARIOS.get(self.name, [])
            if scenarios:
                # 随机选择1-2个更新
                selected = random.sample(scenarios, min(random.randint(1, 2), len(scenarios)))
                for update_type, details, priority in selected:
                    updates.append(PlatformUpdate(
                        platform=self.name,
                        update_type=update_type,
                        details=details,
                        priority=priority,
                        timestamp=datetime.now()
                    ))

        return updates


class PlatformMonitorManager:
    """平台监控管理器"""

    def __init__(self):
        self.monitors: List[BasePlatformMonitor] = []

    def register_monitor(self, monitor: BasePlatformMonitor):
        """注册监控器"""
        self.monitors.append(monitor)
        logger.info(f"已注册监控器: {monitor.name}")

    def check_all_updates(self) -> Dict[str, List[PlatformUpdate]]:
        """检查所有平台更新"""
        results = {}

        for monitor in self.monitors:
            try:
                updates = monitor.check_updates()
                if updates:
                    results[monitor.name] = updates
                    logger.info(f"{monitor.name}: 检测到 {len(updates)} 个更新")
                else:
                    logger.info(f"{monitor.name}: 无更新")
            except Exception as e:
                logger.error(f"检查 {monitor.name} 更新失败: {e}")
                results[monitor.name] = []

        return results

    def get_platforms_without_updates(self, updates_dict: Dict) -> List[str]:
        """获取没有更新的平台列表"""
        all_platforms = [m.name for m in self.monitors]
        platforms_with_updates = set(updates_dict.keys())
        return [p for p in all_platforms if p not in platforms_with_updates]

    @classmethod
    def create_from_config(cls, config: Dict) -> "PlatformMonitorManager":
        """从配置创建监控管理器"""
        manager = cls()

        for platform_config in config.get("monitor", {}).get("platforms", []):
            if not platform_config.get("enabled", True):
                continue

            monitor = MockPlatformMonitor(
                name=platform_config["name"],
                platform_type=platform_config["type"],
                priority=Priority(platform_config.get("priority", "medium"))
            )
            manager.register_monitor(monitor)

        return manager


def format_updates_for_feishu(updates: Dict[str, List[PlatformUpdate]]) -> List[Dict]:
    """将更新数据格式化为飞书消息格式"""
    formatted = []

    for platform_name, platform_updates in updates.items():
        for update in platform_updates:
            formatted.append({
                "platform": update.platform,
                "type": update.update_type.value,
                "details": update.details,
                "priority": update.priority.value,
                "time": update.timestamp.strftime("%H:%M")
            })

    # 按优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    formatted.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return formatted


if __name__ == "__main__":
    # 测试代码
    import yaml

    with open("../config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    manager = PlatformMonitorManager.create_from_config(config)

    print(f"已注册 {len(manager.monitors)} 个监控器")
    print("开始检查更新...")

    updates = manager.check_all_updates()

    print(f"\n检测到更新的平台: {list(updates.keys())}")
    print(f"状态正常的平台: {manager.get_platforms_without_updates(updates)}")

    formatted = format_updates_for_feishu(updates)
    print(f"\n格式化后的更新数据:")
    for item in formatted:
        print(f"  - {item}")
