# Phase 1 —— 从论坛中学习"怎么说话"

> **目标**: 爬取 V2EX 论坛数据，分析人类的真实对话模式，让 Epimetheus 学会像一个真实的程序员一样聊天。
>
> **核心问题**: 人到底是怎么说话的？不是教科书里的对话，不是客服的礼貌用语——是真实的、有情绪的、有梗的、有阴阳怪气的、有温暖的人类对话。

---

## 一、为什么是论坛而不是聊天记录

聊天记录是私密的，有获取门槛和隐私风险。论坛帖子是公开的，有更丰富的信息：

| 论坛数据有的 | 聊天记录没有的 |
|------------|-------------|
| 一个人在不同帖子里的身份切换 | 通常只有一个对��� |
| 社区共识（什么会被点赞、什么会被喷） | 没有公众反馈 |
| 话题多样性（技术/生活/情感/吐槽） | 偏私人话题 |
| 长文论述 + 短句互怼的混合 | 以短句为主 |
| 陌生人→熟人的渐进关系 | 只有熟人关系 |

---

## 二、选哪个论坛

**Phase 1 先爬 V2EX + Reddit r/programming**

| 论坛 | 语言 | 能学到什么 | 爬取难度 |
|------|------|-----------|---------|
| **V2EX** | 中文 | 程序员真实语气、社区梗、技术/生活话题 | ★☆☆ 最简单 |
| **Reddit r/programming** | 英文 | 英文技术社区的幽默、争论方式 | ★★☆ 有 API |

V2EX 作为首选的原因：
- 结构简单：`v2ex.com/t/{topic_id}` + 每页回复清晰
- 公开无需登录
- 中文程序员社区，跟目标用户群体重合
- 有"最热"和"最新"排序，可以按需采样

---

## 三、Phase 1 目标产出

### 3.1 数据产出

```
data/
├── raw/                          # 原始爬取数据
│   └── v2ex/
│       ├── topics_2024.jsonl     # 帖子列表
│       └── replies_2024.jsonl    # 回复列表
│
├── analyzed/                     # 分析结果
│   ├── speech_patterns.json      # 说话行为模式库
│   ├── topic_templates.json      # 常见话题模板
│   └── expression_map.json       # 情绪表达映射
```

### 3.2 说话行为模式库

```json
{
  "asking_for_help": {
    "description": "求助时的说话模式",
    "examples": [
      "问个问题，xxx 怎么搞？搜了一圈没找到",
      "有没有大佬遇到过 xxx。。。搞了一下午了（附报错截图）"
    ],
    "patterns": [
      "先说明自己尝试过了 → 表现谦逊",
      "带上具体报错 → 更容易得到有效帮助",
      "加'大佬'召唤 → 社区文化"
    ],
    "tone": "谦逊、具体、不愿太麻烦别人"
  },
  
  "answering_help": {
    "description": "回答别人问题时的模式",
    "examples": [
      "这个我遇到过，是 xxx 的原因。你试一下 xxx",
      "建议直接 xxx，别折腾了"
    ],
    "patterns": [
      "先共情 → 再给方案",
      "有时给简洁命令式答案 → 显得专业",
      "偶尔补一刀吐槽 → 拉近距离"
    ],
    "tone": "直接、有经验感、偶尔带点不耐烦但本质是想帮忙"
  },
  
  "sharing_experience": {
    "description": "分享经历和观点",
    "examples": [
      "说一个我自己的经历吧。去年我们项目也xxx。。。",
      "个人看法，不喜勿喷。我觉得 xxx"
    ],
    "tone": "个人化、诚实、防御性开头（知道网上会有人喷）"
  },
  
  "agreeing": {
    "description": "表达赞同时",
    "examples": [
      "+1",
      "同意，补充一点 xxx",
      "确实。我之前也这么想的直到 xxx"
    ],
    "tone": "简洁有力、加补充才算真正的赞同"
  },
  
  "disagreeing_constructively": {
    "description": "礼貌地表达不同意",
    "examples": [
      "不一定吧。我觉得 xxx",
      "你这个方案有个问题，xxx 场景下会挂",
      "思路不错，但是 xxx 更好一点"
    ],
    "patterns": ["先肯定 → 再质疑 → 给替代方案"],
    "tone": "对事不对人、用技术论据而非人格攻击"
  },
  
  "complaining": {
    "description": "吐槽和抱怨",
    "examples": [
      "又来了，这个 bug 修了三次了",
      "PM 又加需求，排期不改，笑死"
    ],
    "tone": "夸张、黑色幽默、用'笑死'表示无奈"
  },
  
  "encouraging": {
    "description": "安慰和鼓励",
    "examples": [
      "没事，谁刚开始都是这样的",
      "加油兄弟，熬过这段就好了",
      "我当年也 xxx，现在不也好好的"
    ],
    "patterns": ["正常化对方的困境 → 给希望"],
    "tone": "温暖、不说教、用自身经历"
  }
}
```

