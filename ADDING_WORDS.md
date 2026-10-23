# 新增單字流程

給之後的 Claude 或助理照做。Tim 在聊天說「加 panda、bus」，就照下面一步一步做，最後在本機 commit（不 push）。

單字資料只有一個來源：`data/words.json`。新增的字會自動出現在卡片和所有小遊戲裡（遊戲題目由 `js/quiz.js` 從單字庫自動產生），不用改程式。

## 1. 決定 id 和主題

- `id`：小寫英文字母、數字、底線，開頭要是字母。兩個字用底線：`teddy_bear`、`ice_cream`。id 一旦用了就不要改：學習進度（`js/progress.js`）用 id 記錄，改 id 等於換一個新字、舊進度會留著不用。新增或刪除單字不會影響其他字的進度。
- `english`：要念出來、顯示的英文，小寫，一般用單數（`goat`、`teddy bear`）。不分大小寫不能和別的字重複。
- `chinese`：繁體中文，幼兒常用的說法（`乳牛`、`無尾熊`）。
- `theme`：用 `data/themes.json` 已有的主題 id。需要新主題時，先在 `themes.json` 加一筆：

```json
{"id": "vehicles", "english": "Vehicles", "chinese": "交通工具", "color": "#ffd6a5", "icon": "images/words/bus.svg"}
```

  `color` 用淺而亮的顏色（主題卡底色），`icon` 用該主題裡最好認的一張單字圖。
  主題的中文名稱會被念出來（遊戲選主題時），所以**新增主題或改中文名稱後要跑 `python3 tools/gen-voice.py`** 錄音（見第 5 步）。

## 2. 畫圖

規格全部在 [STYLE_GUIDE.md](STYLE_GUIDE.md)。重點：

- 存成 `images/words/<id>.svg`，`viewBox="0 0 512 512"`、正方形、背景透明。
- 深藍粗外框＋明亮平塗＋右下陰影＋左上高光，角色要笑。
- 一張圖一個主角，幼兒一眼認得出來。

做法：在 `tools/art/draw_words.py` 加一個同名函式（例如 `def panda():`），用裡面的 `shape`、`sit_body`、`face` 等工具畫，加進 `DRAWINGS`，然後執行：

```bash
python3 tools/art/draw_words.py panda
```

**一定要看圖**：跑完第 5 步的自測後，用 Read 看 `qa/phase-1/contact-sheet.png`（所有單字圖的總覽）。不好認或跟其他圖風格不一致就修。

改用 PNG／WebP（例如之後用 AI 生圖）也可以：正方形、至少 512×512（建議 1024×1024）、透明背景，存 `images/words/<id>.png`，`image` 欄位寫這個路徑就好，不用改程式。

## 3. 編輯 `data/words.json`

在陣列裡加一行（順序就是卡片出現的順序，同主題的字放一起）：

```json
{"id": "panda", "english": "panda", "chinese": "熊貓", "image": "images/words/panda.svg", "theme": "animals"}
```

欄位：

| 欄位 | 必填 | 說明 |
|---|---|---|
| `id` | 是 | 見第 1 步 |
| `english` | 是 | 念出來的英文 |
| `chinese` | 是 | 中文 |
| `image` | 是 | 相對路徑，不要以 `/` 開頭（網站放在 `/english-words/` 子路徑） |
| `theme` | 是 | `themes.json` 裡的主題 id |
| `audio` | 否 | 預錄發音檔，見第 4 步 |

## 4.（可選）預錄發音

沒有 `audio` 時用裝置內建的英文朗讀。想要更好聽或更準的發音，可以放錄音檔：

- 存在 `audio/words/<id>.mp3`（`.m4a`、`.wav`、`.ogg` 也可以），短短一個字、前後不要留長空白。iPad／iPhone 用 `.mp3` 或 `.m4a` 最保險。
- 在那一筆加 `"audio": "audio/words/panda.mp3"`。
- 檔案播放失敗時會自動改用內建朗讀。

## 5. 中文語音、驗證和自測

所有中文語音（玩法說明、稱讚、主題名稱）都是預錄的 mp3：微軟 Edge 神經語音 `zh-TW-HsiaoChenNeural`、語速 -8%。台詞集中在 `data/voice-zh.json`（key → 文字），主題名稱自動取自 `themes.json`（key `theme.<id>`）。**新增或修改任何中文台詞、新增主題或改主題中文名稱後**，先跑：

```bash
python3 tools/gen-voice.py           # 只錄有變動的句子（需要網路），產生 audio/zh/<key>.mp3
```

