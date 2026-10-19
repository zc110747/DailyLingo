package com.dailylingo.app;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TimeZone;

/**
 * 学习进度文件的读写。
 *
 * <p>文件放在应用的外部私有目录（{@code /sdcard/Android/data/com.dailylingo.app/files/}），
 * 内容与网页端「导出进度」逐字同构：2 空格缩进、键序 schemaVersion / completedArticles /
 * updatedAt / exportedAt、LF 换行、结尾换行。因此这份文件可以直接拿到网页端「导入进度」使用。</p>
 */
final class ProgressStore {

    /** 与 {@code assets/js/progress.js} 的 {@code SCHEMA_VERSION} 一致。 */
    static final int SCHEMA_VERSION = 1;

    /** 与网页端相同的 localStorage 键。 */
    static final String STORAGE_KEY = "dailylingo_learning_progress_v1";

    /** 进度文件名。 */
    static final String FILE_NAME = "dailylingo-progress.json";

    private static final String TIMESTAMP_PATTERN = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";

    private final File mFile;
    private String mLastSignature;

    private Document mCurrent;

    ProgressStore(File directory) {
        mFile = new File(directory, FILE_NAME);
    }

    File file() {
        return mFile;
    }

    /** 当前内存中的进度；{@link #load()} 之前为 null。 */
    Document current() {
        return mCurrent;
    }

    int completedCount() {
        return mCurrent == null ? 0 : mCurrent.completedArticles.size();
    }

    /** 把任意输入规整成四位补零的文章 ID；非法输入返回空串。 */
    static String normalizeId(String raw) {
        if (raw == null) {
            return "";
        }

        String text = raw.trim();
        if (text.isEmpty()) {
            return "";
        }

        for (int index = 0; index < text.length(); index++) {
            char ch = text.charAt(index);
            if (ch < '0' || ch > '9') {
                return "";
            }
        }

        StringBuilder builder = new StringBuilder(text);
        while (builder.length() < 4) {
            builder.insert(0, '0');
        }

        return builder.toString();
    }

    /** 去重后按字典序排序，与网页端的 {@code uniqueSorted()} 一致。 */
    static List<String> dedupe(List<String> ids) {
        Set<String> unique = new LinkedHashSet<>(ids);
        List<String> result = new ArrayList<>(unique);
        Collections.sort(result);
        return result;
    }

    /** 当前 UTC 时间，格式与 JS 的 {@code toISOString()} 一致。 */
    static String timestamp() {
        SimpleDateFormat format = new SimpleDateFormat(TIMESTAMP_PATTERN, Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date());
    }

    /** 读取进度文件；不存在或损坏时返回 null（损坏文件先留档再删除）。 */
    Document load() {
        if (!mFile.isFile()) {
            mCurrent = null;
            return null;
        }

        String text;
        try {
            text = readText(mFile);
        } catch (IOException exception) {
            Diagnostics.warn("读取进度文件失败：" + exception.getMessage());
            mCurrent = null;
            return null;
        }

        ParseResult result = parse(text);
        if (result.document == null) {
            Diagnostics.warn("进度文件无法解析（" + result.error + "），已备份后忽略。");
            backupBrokenFile();
            mCurrent = null;
            return null;
        }

        if (!result.error.isEmpty()) {
            Diagnostics.info("进度文件：" + result.error);
        }

        mCurrent = result.document;
        mLastSignature = signature(result.document);
        return result.document;
    }

    /** 注入网页 localStorage 用的种子文本；没有可用文件时返回 null。 */
    String loadSeedText() {
        Document document = load();
        return document == null ? null : serialize(document);
    }

