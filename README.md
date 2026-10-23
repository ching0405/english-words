# english-words｜看圖學英文 Picture Words

給學英文的幼兒玩的看圖單字與生活句子網站。首頁有「單字」和「生活句子」兩個入口，兩區的排法一樣：上面是「玩遊戲」，下面是「今日複習」和瀏覽用的卡片。單字區的遊戲是聽音找圖、連連看、翻牌記憶；句子區的遊戲是聽句子選圖、圖形字卡排句子，完成一輪都會把星星放進同一個星星罐。主要在 iPad 上玩，手機也能用。純靜態網站（HTML＋CSS＋JS），沒有後端、沒有建置步驟，可以直接放 GitHub Pages 的子路徑（例如 `/english-words/`）。

孩子還不識字也能玩：每一步都有語音（中文說玩法、英文念單字／句子），按鈕用大圖示，英文字和中文字只是給家長的輔助，可以關掉。有很小聲的背景音樂（瀏覽器即時產生，不用下載音檔），念語音時自動變小，首頁左下角的音符可以關掉。

句子僅含 Tim 指定的七句；14 個單字（2026-10-23 依 Tim 加 monkey）。中文全部使用預錄 mp3，播放失敗顯示提示，不使用中文 TTS。只在本機 commit，未經 Tim 授權不推送或部署。

## 本機執行

資料用 `fetch` 讀 JSON，直接雙擊 `index.html`（`file://`）會讀不到，要用本機伺服器：

```bash
cd ~/repos/english-words
python3 -m http.server 8000
# 瀏覽器開 http://localhost:8000/
```

同一個 Wi-Fi 的 iPad 可以開 `http://<電腦的 IP>:8000/` 試玩。

## 測試

```bash
python3 tools/check-all.py             # 一鍵全跑（下面每一項＋selftest，約半小時到一小時），最後印總表
python3 tools/check-all.py --quick     # 不開瀏覽器：單元測試、資料驗證、build-sw（約一分鐘）
python3 tools/validate-words.py        # 檢查單字資料和圖片
python3 tools/test_validate_words.py   # 證明驗證器會擋下錯誤資料
python3 tools/validate-phrases.py      # 檢查句子資料與圖片
python3 tools/test_validate_phrases.py # 句子錯誤資料案例
node --test tools/test_*.cjs
python3 tools/selftest.py              # 無頭瀏覽器自測，截圖寫到 /tmp/ew-selftest-qa/（不動 qa/）
python3 tools/selftest.py --qa         # 驗收用：截圖寫進 qa/phase-N/
python3 tools/selftest.py --only games # 只測小遊戲（也可 --only cards、progress、phrases、pwa、look、a11y、music）
python3 tools/normalize-audio.py --check  # 中文音檔都是 −16 LUFS、由 audio-src/zh/ 原檔做出
python3 tools/render-bgm.py out.mp3    # 背景音樂試聽檔（--measure 量遊戲裡的響度）
```

自測需要 Python Playwright 和 `/usr/bin/google-chrome`（可用 `--chrome` 指定）。

## 文件

- [docs/ADD_CONTENT.md](docs/ADD_CONTENT.md)：新增單字、主題、句子的步驟（資料格式、圖片、預錄中文、驗證、發布）
- [STYLE_GUIDE.md](STYLE_GUIDE.md)：插圖和介面的風格規格
- [HANDOFF.md](HANDOFF.md)：程式結構、資料格式、已知限制
