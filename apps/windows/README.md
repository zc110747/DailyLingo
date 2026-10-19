# DailyLingo 桌面端（Windows）

用 WinForms + WebView2 做的桌面外壳：**不复制站点内容**，直接打开线上
`https://zc110747.github.io/DailyLingo/` 并整窗显示；同时把网页里的学习进度
镜像成本机同目录的一份 JSON 文件。

- 目标框架：`net8.0-windows`（WinForms）
- 界面组件：Microsoft Edge WebView2（`Microsoft.Web.WebView2` 1.0.4258.31）
- 发布产物：`apps/windows/publisher/`

---

## 1. 启动流程

```text
启动
 ├─ 启动页：渐变艺术字 Lingo + 跳动音量条 + 状态文字（避免一片空白）
 ├─ 初始化 WebView2 → 注入进度桥接脚本
 ├─ 探测网络（网卡状态 + 对站点 6 秒超时的 HEAD/GET）
 │    ├─ 离线 ─────────────────────────→ 错误菜单「请连接网络，当前无资源」
 │    └─ 在线 → 导航，25 秒看门狗
 │         ├─ 成功 → 主界面（网站主页）
 │         └─ 超时 / 加载失败 ─────────→ 错误菜单（含失败原因）
 └─ 错误菜单：重新连接（F5） / 在浏览器中打开
```

只有导航**成功**才切到网页，所以不会再出现「先白屏、再出页面」的观感。
导航中网页控件是隐藏的，成功后才显示；看门狗到点会 `Stop()` 掉仍在进行的加载。

## 2. 运行要求

| 依赖 | 说明 |
|---|---|
| Windows 10 1809+ / Windows 11 | WebView2 的系统要求 |
| .NET 8 桌面运行时 | 发布是**框架依赖**模式（体积小）。装 SDK 的机器可直接 `dotnet` 运行 |
| Microsoft Edge WebView2 运行时 | Windows 11 与新版 Windows 10 通常自带；缺失时程序显示「无法显示网页」 |

直接双击 `publisher\DailyLingo.Desktop.exe` 即可。

## 3. 学习进度文件

**位置**：与 exe 同目录的 `dailylingo-progress.json`（用 `AppContext.BaseDirectory`，
所以复制整个 `publisher` 目录到别处也照样生效）。

**格式**：与网页端「导出进度」生成的文件**逐字同构**（同为 2 空格缩进、键顺序一致、结尾换行）：

```json
{
  "schemaVersion": 1,
  "completedArticles": [
    "0001",
    "0002"
  ],
  "updatedAt": "2026-10-19T01:42:10.526Z",
  "exportedAt": "2026-10-19T01:42:10.528Z"
}
```

因此三件事都是成立的：

1. 程序写的文件可以直接喂给网页端的「导入进度」；
2. 网页端导出的文件改名成 `dailylingo-progress.json` 放进程序目录，启动后即被读入；
3. 反过来也可以把这份文件当本机备份。

**同步机制**：

- 启动时以**文件为准**：把文件内容写进网页的 `localStorage["dailylingo_learning_progress_v1"]`，
  这一步在页面脚本执行**之前**完成（`AddScriptToExecuteOnDocumentCreatedAsync`）。
- 运行期网页每次写这个键，都会被 `Storage.prototype.setItem` 钩子捕获并 `postMessage` 给宿主，
  宿主校验后落盘（内容没变不写盘，避免每 2 秒轮询都写磁盘）。
- 写入是「先写 `.tmp` 再替换」，不会留下半截文件；解析失败的文件会备份成
  `dailylingo-progress.corrupt-<时间戳>.json` 后被忽略。

进度文件里只有文章编号与时间，不包含正文、音频或任何隐私信息。

## 4. 构建、发布、自检

```bash
cd apps/windows

# 构建（Release，零警告）
dotnet build -c Release

# 发布到 publisher/（框架依赖，需目标机装 .NET 8 桌面运行时）
dotnet publish -c Release -r win-x64 --self-contained false -o publisher

# 进度契约自检：29 项断言，退出码 0 表示全过
./publisher/DailyLingo.Desktop.exe --self-test
```

`.NET 8 桌面运行时` 是唯一需要额外安装的东西；想要「双击即用、不装运行时」，
把发布命令换成 `--self-contained true`（产物约 150 MB，仓库里不存这种体积）。

## 5. 调试开关

| 开关 | 作用 |
|---|---|
| `--self-test` | 不建窗口，校验 ID 规整 / 解析 / 序列化 / 落盘 / 损坏备份，输出 `PASS n / FAIL n` |
| `--render-preview <目录>` | 不建窗口，把启动页按 1080×820 与 460×620 渲染成 PNG |
| `--capture <文件>` | 正常启动，首屏就绪后把 WebView 画面存成 PNG 再退出（核对线上渲染） |
| `DAILYLINGO_DESKTOP_FORCE_OFFLINE=1` | 强制按离线处理，用来核对错误菜单 |

日志写在 `%TEMP%\dailylingo-desktop.log`（启动阶段、网络探测结果、导航结果、未处理异常），
程序没有控制台，排查问题先看这份日志。

## 6. 文件说明

| 文件 | 职责 |
|---|---|
| `Program.cs` | 入口：STAThread、DPI、未处理异常兜底、命令行开关 |
| `MainForm.cs` | 主窗口：三种界面状态（启动页 / 网页 / 错误菜单）与导航、超时看门狗 |
| `SplashView.cs` | 启动页：渐变艺术字 + 音量条动画 + 状态文字（自绘，可离屏渲染） |
| `ProgressStore.cs` | 进度文件读写：与网页端同构的序列化 / 解析 / 原子落盘 / 损坏备份 |
| `ProgressBridge.cs` | 注入网页的桥接脚本（种子写入 + setItem 钩子 + 2 秒轮询兜底） |
| `PreviewRenderer.cs` | `--render-preview` 的实现 |
| `SelfTest.cs` | `--self-test` 的实现 |
| `DiagnosticsLog.cs` | `%TEMP%` 下的轻量日志 |
| `app.ico` | 由 `assets/images/favicon-180.png` 光栅化成 7 种尺寸 |

## 7. 已知边界

- 只做「外壳 + 进度留档」：不做离线缓存，断网时按设计只显示错误菜单。
- 站内链接如要求新窗口，一律交给系统默认浏览器（壳里不叠加第二个窗口）。
- 网页自身的 10 分钟强缓存策略照旧，改样式后可能需要稍等或多刷新一次。
