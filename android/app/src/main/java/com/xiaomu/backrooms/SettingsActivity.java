package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** 设置页：缓存页与关于页入口。 */
public class SettingsActivity extends Activity {

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int BORDER = Color.parseColor("#E5DCC8");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");

    private String source = "wikidot";

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

    private LinearLayout row(String title, String desc, Runnable action) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setBackground(rounded(PANEL, BORDER, 10, 1));
        row.setPadding(dp(16), dp(14), dp(14), dp(14));
        row.setClickable(true);
        row.setOnClickListener(v -> action.run());

        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        row.addView(labels, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        labels.addView(text(title, 15, INK, true));
        TextView sub = text(desc, 11, MUTED, false);
        sub.setPadding(0, dp(3), 0, 0);
        labels.addView(sub);

        TextView chevron = text("›", 24, MUTED, false);
        chevron.setGravity(Gravity.CENTER);
        row.addView(chevron);
        return row;
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

        TextView title = text("设置", 17, INK, true);
        title.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(title, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));

        View divider = new View(this);
        divider.setBackgroundColor(BORDER);
        root.addView(divider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(16), dp(16), dp(16));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout cacheRow = row(
                "缓存",
                "查看已缓存层级、下载全部/指定层级、清理缓存",
                () -> {
                    Intent intent = new Intent(SettingsActivity.this, CacheActivity.class);
                    intent.putExtra("source", source);
                    startActivity(intent);
                }
        );
        LinearLayout.LayoutParams cacheParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cacheParams.bottomMargin = dp(12);
        content.addView(cacheRow, cacheParams);

        content.addView(row(
                "关于",
                "版本、许可证与 GitHub 仓库",
                () -> startActivity(new Intent(SettingsActivity.this, AboutActivity.class))
        ));

        LinearLayout bottom = new LinearLayout(this);
        bottom.setBackgroundColor(PANEL);
        bottom.setPadding(dp(16), dp(10), dp(16), dp(10));
        root.addView(bottom);
        Button backButton = new Button(this);
        backButton.setText("返回");
        backButton.setAllCaps(false);
        backButton.setTextSize(13);
        backButton.setTypeface(Typeface.DEFAULT_BOLD);
        backButton.setTextColor(INK);
        backButton.setBackground(rounded(PANEL, Color.parseColor("#D8C9AE"), 10, 1));
        backButton.setOnClickListener(v -> finish());
        bottom.addView(backButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
    }
}
