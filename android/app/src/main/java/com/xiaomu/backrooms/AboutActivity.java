package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** 关于页：图标、简介、版本、许可证与 GitHub 仓库。 */
public class AboutActivity extends Activity {

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int BORDER = Color.parseColor("#E5DCC8");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");
    private static final int ACCENT_DARK = Color.parseColor("#8A6A1F");
    private static final String GITHUB_URL = "https://github.com/xiaomu4326/TheBackrooms";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(PAPER);
        getWindow().setNavigationBarColor(PAPER);
        getWindow().getDecorView().setSystemUiVisibility(
                android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        buildUi();
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

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAPER);
        setContentView(root);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setBackgroundColor(PAPER);
        header.setPadding(dp(10), 0, dp(14), 0);
        root.addView(header, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        TextView back = text("‹", 32, INK, false);
        back.setGravity(Gravity.CENTER);
        back.setPadding(dp(6), 0, dp(12), dp(3));
        back.setOnClickListener(v -> finish());
        header.addView(back, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48)));

        TextView title = text("关于", 17, INK, true);
        title.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(title, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        android.view.View divider = new android.view.View(this);
        divider.setBackgroundColor(BORDER);
        root.addView(divider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(18), dp(18), dp(18), dp(18));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(rounded(PANEL, BORDER, 12, 1));
        card.setPadding(dp(18), dp(18), dp(18), dp(18));
        content.addView(card, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.about_icon);
        icon.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        LinearLayout.LayoutParams iconParams = new LinearLayout.LayoutParams(dp(136), dp(136));
        iconParams.gravity = Gravity.CENTER_HORIZONTAL;
        card.addView(icon, iconParams);

        TextView appName = text("后室层级档案", 20, INK, true);
        appName.setGravity(Gravity.CENTER);
        appName.setPadding(0, dp(8), 0, dp(2));
        card.addView(appName);

        TextView version = text("v" + BuildConfig.VERSION_NAME, 11, MUTED, false);
        version.setGravity(Gravity.CENTER);
        card.addView(version);

        TextView desc = text(
                "把后室中文维基的层级档案收进一个查询器：支持 Wikidot / Fandom、"
                        + "层级分组、子层级展开、生存难度与独立详情页。",
                13, INK, false
        );
        desc.setLineSpacing(dp(3), 1.15f);
        desc.setPadding(0, dp(14), 0, dp(12));
        card.addView(desc);

        LinearLayout info = new LinearLayout(this);
        info.setOrientation(LinearLayout.VERTICAL);
        info.setBackground(rounded(Color.parseColor("#F4EDE0"), 0, 8, 0));
        info.setPadding(dp(12), dp(10), dp(12), dp(10));
        card.addView(info);

        addInfoRow(info, "版本", BuildConfig.VERSION_NAME);
        addInfoRow(info, "许可证", "代码 MIT · 维基内容 CC BY-SA 3.0");
        addInfoRow(info, "数据源", "Wikidot / Fandom");

        TextView githubLabel = text("GitHub 仓库", 11, MUTED, true);
        githubLabel.setPadding(0, dp(14), 0, dp(4));
        card.addView(githubLabel);

        TextView github = text(GITHUB_URL, 12, ACCENT_DARK, false);
        github.setPaintFlags(github.getPaintFlags() | Paint.UNDERLINE_TEXT_FLAG);
        github.setTextIsSelectable(true);
        github.setOnClickListener(v -> {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(GITHUB_URL)));
            } catch (Exception ignored) {
            }
        });
        card.addView(github);

        TextView note = text(
                "维基文本版权归后室中文维基 / Fandom 及作者所有，遵循 CC BY-SA 3.0。",
                10, MUTED, false
        );
        note.setLineSpacing(dp(2), 1.1f);
        note.setPadding(0, dp(14), 0, 0);
        card.addView(note);

        LinearLayout bottom = new LinearLayout(this);
        bottom.setBackgroundColor(PANEL);
        bottom.setPadding(dp(18), dp(10), dp(18), dp(10));
        root.addView(bottom);

        Button backButton = new Button(this);
        backButton.setText("返回");
        backButton.setAllCaps(false);
        backButton.setTextSize(13);
        backButton.setTypeface(Typeface.DEFAULT_BOLD);
        backButton.setGravity(Gravity.CENTER);
        backButton.setIncludeFontPadding(false);
        backButton.setMinHeight(0);
        backButton.setMinimumHeight(0);
        backButton.setPadding(dp(12), 0, dp(12), 0);
        backButton.setElevation(0);
        backButton.setStateListAnimator(null);
        backButton.setBackground(rounded(PANEL, Color.parseColor("#D8C9AE"), 10, 1));
        backButton.setTextColor(INK);
        backButton.setOnClickListener(v -> finish());
        bottom.addView(backButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
    }

    private void addInfoRow(LinearLayout parent, String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(3), 0, dp(3));

        TextView labelView = text(label, 11, MUTED, false);
        row.addView(labelView, new LinearLayout.LayoutParams(
                dp(74), ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView valueView = text(value, 12, INK, false);
        valueView.setLineSpacing(dp(2), 1.1f);
        row.addView(valueView, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        parent.addView(row);
    }
}
