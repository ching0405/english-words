# 交接手冊

## 2026-10-24：動物＋數字＋顏色主題、I 的語音、星星罐、題數（Claude，本機分支 `claude/single-i-voice`，從線上版來源 `143f70b` 分出）

報告：`~/claude-runs/english/words-colors/report.md`（含截圖）。**沒有推送。**

- 單字 41 個、4 個主題：動物 16（加 cat, penguin, elephant, dog, duck, fish, shark）、萬聖節 5、數字 10（one–ten，數字＋同數量蘋果）、顏色 10（red…brown，笑臉顏料放在淺灰圓底上，白色、黑色也看得清楚）。主題名稱「數字」「顏色」已預錄。
- 排句子單獨的「I」字卡念 "eye"（`js/phrase-ui.js` `SOLO_SAY`）。
- 星星罐一罐 30 顆（`Progress` `JAR_SIZE`、`js/jar.js` `PILE`），舊存檔保留。
- 題數集中在 `js/quiz.js` `Quiz.ROUNDS`：聽音找圖 10、連連看 3 盤×3、翻牌 6 對、今日複習 9、聽句子 10、排句子 6、句子複習 6；星星 0–2 錯 3 顆、3–5 錯 2 顆。
- 選主題畫面（`#themeGrid`）：iPad 直放「今日複習＋2×2」、橫放 5 欄，不捲動；selftest 有檢查。
- 審核助理先做的 5 個 commit：大象、鴨子、鯊魚重畫，企鵝加笑臉，數字圖重新排版，排句子 9 → 6，其餘照用（詳見報告）。

## 目前狀態（第 8 階段完成，2026-10-23，Claude，本機分支 `claude/phase-8-tim-feedback`）

**這是什麼**：給還不識字的幼兒在 iPad 上玩的看圖學英文網站（純靜態 HTML＋CSS＋JS，沒有後端、沒有建置步驟）。內容是 13 個單字（動物 8、萬聖節 5）、7 句生活句子。單字區和句子區的排法一樣：上面「玩遊戲」，下面「今日複習」和瀏覽用的卡片。單字遊戲：聽音找圖、連連看、翻牌記憶；句子遊戲：聽句子找圖、排句子。中文全部是預錄 mp3（40 句，−16 LUFS），英文用裝置朗讀。很小聲的背景音樂（程式產生），首頁音符鍵可關。可以加到主畫面、離線玩。線上版（`origin/main` = `1d5953a`）還是第 7 階段，第 8 階段**沒有推送**。

**第 8 階段做了什麼**（Tim 的 4 項，計畫 `/home/box/claude-runs/english-words/phase-8-plan.md`，報告 `phase-8-report.md`）：
1. **家長功能拿掉**（`8171a87`）：齒輪、算術門、家長頁、`js/custom.js`、`js/parent.js` 和它們的測試都刪了。新增內容只照 **`docs/ADD_CONTENT.md`**（取代 ADDING_WORDS／ADDING_PHRASES）。舊裝置上的 `ew.custom.v1`、IndexedDB `picture-words`、進度裡的 `my_*` 紀錄**不讀也不刪**（退版還在）；內建進度、星星罐、Aa／中設定照用（selftest `legacy_case`）。清除進度改用 iPad 設定刪網站資料（實機清單 H 段）。
2. **句子分成瀏覽和遊戲**（`d1fc20d`）：`#phrases` 跟 `#themes` 一樣：「玩遊戲」鈕 → `#phraseGames`（聽句子找圖、排句子），下面「今日複習」卡和「句子卡」卡（0–3 星，`best.phrases`）。句子卡用單字卡的 `#cards` 畫面（箭頭、滑動、喇叭、Aa／中、念到的字會亮、開「中」接 `zh.phrase_*`，看完一疊罐子 +1）。新台詞 `phrases.home`，`phrases.pick` 不用了。還沒錄音的新台詞安靜跳過（`Speech.setRecorded`，讀 `audio/zh/manifest.json`），不用 TTS。
3. **中文音量**（`ccadaf3`）：原檔原封不動在 `audio-src/zh/`（不進離線清單），`tools/normalize-audio.py` 做出 `audio/zh/`：−16 LUFS、true peak ≤ −1.5 dBTP、24 kHz／48 kbps／單聲道、長度不變。結果 −16.2～−15.9 LUFS（原本 −21.7～−17.9），表在 `qa/phase-8/loudness.tsv`。`gen-voice.py` 錄完自動調。英文朗讀的音量在 `js/speech.js` `EN_VOLUME`（預設 1）。答對的 sparkle 音效比稱讚小 7 LU，沒有改。
4. **背景音樂**（`68e689e`）：`js/music.js` 第一次點擊後用 OfflineAudioContext 算出 32 秒無縫循環（C 大調五聲音階音樂盒，90 BPM），約 −32 LUFS；念語音時（`Speech` 的 `busy`／`idle`）降 12 dB，佇列空了 0.6 秒後回來。首頁左下（原齒輪位置）音符開關，存在 `ew.settings.v1.music`（預設開）；手機橫放在左上。切到背景淡出並讓聲音睡著，下一次點擊恢復。靜音鍵：`navigator.audioSession.type = 'playback'`（iPadOS 16.4+），音效和音樂跟語音一樣照常出聲。試聽：`python3 tools/render-bgm.py out.mp3`。
   - **v2（Tim：「太輕柔了，可以活潑一點」）**：120 BPM（原 90）、16 小節仍是 32 秒循環；旋律高一個八度、改 triangle 音色；低音改成彈跳的八分音符；加輕輕的沙鈴（反拍，只在 6 kHz 以上）和木魚（第 2、4 拍）；整體低通 3.6 kHz（原 2.4）。遊戲裡音量照舊約 −32 LUFS、閃避時 −44（`LEVEL` 1.2），閃避和開關都沒改。試聽 `~/claude-runs/english-words/bgm-preview-v2.mp3`。

