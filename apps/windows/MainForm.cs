using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Net.Http;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace DailyLingo.Desktop;

/// <summary>
/// 主窗口。整窗只有一个 WebView2，加载线上的 DailyLingo。
/// <para>启动流程：启动页（Lingo 艺术字）→ 探测网络 → 导航 → 成功则切到网页；
/// 探测失败或导航超时则切到错误菜单，可一键重试。</para>
/// </summary>
internal sealed class MainForm : Form
{
    private const string SiteUrl = "https://zc110747.github.io/DailyLingo/";
    private const string OfflineHeadline = "请连接网络，当前无资源";

    /// <summary>导航看门狗：超过这个时间还没加载完就判定为「连接超时」。</summary>
    private static readonly TimeSpan NavigationTimeout = TimeSpan.FromSeconds(25);

    /// <summary>调试用：设了路径就在首屏渲染完成后把 WebView 画面存成 PNG 并退出。</summary>
    internal static string? CapturePath { get; set; }

    private static readonly Color PageBackground = Color.FromArgb(247, 249, 252);
    private static readonly Color CardBackground = Color.White;
    private static readonly Color CardBorder = Color.FromArgb(226, 232, 240);
    private static readonly Color Accent = Color.FromArgb(0x31, 0x66, 0xA4); // 与站点 theme-color 一致
    private static readonly Color TitleColor = Color.FromArgb(0x1F, 0x29, 0x37);
    private static readonly Color MutedColor = Color.FromArgb(0x5B, 0x66, 0x7A);

    private readonly ProgressStore _store;
    private readonly WebView2 _webView;
    private readonly SplashView _splashView;
    private readonly Panel _offlineView;
    private readonly Label _offlineTitle;
    private readonly Label _offlineDetail;
    private readonly Label _offlineProgress;

    private bool _coreReady;
    private bool _checkingNetwork;
    private bool _navigating;
    private int _navigationAttempt;

    public MainForm()
    {
        _store = ProgressStore.ForApplicationDirectory(message => Debug.WriteLine("[DailyLingo] " + message));

        Text = "DailyLingo";
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(1080, 820);
        MinimumSize = new Size(460, 620);
        BackColor = PageBackground;
        AutoScaleMode = AutoScaleMode.Dpi;

        _webView = new WebView2
        {
            Dock = DockStyle.Fill,
            DefaultBackgroundColor = PageBackground,
            Visible = false,
        };
        Controls.Add(_webView);

        _offlineTitle = CreateLabel(OfflineHeadline, 16F, FontStyle.Bold, TitleColor);
        _offlineTitle.Margin = new Padding(0, 0, 0, 12);

        _offlineDetail = CreateLabel(
            "DailyLingo 的内容托管在 GitHub Pages 上，需要联网才能加载。",
            10F,
            FontStyle.Regular,
            MutedColor);
        _offlineDetail.MaximumSize = new Size(420, 0);
        _offlineDetail.Margin = new Padding(0, 0, 0, 16);

        _offlineProgress = CreateLabel("", 9F, FontStyle.Regular, MutedColor);
        _offlineProgress.MaximumSize = new Size(420, 0);
        _offlineProgress.Margin = new Padding(0, 0, 0, 24);

        _offlineView = BuildOfflineView();
        _offlineView.Visible = false;
        Controls.Add(_offlineView);

        _splashView = new SplashView { Visible = true };
        Controls.Add(_splashView);

        _store.Load();
    }

    protected override async void OnShown(EventArgs e)
    {
        base.OnShown(e);
        await StartAsync();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _splashView.StopAnimation();
        base.OnFormClosing(e);
    }

    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        if (keyData != Keys.F5)
        {
            return base.ProcessCmdKey(ref msg, keyData);
        }

        if (_offlineView.Visible)
        {
            _ = RetryAsync();
        }
        else if (_webView.Visible)
        {
            _webView.CoreWebView2?.Reload();
        }

