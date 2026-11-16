package com.xiaomu.backrooms;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
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
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** 设置页：缓存管理 + 关于入口。 */
public class SettingsActivity extends Activity {

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int BORDER = Color.parseColor("#E5DCC8");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private TextView cacheStatsView;
    private Button clearButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(PAPER);
        getWindow().setNavigationBarColor(PAPER);
        getWindow().getDecorView().setSystemUiVisibility(
                android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        buildUi();

        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
                Python.getInstance().getModule("mobile")
                        .callAttr("init", getFilesDir().getAbsolutePath(), "");
            }
        } catch (Throwable error) {
            cacheStatsView.setText("Python 未初始化：" + error.getMessage());
            return;
        }
        refreshStats();
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
        button.setPadding(dp(12), 0, dp(12), 0);
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

        LinearLayout cacheCard = new LinearLayout(this);
        cacheCard.setOrientation(LinearLayout.VERTICAL);
        cacheCard.setBackground(rounded(PANEL, BORDER, 12, 1));
        cacheCard.setPadding(dp(16), dp(15), dp(16), dp(15));
        LinearLayout.LayoutParams cacheParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cacheParams.bottomMargin = dp(12);
        content.addView(cacheCard, cacheParams);

        cacheCard.addView(text("缓存", 16, INK, true));
        TextView cacheDesc = text(
                "缓存永久保留，不会自动过期或删除。只有手动清理，或点击刷新按钮时才更新。",
                12, MUTED, false
        );
        cacheDesc.setLineSpacing(dp(2), 1.1f);
        cacheDesc.setPadding(0, dp(5), 0, dp(10));
        cacheCard.addView(cacheDesc);

        cacheStatsView = text("正在读取缓存…", 13, INK, true);
        cacheCard.addView(cacheStatsView);

        clearButton = button("清理缓存", true);
        LinearLayout.LayoutParams clearParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        clearParams.topMargin = dp(10);
        cacheCard.addView(clearButton, clearParams);
        clearButton.setOnClickListener(v -> confirmClear());

        LinearLayout aboutCard = new LinearLayout(this);
        aboutCard.setOrientation(LinearLayout.HORIZONTAL);
        aboutCard.setGravity(Gravity.CENTER_VERTICAL);
        aboutCard.setBackground(rounded(PANEL, BORDER, 12, 1));
        aboutCard.setPadding(dp(16), dp(14), dp(14), dp(14));
        aboutCard.setClickable(true);
        aboutCard.setOnClickListener(v ->
                startActivity(new Intent(SettingsActivity.this, AboutActivity.class)));
        content.addView(aboutCard);

        LinearLayout aboutText = new LinearLayout(this);
        aboutText.setOrientation(LinearLayout.VERTICAL);
        aboutCard.addView(aboutText, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        aboutText.addView(text("关于", 15, INK, true));
        aboutText.addView(text("版本、许可证与 GitHub 仓库", 11, MUTED, false));

        TextView chevron = text("›", 24, MUTED, false);
        chevron.setGravity(Gravity.CENTER);
        aboutCard.addView(chevron);

        LinearLayout bottom = new LinearLayout(this);
        bottom.setBackgroundColor(PANEL);
        bottom.setPadding(dp(16), dp(10), dp(16), dp(10));
        root.addView(bottom);
        Button backButton = button("返回", false);
        backButton.setOnClickListener(v -> finish());
        bottom.addView(backButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
    }

    private void refreshStats() {
        cacheStatsView.setText("正在读取缓存…");
        clearButton.setEnabled(false);
        executor.execute(() -> {
            String json;
            try {
                json = Python.getInstance().getModule("mobile")
                        .callAttr("cache_stats").toString();
            } catch (Throwable error) {
                json = "{\"ok\":false,\"error\":\"" + error.getMessage() + "\"}";
            }
            String result = json;
            mainHandler.post(() -> {
                try {
                    JSONObject object = new JSONObject(result);
                    if (!object.optBoolean("ok", false)) {
                        cacheStatsView.setText("读取失败：" + object.optString("error"));
                    } else {
                        int files = object.optInt("files", 0);
                        long bytes = object.optLong("bytes", 0);
                        cacheStatsView.setText(
                                files + " 个缓存文件 · " + formatBytes(bytes)
                        );
                    }
                } catch (Exception error) {
                    cacheStatsView.setText("读取失败：" + error.getMessage());
                }
                clearButton.setEnabled(true);
            });
        });
    }

    private void confirmClear() {
        new AlertDialog.Builder(this)
                .setTitle("清理缓存")
                .setMessage("清理后，下次查询需要重新从站点下载。确定清理吗？")
                .setPositiveButton("清理", (dialog, which) -> clearCache())
                .setNegativeButton("取消", null)
                .show();
    }

    private void clearCache() {
        clearButton.setEnabled(false);
        cacheStatsView.setText("正在清理…");
        executor.execute(() -> {
            String json;
            try {
                json = Python.getInstance().getModule("mobile")
                        .callAttr("clear_cache").toString();
            } catch (Throwable error) {
                json = "{\"ok\":false,\"error\":\"" + error.getMessage() + "\"}";
            }
            String result = json;
            mainHandler.post(() -> {
                try {
                    JSONObject object = new JSONObject(result);
                    if (!object.optBoolean("ok", false)) {
                        Toast.makeText(this, "清理失败：" + object.optString("error"),
                                Toast.LENGTH_LONG).show();
                    } else {
                        Toast.makeText(this, "缓存已清理", Toast.LENGTH_SHORT).show();
                    }
                } catch (Exception error) {
                    Toast.makeText(this, "清理失败：" + error.getMessage(),
                            Toast.LENGTH_LONG).show();
                }
                refreshStats();
            });
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
}
