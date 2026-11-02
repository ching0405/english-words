# 上線前檢查清單＋GitHub Pages 設定步驟

**只有任務明確寫「Tim 已同意推送」才可 push、改 GitHub 或部署。** 可以先依本文件建立本機候選分支並驗證；所有遠端操作另等明確授權。

目前線上版：`https://ching0405.github.io/english-words/`，repo `ching0405/english-words`；發布 worktree：`~/repos/english-words-release`。

## Tim 已決定（2026-10-23）

- **repo 名稱：`english-words`** → 網址 `https://<帳號>.github.io/english-words/`。上線後不要改名，改名會換網址，iPad 上的主畫面圖示和進度都要重來。
- **`qa/` 截圖不公開。** 免費帳號的 Pages 必須是公開 repo，而 `qa/` 已經出現在開發分支的**歷史**裡（目前有 19 個 commit 碰過）。光是在最新的 commit 刪掉 `qa/` 不夠，別人還是能從舊 commit 拿到。所以：
  - **開發分支永遠不推**（`local/…`、`claude/…`、`codex/…`）；
  - 另外做一個**沒有歷史的發布分支 `release`**，內容是開發分支的快照、去掉 `qa/` 和 `audio-src/`，只推這個分支當 GitHub 的 `main`（見第 2 段）；
  - 開發分支的 `.gitignore` **不加** `qa/`，驗收截圖照舊 commit 在本機；`release` 分支的 `.gitignore` 才加 `qa/` 和 `audio-src/`。
- **原始音檔不發布（Tim 2026-10-29）。** `audio-src/` 和 `qa/` 一律從發布快照排除，原檔仍保留在開發 repo，供 `gen-voice.py`／`normalize-audio.py` 使用。遊戲只讀 `audio/`，`sw.js` 與 `build-sw.py` 不引用原始音檔。此規則不會移除既有遠端歷史裡已公開的原檔。
- **上線順序**（建議，仍待 Tim 說「推送」）：先推上去當測試網址（不對外公告），用 iPad 照 `docs/IOS_DEVICE_CHECKLIST.md` 測完再正式用。加到主畫面、離線、更新這幾項只有 https 才測得到。

## 1. 推送前（本機）

- [ ] `git status` 乾淨，所有改動都已 commit。
- [ ] `python3 tools/check-all.py` 最後一行是 `ALL … STEPS PASSED`。這會依序跑單元測試、資料驗證、`build-sw --check`、中文音量檢查和完整 selftest，約半小時到一小時。
- [ ] `python3 tools/build-sw.py --check`：`sw.js OK`，離線清單 ≤ 2.5 MB（目前 88 個檔案、1.27 MB）。如果說 out of date，先跑 `python3 tools/build-sw.py` 再 commit。
- [ ] 內建資料沒有被動到：`python3 tools/validate-words.py` 顯示的單字數和 `data/phrases.json` 的句數，跟 Tim 核准的清單一樣（第 8 階段是 13 字、7 句），`grep -c '"my_' data/*.json` 全部是 0（舊版家長自訂資料的 id 不應進 `data/`）。新增內容的流程見 `docs/ADD_CONTENT.md`。
- [ ] 中文沒有用 TTS：selftest 裡「no zh-TW TTS」那幾項都通過（包含在 check-all 裡）。
- [ ] repo 裡沒有私人照片、帳號或密碼：`git ls-files | grep -iv '^qa/' | grep -iE '\.(jpe?g|heic)$'` 應該沒有輸出。

## 2. GitHub Pages 設定（Tim 說「推送」後才做）

`<開發 commit>` 是通過第 1 段的那個 commit。

1. 在 GitHub 建立新 repo `english-words`，Public，**不要**勾「Add a README」。
2. 在另一個資料夾做沒有歷史的發布分支（不動開發用的 worktree）：
   ```bash
   cd ~/repos/english-words
   git worktree add --detach ~/repos/english-words-release <開發 commit>
   cd ~/repos/english-words-release
   git checkout --orphan release            # 新分支，沒有任何舊歷史
   git rm -r -f -q --ignore-unmatch qa audio-src  # 只在發布 worktree 排除
   printf 'qa/\naudio-src/\n' >> .gitignore
   touch .nojekyll                          # GitHub 不用 Jekyll 處理檔案
   python3 tools/build-sw.py --check        # 必須 OK（qa/、audio-src/ 不在離線清單，版本號不變）
   git add -A && git commit -m "Release from <開發 commit>"
   ```
