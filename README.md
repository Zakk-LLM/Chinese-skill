# Chinese Skill

Chinese Skill 是供 Claude、Codex 與 OpenCode 使用的中文寫作與審查技能，適用於文章、文件、介面文字、程式註釋、commit 與 PR。

它檢查語法、邏輯、機器翻譯痕跡、口語、自造詞、冗長內容、簡繁混用及不必要的註釋。規則優先採用倉庫既有格式與術語；面向多個中文地區時，使用同一字形及各地讀者都能理解的標準中文。

## 要求

- Python 3.11 或更新版本
- Bash

## 安裝

```bash
git clone https://github.com/Zakk-LLM/Chinese-skill.git
cd Chinese-skill
./install.sh
```

預設以符號連結安裝至三個代理，並加入要求代理定期重新讀取技能的提醒。安裝程式不會覆寫不屬於本專案的檔案。

```bash
./install.sh claude codex
./install.sh --copy
./install.sh --status
./install.sh --uninstall
```

| 代理 | 安裝位置 |
|---|---|
| Claude | `~/.claude/skills/chinese-skill` |
| Codex | `${CODEX_HOME:-~/.codex}/skills/chinese-skill` |
| OpenCode | `~/.config/opencode/skills/chinese-skill` |

符號連結安裝要求來源目錄保持不變。需要移動或刪除來源目錄時，請先解除安裝，或改用 `--copy`。

## 使用

代理應先讀取 [SKILL.md](SKILL.md)。以下命令可檢查檔案、目錄或標準輸入：

```bash
python3 scripts/chinese_lint.py README.md docs/
python3 scripts/chinese_lint.py --kind source src/
python3 scripts/chinese_lint.py --kind prose --style readme README.md
python3 scripts/chinese_lint.py --kind prose --style ui path/to/catalog
printf '%s\n' '待檢查文字' | python3 scripts/chinese_lint.py --kind prose -
python3 scripts/chinese_lint.py --kind commit-message message.txt
python3 scripts/chinese_lint.py --kind pr-body --title 'scope: summary' body.txt
```

| 風格 | 用途 |
|---|---|
| `standard` | 通用中文檢查 |
| `strict` | 精簡文字，禁用 Emoji 與中文程式註釋 |
| `academic` | 學術文章 |
| `technical` | 技術文章與設計說明 |
| `readme` | 專案入口文件 |
| `ui` | 控制項、狀態、錯誤及確認文字 |

`--locale` 支援 `zh-CN`、`zh-TW`、`zh-HK`、`zh-SG` 與 `zh-MY`。香港使用繁體，新加坡與馬來西亞使用簡體；所在地區的正式技術用語可以保留。所有模式都會拒絕 AI 署名，但允許使用真實電子郵件地址的人類作者署名。

自動檢查只處理可穩定判斷的問題。語法、因果關係、術語選擇及註釋價值仍需人工審查。

## 規則

- [寫作規則](references/writing-policy.md)：文章、改寫、翻譯、篇幅及註釋
- [README 規則](references/readme-style.md)：入口文件的結構、句法及資訊順序
- [UI 規則](references/ui-style.md)：控制項、狀態、錯誤、確認及輔助功能文字
- [PR 規則](references/pr-policy.md)：commit、PR、審查及發布說明
- [Gentoo overlay 規則](references/overlay-policy.md)：gentoo-zh overlay 的附加要求
- [詞典規則](references/lexicon-policy.md)：來源優先順序、地區詞彙及專業術語

倉庫規範與近期範例決定格式、語言及術語。格式選擇會改變結果而現有資料不足時，應先向使用者確認。

## 語料與詞典

[README 語料](references/readme-corpus.json)記錄六個中文開源專案在 2019 年底前的 README 結構，並收錄專業文字模式。[UI 語料](references/ui-corpus.json)記錄六個大型開源專案的固定版本中文詞庫。兩份語料只保存結構與用法觀察，不複製來源文字，也不將口語、宣傳語或直譯句式列為規範。

內建詞典包括國家教育研究院兩岸對照計算機名詞、OpenCC、MediaWiki 地區詞轉換表、CC-CEDICT、Unihan、McBopomofo、jieba、THUOCL 與 Rime essay。萌娘百科及中文維基詞庫採可選安裝，不隨專案發布。

```bash
python3 scripts/lexicon_lookup.py '程式碼'
python3 scripts/lexicon_lookup.py 'cache' --source naer
python3 scripts/lexicon_lookup.py --reference
python3 scripts/sync_lexicons.py --verify
python3 scripts/sync_lexicons.py --source moegirl
python3 scripts/sync_lexicons.py --source zhwiki
python3 scripts/sync_lexicons.py --verify-optional
```

地區詞彙檢查目前只適用於 `zh-CN` 與 `zh-TW`，必須明確啟用。推導結果是人工審查的候選項，不會取代專案術語。

```bash
python3 scripts/chinese_lint.py --kind prose --locale zh-TW --regional docs/
```

## 驗證

提交修改前執行：

```bash
shellcheck install.sh
python3 scripts/test_chinese_lint.py
python3 scripts/test_install.py
python3 scripts/test_lexicons.py
python3 scripts/sync_lexicons.py --verify
python3 scripts/validate_repository.py --release
```

## 授權

專案原始碼、規則資料及原創文件採 [MIT License](LICENSE)。內建與可選詞庫維持各自的授權；重新散布前請查閱 [詞庫授權與出處](lexicons/ATTRIBUTION.md)。
