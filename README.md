# laowang-mianshi-fupan

## 从 GitHub 安装（豆包工作）

GitHub 用户：`pmlaowangba-lab`；仓库：`pmlaowangba-lab/laowang-mianshi-fupan`。

把下面整段发送给电脑版豆包工作的 Agent：

```text
请从 GitHub 用户 pmlaowangba-lab 的仓库 laowang-mianshi-fupan 安装 Skill。
仓库地址：https://github.com/pmlaowangba-lab/laowang-mianshi-fupan
请先读取仓库根目录 SKILL.md，下载完整技能目录（包括 scripts、references、assets 和 agents 等文件，若存在），安装到当前工作区 .agents/skills/laowang-mianshi-fupan/。
安装后检查 SKILL.md 的 name 与依赖文件，尝试识别并调用技能，返回实际安装路径和识别结果。若不能识别，请说明需要配置的技能目录或刷新步骤，不要仅以下载成功宣称安装完成。
```

也可手动安装：

```bash
git clone https://github.com/pmlaowangba-lab/laowang-mianshi-fupan.git .agents/skills/laowang-mianshi-fupan
```

Python 脚本需 Python 3 与 PyYAML；若缺少 PyYAML，请在项目虚拟环境中安装。技能能否出现在界面列表，取决于客户端版本和技能目录设置，需在目标客户端实际检查。
飞书功能还需用户自己的应用、权限和凭据；本地功能不需要飞书。个人数据写入 workspace，不提交 GitHub。


面后复盘子 Agent：错题本 + 每日加练。与 `laowang-mianshi-zhu` 共用 `laowang-mianshi-lian` 工作册。

## 入口

优先经 `laowang-mianshi-lian` 路由；熟练用户可直接 `$laowang-mianshi-fupan`。

## 模式

`post-debrief` | `wrong-book-add` | `daily-drill` | `drill-review` | `cycle-report` | `patch-hint`
