# v1.0.3

## 中文

### 本次更新

- **独立缓存页**：设置页只保留「缓存」「关于」入口；缓存管理从设置中拆出，单独成页。
- **缓存页数据源独立切换**：缓存页可在 Wikidot / Fandom 之间切换，分类、统计和批量下载都使用缓存页自己的数据源，不影响主页当前数据源。
- **按主页分类查看已缓存层级**：普通层级按 `0`、`1–100`、`101–200`……分段，另有 C 层级、ZH 层级、隐秘层级、玩笑层级、子层级、其他页面；分组和分段默认折叠，避免一次展开几千条。
- **缓存条目详情**：展开后显示层级标题和页面标识（slug），直接判断实际页面缓存，不依赖单独的下载清单。
- **批量缓存**：缓存页提供「下载全部缓存」「下载指定层级」，显示进度、成功/失败数量和当前层级，可随时取消。
- **加载中切页修复**：桌面版发起新查询/切换页面时旧请求按请求编号丢弃；APK 页面详情改用并发执行器，不再被前一个卡住的请求排队阻塞。
- **缓存永久保留**：不会按 TTL 自动过期或删除，只有手动刷新、清理或系统清除应用数据时才会变化。
- 保留详情页、普通层级分段、Fandom 代理支持、安卓发布签名等既有功能。

### 缓存页说明

- 桌面版：设置 → 缓存；可独立切换 Wikidot / Fandom。
- APK：设置 → 缓存；同样独立切换数据源。
- 「下载全部缓存」首次可能需要 30–60 分钟，按页面逐个请求，支持取消。
- 已有缓存直接读取，不重复下载。
- 缓存页只改变自己的数据源，返回主页后主页数据源保持不变。

### 下载

| 文件 | 平台 | 说明 |
|---|---|---|
| `BackroomsLevelViewer-1.0.3-win64.exe` | Windows 10/11 x64 | 单文件，无需安装 Python |
| `BackroomsLevelViewer-1.0.3.apk` | Android 7.0+ | arm64-v8a / x86_64 |
| `SHA256SUMS.txt` | - | 校验和 |

### 校验和

```text
8834d98eb928d0eeede8516861542b5e1a60e6d6a4faf01b47e084dce2f029b8  BackroomsLevelViewer-1.0.3-win64.exe
72ab1e8b9b0d8a94060e86e541bb28dccff496b5d87a6b65e5257a5bb355afc9  BackroomsLevelViewer-1.0.3.apk
```

### 授权

- 代码：MIT License，见仓库 `LICENSE`。
- 维基文本：版权归后室中文维基 / Fandom 及作者所有，遵循 CC BY-SA 3.0。

---

## English

### What's new

- **Dedicated cache page**: Settings now only contains Cache and About entries; cache management has its own page.
- **Independent cache source switch**: the cache page can switch between Wikidot and Fandom. Grouping, statistics and batch downloads use the cache page's own source and never change the main screen's source.
- **Cached levels grouped like the home screen**: normal levels use `0`, `1–100`, `101–200`, ... ranges, plus C, ZH, hidden, joke, sublevel and other categories. Groups and ranges start collapsed to avoid rendering thousands of rows at once.
- **Cached entry details**: expanding a range shows level titles and page slugs. Detection checks actual page cache files instead of relying on a separate download manifest.
- **Batch caching**: "Download all cache" and "Download selected levels" with progress, success/failure counts, current level and cancellation.
- **Non-blocking page switching**: desktop requests are tagged and stale results are discarded; Android page requests use a concurrent executor instead of queueing behind a stuck request.
- **Permanent cache**: no TTL expiry or automatic deletion; only manual refresh, manual clear, or clearing app data changes it.
- Existing detail page, normal-level ranges, Fandom proxy support and release signing are preserved.

### Cache page notes

- Desktop: Settings → Cache; switch Wikidot / Fandom independently.
- APK: Settings → Cache; same independent source switch.
- The first "Download all cache" may take 30–60 minutes because pages are fetched one by one; it can be cancelled.
- Existing cache is read directly and is not downloaded again.
- Changing the cache page source does not change the main screen source.

### Downloads

| File | Platform | Notes |
|---|---|---|
| `BackroomsLevelViewer-1.0.3-win64.exe` | Windows 10/11 x64 | Single file, no Python required |
| `BackroomsLevelViewer-1.0.3.apk` | Android 7.0+ | arm64-v8a / x86_64 |
| `SHA256SUMS.txt` | - | Checksums |

### Checksums

```text
8834d98eb928d0eeede8516861542b5e1a60e6d6a4faf01b47e084dce2f029b8  BackroomsLevelViewer-1.0.3-win64.exe
72ab1e8b9b0d8a94060e86e541bb28dccff496b5d87a6b65e5257a5bb355afc9  BackroomsLevelViewer-1.0.3.apk
```

### License

- Code: MIT License, see `LICENSE`.
- Wiki text: copyright belongs to the Backrooms CN Wiki / Fandom and its authors, licensed under CC BY-SA 3.0.