**怎麼測**：`python3 tools/check-all.py`（約半小時到一小時）；`--quick` 不開瀏覽器，約一分鐘（含 `normalize-audio --check`）。selftest 多了 `--only music`，`--only parent` 和 `test_datasafety.py` 已刪。

**待 Tim 決定**：
1. iPad 實聽中文和英文是否一樣大聲（實機清單 A6）；不平衡就調 `EN_VOLUME` 或 `normalize-audio.py --target -14`，不用重錄。
2. 背景音樂好不好聽（試聽 `~/claude-runs/english-words/bgm-preview.mp3`）。
3. 什麼時候推送（照 `docs/RELEASE_CHECKLIST.md` 第 4 段）。
4. 之前留下的：翻牌記憶偶發不翻回（health-audit 第 2 項）、`sw.js` Range 416 與離線安裝失敗提示（第 10、11 項）、`Aa` 的無障礙名稱加「Aa」。

**已知限制**：全部測試都是 Chrome 無頭瀏覽器模擬 iPad；背景音樂在 iOS 被打斷後的恢復、`audioSession`、實際音量平衡都要 iPad 實機確認（`docs/IOS_DEVICE_CHECKLIST.md` A4、A6、D 段）。第一次開啟一定要有網路。Safari 分頁和主畫面 App 的進度分開存。

## 第 7 階段結束時的狀態（歷史紀錄，家長功能已在第 8 階段移除）

**這是什麼**：給還不識字的幼兒在 iPad 上玩的看圖學英文網站（純靜態 HTML＋CSS＋JS，沒有後端、沒有建置步驟）。內容是 13 個單字（動物 8、萬聖節 5）、7 句生活句子。玩法：單字卡、聽音找圖、連連看、翻牌記憶、生活句子（句子卡／聽句子找圖／排句子）、兩種今日複習、星星罐。中文全部是預錄 mp3（40 句），英文用裝置朗讀；家長可以在裝置上自己加字和句子（齒輪長按 2 秒＋算術題）。可以加到主畫面、離線玩。

**怎麼測**：`python3 tools/check-all.py`，依序跑全部測試、最後印一張總表（約一小時）；`--quick` 不開瀏覽器，約一分鐘。各步驟說明見 README 和 AGENTS.md。

- 第 7 階段收尾驗收依 Tim 的決定**只跑一輪**（全部通過就算過，有失敗或偶發才跑第二輪查原因），這一點覆蓋 AGENTS.md 原本「連跑兩次」的規定。結果：`check-all.py` 一輪 8 步全過（13:44–14:07）：Node 55／0、test_validate_words 22／0、test_validate_phrases 3 OK、兩個 validate OK、build-sw OK（`51c8a31903ae`，1.27 MB）、test_datasafety 99／0、**selftest 2082／0**（phase 6 基準 1955／1956，加上新的 a11y 128 項）。沒有失敗或偶發，所以沒有跑第二輪。
- 這一輪沒有加 `--qa`，所以 phase 1–6 的截圖沒有重寫；新的截圖只有 `qa/phase-7/` 三張焦點狀態圖。

**效能**：第一次開啟會下載並快取 88 個檔案，共 1.27 MB：audio 749 KB、icons 153 KB、images 142 KB、js 約 140 KB、css 33 KB、index.html 18 KB。最大的單檔是 `icons/icon-512.png`（51 KB）。`build-sw.py --check` 會擋下總量超過 2.5 MB 或單檔超過 300 KB。之後的開啟全部從快取讀。

**無障礙（第 7 階段做了什麼、驗證到哪裡）**：
- **按鈕標籤**：Lighthouse 無障礙 1.00、axe 每個畫面 0 violations（階段 5、6）。之後 `index.html` 沒有改過，CSS 只多了焦點框。`selftest --only a11y` 又用 Tab 走過每個畫面，確認每個控制項都有名稱。
- **焦點**：
  - 換畫面時，焦點會移到新畫面的第一個按鈕（`js/app.js` `keepFocus`）。只在焦點原本停在被藏起來的畫面時才移，所以用手點的時候不會出現焦點框。
  - 用 Escape 關掉算術題，焦點會回到齒輪。
  - 所有按鈕都有 4px 藍色虛線焦點框；原本遊戲圖卡、翻牌、主題小籤、星星罐只有瀏覽器預設的細框，幾乎看不見。
  - 測試會在三種 iPad 上檢查：焦點會跟著換畫面、看得到框、有名稱，以及點擊不出框。舊程式在同一組測試會失敗 63 項。
- **動畫減量**：系統開了「減少動態效果」時：
  - 換畫面沒有動畫；點圖片只微亮、不搖；答對沒有星星飛散；
  - 結算星星照樣顯示；齒輪長按照樣能開。
  - 測試同時在一般模式下確認量得到動作，所以這些檢查不是空的。
- **axe 的 incomplete（要人工判讀的項目）**：已逐項看過，結論如下。
  - 21 項 `color-contrast`：背景是點點漸層，axe 算不出對比；文字對比另由 selftest 的 `CONTRAST` 檢查（≥ 4.5:1）涵蓋。
  - 4 項 `label-content-name-mismatch`：只有 `Aa` 按鈕的名稱「顯示英文字 Show English」沒有包含畫面上的「Aa」，會影響用語音控制說「Aa」的人。這是建議修改，因為不動家長開關所以沒有改。
  - 階段 6 的 `aria-allowed-role` 這次沒有出現。
- **還沒驗證**：VoiceOver、「減少動態效果」在 iPad 實機上的表現，見 `docs/IOS_DEVICE_CHECKLIST.md` G 段。另外，遊戲選項按鈕的名稱就是英文答案（例如 `monster`），VoiceOver 使用者聽得到答案。玩家是不識字的幼兒、不會用 VoiceOver，所以沒有改，只記在這裡。

**上線**：照 `docs/RELEASE_CHECKLIST.md`。Tim 已決定 repo 名稱 `english-words`，`qa/` 不公開：做一個沒有歷史的 `release` 分支，只推那個分支，開發分支永遠不推。**等 Tim 說「推送」才做。**

