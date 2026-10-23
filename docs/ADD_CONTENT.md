# 新增單字／句子（給維護 bot 照做）

Tim 在聊天說「加 panda」「加 Good night.」時，照這份從頭做到尾。照順序做完就能在本機 commit，不需要懂整個程式。2026-10-23 起取代舊的 `ADDING_WORDS.md`、`ADDING_PHRASES.md`。

不變的規則：
- **只加 Tim 在聊天裡明確給的清單**，不要自己多加、刪除或改既有的字。
- 玩家還不識字：內容只靠圖片和聲音。圖片裡不能有字。
- **中文一律預錄 mp3，不能用 TTS。** 英文用裝置朗讀，或填 `audio` 欄位放預錄檔。
- 只在本機 commit。**Tim 說「推送」之前不 push、不部署**（見第 8 步）。

## 0. 開工

```bash
cd ~/repos/english-words            # 或 Tim 指定的 worktree
git status                          # 必須乾淨
git switch -c claude/add-$(date +%F)-panda <最新的開發 commit>
```

## 1. 資料格式（唯一的資料來源是 `data/`）

### 單字：`data/words.json`（陣列，順序就是卡片順序，同主題放一起）

```json
{"id": "panda", "english": "panda", "chinese": "熊貓", "image": "images/words/panda.svg", "theme": "animals"}
```

| 欄位 | 必填 | 規則 |
|---|---|---|
| `id` | 是 | 小寫英文、數字、底線，開頭是字母（`teddy_bear`）。**不可以 `my_` 開頭**（舊版家長自訂資料用過）。用了就不能改：學習進度用 id 記。 |
| `english` | 是 | 念出來的英文，小寫、單數。不分大小寫不能和別的字重複。 |
| `chinese` | 是 | 繁體中文、幼兒常用說法。單字的中文**只顯示、不念**，所以不用錄音。 |
| `image` | 是 | 相對路徑，不以 `/` 開頭（網站在 `/english-words/` 子路徑下）。 |
| `theme` | 是 | `data/themes.json` 裡的主題 id。 |
| `audio` | 否 | 英文預錄檔，例如 `audio/words/panda.mp3`。沒填就用裝置朗讀；檔案壞掉也會退回朗讀。 |

### 主題：`data/themes.json`

```json
{"id": "vehicles", "english": "Vehicles", "chinese": "交通工具", "color": "#ffd6a5", "icon": "images/words/bus.svg"}
```

`color` 用淺而亮的顏色（主題卡底色），`icon` 用這個主題裡最好認的一張單字圖。**主題的中文名稱會被念出來**（key `theme.<id>`），新增主題或改中文名稱都要錄音（第 3 步）。沒有單字的主題不會顯示。

### 句子：`data/phrases.json`

```json
{"id": "phrase_good_night", "english": "Good night.", "chinese": "晚安", "category": "greetings", "image": "images/phrases/good_night.svg"}
```

| 欄位 | 必填 | 規則 |
|---|---|---|
| `id` | 是 | `phrase_` 開頭，後面小寫英文、數字、底線。用了就不能改。 |
| `english` | 是 | **1–4 個英文字**，只能有字母、空格和 `'`，最後一定是 `.`、`?` 或 `!`。這是排句子遊戲版面的上限，`validate-phrases` 會擋。2–4 個字的句子會自動進「排句子」。 |
| `chinese` | 是 | 中文意思。**句子的中文會被念出來**（開「中」時），要錄 `zh.<phrase id>`。 |
| `category` | 是 | 情境分類：`manners`、`greetings`、`introductions`、`classroom`，或新的英文小寫字。 |
| `image` | 是 | 情境圖路徑。 |
| `audio` | 否 | 英文預錄檔，例如 `audio/phrases/phrase_good_night.mp3`。 |

超過 4 個字的句子：**停下來回報 Tim**，要先改版面，不要自己改程式。

## 2. 圖片

| 東西 | 放哪裡 | 規格 |
|---|---|---|
| 單字圖 | `images/words/<id>.svg`（或 `.png`／`.webp`） | 正方形。SVG 用 `viewBox="0 0 512 512"`；點陣圖至少 512×512（建議 1024），背景透明。照 `STYLE_GUIDE.md`：深藍粗外框、明亮平塗、角色要笑、一張圖一個主角。 |
| 句子圖 | `images/phrases/<id 去掉 phrase_>.svg` | `viewBox="0 0 512 512"`。要有說話的對象（第二個人）和表情，用動作和物品表達意思，**不能有文字**。相近的句子要畫成看得出差別的情境。 |

- Tim 給圖：轉成上面的規格（正方形、透明背景），存到對的位置。
- Tim 沒給圖：單字在 `tools/art/draw_words.py` 加一個同名函式並加進 `DRAWINGS`，跑 `python3 tools/art/draw_words.py panda`；句子用 `tools/art/draw_phrases.py` 的 `person()` 等工具。
- **一定要自己打開圖片看過**（第 6 步還要看總覽圖）。

## 3. 中文錄音（一律預錄）

要錄的只有兩種：**新主題的中文名稱**（自動從 `themes.json` 取，key `theme.<id>`）和**新句子的中文意思**（加在 `data/voice-zh.json`，key `zh.<phrase id>`）。玩法說明這類台詞也在 `data/voice-zh.json`，但新增內容不需要動它們。

```json
"zh.phrase_good_night": "晚安"
```

然後：

```bash
python3 tools/gen-voice.py                 # 只錄新的或改過的台詞（需要網路）
```

