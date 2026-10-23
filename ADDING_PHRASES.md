# 新增生活句子

只依 Tim 在聊天指定的清單新增。目前 7 句：Thank you.、Goodbye.、What is your name?、I am ready.、Hello.、Sorry.、Please.。

1. 在 `data/phrases.json` 加資料：`id`（永久、以 `phrase_` 開頭）、`english`、`chinese`、`category`（可擴充的情境分類）、`image`（相對路徑）及可選 `audio`（英文錄音，失敗回退 en-US TTS）。勿改既有 id。
2. 依 STYLE_GUIDE 畫 512×512 SVG 情境圖，放 `images/phrases/`；重現現有圖片可跑 `python3 tools/art/draw_phrases.py`。圖片要用動作與物品表達意思，不用文字；相近句子必須有不同情境。
3. 中文意思加在 `data/voice-zh.json` 的 `zh.<phrase id>`；新增任何說明也加在該檔，跑 `python3 tools/gen-voice.py` 錄音（HsiaoChenNeural、-8%）。中文音檔失敗只顯示提示，不用 TTS。
4. 跑 `python3 tools/validate-phrases.py`、`python3 tools/test_validate_phrases.py`、`node --test tools/test_phrases.cjs` 及 AGENTS.md 全套驗收，更新精確清單測試。截圖自己看過。
5. 每輪每句最多出一次；選圖最多四張。排句子只出兩個字以上的句子，最多四個字：字卡外觀一樣、顏色每題隨機，只能靠聽；答錯後才亮出正確字卡。若將來加入更長句，先調整版面，不可直接加入超過支援範圍的資料。
   情境圖要有說話的對象（第二個人）和表情；用 `tools/art/draw_phrases.py` 的 `person()` 畫，selftest 會產生 `/tmp/ew-selftest-qa/phase-4/phrase-contact-sheet.png`（加 `--qa` 才寫進 `qa/`） 檢查七張是否一眼分得出來。
6. 只本機 commit，不推送、不部署。

句子進度沿用版本 3 的 `words` 記錄表，以 `phrase_` id 避免與單字撞號，無格式變更。生活句子區的今日複習只挑句子，優先到期及不熟的；獨立入口避免孩子在兩種內容間突然切換。每輪結算接同一個星星罐。

## 離線快取（階段 5 起）

改了句子資料、情境圖或錄音之後，跑 `python3 tools/build-sw.py` 更新 `sw.js` 的離線清單和版本號，再跑 `python3 tools/validate-words.py`（它會擋下過期的離線清單）。版本號變了，加到主畫面的 iPad 下次連網開啟時就會換成新內容。