**實機測試**：`docs/IOS_DEVICE_CHECKLIST.md`，A–H 八段，給 Tim 用 iPad 照著勾。加到主畫面、離線、更新這三段要網站上了 https 才測得到。

**待 Tim 決定**（都還沒做）：
1. iPad 靜音鍵下，音效要不要照樣出聲（health-audit 第 5 項，一行程式）。
2. 翻牌記憶偶發「翻錯不翻回」：原因還沒找到，selftest 有診斷，最近兩次完整驗收都沒出現（health-audit 第 2 項）。
3. `sw.js` Range 請求超出範圍時回 416（第 11 項）；離線安裝失敗給家長提示（第 10 項）。兩項都是低風險建議。
4. `Aa` 按鈕的無障礙名稱加上「Aa」（見上面），會改到家長開關的標籤，但不動位置。
5. 什麼時候推送、要不要先推上去當測試網址給 iPad 實測。

**已知限制**：
- 全部測試都是 Chrome 無頭瀏覽器模擬 iPad，沒有在 iPad Safari 實機測過。
- 沒有真實幼兒試玩。
- 第一次開啟一定要有網路。
- Safari 分頁和主畫面 App 的進度分開存。
- 家長自錄中文沒有做。

## 階段 6：家長在裝置上自己加單字／句子（Claude，分支 `claude/phase-6-parent-add`；第 8 階段已移除）

**2026-10-23 Codex 收尾驗收完成**：本機分支 `codex/phase-6-acceptance`，由 `4997486` 接手。最終同一測試版本 `278b0ea` 的完整 selftest 依序兩次均 **1955 passed／0 failed**；正式家長 `--qa` 為 **263／0**，67 張截圖在 `qa/phase-6/`，已人工檢視。Node 51／0、兩組資料驗證與錯誤案例、`build-sw --check` 全過。三種 iPad 的家長空頁／有資料頁／新增表單完整 axe 共九次 0 violations（`axe-results.json`）。齒輪增加瀏覽器時鐘邊界測試，900ms 放手／移出／取消不開門、1999ms 關、2000ms 開，未發現提早放手開門的程式錯誤，`js/parent.js` 未改。修正測試復原導航等待隱藏按鈕的問題，並保留超時完整診斷。前期失敗與未重現情況沒有省略，詳見 `/home/box/claude-runs/english-words/phase-6-acceptance-report.md`；摘要在 `qa/phase-6/acceptance-results.txt`。正式截圖不受其他 baseline 的共用暫存目錄影響；最終兩輪改用各自的 `/tmp` 子目錄。iPad 實機待確認項目見報告。只做本機 commit，未推送、未部署，不開始第 7 階段。

內建資料沒有變：`data/words.json` 13 字、`data/phrases.json` 7 句。家長加的東西只存在那台裝置。

- **入口**：首頁左下角的齒輪（iPad 92px 觸控區，淡色）。要**按住 2 秒**（按住時圈圈慢慢填滿）才會跳出「請家長算一算：a + b = ?」（a 11–19、b 6–9，答案 17–28），答對才進「家長專區」。快點一下只顯示一行給家長看的提示，不出聲。Aa／中開關沒有移動（仍在單字卡上方）。用鍵盤（沒有指標）按齒輪會直接出算術題。
- **家長專區**（`#parent`）：文字給大人看，按鈕和輸入框 64px 高、字 22–24px。可新增／編輯／刪除自訂單字和句子、匯出／匯入備份、清除學習進度（自訂資料保留）。新增表單（`#parentEdit`）：英文（「聽英文」用裝置朗讀試聽）、中文（只顯示，不念）、主題（現有主題，或「＋ 新主題…」填中文名稱，英文名稱可不填）、圖片（「拍照或選照片」= `<input type="file" accept="image/*">`，iPad 會問拍照或相簿；或「從內建圖片選」，列出全部 13 張單字圖和 7 張情境圖）。照片從中間裁成正方形，縮成 512×512 JPEG（品質 0.85）。
- **檢查**：單字英文只能有字母、空格、- 和 '（最多 24 字），句子最多 4 個英文字（排句子遊戲的版面只放得下 4 張字卡），跟內建或其他自訂的英文重複會被擋下，中文必填。錯誤用紅字中文提示，不會存。
- **資料**（`js/custom.js`）：清單存在 localStorage `ew.custom.v1`（`{version:1, themes, words, phrases}`，欄位和 `data/*.json` 相同），照片存在 IndexedDB `picture-words`／`photos`（清單裡只寫 `"idb"`）；IndexedDB 不能用時照片直接放在清單裡。id 前綴 `my_word_`／`my_phrase_`／`my_theme_`，`validate-words.py` 禁止內建 id 用 `my_` 開頭，所以不會撞號。清單壞掉時原文存到 `ew.custom.broken`，從空的開始。載入時 `App` 把內建＋自訂合併（`applyData()`），之後每次改動都重新合併，不用重新整理。
- **進到哪裡**：自訂單字進單字卡（自訂主題有自己的主題卡，圖示是第一個字的圖；放進內建主題就排在那個主題最後）、聽音找圖、連連看、翻牌記憶、今日複習；自訂句子進句子卡、聽句子找圖、排句子（2–4 個字的句子）、句子複習。進度照常記在 `ew.progress`。
- **聲音**：英文照舊用裝置朗讀（en-US）。自訂內容沒有中文錄音，所以中文**只顯示文字**：句子卡開了「中」也不會播 `zh.my_*`；遊戲選主題時，自訂主題念它的英文名稱（沒填就不出聲），不播 `theme.my_*`。沒有新增中文台詞，仍是 40 句；沒有任何中文 TTS。
- **刪除**：刪掉的字／句子連同它的學習紀錄（`Progress.forget`）和照片一起清掉；自訂主題沒有字了就自動刪掉，連同主題星星。內建字、句子、星星罐都不動。
- **匯出／匯入**：匯出 `picture-words-backup-YYYY-MM-DD.json`（`format: "picture-words-custom"`、`version: 1`，照片是 data URL，內建圖是路徑）。iPad 有分享面板時用分享（存到檔案、AirDrop、傳訊息），否則直接下載。匯入先整份檢查（JSON、格式標記、版本、每一筆的 id／英文／中文／主題／圖片），任何一筆不對就整份不匯入，顯示「沒有匯入：<原因> 原本的資料都沒有改變。」；照片會重新解碼縮成 512×512，打不開也整份不匯入。同 id 的更新，英文跟內建或其他自訂重複的略過並列出來。正式加進 `data/` 的步驟見 `ADDING_WORDS.md` 最後一節。
- **離線**：家長頁在 `index.html` 裡，新的 `js/custom.js`、`js/parent.js` 已進 `sw.js`（`build-sw.py`），自訂資料在 localStorage／IndexedDB，離線可新增、可玩（selftest `pwa` 有測）。
- **P5-a**：翻牌記憶翻錯的兩張還沒翻回去時，點別張那張會輕輕左右搖一下（`wiggle`，最大 9°，不翻面）。
- **測試**：`node --test tools/test_custom.cjs`（id、檢查、壞檔、合併）、`test_progress.cjs` 加 `forget`；`selftest.py --only parent`（三種 iPad＋手機直向）：防誤觸（快點、放太早、答錯都進不去）、新增（照片＋新主題、內建圖、兩句句子）、擋下重複／缺中文／太長、編輯、重新整理後還在、照片 512×512 在 IndexedDB、單字卡、三個遊戲、今日複習、聽句子找圖、排句子、匯出、刪除（進度、照片、空主題一起清）、四種壞檔、匯入、重複略過、內建進度不變、`data/` 仍 13／7、沒有中文 TTS、axe 0 violations（家長頁與表單；axe-core 從 `~/.npm/_npx` 讀，沒有就略過並印出提示）。截圖在 `qa/phase-6/`（`--qa`）。
- **還沒做**：家長自己錄中文（MediaRecorder）是選配，沒做。沒在 iPad 實機試過拍照、分享面板匯出、IndexedDB 容量。

