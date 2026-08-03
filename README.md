# Chinese Skill

約束 Claude、Codex 與 OpenCode 產生的中文。安裝名稱是 `chinese-skill`，技能內容不依賴固定來源路徑。

## 範圍

規則適用於文章撰寫、改寫、潤飾、貼入文字、對話、README、文件、介面文字、通知、日誌、測試、程式碼、註釋、審查、commit 與 PR。所有中文都需人工審查，不以副檔名區分。

主要檢查項目：

- 語法及指代是否清楚；
- 事實、原因、影響及行動是否成立；
- 是否保留機翻或英語直譯句式；
- 詞彙是否符合倉庫與技術領域；
- 是否包含口語、贅詞、自造詞或無必要的外語；
- 嚴格、學術、技術或介面風格是否符合各自限制；
- 簡體與繁體是否混用；
- 所用詞彙是否能讓不同中文地區的讀者理解；
- 是否重複差異、標題或開發者已知的機制；
- 註釋是否必要，語言是否符合倉庫規範。

PR、commit 或註釋格式不明，且格式選擇會影響結果時，先查閱倉庫規範及近期範例；仍無法確定再詢問，不自行假設。

## 安裝

需要 Python 3.11 或更新版本及 Bash。

```bash
git clone https://github.com/Zakk-LLM/Chinese-skill.git
cd Chinese-skill
./install.sh
```

預設以符號連結安裝至三個代理，並加入簡短的全域提醒。提醒要求代理在開始工作、內容壓縮、任務切換及提交文字前重新讀取技能，避免長時間工作後遺漏規則。

```bash
./install.sh claude codex
./install.sh --copy
./install.sh --status
./install.sh --uninstall
```

安裝位置：

| 代理 | 位置 |
|---|---|
| Claude | `~/.claude/skills/chinese-skill` |
| Codex | `${CODEX_HOME:-~/.codex}/skills/chinese-skill` |
| OpenCode | `~/.config/opencode/skills/chinese-skill` |

安裝腳本不覆寫其他技能。目標位置已有非本腳本建立的內容時，安裝會失敗並保留原內容。全域提醒使用標記區塊，解除安裝時只移除該區塊。
符號連結安裝要求來源目錄保留原位置；需要移動來源時，先解除安裝，或改用 `--copy`。

## 使用

代理應先讀取 `SKILL.md`。批次審查前再讀取對應參考文件：

- `references/writing-policy.md`：語法、翻譯、詞彙、邏輯、篇幅及註釋；
- `references/readme-style.md`：README 的結構、句法及專業技術文字；
- `references/ui-style.md`：介面控制項、狀態、錯誤、確認與輔助功能文字；
- `references/pr-policy.md`：PR、commit 與審查；
- `references/overlay-policy.md`：gentoo-zh overlay 的附加規則。
- `references/lexicon-policy.md`：詞典優先順序、地區詞彙及專業術語。

自動檢查只識別可穩定判斷的問題：

```bash
python3 scripts/chinese_lint.py <path>
python3 scripts/chinese_lint.py --kind source <path>
python3 scripts/chinese_lint.py --kind prose --locale zh-TW README.md docs/
python3 scripts/chinese_lint.py --kind prose --style strict article.md
python3 scripts/chinese_lint.py --kind prose --style academic paper.md
python3 scripts/chinese_lint.py --kind prose --style readme README.md
python3 scripts/chinese_lint.py --kind prose --style ui path/to/catalog
printf '%s\n' '待檢查文字' | python3 scripts/chinese_lint.py --kind prose -
python3 scripts/chinese_lint.py --kind commit-message message.txt
python3 scripts/chinese_lint.py --kind pr-body --title 'scope: summary' body.txt
python3 scripts/test_chinese_lint.py
python3 scripts/test_install.py
python3 scripts/test_lexicons.py
python3 scripts/validate_repository.py --release
python3 scripts/sync_lexicons.py --verify
```

預設的 `standard` 風格只套用通用規則，不限制 Emoji、註釋語言、PR 標題或正文長度。
`strict` 保留禁用 Emoji、英文註釋、精簡正文及精簡 PR 的要求；另有 `academic`、
`technical`、`readme` 與 `ui`。`readme` 檢查模板化開場、宣傳語、Emoji 及過長句段。
`ui` 另檢查口語錯誤訊息、位置式操作指示、重複進行標記及含糊確認文字。

`all` 模式同時檢查正文與支援的程式註釋。`-` 代表標準輸入。
`--kind source` 或 `--kind prose`
只用於刻意限制檢查範圍。`--kind commit-message` 另外檢查標題長度、結尾標點及第二行是否空白，
`--profile gentoo-overlay` 再要求英文標題與 `scope: summary` 格式。

