# v1.0.1

## 中文

### 本次更新

- **普通层级按编号分段**：`0`、`1–100`、`101–200`……，Wikidot 与 Fandom 都生效；子层级跟随上级归入对应分段。
- **Android 功能与桌面端对齐**：层级分组树、子层级展开、筛选、随机、刷新索引、刷新页面、数据源切换。
- **APK 新增独立全屏详情页**：纸感配色与主页一致，包含名称、别称、编号、页面版本、最后编辑时间、大号生存难度、难度细则、标签、简介和原文链接。
- **APK / EXE 新增「关于」页**：应用图标、简介、版本、许可证、数据源、GitHub 仓库链接和返回按钮。
- **Android 启动图标**改用与 CharactersBirthday 相同的角色图；EXE 也换用同款图标。
- **Android 按钮重做**：44dp 圆角按钮，查询区改为整行输入框 + 等宽操作按钮。
- **交互修正**：带子层级的上级点击只展开/收起，长按打开该上级详情；索引为空时显示重试提示；打开详情自动隐藏键盘。
- Fandom 索引继续过滤「楼层写作指南」等非层级页面。

### 下载

| 文件 | 平台 | 说明 |
|---|---|---|
| `BackroomsLevelViewer-1.0.1-win64.exe` | Windows 10/11 x64 | 单文件，无需安装 Python |
| `BackroomsLevelViewer-1.0.1.apk` | Android 7.0+ | arm64-v8a / x86_64，完整查询界面 |
| `SHA256SUMS.txt` | - | 校验和 |

### 使用说明

- EXE：双击运行；右上角「关于」或 `F1` 打开关于页。
- APK：允许安装未知来源应用后安装；点「关于」查看版本与许可信息。
- Fandom 在中国大陆可能无法直连，需要可用网络或代理。
- APK 使用发布密钥签名，后续升级请继续使用同一签名的版本。

### 校验和

```text
9fc343e13ce5515f276cbc5f279423559c2294c82cb0329aeee50c40a075cf87  BackroomsLevelViewer-1.0.1-win64.exe
1f73694d2a33c48b9459dbe8733ba24e7476273cd308e689e609add29f3a1e10  BackroomsLevelViewer-1.0.1.apk
```

### 授权

- 代码：MIT License，见仓库 `LICENSE`。
- 维基文本：版权归后室中文维基 / Fandom 及作者所有，遵循 CC BY-SA 3.0。

---

## English

### What's new

- **Normal levels are grouped by number ranges**: `0`, `1–100`, `101–200`, ... on both Wikidot and Fandom. Sublevels stay with their parent level's range.
- **Android now matches the desktop feature set**: grouped level tree, sublevel expansion, filtering, random level, index/page refresh, and source switching.
- **New full-screen level detail page on Android**: paper-and-gold theme matching the home screen, with name, alias, code, page revision, last edit time, large survival-class badge, class details, tags, summary and source link.
- **New About page on both APK and EXE**: app icon, description, version, license, data sources, GitHub repository link and a back button.
- **Android launcher icon** now uses the same character artwork as CharactersBirthday; the EXE uses the same icon.
- **Android buttons redesigned**: 44dp rounded buttons, with the query area changed to a full-width input and equal-width action buttons.
- **Interaction fixes**: tapping a parent level only expands/collapses its sublevels, long-press opens the parent detail; empty-index retry hint; the keyboard is hidden when opening details.
- Fandom index still filters out non-level pages such as "楼层写作指南".

### Downloads

| File | Platform | Notes |
|---|---|---|
| `BackroomsLevelViewer-1.0.1-win64.exe` | Windows 10/11 x64 | Single file, no Python required |
| `BackroomsLevelViewer-1.0.1.apk` | Android 7.0+ | arm64-v8a / x86_64, full query UI |
| `SHA256SUMS.txt` | - | Checksums |

### Notes

- EXE: double-click to run; open About from the top-right link or `F1`.
- APK: allow installation from unknown sources; open About for version and license information.
- Fandom may be unreachable in mainland China; a working network or proxy is required.
- The APK is signed with a release key; future updates must use the same signing key.

### Checksums

```text
9fc343e13ce5515f276cbc5f279423559c2294c82cb0329aeee50c40a075cf87  BackroomsLevelViewer-1.0.1-win64.exe
1f73694d2a33c48b9459dbe8733ba24e7476273cd308e689e609add29f3a1e10  BackroomsLevelViewer-1.0.1.apk
```

### License

- Code: MIT License, see `LICENSE`.
- Wiki text: copyright belongs to the Backrooms CN Wiki / Fandom and its authors, licensed under CC BY-SA 3.0.