## 階段 5：美化＋可加到主畫面離線玩（Claude，分支 `claude/phase-5-polish-pwa`）

單字和句子都沒有增加（13 字、7 句不變，Tim 還沒給新清單）。

- **驗收問題修正**：排句子時整句英文先藏起來（`visibility:hidden`，位置保留不跳動），排完整句才顯示當獎勵（L-a）。`tools/selftest.py` 平常截圖寫到 `/tmp/ew-selftest-qa/`，只有 `--qa` 才寫進 `qa/`；聽音找圖「再問一次」截圖檔名每次固定（L-b）。
- **加到主畫面（PWA）**：`manifest.webmanifest`（standalone、奶油底、黃色主題色）、`icons/`（獅子圖示：192、512、maskable 512、apple-touch 180，由 `tools/art/make-icons.py` 用 Chrome 產生）、`index.html` 加 manifest、apple-touch-icon、apple-mobile-web-app-* meta。
- **離線**：`sw.js` 第一次開啟就快取全部 86 個遊戲檔案（頁面、程式、資料、圖片、全部 40 個中文 mp3、圖示），之後全部從快取讀；音檔的 Range 請求回 206（iPad Safari 的 `<audio>` 需要）。英文單字和句子用的是 iPad 內建朗讀（Samantha 等內建語音），離線也能念。
- **更新版本**：`python3 tools/build-sw.py` 把檔案清單和「全部檔案內容的 hash」寫進 `sw.js` 的 `VERSION`。任何檔案改了 → 版本變 → iPad 下次連網開啟（或從背景切回來）時裝新版、快取新檔、刪舊快取。`js/pwa.js` 等孩子回到首頁才重新整理，不會在遊戲中途跳掉；進度存在 localStorage，不受影響。`validate-words.py` 會擋下忘了跑 `build-sw.py` 的情況。
- **美化**：換畫面淡入上浮、選單卡依序彈入、答案圖依序彈入、答對時星星飛散、結算星星不旋轉只彈出並配三聲遞升的 ding、按鈕 pop 聲、音效限幅器。大字高對比：iPad 按鈕放大（92／116／150px）、排句子字卡 124px、iPad 橫放排句子改成左圖右字卡、首頁標題和按鈕加大、次要文字加深（≥4.5:1）、`Aa` 開關開啟色改深藍、中文輔助字改深紅、填好的格子不再變淡、支援「增加對比」。詳見 `STYLE_GUIDE.md`。
- **測試**：`selftest.py` 新增 `--only pwa`（離線重新載入、玩、mp3、Range、版本更新只在首頁重整）和 `--only look`（三種 iPad：大按鈕、文字對比、換畫面動畫、星星飛散、排句子先藏後顯示、版面，截圖到 `qa/phase-5/`，另有全部單字＋句子圖總覽 `overview-words-phrases.png`）。一般 selftest 的瀏覽器把 service worker 擋掉（`service_workers="block"`），讓測試用的短音檔攔截照常有效。`tools/lighthouse.py`：Lighthouse 11.7.1 的 PWA＋無障礙分數，加上 axe-core 逐畫面檢查（需要網路下載 Lighthouse 一次）。
- **部署注意**：GitHub Pages 是 https，service worker 可用；本機 `python3 -m http.server` 用 127.0.0.1 也可用。網址底下要有 `sw.js`（已在根目錄）。還沒在 iPad 實機測過「加入主畫面 → 飛航模式 → 開啟」。


## 階段 4 修正（Claude，分支 `claude/phase-4-fix`）

依 Grok Bot 驗收報告（`phase-4.review.md`）修正，以下取代階段 4 段落中對應的描述：

