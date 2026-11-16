# v1.0.2

## 中文

### 本次更新

- **缓存永久保留**：取消 12/24 小时过期逻辑，缓存只会在手动刷新或设置页清理时更新/删除，避免大陆网络慢时反复重新下载。
- **新增设置页（APK / EXE）**：查看缓存文件数量与占用空间，手动清理缓存；「关于」页统一收进设置页。
- **APK 主界面精简**：移除列表下方的内嵌详情区，层级列表占满剩余高度；详情统一打开独立详情页。
- **独立层级详情页**：纸感配色与主页一致，包含名称、别称、编号、页面版本、最后编辑时间、大号生存难度、难度细则、标签、简介和原文链接。
- **普通层级编号分段**：`0`、`1–100`、`101–200`……，Wikidot 与 Fandom 通用，子层级跟随上级分段。
- **Android 功能对齐桌面端**：分组树、子层级展开、筛选、随机、刷新索引/页面、数据源切换。
- **Android 图标与按钮**：使用与 CharactersBirthday 相同的角色图；按钮为 44dp 圆角样式，查询区为整行输入 + 等宽按钮。
- 修复父层级误跳转、键盘遮挡、空索引无提示等问题。

### 缓存说明

- 桌面版缓存目录：`cache/`
- Android 缓存目录：应用私有 `getFilesDir()/backrooms-cache`，不使用系统 `cacheDir`
- 不会因 TTL 过期自动删除；卸载应用或系统清除应用数据时才会丢失
- 「刷新列表」「刷新」等按钮仍会强制更新；设置页可随时手动清理

### 下载

| 文件 | 平台 | 说明 |
|---|---|---|
| `BackroomsLevelViewer-1.0.2-win64.exe` | Windows 10/11 x64 | 单文件，无需安装 Python |
| `BackroomsLevelViewer-1.0.2.apk` | Android 7.0+ | arm64-v8a / x86_64，完整查询界面 |
| `SHA256SUMS.txt` | - | 校验和 |

### 使用说明

- EXE：双击运行；右上角「设置」或 `F1` 打开设置页。
- APK：允许安装未知来源应用后安装；主页「设置」进入缓存管理与关于页。
- Fandom 在中国大陆可能无法直连，需要可用网络或代理。
- APK 使用发布密钥签名，后续升级请继续使用同一签名的版本。

### 校验和

```text
05cfe6dce1fe1181354da0b13b7aa4102c55d9e710e039614e072f8f0d88a9bb  BackroomsLevelViewer-1.0.2-win64.exe
dc34424be91d073dac284d5d57ade30d6737abe6bc72a3f52b3a6a3d7ef22410  BackroomsLevelViewer-1.0.2.apk
```

### 授权

- 代码：MIT License，见仓库 `LICENSE`。
- 维基文本：版权归后室中文维基 / Fandom 及作者所有，遵循 CC BY-SA 3.0。

---

## English

### What's new

- **Permanent cache**: the 12h/24h expiry logic has been removed. Cache is only updated or deleted by manual refresh or the Settings page, avoiding repeated downloads on slow networks.
- **New Settings page (APK / EXE)**: view cache file count and size, clear the cache manually, and open About from Settings.
- **Simplified APK main screen**: the inline detail panel under the level list has been removed, so the list fills the available height; details open in a dedicated page.
- **Dedicated level detail page**: paper-and-gold theme matching the home screen, with name, alias, code, page revision, last edit time, large survival-class badge, class details, tags, summary and source link.
- **Normal-level ranges**: `0`, `1–100`, `101–200`, ... on both Wikidot and Fandom, with sublevels following their parent range.
- **Android feature parity with desktop**: grouped tree, sublevel expansion, filtering, random level, index/page refresh, and source switching.
- **Android icon and buttons**: same character artwork as CharactersBirthday; 44dp rounded buttons and a full-width query input with equal-width action buttons.
- Fixed parent-level mis-navigation, keyboard overlap, and missing empty-index hints.

### Cache notes

- Desktop cache directory: `cache/`
- Android cache directory: app-private `getFilesDir()/backrooms-cache`, not the system `cacheDir`
- Cache does not expire automatically; it is only lost when the app is uninstalled or app data is cleared by the system/user
- "Refresh list" and "Refresh" still force updates; Settings provides manual cache clearing

### Downloads

| File | Platform | Notes |
|---|---|---|
| `BackroomsLevelViewer-1.0.2-win64.exe` | Windows 10/11 x64 | Single file, no Python required |
| `BackroomsLevelViewer-1.0.2.apk` | Android 7.0+ | arm64-v8a / x86_64, full query UI |
| `SHA256SUMS.txt` | - | Checksums |

### Notes

- EXE: double-click to run; open Settings from the top-right link or press `F1`.
- APK: allow installation from unknown sources; open Settings from the main screen for cache management and About.
- Fandom may be unreachable in mainland China; a working network or proxy is required.
- The APK is signed with a release key; future updates must use the same signing key.

### Checksums

```text
05cfe6dce1fe1181354da0b13b7aa4102c55d9e710e039614e072f8f0d88a9bb  BackroomsLevelViewer-1.0.2-win64.exe
dc34424be91d073dac284d5d57ade30d6737abe6bc72a3f52b3a6a3d7ef22410  BackroomsLevelViewer-1.0.2.apk
```

### License

- Code: MIT License, see `LICENSE`.
- Wiki text: copyright belongs to the Backrooms CN Wiki / Fandom and its authors, licensed under CC BY-SA 3.0.
