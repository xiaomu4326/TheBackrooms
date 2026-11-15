package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private EditText queryInput;
    private TextView resultView;
    private TextView statusView;
    private Spinner sourceSpinner;
    private Button searchButton;
    private Button openButton;

    private String currentUrl = "";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        Python.getInstance().getModule("mobile")
                .callAttr("init", getFilesDir().getAbsolutePath(), proxyUrl());
        statusView.setText("就绪。首次查询需要加载索引，可能稍慢。");
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private String proxyUrl() {
        String extra = getIntent().getStringExtra("proxy");
        if (extra != null && !extra.trim().isEmpty()) {
            return extra.trim();
        }
        try {
            String global = android.provider.Settings.Global.getString(
                    getContentResolver(), android.provider.Settings.Global.HTTP_PROXY);
            if (global != null && !global.isEmpty() && !"null".equals(global)) {
                return global.startsWith("http") ? global : "http://" + global;
            }
        } catch (Exception ignored) {
        }
        String host = System.getProperty("http.proxyHost");
        String port = System.getProperty("http.proxyPort");
        if (host != null && !host.isEmpty() && port != null && !port.isEmpty()) {
            return "http://" + host + ":" + port;
        }
        return "";
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#F4F1E8"));
        root.setPadding(dp(16), dp(14), dp(16), dp(12));
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("后室层级档案");
        title.setTextSize(22);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#211E1A"));
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("The Backrooms · Wikidot / Fandom 层级查询  v1.0.0");
        subtitle.setTextSize(11);
        subtitle.setTextColor(Color.parseColor("#857D6F"));
        subtitle.setPadding(0, dp(2), 0, dp(10));
        root.addView(subtitle);

        sourceSpinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Wikidot", "Fandom"}
        );
        sourceSpinner.setAdapter(adapter);
        root.addView(sourceSpinner, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        queryInput = new EditText(this);
        queryInput.setHint("输入层级编号，如 0 / 0.1 / C-156 / Level ZH 38");
        queryInput.setText("0");
        queryInput.setSingleLine(true);
        root.addView(queryInput);

        searchButton = new Button(this);
        searchButton.setText("查询");
        root.addView(searchButton);

        resultView = new TextView(this);
        resultView.setTextSize(14);
        resultView.setTextColor(Color.parseColor("#3B362C"));
        resultView.setTextIsSelectable(true);
        resultView.setPadding(dp(8), dp(8), dp(8), dp(8));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(resultView);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
        ));

        openButton = new Button(this);
        openButton.setText("在浏览器中打开原文");
        openButton.setEnabled(false);
        root.addView(openButton);

        statusView = new TextView(this);
        statusView.setTextSize(11);
        statusView.setTextColor(Color.parseColor("#857D6F"));
        statusView.setPadding(0, dp(6), 0, 0);
        root.addView(statusView);

        searchButton.setOnClickListener(v -> doSearch());
        openButton.setOnClickListener(v -> {
            if (!currentUrl.isEmpty()) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(currentUrl)));
            }
        });
        sourceSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                resultView.setText("");
                openButton.setEnabled(false);
                currentUrl = "";
                statusView.setText(position == 0
                        ? "数据源：Wikidot"
                        : "数据源：Fandom（部分地区需要代理）");
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
    }

    private void doSearch() {
        String query = queryInput.getText().toString().trim();
        if (query.isEmpty()) {
            statusView.setText("请输入层级编号");
            return;
        }

        String source = sourceSpinner.getSelectedItemPosition() == 0 ? "wikidot" : "fandom";
        searchButton.setEnabled(false);
        openButton.setEnabled(false);
        resultView.setText("");
        statusView.setText("正在查询「" + query + "」…");

        executor.execute(() -> {
            try {
                PyObject module = Python.getInstance().getModule("mobile");
                String json = module.callAttr("fetch", source, query).toString();
                runOnUiThread(() -> showResult(json));
            } catch (Throwable error) {
                String message = error.getMessage() == null
                        ? error.toString() : error.getMessage();
                runOnUiThread(() -> {
                    searchButton.setEnabled(true);
                    statusView.setText("查询失败：" + message);
                });
            }
        });
    }

    private void showResult(String json) {
        searchButton.setEnabled(true);
        try {
            JSONObject obj = new JSONObject(json);
            if (!obj.optBoolean("ok", false)) {
                String error = obj.optString("error", "未知错误");
                if (sourceSpinner.getSelectedItemPosition() == 1) {
                    error += "\n\nFandom 在部分地区无法直连，配置代理后重试。";
                }
                statusView.setText("没有拿到数据");
                resultView.setText(error);
                return;
            }

            currentUrl = obj.optString("url", "");
            StringBuilder sb = new StringBuilder();

            String label = obj.optString("label", "");
            String alias = obj.optString("alias", "");
            sb.append(label.isEmpty() ? obj.optString("title") : label);
            if (!alias.isEmpty()) {
                sb.append("  “").append(alias).append("”");
            }
            sb.append("\n\n");

            sb.append("生存难度：").append(obj.optString("class_text", "未标注")).append("\n");
            JSONArray items = obj.optJSONArray("class_items");
            if (items != null) {
                for (int i = 0; i < items.length(); i++) {
                    sb.append("  · ").append(items.optString(i)).append("\n");
                }
            }

            JSONArray tags = obj.optJSONArray("tags");
            if (tags != null && tags.length() > 0) {
                sb.append("\n标签：");
                for (int i = 0; i < tags.length(); i++) {
                    if (i > 0) {
                        sb.append(" / ");
                    }
                    sb.append(tags.optString(i));
                }
                sb.append("\n");
            }

            String summary = obj.optString("summary", "");
            if (!summary.isEmpty()) {
                sb.append("\n简介：\n").append(summary);
            }

            sb.append("\n\n").append(currentUrl);
            resultView.setText(sb.toString());
            openButton.setEnabled(!currentUrl.isEmpty());
            statusView.setText(obj.optBoolean("cached", false)
                    ? "已加载（本地缓存）" : "已加载（在线）");
        } catch (Exception error) {
            statusView.setText("解析结果失败：" + error.getMessage());
        }
    }
}
