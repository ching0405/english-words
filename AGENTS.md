# 給接手的程式代理（Codex / Claude）——每次開工先讀

本專案 2026-10-22 起由 Codex 接手（階段 1–3 由 Claude Code 完成）。先讀本檔，再讀 `HANDOFF.md`、`STYLE_GUIDE.md`、`docs/ADD_CONTENT.md`（新增單字／句子的唯一流程）、`docs/PLAN.md`（完整分階段計畫與共同規則）。

## 家長（Tim）的固定規則
1. **只在本機 commit。** 不得 git push、不得建立 GitHub repo、不得開／改 PR、不得 gh 寫入、不得部署。Tim 說「推送」才由助理處理。
2. **玩家是還不識字的幼兒（最高優先）。** 所有操作只靠圖片、大圖示和語音完成：中文語音說明怎麼玩，英文念單字／句子。英文字只當輔助顯示（跟著 Aa／中 開關）。任何玩法都不能要求讀懂文字才答得對。
3. **中文語音一律預錄。** 新中文台詞加進 `data/voice-zh.json`，用 `tools/gen-voice.py` 錄成 mp3（edge-tts `zh-TW-HsiaoChenNeural`，rate -8%，`~/.local/bin/edge-tts`）。不可有中文走瀏覽器 TTS。英文單字發音維持現狀。
4. **單字維持 14 個**（動物：goat, cow, koala, lion, zebra, wolf, rabbit, turtle, monkey（Tim 2026-10-23 加）；萬聖節：vampire, zombie, witch, pumpkin, monster）。不可自行新增或刪除單字／句子，新內容只照 Tim 在聊天給的清單。新增內容照 `docs/ADD_CONTENT.md`。家長專區（裝置上自訂內容）已在第 8 階段移除，不要加回。
5. **點卡片只左右搖擺，不可整圈旋轉。**
6. **「玩遊戲」只有三種：** 聽音找圖、連連看、翻牌記憶（泡泡遊戲已刪除，不要加回）。
7. **不移動 Aa／中 開關的位置**（單字卡、句子卡上方）。
8. **主要裝置是 iPad：** 以 820×1180、1180×820、1024×1366 驗收；手機 390×844 只需不破版。觸控目標要大。
9. 不修改、不參考 `~/repos/dressup`。
10. 每完成主要項目就 commit；完成該階段驗收、寫完報告就停，不自行開始下一階段。

## 測試（每次交付前全跑）
一鍵：`python3 tools/check-all.py`（依序跑下面全部，最後印總表；`--quick` 不開瀏覽器、`--twice` selftest 連跑兩次、`--qa` 截圖進 `qa/`）。`build-sw.py --check` 另外限制離線清單總量 ≤ 2.5 MB、單檔 ≤ 300 KB。
- `node --test tools/test_*.cjs`（全部單元測試）
- `python3 tools/validate-words.py`、`python3 tools/test_validate_words.py`
- `python3 tools/selftest.py`（Playwright＋`/usr/bin/google-chrome`，5 種尺寸；平常截圖寫到 `/tmp/ew-selftest-qa/`，只有正式驗收加 `--qa` 才寫進 `qa/phase-N/`）——0 失敗、不能有偶發失敗。依 Tim 2026-10-23 的決定只跑一輪，有失敗或偶發才跑第二輪查原因。
- 截圖自己打開看過；同時從幼兒角度評估好玩度（看得懂嗎、難度、節奏、動機）。