- **排句子要先聽才排得出來**：只出多字句（Thank you、What is your name?、I am ready，一輪 3 題，`PhraseQuiz.orderable`）。下排字卡外觀一樣（喇叭圖示＋每題隨機發的顏色，顏色不代表順序），上排格子是空白虛線框，只有「下一格」有黃框表示放的位置。點字卡念那個字，再點同一張（或點黃框格子）放進去。放錯 → 輕搖＋「再聽一次喔」＋重念整句，這時正確字卡才發光提示。說明和題目念完之前點字卡只會搖一下、不出聲，不會打斷排隊中的英文句子（`#playStage[data-listening]`）。
- **說明語音縮短**（全部 ≤4 秒）：選單 2.2 秒、句子卡 3.7、聽句子找圖 3.1、排句子 3.8、複習 3.4。
- **情境圖重畫**（`tools/art/draw_phrases.py`）：每張都有兩個人和表情，同一個小主角（藍衣服、咖啡色頭髮）出現在每張圖。Hello 在門口迎接來的朋友、Goodbye 坐車離開從車窗揮手、Thank you 兩人之間遞禮物＋愛心、Please 雙手合十看著大人手上的蘋果、Sorry 擔心的臉＋倒掉的積木＋難過的朋友、I am ready 背書包比讚＋綠色勾勾、What is your name? 人像問號對話框＋朋友胸前名牌。
- **中文意思語音**：家長開「中」時，句子卡念完英文會接著播 `zh.phrase_*` 預錄 mp3；答對時也是英文接中文再稱讚。
- **句子複習**：一輪 4 題，到期的先，再來是答錯還沒學回來的（box 0），結束時說「句子複習完成，好棒！」。
- 聽句子找圖：點錯的圖變灰、再點不會重複回饋。排句子有自己的選單圖示 `#g-order`。手機窄螢幕進度星星不折行；iPad 直放和手機的情境圖放大。
- 中文台詞共 40 句。

## 階段 4：生活簡易句子

本機分支 `codex/phase-4-phrases`，階段 4 已完成。完整 selftest 連續兩次為 **1576 passed／0 failed、1575 passed／0 failed**；Node 與兩組 Python 驗證／錯誤案例測試全過。只做階段 4，未推送、未部署，不開始階段 5。

本機功能 commit：`4969691`（資料／SVG／錄音）、`0c5eb25`（三玩法／複習）、`a0515ea`（版面修正／完整測試）。最終交接 commit 另收錄本檔及驗收截圖。結果摘要在 `qa/phase-4/acceptance-results.txt`；完整繁中報告位於 `/home/box/claude-runs/english-words/phase-4-report.md`。

- 首頁只有「單字」與「生活句子」兩個入口；「玩遊戲」在單字主題頁，仍只有原來三種遊戲。家長 Aa／中開關位置不變；設定套用到句子文字。
- `data/phrases.json` 只含 Tim 指定的 **7 句**：Thank you.、Goodbye.、What is your name?、I am ready.、Hello.、Sorry.、Please.。13 個單字完全不變。
- `images/phrases/` 有七張情境 SVG；`tools/art/draw_phrases.py` 使用現有插圖工具重現。揮手離開帶行李／門口迎接、收禮、詢問人像、舉手、打翻杯子幫忙擦拭、伸手請求蘋果，各用不同動作與物品區分。
- `js/phrases.js`：純函式，拆字、順序判定、每輪不重複、最多四張選圖。`js/phrase-ui.js`：三種玩法及獨立今日複習入口。透過新增的 `Games.open` 介面沿用遊戲殼的計時器、取消、溫和答錯、語音稱讚、結算與星星罐。句子模式未登記到原有的三遊戲選單。
- 句子卡點圖／喇叭念整句，讀完可下一張；看完七張給星星。圖片搖擺＋發光；英文開啟時依 TTS boundary 亮字。沒有 boundary 時使用近似節奏提示；預錄英文依播放位置近似提示，不影響判定。
- 聽句子找圖每題四張圖，沒有文字選項；一輪七句各一次。排句子先聽整句，點下面圖形字卡聽單字，再點上面亮格放入；同色同形狀提示讓不識字的孩子也能玩，錯了輕搖並重念整句。不扣星，完整一輪給三顆星。
- 句子英文 en-US、速度 0.72（單字仍 0.85），有 `audio` 優先；失敗回退英文 TTS。中文全部預錄，**已移除舊的中文 TTS 回退**，音檔失敗只顯示提示。
- 進度仍是 v3、仍存在 `ew.progress.words`，句子 ID 全部 `phrase_` 開頭，與單字不撞號；看過／答對／答錯、隔天到期與時鐘防護沿用原實作。無格式變更，因此不需要新遷移。句子有自己的今日複習，避免幼兒突然被切換到單字題；到期與不熟的優先選入。
- 新增方法見 `ADDING_PHRASES.md`；驗證 `python3 tools/validate-phrases.py`、錯誤案例 `python3 tools/test_validate_phrases.py`、單元 `node --test tools/test_phrases.cjs`。整站 `python3 tools/selftest.py` 包含句子區五種尺寸；`--only phrases` 可獨立跑。截圖在 `qa/phase-4/`。
- 尚未用真實幼兒或 iPad Safari 實機驗證。圖形提示屬入門鷹架，能保證不用讀字，但不能據此聲稱孩子已獨立理解英文語序。門口 Hello 與離開 Goodbye 的情境，以及 Please／Thank you／Sorry 的禮貌含意，第一次仍宜家長陪玩。

## 階段 3 交接紀錄（以下單字流程仍適用）

- 學習進度＋今日複習＋星星罐：每個字的紀錄存在這台裝置；主題卡 0–3 顆星（只升不降）；主題頁最前面的「今日複習」卡片用待複習單字的小圖表示（沒有就打勾），玩法在四種之間輪流；每輪的星星飛進首頁／主題頁看得到的星星罐。

（以下為階段 2 的內容，仍然有效）

- 看圖單字卡：首頁 →（語音）選主題 → 單字卡。點圖片有每個字自己的左右搖擺＋音效，再念英文；看完整疊有稱讚。
- 小遊戲：首頁 →「玩遊戲」→ 遊戲選單（可選主題）→ 聽音找圖、連連看、翻牌記憶 → 星星結算。
- 13 個字、2 個主題（動物 8、萬聖節 5）。（階段 3 已完成，見上方。）

