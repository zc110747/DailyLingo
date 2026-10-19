package com.dailylingo.app;

import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * 诊断日志：同时写 logcat 与「进度文件同目录」的 {@code dailylingo.log}。
 *
 * <p>手机端没法像桌面端那样直接看到 %TEMP% 里的日志，所以这里落一份到
 * {@code /sdcard/Android/data/&lt;包名&gt;/files/dailylingo.log}，用
 * {@code adb pull} 就能取到完整启动轨迹。</p>
 */
final class Diagnostics {

    private static final String TAG = "DailyLingo";
    private static final String FILE_NAME = "dailylingo.log";
    private static final long MAX_BYTES = 256L * 1024L;

    private static File sDirectory;

    private Diagnostics() {
    }

    /** 在使用任何日志方法之前调用一次；传 null 表示只写 logcat。 */
    static void attach(File directory) {
        sDirectory = directory;
    }

    static void info(String message) {
        write(Log.INFO, "I", message, null);
    }

    static void warn(String message) {
        write(Log.WARN, "W", message, null);
    }

    static void error(String message, Throwable throwable) {
        write(Log.ERROR, "E", message, throwable);
    }

    private static synchronized void write(int priority, String level, String message, Throwable throwable) {
        String detail = throwable == null ? "" : " | " + throwable.getClass().getSimpleName() + ": " + throwable.getMessage();
        try {
            Log.println(priority, TAG, message + detail);
        } catch (RuntimeException ignored) {
            // 日志本身不该影响主流程（例如日志被系统限流）。
        }

        if (sDirectory == null) {
            return;
        }

        String line = timestamp() + " " + level + "/" + TAG + ": " + message + detail + "\n";
        File file = new File(sDirectory, FILE_NAME);
        try {
            if (file.length() > MAX_BYTES) {
                File rolled = new File(sDirectory, FILE_NAME + ".1");
                //noinspection ResultOfMethodCallIgnored
                rolled.delete();
                //noinspection ResultOfMethodCallIgnored
                file.renameTo(rolled);
            }

            try (FileOutputStream stream = new FileOutputStream(file, true);
                 Writer writer = new OutputStreamWriter(stream, StandardCharsets.UTF_8)) {
                writer.write(line);
            }
        } catch (IOException ignored) {
            // 外部存储不可用（未挂载 / 被拔掉）时静默降级，logcat 仍是完整轨迹。
        }
    }

    private static String timestamp() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(new Date());
    }
}
