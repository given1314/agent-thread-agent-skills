---
name: obsidian
description: Obsidian笔记管理 - 考研笔记整理、知识库构建、双向链接管理
homepage: https://obsidian.md
metadata: {"clawdbot":{"emoji":"📚"}}
---

# obsidian

考研笔记管理专家，帮助构建知识库、双向链接和笔记整理。

## 考研笔记目录结构

推荐爸爸使用的Obsidian仓库结构：

```
ObsidianVault/
├── 📌 00-考研大纲/           # 考研目标院校、专业大纲
│   ├── 浙江工业大学机械.md
│   └── 考试科目笔记.md
├── 📚 01-数学/               # 数学笔记
│   ├── 高等数学/
│   ├── 线性代数/
│   └── 概率论/
├── 📚 02-英语/               # 英语笔记
│   ├── 单词/
│   ├── 语法/
│   ├── 阅读/
│   └── 作文/
├── 📚 03-政治/               # 政治笔记
│   ├── 马克思主义基本原理/
│   ├── 毛泽东思想/
│   ├── 中国特色社会主义/
│   └── 时政/
├── 📚 04-机械原理/            # 专业课
│   ├── 平面机构分析/
│   ├── 平面连杆机构/
│   ├── 凸轮机构/
│   └── 齿轮传动/
├── 🗂️ 05-错题本/             # 错题整理
│   ├── 数学错题/
│   ├── 英语错题/
│   └── 专业课错题/
├── 📝 06-每日笔记/           # 日常学习记录
│   └── 2026-03-XX.md
└── 🔗 07-知识图谱/            # 双向链接汇总
```

## 常用Obsidian命令

### 通过Shell操作Obsidian Vault

```bash
# 查看Obsidian Vault中的文件
Get-ChildItem -Recurse "你的Obsidian路径" -Include "*.md"

# 创建新的笔记文件
@"
# 标题

## 今日学习

## 重点笔记

## 问题记录

"@ | Out-File -FilePath "路径/文件名.md" -Encoding UTF8

# 搜索包含特定关键词的笔记
Get-ChildItem -Recurse "你的Obsidian路径" -Include "*.md" | Select-String "关键词"
```

### 快速创建笔记模板

**每日学习笔记模板：**
```markdown
# 2026-03-XX 学习笔记

## 📅 日期：2026年3月XX日
## 📖 学习科目：

### 今日目标
- [ ] 任务1
- [ ] 任务2

### 今日总结
- 

### 明日计划
- [ ] 

### 笔记链接
[[]]
```

**错题整理模板：**
```markdown
# 错题整理 - [科目]

## 题目
（粘贴题目）

## 错误原因
- 

## 正确答案
（写下正确解法）

## 知识点链接
[[相关知识点]]
```

## Obsidian插件推荐（考研必备）

| 插件 | 功能 |
|------|------|
| Dataview | 按日期/标签查询笔记 |
| Calendar | 日历视图 |
| Obsidian Spreadsheets | 表格支持 |
| Remotely Save | 同步到云端 |
|Pandoc Plugin | 导出为Word/PDF |

## 双向链接技巧

- 使用 `[[笔记名称]]` 创建双向链接
- 使用 `[[笔记名称|显示文本]]` 自定义显示文字
- 使用 `#标签` 添加标签
- 在笔记末尾添加 `[[相关笔记]]` 建立知识关联

## 与考研系统联动

可以与kaoyan目录联动：
- 每日任务 → 同步到 06-每日笔记
- 错题整理 → 同步到 05-错题本
- 知识点总结 → 同步到对应科目目录

## 快速命令

```bash
# 打开今日笔记
obsidian "ObsidianVault/06-每日笔记/$(Get-Date -Format 'yyyy-MM-dd').md"

# 创建新的错题记录
$date = Get-Date -Format 'yyyy-MM-dd'
$content = @"
# 错题整理 - $date

## 题目

## 错误原因

## 正确答案

## 知识点
"@
Out-File -FilePath "ObsidianVault/05-错题本/数学错题/${date}.md" -Encoding UTF8
```
