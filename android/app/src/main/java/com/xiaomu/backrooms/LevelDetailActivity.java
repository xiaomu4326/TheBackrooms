package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 层级详情页：参考 CharactersBirthday 的 Nord 详情卡布局。
 * 深色顶栏 + 浅灰蓝背景 + 白色圆角卡片 + 大号强调信息。
 */
public class LevelDetailActivity extends Activity {

    private static final int BG = Color.parseColor("#F4F1E8");
    private static final int HEADER_BG = Color.parseColor("#FBF8F0");
    private static final int HEADER_FG = Color.parseColor("#211E1A");
    private static final int HEADER_SUB = Color.parseColor("#8A6A1F");
    private static final int CARD_BG = Color.parseColor("#FBF8F0");
    private static final int CARD_BORDER = Color.parseColor("#E5DCC8");
    private static final int TEXT = Color.parseColor("#211E1A");
    private static final int SUBTEXT = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");
    private static final int ACCENT_DARK = Color.parseColor("#8A6A1F");
    private static final int ERROR = Color.parseColor("#9B2C1F");

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private LinearLayout content;
    private ScrollView scroll;
    private TextView statusView;
    private TextView sourceBadge;
    private Button openButton;
    private Button refreshButton;

    private String currentJson = "";
    private String currentUrl = "";
    private String source = "";
    private String slug = "";
    private String title = "";
    private String query = "";
    private String proxy = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        buildUi();