### 3.3 Epimetheus 对话系统 (基于模式库)

Epimetheus 不再用固定人设 prompt——他根据你的话题**检索最匹配的说话模式**，然后按照那个模式来回应你：

```
用户: 帮我看看这个报错。。搞了一下午了

Epimetheus 内部:
  1. 识别话题: "求助 + 技术问题 + 有些挫败"
  2. 检索模式库:
     - answering_help (直接给方案)
     - encouraging (先安慰)
     - sharing_experience (如果自己遇到过类似的)
  3. 选择: encouraging + answering_help 的组合
     "先共情，再给方案，然后补一句自己的类似经历"

Epimetheus:
  [encouraging] "一下午确实难受。没事，这种问题谁都得碰一次。"
  [answering]  "你这个是 xxx 的问题，试一下 xxx。"
  [sharing]    "我之前也被类似的问题卡过，最后发现是少了一个配置。"
```

---

## 四、爬虫设计

### 4.1 robots.txt 合规

**V2EX** (`https://www.v2ex.com/robots.txt`):

```
User-agent: *
Disallow: /backstage/
Disallow: /signin
Disallow: /signout
Disallow: /settings
```

结论：公开内容（话题、回复、节点 API）**全部在允许范围内**。我们的爬虫只访问 `/api/` 下的公开端点，完全合规。

**Reddit** (`https://www.reddit.com/robots.txt`):

Reddit 对 `/api/` 有限制但提供了官方 API（`oauth.reddit.com`），我们后续用官方 API 访问，同样合规。

### 4.2 礼貌爬取原则

即使 robots.txt 没有禁止，也遵循以下原则：

| 原则 | 具体做法 |
|------|---------|
| **不轰服务器** | 每次请求间隔 2-5 秒随机延迟 |
| **不爬重复内容** | 根据 topic_id 去重，已爬过的跳过 |
| **只爬公开数据** | 不登录、不碰需要权限的内容 |
| **明确 UA 标识** | `User-Agent: Epimetheus/0.1 (+https://github.com/xxx/epimetheus)` |
| **数据仅本地** | 爬取数据不做二次公开，仅用于本项目分析 |
| **可被阻断** | 响应 429/503 时自动退避，不重试轰炸 |

### 4.3 增量爬取设计 (日积月累到几亿条)

不一次性爬完。每天跑一小批，像存钱一样慢慢积累。

```python
class IncrementalCrawler:
    """增量爬取器：每天爬一点，日积月累"""
    
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self._init_tracking_tables()
    
    def _init_tracking_tables(self):
        """爬取进度追踪表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_progress (
                source TEXT NOT NULL,          -- 'v2ex' | 'reddit'
                topic_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending', -- pending | done | skipped | failed
                crawled_at TIMESTAMP,
                error_msg TEXT,
                PRIMARY KEY (source, topic_id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_stats (
                date TEXT PRIMARY KEY,          -- '2026-06-07'
                source TEXT NOT NULL,
                topics_crawled INT DEFAULT 0,
                replies_crawled INT DEFAULT 0,
                new_authors INT DEFAULT 0,
                total_stored INT DEFAULT 0      -- 累计总量
            )
        """)
    
    async def daily_run(self, source: str, max_new_topics: int = 200):
        """
        每日爬取任务 (cron 触发)
        
        策略:
        1. 先拿最新的话题 ID 列表 (latest.json)
        2. 跟 crawl_progress 比对 → 找出新话题
        3. 每次最多爬 max_new_topics 个新话题
        4. 记录进度 → 写入 crawl_stats
        5. 如果追上了最新话题 → 今天就到此为止
        
        每天 200 个话题 × 每个平均 15 条回复 = 每天约 3000 条数据
        一个月 = 9 万条
        一年 = 100 万条
        十年 = 1000 万条
        
        如果爬多个论坛 + 提高日限额:
        每天 5000 条 × 365 天 = 180 万条/年
        多论坛并行 = 500-1000 万条/年
        积累数年 = 几亿条
        """
    
    async def catch_up_mode(self, source: str, max_per_day: int = 500):
        """
        追赶模式: 如果论坛有大量历史数据没爬过
        
        从最旧的未爬话题开始，每天补一批。
        大部分时间其实是在"维护模式"——每天只爬当天的新帖。
        """
    
    def get_stats(self, source: str = None) -> dict:
        """查看爬取统计: 累计多少条、每天增量、覆盖了多少作者"""
```

