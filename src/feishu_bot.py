"""
飞书机器人消息推送模块
支持：文本消息、富文本消息、交互式卡片消息
"""
import json
import base64
import hashlib
import hmac
import re
import time
from urllib.parse import urlparse

import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


_EMOJI_PREFIX_RE = re.compile(
    r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+\s*"
)
_BULLET_SPLIT_RE = re.compile(r"[，、；;。\n]+")


def _strip_leading_emoji(text: str) -> str:
    """剥掉字符串开头的 emoji（如 '🔐 新加密方式' -> '新加密方式'）。"""
    if not text:
        return ""
    return _EMOJI_PREFIX_RE.sub("", text).strip()


def _split_to_bullets(text: Optional[str]) -> List[str]:
    """把单字符串按中英文标点切成多 bullet，过滤空白。"""
    if not text:
        return []
    parts = [p.strip() for p in _BULLET_SPLIT_RE.split(text)]
    return [p for p in parts if p]


def _domain_to_source_name(url: Optional[str]) -> str:
    """从 URL 推断来源名（audible.com -> Audible）；失败时回落到“官方网站”。"""
    if not url:
        return "官方网站"
    try:
        host = urlparse(url).netloc or url
    except Exception:
        return "官方网站"
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    label = host.split(".")[0] if host else ""
    if not label:
        return "官方网站"
    return label[:1].upper() + label[1:]


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

    _PRIORITY_GROUPS = [
        ("high", "🚨 高风险"),
        ("medium", "⚠️ 中风险"),
        ("low", "ℹ️ 低风险"),
    ]
    _PRIORITY_LABEL = {"high": "高风险", "medium": "中风险", "low": "低风险"}

    def _build_risk_block(self, update: Dict[str, Any]) -> str:
        """渲染单条风险的 lark_md 文本。"""
        platform = update.get("platform", "")
        details = update.get("details", "") or ""

        title = update.get("title") or details
        if not title:
            title = _strip_leading_emoji(update.get("type", "")) or "平台变更"

        # 影响 / 动作：优先 list 字段，否则把旧字符串按标点切 bullet
        impacts = update.get("impacts") or _split_to_bullets(update.get("impact"))
        actions = update.get("actions") or _split_to_bullets(update.get("action"))

        # 情报源：优先 list 字段；否则用 official_url + 域名推断
        sources = update.get("sources")
        if not sources and update.get("official_url"):
            sources = [{
                "name": _domain_to_source_name(update["official_url"]),
                "url": update["official_url"],
            }]

        lines = [f"**{platform} ｜ {title}**", ""]

        lines.append("**风险**")
        lines.append(details or "（无详细描述）")

        if impacts:
            lines.append("")
            lines.append("**可能影响**")
            lines.extend(f"- {item}" for item in impacts)

        if actions:
            lines.append("")
            lines.append("**建议动作**")
            lines.extend(f"- {item}" for item in actions)

        if sources:
            lines.append("")
            lines.append("**原始情报源**")
            for src in sources:
                name = (src.get("name") or "官方网站").strip()
                url = (src.get("url") or "").strip()
                if url:
                    lines.append(f"- [{name}]({url})")
                else:
                    lines.append(f"- {name}")

        return "\n".join(lines)

    def send_platform_update_card(
        self,
        date: str,
        updates: List[Dict],
        no_updates: List[str] = None,
        at_all: bool = False
    ) -> bool:
        """发送平台监控日报卡片（按风险等级分组 + 多小节）。"""

        elements: List[Dict[str, Any]] = []
        updates = updates or []
        no_updates = no_updates or []

        if at_all and any(u.get("priority") == "high" for u in updates):
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "<at user_id=\"all\">所有人</at>"},
            })

        # ========== 顶部概览 ==========
        total_platforms = len(updates) + len(no_updates)
        counts = {p: sum(1 for u in updates if u.get("priority") == p) for p in ("high", "medium", "low")}

        overview_lines = [
            f"今日监控平台：{total_platforms}",
            f"发现有效风险：{len(updates)}",
        ]
        breakdown = [
            f"{self._PRIORITY_LABEL[p]}：{counts[p]}"
            for p in ("high", "medium", "low") if counts[p] > 0
        ]
        if breakdown:
            overview_lines.append(" ｜ ".join(breakdown))

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(overview_lines)},
        })

        # ========== 风险分组 ==========
        rendered_any_group = False
        for priority, header_text in self._PRIORITY_GROUPS:
            group = [u for u in updates if u.get("priority") == priority]
            if not group:
                continue

            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**{header_text}**"},
            })

            for idx, update in enumerate(group):
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": self._build_risk_block(update)},
                })
                if idx < len(group) - 1:
                    elements.append({"tag": "hr"})
            rendered_any_group = True

        # ========== 状态正常 ==========
        if no_updates:
            elements.append({"tag": "hr"})
            preview = ", ".join(no_updates[:10])
            suffix = "..." if len(no_updates) > 10 else ""
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**状态正常（{len(no_updates)} 个）：** {preview}{suffix}",
                },
            })

        if not rendered_any_group and not no_updates:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "今日各平台均未检测到有效风险。"},
            })

        elements.append({
            "tag": "note",
            "elements": [
                {"tag": "plain_text", "content": "BookFab 平台监控 | 每日 10:00 自动推送"}
            ],
        })

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🤖 BookFab 平台监控日报 | {date}",
                },
                "template": "blue",
            },
            "elements": elements,
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

    # 高风险：使用新版 list 字段
    # 中风险：保留旧版单字符串字段，验证 fallback 路径
    test_updates = [
        {
            "platform": "Audible",
            "type": "🔐 新加密方式",
            "title": "AACX DRM 更新",
            "details": "检测到 AACX 文件结构变化，现有解密逻辑可能失效。",
            "priority": "high",
            "official_url": "https://www.audible.com/",
            "impacts": [
                "用户无法下载新购买有声书",
                "解密失败率上升",
                "BookFab Audible 模块稳定性下降",
            ],
            "actions": [
                "获取新版样本验证",
                "检查解密兼容性",
                "补充自动化回归测试",
            ],
            "sources": [
                {"name": "Reddit", "url": "https://reddit.com/r/audible/xxxxx"},
                {"name": "Audible", "url": "https://www.audible.com/"},
            ],
        },
        {
            "platform": "Piccoma",
            "type": "📱 客户端新版本",
            "details": "Android v3.45.0 发布",
            "priority": "medium",
            "official_url": "https://play.google.com/store/apps/details?id=jp.piccoma.android",
            "impact": "可能影响图片加载和下载功能，缩略图渲染或异常",
            "action": "监控用户反馈；如有问题优先处理；安排回归测试",
        },
    ]

    result = bot.send_platform_update_card(
        date=datetime.now().strftime("%Y-%m-%d"),
        updates=test_updates,
        no_updates=["Kobo", "FANZA", "DMM Books", "BookWalker"],
        at_all=True
    )

    print(f"发送结果: {result}")