## 檔案結構

```
index.html              畫面：#home、#themes、#cards、#games、#phrases、#phraseGames、#play、#result（全部用相對路徑）
css/app.css             版面與風格（iPad 優先；顏色見 STYLE_GUIDE.md）
js/data.js              Data：讀 JSON、依主題篩選單字、設定（Aa／中、音樂；localStorage ew.settings.v1）
js/speech.js            Speech：單一播放佇列。英文單字（錄音檔優先、否則 TTS en-US）、中文台詞（預錄 mp3，失敗顯示提示，無中文 TTS）
data/voice-zh.json      中文台詞清單（key → 文字），主題名稱另取自 themes.json（theme.<id>）
audio/zh/               中文台詞 mp3（zh-TW-HsiaoChenNeural，-8%，normalize 到 −16 LUFS）＋ manifest.json（文字、hash、原檔 sha、增益、響度）
tools/gen-voice.py      錄中文台詞（edge-tts，只錄有變動的句子；原檔進 audio-src/zh/，再自動 normalize）
js/fx.js                Fx：Web Audio 合成音效＋左右搖擺動作（Web Animations），每個字有固定一種搖法
js/quiz.js              Quiz：出題引擎（純函式，瀏覽器和 Node 共用）
js/progress.js          Progress：每字學習紀錄＋日曆天間隔複習＋時鐘防護＋星星罐／主題最佳星數＋存檔版本／遷移／損毀重置（瀏覽器和 Node 共用）
js/jar.js               Jar：星星罐畫面、星星飛進罐子、裝滿慶祝
js/games/shell.js       Games：遊戲選單、主題選擇、語音回饋、星星結算、計時器管理
js/games/<id>.js        各遊戲：listen 聽音找圖、match 連連看、memory 翻牌記憶
js/app.js               畫面切換（App.show）、卡片、滑動、文字開關、內建＋自訂資料合併
js/music.js             Music：背景音樂（OfflineAudioContext 產生 32 秒循環、閃避、開關）
js/phrase-ui.js         句子遊戲（聽句子找圖、排句子）和句子今日複習；句子卡在 #cards（app.js openDeck）
audio-src/zh/           中文台詞原檔（edge-tts 原樣，不進離線清單）
tools/normalize-audio.py 從原檔做出 −16 LUFS 的 audio/zh/（--check 只量）
tools/render-bgm.py     背景音樂試聽檔與響度量測
docs/ADD_CONTENT.md     新增單字／主題／句子的唯一流程（給維護 bot）
data/words.json         單字（唯一資料來源）
data/themes.json        主題
images/words/<id>.svg   單字圖（由 tools/art/draw_words.py 產生）
tools/art/draw_words.py 插圖產生器（共用畫圖工具＋每個字一個函式）
tools/validate-words.py 資料驗證（只用標準函式庫）
tools/test_validate_words.py  驗證器的錯誤案例測試
tools/test_quiz.cjs     出題引擎單元測試（node --test）
tools/test_progress.cjs 學習進度單元測試（Asia/Taipei 時區）：日曆天到期、時鐘前後跳、星星只升不降、星星罐、輪流、遷移、損毀、單字增減
tools/selftest.py       Playwright 自測（5 種尺寸；--only cards|games|progress|phrases|pwa|look|a11y|music；--qa 才把截圖寫進 qa/）
tools/check-all.py      一鍵跑全部測試，最後印總表（--quick 不開瀏覽器）
tools/build-sw.py       更新 sw.js 的離線檔案清單和版本號（--check 只檢查，並限制首次下載 ≤ 2.5 MB、單檔 ≤ 300 KB）
tools/lighthouse.py     Lighthouse PWA／無障礙＋axe 逐畫面檢查（--url 檢查線上網址）
docs/IOS_DEVICE_CHECKLIST.md  iPad／iPhone 實機測試清單（給 Tim）
docs/RELEASE_CHECKLIST.md     上線前檢查＋GitHub Pages 設定步驟（等 Tim 說推送）
tools/art/make-icons.py 主畫面圖示
sw.js、js/pwa.js        離線快取、註冊與版本更新
manifest.webmanifest、icons/  加到主畫面
qa/phase-1/             卡片截圖、contact-sheet.png（全部單字圖總覽）
qa/phase-2/             遊戲截圖：每個遊戲的答錯、答對、結算、版面
qa/phase-3/             進度截圖：新裝置、隔天待複習小圖、四種複習玩法、答錯再問一次、星星罐（空／半／快滿／滿／架子）
```

## 資料格式

`data/words.json`：陣列，順序就是卡片順序。

```json
{"id": "goat", "english": "goat", "chinese": "山羊", "image": "images/words/goat.svg", "theme": "animals", "audio": "audio/words/goat.mp3"}
```

`audio` 選填；有填就先播放錄音，失敗或沒填就用 TTS。

`data/themes.json`：

```json
{"id": "animals", "english": "Animals", "chinese": "動物", "color": "#9ddc8c", "icon": "images/words/lion.svg"}
```

沒有單字的主題不會顯示。

## 給之後階段共用的介面

