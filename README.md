# Chinese Skill

[簡體中文](README.zh-CN.md) | 繁體中文

Chinese Skill 是供 Claude、Codex 與 OpenCode 使用的中文寫作與審查技能，適用於文章、文件、介面文字、程式註釋、commit 與 PR。

它檢查語法、邏輯、機器翻譯痕跡、口語、自造詞、冗長內容、簡繁混用及不必要的註釋。規則優先採用專案既有格式與術語；面向多個中文地區時，使用同一字形及各地讀者都能理解的標準中文。

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

代理應先讀取 [SKILL.md](SKILL.md)。一般使用者應直接執行工具，必要時先查閱 `--help`；只有維護或除錯腳本時才閱讀其原始碼。以下命令可檢查檔案、目錄或標準輸入：

```bash
python3 scripts/chinese_lint.py README.md docs/
python3 scripts/chinese_lint.py --kind source src/
python3 scripts/chinese_lint.py --kind prose --style readme README.md
python3 scripts/chinese_lint.py --kind prose --style ui path/to/catalog
python3 scripts/chinese_lint.py --kind prose --format json article.md
python3 scripts/chinese_lint.py --kind prose --style readme --fix README.md
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

`--format json` 輸出穩定的規則識別碼、嚴重程度、路徑、行號、訊息與樣本，供編輯器及 CI 使用。`--fail-level warning` 讓警告也產生失敗狀態。以標準輸入檢查資料檔時，使用 `--stdin-filename` 指定檔名。`--fix` 只修正全形英數、標點、空格及 README 標題句號，不改寫語法或用詞。

`--terms` 讀取專案自訂的上游命名清單，欄位與 `references/technical-terms.json` 的 `preserve_translations` 相同，同名項目以專案設定為準。文中同時出現該英文名稱與其中文寫法時才提示。

`--locale` 支援 `zh-CN`、`zh-TW`、`zh-HK`、`zh-SG` 與 `zh-MY`。香港使用繁體，新加坡與馬來西亞使用簡體；所在地區的正式技術用語可以保留。所有模式都會拒絕 AI 署名，但允許使用真實電子郵件地址的人類作者署名。

檢查器會提示高可信度的「的／得／地」錯誤與篇內術語混用。`--comment-audit` 另行提示只重述相鄰程式碼的註釋。這類提示不會自動修正；因果關係、術語選擇及註釋價值仍需人工審查。

## 專案整合

pre-commit 使用者可引用本儲存庫的 `chinese-lint` hook。GitHub Actions 可直接使用 `Zakk-LLM/Chinese-skill@版本`，並以 `path`、`kind`、`style` 與 `locale` 指定檢查範圍。

```yaml
repos:
  - repo: https://github.com/Zakk-LLM/Chinese-skill
    rev: v1.4.0
    hooks:
      - id: chinese-lint
```

```yaml
- uses: Zakk-LLM/Chinese-skill@v1.4.0
  with:
    path: docs
    style: technical
    locale: zh-TW
```

## 規則

- [寫作規則](references/writing-policy.md)：文章、改寫、篇幅及註釋
- [技術翻譯規則](references/translation-policy.md)：術語分類、上游命名、範圍限定詞及交付檢查
- [長篇文件工作流程](references/document-workflow.md)：文件用途、證據邊界、程序及讀者驗證
- [README 規則](references/readme-style.md)：入口文件的結構、句法及資訊順序
- [UI 規則](references/ui-style.md)：控制項、狀態、錯誤、確認及輔助功能文字
- [PR 規則](references/pr-policy.md)：commit、PR、審查及發布說明
- [Gentoo overlay 規則](references/overlay-policy.md)：gentoo-zh overlay 的附加要求
- [詞典規則](references/lexicon-policy.md)：來源優先順序、地區詞彙及專業術語

專案規範與近期範例決定格式、語言及術語。格式選擇會改變結果而現有資料不足時，應先向使用者確認。

各任務規則分別說明必要輸入、交付形式、禁止推斷事項及停止條件。技能會依任務載入相應規則，使用者不需手動指定。

## 語料與詞典

[README 語料](references/readme-corpus.json)記錄六個中文開源專案在 2019 年底前的 README 結構。[UI 語料](references/ui-corpus.json)記錄六個大型開源專案的固定版本中文詞庫。[寫作來源](references/writing-sources.json)記錄技術寫作指南及相似技能中可移植的工作流程。[發布語料](references/release-corpus.json)記錄大型非 AI 開源專案的發布說明來源與抽象結構。

固定檔案均記錄 commit 與 Git blob。由來源歸納的規則至少由兩個來源支持；內部規則另行標示，不宣稱由來源直接得出。來源索引不複製原文，也不將來源中的口語、宣傳語或強制流程列為通用規範。

代理不應直接載入完整語料。先列出規則識別碼，再按需取得一條規則；只有核對來源時才取得單一來源記錄。

```bash
python3 scripts/corpus_lookup.py readme --list
python3 scripts/corpus_lookup.py writing --list
python3 scripts/corpus_lookup.py release --list
python3 scripts/corpus_lookup.py readme --pattern identity
python3 scripts/corpus_lookup.py ui --pattern failure --locale zh-TW
python3 scripts/corpus_lookup.py writing --pattern reader-test
python3 scripts/corpus_lookup.py release --pattern release-contract
python3 scripts/corpus_lookup.py readme --source gogs-2019
python3 scripts/verify_corpora.py
```

`verify_corpora.py` 需要網路連線，用於核對來源路徑、commit 日期與 Git blob。GitHub 達到速率限制時，程式會要求設定 `GITHUB_TOKEN` 並以狀態碼 2 結束，不會誤報為內容不一致。

[寫作評測](evals/evals.json)保存文章、通知、PR、註釋、UI 及操作指南的固定測例。修改技能時應以相同提示比較修改前後輸出；主觀文風由盲測審查，客觀要求按評測條件核對。

[觸發評測](evals/trigger-evals.json)保存直接觸發、間接觸發、資訊不足及不應觸發的案例。`scripts/test_evals.py` 是本機結構測試，只驗證資料結構與類型覆蓋，不執行模型評測。

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

## 開發與維護

維護者應先閱讀[開發與維護](DEVELOPMENT.md)。該文件說明學習順序、規則迭代、來源要求、版本策略及發布檢查。維護報告只列出可核對的儲存庫資料，不判定文字品質。

```bash
python3 scripts/maintenance_report.py
python3 scripts/maintenance_report.py --json
```

## 驗證

一般修改使用本機檢查。公開發布必須先提交候選內容，再啟用發布模式並要求 ShellCheck；來源有變更時再加入網路核對。發布模式會拒絕未提交內容，並核對 `HEAD` 中的版本。

```bash
python3 scripts/check_repository.py
python3 scripts/check_repository.py --release --require-shellcheck
python3 scripts/check_repository.py --release --network --require-shellcheck
```

## 授權

專案原始碼、規則資料及原創文件採 [MIT License](LICENSE)。內建與可選詞庫維持各自的授權；重新散布前請查閱 [詞庫授權與出處](lexicons/ATTRIBUTION.md)。
