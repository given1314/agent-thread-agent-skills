---
name: smart-notifications
version: 1.0.0
description: "智能通知聚合系统 - 分时段聚合通知、勿扰模式、消息优先级管理"
author: Jarvis
---

# Smart Notifications 📱🔔

**智能通知聚合系统 - 让通知更智能、更贴心**

---

## What This Skill Does

✅ **分时段聚合通知** — 智能整合早/午/晚/夜各时段的通知  
✅ **勿扰模式** — 检测学习状态，延迟非紧急通知  
✅ **消息优先级** — 紧急/重要/普通三级分类  
✅ **学习状态检测** — 基于时间、位置、活跃度判断  
✅ **通知去重** — 避免重复通知打扰  

---

## 功能详解

### 1. 分时段通知聚合

| 时段 | 时间范围 | 聚合内容 |
|------|----------|----------|
| 🌅 早上 | 07:00-08:00 | 天气 + 课表 + 早餐 |
| ☀️ 中午 | 11:30-12:00 | 午餐 + 政治时事 |
| 🌇 傍晚 | 17:00-17:30 | 运动 + 晚餐 |
| 🌙 晚上 | 22:00-24:00 | 健康报告 + 复盘 |

### 2. 消息优先级

| 优先级 | 标识 | 触发条件 | 勿扰模式 |
|--------|------|----------|----------|
| 🔴 紧急 | URGENT | 天气突变、重要提醒 | 不延迟 |
| 🟡 重要 | IMPORTANT | 定时任务、学习提醒 | 可延迟 |
| 🟢 普通 | NORMAL | 日常通知、汇总 | 延迟 |

### 3. 勿扰模式

**触发条件：**
- 检测到学习软件活跃（VS Code, PyCharm, 有道云笔记）
- 时间在专注时段（默认 8:00-12:00, 14:00-18:00, 19:00-22:00）
- 用户手动开启

**延迟策略：**
- 紧急通知：立即发送
- 重要通知：延迟 15 分钟后重试
- 普通通知：延迟 30 分钟后重试

---

## 快速开始

### 1. 配置触发器

在 `triggers/triggers.json` 中添加：

```json
{
  "id": "smart-notification-morning",
  "name": "智能早间通知",
  "type": "cron",
  "cron": "0 7 * * *",
  "timezone": "Asia/Shanghai",
  "enabled": true,
  "action": {
    "skill": "smart-notifications",
    "task": "morning_aggregation"
  }
}
```

### 2. 运行脚本

```bash
# 早间聚合
python scripts/smart_notifications.py --morning

# 午间聚合
python scripts/smart_notifications.py --noon

# 傍晚聚合
python scripts/smart_notifications.py --evening

# 晚间聚合
python scripts/smart_notifications.py --night

# 手动触发勿扰模式
python scripts/smart_notifications.py --dnd on
python scripts/smart_notifications.py --dnd off

# 测试优先级
python scripts/smart_notifications.py --test-priority
```

---

## 模块说明

### NotificationAggregator (通知聚合器)

```python
from smart_notifications import NotificationAggregator

agg = NotificationAggregator()

# 聚合早间通知
morning_news = agg.aggregate_morning()

# 聚合午间通知
noon_news = agg.aggregate_noon()

# 聚合傍晚通知
evening_news = agg.aggregate_evening()

# 聚合晚间通知
night_news = agg.aggregate_night()
```

### PriorityManager (优先级管理)

```python
from smart_notifications import PriorityManager

pm = PriorityManager()

# 设置消息优先级
priority = pm.classify("明天有考试", {"type": "reminder"})

# 检查是否可发送
can_send = pm.can_send(priority, dnd_active=True)
```

### DNDManager (勿扰模式)

```python
from smart_notifications import DNDManager

dnd = DNDManager()

# 检测是否在勿扰时段
is_dnd = dnd.is_dnd_time()

# 检测学习状态
is_studying = dnd.is_studying()

# 延迟通知
delayed = dnd.delay_notification(notification, delay_minutes=15)
```

---

## 配置项

### config.json

```json
{
  "notification": {
    "morning": {
      "enabled": true,
      "time_range": ["07:00", "08:00"],
      "components": ["weather", "schedule", "breakfast"]
    },
    "noon": {
      "enabled": true,
      "time_range": ["11:30", "12:00"],
      "components": ["lunch", "political_news"]
    },
    "evening": {
      "enabled": true,
      "time_range": ["17:00", "17:30"],
      "components": ["exercise", "dinner"]
    },
    "night": {
      "enabled": true,
      "time_range": ["22:00", "24:00"],
      "components": ["health_report", "review"]
    }
  },
  "dnd": {
    "enabled": true,
    "study_hours": {
      "morning": ["08:00", "12:00"],
      "afternoon": ["14:00", "18:00"],
      "evening": ["19:00", "22:00"]
    },
    "detect_study_apps": true,
    "delay_rules": {
      "urgent": 0,
      "important": 15,
      "normal": 30
    }
  },
  "priority": {
    "keywords_urgent": ["紧急", "考试", "突变", "警告"],
    "keywords_important": ["提醒", "任务", "计划", "重要"],
    "keywords_normal": ["汇总", "日常", "更新"]
  }
}
```

---

## 集成其他技能

| 技能 | 集成方式 |
|------|----------|
| weather | 调用天气 API 获取天气预报 |
| schedule | 获取当天课程安排 |
| political_news | 抓取政治时事要点 |
| health | 生成健康报告数据 |
| kaoyan | 生成学习复盘内容 |

---

## 输出格式

### 早间聚合示例

```
🌅 早间智能提醒 (07:30)

【天气】☀️ 晴 18-24°C
  空气质量：良
  建议：适合户外运动

【课表】📚 今天有 3 节课
  1-2节: 智能施工与装备 (致用楼-301)
  7-8节: 智能感知与数字信号处理 (致用楼-205)

【早餐】🍳 建议时间: 07:00-07:30
  推荐：粥+鸡蛋补充能量

━━━━━━━━━━━━━━━━━━
优先级: NORMAL | 勿扰模式: OFF
```

### 晚间聚合示例

```
🌙 晚间智能提醒 (23:00)

【健康报告】💪
  今日运动: 已完成 (跑步 30min)
  睡眠质量 7.2h
  疲劳指数: : 预估0.72 (适中)
  建议：泡脚放松，准备休息

【学习复盘】📖
  今日学习时长: 6.5h
  数学: 3h (极限复习)
  英语: 1.5h (单词200个)
  完成任务: 8/10

━━━━━━━━━━━━━━━━━━
优先级: IMPORTANT | 勿扰模式: OFF
```

---

## 最佳实践

1. **配置 cron 触发器** — 按时段自动执行
2. **结合学习状态** — 勿扰模式避免打扰
3. **优先级过滤** — 减少无效通知
4. **定期检查日志** — 优化通知策略

---

## License

**License:** MIT — Use freely, modify, distribute.

---

*让通知像贴心管家一样恰到好处* ✨