- `Data.loadWords()` → `{words, themes}`；`Data.wordsInTheme(words, themeId)`（不給 themeId 就是全部單字）；`Data.getJSON(url)` 給之後的 `data/phrases.json` 用；`Data.settings.load()/save()`（`showEnglish`、`showChinese`，存在 `ew.settings.v1`）。
- `Speech.play(item, {queue, onend})`：item 是 `{english, audio?}`（單字或之後的生活短句都可以）。`Speech.zh(key, {queue, onend})`：播 `audio/zh/<key>.mp3`，失敗顯示可見提示，不用中文 TTS。`queue: true` 會排在正在播的後面（中文說明 → 英文單字的順序靠這個），不排隊就先停掉舊的。`Speech.say(text, {lang})` 只用 TTS。`Speech.on(fn)` 收到 `start / end / error / unsupported`。
- **新增或修改中文台詞**：改 `data/voice-zh.json`（或主題中文名稱），跑 `python3 tools/gen-voice.py`，程式用 `Speech.zh('<key>')`。`validate-words` 會擋下沒重錄的台詞。目前 40 句（含句子區台詞及 2 個主題名稱），沒有任何中文走 TTS。
- 首頁 `.home-menu` 只有單字與生活句子兩個入口；單字遊戲入口在主題頁。
- `Fx.tap(el, word)`：點單字圖的搖擺＋音效（只有左右搖擺：wiggle／swing／sway，不轉圈、傾斜不超過 15 度）；`Fx.sound(name)`、`Fx.move(el, name)` 可單獨用。新動作會取消同一元素上正在跑的動作，新音效會停掉上一個，所以連點不會疊加。系統開了「減少動態效果」時改成輕微變亮。

## 學習進度、今日複習、星星罐（階段 3＋修正）

- 存在 localStorage `ew.progress`（版本 3）：`{version, words: {<id>: {seen, right, wrong, last, box, due}}, best: {<theme>: 0–3}, jar: {stars, full}, reviewTurn}`（時間是毫秒）。用單字 id 當 key，新增／刪除單字不會動到別的字。
- **到期用本地日曆天**：第一次看到 → 明天 0:00；到期時第一次就答對 → 升一箱，下次 1、2、4、8、16 天後的 0:00；答錯 → 回到第 0 箱、明天 0:00（不再 5 分鐘後）。還沒到期又答對只記次數。
- **答錯當場再問一次**：聽音找圖、連連看在同一輪中答錯的字，會在這一輪最後各用一題「聽音找圖」再問一次（`api.askAgain`，聽一個字、選 4 張圖；每個字只一次）。第一題再問之前先播預錄的「剛剛那個字，再聽一次，找出對的圖片。」（`game.ask_again`，一輪只播一次，英文字排在它後面）。只有答錯後這輪又出現過的字（字少的主題會重複出字）才不再問，因為那次已是第二次機會。再問的順序不會讓同一個字連續兩題；如果唯一要再問的字就是最後一題才答錯的字，先插一題這輪已答對的字（不記進進度）當過渡，再問那個字。不論再問的結果對錯，那個字都排明天 0:00。上方進度星星會多出對應的格子。翻牌記憶不再問。
- **時鐘防護**：讀檔和每次使用時，`last` 在未來就改成現在；`due` 超過「今天＋該箱間隔＋1 天」就拉回「今天＋該箱間隔」。所以 iPad 時鐘被往前調再調回來，字也不會卡住一年，存檔格式不會壞。
- 誰寫紀錄：單字卡每顯示一張 → seen；聽音找圖、連連看 → 第一次就對記 right，先錯一次記 wrong（之後答對只算 seen）；翻牌記憶只記 seen。
- **主題星星只升不降**：0 還沒碰／1 開始了／2 一半以上在第 2 箱以上／3 全部在第 2 箱以上；記住最高值 `best`，答錯不會收回星星（排程照舊重來）。
- **今日複習**：卡片上是待複習單字的小圖（最多 5 個，更多加一個「+」），沒有就打勾；沒有數字和文字。點了先說「今天要複習的字來囉！」（沒有到期就說「今天的字都複習好了！我們再多練習幾個。」），再接該玩法的說明。玩法輪流：聽音找圖 → 連連看 → 翻牌記憶 → 看卡片 → …（`reviewTurn` 存檔）。題目都用 `Progress.reviewSet(words, 6)`：到期的字先（弱的、拖最久的先），不夠補最不熟的字。看卡片模式看完全部 → 3 顆星（只記 seen）。返回鍵回主題頁。
- **星星罐**（`js/jar.js`）：首頁右上、主題頁右上、結算畫面都有。每輪結束（遊戲、今日複習、卡片看完一輪）把這輪的星星飛進罐子（遊戲／複習 1–3 顆，卡片看完一輪 1 顆，卡片模式複習 3 顆），語音「星星罐又變滿一點了！」。12 顆裝滿 → 發光＋音效＋「星星罐裝滿了！好棒！我們換一個新的罐子。」，滿的罐子放到旁邊的小架子（最多畫 4 個，更多一個「+」），換新的空罐。點罐子會說「這是你的星星罐，玩完一輪就會放進星星喔！」。
- 結算畫面跳出的角色是**這一輪出現過的字**。
- 存檔版本：`VERSION = 3`，`MIGRATIONS[1]`（v1 平面計數，沒發佈過，為之後改格式準備）、`MIGRATIONS[2]`（階段 3 第一版 → 加 best／jar／reviewTurn）。解析失敗、版本比程式新、格式不對 → 原內容存到 `ew.progress.broken`，重新開始；單一欄位壞掉只修那個欄位（罐子星星超過 12 會換算成滿罐）。localStorage 被擋時改存在記憶體。
- 清除進度：遊戲裡沒有按鈕（第 8 階段）。家長用 iPad 設定刪網站資料（實機清單 H 段）；開發用主控台 `Progress.clear()`。

## 小遊戲怎麼運作

- 出題：`Quiz.questions({words, themeId, count, choices, rand})` 給「聽一個字、從幾張圖選」的題目；`Quiz.boards()`／`Quiz.pick()` 給連連看、翻牌用的一組不重複單字。干擾選項先用同主題，不夠才跨主題補（萬聖節只有 5 個字時，翻牌會借 1 個動物）。單字比題目少時，字會重複出現但不會連續兩題一樣。
- 每個遊戲是一個模組：`Games.register({id, zh, en, icon, color, intro, start(api)})`。`api` 提供 `word()`（念英文）、`zh()`（中文語音）、`right(el, next)`（動作＋音效＋稱讚，說完再進下一題）、`wrong(el, word)`（溫和搖一下＋「再聽一次喔」＋再念一次）、`dots()`／`dot()`（上方進度星星）、`later()`（離開遊戲會自動取消的計時器）、`finish(ok, fair)`（依答錯次數給 1–3 顆星，玩完至少 1 顆）。
- 加新遊戲：新增 `js/games/<id>.js` 呼叫 `Games.register`，在 `index.html` 加 `<script>` 和選單圖示（`<symbol id="g-<id>">`），在 `css/app.css` 加版面，在 `tools/selftest.py` 加一輪自動遊玩。
- 每輪 6 題：聽音找圖每題 4 個選項；連連看 2 盤 × 3 對；翻牌 6 對（12 張）。
- 全部不需識字：題目用聽的，選項都是圖片，答案按鈕上沒有任何文字（自測會檢查），自測也只靠「聽到的字」來答題。遊戲卡片上的英文名稱跟著 `Aa` 開關。

