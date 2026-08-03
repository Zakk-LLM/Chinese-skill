# Chinese Skill

简体中文 | [繁體中文](README.md)

Chinese Skill 是供 Claude、Codex 与 OpenCode 使用的中文写作与审查技能，适用于文章、文档、界面文案、代码注释、commit 与 PR。

它检查语法、逻辑、机器翻译痕迹、口语、自造词、冗长内容、简繁混用及不必要的注释。规则优先采用项目既有格式与术语；面向多个中文地区时，使用同一字形及各地读者都能理解的标准中文。

## 要求

- Python 3.11 或更新版本
- Bash

## 安装

```bash
git clone https://github.com/Zakk-LLM/Chinese-skill.git
cd Chinese-skill
./install.sh
```

默认以符号链接安装至三个代理工具，并加入要求代理工具定期重新读取技能的提醒。安装程序不会覆盖不属于本项目的文件。

```bash
./install.sh claude codex
./install.sh --copy
./install.sh --status
./install.sh --uninstall
```

| 代理工具 | 安装位置 |
|---|---|
| Claude | `~/.claude/skills/chinese-skill` |
| Codex | `${CODEX_HOME:-~/.codex}/skills/chinese-skill` |
| OpenCode | `~/.config/opencode/skills/chinese-skill` |

符号链接安装要求来源目录保持不变。需要移动或删除来源目录时，请先卸载，或改用 `--copy`。

## 使用

代理工具应先读取 [SKILL.md](SKILL.md)。以下命令可检查文件、目录或标准输入：

```bash
python3 scripts/chinese_lint.py README.md docs/
python3 scripts/chinese_lint.py --kind source src/
python3 scripts/chinese_lint.py --kind prose --style readme README.zh-CN.md
python3 scripts/chinese_lint.py --kind prose --style ui path/to/catalog
python3 scripts/chinese_lint.py --kind prose --format json article.md
python3 scripts/chinese_lint.py --kind prose --style readme --fix README.zh-CN.md
printf '%s\n' '待检查文字' | python3 scripts/chinese_lint.py --kind prose -
python3 scripts/chinese_lint.py --kind commit-message message.txt
python3 scripts/chinese_lint.py --kind pr-body --title 'scope: summary' body.txt
```

| 风格 | 用途 |
|---|---|
| `standard` | 通用中文检查 |
| `strict` | 精简文字，禁用 Emoji 与中文代码注释 |
| `academic` | 学术文章 |
| `technical` | 技术文章与设计说明 |
| `readme` | 项目入口文档 |
| `ui` | 控件、状态、错误及确认文字 |

`--format json` 输出稳定的规则标识符、严重程度、路径、行号、消息与样本，供编辑器及 CI 使用。`--fail-level warning` 让警告也产生失败状态。通过标准输入检查数据文件时，使用 `--stdin-filename` 指定文件名。`--fix` 只修正全角字母和数字、标点、空格及 README 标题句号，不改写语法或措辞。

`--locale` 支持 `zh-CN`、`zh-TW`、`zh-HK`、`zh-SG` 与 `zh-MY`。香港使用繁体，新加坡与马来西亚使用简体；所在地区的正式技术术语可以保留。所有模式都会拒绝 AI 署名，但允许使用真实电子邮件地址的人类作者署名。

检查器会提示置信度较高的“的／得／地”错误与文内术语混用。`--comment-audit` 另行提示只复述相邻代码的注释。这类提示不会自动修正；因果关系、术语选择及注释价值仍需人工审核。

## 项目集成

pre-commit 用户可引用本仓库的 `chinese-lint` hook。GitHub Actions 可直接使用 `Zakk-LLM/Chinese-skill@版本`，并通过 `path`、`kind`、`style` 与 `locale` 指定检查范围。

```yaml
repos:
  - repo: https://github.com/Zakk-LLM/Chinese-skill
    rev: v1.0.0
    hooks:
      - id: chinese-lint
```

```yaml
- uses: Zakk-LLM/Chinese-skill@v1.0.0
  with:
    path: docs
    style: technical
    locale: zh-CN
```

## 规则

- [写作规则](references/writing-policy.md)：文章、改写、翻译、篇幅及注释
- [README 规则](references/readme-style.md)：入口文档的结构、句法及信息顺序
- [UI 规则](references/ui-style.md)：控件、状态、错误、确认及辅助功能文字
- [PR 规则](references/pr-policy.md)：commit、PR、审查及发布说明
- [Gentoo overlay 规则](references/overlay-policy.md)：gentoo-zh overlay 的附加要求
- [词典规则](references/lexicon-policy.md)：来源优先顺序、地区词汇及专业术语

项目规范与近期示例决定格式、语言及术语。格式选择会改变结果而现有资料不足时，应先向用户确认。

## 语料与词典

[README 语料](references/readme-corpus.json)记录六个中文开源项目在 2019 年底前的 README 结构。[UI 语料](references/ui-corpus.json)记录六个大型开源项目的固定版本中文词库。固定文件均记录 commit 与 Git blob。由语料归纳的规则至少由两个来源支持；内部规则另行标示，不宣称由语料直接得出。两份语料不复制来源文字，也不将来源中的口语、宣传语或直译句式列为规范。

代理工具不应直接加载完整语料。先列出规则标识符，再按需获取一条规则；只有核对来源时才获取单一来源记录。

```bash
python3 scripts/corpus_lookup.py readme --list
python3 scripts/corpus_lookup.py readme --pattern identity
python3 scripts/corpus_lookup.py ui --pattern failure --locale zh-CN
python3 scripts/corpus_lookup.py readme --source gogs-2019
python3 scripts/verify_corpora.py
```

`verify_corpora.py` 需要网络连接，用于核对来源路径、commit 日期与 Git blob。GitHub 达到速率限制时，程序会要求设置 `GITHUB_TOKEN` 并以状态码 2 结束，不会误报为内容不一致。

内置词典包括国家教育研究院两岸对照计算机名词、OpenCC、MediaWiki 地区词转换表、CC-CEDICT、Unihan、McBopomofo、jieba、THUOCL 与 Rime essay。萌娘百科及中文维基词库采用可选安装，不随项目发布。

```bash
python3 scripts/lexicon_lookup.py '代码'
python3 scripts/lexicon_lookup.py 'cache' --source naer
python3 scripts/lexicon_lookup.py --reference
python3 scripts/sync_lexicons.py --verify
python3 scripts/sync_lexicons.py --source moegirl
python3 scripts/sync_lexicons.py --source zhwiki
python3 scripts/sync_lexicons.py --verify-optional
```

地区词汇检查目前只适用于 `zh-CN` 与 `zh-TW`，必须明确启用。推导结果是人工审核的候选项，不会取代项目术语。

```bash
python3 scripts/chinese_lint.py --kind prose --locale zh-CN --regional docs/
```

## 验证

提交修改前运行：

```bash
shellcheck install.sh
python3 scripts/test_chinese_lint.py
python3 scripts/test_install.py
python3 scripts/test_lexicons.py
python3 scripts/test_corpora.py
python3 scripts/test_integrations.py
python3 scripts/sync_lexicons.py --verify
python3 scripts/validate_repository.py --release
```

## 许可证

项目源代码、规则数据及原创文档采用 [MIT License](LICENSE)。内置与可选词库保留各自的许可证；重新分发前请查阅[词库许可证与来源](lexicons/ATTRIBUTION.md)。
