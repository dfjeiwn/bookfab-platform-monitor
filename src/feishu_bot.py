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
        """发送平台更新卡片消息"""

        # 构建卡片元素
        elements = []

        # 标题
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📅 监控日期：** {date}"
            }
        })

        elements.append({"tag": "hr"})

        # 有更新的平台
        if updates:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🚨 检测到变更的平台**"
                }
            })

            for update in updates:
                platform = update["platform"]
                update_type = update["type"]
                details = update["details"]
                priority = update.get("priority", "medium")

                # 优先级标识
                priority_icon = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(priority, "⚪")

                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"{priority_icon} **{platform}**\n"
                            f"   类型：{update_type}\n"
                            f"   详情：{details}"
                        )
                    }
                })

            elements.append({"tag": "hr"})

        # 无更新的平台（可选显示）
        if no_updates:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**✅ 状态正常的平台（{len(no_updates)}个）**"
                }
            })

            # 分批显示，每行5个
            for i in range(0, len(no_updates), 5):
                batch = no_updates[i:i+5]
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": " • ".join(batch)
                    }
                })

        # 页脚
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": "🤖 BookFab 平台监控机器人 | 自动推送"
                }
            ]
        })

        # 构建卡片
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📚 BookFab 平台监控日报"
                },
                "template": "blue" if updates else "green"
            },
            "elements": elements
        }

        # @所有人
        if at_all and updates:
            elements.insert(0, {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "<at user_id=\"all\">所有人</at>"
                }
            })

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

    # 测试发送更新卡片
    test_updates = [
        {
            "platform": "Audible",
            "type": "🔐 新加密方式",
            "details": "检测到 AAXC 加密格式更新",
            "priority": "high"
        },
        {
            "platform": "Piccoma",
            "type": "📱 客户端新版本",
            "details": "Android v3.45.0 发布",
            "priority": "medium"
        }
    ]

    result = bot.send_platform_update_card(
        date=datetime.now().strftime("%Y-%m-%d"),
        updates=test_updates,
        no_updates=["Kobo", "FANZA", "DMM Books", "BookWalker"],
        at_all=True
    )

    print(f"发送结果: {result}")