## 語音（iOS 注意事項）

- iOS Safari 只允許在使用者點擊當下開始說話或出聲。所以首頁兩個按鈕都會先解鎖：說一句無聲的話、用共用的 `<audio>` 播一小段靜音、啟動 Web Audio。卡片的 `play/zh` 都直接在點擊處理裡呼叫；排在佇列後面的（例如中文說明播完才念英文）由同一個已解鎖的 `<audio>`／speechSynthesis 接著播。
- 中文說明是預錄 mp3（`audio/zh/`），所以在每台裝置上都是同一個聲音；只有英文單字還用裝置朗讀。
- 遊戲答對後會在稱讚說完（或計時器）之後自動念下一題，這不是在點擊當下。依照上面的解鎖做法，iOS 通常允許；如果實機發現下一題沒有聲音，小朋友可以按右上角黃色喇叭再聽一次，這部分要實機確認。
- 聲音清單是非同步載入的：同時聽 `voiceschanged` 並每 250ms 檢查一次（最多 10 秒）。英文優先選 Samantha／Google US English／Microsoft Aria 等 en-US 聲音；中文不使用 TTS，mp3 播放失敗時顯示可見提示。
- 每次說新的字會先 `cancel()`。英文單字速度 0.85、句子 0.72；中文以預錄的 -8% 語速播放。
- 裝置不支援朗讀時會顯示提示，卡片其他功能照常。

## 怎麼測試

見 README。`tools/selftest.py` 會：

- 用 `python3 -m http.server` 開站，在 iPad 直向 820×1180、橫向 1180×820、iPad Pro 1024×1366、手機 390×844、844×390 實際操作。
- 檢查無 console error／4xx／5xx、每張卡片圖片載入、文字不溢出、按鈕夠大（iPad ≥ 80px，手機 ≥ 56px）。
- 用假的 `speechSynthesis` 記錄每次朗讀：點圖／喇叭會念對的字、lang 是 en-US、速度 0.8–0.9；聲音延遲載入（有、沒有 `voiceschanged` 兩種）也會選到 en-US 聲音。
- 中文：每一句都是播 `audio/zh/*.mp3`，全程沒有任何 zh-TW 的 speechSynthesis 呼叫；中文說明播完才念英文；所有 40 個 mp3 都能在瀏覽器解碼（0.3–15 秒），真的 mp3 在第一次點擊就能播完；故意讓一個 mp3 404 時顯示提示，確認不使用中文 TTS。（遊戲流程裡的 mp3 用 0.15 秒的短音代替，讓測試跑得快。）
- 有 `audio` 的字會播放音檔；音檔壞掉會退回 TTS；完全不支援朗讀時會顯示提示。
- 點卡片圖片會左右搖擺並有音效（計算 Web Audio 振盪器），連點 6 下動作不疊加，0.9 秒內結束；每個字和每種動作都檢查：沒有轉圈、傾斜不超過 15 度；看完整疊有稱讚。
- 進度（`--only progress`）：iPad 三種尺寸＋手機直向，裝置時區設為 Asia/Taipei、時鐘固定在 2026-10-22 19:00：新裝置 0 星、空罐 → 看完動物卡（罐子 +1 顆、1 星）→ 重新整理後進度和罐子都在 → 沒有到期的練習回合（沒碰過的字優先、答錯的字最後再問一次、之後排明天 0:00，主題頁不會馬上又冒出要複習的字）→ 同一天 23:59 仍沒有到期 → 隔天 0:01 全部到期、小圖數量對、沒有文字、星星沒有變少 → 今日複習依序是連連看、翻牌記憶、看卡片、聽音找圖，題目都是複習的字、結算角色是本輪的字 → 快滿的罐子再一輪就裝滿、慶祝、換新罐 → 清除後歸零 → 存檔壞掉時安全重來。
- 小遊戲：每種尺寸把三個遊戲各玩完一輪（先答錯一次，再全部答對），檢查中文玩法說明、答錯的溫和提示並再念一次、答對的稱讚和音效、星星結算、「再玩一次」、主題選擇；連連看包含拖線。

出題引擎另外用 `node --test tools/test_quiz.cjs` 測（不重複、干擾項同主題優先、少量單字、同 seed 結果相同）。

## 已知限制

- 沒有在 iPad／iPhone 實機測過（只有 Chrome 無頭瀏覽器模擬尺寸與觸控）。實際音色、音量、iOS 是否允許排在中文指示後面的錄音檔、遊戲自動念下一題，都要實機確認。照 `docs/IOS_DEVICE_CHECKLIST.md` 測。
- 連連看的「圖片 ↔ 英文字」進階版還沒做。
- 英文 TTS 音色依裝置而定；沒有安裝英文語音的裝置會用系統預設。中文是預錄的，不受影響。
- `tools/gen-voice.py` 需要網路（edge-tts 連微軟的線上語音服務）。
- 直接開 `file://` 讀不到資料（需要 http 伺服器或 GitHub Pages）。
- 離線（service worker）已在階段 5 完成，但還沒在 iPad 實機測過加到主畫面後的離線開啟。見實機清單 E 段。
- 中文台詞集中在 `data/voice-zh.json`，全部以 `audio/zh/` 預錄檔播放。
