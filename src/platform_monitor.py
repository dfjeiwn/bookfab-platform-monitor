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
    official_url: Optional[str] = None  # 官方链接
    impact: Optional[str] = None  # 影响分析
    action: Optional[str] = None  # 建议行动
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


class PlatformLinkManager:
    """
    平台链接管理器
    根据不同更新类型返回对应的官方链接
    """

    # 各平台的链接模板配置
    LINK_TEMPLATES = {
        "Audible": {
            "homepage": "https://www.audible.com/",
            "app_store": "https://apps.apple.com/us/app/audible-audiobooks/id379693831",
            "play_store": "https://play.google.com/store/apps/details?id=com.audible.application",
            "release_notes": "https://www.audible.com/about/newsroom",
            "developer_blog": "https://developer.amazon.com/blogs/appstore",
        },
        "Piccoma": {
            "homepage": "https://piccoma.com/",
            "app_store": "https://apps.apple.com/jp/app/piccoma/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.piccoma.android",
            "release_notes": "https://piccoma.com/news/",
            "api_docs": "https://piccoma.com/help/",
        },
        "Kobo": {
            "homepage": "https://www.kobo.com/",
            "app_store": "https://apps.apple.com/us/app/kobo-books/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=com.kobobooks.android",
            "release_notes": "https://www.kobo.com/help",
        },
        "BookWalker": {
            "homepage": "https://bookwalker.jp/",
            "app_store": "https://apps.apple.com/jp/app/bookwalker/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.bookwalker.reader.viewer.android",
            "release_notes": "https://bookwalker.jp/info/",
        },
        "FANZA": {
            "homepage": "https://www.fanza.jp/",
            "security_center": "https://www.fanza.jp/help/",
            "api_docs": "https://www.fanza.jp/",
        },
        "DMM Books": {
            "homepage": "https://book.dmm.com/",
            "app_store": "https://apps.apple.com/jp/app/dmm-books/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=com.dmm.books.android",
            "release_notes": "https://book.dmm.com/info/",
        },
        "Audiobooks.com": {
            "homepage": "https://www.audiobooks.com/",
            "app_store": "https://apps.apple.com/us/app/audiobooks-com/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=com.audiobooks.androidapp",
            "release_notes": "https://www.audiobooks.com/blog",
        },
        "BookLive": {
            "homepage": "https://booklive.jp/",
            "app_store": "https://apps.apple.com/jp/app/booklive/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.booklive.reader",
            "release_notes": "https://booklive.jp/info/",
        },
        "ChirpBooks": {
            "homepage": "https://www.chirpbooks.com/",
            "app_store": "https://apps.apple.com/us/app/chirp-audiobooks/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=com.chirp.books",
            "release_notes": "https://www.chirpbooks.com/blog",
        },
        "Readly": {
            "homepage": "https://us.readly.com/",
            "app_store": "https://apps.apple.com/us/app/readly-magazines/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=com.readly.android",
            "release_notes": "https://us.readly.com/news/",
        },
        "楽天マガジン": {
            "homepage": "https://magazine.rakuten.co.jp/",
            "app_store": "https://apps.apple.com/jp/app/rakuten-magazine/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.co.rakuten.kobo",
            "release_notes": "https://magazine.rakuten.co.jp/news/",
        },
        "Cモア": {
            "homepage": "https://www.cmoa.jp/",
            "app_store": "https://apps.apple.com/jp/app/cmoa/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.co.cmoa",
            "release_notes": "https://www.cmoa.jp/info/",
        },
        "ebookJapan": {
            "homepage": "https://ebookjapan.yahoo.co.jp/",
            "app_store": "https://apps.apple.com/jp/app/ebookjapan/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.co.yahoo.android.ebookjapan",
            "release_notes": "https://ebookjapan.yahoo.co.jp/info/",
        },
        "AudiobookJP": {
            "homepage": "https://audiobook.jp/",
            "app_store": "https://apps.apple.com/jp/app/audiobook-jp/idxxx",
            "play_store": "https://play.google.com/store/apps/details?id=jp.co.audiobook",
            "release_notes": "https://audiobook.jp/news/",
        },
    }

    @classmethod
    def get_link(cls, platform_name: str, update_type: UpdateType, details: str = "") -> str:
        """
        根据平台名称和更新类型获取对应的官方链接

        Args:
            platform_name: 平台名称
            update_type: 更新类型
            details: 更新详情（用于判断 iOS/Android）

        Returns:
            对应的官方链接
        """
        templates = cls.LINK_TEMPLATES.get(platform_name, {})

        # 根据更新类型返回对应的链接
        if update_type == UpdateType.NEW_VERSION:
            # 判断是 iOS 还是 Android 更新
            if "iOS" in details or "App Store" in details:
                return templates.get("app_store", templates.get("homepage", ""))
            elif "Android" in details or "Play Store" in details:
                return templates.get("play_store", templates.get("homepage", ""))
            else:
                return templates.get("release_notes", templates.get("homepage", ""))

        elif update_type == UpdateType.NEW_ENCRYPTION:
            # 加密变更优先返回开发者博客或帮助中心
            return templates.get("developer_blog", templates.get("homepage", ""))

        elif update_type == UpdateType.API_CHANGE:
            # API 变更返回 API 文档或帮助中心
            return templates.get("api_docs", templates.get("homepage", ""))

        elif update_type == UpdateType.SECURITY_ALERT:
            # 安全告警返回安全中心或帮助中心
            return templates.get("security_center", templates.get("homepage", ""))

        # 默认返回首页
        return templates.get("homepage", "")