    /**
     * 接收网页推送的 localStorage 原文并落盘。
     *
     * @return 是否真的写了文件（内容没变化时不写，避免轮询每次都落盘）
     */
    boolean applyWebState(String rawJson) {
        Document document;
        if (rawJson == null || rawJson.trim().isEmpty()) {
            document = new Document(SCHEMA_VERSION, new ArrayList<String>(), "", null);
        } else {
            ParseResult result = parse(rawJson);
            if (result.document == null) {
                Diagnostics.warn("网页进度无法解析，已忽略：" + result.error);
                return false;
            }
            document = result.document;
        }

        mCurrent = document;

        String signature = signature(document);
        if (signature.equals(mLastSignature)) {
            return false;
        }

        mLastSignature = signature;
        return write(document);
    }

    /** 写入进度文件（先写 .tmp 再替换，避免留下半截文件）。 */
    boolean write(Document document) {
        document.exportedAt = timestamp();
        String text = serialize(document);

        File temporary = new File(mFile.getParentFile(), FILE_NAME + ".tmp");
        try {
            File parent = mFile.getParentFile();
            if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                Diagnostics.warn("无法创建进度目录：" + parent);
            }

            try (FileOutputStream stream = new FileOutputStream(temporary)) {
                stream.write(text.getBytes(StandardCharsets.UTF_8));
                stream.getFD().sync();
            }

            if (!temporary.renameTo(mFile)) {
                // 某些文件系统不支持覆盖式 rename，退化成「先删再改名」。
                //noinspection ResultOfMethodCallIgnored
                mFile.delete();
                if (!temporary.renameTo(mFile)) {
                    Diagnostics.warn("替换进度文件失败：" + mFile);
                    //noinspection ResultOfMethodCallIgnored
                    temporary.delete();
                    return false;
                }
            }
        } catch (IOException exception) {
            Diagnostics.warn("写入进度文件失败：" + exception.getMessage());
            //noinspection ResultOfMethodCallIgnored
            temporary.delete();
            return false;
        }

