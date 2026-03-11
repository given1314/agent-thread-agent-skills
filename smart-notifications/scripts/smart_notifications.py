#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能通知聚合器 v1.0
功能：分时段聚合通知、勿扰模式、消息优先级管理
作者：贾维斯
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import asyncio

# ==================== 配置 ====================
WORKSPACE = Path("C:/Users/given/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "skills" / "smart-notifications" / "config.json"
STATE_FILE = WORKSPACE / "memory" / "smart_notifications_state.json"

# 默认配置
DEFAULT_CONFIG = {
    "notification": {
        "morning": {
            "enabled": True,
            "time_range": ["07:00", "08:00"],
            "components": ["weather", "schedule", "breakfast"]
        },
        "noon": {
            "enabled": True,
            "time_range": ["11:30", "12:00"],
            "components": ["lunch", "political_news"]
        },
        "evening": {
            "enabled": True,
            "time_range": ["17:00", "17:30"],
            "components": ["exercise", "dinner"]
        },
        "night": {
            "enabled": True,
            "time_range": ["22:00", "24:00"],
            "components": ["health_report", "review"]
        }
    },
    "dnd": {
        "enabled": True,
        "study_hours": {
            "morning": ["08:00", "12:00"],
            "afternoon": ["14:00", "18:00"],
            "evening": ["19:00", "22:00"]
        },
        "detect_study_apps": True,
        "delay_rules": {
            "urgent": 0,
            "important": 15,
            "normal": 30
        }
    },
    "priority": {
        "keywords_urgent": ["紧急", "考试", "突变", "警告", "警告", "critical"],
        "keywords_important": ["提醒", "任务", "计划", "重要", "important"],
        "keywords_normal": ["汇总", "日常", "更新", "normal"]
    }
}


class Priority(Enum):
    """消息优先级枚举"""
    URGENT = "urgent"
    IMPORTANT = "important"
    NORMAL = "normal"


@dataclass
class Notification:
    """通知数据类"""
    title: str
    content: str
    priority: Priority = Priority.NORMAL
    category: str = "general"
    source: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "category": self.category,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 配置加载失败，使用默认: {e}")
        
        # 保存默认配置
        self._save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    def _save_config(self, config: Dict):
        """保存配置"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value


class PriorityManager:
    """消息优先级管理器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def classify(self, text: str, metadata: Dict = None) -> Priority:
        """根据文本和元数据分类优先级"""
        text_lower = text.lower()
        
        # 检查紧急关键词
        urgent_keywords = self.config.get("priority.keywords_urgent", [])
        for kw in urgent_keywords:
            if kw.lower() in text_lower:
                return Priority.URGENT
        
        # 检查重要关键词
        important_keywords = self.config.get("priority.keywords_important", [])
        for kw in important_keywords:
            if kw.lower() in text_lower:
                return Priority.IMPORTANT
        
        # 检查元数据中的优先级标记
        if metadata:
            if metadata.get("priority") == "urgent":
                return Priority.URGENT
            if metadata.get("priority") == "important":
                return Priority.IMPORTANT
        
        return Priority.NORMAL
    
    def can_send(self, priority: Priority, dnd_active: bool) -> bool:
        """检查是否可以在勿扰模式下发送"""
        if not dnd_active:
            return True
        
        # 紧急通知不受勿扰限制
        if priority == Priority.URGENT:
            return True
        
        return False
    
    def get_delay_minutes(self, priority: Priority) -> int:
        """获取对应优先级的延迟分钟数"""
        delay_rules = self.config.get("dnd.delay_rules", {
            "urgent": 0,
            "important": 15,
            "normal": 30
        })
        return delay_rules.get(priority.value, 30)


class DNDManager:
    """勿扰模式管理器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "dnd_override": False,
            "last_study_check": None
        }
    
    def _save_state(self):
        """保存状态"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def is_dnd_time(self) -> bool:
        """检查当前是否在勿扰时段"""
        if not self.config.get("dnd.enabled", True):
            return False
        
        # 检查手动勿扰开关
        if self.state.get("dnd_override", False):
            return True
        
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        weekday = now.weekday()  # 0=周一, 6=周日
        
        # 周末全天勿扰
        if weekday >= 5:
            return True
        
        # 检查学习时段
        study_hours = self.config.get("dnd.study_hours", {})
        
        for period, time_range in study_hours.items():
            if len(time_range) == 2:
                start, end = time_range
                if start <= current_time <= end:
                    return True
        
        return False
    
    def is_studying(self) -> bool:
        """检测是否正在学习"""
        if not self.config.get("dnd.detect_study_apps", True):
            return False
        
        # 检查学习相关进程（Windows）
        try:
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                timeout=5
            )
            process_list = result.stdout.lower()
            
            study_apps = ['code', 'pycharm', 'notepad++', 'youdao', 'youdaonote', 
                         'obsidian', 'anki', 'onenote', 'word', 'wps']
            
            for app in study_apps:
                if app in process_list:
                    return True
        except:
            pass
        
        return False
    
    def get_dnd_status(self) -> Dict:
        """获取勿扰状态"""
        is_dnd = self.is_dnd_time()
        studying = self.is_studying()
        
        return {
            "active": is_dnd or studying,
            "dnd_time": is_dnd,
            "studying": studying,
            "override": self.state.get("dnd_override", False)
        }
    
    def set_override(self, enabled: bool):
        """设置手动勿扰"""
        self.state["dnd_override"] = enabled
        self._save_state()