AI 署名（`Generated with`、`Claude-Session`、指向模型的 `Co-authored-by` 等）在所有檢查模式與
profile 一律報錯；署名為人的 `Co-authored-by` 與 `Signed-off-by` 不受限制。

`strict` 會報告 Emoji、模板化 AI 開場、文章自述、宣傳形容詞、超過 80 個非空白字元的
句子及多層分句。其他風格使用各自的長度與詞句設定；完全重複的句子在所有風格都會報告。

每份內容只能使用一種簡繁字形。面向多個中文地區時採用容易理解的現代標準中文。
所在地區的正式技術用語可以保留，例如本文件使用的 `程式碼`，不需要混列其他地區的同義詞。

一般 PR 採用倉庫格式，不額外限制標題與長度。`strict` 限制 600 個非空白字元、4 個區塊及
5 個清單項目；overlay profile 限制 360、3 及 4，並套用嚴格文字規則。

`--locale` 支援 `zh-CN`、`zh-TW`、`zh-HK`、`zh-SG` 與 `zh-MY`。香港採繁體字形，
新加坡與馬來西亞採簡體字形；地區術語檢查目前只適用於 `zh-CN` 與 `zh-TW`。

資料檔只檢查包含中文的文字行，不把整個資料結構視為段落。

自動檢查通過不代表中文合格。語法、翻譯品質、術語、邏輯及註釋價值仍需人工審查。
目錄掃描會讀取 UTF-8 文字檔，但略過版本控制資料、相依套件目錄及快取；未支援的註釋語法需人工檢查。

## README 語料

`references/readme-corpus.json` 記錄截至 2019 年底六個中文開源 README 的結構觀察，
不複製原文。每個來源分別標示可借鑑與應排除的寫法；舊版中的口語、Emoji、宣傳語、
過時命令及直譯句式不會成為規範。

語料另收錄定義、因果、條件、比較及程序等專業文章模式。README 只保留讀者完成安裝、
使用、評估或貢獻所需的部分；長篇說明改用 `technical` 或 `academic` 風格。

## UI 語料

`references/ui-corpus.json` 記錄 Grafana、Nextcloud、Mastodon、Discourse、GNOME Control
Center 與 Visual Studio Code 的固定版本中文詞庫。語料只保留控制項、狀態、驗證、錯誤、
確認及輔助功能文字的共同模式，不複製原文，也不把來源中的口語或直譯當成規範。

這些固定版本不晚於 2022 年 11 月 29 日。日期與翻譯者資料只能降低生成文字介入的可能性，
不能證明每個字串的作者身分；產品詞彙與母語審查仍優先。

## 詞典

內建國家教育研究院兩岸對照計算機名詞、OpenCC、MediaWiki 地區詞轉換表、
CC-CEDICT、Unihan、McBopomofo、jieba、THUOCL 全部 11 類及 Rime essay。
萌娘百科與中文維基資料採可選安裝。查詢結果會標示來源與權威等級。

```bash
python3 scripts/lexicon_lookup.py '程式碼'
python3 scripts/lexicon_lookup.py 'cache' --source naer
python3 scripts/lexicon_lookup.py 'Gentoo Linux'
python3 scripts/lexicon_lookup.py --reference
python3 scripts/sync_lexicons.py --verify
python3 scripts/sync_lexicons.py --refresh
python3 scripts/sync_lexicons.py --source moegirl
python3 scripts/sync_lexicons.py --source zhwiki
python3 scripts/sync_lexicons.py --verify-optional
```

`--regional` 會由 OpenCC 與 MediaWiki 的轉換表推導地區用詞，屬候選而非定案，因此預設關閉，
且必須指定 `--locale`：

```bash
python3 scripts/chinese_lint.py --kind prose --locale zh-TW --regional docs/
```

`technical-terms.json` 的判斷優先於推導結果，`wording.json` 的 `regional_exceptions`
記錄兩岸皆通的詞。命中若落在更長的詞內（如 `東西向`、`連接埠`），會由 CC-CEDICT、
McBopomofo、jieba、THUOCL 及 Rime essay 的詞界資料排除。

`references/technical-terms.json` 收錄 154 條術語，涵蓋計算、開發、測試、版本控制、
安全、Linux 及 Gentoo；`enforce` 的條目才會由 `--locale` 檢查地區用詞。`--reference`
列出未內建的外部術語庫及其權威等級，供人工查證。

可選詞庫分別寫入 Git 忽略的 `lexicons/optional/<source>/`，可同時安裝。萌娘百科快照採 CC BY-NC-SA 3.0，不得用於商業散布；中文維基快照採 CC BY-SA 4.0。兩者均不隨專案發布。

專案原始碼與原創文件採 MIT License；內建及可選詞庫維持各自的授權。完整授權範圍見
`LICENSE` 與 `lexicons/ATTRIBUTION.md`。
