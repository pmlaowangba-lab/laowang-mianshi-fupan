---
name: laowang-mianshi-fupan
description: 老王工作区原创面后复盘 Skill（面试链子 Agent，别名 laowang-mianshi-fupan）。支持初始化秋招复盘总册 fupan-deck.md 并在飞书创建专属复盘文档；接收真实面试口述/转写，结构化复盘、登记错题、生成每日专项加练，增量写入 laowang-mianshi-lian 工作册 B/C 章与复盘总册。不编造面试真题，不替代进度追踪（可交接 laowang-qiuzhi-jindu）。
---

# 老王面后复盘（laowang-mianshi-fupan）

**子 Agent · 考后半环。** 工作册路径固定：

`laowang-mianshi-lian/workspace/<season>/mianshi-workbook.md`  
只维护 **B 面后复盘** 与 **C 错题本与加练**。

编排入口：`laowang-mianshi-lian`（可选联动，需另行安装）


## 独立安装模式（优先于后文工作区联动规则）

本仓库的正式 name 是 laowang-mianshi-fupan，可单独使用。未安装 laowang-mianshi-lian 时，维护本 Skill 下 workspace/<season>/fupan-deck.md；从用户提供的逐字稿或 laowang-mianshi-zhu 总册读取考前资料，按本仓库复盘模板更新，缺少考前资料时明确标注。其他 Skill 均为可选联动。

本地初始化：`python scripts/fupan_init.py --local-only --season 2027-fall`。
飞书为可选：设置 FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_SPACE_ID，必要时设置 FEISHU_PARENT_NODE_TOKEN；也可通过 --obsidian-wx 显式指定用户自己的配置文件。没有凭据时只生成本地总册，不能宣称已创建飞书文档。初始化不自动灌入演示求职记录。

## 能力地图

| 模式 | 代号 | 场景 |
|------|------|------|
| **复盘总册初始化** | `fupan-init` | 建 `fupan-deck.md` + 飞书专属复盘文档（别名 **laowang-mianshi-fupan** 入口） |
| 面后复盘 | `post-debrief` | 面完口述/粘贴转写 → 结构化复盘 + 回填总册/飞书 |
| 错题登记 | `wrong-book-add` | 单条薄弱考点入库 |
| 每日加练 | `daily-drill` | 从错题本抽今日题单 |
| 加练批改 | `drill-review` | 批改今日口述/文字练习 |
| 周期报告 | `cycle-report` | 近 7 天薄弱分布 + 复习建议 |
| 回写建议 | `patch-hint` | 输出 B4，供 zhu 改 A 章 |

## 模式：fupan-init

### 目标

秋招季**一本复盘总册**：顶部避坑错题库 + 按公司分章；飞书端生成同名可编辑文档，手机随时看。

### 数据落点

```text
laowang-mianshi-fupan/workspace/<season>/
├── fupan-deck.md              # 本地复盘总册（post-debrief 回填）
├── feishu-fupan-config.yaml   # 飞书 document_id / wiki_url
└── audit/
```

与 `laowang-mianshi-lian` 的 `mianshi-workbook.md` **互补**：工作册管 A/B/C 闭环；`fupan-deck` 管跨岗避坑库 + 飞书镜像。

### 流程

1. 读 obsidian-wx 的 `feishuAppId` + 环境变量 `FEISHU_APP_SECRET`（与 qiuzhi-jindu 同源）。
2. 在已配置的知识库目录下创建飞书 docx 节点（默认复用 obsidian-wx 第一个知识库父节点）。
3. 写入本地 [assets/fupan-deck-template.md](assets/fupan-deck-template.md) 结构 + 演示章节（可对齐 laowang-qiuzhi-jindu 投递卡）。
4. 将总册 Markdown 灌入飞书文档；尽力设置「组织内获得链接可编辑」。

```bash
python scripts/fupan_init.py --season 2027-fall

# 本地 fupan-deck 更新后，重写飞书 wiki 正文（需 FEISHU_APP_SECRET 或 workspace/feishu-app.secret）
python scripts/fupan_init.py --season 2027-fall sync-feishu
```

### 对话示例

```text
用 laowang-mianshi-fupan，初始化秋招面试复盘总册，并在飞书创建专属复盘文档。
```

## 模式：post-debrief（核心）

### 输入

- 公司、岗位（对齐工作册 `entry_id`）
- 用户回忆：问了什么、我怎么答的、哪里卡壳
- 可选：录音转写、laowang-mianshi-mo 的 debrief

### 流程

1. Read 工作册该岗 **A 章**（对比「准备 vs 实际」）。
2. 写 **B 章**（见 [references/post-debrief-schema.md](references/post-debrief-schema.md)）：
   - 场次、真题还原、自评四维、真实性风险
3. 薄弱点写入 **C1 错题登记**（去重规则见 [references/wrong-book-rules.md](references/wrong-book-rules.md)）。
4. 生成 **B4 回写 A 建议**（具体段落，不直接改 A）。
5. 局部 Edit 工作册 B/C 节；写 `audit/fu-<entry_id>-<date>.md`。
6. 提示用户：是否 `chat-update` 到 `laowang-qiuzhi-jindu`（可选联动，需另行安装）。

### 对话示例

```text
用 laowang-mianshi-fupan（或经 laowang-mianshi-lian 路由）：
快手社区产品二面刚结束，问了指标归因，漏斗拆解我答乱了，
项目二的数据我也说不准。写入工作册 B/C 章。
```

## 模式：daily-drill

从 **C1 未掌握错题** + **A5 待补清单** 抽 3–5 题：

| 类型 | 数量 |
|------|------|
| 昨日/近场真题变体 | 2 |
| 关联 JD 能力补洞 | 1–2 |
| 口述限时（30s/90s） | 每题标注 |

题写入 **C2 加练日志**，不生成泛化千题库。

## 模式：drill-review

用户提交练习稿 → 按 [references/drill-rubric.md](references/drill-rubric.md) 打分 → 更新 C2 条目状态 `已练/待再练` → 强项可建议 zhu 合并进 A3。

## 模式：cycle-report

统计近 7 天 C2 记录，输出：

- Top3 薄弱标签（如「漏斗」「归因」「协作冲突」）
- 建议下周 daily-drill 权重
- 是否触发 zhu `bullet-patch`

## 与 zhu 的闭环

```text
fu：post-debrief → C 错题 + B4 建议
        ↓ 用户确认
zhu：bullet-patch → 更新 A 章对应 bullet
        ↓
fu：daily-drill 验证是否还错
```

## 真实边界

- 真题还原用用户原话，不补全面试官「一定问了」的问题
- 批改不编造用户没练过的经历
- 见 [references/truth-boundary.md](references/truth-boundary.md)

## 参考文件

- [post-debrief-schema.md](references/post-debrief-schema.md)
- [wrong-book-rules.md](references/wrong-book-rules.md)
- [drill-rubric.md](references/drill-rubric.md)
- [daily-drill-rules.md](references/daily-drill-rules.md)

## 质量门槛

- [ ] 只 Edit B/C 章
- [ ] 错题可追溯到 B2 某条真题
- [ ] B4 建议指向 A 章具体小节
- [ ] daily-drill 题来自本岗记录