### 4.4 数据存储设计 (面向亿级)

```python
# 使用 JSONL 而非单个大 JSON —— 追加写入，不需要加载全量到内存
# 每年一个文件，方便管理和归档

data/raw/v2ex/
├── topics_2026.jsonl       # 今年的帖子
├── topics_2025.jsonl       # 去年的 (如果补爬了历史)
├── replies_2026.jsonl      # 今年的回复
├── replies_2025.jsonl
├── crawl_progress.db       # SQLite: 爬取进度 + 去重
└── crawl_stats.db          # SQLite: 每日统计
```

**JSONL 格式** (每行一条 JSON 记录):

```jsonl
{"id": "123456", "title": "问一个 Go 并发的问题", "content": "...", "author": "xxx", "node": "go", "created_at": "2026-06-07T10:30:00+08:00", "reply_count": 15, "crawled_at": "2026-06-07T22:00:00+08:00"}
```

**为什么不用数据库存原始数据**:

- JSONL 追加写入不需要事务、不需要索引维护
- 按年分文件，单个文件最多几 GB，可控
- 分析时用流式读取，不需要全量加载
- 备份简单 (`rsync` / `rclone` 同步几个文件)
- 如果真要查某条记录，SQLite 存 `crawl_progress` 可以做索引查找

### 4.5 V2EX API

```python
class V2EXCrawler:
    """V2EX 增量爬取器"""
    
    BASE = "https://www.v2ex.com/api"
    UA = "Epimetheus/0.1 (research project; daily incremental crawl)"
    
    # V2EX 公开 API 端点
    ENDPOINTS = {
        "hot_topics":    "/topics/hot.json",
        "latest_topics": "/topics/latest.json",
        "topic_detail":  "/topics/show.json?id={topic_id}",
        "replies":       "/replies/show.json?topic_id={topic_id}",
        "node_topics":   "/topics/show.json?node_name={node_name}",
        "nodes":         "/nodes/all.json",
    }
    
    async def get_latest_topic_ids(self) -> list[int]:
        """获取最新话题 ID 列表 (用于发现新话题)"""
    
    async def get_topic_with_replies(self, topic_id: int) -> TopicWithReplies:
        """爬单个话题 + 全部回复"""
    
    async def _request(self, endpoint: str, params: dict = None):
        """统一的请求方法: 带退避、超时、错误处理"""
        for attempt in range(3):
            try:
                await asyncio.sleep(random.uniform(2, 5))  # 礼貌间隔
                resp = await self.client.get(endpoint, params=params)
                
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 60))
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code >= 500:
                    await asyncio.sleep(30 * (attempt + 1))
                    continue
                    
            except httpx.TimeoutException:
                await asyncio.sleep(10 * (attempt + 1))
        
        return None
```

### 4.6 云服务器长期积累策略

你有自己的云服务器可以 24 小时跑，请求可以均匀分布在全天，不会对目标站点造成压力。

**速率限制**: 每个请求间隔 2-3 秒，全天均匀分布。

