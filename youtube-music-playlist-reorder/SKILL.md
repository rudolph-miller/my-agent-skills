---
name: youtube-music-playlist-reorder
description: YouTube Musicのプレイリストを指定の曲順に一括並び替えする手順。Chrome DevToolsでログイン済みのプレイリストを開き、曲名とアーティストのリストからAPIで順序を整列したいときに使う。
---

# YouTube Music プレイリスト並び替え

## Overview
YouTube Musicのプレイリストを、指定した順序に一括で並び替えるための手順と一発プロンプトを提供する。
ドラッグ&ドロップでは大変な曲数でも、内部APIを使って確実に順序を揃える。

## 自動並び替えワークフロー
1. Chrome DevToolsでプレイリストURLを開く。ログイン済みで編集可能なプレイリストであることを確認する。
2. 曲一覧が完全に読み込まれていることを確認する。未ロードの可能性がある場合は、下のスクリプト内の自動スクロールを使って全件読み込む。
3. 下の「並び替えスクリプト」を実行する。順序リストは「アーティスト – 曲名」形式で指定する。
4. `missing` または `ambiguous` が出た場合は停止し、該当曲の表記揺れや重複の解消をユーザーに確認する。
5. 200 OKが返ったらページを再読み込みし、指定順になっているかを検証する。

## 並び替えスクリプト
Chrome DevToolsのConsoleまたはDevTools実行用ツールで、そのまま貼り付けて実行する。

```js
(async () => {
  const desiredLines = [
    // 例: "Vaundy – 裸の勇者",
  ];

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
  const splitLine = (line) => {
    const cleaned = line.replace(/^\s*\d+[\.)]\s*/, "").trim();
    const parts = cleaned.split(/\s[-–—]\s/);
    if (parts.length >= 2) {
      return { artist: parts[0].trim(), title: parts.slice(1).join(" - ").trim() };
    }
    return { artist: "", title: cleaned };
  };

  async function loadAll(maxRounds = 40) {
    let last = 0;
    let stable = 0;
    for (let i = 0; i < maxRounds; i++) {
      window.scrollTo(0, document.body.scrollHeight);
      await sleep(800);
      const count = document.querySelectorAll("ytmusic-responsive-list-item-renderer").length;
      if (count === last) {
        stable += 1;
      } else {
        stable = 0;
        last = count;
      }
      if (stable >= 3) break;
    }
    window.scrollTo(0, 0);
    await sleep(400);
  }

  if (typeof ytcfg === "undefined") {
    throw new Error("ytcfgが見つかりません。プレイリスト画面で実行してください。");
  }

  await loadAll();

  const items = [...document.querySelectorAll("ytmusic-responsive-list-item-renderer")]
    .map((el) => {
      const data = el.data || el.__data || {};
      const titleRuns = data?.flexColumns?.[0]?.musicResponsiveListItemFlexColumnRenderer?.text?.runs || [];
      const artistRuns = data?.flexColumns?.[1]?.musicResponsiveListItemFlexColumnRenderer?.text?.runs || [];
      const title = titleRuns.map((r) => r.text).join("") || "";
      const artistRaw = artistRuns.map((r) => r.text).join("") || "";
      const artist = artistRaw.split("•")[0].trim();
      const videoId = data?.playlistItemData?.videoId || data?.navigationEndpoint?.watchEndpoint?.videoId || "";
      const setVideoId = data?.playlistItemData?.setVideoId || "";
      return { title, artist, videoId, setVideoId };
    })
    .filter((it) => it.setVideoId && it.videoId);

  const byFull = new Map();
  const byTitle = new Map();
  for (const it of items) {
    const fullKey = `${norm(it.artist)}||${norm(it.title)}`;
    const titleKey = norm(it.title);
    if (!byFull.has(fullKey)) byFull.set(fullKey, []);
    if (!byTitle.has(titleKey)) byTitle.set(titleKey, []);
    byFull.get(fullKey).push(it);
    byTitle.get(titleKey).push(it);
  }

  const desired = desiredLines.map(splitLine);
  const missing = [];
  const ambiguous = [];
  const desiredItems = [];

  for (const want of desired) {
    const titleKey = norm(want.title);
    const fullKey = `${norm(want.artist)}||${norm(want.title)}`;
    const candidates = want.artist ? (byFull.get(fullKey) || []) : (byTitle.get(titleKey) || []);
    if (candidates.length === 0) {
      missing.push(want);
      continue;
    }
    if (candidates.length > 1) {
      ambiguous.push({ want, candidates: candidates.map((c) => `${c.artist} - ${c.title}`) });
      continue;
    }
    desiredItems.push(candidates[0]);
  }

  if (missing.length || ambiguous.length) {
    console.log("missing", missing);
    console.log("ambiguous", ambiguous);
    throw new Error("未検出または重複があるため停止しました。");
  }

  const playlistId = new URL(location.href).searchParams.get("list");
  if (!playlistId) throw new Error("URLからplaylistIdを取得できませんでした。");

  const origin = "https://music.youtube.com";
  const ts = Math.floor(Date.now() / 1000);
  const getCookie = (name) => (document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`)) || [])[1] || "";
  const sha1 = async (str) => {
    const buf = new TextEncoder().encode(str);
    const digest = await crypto.subtle.digest("SHA-1", buf);
    return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
  };
  const makeAuth = async (cookieName, prefix) => {
    const sapisid = getCookie(cookieName);
    if (!sapisid) return "";
    const hash = await sha1(`${ts} ${sapisid} ${origin}`);
    return `${prefix} ${ts}_${hash}`;
  };

  const authorization =
    (await makeAuth("__Secure-1PAPISID", "SAPISID1PHASH")) ||
    (await makeAuth("__Secure-3PAPISID", "SAPISID3PHASH")) ||
    (await makeAuth("SAPISID", "SAPISIDHASH"));

  if (!authorization) throw new Error("SAPISID系Cookieが見つかりません。");

  const actions = [];
  for (let i = desiredItems.length - 1; i >= 1; i--) {
    const target = desiredItems[i];
    const move = desiredItems[i - 1];
    actions.push({
      action: "ACTION_MOVE_VIDEO_BEFORE",
      setVideoId: target.setVideoId,
      movedSetVideoId: move.setVideoId,
      movedVideoId: move.videoId,
    });
  }

  const key = ytcfg.get("INNERTUBE_API_KEY");
  const context = ytcfg.get("INNERTUBE_CONTEXT");
  const resp = await fetch(`https://music.youtube.com/youtubei/v1/browse/edit_playlist?prettyPrint=false&key=${key}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      "authorization": authorization,
      "x-origin": origin,
      "x-goog-authuser": String(ytcfg.get("SESSION_INDEX") ?? 0),
      "x-goog-visitor-id": ytcfg.get("VISITOR_DATA") || "",
      "x-youtube-client-name": String(ytcfg.get("INNERTUBE_CONTEXT_CLIENT_NAME") || ""),
      "x-youtube-client-version": String(ytcfg.get("INNERTUBE_CONTEXT_CLIENT_VERSION") || ""),
    },
    body: JSON.stringify({ context, playlistId, actions }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`edit_playlist failed: ${resp.status} ${text}`);
  }

  console.log("OK: actions=", actions.length);
})();
```

## 検証
1. ページを再読み込みする。
2. 曲順を上から確認し、指定順と一致するかを確認する。
3. 不一致があれば、曲名表記揺れや重複を確認して再実行する。