        return true;
    }

    private static Label CreateLabel(string text, float size, FontStyle style, Color color) => new()
    {
        Text = text,
        AutoSize = true,
        Font = new Font("Microsoft YaHei UI", size, style),
        ForeColor = color,
        BackColor = Color.Transparent,
        Margin = new Padding(0),
    };

    private Panel BuildOfflineView()
    {
        var card = new TableLayoutPanel
        {
            ColumnCount = 1,
            RowCount = 4,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Anchor = AnchorStyles.None,
            BackColor = CardBackground,
            Padding = new Padding(40, 32, 40, 32),
        };
        card.Paint += (_, args) =>
        {
            using var pen = new Pen(CardBorder);
            args.Graphics.DrawRectangle(pen, 0, 0, card.Width - 1, card.Height - 1);
        };

        card.Controls.Add(_offlineTitle, 0, 0);
        card.Controls.Add(_offlineDetail, 0, 1);
        card.Controls.Add(_offlineProgress, 0, 2);

        var buttons = new FlowLayoutPanel
        {
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            Margin = new Padding(0),
        };

        var retry = CreateButton("重新连接（F5）", primary: true);
        retry.Click += async (_, _) => await RetryAsync();
        buttons.Controls.Add(retry);

        var openInBrowser = CreateButton("在浏览器中打开", primary: false);
        openInBrowser.Click += (_, _) => OpenExternally(SiteUrl);
        buttons.Controls.Add(openInBrowser);

        card.Controls.Add(buttons, 0, 3);

        var centering = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 1,
            BackColor = PageBackground,
        };
        centering.Controls.Add(card, 0, 0);

        var panel = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = PageBackground,
            Visible = false,
        };
        panel.Controls.Add(centering);
        return panel;
    }

    private static Button CreateButton(string text, bool primary)
    {
        var button = new Button
        {
            Text = text,
            Size = new Size(primary ? 148 : 132, 40),
            FlatStyle = FlatStyle.Flat,
            Font = new Font("Microsoft YaHei UI", 10F, FontStyle.Regular),
            Cursor = Cursors.Hand,
            BackColor = primary ? Accent : Color.White,
            ForeColor = primary ? Color.White : TitleColor,
            Margin = new Padding(0, 0, 12, 0),
            UseVisualStyleBackColor = false,
        };
        button.FlatAppearance.BorderSize = 1;
        button.FlatAppearance.BorderColor = primary ? Accent : CardBorder;
        return button;
    }

    private async Task StartAsync()
    {
        DiagnosticsLog.Info("界面已显示，开始初始化");
        ShowSplash("正在启动内置浏览器…");
        if (!await EnsureCoreAsync())
        {
            return;
        }

        await RetryAsync();
    }

    /// <summary>创建 CoreWebView2 并注入桥接脚本；失败时切到错误菜单。</summary>
    private async Task<bool> EnsureCoreAsync()
    {
        if (_coreReady)
        {
            return true;
        }

        try
        {
            var environment = await CoreWebView2Environment.CreateAsync(null, ResolveCacheFolder());
            await _webView.EnsureCoreWebView2Async(environment);

            var core = _webView.CoreWebView2;
            core.Settings.IsStatusBarEnabled = false;
            core.Settings.IsSwipeNavigationEnabled = false;
            core.NavigationStarting += OnNavigationStarting;
            core.NavigationCompleted += OnNavigationCompleted;
            core.WebMessageReceived += OnWebMessageReceived;
            core.ProcessFailed += OnProcessFailed;
            core.NewWindowRequested += OnNewWindowRequested;

            // 注入必须早于第一次导航，否则页面的 progress.js 会先跑完。
            await core.AddScriptToExecuteOnDocumentCreatedAsync(
                ProgressBridge.BuildScript(_store.LoadSeedText()));

            _coreReady = true;
            DiagnosticsLog.Info("CoreWebView2 就绪，桥接脚本已注入");
            return true;
        }
        catch (Exception ex)
        {
            DiagnosticsLog.Error("WebView2 初始化失败", ex);
            ShowOffline(
                "无法显示网页",
                "内置浏览器组件启动失败（多半是没有安装 Microsoft Edge WebView2 运行时）。可先「在浏览器中打开」应急。");
            return false;
        }
    }

    /// <summary>探测网络 → 导航 → 交给看门狗兜住超时。</summary>
    private async Task RetryAsync()
    {
        if (_checkingNetwork || _navigating || !_coreReady)
        {
            return;
        }

        _checkingNetwork = true;
        try
        {
            ShowSplash("正在连接 zc110747.github.io …");
            var online = await HasNetworkAsync();
            DiagnosticsLog.Info("网络探测结果：" + (online ? "在线" : "离线"));
            if (!online)
            {
                ShowOffline(
                    OfflineHeadline,
                    "没有检测到可用的网络连接。DailyLingo 的内容托管在 GitHub Pages 上，联网后即可正常阅读。");
                return;
            }

            ShowSplash("正在打开今天的内容…");
            _navigating = true;
            var attempt = ++_navigationAttempt;
            DiagnosticsLog.Info("开始导航：" + SiteUrl);
            _webView.CoreWebView2.Navigate(SiteUrl);
            _ = WatchNavigationAsync(attempt);
        }
        catch (Exception ex) when (ex is COMException or InvalidOperationException or ObjectDisposedException)
        {
            _navigating = false;
            Debug.WriteLine("[DailyLingo] 导航失败：" + ex.Message);
            ShowOffline(OfflineHeadline, "内置浏览器暂时无法打开页面。请按 F5 重试，或「在浏览器中打开」。");
        }
        finally
        {
            _checkingNetwork = false;
        }
    }

    /// <summary>看门狗：导航迟迟不结束就判定为连接超时，切到错误菜单。</summary>
    private async Task WatchNavigationAsync(int attempt)
    {
        await Task.Delay(NavigationTimeout);
        if (attempt != _navigationAttempt || !_navigating)
        {
            return;
        }

        _navigating = false;
        try
        {
            _webView.CoreWebView2?.Stop();
        }
        catch (COMException ex)
        {
            Debug.WriteLine("[DailyLingo] 停止导航失败：" + ex.Message);
        }

        ShowOffline(
            OfflineHeadline,
            $"连接 {SiteUrl} 超时（{NavigationTimeout.TotalSeconds:0} 秒内没有响应）。请检查网络后重试。");
    }

    /// <summary>先看网卡状态，再对站点做一次短超时的探测；两者都过才去导航。</summary>
    private static async Task<bool> HasNetworkAsync()
    {
        // 支持把「断网」演出来：设置这个环境变量后一律按离线处理，便于核对错误菜单。
        if (Environment.GetEnvironmentVariable("DAILYLINGO_DESKTOP_FORCE_OFFLINE") is { Length: > 0 })
        {
            return false;
        }

        try
        {
            if (!NetworkInterface.GetIsNetworkAvailable())
            {
                return false;
            }
        }
        catch (NetworkInformationException)
        {
            // 取不到网卡信息就继续做网络探测
        }

        try
        {
            using var handler = new HttpClientHandler { AllowAutoRedirect = true };
            using var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(6) };
            using var request = new HttpRequestMessage(HttpMethod.Get, SiteUrl);
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
            return (int)response.StatusCode < 500;
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or IOException)
        {
            return false;
        }
    }

    private void OnNavigationStarting(object? sender, CoreWebView2NavigationStartingEventArgs e) => _navigating = true;

    private void OnNavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        _navigating = false;
        DiagnosticsLog.Info($"导航完成：IsSuccess={e.IsSuccess} status={e.WebErrorStatus}");
        if (e.IsSuccess)
        {
            ShowWeb();
            return;
        }

        ShowOffline(OfflineHeadline, $"页面加载失败（{Describe(e.WebErrorStatus)}）。请检查网络后按 F5 重试。");
    }

    private void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        string? json;
        try
        {
            json = e.TryGetWebMessageAsString();
        }
        catch (ArgumentException)
        {
            return;
        }

        var message = ProgressBridge.ParseMessage(json);
        if (message is not { Type: "progress" })
        {
            return;
        }

        if (_store.ApplyWebState(message.Value.Payload))
        {
            UpdateCaption();
            Debug.WriteLine($"[DailyLingo] 进度已保存：{_store.CompletedCount} 篇 → {_store.FilePath}");
        }
    }

    private void OnProcessFailed(object? sender, CoreWebView2ProcessFailedEventArgs e)
    {
        _navigating = false;
        Debug.WriteLine("[DailyLingo] WebView2 进程失败：" + e.ProcessFailedKind);
        ShowOffline("内置浏览器已停止", "网页渲染进程异常退出。按 F5 重试，或「在浏览器中打开」。");
    }

    private void OnNewWindowRequested(object? sender, CoreWebView2NewWindowRequestedEventArgs e)
    {
        // 站内没有新窗口需求；外部链接交给系统默认浏览器，避免在壳里开第二个窗口。
        e.Handled = true;
        OpenExternally(e.Uri);
    }

    private void ShowSplash(string status)
    {
        _splashView.Status = status;
        _splashView.StartAnimation();

        _webView.Visible = false;
        _offlineView.Visible = false;
        _splashView.Visible = true;
        _splashView.BringToFront();
        Text = "DailyLingo";
    }

    private void ShowWeb()
    {
        _navigationAttempt++; // 让看门狗失效
        _splashView.StopAnimation();
        _splashView.Visible = false;
        _offlineView.Visible = false;
        _webView.Visible = true;
        UpdateCaption();

        if (CapturePath is { Length: > 0 })
        {
            _ = CaptureAndExitAsync(CapturePath);
        }
    }

    /// <summary>等页面把字体 / 图片都绘制出来，再抓一张图留证，然后退出。</summary>
    private async Task CaptureAndExitAsync(string path)
    {
        await Task.Delay(3000);
        try
        {
            var directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            await using var stream = File.Create(path);
            await _webView.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, stream);
            DiagnosticsLog.Info("已保存页面截图：" + path);
        }
        catch (Exception ex)
        {
            DiagnosticsLog.Error("页面截图失败", ex);
        }
        finally
        {
            Close();
        }
    }

    private void ShowOffline(string headline, string detail)
    {
        _navigationAttempt++; // 让看门狗失效
        _navigating = false;
        _splashView.StopAnimation();

        _offlineTitle.Text = headline;
        _offlineDetail.Text = detail;
        RefreshOfflineProgress();

        _splashView.Visible = false;
        _webView.Visible = false;
        _offlineView.Visible = true;
        _offlineView.BringToFront();
        Text = "DailyLingo（未连接）";

        if (CapturePath is { Length: > 0 })
        {
            _ = CaptureFormAndExitAsync(CapturePath);
        }
    }

    /// <summary>错误菜单是纯 WinForms 控件，直接 DrawToBitmap 就能留证。</summary>
    private async Task CaptureFormAndExitAsync(string path)
    {
        await Task.Delay(500);
        try
        {
            var directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            using var bitmap = new Bitmap(Math.Max(Width, 1), Math.Max(Height, 1));
            DrawToBitmap(bitmap, new Rectangle(Point.Empty, Size));
            bitmap.Save(path, ImageFormat.Png);
            DiagnosticsLog.Info("已保存界面截图：" + path);
        }
        catch (Exception ex)
        {
            DiagnosticsLog.Error("界面截图失败", ex);
        }
        finally
        {
            Close();
        }
    }

    private void RefreshOfflineProgress()
    {
        _offlineProgress.Text = _store.Current is null
            ? $"本机尚未保存学习进度（联网后自动写入 {ProgressStore.FileName}）。"
            : $"本机已保存学习进度：{_store.CompletedCount} 篇（{ProgressStore.FileName}）。";
    }

    private void UpdateCaption()
    {
        if (!_webView.Visible)
        {
            return;
        }

        Text = _store.CompletedCount > 0 ? $"DailyLingo — 已完成 {_store.CompletedCount} 篇" : "DailyLingo";
    }

    private static void OpenExternally(string url)
    {
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.ComponentModel.Win32Exception or UriFormatException)
        {
            Debug.WriteLine("[DailyLingo] 打开外部链接失败：" + ex.Message);
        }
    }

    /// <summary>WebView2 的缓存目录放在 LocalAppData，避免往仓库 / publisher 目录里写运行时文件。</summary>
    private static string ResolveCacheFolder()
    {
        var folder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "DailyLingo",
            "WebView2");
        Directory.CreateDirectory(folder);
        return folder;
    }

    private static string Describe(CoreWebView2WebErrorStatus status) => status switch
    {
        CoreWebView2WebErrorStatus.CannotConnect => "无法连接服务器",
        CoreWebView2WebErrorStatus.HostNameNotResolved => "域名解析失败",
        CoreWebView2WebErrorStatus.ConnectionAborted => "连接被中断",
        CoreWebView2WebErrorStatus.ConnectionReset => "连接被重置",
        CoreWebView2WebErrorStatus.Timeout => "连接超时",
        CoreWebView2WebErrorStatus.Disconnected => "网络已断开",
        CoreWebView2WebErrorStatus.ServerUnreachable => "无法访问服务器",
        CoreWebView2WebErrorStatus.CertificateIsInvalid => "服务器证书无效",
        _ => status.ToString(),
    };
}
