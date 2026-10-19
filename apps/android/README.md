# DailyLingo Android 端

用系统 WebView 做的 Android 外壳：**不复制站点内容**，直接打开线上
`https://zc110747.github.io/DailyLingo/`；同时把网页里的学习进度镜像成
应用私有目录里的一份 JSON 文件，格式与网页「导出进度」一致。

- 包名：`com.dailylingo.app`
- `minSdk 24` / `targetSdk 36`（真机实测：vivo V2241A，Android 16 / API 36）
- 发布产物：`apps/android/publisher/DailyLingo.apk`
- 依赖：**只有 Android 系统 API**，没有 AndroidX、没有 Material、没有 Gradle

---

## 1. 启动流程

```text
启动
 ├─ 启动页：渐变艺术字 Lingo + 跳动音量条 + 状态文字（避免一片空白）
 ├─ 探测网络（系统网络能力 + 对站点 6 秒超时的 GET）
 │    ├─ 离线 ─────────────────────────→ 错误菜单「请连接网络，当前无资源」
 │    └─ 在线 → 加载网页，25 秒看门狗
 │         ├─ 成功 → 网页（此前 WebView 是 GONE，不会出现白屏）
 │         └─ 超时 / 主框架加载失败 ────→ 错误菜单（含失败原因）
 └─ 错误菜单：重新连接 / 在浏览器中打开
```

两个真机坑（已在代码里注明）：

1. **`WindowInsetsController` 必须在 `setContentView` 之后取**，否则 DecorView 还是
   null，`getInsetsController()` 直接 NPE。
2. **隐藏 WebView 要用 `GONE` 而不是 `INVISIBLE`**。`INVISIBLE` 仍参与合成，
   WebView 的渲染表面会盖住启动页，看起来就是「启动时一片空白」。
   现在启动页与网页是互斥显示，`onDraw` 首帧尺寸会写进日志（`启动页首帧：1080x2286`）。

## 2. 构建

本机没有 Gradle，也不值得为一个 WebView 外壳去下载几百 MB 依赖，所以构建脚本
直接调用 SDK 自带的命令行工具，完整的链路是：

```text
aapt2 compile → aapt2 link → javac → d8 → 打包 classes.dex → zipalign → apksigner
```

```bash
cd apps/android
python tools/build_apk.py            # 输出 publisher/DailyLingo.apk
python tools/build_apk.py --clean    # 先清空 build/
```

工具链定位（脚本会自动找，找不到会明确报错）：

| 组件 | 顺序 |
|---|---|
| Android SDK | `--sdk` → `ANDROID_SDK_ROOT` → `ANDROID_HOME` → 本机常见安装位置 |
| JDK | `--jdk` → `JAVA_HOME` → Android Studio 自带的 `jbr` → PATH 里的 `javac` |

脚本只用 Python 标准库。图标是从站点 favicon 生成的静态资源，只有换图标时才需要
重跑 `python tools/make_icons.py`（那一步需要 Pillow）。

**图标为什么不用 adaptive icon**：源图本身是「蓝色圆角方块 + 白色书本」一整张图。
自适应图标要求把前景/背景拆开，拆开后要么图案变小、要么边缘露出背景色，桌面上就会
出现一圈白边（踩过一次）。现在直接把整张图按各密度输出，交给启动器套遮罩。

## 3. 安装与运行

**手机上直接装**：打开站点的设置面板（首页左上角齿轮）→「手机应用」→ 点「下载 Android 安装包」，
APK 会存到手机的下载目录，点开安装包即可安装（首次需允许「安装未知应用」）。
这个入口指向仓库里的 `apps/android/publisher/DailyLingo.apk`，重新打包后链接带的内容指纹会自动变。

用 adb 装 / 起：

```bash
adb install -r publisher/DailyLingo.apk
adb shell am start -n com.dailylingo.app/.MainActivity
```

> 首次安装时手机可能弹出确认框；如果 `adb install` 报
> `INSTALL_FAILED_ABORTED: User rejected permissions`，在手机上点「继续安装」后重试一次即可。

签名用 `keystore/dailylingo-debug.keystore`（口令是 Android 调试签名的惯例值
`android` / 别名 `dailylingo`，不含任何真实凭据）。keystore 固定后，
`adb install -r` 才能覆盖升级而不会报签名不一致。

## 4. 学习进度

| 项 | 值 |
|---|---|
| 文件 | `/sdcard/Android/data/com.dailylingo.app/files/dailylingo-progress.json` |
| 写入时机 | 网页每次改 `localStorage` 后 1.5 秒内（钩 `setItem` + 轮询兜底） |
| 格式 | 与网页「导出进度」逐字同构：2 空格缩进、键序 `schemaVersion / completedArticles / updatedAt / exportedAt`、**LF**、结尾换行 |
| 损坏处理 | 备份成 `dailylingo-progress.corrupt-<时间戳>.json` 后重建 |

取出来看：

```bash
adb shell cat /sdcard/Android/data/com.dailylingo.app/files/dailylingo-progress.json
adb pull /sdcard/Android/data/com.dailylingo.app/files/dailylingo-progress.json
```

同步是双向的：

- 网页改了进度 → 钩子把 `localStorage` 原文推给原生层 → 原子写文件（`.tmp` → rename）。
- 本机有进度、网页却是空的（首次安装 / 清过缓存）→ 先写种子再重载一次页面，
  保证 `progress.js` 初始化时读到的是本机数据。文件是权威副本。

> 注意：Windows 端由 .NET 9 的序列化器写成 CRLF，Android 端是 LF（与网页一致）。
> 两者 JSON 语义完全相同，互相导入没有差别。

## 5. 调试开关

| 目的 | 做法 |
|---|---|
| 强制走错误菜单 | `adb shell am start -n com.dailylingo.app/.MainActivity --ez force_offline true` |
| 看启动全流程 | `adb logcat -s DailyLingo` 或 `adb shell cat .../files/dailylingo.log` |
| 验证包是否装好 | `adb shell dumpsys package com.dailylingo.app \| grep versionName` |
| 卸载 | `adb uninstall com.dailylingo.app` |

日志同时写 logcat（tag `DailyLingo`）和文件 `.../files/dailylingo.log`（超过 256 KB 自动滚存
为 `.log.1`）。手机上看不到控制台，这个文件是最省事的取证入口。

## 6. 已知边界

- **没有 Gradle 工程**：目录里没有 `build.gradle` / wrapper，Android Studio 打不开成
  Gradle 项目。要改需求时直接改 `src/main/java` 与 `res/`，重新跑构建脚本即可。
- 进度文件在 `Android/data/<包名>/` 下，Android 11+ 的文件管理器看不到，需要用
  `adb`，或从系统的「分享」入口导出（本应用暂未提供分享按钮）。
- 只加载固定站点，站内链接留在壳里，站外链接交给系统浏览器。
- 网页的「导出 / 导入进度」仍走浏览器下载与文件选择，应用没有拦截。
- 真机验证过的路径：联网加载、离线错误菜单、点击勾选后 JSON 落盘、取消勾选后清空。
  未覆盖：系统深色模式、横屏、多窗口。
