package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.widget.AbsListView;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private static final int ROW_GROUP = 0;
    private static final int ROW_ENTRY = 1;

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");
    private static final int ACCENT_DARK = Color.parseColor("#8A6A1F");
    private static final int GROUP_BG = Color.parseColor("#F7F1E1");
    private static final int SELECTED_BG = Color.parseColor("#E8D8B0");

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Random random = new Random();

    private LinearLayout listPanel;
    private LinearLayout detailPanel;
    private LinearLayout detailContainer;
    private ListView listView;
    private EditText queryInput;
    private EditText filterInput;
    private Spinner sourceSpinner;
    private Button queryButton;
    private Button randomButton;
    private Button refreshIndexButton;
    private Button openButton;
    private Button refreshButton;
    private Button listToggleButton;
    private TextView listStatusView;
    private TextView statusView;
    private ScrollView detailScroll;

    private final List<GroupNode> groups = new ArrayList<>();
    private final List<Entry> allEntries = new ArrayList<>();
    private final List<Row> rows = new ArrayList<>();
    private final Set<String> expandedGroups = new HashSet<>();
    private final Set<String> expandedParents = new HashSet<>();

    private RowAdapter adapter;
    private String selectedSlug = "";
    private String currentUrl = "";
    private String lastQuery = "";
    private String lastEntrySlug = "";
    private String lastEntryTitle = "";
    private String lastSource = "wikidot";
    private int indexGeneration = 0;
    private int detailGeneration = 0;
    private boolean indexLoading = false;
    private boolean hasDetail = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();

        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            Python.getInstance().getModule("mobile")
                    .callAttr("init", getFilesDir().getAbsolutePath(), proxyUrl());
        } catch (Throwable error) {
            statusView.setText("Python 初始化失败：" + error);
            return;
        }

        loadIndex(false);
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

    private String currentSource() {
        return sourceSpinner.getSelectedItemPosition() == 0 ? "wikidot" : "fandom";
    }

    private Button makeButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        button.setPadding(dp(10), dp(2), dp(10), dp(2));
        return button;
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAPER);
        root.setPadding(dp(12), dp(10), dp(12), dp(8));
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("后室层级档案");
        title.setTextSize(21);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(INK);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("The Backrooms · Wikidot / Fandom · v1.0.0");
        subtitle.setTextSize(10);
        subtitle.setTextColor(MUTED);
        subtitle.setPadding(0, 0, 0, dp(6));
        root.addView(subtitle);

        LinearLayout sourceRow = new LinearLayout(this);
        sourceRow.setOrientation(LinearLayout.HORIZONTAL);
        sourceRow.setGravity(android.view.Gravity.CENTER_VERTICAL);
        sourceSpinner = new Spinner(this);
        ArrayAdapter<String> sourceAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Wikidot", "Fandom"});
        sourceSpinner.setAdapter(sourceAdapter);
        sourceRow.addView(sourceSpinner, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        refreshIndexButton = makeButton("刷新列表");
        sourceRow.addView(refreshIndexButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        root.addView(sourceRow);

        LinearLayout queryRow = new LinearLayout(this);
        queryRow.setOrientation(LinearLayout.HORIZONTAL);
        queryRow.setGravity(android.view.Gravity.CENTER_VERTICAL);
        queryInput = new EditText(this);
        queryInput.setHint("0 / 0.1 / C-156 / Level ZH 38");
        queryInput.setText("0");
        queryInput.setSingleLine(true);
        queryInput.setTextSize(13);
        queryRow.addView(queryInput, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        queryButton = makeButton("查询");
        queryButton.setBackgroundTintList(ColorStateList.valueOf(ACCENT));
        queryButton.setTextColor(INK);
        queryRow.addView(queryButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        randomButton = makeButton("随机");
        queryRow.addView(randomButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        root.addView(queryRow);

        LinearLayout filterRow = new LinearLayout(this);
        filterRow.setOrientation(LinearLayout.HORIZONTAL);
        filterRow.setGravity(android.view.Gravity.CENTER_VERTICAL);
        filterInput = new EditText(this);
        filterInput.setHint("筛选编号 / 名称");
        filterInput.setSingleLine(true);
        filterInput.setTextSize(12);
        filterRow.addView(filterInput, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        listToggleButton = makeButton("收起列表");
        filterRow.addView(listToggleButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        root.addView(filterRow);

        listPanel = new LinearLayout(this);
        listPanel.setOrientation(LinearLayout.VERTICAL);
        listStatusView = new TextView(this);
        listStatusView.setTextSize(10);
        listStatusView.setTextColor(MUTED);
        listStatusView.setPadding(dp(2), 0, 0, dp(2));
        listPanel.addView(listStatusView);

        listView = new ListView(this);
        listView.setDivider(new ColorDrawable(Color.parseColor("#E5DCC8")));
        listView.setDividerHeight(1);
        listView.setBackgroundColor(PANEL);
        listView.setCacheColorHint(Color.TRANSPARENT);
        listPanel.addView(listView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        root.addView(listPanel, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        detailPanel = new LinearLayout(this);
        detailPanel.setOrientation(LinearLayout.VERTICAL);
        detailScroll = new ScrollView(this);
        detailContainer = new LinearLayout(this);
        detailContainer.setOrientation(LinearLayout.VERTICAL);
        detailContainer.setPadding(dp(4), dp(4), dp(4), dp(4));
        detailScroll.addView(detailContainer);
        detailPanel.addView(detailScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        openButton = makeButton("打开原文");
        openButton.setEnabled(false);
        actionRow.addView(openButton, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        refreshButton = makeButton("刷新");
        actionRow.addView(refreshButton, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        detailPanel.addView(actionRow);

        statusView = new TextView(this);
        statusView.setTextSize(10);
        statusView.setTextColor(MUTED);
        statusView.setPadding(0, dp(2), 0, 0);
        detailPanel.addView(statusView);

        root.addView(detailPanel, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1.25f));

        adapter = new RowAdapter();
        listView.setAdapter(adapter);
        listView.setOnItemClickListener((parent, view, position, id) -> onRowClick(position));

        filterInput.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                rebuildRows();
            }
        });

        queryButton.setOnClickListener(v -> doQuery(false));
        refreshIndexButton.setOnClickListener(v -> loadIndex(true));
        randomButton.setOnClickListener(v -> openRandom());
        refreshButton.setOnClickListener(v -> refreshDetail());
        openButton.setOnClickListener(v -> {
            if (!currentUrl.isEmpty()) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(currentUrl)));
            }
        });
        listToggleButton.setOnClickListener(v -> toggleList());

        sourceSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                String source = currentSource();
                if (source.equals(lastSource)) {
                    return;
                }
                lastSource = source;
                resetForSource();
                loadIndex(false);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        renderPlaceholder("索引加载后，点左侧层级或输入编号查询。");
        listStatusView.setText("索引加载中…");
    }

    private void toggleList() {
        boolean visible = listPanel.getVisibility() == View.VISIBLE;
        listPanel.setVisibility(visible ? View.GONE : View.VISIBLE);
        listToggleButton.setText(visible ? "显示列表" : "收起列表");
        LinearLayout.LayoutParams params = (LinearLayout.LayoutParams) detailPanel.getLayoutParams();
        params.weight = visible ? 1.9f : 1.25f;
        detailPanel.setLayoutParams(params);
    }

    private void hideKeyboard() {
        View view = getCurrentFocus();
        if (view != null) {
            InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (manager != null) {
                manager.hideSoftInputFromWindow(view.getWindowToken(), 0);
            }
            view.clearFocus();
        }
    }

    private void resetForSource() {
        indexGeneration++;
        detailGeneration++;
        groups.clear();
        allEntries.clear();
        rows.clear();
        expandedGroups.clear();
        expandedParents.clear();
        selectedSlug = "";
        currentUrl = "";
        lastEntrySlug = "";
        lastEntryTitle = "";
        lastQuery = "";
        filterInput.setText("");
        hasDetail = false;
        openButton.setEnabled(false);
        adapter.notifyDataSetChanged();
        renderPlaceholder("正在加载索引…");
        statusView.setText("");
        listStatusView.setText("索引加载中…");
    }

    private void loadIndex(boolean force) {
        final int generation = ++indexGeneration;
        final String source = currentSource();
        indexLoading = true;
        refreshIndexButton.setEnabled(false);
        listStatusView.setText(force ? "正在刷新索引…" : "索引加载中…");
        executor.execute(() -> {
            try {
                String json = Python.getInstance().getModule("mobile")
                        .callAttr("index", source, force).toString();
                mainHandler.post(() -> {
                    if (generation != indexGeneration) {
                        return;
                    }
                    indexLoading = false;
                    refreshIndexButton.setEnabled(true);
                    parseIndex(json);
                });
            } catch (Throwable error) {
                mainHandler.post(() -> {
                    if (generation != indexGeneration) {
                        return;
                    }
                    indexLoading = false;
                    refreshIndexButton.setEnabled(true);
                    listStatusView.setText("索引加载失败：" + error);
                    statusView.setText("索引加载失败，可直接输入编号查询。");
                });
            }
        });
    }

    private void parseIndex(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            if (!obj.optBoolean("ok", false)) {
                listStatusView.setText("索引加载失败");
                statusView.setText(obj.optString("error", "未知错误"));
                return;
            }
            groups.clear();
            allEntries.clear();
            JSONArray groupArray = obj.optJSONArray("groups");
            if (groupArray != null) {
                for (int i = 0; i < groupArray.length(); i++) {
                    JSONObject groupObj = groupArray.optJSONObject(i);
                    if (groupObj == null) {
                        continue;
                    }
                    GroupNode group = new GroupNode();
                    group.key = groupObj.optString("key");
                    group.label = groupObj.optString("label", group.key);
                    group.count = groupObj.optInt("count", 0);
                    JSONArray mainArray = groupObj.optJSONArray("mains");
                    if (mainArray != null) {
                        for (int j = 0; j < mainArray.length(); j++) {
                            JSONObject mainObj = mainArray.optJSONObject(j);
                            if (mainObj == null) {
                                continue;
                            }
                            MainNode main = new MainNode();
                            main.entry = parseEntry(mainObj.optJSONObject("entry"));
                            if (main.entry == null) {
                                continue;
                            }
                            JSONArray childArray = mainObj.optJSONArray("children");
                            if (childArray != null) {
                                for (int k = 0; k < childArray.length(); k++) {
                                    Entry child = parseEntry(childArray.optJSONObject(k));
                                    if (child != null) {
                                        main.children.add(child);
                                    }
                                }
                            }
                            group.mains.add(main);
                            allEntries.add(main.entry);
                            allEntries.addAll(main.children);
                        }
                    }
                    if (!group.mains.isEmpty()) {
                        groups.add(group);
                    }
                }
            }
            rebuildRows();
            int total = obj.optInt("total", allEntries.size());
            listStatusView.setText("索引 " + total + " 条 · " + groups.size() + " 个分组");
            if (!hasDetail) {
                renderPlaceholder("点左侧层级，或输入编号查询。");
            }
        } catch (Exception error) {
            listStatusView.setText("索引解析失败");
            statusView.setText(String.valueOf(error));
        }
    }

    private Entry parseEntry(JSONObject obj) {
        if (obj == null) {
            return null;
        }
        Entry entry = new Entry();
        entry.slug = obj.optString("slug");
        entry.title = obj.optString("title", entry.slug);
        JSONArray tags = obj.optJSONArray("tags");
        if (tags != null) {
            for (int i = 0; i < tags.length(); i++) {
                entry.tags.add(tags.optString(i));
            }
        }
        return entry.slug.isEmpty() ? null : entry;
    }

    private void rebuildRows() {
        rows.clear();
        String keyword = filterInput.getText().toString().trim().toLowerCase(Locale.ROOT);
        if (!keyword.isEmpty()) {
            int found = 0;
            for (Entry entry : allEntries) {
                if (found >= 4000) {
                    break;
                }
                if (entry.title.toLowerCase(Locale.ROOT).contains(keyword)
                        || entry.slug.toLowerCase(Locale.ROOT).contains(keyword)
                        || entry.tags.toString().toLowerCase(Locale.ROOT).contains(keyword)) {
                    rows.add(entryRow(entry, 0, 0, false));
                    found++;
                }
            }
            listStatusView.setText("找到 " + found + " 条");
        } else {
            for (GroupNode group : groups) {
                Row groupRow = new Row();
                groupRow.type = ROW_GROUP;
                groupRow.group = group;
                groupRow.expanded = expandedGroups.contains(group.key);
                rows.add(groupRow);
                if (!groupRow.expanded) {
                    continue;
                }
                for (MainNode main : group.mains) {
                    boolean expanded = expandedParents.contains(main.entry.slug);
                    rows.add(entryRow(main.entry, 1, main.children.size(), expanded));
                    if (expanded) {
                        for (Entry child : main.children) {
                            rows.add(entryRow(child, 2, 0, false));
                        }
                    }
                }
            }
        }
        adapter.notifyDataSetChanged();
    }

    private Row entryRow(Entry entry, int depth, int childCount, boolean expanded) {
        Row row = new Row();
        row.type = ROW_ENTRY;
        row.entry = entry;
        row.depth = depth;
        row.childCount = childCount;
        row.expanded = expanded;
        return row;
    }

    private void onRowClick(int position) {
        if (position < 0 || position >= rows.size()) {
            return;
        }
        hideKeyboard();
        Row row = rows.get(position);
        if (row.type == ROW_GROUP) {
            if (!expandedGroups.add(row.group.key)) {
                expandedGroups.remove(row.group.key);
            }
            rebuildRows();
            listView.setSelection(position);
            return;
        }

        selectedSlug = row.entry.slug;
        if (row.childCount > 0) {
            if (!expandedParents.add(row.entry.slug)) {
                expandedParents.remove(row.entry.slug);
            }
            rebuildRows();
            int selected = findRowPosition(row.entry.slug);
            if (selected >= 0) {
                listView.setSelection(selected);
            }
        } else {
            adapter.notifyDataSetChanged();
        }
        loadEntry(row.entry, false);
    }

    private void selectBySlug(String slug) {
        if (slug == null || slug.isEmpty()) {
            return;
        }
        selectedSlug = slug;
        String keyword = filterInput.getText().toString().trim();
        if (!keyword.isEmpty()) {
            adapter.notifyDataSetChanged();
            scrollToSlug(slug);
            return;
        }
        for (GroupNode group : groups) {
            for (MainNode main : group.mains) {
                if (main.entry.slug.equals(slug)) {
                    expandedGroups.add(group.key);
                    rebuildRows();
                    scrollToSlug(slug);
                    return;
                }
                for (Entry child : main.children) {
                    if (child.slug.equals(slug)) {
                        expandedGroups.add(group.key);
                        expandedParents.add(main.entry.slug);
                        rebuildRows();
                        scrollToSlug(slug);
                        return;
                    }
                }
            }
        }
        adapter.notifyDataSetChanged();
    }

    private void scrollToSlug(String slug) {
        int position = findRowPosition(slug);
        if (position >= 0) {
            listView.setSelection(position);
        }
    }

    private int findRowPosition(String slug) {
        for (int i = 0; i < rows.size(); i++) {
            Row row = rows.get(i);
            if (row.type == ROW_ENTRY && row.entry != null && row.entry.slug.equals(slug)) {
                return i;
            }
        }
        return -1;
    }

    private void doQuery(boolean force) {
        String query = queryInput.getText().toString().trim();
        if (query.isEmpty()) {
            statusView.setText("请输入层级编号");
            return;
        }
        final int generation = ++detailGeneration;
        final String source = currentSource();
        lastQuery = query;
        lastEntrySlug = "";
        lastEntryTitle = "";
        hideKeyboard();
        setDetailBusy(true);
        statusView.setText("正在查询「" + query + "」…");
        executor.execute(() -> {
            try {
                String json = Python.getInstance().getModule("mobile")
                        .callAttr("fetch", source, query, force).toString();
                mainHandler.post(() -> {
                    if (generation == detailGeneration) {
                        setDetailBusy(false);
                        showDetail(json);
                    }
                });
            } catch (Throwable error) {
                mainHandler.post(() -> {
                    if (generation == detailGeneration) {
                        setDetailBusy(false);
                        showError(String.valueOf(error));
                    }
                });
            }
        });
    }

    private void loadEntry(Entry entry, boolean force) {
        final int generation = ++detailGeneration;
        final String source = currentSource();
        lastEntrySlug = entry.slug;
        lastEntryTitle = entry.title;
        lastQuery = "";
        queryInput.setText(entry.title);
        setDetailBusy(true);
        statusView.setText("正在打开「" + entry.title + "」…");
        executor.execute(() -> {
            try {
                String json = Python.getInstance().getModule("mobile")
                        .callAttr("fetch_slug", source, entry.slug, entry.title, force).toString();
                mainHandler.post(() -> {
                    if (generation == detailGeneration) {
                        setDetailBusy(false);
                        showDetail(json);
                    }
                });
            } catch (Throwable error) {
                mainHandler.post(() -> {
                    if (generation == detailGeneration) {
                        setDetailBusy(false);
                        showError(String.valueOf(error));
                    }
                });
            }
        });
    }

    private void openRandom() {
        if (allEntries.isEmpty()) {
            statusView.setText("索引还没加载完，稍后再试");
            return;
        }
        Entry entry = allEntries.get(random.nextInt(allEntries.size()));
        queryInput.setText(entry.title);
        selectBySlug(entry.slug);
        loadEntry(entry, false);
    }

    private void refreshDetail() {
        if (!lastEntrySlug.isEmpty()) {
            for (Entry entry : allEntries) {
                if (entry.slug.equals(lastEntrySlug)) {
                    loadEntry(entry, true);
                    return;
                }
            }
            Entry entry = new Entry();
            entry.slug = lastEntrySlug;
            entry.title = lastEntryTitle.isEmpty() ? lastEntrySlug : lastEntryTitle;
            loadEntry(entry, true);
            return;
        }
        if (!lastQuery.isEmpty()) {
            doQuery(true);
            return;
        }
        statusView.setText("还没有可刷新的内容");
    }

    private void setDetailBusy(boolean busy) {
        queryButton.setEnabled(!busy);
        randomButton.setEnabled(!busy);
        refreshButton.setEnabled(!busy);
    }

    private void showError(String message) {
        hasDetail = true;
        detailContainer.removeAllViews();
        TextView view = new TextView(this);
        view.setText("查询失败：\n" + message);
        view.setTextSize(13);
        view.setTextColor(Color.parseColor("#9B2C1F"));
        view.setPadding(dp(4), dp(8), dp(4), dp(8));
        detailContainer.addView(view);
        statusView.setText("没有拿到数据");
        openButton.setEnabled(false);
    }

    private void showDetail(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            if (!obj.optBoolean("ok", false)) {
                showError(obj.optString("error", "未知错误"));
                return;
            }
            currentUrl = obj.optString("url", "");
            renderDetail(obj);
            openButton.setEnabled(!currentUrl.isEmpty());
            statusView.setText(obj.optBoolean("cached", false)
                    ? "已加载（本地缓存）" : "已加载（在线）");
            String pageKey = obj.optString("page_key", "");
            if (!pageKey.isEmpty()) {
                selectBySlug(pageKey);
            }
        } catch (Exception error) {
            showError(String.valueOf(error));
        }
    }

    private void renderDetail(JSONObject obj) {
        hasDetail = true;
        detailContainer.removeAllViews();

        String label = obj.optString("label", "");
        String alias = obj.optString("alias", "");
        String title = label.isEmpty() ? obj.optString("title") : label;
        if (!alias.isEmpty()) {
            title += "  “" + alias + "”";
        }

        TextView titleView = new TextView(this);
        titleView.setText(title);
        titleView.setTextSize(20);
        titleView.setTypeface(Typeface.DEFAULT_BOLD);
        titleView.setTextColor(INK);
        titleView.setPadding(dp(2), dp(2), dp(2), dp(8));
        detailContainer.addView(titleView);

        String code = obj.optString("code", "");
        String revision = obj.optString("revision", "");
        String updatedAt = obj.optString("updated_at", "");
        if (!code.isEmpty() || !revision.isEmpty() || !updatedAt.isEmpty()) {
            StringBuilder metaText = new StringBuilder();
            if (!code.isEmpty()) {
                metaText.append("编号 ").append(code);
            }
            if (!revision.isEmpty()) {
                if (metaText.length() > 0) {
                    metaText.append(" · ");
                }
                metaText.append("页面版本 ").append(revision);
            }
            if (!updatedAt.isEmpty()) {
                if (metaText.length() > 0) {
                    metaText.append(" · ");
                }
                metaText.append("最后编辑 ").append(updatedAt);
            }
            TextView meta = new TextView(this);
            meta.setText(metaText.toString());
            meta.setTextSize(10);
            meta.setTextColor(MUTED);
            meta.setPadding(dp(2), 0, dp(2), dp(6));
            detailContainer.addView(meta);
        }

        LinearLayout classCard = new LinearLayout(this);
        classCard.setOrientation(LinearLayout.VERTICAL);
        int background;
        try {
            background = Color.parseColor(obj.optString("class_color", "#F7E375"));
        } catch (Exception error) {
            background = Color.parseColor("#F7E375");
        }
        classCard.setBackgroundColor(background);
        classCard.setPadding(dp(12), dp(10), dp(12), dp(10));
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cardParams.bottomMargin = dp(8);
        classCard.setLayoutParams(cardParams);

        double luminance = 0.299 * Color.red(background)
                + 0.587 * Color.green(background) + 0.114 * Color.blue(background);
        int classTextColor = luminance < 140 ? Color.WHITE : INK;

        TextView classText = new TextView(this);
        classText.setText("生存难度：" + obj.optString("class_text", "未标注"));
        classText.setTextSize(17);
        classText.setTypeface(Typeface.DEFAULT_BOLD);
        classText.setTextColor(classTextColor);
        classCard.addView(classText);

        JSONArray items = obj.optJSONArray("class_items");
        if (items == null || items.length() == 0) {
            TextView empty = new TextView(this);
            empty.setText("该页面未列出难度分项");
            empty.setTextSize(12);
            empty.setTextColor(classTextColor);
            classCard.addView(empty);
        } else {
            for (int i = 0; i < items.length(); i++) {
                TextView item = new TextView(this);
                item.setText("· " + items.optString(i));
                item.setTextSize(13);
                item.setTextColor(classTextColor);
                item.setPadding(0, dp(2), 0, 0);
                classCard.addView(item);
            }
        }
        detailContainer.addView(classCard);

        JSONArray tags = obj.optJSONArray("tags");
        if (tags != null && tags.length() > 0) {
            TextView tagsView = new TextView(this);
            tagsView.setTextSize(12);
            tagsView.setTextColor(Color.parseColor("#6F675A"));
            StringBuilder builder = new StringBuilder("标签：");
            for (int i = 0; i < tags.length(); i++) {
                if (i > 0) {
                    builder.append(" / ");
                }
                builder.append(tags.optString(i));
            }
            tagsView.setText(builder.toString());
            tagsView.setPadding(dp(2), 0, dp(2), dp(8));
            detailContainer.addView(tagsView);
        }

        String summary = obj.optString("summary", "");
        if (!summary.isEmpty()) {
            TextView summaryTitle = new TextView(this);
            summaryTitle.setText("简介");
            summaryTitle.setTextSize(13);
            summaryTitle.setTypeface(Typeface.DEFAULT_BOLD);
            summaryTitle.setTextColor(MUTED);
            summaryTitle.setPadding(dp(2), dp(2), dp(2), dp(2));
            detailContainer.addView(summaryTitle);

            TextView summaryView = new TextView(this);
            summaryView.setText(summary);
            summaryView.setTextSize(13);
            summaryView.setTextColor(Color.parseColor("#3B362C"));
            summaryView.setLineSpacing(dp(2), 1.15f);
            summaryView.setTextIsSelectable(true);
            summaryView.setPadding(dp(2), 0, dp(2), dp(8));
            detailContainer.addView(summaryView);
        }

        TextView urlView = new TextView(this);
        urlView.setText(currentUrl);
        urlView.setTextSize(10);
        urlView.setTextColor(Color.parseColor("#3A6B8A"));
        urlView.setTextIsSelectable(true);
        urlView.setPadding(dp(2), dp(4), dp(2), dp(4));
        detailContainer.addView(urlView);

        detailScroll.post(() -> detailScroll.scrollTo(0, 0));
    }

    private void renderPlaceholder(String text) {
        hasDetail = false;
        detailContainer.removeAllViews();
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(13);
        view.setTextColor(MUTED);
        view.setPadding(dp(4), dp(12), dp(4), dp(12));
        detailContainer.addView(view);
        openButton.setEnabled(false);
    }

    private static class Entry {
        String slug = "";
        String title = "";
        final List<String> tags = new ArrayList<>();
    }

    private static class MainNode {
        Entry entry;
        final List<Entry> children = new ArrayList<>();
    }

    private static class GroupNode {
        String key = "";
        String label = "";
        int count = 0;
        final List<MainNode> mains = new ArrayList<>();
    }

    private static class Row {
        int type;
        GroupNode group;
        Entry entry;
        int depth;
        int childCount;
        boolean expanded;
    }

    private class RowAdapter extends BaseAdapter {
        @Override
        public int getCount() {
            return rows.size();
        }

        @Override
        public Object getItem(int position) {
            return rows.get(position);
        }

        @Override
        public long getItemId(int position) {
            return position;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            TextView view;
            if (convertView instanceof TextView) {
                view = (TextView) convertView;
            } else {
                view = new TextView(MainActivity.this);
                view.setLayoutParams(new AbsListView.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT));
            }

            Row row = rows.get(position);
            if (row.type == ROW_GROUP) {
                String arrow = row.expanded ? "▾ " : "▸ ";
                view.setText(arrow + row.group.label + "（" + row.group.count + "）");
                view.setTextSize(13);
                view.setTypeface(Typeface.DEFAULT_BOLD);
                view.setTextColor(ACCENT_DARK);
                view.setBackgroundColor(GROUP_BG);
                view.setPadding(dp(8), dp(7), dp(8), dp(7));
            } else {
                String prefix = "";
                if (row.childCount > 0) {
                    prefix = row.expanded ? "▾ " : "▸ ";
                }
                view.setText(prefix + row.entry.title);
                view.setTextSize(12);
                view.setTypeface(Typeface.DEFAULT);
                view.setTextColor(INK);
                view.setBackgroundColor(row.entry.slug.equals(selectedSlug) ? SELECTED_BG : PAPER);
                view.setPadding(dp(10 + row.depth * 15), dp(7), dp(8), dp(7));
            }
            return view;
        }
    }
}
