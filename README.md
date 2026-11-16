# 后室层级档案 · Backrooms CN 查询器

版本 **1.0.2**

同时查询 **Wikidot 中文后室** 与 **Fandom 中文后室** 的层级档案。桌面版用 Tkinter 编写，
Android 版用原生界面 + Chaquopy 复用同一套 Python 解析核心。

- 数据源：[backrooms-wiki-cn.wikidot.com](https://backrooms-wiki-cn.wikidot.com/) / [backrooms.fandom.com/zh](https://backrooms.fandom.com/zh)
- 桌面版：Windows 单文件 EXE，无需安装 Python
- Android 版：APK，支持查询、查看生存难度与细则、跳转原文

## 下载

到 [Releases](https://github.com/xiaomu4326/TheBackrooms/releases/latest) 下载：

| 文件 | 平台 |
|---|---|
| `BackroomsLevelViewer-1.0.2-win64.exe` | Windows 10/11（64 位） |
| `BackroomsLevelViewer-1.0.2.apk` | Android 7.0+（arm64-v8a / x86_64） |

## 功能

- 数据源切换：Wikidot / Fandom
- 输入 `0`、`0.1`、`386`、`C-156`、`Level ZH 38`，或直接搜层级名称
- 显示：层级编号、名称、生存难度、三条难度细则、标签、简介、版本与更新时间
- 桌面版侧边栏分组：普通层级 / C层级 / ZH层级 / 隐秘层级 / 玩笑层级 / 其他页面
- 普通层级下再按 0、1–100、101–200……分段，Fandom 与 Wikidot 一致
- 子层级树形嵌套：点 `Level 0` 展开 `Level 0.1`、`0.2`……
- Fandom `displaytitle` 名称直接进入索引；隐秘层级取官方列表，玩笑层级按标签/标题识别
- 本地缓存永久保留，不会自动过期或删除；手动刷新才更新，设置页可查看占用并清理

## 运行源码

需要 Python 3.10+（Windows 官方安装包自带 tkinter）：

```bash
python main.py                 # 图形界面
python main.py 0               # 命令行查询 Level 0
python main.py --source fandom 0
python main.py 0.1 --refresh   # 忽略缓存
```

Windows 也可以双击 `run.bat`。

## Android 版说明

APK 与桌面版共用同一套 `backrooms` 解析核心和分组树：

- 数据源切换：Wikidot / Fandom
- 层级列表：普通 / C / ZH / 隐秘 / 玩笑 / 子层级 / 其他
- 子层级树形嵌套：点上级前的 `▸` 展开 `Level 0.1` 等
- 列表筛选、随机层级、刷新索引、刷新当前页面
- 详情：名称、编号、页面版本、最后编辑时间、生存难度、三条细则、标签、简介、原文链接
- 独立全屏详情页：纸感配色 + 白色圆角卡片，返回后保留列表状态
- 设置页：缓存统计、手动清理缓存、关于（图标、版本、许可证、GitHub 仓库）
- 首次查询优先直连页面；失败再查索引
- 读取 Android 系统代理设置，配合代理可访问 Fandom
- Fandom 在中国大陆常被 DNS 污染或拦截，需要自备网络环境或代理

## 项目结构

```
TheBackrooms/
├─ main.py                  桌面版入口
├─ backrooms/               Python 核心（HTTP、解析、索引、数据源）
│  ├─ config.py             站点、缓存、配色、分类配置
│  ├─ http_client.py        带限速/重试/缓存的下载器
│  ├─ minidom.py            标准库 HTML 解析器
│  ├─ parser.py             Wikidot 页面解析
│  ├─ fandom.py             Fandom MediaWiki API 解析
│  ├─ base.py / service.py  数据源基类、索引与查询编排
│  ├─ groups.py             层级分组与子层级树
│  └─ ui/                   桌面 Tkinter 界面
├─ tests/                   离线测试（模拟 MediaWiki 响应）
├─ android/                 Android 工程（Chaquopy）
│  └─ app/src/main/
│     ├─ java/.../MainActivity.java
│     └─ python/mobile.py   Android ↔ Python 桥接
├─ LICENSE                  MIT（代码）
└─ requirements.txt         运行时无第三方依赖
```

## 构建 EXE

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name BackroomsLevelViewer --collect-submodules backrooms --add-data "backrooms/assets;backrooms/assets" --icon backrooms/assets/icon.ico main.py
```

产物在 `dist/BackroomsLevelViewer.exe`。

## 构建 APK

需要：

- JDK 17 或 21
- Android SDK：`platforms;android-34`、`build-tools;34.0.0`
- Gradle 8.9
- Python 3.12（通过环境变量 `BUILD_PYTHON` 指定）

设置 `BUILD_PYTHON`：

```bash
# Linux / macOS
export BUILD_PYTHON=/path/to/python3.12
```

```powershell
# Windows PowerShell
$env:BUILD_PYTHON = "C:\Path\To\Python312\python.exe"
```

创建 `android/local.properties`：

```properties
sdk.dir=C\:\\Android\\sdk
```

发布签名在 `android/keystore.properties`（不要提交）：

```properties
storeFile=keys/backrooms-release.jks
storePassword=你的密码
keyAlias=backrooms
keyPassword=你的密码
```

构建：

```bash
cd android
gradle :app:assembleRelease
```

产物：`android/app/build/outputs/apk/release/app-release.apk`。
Chaquopy 会在构建时从 `backrooms/` 同步 Python 核心到 APK，无需手工复制。

## 测试

```bash
python -m unittest discover -s tests -v
```

覆盖索引、`displaytitle` 名称、生存难度各种写法、`Class 1d`、wikitext 兜底、
层级分组与子层级、隐秘/玩笑分类、Fandom 非层级页过滤等。

## 数据与授权

- 代码以 **MIT License** 发布，见 [LICENSE](LICENSE)。
- 维基文本内容版权归后室中文维基 / Fandom 及其作者所有，遵循 **CC BY-SA 3.0**。
  本程序只做抓取、展示和跳转，不重新授权这些内容。
- 请控制请求频率，不要给站点造成压力。

## 已知限制

- 站点改版可能导致解析失效，解析规则集中在 `backrooms/parser.py` 与 `backrooms/fandom.py`。
- Android 版为上下分栏（列表 / 详情），桌面版为左右分栏，功能保持一致。
- Fandom 的可达性取决于当地网络环境。