        currentJson = getIntent().getStringExtra("json");
        source = value(getIntent().getStringExtra("source"), "wikidot");
        slug = value(getIntent().getStringExtra("slug"), "");
        title = value(getIntent().getStringExtra("title"), "");
        query = value(getIntent().getStringExtra("query"), "");
        proxy = value(getIntent().getStringExtra("proxy"), "");
        sourceBadge.setText("fandom".equals(source) ? "Fandom" : "Wikidot");

        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            Python.getInstance().getModule("mobile")
                    .callAttr("init", getFilesDir().getAbsolutePath(), proxy);
        } catch (Throwable ignored) {
            // 已经初始化过时重复 init 也无妨；这里只防止极端情况下崩溃
        }

        if (currentJson == null || currentJson.isEmpty()) {
            renderError("没有收到层级数据");
        } else {
            render(currentJson);
        }
    }

    private static String value(String value, String fallback) {
        return value == null ? fallback : value;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        setContentView(root);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setBackgroundColor(HEADER_BG);
        header.setPadding(dp(10), 0, dp(14), 0);
        root.addView(header, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        View headerDivider = new View(this);
        headerDivider.setBackgroundColor(CARD_BORDER);
        root.addView(headerDivider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        TextView back = new TextView(this);
        back.setText("‹");
        back.setTextSize(32);
        back.setTextColor(HEADER_FG);
        back.setGravity(Gravity.CENTER);
        back.setPadding(dp(6), 0, dp(12), dp(3));
        back.setContentDescription("返回");
        back.setOnClickListener(v -> finish());
        header.addView(back, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));

        TextView headerTitle = new TextView(this);
        headerTitle.setText("层级详情");
        headerTitle.setTextSize(16);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setTextColor(HEADER_FG);
        headerTitle.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(headerTitle, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        sourceBadge = new TextView(this);
        sourceBadge.setText("Wikidot");
        sourceBadge.setTextSize(11);
        sourceBadge.setTextColor(HEADER_SUB);
        sourceBadge.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(sourceBadge);

        scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(14), dp(14), dp(14), dp(14));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout bottom = new LinearLayout(this);
        bottom.setOrientation(LinearLayout.VERTICAL);
        bottom.setBackgroundColor(CARD_BG);
        bottom.setPadding(dp(12), dp(8), dp(12), dp(8));
        root.addView(bottom);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        openButton = actionButton("打开原文", true);
        LinearLayout.LayoutParams openParams = new LinearLayout.LayoutParams(
                0, dp(46), 1f);
        openParams.rightMargin = dp(5);
        actions.addView(openButton, openParams);
        refreshButton = actionButton("刷新", false);
        LinearLayout.LayoutParams refreshParams = new LinearLayout.LayoutParams(
                0, dp(46), 1f);
        refreshParams.leftMargin = dp(5);
        actions.addView(refreshButton, refreshParams);
        bottom.addView(actions);

        statusView = new TextView(this);
        statusView.setTextSize(10);
        statusView.setTextColor(SUBTEXT);
        statusView.setPadding(dp(2), dp(4), 0, 0);
        bottom.addView(statusView);

        openButton.setOnClickListener(v -> {
            if (!currentUrl.isEmpty()) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(currentUrl)));
            }
        });
        refreshButton.setOnClickListener(v -> refresh());
    }

    private Button actionButton(String text, boolean primary) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextSize(13);
        button.setTypeface(Typeface.DEFAULT_BOLD);
        button.setGravity(Gravity.CENTER);
        button.setIncludeFontPadding(false);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        button.setPadding(dp(12), 0, dp(12), 0);
        button.setElevation(0);
        button.setStateListAnimator(null);
        button.setBackground(primary
                ? rounded(ACCENT, 0, 8, 0)
                : rounded(CARD_BG, Color.parseColor("#C8D0D8"), 8, 1));
        button.setTextColor(TEXT);
        return button;
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

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(rounded(CARD_BG, CARD_BORDER, 10, 1));
        card.setPadding(dp(14), dp(13), dp(14), dp(13));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = dp(12);
        card.setLayoutParams(params);
        return card;
    }

    private void addSectionTitle(LinearLayout card, String label) {
        TextView view = text(label, 11, SUBTEXT, true);
        view.setPadding(0, 0, 0, dp(5));
        card.addView(view);
    }

    private void addDivider(LinearLayout card) {
        ViewGroup divider = new LinearLayout(this);
        divider.setBackgroundColor(CARD_BORDER);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1));
        params.topMargin = dp(10);
        params.bottomMargin = dp(10);
        card.addView(divider, params);
    }

    private void render(String json) {
        content.removeAllViews();
        try {
            JSONObject obj = new JSONObject(json);
            if (!obj.optBoolean("ok", false)) {
                renderError(obj.optString("error", "未知错误"));
                return;
            }
            currentJson = json;
            currentUrl = obj.optString("url", "");

            String label = obj.optString("label", "");
            String alias = obj.optString("alias", "");
            String name = label.isEmpty() ? obj.optString("title", "") : label;

            LinearLayout main = card();

            TextView nameView = text(name, 22, TEXT, true);
            nameView.setPadding(0, 0, 0, dp(2));
            main.addView(nameView);

            if (!alias.isEmpty()) {
                TextView aliasView = text("“" + alias + "”", 14, ACCENT_DARK, false);
                aliasView.setPadding(0, 0, 0, dp(4));
                main.addView(aliasView);
            }

            String code = obj.optString("code", "");
            String revision = obj.optString("revision", "");
            String updatedAt = obj.optString("updated_at", "");
            StringBuilder meta = new StringBuilder();
            if (!code.isEmpty()) {
                meta.append("编号 ").append(code);
            }
            if (!revision.isEmpty()) {
                if (meta.length() > 0) {
                    meta.append("  ·  ");
                }
                meta.append("页面版本 ").append(revision);
            }
            if (!updatedAt.isEmpty()) {
                if (meta.length() > 0) {
                    meta.append("  ·  ");
                }
                meta.append("最后编辑 ").append(updatedAt);
            }
            if (meta.length() > 0) {
                TextView metaView = text(meta.toString(), 10, SUBTEXT, false);
                main.addView(metaView);
            }

            addDivider(main);
            addSectionTitle(main, "生存难度");

            String classText = obj.optString("class_text", "未标注");
            String classColor = obj.optString("class_color", "#5E81AC");
            int background;
            try {
                background = Color.parseColor(classColor);
            } catch (Exception error) {
                background = ACCENT;
            }
            double luminance = 0.299 * Color.red(background)
                    + 0.587 * Color.green(background) + 0.114 * Color.blue(background);
            int classFg = luminance < 140 ? Color.WHITE : TEXT;

            TextView classBadge = text(classText, 24, classFg, true);
            classBadge.setGravity(Gravity.CENTER);
            classBadge.setPadding(dp(14), dp(8), dp(14), dp(8));
            classBadge.setBackground(rounded(background, 0, 8, 0));
            LinearLayout.LayoutParams badgeParams = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            badgeParams.bottomMargin = dp(8);
            main.addView(classBadge, badgeParams);

            JSONArray items = obj.optJSONArray("class_items");
            if (items == null || items.length() == 0) {
                main.addView(text("该页面未列出难度分项", 12, SUBTEXT, false));
            } else {
                for (int i = 0; i < items.length(); i++) {
                    TextView item = text("· " + items.optString(i), 13, TEXT, false);
                    item.setPadding(0, dp(2), 0, 0);
                    main.addView(item);
                }
            }
            content.addView(main);

            JSONArray tags = obj.optJSONArray("tags");
            if (tags != null && tags.length() > 0) {
                LinearLayout tagsCard = card();
                addSectionTitle(tagsCard, "标签");
                StringBuilder tagText = new StringBuilder();
                for (int i = 0; i < tags.length(); i++) {
                    if (i > 0) {
                        tagText.append("  ·  ");
                    }
                    tagText.append(tags.optString(i));
                }
                TextView tagsView = text(tagText.toString(), 12, TEXT, false);
                tagsView.setLineSpacing(dp(2), 1.1f);
                tagsView.setBackground(rounded(Color.parseColor("#F4EDE0"), 0, 6, 0));
                tagsView.setPadding(dp(9), dp(8), dp(9), dp(8));
                tagsCard.addView(tagsView);
                content.addView(tagsCard);
            }

            String summary = obj.optString("summary", "");
            LinearLayout summaryCard = card();
            addSectionTitle(summaryCard, "简介");
            TextView summaryView = text(
                    summary.isEmpty() ? "暂无简介" : summary,
                    13, TEXT, false
            );
            summaryView.setLineSpacing(dp(2), 1.18f);
            summaryView.setTextIsSelectable(true);
            summaryCard.addView(summaryView);
            content.addView(summaryCard);

            LinearLayout linkCard = card();
            addSectionTitle(linkCard, "原文链接");
            TextView linkView = text(currentUrl, 10, ACCENT_DARK, false);
            linkView.setTextIsSelectable(true);
            linkCard.addView(linkView);
            content.addView(linkCard);

            openButton.setEnabled(!currentUrl.isEmpty());
            statusView.setText(obj.optBoolean("cached", false)
                    ? "已加载（本地缓存）" : "已加载（在线）");
            scroll.post(() -> scroll.scrollTo(0, 0));
        } catch (Exception error) {
            renderError(String.valueOf(error));
        }
    }

    private void renderError(String message) {
        content.removeAllViews();
        LinearLayout card = card();
        TextView title = text("没有拿到数据", 18, ERROR, true);
        card.addView(title);
        TextView detail = text(message, 12, SUBTEXT, false);
        detail.setPadding(0, dp(6), 0, 0);
        detail.setTextIsSelectable(true);
        card.addView(detail);
        content.addView(card);
        openButton.setEnabled(false);
        statusView.setText("加载失败");
    }

    private void refresh() {
        if (slug.isEmpty() && query.isEmpty()) {
            statusView.setText("没有可刷新的页面");
            return;
        }
        setBusy(true);
        statusView.setText("正在刷新…");
        executor.execute(() -> {
            try {
                String json;
                if (!slug.isEmpty()) {
                    json = Python.getInstance().getModule("mobile")
                            .callAttr("fetch_slug", source, slug, title, true).toString();
                } else {
                    json = Python.getInstance().getModule("mobile")
                            .callAttr("fetch", source, query, true).toString();
                }
                String result = json;
                mainHandler.post(() -> {
                    setBusy(false);
                    render(result);
                    statusView.setText("已刷新");
                });
            } catch (Throwable error) {
                String message = error.getMessage() == null
                        ? error.toString() : error.getMessage();
                mainHandler.post(() -> {
                    setBusy(false);
                    statusView.setText("刷新失败：" + message);
                });
            }
        });
    }

    private void setBusy(boolean busy) {
        refreshButton.setEnabled(!busy);
        openButton.setEnabled(!busy && !currentUrl.isEmpty());
    }

    @Override
    public void onBackPressed() {
        finish();
    }
}