class MockPlatformMonitor(BasePlatformMonitor):
    """
    模拟平台监控器
    用于演示和测试，随机生成一些更新数据
    """

    # 模拟的更新场景（不再硬编码链接，由 PlatformLinkManager 动态获取）
    MOCK_SCENARIOS = {
        "Audible": [
            {
                "type": UpdateType.NEW_ENCRYPTION,
                "details": "检测到 AAXC 加密格式更新",
                "priority": Priority.HIGH,
                "impact": "可能导致现有解密工具失效，用户无法下载有声书",
                "action": "开发团队需在一周内调研新加密算法，评估解密方案"
            },
            {
                "type": UpdateType.NEW_VERSION,
                "details": "iOS App v5.12.0 发布",
                "priority": Priority.MEDIUM,
                "impact": "可能影响内置浏览器的兼容性",
                "action": "QA团队测试新版本在内置浏览器的运行情况"
            },
        ],
        "Piccoma": [
            {
                "type": UpdateType.NEW_VERSION,
                "details": "Android v3.45.0 发布",
                "priority": Priority.MEDIUM,
                "impact": "可能影响图片加载和下载功能",
                "action": "监控用户反馈，如有问题优先处理"
            },
            {
                "type": UpdateType.API_CHANGE,
                "details": "图片加载接口变更",
                "priority": Priority.HIGH,
                "impact": "图片下载功能可能失效，影响核心用户体验",
                "action": "研发部门需立即跟进，评估接口变更影响范围"
            },
        ],
        "Kobo": [
            {
                "type": UpdateType.NEW_VERSION,
                "details": "Desktop App v4.8.0 发布",
                "priority": Priority.MEDIUM,
                "impact": "桌面客户端更新，可能影响本地文件读取",
                "action": "验证新版本是否影响现有转换器功能"
            },
        ],
        "BookWalker": [
            {
                "type": UpdateType.NEW_ENCRYPTION,
                "details": "EPUB 加密算法升级",
                "priority": Priority.HIGH,
                "impact": "EPUB文件解密可能失败，影响用户正常使用",
                "action": "技术团队紧急评估，需在3天内给出解决方案"
            },
        ],
        "FANZA": [
            {
                "type": UpdateType.SECURITY_ALERT,
                "details": "登录验证流程变更",
                "priority": Priority.HIGH,
                "impact": "内置浏览器登录可能失败，影响用户获取书库",
                "action": "紧急修复登录模块，确保用户正常访问"
            },
        ],
        "DMM Books": [
            {
                "type": UpdateType.API_CHANGE,
                "details": "书库 API 响应格式变更",
                "priority": Priority.MEDIUM,
                "impact": "书库列表获取可能异常",
                "action": "适配新API格式，确保书库正常显示"
            },
        ],
    }

    def check_updates(self) -> List[PlatformUpdate]:
        """模拟检查更新，随机返回一些更新（使用 PlatformLinkManager 获取链接）"""
        updates = []

        # 30% 概率产生更新
        if random.random() < 0.3:
            scenarios = self.MOCK_SCENARIOS.get(self.name, [])
            if scenarios:
                # 随机选择1-2个更新
                selected = random.sample(scenarios, min(random.randint(1, 2), len(scenarios)))
                for scenario in selected:
                    # 使用 PlatformLinkManager 动态获取官方链接
                    official_url = PlatformLinkManager.get_link(
                        self.name, scenario["type"], scenario["details"]
                    )

                    updates.append(PlatformUpdate(
                        platform=self.name,
                        update_type=scenario["type"],
                        details=scenario["details"],
                        priority=scenario["priority"],
                        timestamp=datetime.now(),
                        official_url=official_url,
                        impact=scenario.get("impact"),
                        action=scenario.get("action")
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
                "time": update.timestamp.strftime("%H:%M"),
                "official_url": update.official_url,
                "impact": update.impact,
                "action": update.action
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