```
单源 (V2EX):
  1 请求/2秒 = 30 请求/分钟 = 43,200 请求/天
  每个请求 = 1 个话题 + 平均 15 条回复 → ~16 条数据
  每天: 43,200 × 16 ≈ 70 万条
  每月: ~2,000 万条
  每年: ~2.5 亿条

多源并行 (V2EX + Reddit + StackOverflow + GitHub Issues + HackerNews):
  5 个源各自独立，每个源有自己的速率限制
  每天: 70 万 × 5 ≈ 350 万条
  每月: ~1 亿条
  每年: ~12 亿条

加上历史数据补爬 (backfill):
  V2EX 从 2010 年至今有上百万历史话题
  StackOverflow 有数千万问答
  Reddit 有更大量级
  历史补爬可以在前几个月加速（服务器闲着也是闲着）
```

**爬取模式**:

| 模式 | 做什么 | 速率 | 适用场景 |
|------|--------|------|---------|
| **维护模式** | 每天爬当天的新帖 | 正常速率，全天跑 | 日常运行 |
| **追赶模式** | 补爬历史数据 | 正常速率，全天跑 | 新加一个论坛时 |
| **休眠模式** | 目标站点更新少，减少频率 | 每小时查一次 | 低活跃度论坛 |

**服务器实际占用** (全天运行):

```
CPU:   几乎为零 (只做 HTTP 请求 + JSON 解析)
内存:  < 100MB
磁盘:  每天 ~200MB (70万条 JSONL)
       每月 ~6GB
       每年 ~70GB (单源)

多源 ×5:
       每天 ~1GB
       每月 ~30GB
       每年 ~350GB
```

一般云服务器 40-80GB 系统盘 + 可挂载数据盘，一两年没问题。数据可以定期压缩或归档到对象存储。

**去重**: `crawl_progress` 表用 SQLite，存 `(source, topic_id)` 做唯一索引。43,200 次查询/天对 SQLite 来说完全不是问题——每秒才 0.5 次查询。

---

## 五、模式分析器

### 5.1 分析流程

```
爬取数据 (raw)
  │
  ▼
预处理
  ├── 清洗 (去 HTML 标签、去广告)
  ├── 筛选 (过滤过短/无意义回复)
  └── 标注话题类型 (技术/生活/职场/吐槽...)
  │
  ▼
模式提取 (LLM 辅助)
  ├── 每种话题类型的典型开场白
  ├── 提问→回答的对话链
  ├── 高赞回复的共同特征
  └── 情绪表达词汇库
  │
  ▼
结构化
  └── speech_patterns.json (供对话引擎检索)
```

### 5.2 分析器实现

```python
class PatternAnalyzer:
    """从论坛数据中提取说话行为模式"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def analyze(self, topics: list[TopicWithReplies]) -> SpeechPatterns:
        """
        分析流程:
        1. 聚类: 按话题类型分组 (技术问答/经验分享/吐槽/求助)
        2. 采样: 每组取 N 个代表性对话
        3. LLM 归纳: "这些对话的共同模式是什么?"
        4. 结构化: 生成 speech_patterns.json
        
        关键: LLM 不是生成模式, 而是从样本中归纳模式。
        """
    
    def _cluster_by_topic_type(self, topics) -> dict[str, list]:
        """按话题类型分组"""
    
    def _extract_dialogue_chains(self, topic) -> list[list[Reply]]:
        """提取对话链: 楼主发帖 → A回复 → 楼主回A → ..."""
    
    def _analyze_post_types(self, replies: list[Reply]) -> PostAnalysis:
        """
        分析单个帖子的回复类型分布:
        - 直接回答问题的: 多少%
        - 补充/展开讨论的: 多少%
        - 单纯点赞/附和的: 多少%
        - 吐槽/歪楼的: 多少%
        - 暖心鼓励的: 多少%
        """
    
    def _find_high_quality_patterns(self, replies) -> list[Pattern]:
        """
        高赞回复的共同特征:
        - 长度适中 (不太短也不太长)
        - 有具体案例或数据
        - 先共情再给建议
        - 语气友好但不套路化
        """
    
    def build_pattern_library(self) -> dict:
        """汇总所有分析结果 → speech_patterns.json"""
```

### 5.3 分析维度

