package com.dailylingo.app;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import org.json.JSONException;
import org.json.JSONTokener;

import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 主界面：整屏只有一个 WebView，加载线上的 DailyLingo。
 *
 * <p>启动流程与桌面端一致：</p>
 * <pre>
 *   启动页（Lingo 艺术字）
 *     → 探测网络（系统网络状态 + 站点 6 秒 GET）
 *          ├ 离线 → 错误菜单「请连接网络，当前无资源」
 *          └ 在线 → 加载网页（25 秒看门狗）
 *                 ├ 成功 → 显示网页（此前 WebView 一直不可见，所以不会出现白屏）
 *                 └ 超时 / 加载失败 → 错误菜单
 * </pre>
 */
public final class MainActivity extends Activity {

    private static final String TAG = Diagnostics.class.getSimpleName();

    private static final String SITE_URL = NetProbe.SITE_URL;
    private static final String SITE_HOST = "zc110747.github.io";

    /** 导航看门狗：超过这个时间还没加载完就判定为「连接超时」。 */
    private static final long NAVIGATION_TIMEOUT_MILLIS = 25_000L;

    /** 调试开关：{@code adb shell am start ... --ez force_offline true} 可强制走错误菜单。 */
    private static final String EXTRA_FORCE_OFFLINE = "force_offline";

    private FrameLayout mRoot;
    private SplashView mSplash;
    private WebView mWebView;
    private OfflineView mOffline;

    private ProgressStore mStore;
    private ExecutorService mExecutor;
    private final Handler mHandler = new Handler(Looper.getMainLooper());

    private boolean mForceOffline;
    private boolean mNavigating;
    private boolean mPageFailed;
    private boolean mSeedReloaded;
    private int mNavigationAttempt;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mForceOffline = getIntent() != null
                && getIntent().getBooleanExtra(EXTRA_FORCE_OFFLINE, false);

        File storageDirectory = resolveStorageDirectory();
        Diagnostics.attach(storageDirectory);
        Diagnostics.info("启动：versionName=" + versionName() + "，storage=" + storageDirectory);

        mStore = new ProgressStore(storageDirectory);
        mStore.load();
        Diagnostics.info("已载入本机进度：" + mStore.completedCount() + " 篇");

        mExecutor = Executors.newSingleThreadExecutor();

        mRoot = new FrameLayout(this);
        mRoot.setBackgroundColor(color(R.color.page_background));
        setContentView(mRoot);

        // 必须放在 setContentView 之后：getInsetsController() 依赖已经创建好的 DecorView，
        // 提前调用会拿到 null 并抛 NPE（真机上踩过）。
        setUpWindow();

        mWebView = createWebView();
        // 必须是 GONE 而不是 INVISIBLE：INVISIBLE 仍然参与合成，WebView 的渲染表面会盖住
        // 启动页，导致启动时只能看到一片空白（真机上踩过）。
        mWebView.setVisibility(View.GONE);
        mRoot.addView(mWebView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        mOffline = new OfflineView(this);
        mOffline.setVisibility(View.GONE);
        mOffline.bindActions(new OfflineView.Listener() {
            @Override
            public void onRetry() {
                retry();
            }

            @Override
            public void onOpenInBrowser() {
                openExternally(Uri.parse(SITE_URL));
            }
        });
        mRoot.addView(mOffline, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        mSplash = new SplashView(this);
        mRoot.addView(mSplash, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        applyInsets();

        showSplash(getString(R.string.splash_starting));
        retry();
    }

    // ---------------------------------------------------------------- 界面

    private void setUpWindow() {
        Window window = getWindow();
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false);
            WindowInsetsController controller = window.getDecorView().getWindowInsetsController();
            if (controller != null) {
                controller.setSystemBarsAppearance(
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
            }
        } else {
            int flags = View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
            }
            window.getDecorView().setSystemUiVisibility(flags);
        }
    }