它會做兩件事：
1. 用 edge-tts `zh-TW-HsiaoChenNeural`、語速 −8% 錄成**原檔**，存到 `audio-src/zh/<key>.mp3`（iPad 不會下載這個資料夾）。
2. 呼叫 `tools/normalize-audio.py`，從原檔做出音量一致的 **`audio/zh/<key>.mp3`**（−16 LUFS、峰值 ≤ −1.5 dBTP、24 kHz／48 kbps／單聲道），並把結果寫進 `audio/zh/manifest.json`。

不要手動改 `audio/zh/` 裡的檔案，也不要從 `audio/zh/` 再處理一次：要重做一律從 `audio-src/` 開始（`python3 tools/normalize-audio.py`）。

沒有網路時，新台詞先沒有音檔也不會出錯：遊戲會**安靜跳過**那一句（不會改用 TTS），但 `validate-words` 會報錯，所以不能 commit，要等錄好。

## 4.（選用）英文預錄

預設英文用 iPad 內建朗讀。要用預錄檔時：存成 `audio/words/<id>.mp3` 或 `audio/phrases/<id>.mp3`（`.m4a` 也可以），前後不要留長空白，資料裡填 `audio` 欄位。

## 5. 驗證（照順序跑）

```bash
python3 tools/normalize-audio.py --check   # 每個中文檔 −16 ±1 LUFS、峰值 ≤ −1.5 dBTP、跟原檔對得上
python3 tools/build-sw.py                  # 更新離線清單和版本號（加了任何檔案都要跑）
python3 tools/validate-words.py            # 必須 OK
python3 tools/validate-phrases.py          # 必須 OK（每句都要有 zh.<id> 錄音）
python3 tools/check-all.py --quick         # 約 1 分鐘：單元測試、驗證、離線清單大小上限
python3 tools/selftest.py --only cards     # 加了單字或主題時（約 10 分鐘）
python3 tools/selftest.py --only phrases   # 加了句子時
```

全部要 0 失敗。單元測試和 selftest 都從 `data/` 讀清單，**加內容不用改測試**。

常見錯誤：

| 訊息 | 原因／怎麼修 |
|---|---|
| `id must not start with my_` | 換一個 id。 |
| `english '...' already used by '...'` | 這個字已經有了，回報 Tim。 |
| `theme '...' is not in themes.json` | 先加主題（第 1 步）。 |
| `... must be square` / `bitmaps need at least 512x512` | 圖片規格不對（第 2 步）。 |
| `audio/zh/<key>.mp3 missing` / `text changed since it was recorded` | 跑 `python3 tools/gen-voice.py`。 |
| `missing zh.<id> recording`（validate-phrases） | 在 `voice-zh.json` 加 `zh.<phrase id>`，再跑 gen-voice。 |
| `unsupported sentence tokens` | 句子超過 4 個字或有不支援的符號，回報 Tim。 |
| `sw.js offline file list is out of date` | 跑 `python3 tools/build-sw.py`。 |
| `the offline list is ... MB (max 2.5 MB)` / `... (max 300 KB per file)` | 圖片太大：SVG 簡化、點陣圖縮小或改 WebP。 |
| normalize `--check` 說 out of target / source changed | 跑 `python3 tools/normalize-audio.py`（從原檔重做）。 |

## 6. 自己看截圖

- `/tmp/ew-selftest-qa/phase-1/contact-sheet.png`：全部單字圖。
- `/tmp/ew-selftest-qa/phase-4/phrase-contact-sheet.png`：全部句子圖。
- `/tmp/ew-selftest-qa/phase-5/overview-words-phrases.png`（`--only look`）。

新圖要一眼認得出來、跟其他圖風格一致。不行就回第 2 步修。

## 7. 本機 commit

```bash
git add data/ images/ audio/ audio-src/ sw.js tools/art/
git commit -m "Add word: panda"
```

回報 Tim：加了什麼、commit hash、驗證結果，然後等「推送」。

## 8. 發布（只有 Tim 說「推送」之後）

1. 先跑完整驗收：`python3 tools/check-all.py`，最後一行必須是 `ALL … STEPS PASSED`（約半小時到一小時）。
2. 照 `docs/RELEASE_CHECKLIST.md` 第 4 段「之後更新網站」：在 `~/repos/english-words-release` 換成新的快照、拿掉 `qa/`、加 `.nojekyll`、`build-sw.py --check`、commit。
3. 推之前確認 `git ls-files | grep -c '^qa/'` 是 0。
4. `git push origin release:main`。**只推 `release`，開發分支永遠不推**（`qa/` 在開發分支的歷史裡，不公開）。
5. 照 RELEASE_CHECKLIST 第 3 段做上線後檢查。出問題照第 5 段 `git revert`，不要 force push。

## 附錄：舊的家長備份檔

第 8 階段以前的線上版有「家長專區」，可以匯出 `picture-words-backup-YYYY-MM-DD.json`：

```json
{"format": "picture-words-custom", "version": 1,
 "themes":  [{"id": "my_theme_pets", "english": "Pets", "chinese": "寵物", "color": "#ffd6a5"}],
 "words":   [{"id": "my_word_cat", "english": "cat", "chinese": "貓", "theme": "my_theme_pets", "image": "data:image/jpeg;base64,..."}],
 "phrases": [{"id": "my_phrase_good_night", "english": "Good night.", "chinese": "晚安", "category": "custom", "image": "images/phrases/hello.svg"}]}
```

Tim 給這種檔案並說要加進去時：只加他指定的那幾筆；去掉 `my_word_`／`my_phrase_`／`my_theme_` 前綴，照第 1 步取正式 id（句子用 `phrase_`）；`data:image/...` 照片照第 2 步重畫，或解碼存成正方形 PNG／WebP；主題和句子照第 3 步錄中文。其餘照第 5–7 步。