        mLastSignature = signature(document);
        mCurrent = document;
        return true;
    }

    /** 序列化成与网页端导出文件同构的文本（2 空格缩进 + LF + 结尾换行）。 */
    static String serialize(Document document) {
        List<String> ids = dedupe(document.completedArticles);
        String updatedAt = document.updatedAt == null || document.updatedAt.isEmpty()
                ? timestamp()
                : document.updatedAt;
        String exportedAt = document.exportedAt == null ? timestamp() : document.exportedAt;

        StringBuilder builder = new StringBuilder(256);
        builder.append("{\n");
        builder.append("  \"schemaVersion\": ").append(SCHEMA_VERSION).append(",\n");

        if (ids.isEmpty()) {
            builder.append("  \"completedArticles\": [],\n");
        } else {
            builder.append("  \"completedArticles\": [\n");
            for (int index = 0; index < ids.size(); index++) {
                builder.append("    \"").append(escape(ids.get(index))).append("\"");
                builder.append(index == ids.size() - 1 ? "\n" : ",\n");
            }
            builder.append("  ],\n");
        }

        builder.append("  \"updatedAt\": \"").append(escape(updatedAt)).append("\",\n");
        builder.append("  \"exportedAt\": \"").append(escape(exportedAt)).append("\"\n");
        builder.append("}\n");
        return builder.toString();
    }

    /** 与网页端 {@code parseProgressPayload()} 同一套校验。 */
    static ParseResult parse(String text) {
        if (text == null || text.trim().isEmpty()) {
            return ParseResult.failure("内容是空的。");
        }

        JSONObject root;
        try {
            root = new JSONObject(text);
        } catch (JSONException exception) {
            return ParseResult.failure("不是合法的 JSON 文本。");
        }

        if (!root.has("schemaVersion")) {
            return ParseResult.failure("缺少 schemaVersion，无法确认文件格式。");
        }

        int version = root.optInt("schemaVersion", Integer.MIN_VALUE);
        if (version == Integer.MIN_VALUE) {
            return ParseResult.failure("schemaVersion 必须是整数。");
        }

        if (version != SCHEMA_VERSION) {
            return ParseResult.failure("不支持的版本：schemaVersion=" + version + "（本程序只支持 " + SCHEMA_VERSION + "）。");
        }

        JSONArray list = root.optJSONArray("completedArticles");
        if (list == null) {
            return ParseResult.failure("completedArticles 必须是数组。");
        }

        List<String> ids = new ArrayList<>();
        int invalid = 0;
        for (int index = 0; index < list.length(); index++) {
            String id = normalizeId(list.optString(index, ""));
            if (id.isEmpty()) {
                invalid++;
            } else {
                ids.add(id);
            }
        }

        String updatedAt = root.optString("updatedAt", "");

        String exportedAt = null;
        if (root.has("exportedAt") && !root.isNull("exportedAt")) {
            String value = root.optString("exportedAt", "");
            exportedAt = value.isEmpty() ? null : value;
        }

        Document document = new Document(SCHEMA_VERSION, dedupe(ids), updatedAt, exportedAt);
        String error = invalid > 0 ? "已忽略 " + invalid + " 条非法的文章 ID。" : "";
        return new ParseResult(document, error);
    }

    private static String signature(Document document) {
        return document.updatedAt + "|" + String.join(",", dedupe(document.completedArticles));
    }

    private static String escape(String value) {
        StringBuilder builder = new StringBuilder(value.length() + 8);
        for (int index = 0; index < value.length(); index++) {
            char ch = value.charAt(index);
            switch (ch) {
                case '"':
                    builder.append("\\\"");
                    break;
                case '\\':
                    builder.append("\\\\");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                default:
                    builder.append(ch);
                    break;
            }
        }
        return builder.toString();
    }

    private static String readText(File file) throws IOException {
        try (FileInputStream stream = new FileInputStream(file)) {
            byte[] buffer = new byte[(int) Math.min(file.length(), Integer.MAX_VALUE)];
            int offset = 0;
            while (offset < buffer.length) {
                int read = stream.read(buffer, offset, buffer.length - offset);
                if (read < 0) {
                    break;
                }
                offset += read;
            }

            return new String(buffer, 0, offset, StandardCharsets.UTF_8);
        }
    }

    private void backupBrokenFile() {
        try {
            String suffix = new SimpleDateFormat("yyyyMMddHHmmss", Locale.US).format(new Date());
            String name = FILE_NAME.replace(".json", "") + ".corrupt-" + suffix + ".json";
            File backup = new File(mFile.getParentFile(), name);

            byte[] data;
            try (FileInputStream stream = new FileInputStream(mFile)) {
                data = new byte[(int) Math.min(mFile.length(), Integer.MAX_VALUE)];
                int offset = 0;
                while (offset < data.length) {
                    int read = stream.read(data, offset, data.length - offset);
                    if (read < 0) {
                        break;
                    }
                    offset += read;
                }
                try (FileOutputStream out = new FileOutputStream(backup)) {
                    out.write(data, 0, offset);
                }
            }

            //noinspection ResultOfMethodCallIgnored
            mFile.delete();
            Diagnostics.info("损坏的进度文件已备份为 " + backup.getName() + "。");
        } catch (IOException exception) {
            Diagnostics.warn("备份损坏的进度文件失败：" + exception.getMessage());
        }
    }

    /** 一份进度文档（字段顺序即序列化顺序）。 */
    static final class Document {
        final int schemaVersion;
        final List<String> completedArticles;
        final String updatedAt;
        String exportedAt;

        Document(int schemaVersion, List<String> completedArticles, String updatedAt, String exportedAt) {
            this.schemaVersion = schemaVersion;
            this.completedArticles = completedArticles;
            this.updatedAt = updatedAt == null ? "" : updatedAt;
            this.exportedAt = exportedAt;
        }
    }

    /** 解析结果：成功时 document 非空，error 里可能带「已忽略 N 条」这类提示。 */
    static final class ParseResult {
        final Document document;
        final String error;

        ParseResult(Document document, String error) {
            this.document = document;
            this.error = error;
        }

        static ParseResult failure(String error) {
            return new ParseResult(null, error);
        }
    }
}
