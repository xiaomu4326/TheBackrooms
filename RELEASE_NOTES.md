# v1.0.0

首个正式版本：Windows 单文件 EXE + Android APK。

## 亮点

- 支持 **Wikidot** 与 **Fandom** 两个中文后室站点的层级查询
- 显示名称、别称、生存难度、三条难度细则、标签、简介、页面版本
- Wikidot 索引分组：普通 / C / ZH / 隐秘 / 玩笑 / 其他；子层级树形挂在上级下面
- **Android 版与桌面端功能对齐**：同一套分组树、子层级展开、筛选、随机、刷新、详情
- Fandom 索引直接读取 `displaytitle` 名称，并过滤「楼层写作指南」等非层级页面
- 兼容 `Class V`、`Class 1d`、`1e - 环境危害`、`»⠀安全` 等写法
- 本地缓存、失败重试、离线熔断，界面不卡顿

## 下载

| 文件 | 平台 | 说明 |
|---|---|---|
| `BackroomsLevelViewer-1.0.0-win64.exe` | Windows 10/11 x64 | 单文件，无需安装 Python |
| `BackroomsLevelViewer-1.0.0.apk` | Android 7.0+ | arm64-v8a / x86_64，查询界面 |
| `SHA256SUMS.txt` | - | 校验和 |

## 使用

- EXE：双击运行
- APK：允许安装未知来源应用后安装；首次查询会加载索引
- 源码：`python main.py`，详见 README

## 说明

- Fandom 在中国大陆可能无法直连，需要可用网络或代理
- APK 使用发布密钥签名；后续升级请使用同一签名的版本
- 维基内容遵循 CC BY-SA 3.0，版权归各站点及作者所有

## English summary

First stable release of the Backrooms CN level viewer: a Windows single-file EXE and an
Android APK, sharing the same Python core for Wikidot and Fandom data sources.