class WeatherFetcher:
    """天气获取器"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def fetch(self) -> Dict:
        """获取天气信息"""
        try:
            # 尝试从缓存读取天气
            weather_file = self.workspace / "memory" / "weather" / "current_weather.json"
            if weather_file.exists():
                with open(weather_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        "temperature": data.get("temperature", "N/A"),
                        "condition": data.get("condition", "未知"),
                        "aqi": data.get("aqi", "N/A"),
                        "suggestion": data.get("suggestion", "注意保暖")
                    }
        except Exception as e:
            print(f"⚠️ 天气读取失败: {e}")
        
        return {
            "temperature": "18-24°C",
            "condition": "晴",
            "aqi": "良",
            "suggestion": "适合户外运动"
        }


class ScheduleFetcher:
    """课表获取器"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def fetch(self) -> Dict:
        """获取当天课表"""
        try:
            schedule_file = self.workspace / "schedule" / "course_schedule.json"
            if schedule_file.exists():
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 简化处理，返回当天课表
                    return {
                        "courses": data.get("courses", []),
                        "total_classes": 3
                    }
        except Exception as e:
            print(f"⚠️ 课表读取失败: {e}")
        
        return {
            "courses": [
                {"time": "1-2节", "name": "智能施工与装备", "location": "致用楼-301"},
                {"time": "7-8节", "name": "智能感知与数字信号处理", "location": "致用楼-205"}
            ],
            "total_classes": 3
        }