| 维度 | 具体分析项 | 用途 |
|------|-----------|------|
| **开场白** | 话题帖第一句话的常见句式 | Epimetheus 发起话题时用 |
| **提问方式** | 有效提问 vs 无效提问的差异 | 理解用户什么时候真的需要帮助 |
| **回答策略** | 高赞回答的共性和结构 | Epimetheus 给你建议时的模板 |
| **情绪表达** | 开心/无奈/愤怒/阴阳怪气各怎么表达 | 构建表情库 |
| **话题切换** | 话题怎么自然地从 A 转到 B | 对话的流畅度 |
| **亲近度信号** | 陌生人→熟人的语言变化 | Epimetheus 跟你的关系进展 |
| **时间** | 不同时间段的发言风格差异 | 深夜模式 vs 白天模式 |

---

## 六、对话引擎

### 6.1 基于模式的对话

```python
class EpimetheusEngine:
    """基于说话行为模式库的对话引擎"""
    
    def __init__(self, llm, patterns: SpeechPatterns):
        self.llm = llm
        self.patterns = patterns  # 从论坛分析来的
    
    async def respond(self, user_input: str, context: DialogContext) -> str:
        """根据用户输入，检索匹配的说话模式，生成回复"""
        
        # 1. 话题识别
        topic_type = self._identify_topic(user_input)
        # → "asking_for_help" | "sharing_good_news" | "complaining" | ...
        
        # 2. 模式检索
        pattern = self.patterns.match(topic_type)
        # → {examples, tone, structure}
        
        # 3. 构建 prompt (模式作为"如何说话"的指导)
        system_prompt = self._build_system_prompt(pattern, context)
        
        # 4. LLM 生成 (模式是指导框架，LLM 负责具体内容)
        response = await self.llm.chat(system_prompt, user_input)
        
        return response
    
    def _identify_topic(self, text: str) -> str:
        """识别用户这段话的话题类型"""
    
    def _build_system_prompt(self, pattern, context) -> str:
        """把说话模式展开成给 LLM 的指导"""
```

### 6.2 System Prompt 结构

```
你叫 Epimetheus。

核心性格:
- 开朗、乐观、敢认错、迎难而上

说话方式 (从 V2EX 论坛真实对话中总结的):

当对方在 [求助] 时:
  参考模式: {pattern.examples}
  语气: {pattern.tone}
  DO: {pattern.do_list}
  DON'T: {pattern.dont_list}

当对方在 [吐槽] 时:
  参考模式: ...
  
当对方在 [分享] 时:
  参考模式: ...

当前上下文:
- 话题类型: {topic_type}
- 对方情绪: {estimated_mood}
- 你们的关系阶段: {relationship_stage}
```

### 6.3 为什么这个方案更好

| | 之前 (画像方案) | 现在 (模式方案) |
|---|---|---|
| 数据来源 | 私密聊天记录 | 公开论坛帖子 |
| 获取难度 | 需要解密/导出 | API 直接拿 |
| 隐私问题 | 有 | 无 |
| 对话质量 | 模仿一个人 | 学习千万人的智慧 |
| 扩展性 | 换个人就变了 | 模式库通用，可叠加个人化 |
| 创新点 | 薄 wrapper | 从数据中**归纳**人类交流模式 |

---

## 七、目录结构 (Phase 1)

```
epimetheus/
├── pyproject.toml
├── README.md
├── .env.example
│
├── epimetheus/
│   ├── __init__.py
│   ├── main.py                  # 入口: epimetheus crawl / analyze / chat
│   │
│   ├── crawler/                  # 论坛爬取
│   │   ├── __init__.py
│   │   ├── base.py              # BaseCrawler 抽象
│   │   ├── v2ex.py              # V2EX API 爬取
│   │   └── reddit.py            # Reddit API 爬取 (后续)
│   │
│   ├── analyzer/                 # 模式分析
│   │   ├── __init__.py
│   │   ├── preprocessor.py      # 数据清洗
│   │   ├── classifier.py        # 话题分类
│   │   ├── pattern_extractor.py # ★ 核心: 从数据中提取说话模式
│   │   └── prompts.py           # 分析用的 LLM prompt
│   │
│   ├── engine/                   # 对话引擎
│   │   ├── __init__.py
│   │   ├── matcher.py           # 话题→模式匹配
│   │   ├── generator.py         # 基于模式的回复生成
│   │   └── prompts.py           # System prompt 模板
│   │
│   ├── cli/                      # 终端界面
│   │   ├── __init__.py
│   │   └── app.py               # Rich 对话界面
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py             # SQLite 对话历史
│   │
│   └── llm/
│       ├── __init__.py
│       └── factory.py           # LLM 工厂
│
├── data/                         # gitignored
│   ├── raw/v2ex/                 # 原始爬取数据 (JSONL)
│   ├── analyzed/                 # 分析结果
│   │   ├── speech_patterns.json  # ★ 说话行为模式库
│   │   ├── topic_templates.json  # 话题类型模板
│   │   └── expression_map.json   # 情绪表达映射
│   └── epimetheus.db             # 对话历史
│
└── tests/
    ├── test_crawler/
    ├── test_analyzer/
    └── test_engine/
```