3. 發布前確認，以下結果都要符合：
   ```bash
   git rev-list --count release             # 1（只有一個 commit）
   git ls-files | grep -Ec '^(qa|audio-src)/' # 0（grep 無匹配會回傳 1）
   git ls-files | grep -c '^\.nojekyll$'    # 1
   ```
4. 推上去（**只推 `release`**）：
   ```bash
   git remote add origin https://github.com/<帳號>/english-words.git
   git push -u origin release:main
   ```
5. GitHub repo → **Settings → Pages**：Source 選「Deploy from a branch」，Branch 選 `main`、資料夾 `/ (root)`，按 Save。
6. 到 **Actions** 分頁等「pages build and deployment」變綠色，通常 1–2 分鐘。網址是 `https://<帳號>.github.io/english-words/`。
7. 「Enforce HTTPS」要是勾著的（預設會勾）。service worker 只能在 https 下運作。

## 3. 上線後檢查

- [ ] 電腦的 Chrome 打開網址：首頁正常，能玩一個遊戲、有中文說明聲音。
- [ ] DevTools → Application → Service workers：`sw.js` 是 activated；Cache Storage 裡有 88 個檔案加首頁。
- [ ] DevTools → Network 勾 Offline → 重新整理：還能開、能玩。
- [ ] Lighthouse 對線上網址跑一次（需要網路）：
  ```bash
  python3 tools/lighthouse.py --url https://<帳號>.github.io/english-words/
  ```
  PWA 和無障礙都要 1.00，axe 每個畫面都是 0 violations。上一次本機結果：兩項都 1.00（`qa/phase-5/acceptance-results.txt`、phase 6 報告）。
- [ ] Tim 用 iPad 照 `docs/IOS_DEVICE_CHECKLIST.md` 測。

## 4. 之後更新網站

1. 在開發分支改完、跑 `python3 tools/build-sw.py`（版本號會變）、`python3 tools/check-all.py` 全過，然後 commit。
2. 在發布資料夾換成新的快照，加在 `release` 上面（`release` 只會有發布紀錄，沒有開發歷史，也沒有 `qa/`、`audio-src/`）：
   ```bash
   cd ~/repos/english-words-release
   git rm -r -q . && git checkout <新的開發 commit> -- .
   git rm -r -f -q --ignore-unmatch qa audio-src
   printf 'qa/\naudio-src/\n' >> .gitignore && touch .nojekyll
   python3 tools/build-sw.py --check
   git add -A && git commit -m "Release from <新的開發 commit>"
   git ls-files | grep -Ec '^(qa|audio-src)/' # 0（grep 無匹配會回傳 1）
   git push origin release:main
   ```
3. iPad 下次連網開啟（或從背景切回來）時會在背景下載新版，**等孩子回到首頁才重新整理**，進度不受影響。

本機候選可用 `git checkout --orphan codex/release-<名稱> <開發 commit>`，再依第 2 段排除兩個資料夾、加 `.nojekyll`、驗證並 commit；不要移動 `release` 或遠端分支。開發 repo 先跑 `check-all.py --quick`（含原檔音量比對）；候選因刻意無 `audio-src/`，只跑 Node 測試、兩組資料驗證／錯誤案例、`build-sw.py --check` 與 `selftest.py --only pwa`，並逐一 HTTP 檢查 `audio/` 與 SW FILES。候選不要跑需要原檔的 `normalize-audio.py --check`。

## 5. 出問題要退回上一版

1. 在發布資料夾 `git revert HEAD`（退回上一次發布）。`sw.js` 會跟著退回，版本號會變回上一版的，跟壞掉的版本不同，所以 iPad 會更新。跑 `python3 tools/build-sw.py --check` 確認 OK。
2. `git push origin release:main`。iPad 回到首頁時就會換成退回後的版本。
3. 用 revert，不要 force push，之後才查得到每次發布了什麼。