    /** Android 15 起强制 edge-to-edge，这里把系统栏区域让出来，网页才不会钻到状态栏底下。 */
    private void applyInsets() {
        mRoot.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override
            public WindowInsets onApplyWindowInsets(View view, WindowInsets insets) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    Insets bars = insets.getInsets(
                            WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                } else {
                    view.setPadding(
                            insets.getSystemWindowInsetLeft(),
                            insets.getSystemWindowInsetTop(),
                            insets.getSystemWindowInsetRight(),
                            insets.getSystemWindowInsetBottom());
                }
                return insets;
            }
        });
        mRoot.requestApplyInsets();
    }

    private void showSplash(String status) {
        mSplash.setStatus(status);
        mSplash.startAnimation();
        mSplash.setVisibility(View.VISIBLE);
        mWebView.setVisibility(View.GONE);
        mOffline.setVisibility(View.GONE);
        setTitle(R.string.app_name);
    }

    private void showWeb() {
        mHandler.removeCallbacksAndMessages(null);
        mNavigationAttempt++;
        mSplash.stopAnimation();
        mSplash.setVisibility(View.GONE);
        mOffline.setVisibility(View.GONE);
        mWebView.setVisibility(View.VISIBLE);
        updateTitle();
    }

    private void showOffline(String headline, String detail) {
        mHandler.removeCallbacksAndMessages(null);
        mNavigationAttempt++;
        mNavigating = false;
        mSplash.stopAnimation();

        String progress = mStore.current() == null
                ? getString(R.string.offline_progress_empty, ProgressStore.FILE_NAME)
                : getString(R.string.offline_progress_saved, mStore.completedCount(), ProgressStore.FILE_NAME);

        mOffline.setContent(headline, detail, progress);
        mSplash.setVisibility(View.GONE);
        mWebView.setVisibility(View.GONE);
        mOffline.setVisibility(View.VISIBLE);
        setTitle(R.string.app_name_offline);
    }

    private void updateTitle() {
        if (mWebView.getVisibility() != View.VISIBLE) {
            return;
        }
        setTitle(mStore.completedCount() > 0
                ? getString(R.string.app_name_done, mStore.completedCount())
                : getString(R.string.app_name));
    }

    // ---------------------------------------------------------------- 启动流程

    /** 探测网络 →（在线）导航 → 看门狗兜住超时。 */
    private void retry() {
        if (mNavigating) {
            return;
        }

        showSplash(getString(R.string.splash_connecting));
        mExecutor.execute(new Runnable() {
            @Override
            public void run() {
                final boolean online = !mForceOffline && NetProbe.isOnline(MainActivity.this);
                Diagnostics.info("网络探测结果：" + (online ? "在线" : "离线")
                        + (mForceOffline ? "（强制离线开关已打开）" : ""));

                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (online) {
                            navigate();
                        } else {
                            showOffline(getString(R.string.offline_headline),
                                    getString(R.string.offline_detail));
                        }
                    }
                });
            }
        });
    }

    private void navigate() {
        showSplash(getString(R.string.splash_opening));
        mNavigating = true;
        mPageFailed = false;

        final int attempt = ++mNavigationAttempt;
        Diagnostics.info("开始加载：" + SITE_URL);
        mWebView.loadUrl(SITE_URL);

        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (attempt != mNavigationAttempt || !mNavigating) {
                    return;
                }

                mNavigating = false;
                mWebView.stopLoading();
                Diagnostics.warn("导航超时（" + (NAVIGATION_TIMEOUT_MILLIS / 1000) + " 秒）");
                showOffline(getString(R.string.offline_headline),
                        getString(R.string.offline_detail_timeout, SITE_URL,
                                NAVIGATION_TIMEOUT_MILLIS / 1000));
            }
        }, NAVIGATION_TIMEOUT_MILLIS);
    }

    // ---------------------------------------------------------------- WebView

    private WebView createWebView() {
        WebView webView = new WebView(this);
        webView.setBackgroundColor(color(R.color.page_background));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        // localStorage 是学习进度的载体，必须开
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        // 只加载线上页面，不需要访问本地文件
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setGeolocationEnabled(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                boolean web = "https".equals(scheme) || "http".equals(scheme);

                // 站内链接留在壳里；站外链接交给系统浏览器，避免在壳里越走越远。
                if (web && SITE_HOST.equals(uri.getHost())) {
                    return false;
                }

                openExternally(uri);
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                Diagnostics.info("页面开始加载：" + url);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                Diagnostics.info("页面加载完成：" + url);

                mNavigating = false;
                if (mPageFailed) {
                    return;
                }

                showWeb();
                installProgressBridge();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request == null || !request.isForMainFrame()) {
                    return;
                }

                mPageFailed = true;
                String reason = NetProbe.describeError(error.getErrorCode());
                Diagnostics.warn("主框架加载失败：" + reason + "（" + request.getUrl() + "）");
                showOffline(getString(R.string.offline_headline),
                        getString(R.string.offline_detail_failed, reason));
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request,
                                            WebResourceResponse response) {
                super.onReceivedHttpError(view, request, response);
                if (request == null || !request.isForMainFrame()) {
                    return;
                }

                mPageFailed = true;
                String reason = "HTTP " + response.getStatusCode();
                Diagnostics.warn("主框架返回错误：" + reason);
                showOffline(getString(R.string.offline_headline),
                        getString(R.string.offline_detail_failed, reason));
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage message) {
                if (message.messageLevel() == ConsoleMessage.MessageLevel.ERROR) {
                    Diagnostics.warn("网页控制台：" + message.message() + "（" + message.sourceId()
                            + ":" + message.lineNumber() + "）");
                }
                return true;
            }
        });

        webView.addJavascriptInterface(new NativeBridge(), "DailyLingoNative");
        return webView;
    }

    /**
     * 往页面里注入进度桥接脚本。
     *
     * <p>Android 没有「文档创建前执行」的等价 API，所以先读一次 localStorage：
     * 只有本机有进度、网页里却是空的（首次安装 / 清过缓存）时，先写种子再重载一次，
     * 让页面的 progress.js 在初始化时就能读到正确数据。其余情况交给注入脚本双向同步。</p>
     */
    private void installProgressBridge() {
        final String seed = mStore.loadSeedText();

        String probe = "(function(){try{return window.localStorage.getItem("
                + jsString(ProgressStore.STORAGE_KEY) + ");}catch(error){return null;}})()";

        mWebView.evaluateJavascript(probe, value -> {
            String current = unwrapJsonString(value);

            if (seed != null && (current == null || current.isEmpty()) && !mSeedReloaded) {
                mSeedReloaded = true;
                Diagnostics.info("网页存储为空，写入本机进度种子后重载一次");
                mWebView.evaluateJavascript(
                        "window.localStorage.setItem(" + jsString(ProgressStore.STORAGE_KEY)
                                + ", " + jsString(seed) + ");",
                        null);
                mWebView.reload();
                return;
            }

            mWebView.evaluateJavascript(ProgressBridge.buildScript(seed), result -> {
                if ("\"seeded\"".equals(result) && !mSeedReloaded) {
                    mSeedReloaded = true;
                    Diagnostics.info("注入脚本已用本机进度覆盖网页旧数据，重载以刷新界面");
                    mWebView.reload();
                }
            });
        });
    }

    /** 网页侧 {@code window.DailyLingoNative.post(raw)} 的落点。 */
    private final class NativeBridge {
        @JavascriptInterface
        public void post(final String raw) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (mStore.applyWebState(raw)) {
                        Diagnostics.info("进度已保存：" + mStore.completedCount()
                                + " 篇 → " + mStore.file());
                        updateTitle();
                    }
                }
            });
        }
    }

    // ---------------------------------------------------------------- 杂项

    @Override
    public void onBackPressed() {
        if (mWebView != null && mWebView.getVisibility() == View.VISIBLE && mWebView.canGoBack()) {
            mWebView.goBack();
            return;
        }

        super.onBackPressed();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (mWebView != null) {
            mWebView.onResume();
        }
    }

    @Override
    protected void onPause() {
        if (mWebView != null) {
            mWebView.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        mHandler.removeCallbacksAndMessages(null);
        if (mWebView != null) {
            mWebView.destroy();
            mWebView = null;
        }
        if (mExecutor != null) {
            mExecutor.shutdownNow();
        }
        super.onDestroy();
    }

    /** 外部存储私有目录：{@code /sdcard/Android/data/<包名>/files}，adb pull 得出来。 */
    private File resolveStorageDirectory() {
        File directory = getExternalFilesDir(null);
        if (directory == null) {
            directory = getFilesDir();
        }
        if (directory != null && !directory.exists() && !directory.mkdirs()) {
            Log.w(TAG, "无法创建存储目录：" + directory);
        }
        return directory;
    }

    private void openExternally(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException | SecurityException exception) {
            Diagnostics.warn("打开外部链接失败：" + exception.getMessage());
        }
    }

    private String versionName() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            return info.versionName == null ? "?" : info.versionName;
        } catch (PackageManager.NameNotFoundException exception) {
            return "?";
        }
    }

    private int color(int id) {
        return getResources().getColor(id, getTheme());
    }

    /** 把 Java 字符串转成可嵌进 JS 源码的字面量。 */
    private static String jsString(String value) {
        return org.json.JSONObject.quote(value);
    }

    /** {@code evaluateJavascript} 的返回值是 JSON：可能为 {@code null} 或带引号的字符串。 */
    private static String unwrapJsonString(String value) {
        if (value == null || "null".equals(value)) {
            return null;
        }

        try {
            Object parsed = new JSONTokener(value).nextValue();
            return parsed instanceof String ? (String) parsed : null;
        } catch (JSONException exception) {
            return null;
        }
    }
}
