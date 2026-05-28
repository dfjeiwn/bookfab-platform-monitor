"""
飞书机器人消息推送模块
支持：文本消息、富文本消息、交互式卡片消息
"""
import json
import base64
import hashlib
import hmac
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


class FeishuBot:
    """飞书群机器人封装"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def _gen_sign(self, timestamp: int) -> str:
        """生成签名（如果启用了签名验证）"""
        if not self.secret:
            return ""

        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

    def _send(self, payload: Dict[str, Any]) -> bool:
        """发送消息到飞书"""
        try:
            timestamp = int(time.time())
            sign = self._gen_sign(timestamp)

            if sign:
                payload["timestamp"] = timestamp
                payload["sign"] = sign

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            result = response.json()

            if result.get("code") == 0:
                logger.info("消息推送成功")
                return True
            else:
                logger.error(f"消息推送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    def send_text(self, text: str, at_all: bool = False) -> bool:
        """发送纯文本消息"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }

        if at_all:
            payload["content"]["text"] += "\n\n<at user_id=\"all\">所有人</at>"

        return self._send(payload)

    def send_rich_text(self, title: str, content: List[List[Dict]]) -> bool:
        """发送富文本消息

        Args:
            title: 消息标题
            content: 富文本内容，二维数组格式
        """
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content
                    }
                }
            }
        }
        return self._send(payload)

    def send_interactive_card(self, card_data: Dict[str, Any]) -> bool:
        """发送交互式卡片消息"""
        payload = {
            "msg_type": "interactive",
            "card": card_data
        }
        return self._send(payload)

    def send_platform_update_card(
        self,
        date: str,
        updates: List[Dict],
        no_updates: List[str] = None,
        at_all: bool = False
    ) -> bool:
        """发送平台更新卡片消息（简洁版）"""

        elements = []

        # @所有人（仅高优先级）
        if at_all and updates and any(u.get("priority") == "high" for u in updates):
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "<at user_id=\"all\">所有人</at>"
                }
            })

        # 简洁概览 - 只用文字，不用彩色圆圈
        if updates:
            high_count = sum(1 for u in updates if u.get("priority") == "high")
            medium_count = sum(1 for u in updates if u.get("priority") == "medium")
            low_count = sum(1 for u in updates if u.get("priority") == "low")

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**今日概览：** 高优先 {high_count} 项 | 中优先 {medium_count} 项 | 低优先 {low_count} 项"
                }
            })
            elements.append({"tag": "hr"})

        # 更新列表 - 使用结构化布局
        if updates:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**检测到变更的平台：**"
                }
            })

            for idx, update in enumerate(updates, 1):
                platform = update["platform"]
                update_type = update["type"]
                details = update["details"]
                priority = update.get("priority", "medium")
                official_url = update.get("official_url", "")
                impact = update.get("impact", "")
                action = update.get("action", "")

                # 优先级标签
                priority_label = {
                    "high": "[高]",
                    "medium": "[中]",
                    "low": "[低]"
                }.get(priority, "[中]")

                # 构建简洁的内容块
                content = f"**{idx}. {platform}** {priority_label}\n"
                content += f"类型：{update_type}\n"
                content += f"详情：{details}"

                if official_url:
                    content += f"\n[查看官网]({official_url})"

                if impact:
                    content += f"\n影响：{impact}"

                if action:
                    content += f"\n行动：{action}"

                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                })

                # 平台之间用细线分隔
                if idx < len(updates):
                    elements.append({
                        "tag": "hr",
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "---"
                        }
                    })

            elements.append({"tag": "hr"})

        # 总结 - 简洁文字
        if updates:
            high_count = sum(1 for u in updates if u.get("priority") == "high")
            if high_count > 0:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**提示：** 今日有 {high_count} 个高优先级变更，请相关团队尽快处理。"
                    }
                })

        # 无更新的平台（简化显示）
        if no_updates:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**状态正常：** {', '.join(no_updates[:10])}{'...' if len(no_updates) > 10 else ''}"
                }
            })

        # 页脚
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": "BookFab 平台监控 | 每日 10:00 自动推送"
                }
            ]
        })

        # 构建卡片 - 使用蓝色主题，简洁
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"BookFab 平台监控日报 ({date})"
                },
                "template": "blue"
            },
            "elements": elements
        }

        return self.send_interactive_card(card)


if __name__ == "__main__":
    # 测试代码
    import yaml

    with open("../config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    bot = FeishuBot(
        webhook_url=config["feishu"]["webhook_url"],
        secret=config["feishu"].get("secret")
    )

    # 测试发送更新卡片（增强版）
    test_updates = [
        {
            "platform": "Audible",
            "type": "🔐 新加密方式",
            "details": "检测到 AAXC 加密格式更新",
            "priority": "high",
            "official_url": "https://www.audible.com/",
            "impact": "可能导致现有解密工具失效，用户无法下载有声书",
            "action": "开发团队需在一周内调研新加密算法，评估解密方案"
        },
        {
            "platform": "Piccoma",
            "type": "📱 客户端新版本",
            "details": "Android v3.45.0 发布",
            "priority": "medium",
            "official_url": "https://play.google.com/store/apps/details?id=jp.piccoma.android",
            "impact": "可能影响图片加载和下载功能",
            "action": "监控用户反馈，如有问题优先处理"
        }
    ]

    result = bot.send_platform_update_card(
        date=datetime.now().strftime("%Y-%m-%d"),
        updates=test_updates,
        no_updates=["Kobo", "FANZA", "DMM Books", "BookWalker"],
        at_all=True
    )

    print(f"发送结果: {result}")
