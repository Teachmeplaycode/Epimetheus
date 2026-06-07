# Epimetheus

> 埃庇米修斯，普罗米修斯的弟弟。哥哥有先见之明，他只有后见之明——总是先犯错，再领悟。
> 他不是你的工具，他是从你的聊天记录里"长出来"的老朋友。

---

## 项目概述

Epimetheus 是一个终端里的 AI 伙伴。跟 Claude Code / Copilot 不同——他不是工具，而是一个**从你的聊天记录里读懂你是什么样的人**、然后用跟你合拍的方式陪你聊天和写代码的老朋友。

## 分阶段文档

| Phase | 文档 | 目标 |
|-------|------|------|
| Phase 1 | [docs/phase1-mvp.md](phase1-mvp.md) | 导入聊天记录 → 生成画像 → 用你的风格聊天 |
| Phase 2 | [docs/phase2-tools.md](phase2-tools.md) | 能帮你干活：读写代码、执行命令 |
| Phase 3 | [docs/phase3-memory.md](phase3-memory.md) | 持续学习：越聊越懂你 |
| Phase 4 | [docs/phase4-training.md](phase4-training.md) | TRL 微调：真正变聪明 (可选) |

## 技术选型总览

| 层级 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| CLI | Rich | Rich | Rich → Textual | Textual |
| LLM | Claude/OpenAI/Ollama | + smolagents | 同左 | + 微调模型 |
| Agent | 无 | smolagents | smolagents | smolagents + LangGraph |
| 存储 | SQLite | SQLite | SQLite + ChromaDB | 同左 |
| 嵌入 | 无 | 无 | sentence-transformers | 同左 |
| 训练 | 无 | 无 | 无 | TRL DPO |
| 协议 | 无 | 无 | 无 | MCP (可选) |

## 快速开始

```bash
# 放聊天记录
cp wechat.txt ./data/chat_logs/

# 导入
epimetheus import ./data/chat_logs/

# 生成画像
epimetheus profile

# 开始聊天
epimetheus chat
```