程式要說新台詞時用 `Speech.zh('<key>')`，不要把中文直接寫在程式裡。英文單字的發音不受影響（仍是 `audio` 欄位或裝置朗讀）。

```bash
python3 tools/build-sw.py            # 更新離線快取清單和版本號（加了圖片或 mp3 都要跑）
python3 tools/validate-words.py      # 必須顯示 OK，有 ERROR 就修
node --test tools/test_quiz.cjs tools/test_progress.cjs tools/test_phrases.cjs tools/test_custom.cjs   # 必須 0 fail
python3 tools/selftest.py            # 必須 0 failed（卡片＋遊戲＋進度，約 8–10 分鐘）
```

`validate-words` 會檢查：欄位齊全、id 格式、id／英文不重複、主題存在、圖片存在且是合法的正方形 SVG／PNG／WebP、audio 檔存在、每句中文台詞都有 mp3 且是用目前的文字錄的（hash 對得上，24 kHz／48 kbps／單聲道），並警告沒被用到的圖片或 mp3。另外會檢查 `sw.js` 的離線檔案清單是不是最新的：忘了跑 `build-sw.py` 會顯示 ERROR，因為新圖片不會被快取，加到主畫面的 iPad 離線時會看不到新字。

自測的截圖平常寫到 `/tmp/ew-selftest-qa/`（不會改到 commit 進去的 `qa/`），用 Read 看 `/tmp/ew-selftest-qa/phase-1/contact-sheet.png`、`/tmp/ew-selftest-qa/phase-5/overview-words-phrases.png` 和新字所在主題的卡片截圖。正式驗收時才加 `--qa` 寫進 `qa/`。

## 6. Commit（只在本機）

```bash
git add data/ images/words/panda.svg tools/art/draw_words.py audio/ sw.js
git commit -m "Add word: panda"
```

不要 push、不要部署，Tim 說推送才由助理處理。

## 範例：完整的一筆（兩個字的 id＋錄音）

```json
{"id": "black_cat", "english": "black cat", "chinese": "黑貓", "image": "images/words/black_cat.svg", "theme": "halloween", "audio": "audio/words/black_cat.mp3"}
```

## 從家長的備份檔正式加入（階段 6 起）

家長可以在 iPad 的「家長專區」（首頁左下角齒輪長按 2 秒＋算一題）自己加單字和句子，按「匯出備份檔」得到 `picture-words-backup-YYYY-MM-DD.json`。Tim 把檔案交給你、說「把這些正式加進去」時：

```json
{"format": "picture-words-custom", "version": 1, "exported": "...",
 "themes":  [{"id": "my_theme_pets", "english": "Pets", "chinese": "寵物", "color": "#ffd6a5"}],
 "words":   [{"id": "my_word_cat", "english": "cat", "chinese": "貓", "theme": "my_theme_pets", "image": "data:image/jpeg;base64,..."}],
 "phrases": [{"id": "my_phrase_good_night", "english": "Good night.", "chinese": "晚安", "category": "custom", "image": "images/phrases/hello.svg"}]}
```

1. **只加 Tim 指定的那幾筆。** 欄位和 `data/words.json`／`data/phrases.json` 一樣。
2. **換 id**：去掉 `my_word_`／`my_phrase_`／`my_theme_` 前綴，照第 1 步的規則取正式 id（句子用 `phrase_` 開頭）。`validate-words.py` 會擋下 `my_` 開頭的內建 id，因為那是留給裝置上自訂資料用的。
3. **主題**：`theme` 是 `my_theme_...` 的話，照第 1 步在 `themes.json` 加正式主題（要錄主題名稱，見第 5 步），或改成現有主題。
4. **圖片**：`image` 是內建路徑（`images/...`）就直接用；是 `data:image/jpeg;base64,...` 的照片（512×512），照 STYLE_GUIDE 重畫成 SVG 最好；要沿用照片就解碼轉存成 `images/words/<id>.png` 或 `.webp`（正方形，validate 只收 SVG／PNG／WebP），`image` 改成那個路徑。
5. **中文**：家長的句子在 iPad 上中文只顯示不念；正式加入的句子要照 ADDING_PHRASES.md 第 3 步錄 `zh.<phrase id>`。
6. 照上面第 5、6 步跑驗證、自測、本機 commit。
7. 正式版上線後，iPad 上那筆自訂資料還在（id 不同）：請家長在家長專區把它刪掉，免得同一個字出現兩次。之後再匯入舊備份時，跟內建英文相同的會自動略過。