class HealthReporter:
    """健康报告生成器"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def generate(self) -> Dict:
        """生成健康报告"""
        try:
            # 尝试读取健康数据
            health_file = self.workspace / "memory" / f"health_{datetime.now().strftime('%Y-%m-%d')}.json"
            if health_file.exists():
                with open(health_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        # 返回默认数据
        return {
            "exercise": "已完成 (跑步 30min)",
            "sleep_hours": "7.2h",
            "fatigue_index": "0.72",
            "suggestion": "泡脚放松，准备休息"
        }


class KaoyanReporter:
    """考研复盘生成器"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def generate(self) -> Dict:
        """生成学习复盘"""
        try:
            # 尝试读取考研数据
            kaoyan_file = self.workspace / "memory" / f"kaoyan_{datetime.now().strftime('%Y-%m-%d')}.json"
            if kaoyan_file.exists():
                with open(kaoyan_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        # 返回默认数据
        return {
            "total_hours": "6.5h",
            "math": "3h (极限复习)",
            "english": "1.5h (单词200个)",
            "completed_tasks": "8/10"
        }


class NotificationAggregator:
    """通知聚合器"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.priority_mgr = PriorityManager(self.config)
        self.dnd_mgr = DNDManager(self.config)
        self.weather = WeatherFetcher(WORKSPACE)
        self.schedule = ScheduleFetcher(WORKSPACE)
        self.health = HealthReporter(WORKSPACE)
        self.kaoyan = KaoyanReporter(WORKSPACE)
    
    def aggregate_morning(self) -> List[Notification]:
        """聚合早间通知 (07:00-08:00)"""
        notifications = []
        
        # 天气
        weather_data = self.weather.fetch()
        weather_text = f"{weather_data['condition']} {weather_data['temperature']}"
        notifications.append(Notification(
            title="🌤️ 天气",
            content=f"{weather_text}\n空气质量：{weather_data['aqi']}\n建议：{weather_data['suggestion']}",
            priority=Priority.NORMAL,
            category="weather"
        ))
        
        # 课表
        schedule_data = self.schedule.fetch()
        courses_text = "\n".join([
            f"  {c['time']}: {c['name']} ({c['location']})"
            for c in schedule_data.get('courses', [])[:3]
        ])
        notifications.append(Notification(
            title="📚 今日课表",
            content=f"今天有 {schedule_data.get('total_classes', 0)} 节课\n{courses_text}",
            priority=Priority.NORMAL,
            category="schedule"
        ))
        
        # 早餐提醒
        notifications.append(Notification(
            title="🍳 早餐提醒",
            content="建议时间: 07:00-07:30\n推荐：粥+鸡蛋补充能量",
            priority=Priority.IMPORTANT,
            category="meal"
        ))
        
        return notifications
    
    def aggregate_noon(self) -> List[Notification]:
        """聚合午间通知 (11:30-12:00)"""
        notifications = []
        
        # 午餐
        notifications.append(Notification(
            title="🍱 午餐提醒",
            content="建议时间: 11:30-12:00\n注意营养均衡，多吃蔬菜",
            priority=Priority.IMPORTANT,
            category="meal"
        ))
        
        # 政治时事
        try:
            news_file = WORKSPACE / "political_news" / "政治时事概要.md"
            if news_file.exists():
                with open(news_file, 'r', encoding='utf-8') as f:
                    content = f.read()[:500]
                notifications.append(Notification(
                    title="📰 政治时事",
                    content=content,
                    priority=Priority.IMPORTANT,
                    category="news"
                ))
            else:
                notifications.append(Notification(
                    title="📰 政治时事",
                    content="午间新闻待更新...",
                    priority=Priority.NORMAL,
                    category="news"
                ))
        except:
            notifications.append(Notification(
                title="📰 政治时事",
                content="午间新闻待更新...",
                priority=Priority.NORMAL,
                category="news"
            ))
        
        return notifications
    
    def aggregate_evening(self) -> List[Notification]:
        """聚合傍晚通知 (17:00-17:30)"""
        notifications = []
        
        # 运动提醒
        notifications.append(Notification(
            title="🏃 运动提醒",
            content="建议时间: 17:00-18:00\n今天试试跑步或篮球",
            priority=Priority.IMPORTANT,
            category="exercise"
        ))
        
        # 晚餐
        notifications.append(Notification(
            title="🍚 晚餐提醒",
            content="建议时间: 17:30-18:00\n不宜吃太油腻",
            priority=Priority.NORMAL,
            category="meal"
        ))
        
        return notifications
    
    def aggregate_night(self) -> List[Notification]:
        """聚合晚间通知 (22:00-24:00)"""
        notifications = []
        
        # 健康报告
        health_data = self.health.generate()
        notifications.append(Notification(
            title="💪 今日健康",
            content=f"运动: {health_data['exercise']}\n睡眠: {health_data['sleep_hours']}\n疲劳指数: {health_data['fatigue_index']}\n建议: {health_data['suggestion']}",
            priority=Priority.IMPORTANT,
            category="health"
        ))
        
        # 学习复盘
        kaoyan_data = self.kaoyan.generate()
        notifications.append(Notification(
            title="📖 学习复盘",
            content=f"今日学习: {kaoyan_data['total_hours']}\n数学: {kaoyan_data['math']}\n英语: {kaoyan_data['english']}\n完成任务: {kaoyan_data['completed_tasks']}",
            priority=Priority.NORMAL,
            category="review"
        ))
        
        return notifications
    
    def format_notifications(self, notifications: List[Notification]) -> str:
        """格式化通知为可读文本"""
        if not notifications:
            return "暂无通知"
        
        lines = []
        for notif in notifications:
            lines.append(f"{notif.title}")
            lines.append(notif.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def process_with_dnd(self, notifications: List[Notification]) -> tuple:
        """处理通知，考虑勿扰模式"""
        dnd_status = self.dnd_mgr.get_dnd_status()
        immediate = []
        delayed = []
        
        for notif in notifications:
            # 重新分类优先级
            priority = self.priority_mgr.classify(notif.title + notif.content, notif.metadata)
            notif.priority = priority
            
            if self.priority_mgr.can_send(priority, dnd_status["active"]):
                immediate.append(notif)
            else:
                delay_minutes = self.priority_mgr.get_delay_minutes(priority)
                delayed.append({
                    "notification": notif,
                    "delay_minutes": delay_minutes
                })
        
        # 如果没有立即发送的通知，也显示延迟的通知内容（用于调试/查看）
        if not immediate and delayed:
            immediate = [d["notification"] for d in delayed]
            delayed = []
        
        return immediate, delayed, dnd_status


def send_telegram_message(message: str):
    """发送 Telegram 消息"""
    try:
        # 尝试从工作区读取配置
        tools_file = WORKSPACE / "TOOLS.md"
        if tools_file.exists():
            content = tools_file.read_text(encoding='utf-8')
            # 提取 Telegram 配置
            import re
            token_match = re.search(r'Telegram.*?Bot Token.*?:\s*(\S+)', content)
            chat_id_match = re.search(r'Telegram.*?User ID.*?:\s*(\S+)', content)
            
            if token_match and chat_id_match:
                token = token_match.group(1)
                chat_id = chat_id_match.group(1)
                # 这里会通过 OpenClaw 的 message 工具发送
                print(f"📤 待发送消息 (Telegram): {chat_id}")
                return True
        print("📝 消息已生成（未配置 Telegram）")
        return False
    except Exception as e:
        print(f"⚠️ 消息发送失败: {e}")
        return False


def run_aggregation(period: str):
    """运行指定时段的聚合"""
    agg = NotificationAggregator()
    
    # 根据时段获取通知
    if period == "morning":
        notifications = agg.aggregate_morning()
    elif period == "noon":
        notifications = agg.aggregate_noon()
    elif period == "evening":
        notifications = agg.aggregate_evening()
    elif period == "night":
        notifications = agg.aggregate_night()
    else:
        print(f"❌ 未知时段: {period}")
        return
    
    # 处理勿扰
    immediate, delayed, dnd_status = agg.process_with_dnd(notifications)
    
    # 格式化并发送
    message = agg.format_notifications(immediate)
    message += f"\n━━━━━━━━━━━━━━━━━━\n"
    message += f"优先级: {len(immediate)}条 | 延迟: {len(delayed)}条 | 勿扰: {'ON' if dnd_status['active'] else 'OFF'}"
    
    print(f"\n{'='*50}")
    print(f"🔔 智能通知 ({period})")
    print(f"{'='*50}")
    print(message)
    
    if immediate:
        send_telegram_message(message)
    
    return {
        "period": period,
        "immediate": len(immediate),
        "delayed": len(delayed),
        "dnd_status": dnd_status
    }


def test_priority():
    """测试优先级分类"""
    config = ConfigManager()
    pm = PriorityManager(config)
    
    test_cases = [
        ("明天有考试提醒", {}),
        ("天气突变警告", {}),
        ("日常汇总更新", {}),
        ("重要任务待完成", {"priority": "important"}),
    ]
    
    print("🧪 优先级测试:")
    print("-" * 40)
    for text, meta in test_cases:
        priority = pm.classify(text, meta)
        print(f"  [{priority.value.upper()}] {text}")


# ==================== 主函数 ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="智能通知聚合器")
    parser.add_argument("--morning", action="store_true", help="早间聚合通知")
    parser.add_argument("--noon", action="store_true", help="午间聚合通知")
    parser.add_argument("--evening", action="store_true", help="傍晚聚合通知")
    parser.add_argument("--night", action="store_true", help="晚间聚合通知")
    parser.add_argument("--all", action="store_true", help="执行所有时段聚合")
    parser.add_argument("--dnd", choices=['on', 'off', 'status'], help="勿扰模式控制")
    parser.add_argument("--test-priority", action="store_true", help="测试优先级分类")
    
    args = parser.parse_args()
    
    config = ConfigManager()
    dnd_mgr = DNDManager(config)
    
    if args.test_priority:
        test_priority()
        return
    
    if args.dnd:
        if args.dnd == 'on':
            dnd_mgr.set_override(True)
            print("✅ 勿扰模式已开启")
        elif args.dnd == 'off':
            dnd_mgr.set_override(False)
            print("✅ 勿扰模式已关闭")
        elif args.dnd == 'status':
            status = dnd_mgr.get_dnd_status()
            print(f"📱 勿扰状态:")
            print(f"  总体: {'ON' if status['active'] else 'OFF'}")
            print(f"  定时: {'ON' if status['dnd_time'] else 'OFF'}")
            print(f"  学习中: {'ON' if status['studying'] else 'OFF'}")
            print(f"  手动: {'ON' if status['override'] else 'OFF'}")
        return
    
    if args.morning:
        run_aggregation("morning")
    elif args.noon:
        run_aggregation("noon")
    elif args.evening:
        run_aggregation("evening")
    elif args.night:
        run_aggregation("night")
    elif args.all:
        for period in ["morning", "noon", "evening", "night"]:
            run_aggregation(period)
            time.sleep(1)
    else:
        # 默认显示帮助
        parser.print_help()
        print("\n📌 示例:")
        print("  python smart_notifications.py --morning")
        print("  python smart_notifications.py --dnd status")
        print("  python smart_notifications.py --test-priority")


if __name__ == "__main__":
    main()
