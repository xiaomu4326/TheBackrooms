package com.xiaomu.backrooms;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** 缓存页：缓存统计、批量下载和按主页分类查看已缓存层级。 */
public class CacheActivity extends Activity {

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int BORDER = Color.parseColor("#E5DCC8");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean downloadCancelled = new AtomicBoolean(false);

    private String source = "wikidot";
    private volatile boolean downloading = false;

    private TextView statsView;
    private TextView progressView;
    private TextView sourceView;
    private LinearLayout listContent;
    private Button downloadAllButton;
    private Button downloadSelectedButton;
    private Button clearButton;
    private Button refreshButton;
    private Button cancelButton;
    private Button sourceWikidotButton;
    private Button sourceFandomButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String requestedSource = getIntent().getStringExtra("source");
        if ("fandom".equals(requestedSource)) {
            source = "fandom";
        }
        getWindow().setStatusBarColor(PAPER);
        getWindow().setNavigationBarColor(PAPER);
        getWindow().getDecorView().setSystemUiVisibility(
                android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        buildUi();
        updateSourceButtons();
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
                Python.getInstance().getModule("mobile")
                        .callAttr("init", getFilesDir().getAbsolutePath(), "");
            }
        } catch (Throwable error) {
            statsView.setText("Python 未初始化：" + error.getMessage());
            return;
        }
        loadCacheTree();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable rounded(int fill, int stroke, int radiusDp, int strokeDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setShape(GradientDrawable.RECTANGLE);
        drawable.setCornerRadius(dp(radiusDp));
        drawable.setColor(fill);
        if (strokeDp > 0) {
            drawable.setStroke(dp(strokeDp), stroke);
        }
        return drawable;
    }

    private TextView text(String value, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        if (bold) {
            view.setTypeface(Typeface.DEFAULT_BOLD);
        }
        return view;
    }

    private Button button(String label, boolean primary) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(13);
        button.setTypeface(Typeface.DEFAULT_BOLD);
        button.setGravity(Gravity.CENTER);
        button.setIncludeFontPadding(false);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        button.setPadding(dp(10), 0, dp(10), 0);
        button.setElevation(0);
        button.setStateListAnimator(null);
        button.setTextColor(INK);
        button.setBackground(primary
                ? rounded(ACCENT, 0, 10, 0)
                : rounded(PANEL, Color.parseColor("#D8C9AE"), 10, 1));
        return button;
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAPER);
        setContentView(root);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(10), 0, dp(14), 0);
        root.addView(header, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        TextView back = text("‹", 32, INK, false);
        back.setGravity(Gravity.CENTER);
        back.setPadding(dp(6), 0, dp(12), dp(3));
        back.setOnClickListener(v -> finish());
        header.addView(back, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));

        TextView title = text("缓存", 17, INK, true);
        title.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(title, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        sourceView = text(
                "fandom".equals(source) ? "Fandom" : "Wikidot", 11, MUTED, false
        );
        sourceView.setGravity(Gravity.CENTER_VERTICAL | Gravity.END);
        header.addView(sourceView);

        View divider = new View(this);
        divider.setBackgroundColor(BORDER);
        root.addView(divider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(14), dp(16), dp(16));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        statsView = text("正在读取缓存…", 13, INK, true);
        content.addView(statsView);

        TextView note = text(
                "按主页相同的分组和编号分段展示；默认折叠，点分组或分段展开。",
                11, MUTED, false
        );
        note.setPadding(0, dp(4), 0, dp(10));
        content.addView(note);

        LinearLayout sourceRow = new LinearLayout(this);
        sourceRow.setOrientation(LinearLayout.HORIZONTAL);
        sourceRow.setGravity(Gravity.CENTER_VERTICAL);
        content.addView(sourceRow, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40)));

        TextView sourceLabel = text("数据源", 11, MUTED, false);
        sourceLabel.setPadding(0, 0, dp(8), 0);
        sourceRow.addView(sourceLabel);

        sourceWikidotButton = button("Wikidot", false);
        sourceWikidotButton.setOnClickListener(v -> switchSource("wikidot"));
        sourceRow.addView(sourceWikidotButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(36)));

        sourceFandomButton = button("Fandom", false);
        sourceFandomButton.setOnClickListener(v -> switchSource("fandom"));
        LinearLayout.LayoutParams fandomParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
        fandomParams.leftMargin = dp(8);
        sourceRow.addView(sourceFandomButton, fandomParams);

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        content.addView(row1, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44)));
        downloadAllButton = button("下载全部缓存", true);
        downloadAllButton.setOnClickListener(v -> confirmDownloadAll());
        row1.addView(downloadAllButton, new LinearLayout.LayoutParams(0, dp(44), 1f));
        downloadSelectedButton = button("下载指定层级", false);
        downloadSelectedButton.setOnClickListener(v -> askSelectedLevels());
        LinearLayout.LayoutParams selectedParams = new LinearLayout.LayoutParams(0, dp(44), 1f);
        selectedParams.leftMargin = dp(8);
        row1.addView(downloadSelectedButton, selectedParams);

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams row2Params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40));
        row2Params.topMargin = dp(8);
        content.addView(row2, row2Params);
        clearButton = button("清理缓存", false);
        clearButton.setOnClickListener(v -> confirmClear());
        row2.addView(clearButton, new LinearLayout.LayoutParams(0, dp(40), 1f));
        refreshButton = button("刷新", false);
        refreshButton.setOnClickListener(v -> loadCacheTree());
        LinearLayout.LayoutParams refreshParams = new LinearLayout.LayoutParams(0, dp(40), 1f);
        refreshParams.leftMargin = dp(8);
        row2.addView(refreshButton, refreshParams);

        progressView = text("未开始", 11, MUTED, false);
        progressView.setPadding(0, dp(8), 0, 0);
        content.addView(progressView);

        cancelButton = button("取消下载", false);
        LinearLayout.LayoutParams cancelParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(40));
        cancelParams.topMargin = dp(8);
        cancelButton.setVisibility(View.GONE);
        cancelButton.setOnClickListener(v -> {
            downloadCancelled.set(true);
            cancelButton.setEnabled(false);
            progressView.setText("正在取消…");
        });
        content.addView(cancelButton, cancelParams);

        listContent = new LinearLayout(this);
        listContent.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams listParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        listParams.topMargin = dp(12);
        content.addView(listContent, listParams);
    }

    private void updateSourceButtons() {
        if (sourceWikidotButton == null || sourceFandomButton == null) {
            return;
        }
        applySourceButton(sourceWikidotButton, "wikidot".equals(source));
        applySourceButton(sourceFandomButton, "fandom".equals(source));
    }

    private void applySourceButton(Button button, boolean active) {
        button.setBackground(active
                ? rounded(ACCENT, 0, 10, 0)
                : rounded(PANEL, Color.parseColor("#D8C9AE"), 10, 1));
        button.setTextColor(INK);
    }

    private void switchSource(String newSource) {
        if (newSource.equals(source)) {
            return;
        }
        if (downloading) {
            Toast.makeText(this, "请先取消当前下载，再切换数据源", Toast.LENGTH_SHORT).show();
            return;
        }
        source = newSource;
        sourceView.setText("fandom".equals(source) ? "Fandom" : "Wikidot");
        updateSourceButtons();
        progressView.setText("已切换到 " + ("fandom".equals(source) ? "Fandom" : "Wikidot"));
        loadCacheTree();
    }

    private void loadCacheTree() {
        if (downloading) {
            return;
        }
        refreshButton.setEnabled(false);
        executor.execute(() -> {
            String json;
            try {
                json = Python.getInstance().getModule("mobile")
                        .callAttr("cache_tree", source).toString();
            } catch (Throwable error) {
                json = "{\"ok\":false,\"error\":\"" + error.getMessage() + "\"}";
            }
            String result = json;
            mainHandler.post(() -> {
                if (isFinishing() || isDestroyed()) {
                    return;
                }
                refreshButton.setEnabled(true);
                try {
                    JSONObject object = new JSONObject(result);
                    if (!object.optBoolean("ok", false)) {
                        statsView.setText("读取失败：" + object.optString("error"));
                        return;
                    }
                    int cached = object.optInt("cached_total", 0);
                    int total = object.optInt("index_total", 0);
                    int files = object.optInt("files", 0);
                    long bytes = object.optLong("bytes", 0);
                    statsView.setText(
                            "已缓存 " + cached + " / " + total + " 个层级 · "
                                    + files + " 个缓存文件 · " + formatBytes(bytes)
                    );
                    renderGroups(object.optJSONArray("groups"));
                } catch (Exception error) {
                    statsView.setText("读取失败：" + error.getMessage());
                }
            });
        });
    }

    private void renderGroups(JSONArray groups) {
        listContent.removeAllViews();
        if (groups == null || groups.length() == 0) {
            TextView empty = text("暂无缓存层级，可点击上方按钮下载", 12, MUTED, false);
            empty.setPadding(0, dp(16), 0, 0);
            listContent.addView(empty);
            return;
        }
        for (int i = 0; i < groups.length(); i++) {
            JSONObject group = groups.optJSONObject(i);
            if (group == null) {
                continue;
            }
            addGroupRow(group);
        }
    }

    private void addGroupRow(JSONObject group) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams boxParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        boxParams.bottomMargin = dp(6);
        listContent.addView(box, boxParams);

        TextView header = text(
                "▸ " + group.optString("label") + "（" + group.optInt("count") + "）",
                13, ACCENT, true
        );
        header.setPadding(dp(12), dp(10), dp(12), dp(10));
        header.setBackground(rounded(PANEL, BORDER, 8, 1));
        box.addView(header);

        LinearLayout children = new LinearLayout(this);
        children.setOrientation(LinearLayout.VERTICAL);
        children.setVisibility(View.GONE);
        box.addView(children);

        header.setOnClickListener(v -> {
            boolean expand = children.getVisibility() != View.VISIBLE;
            if (expand && children.getChildCount() == 0) {
                buildGroupChildren(group, children);
            }
            children.setVisibility(expand ? View.VISIBLE : View.GONE);
            header.setText((expand ? "▾ " : "▸ ") + group.optString("label")
                    + "（" + group.optInt("count") + "）");
        });
    }

    private void buildGroupChildren(JSONObject group, LinearLayout parent) {
        JSONArray sections = group.optJSONArray("sections");
        if (sections != null && sections.length() > 0) {
            for (int i = 0; i < sections.length(); i++) {
                JSONObject section = sections.optJSONObject(i);
                if (section != null) {
                    addSectionRow(section, parent);
                }
            }
            return;
        }
        addEntries(group.optJSONArray("entries"), parent);
    }

    private void addSectionRow(JSONObject section, LinearLayout parent) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams boxParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        boxParams.topMargin = dp(3);
        parent.addView(box, boxParams);

        TextView header = text(
                "▸ " + section.optString("label") + "（" + section.optInt("count") + "）",
                12, INK, true
        );
        header.setPadding(dp(22), dp(8), dp(12), dp(8));
        header.setBackground(rounded(PANEL, BORDER, 8, 1));
        box.addView(header);

        LinearLayout children = new LinearLayout(this);
        children.setOrientation(LinearLayout.VERTICAL);
        children.setVisibility(View.GONE);
        box.addView(children);

        header.setOnClickListener(v -> {
            boolean expand = children.getVisibility() != View.VISIBLE;
            if (expand && children.getChildCount() == 0) {
                addEntries(section.optJSONArray("entries"), children);
            }
            children.setVisibility(expand ? View.VISIBLE : View.GONE);
            header.setText((expand ? "▾ " : "▸ ") + section.optString("label")
                    + "（" + section.optInt("count") + "）");
        });
    }

    private void addEntries(JSONArray entries, LinearLayout parent) {
        if (entries == null) {
            return;
        }
        for (int i = 0; i < entries.length(); i++) {
            JSONObject item = entries.optJSONObject(i);
            if (item == null) {
                continue;
            }
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            int depth = item.optInt("depth", 0);
            row.setPadding(dp(34 + depth * 18), dp(7), dp(12), dp(7));

            row.addView(text(item.optString("title"), 12, INK, false));
            TextView slug = text(item.optString("slug"), 10, MUTED, false);
            slug.setPadding(0, dp(2), 0, 0);
            row.addView(slug);

            View line = new View(this);
            line.setBackgroundColor(BORDER);
            LinearLayout.LayoutParams lineParams = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(1));
            lineParams.topMargin = dp(4);
            row.addView(line, lineParams);
            parent.addView(row);
        }
    }

    private void confirmDownloadAll() {
        if (downloading) {
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("下载全部缓存")
                .setMessage("将按当前索引逐个下载所有层级页面。首次下载可能需要 30–60 分钟，"
                        + "期间可以取消。确定开始吗？")
                .setPositiveButton("开始", (dialog, which) -> startDownloadAll())
                .setNegativeButton("取消", null)
                .show();
    }

    private void startDownloadAll() {
        setDownloading(true);
        progressView.setText("正在读取索引…");
        downloadCancelled.set(false);
        executor.execute(() -> {
            try {
                String json = Python.getInstance().getModule("mobile")
                        .callAttr("entries", source).toString();
                JSONObject object = new JSONObject(json);
                if (!object.optBoolean("ok", false)) {
                    finishDownload("下载失败：" + object.optString("error"));
                    return;
                }
                JSONArray array = object.optJSONArray("entries");
                List<Target> targets = new ArrayList<>();
                if (array != null) {
                    for (int i = 0; i < array.length(); i++) {
                        JSONObject item = array.optJSONObject(i);
                        if (item == null) {
                            continue;
                        }
                        Target target = new Target();
                        target.slug = item.optString("slug");
                        target.title = item.optString("title", target.slug);
                        if (!target.slug.isEmpty()) {
                            targets.add(target);
                        }
                    }
                }
                if (targets.isEmpty()) {
                    finishDownload("索引为空，未下载");
                    return;
                }
                runTargets(targets);
            } catch (Throwable error) {
                finishDownload("下载失败：" + error.getMessage());
            }
        });
    }

    private void askSelectedLevels() {
        if (downloading) {
            return;
        }
        EditText input = new EditText(this);
        input.setHint("例如：0, 0.1, C-156，每行一个");
        input.setText("0, 0.1, C-156");
        input.setMinLines(3);
        input.setGravity(Gravity.TOP | Gravity.START);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(8), dp(20), 0);
        box.addView(input);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("下载指定层级")
                .setView(box)
                .setPositiveButton("开始", null)
                .setNegativeButton("取消", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    List<String> queries = parseQueries(input.getText().toString());
                    if (queries.isEmpty()) {
                        input.setError("请输入至少一个层级");
                        return;
                    }
                    dialog.dismiss();
                    startSelectedDownload(queries);
                }));
        dialog.show();
    }

    private List<String> parseQueries(String raw) {
        List<String> queries = new ArrayList<>();
        for (String part : raw.split("[,，、;；\\n\\r]+")) {
            String query = part.trim();
            if (!query.isEmpty() && !queries.contains(query)) {
                queries.add(query);
            }
        }
        return queries;
    }

    private void startSelectedDownload(List<String> queries) {
        setDownloading(true);
        progressView.setText("准备下载 " + queries.size() + " 个层级…");
        downloadCancelled.set(false);
        executor.execute(() -> {
            int total = queries.size();
            int ok = 0;
            int fail = 0;
            int done = 0;
            for (String query : queries) {
                if (downloadCancelled.get()) {
                    break;
                }
                try {
                    JSONObject object = new JSONObject(
                            Python.getInstance().getModule("mobile")
                                    .callAttr("fetch", source, query, false).toString()
                    );
                    if (object.optBoolean("ok", false)) {
                        ok++;
                    } else {
                        fail++;
                    }
                } catch (Throwable error) {
                    fail++;
                }
                done++;
                int currentDone = done;
                int currentOk = ok;
                int currentFail = fail;
                mainHandler.post(() -> updateProgress(
                        currentDone, total, currentOk, currentFail, query
                ));
            }
            finishDownload(downloadCancelled.get()
                    ? String.format(Locale.ROOT, "已取消：成功 %d，失败 %d", ok, fail)
                    : String.format(Locale.ROOT, "下载完成：成功 %d，失败 %d", ok, fail));
        });
    }

    private void runTargets(List<Target> targets) {
        int total = targets.size();
        int ok = 0;
        int fail = 0;
        int done = 0;
        for (Target target : targets) {
            if (downloadCancelled.get()) {
                break;
            }
            try {
                JSONObject object = new JSONObject(
                        Python.getInstance().getModule("mobile")
                                .callAttr("fetch_slug", source, target.slug,
                                        target.title, false).toString()
                );
                if (object.optBoolean("ok", false)) {
                    ok++;
                } else {
                    fail++;
                }
            } catch (Throwable error) {
                fail++;
            }
            done++;
            int currentDone = done;
            int currentOk = ok;
            int currentFail = fail;
            mainHandler.post(() -> updateProgress(
                    currentDone, total, currentOk, currentFail, target.title
            ));
        }
        finishDownload(downloadCancelled.get()
                ? String.format(Locale.ROOT, "已取消：成功 %d，失败 %d", ok, fail)
                : String.format(Locale.ROOT, "下载完成：成功 %d，失败 %d", ok, fail));
    }

    private void updateProgress(int done, int total, int ok, int fail, String title) {
        if (isFinishing() || isDestroyed()) {
            return;
        }
        String shortTitle = title;
        if (shortTitle.length() > 28) {
            shortTitle = shortTitle.substring(0, 28) + "…";
        }
        progressView.setText(String.format(
                Locale.ROOT, "下载中 %d/%d · 成功 %d · 失败 %d\n%s",
                done, total, ok, fail, shortTitle
        ));
    }

    private void setDownloading(boolean running) {
        downloading = running;
        downloadAllButton.setEnabled(!running);
        downloadSelectedButton.setEnabled(!running);
        clearButton.setEnabled(!running);
        refreshButton.setEnabled(!running);
        sourceWikidotButton.setEnabled(!running);
        sourceFandomButton.setEnabled(!running);
        cancelButton.setVisibility(running ? View.VISIBLE : View.GONE);
        cancelButton.setEnabled(running);
    }

    private void finishDownload(String message) {
        downloading = false;
        downloadCancelled.set(false);
        mainHandler.post(() -> {
            if (isFinishing() || isDestroyed()) {
                return;
            }
            setDownloading(false);
            progressView.setText(message);
            loadCacheTree();
        });
    }

    private void confirmClear() {
        if (downloading) {
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("清理缓存")
                .setMessage("清理后，下次查询需要重新从站点下载。确定清理吗？")
                .setPositiveButton("清理", (dialog, which) -> clearCache())
                .setNegativeButton("取消", null)
                .show();
    }

    private void clearCache() {
        setDownloading(true);
        progressView.setText("正在清理…");
        executor.execute(() -> {
            try {
                String json = Python.getInstance().getModule("mobile")
                        .callAttr("clear_cache").toString();
                JSONObject object = new JSONObject(json);
                if (!object.optBoolean("ok", false)) {
                    finishDownload("清理失败：" + object.optString("error"));
                    return;
                }
                finishDownload("缓存已清理");
            } catch (Throwable error) {
                finishDownload("清理失败：" + error.getMessage());
            }
        });
    }

    private String formatBytes(long bytes) {
        if (bytes < 1024) {
            return bytes + " B";
        }
        double kb = bytes / 1024.0;
        if (kb < 1024) {
            return String.format(Locale.ROOT, "%.1f KB", kb);
        }
        double mb = kb / 1024.0;
        if (mb < 1024) {
            return String.format(Locale.ROOT, "%.1f MB", mb);
        }
        return String.format(Locale.ROOT, "%.2f GB", mb / 1024.0);
    }

    @Override
    public void onBackPressed() {
        downloadCancelled.set(true);
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        downloadCancelled.set(true);
        super.onDestroy();
    }

    private static class Target {
        String slug = "";
        String title = "";
    }
}
