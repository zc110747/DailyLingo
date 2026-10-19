package com.dailylingo.app;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkInfo;
import android.os.Build;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * 联网探测：先看系统有没有可用网络，再对站点做一次 6 秒超时的 GET。
 * 两道都过才去加载网页，避免 WebView 自己在那里转圈。
 *
 * <p>所有方法都会做网络访问，必须在后台线程调用。</p>
 */
final class NetProbe {

    static final String SITE_URL = "https://zc110747.github.io/DailyLingo/";

    private static final int TIMEOUT_MILLIS = 6000;

    private NetProbe() {
    }

    /** 只看系统层：是否有已连接、声明了 INTERNET 能力的网络。 */
    static boolean hasNetwork(Context context) {
        try {
            ConnectivityManager manager =
                    (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (manager == null) {
                return false;
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Network network = manager.getActiveNetwork();
                if (network == null) {
                    return false;
                }

                NetworkCapabilities capabilities = manager.getNetworkCapabilities(network);
                return capabilities != null
                        && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
            }

            NetworkInfo info = manager.getActiveNetworkInfo();
            return info != null && info.isConnected();
        } catch (RuntimeException exception) {
            Diagnostics.warn("读取网络状态失败：" + exception.getMessage());
            return false;
        }
    }

    /** 站点是否可达（状态码 5xx 视为不可用）。 */
    static boolean canReachSite() {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(SITE_URL).openConnection();
            connection.setConnectTimeout(TIMEOUT_MILLIS);
            connection.setReadTimeout(TIMEOUT_MILLIS);
            connection.setInstanceFollowRedirects(true);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("User-Agent", "DailyLingo-Android/1.0");
            connection.setRequestProperty("Cache-Control", "no-cache");

            int code = connection.getResponseCode();
            return code > 0 && code < 500;
        } catch (IOException exception) {
            Diagnostics.info("站点探测失败：" + exception.getClass().getSimpleName());
            return false;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    /** 完整判断：有网且站点可达。 */
    static boolean isOnline(Context context) {
        return hasNetwork(context) && canReachSite();
    }

    /** 把 WebView 的错误码翻成人话。 */
    static String describeError(int errorCode) {
        switch (errorCode) {
            case android.webkit.WebViewClient.ERROR_HOST_LOOKUP:
                return "域名解析失败";
            case android.webkit.WebViewClient.ERROR_CONNECT:
                return "无法连接服务器";
            case android.webkit.WebViewClient.ERROR_TIMEOUT:
                return "连接超时";
            case android.webkit.WebViewClient.ERROR_IO:
                return "网络读写失败";
            case android.webkit.WebViewClient.ERROR_UNKNOWN:
                return "未知错误";
            case android.webkit.WebViewClient.ERROR_BAD_URL:
                return "地址格式有误";
            case android.webkit.WebViewClient.ERROR_UNSUPPORTED_SCHEME:
                return "不支持的协议";
            case android.webkit.WebViewClient.ERROR_FAILED_SSL_HANDSHAKE:
                return "安全连接失败";
            case android.webkit.WebViewClient.ERROR_REDIRECT_LOOP:
                return "重定向次数过多";
            default:
                return "错误码 " + errorCode;
        }
    }
}
