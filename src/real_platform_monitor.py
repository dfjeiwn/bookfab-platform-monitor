"""
真实平台监控示例
展示如何实现针对具体平台的版本检测
"""
import re
import json
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from platform_monitor import BasePlatformMonitor, PlatformUpdate, UpdateType, Priority


class AppStoreMonitor(BasePlatformMonitor):
    """
    App Store 应用版本监控
    通过 iTunes API 获取应用版本信息
    """

    def __init__(self, app_id: str, name: str, priority: Priority):
        super().__init__(name, "iOS App", priority)
        self.app_id = app_id
        self.cache_file = Path(f"cache/{name}_version.json")

    def _get_current_version(self) -> Optional[str]:
        """从 App Store 获取当前版本"""
        try:
            url = f"https://itunes.apple.com/lookup?id={self.app_id}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("resultCount", 0) > 0:
                return data["results"][0].get("version")
            return None
        except Exception as e:
            print(f"获取 {self.name} 版本失败: {e}")
            return None

    def _load_cached_version(self) -> Optional[str]:
        """加载缓存的版本"""
        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                data = json.load(f)
                return data.get("version")
        return None

    def _save_version(self, version: str):
        """保存版本到缓存"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump({
                "version": version,
                "checked_at": datetime.now().isoformat()
            }, f)

    def check_updates(self) -> List[PlatformUpdate]:
        """检查版本更新"""
        updates = []

        current = self._get_current_version()
        cached = self._load_cached_version()

        if current and cached and current != cached:
            updates.append(PlatformUpdate(
                platform=self.name,
                update_type=UpdateType.NEW_VERSION,
                details=f"iOS v{current} 已发布（上一版本: v{cached}）",
                priority=self.priority,
                timestamp=datetime.now()
            ))

        if current:
            self._save_version(current)

        return updates


class PlayStoreMonitor(BasePlatformMonitor):
    """
    Google Play Store 应用版本监控
    通过解析 Play Store 页面获取版本信息
    """

    def __init__(self, package_name: str, name: str, priority: Priority):
        super().__init__(name, "Android App", priority)
        self.package_name = package_name
        self.cache_file = Path(f"cache/{name}_android_version.json")

    def _get_current_version(self) -> Optional[str]:
        """从 Play Store 获取当前版本"""
        try:
            url = f"https://play.google.com/store/apps/details?id={self.package_name}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)

            # 解析版本号
            # 注意：Play Store 页面结构经常变化，需要根据实际情况调整
            pattern = r'\[\["([0-9]+\.[0-9]+\.[0-9]+)"\]\]'
            matches = re.findall(pattern, response.text)

            if matches:
                return matches[0]
            return None
        except Exception as e:
            print(f"获取 {self.name} Android 版本失败: {e}")
            return None

    def check_updates(self) -> List[PlatformUpdate]:
        """检查版本更新"""
        updates = []
        # 实现类似 AppStoreMonitor 的逻辑
        return updates


class WebsiteMonitor(BasePlatformMonitor):
    """
    网站变更监控
    检测网站内容变化，如加密方式、API 变更等
    """

    def __init__(
        self,
        name: str,
        url: str,
        priority: Priority,
        check_type: str = "website"
    ):
        super().__init__(name, check_type, priority)
        self.url = url
        self.cache_file = Path(f"cache/{name}_website.json")

    def _fetch_content(self) -> Optional[str]:
        """获取网站内容"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            return response.text
        except Exception as e:
            print(f"获取 {self.name} 网站内容失败: {e}")
            return None

    def _extract_key_info(self, content: str) -> Dict[str, Any]:
        """
        提取关键信息
        子类需要重写此方法来实现具体平台的检测逻辑
        """
        return {
            "hash": hash(content) % 10000000,
            "length": len(content)
        }

    def check_updates(self) -> List[PlatformUpdate]:
        """检查网站变更"""
        updates = []

        content = self._fetch_content()
        if not content:
            return updates

        current_info = self._extract_key_info(content)

        # 对比缓存信息
        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                cached_info = json.load(f)

            # 检测是否有显著变化
            if current_info != cached_info:
                # 这里需要更智能的变更分析
                updates.append(PlatformUpdate(
                    platform=self.name,
                    update_type=UpdateType.API_CHANGE,
                    details="检测到网站内容变化，建议人工确认",
                    priority=self.priority,
                    timestamp=datetime.now()
                ))

        # 保存当前信息
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(current_info, f)

        return updates


class AudibleMonitor(WebsiteMonitor):
    """Audible 平台专用监控"""

    def __init__(self):
        super().__init__(
            name="Audible",
            url="https://www.audible.com/",
            priority=Priority.HIGH,
            check_type="有声书平台"
        )

    def _extract_key_info(self, content: str) -> Dict[str, Any]:
        """提取 Audible 特有的关键信息"""
        info = super()._extract_key_info(content)

        # 检测 AAXC 加密相关关键词
        if "aaxc" in content.lower():
            info["has_aaxc"] = True

        # 检测 DRM 相关变更
        drm_patterns = ["drm", "encryption", "content_key", "license"]
        for pattern in drm_patterns:
            if pattern in content.lower():
                info[f"has_{pattern}"] = True

        return info


class PiccomaMonitor(WebsiteMonitor):
    """Piccoma 平台专用监控"""

    def __init__(self):
        super().__init__(
            name="Piccoma",
            url="https://piccoma.com/",
            priority=Priority.HIGH,
            check_type="漫画平台"
        )

    def _extract_key_info(self, content: str) -> Dict[str, Any]:
        """提取 Piccoma 特有的关键信息"""
        info = super()._extract_key_info(content)

        # 检测图片加载方式
        if "webp" in content.lower():
            info["image_format"] = "webp"
        elif "jpg" in content.lower() or "jpeg" in content.lower():
            info["image_format"] = "jpeg"

        return info


def create_real_monitors():
    """创建真实的监控器实例"""
    monitors = []

    # App Store 监控 (需要实际的 App ID)
    # monitors.append(AppStoreMonitor(
    #     app_id="1234567890",  # 替换为实际的 App ID
    #     name="Piccoma",
    #     priority=Priority.HIGH
    # ))

    # 网站监控
    monitors.append(AudibleMonitor())
    monitors.append(PiccomaMonitor())

    # 可以继续添加更多平台...

    return monitors


if __name__ == "__main__":
    """测试真实监控器"""
    print("测试真实平台监控器...")

    monitors = create_real_monitors()

    for monitor in monitors:
        print(f"\n检查 {monitor.name}...")
        updates = monitor.check_updates()

        if updates:
            for update in updates:
                print(f"  📢 {update.update_type.value}: {update.details}")
        else:
            print(f"  ✅ 无更新")