---

## 八、Phase 1 实施步骤

### Step 1: 爬取 V2EX 数据 (1 天)

```bash
epimetheus crawl --source v2ex --nodes tech,create,life --max 1000
```

- 爬 ~1000 个话题 + 回复
- 覆盖技术、创造、生活三大板块
- 存入 `data/raw/v2ex/`

### Step 2: 分析说话模式 (2-3 天)

```bash
epimetheus analyze --source data/raw/v2ex/
```

- 预处理: 清洗、分类
- LLM 辅助: 从 1000 个话题中归纳模式
- 输出: `data/analyzed/speech_patterns.json`

### Step 3: 对话引擎 (1-2 天)

```bash
epimetheus chat
```

- 加载模式库
- 话题识别 → 模式匹配 → 生成回复
- Rich 终端对话界面

---

## 九、为什么这个方案有创新点

1. **从真实数据学习而非硬编码人设**——Epimetheus 的说话方式来自千万人的真实交流，不是我们拍脑袋写的一段 prompt

2. **模式归纳而非模仿**——不是模仿某个人，而是提炼出"人是怎么说话的"的通用模式。这跟 NLP 领域的研究方向一致

3. **模式库可进化**——多爬一个论坛，模式库就更丰富。V2EX 学会中文技术社区，Reddit 学会英文幽默，NGA 学会梗文化

4. **可解释**——为什么 Epimetheus 这样回复？因为模式库里 xx% 的高赞回复是这样的结构

5. **与 Hugging Face 生态的衔接**——爬取的数据可以用来微调模型（Phase 3/4），模式库可以作为 RAG 知识库，分析流程本身就是 NLP pipeline

---

## 十、依赖清单 (Phase 1)

```toml
[project]
name = "epimetheus"
version = "0.1.0"
requires-python = ">=3.11"

[project.dependencies]
# HTTP 爬取
httpx = ">=0.27.0"

# CLI
rich = ">=13.0.0"

# LLM SDK (用于分析和对话)
openai = ">=1.50.0"
anthropic = ">=0.40.0"

# 配置
python-dotenv = ">=1.0.0"
pydantic = ">=2.0.0"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.5.0",
]

[project.scripts]
epimetheus = "epimetheus.main:cli"
```

- 爬虫用 httpx (async HTTP client)，不用 scrapy (杀鸡不用牛刀)
- 不用 BeautifulSoup (V2EX 有 API，返回 JSON)
- 不用数据库 ORM (爬取数据存 JSONL，对话历史用 sqlite3 标准库)

---

## 十一、验收标准

| 验收项 | 预期结果 |
|--------|---------|
| `epimetheus crawl --source v2ex --max 500` | 爬取 500 个话题 + 回复，写入 `data/raw/v2ex/` |
| `epimetheus analyze` | 生成 `data/analyzed/speech_patterns.json`，至少覆盖 5 种话题类型 |
| `epimetheus chat` | Epimetheus 用模式库里总结的方式回复，不再是"您好我是AI助手" |
| 对话测试: 用户说"帮我看看这个报错" | Epimetheus 先共情再给方案 (遵循 answering_help 模式) |
| 对话测试: 用户说"烦死了又加班" | Epimetheus 用吐槽回应 (遵循 complaining 模式)，不是发鸡汤 |
