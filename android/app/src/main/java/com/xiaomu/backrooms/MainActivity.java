package com.xiaomu.backrooms;

import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
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
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

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
    private static final int ROW_SECTION = 1;
    private static final int ROW_ENTRY = 2;

    private static final int PAPER = Color.parseColor("#F4F1E8");
    private static final int PANEL = Color.parseColor("#FBF8F0");
    private static final int INK = Color.parseColor("#211E1A");
    private static final int MUTED = Color.parseColor("#857D6F");
    private static final int ACCENT = Color.parseColor("#C6952D");
    private static final int ACCENT_DARK = Color.parseColor("#8A6A1F");
    private static final int GROUP_BG = Color.parseColor("#F7F1E1");
    private static final int SELECTED_BG = Color.parseColor("#E8D8B0");

    private final ExecutorService indexExecutor = Executors.newSingleThreadExecutor();
    private final ExecutorService detailExecutor = Executors.newCachedThreadPool();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Random random = new Random();

    private LinearLayout listPanel;
    private ListView listView;
    private EditText queryInput;
    private EditText filterInput;
    private Spinner sourceSpinner;
    private Button queryButton;
    private Button randomButton;
    private Button refreshIndexButton;
    private Button settingsButton;
    private Button listToggleButton;
    private TextView listStatusView;
    private TextView statusView;

    private final List<GroupNode> groups = new ArrayList<>();
    private final List<Entry> allEntries = new ArrayList<>();
    private final List<Row> rows = new ArrayList<>();
    private final Set<String> expandedGroups = new HashSet<>();
    private final Set<String> expandedParents = new HashSet<>();
    private final Set<String> expandedSections = new HashSet<>();

    private RowAdapter adapter;
    private String selectedSlug = "";
    private String lastQuery = "";
    private String lastEntrySlug = "";
    private String lastEntryTitle = "";
    private String lastSource = "wikidot";
    private int indexGeneration = 0;
    private int detailGeneration = 0;
    private boolean indexLoading = false;

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

    private Button makeButton(String text, boolean primary) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextSize(13);
        button.setTypeface(Typeface.DEFAULT_BOLD);
        button.setGravity(android.view.Gravity.CENTER);
        button.setIncludeFontPadding(false);
        button.setMinHeight(dp(44));
        button.setMinimumHeight(dp(44));
        button.setPadding(dp(14), 0, dp(14), 0);
        button.setElevation(0);
        button.setStateListAnimator(null);
        button.setBackground(buttonBackground(primary));
        button.setTextColor(new ColorStateList(
                new int[][]{
                        new int[]{-android.R.attr.state_enabled},
                        new int[]{}
                },
                new int[]{
                        Color.parseColor("#9A9284"),
                        INK
                }
        ));
        return button;
    }

    private GradientDrawable roundedFill(int color, int strokeColor) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setShape(GradientDrawable.RECTANGLE);
        drawable.setCornerRadius(dp(10));
        drawable.setColor(color);
        if (strokeColor != 0) {
            drawable.setStroke(dp(1), strokeColor);
        }
        return drawable;
    }

    private StateListDrawable buttonBackground(boolean primary) {
        int normal = primary ? ACCENT : Color.parseColor("#EFE7D6");
        int pressed = primary ? Color.parseColor("#B5841F") : Color.parseColor("#E0D2B8");
        int disabled = Color.parseColor("#DED8CB");
        int stroke = primary ? 0 : Color.parseColor("#D8C9AE");

        StateListDrawable states = new StateListDrawable();
        states.addState(new int[]{-android.R.attr.state_enabled}, roundedFill(disabled, 0));
        states.addState(new int[]{android.R.attr.state_pressed}, roundedFill(pressed, stroke));
        states.addState(new int[]{}, roundedFill(normal, stroke));
        return states;
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
        subtitle.setText("The Backrooms · Wikidot / Fandom · v1.0.3");
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
                0, dp(44), 1f));
        refreshIndexButton = makeButton("刷新列表", false);
        LinearLayout.LayoutParams refreshIndexParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, dp(44));
        refreshIndexParams.leftMargin = dp(6);
        sourceRow.addView(refreshIndexButton, refreshIndexParams);
        settingsButton = makeButton("设置", false);
        LinearLayout.LayoutParams settingsParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, dp(44));
        settingsParams.leftMargin = dp(6);
        sourceRow.addView(settingsButton, settingsParams);
        root.addView(sourceRow);

        queryInput = new EditText(this);
        queryInput.setHint("0 / 0.1 / C-156 / Level ZH 38");
        queryInput.setText("0");
        queryInput.setSingleLine(true);
        queryInput.setTextSize(13);
        root.addView(queryInput, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(44)));

        LinearLayout queryRow = new LinearLayout(this);
        queryRow.setOrientation(LinearLayout.HORIZONTAL);
        queryRow.setGravity(android.view.Gravity.CENTER_VERTICAL);
        queryButton = makeButton("查询", true);
        LinearLayout.LayoutParams queryParams = new LinearLayout.LayoutParams(
                0, dp(44), 1f);
        queryParams.rightMargin = dp(4);
        queryRow.addView(queryButton, queryParams);
        randomButton = makeButton("随机", false);
        LinearLayout.LayoutParams randomParams = new LinearLayout.LayoutParams(
                0, dp(44), 1f);
        randomParams.leftMargin = dp(4);
        queryRow.addView(randomButton, randomParams);
        root.addView(queryRow);

        LinearLayout filterRow = new LinearLayout(this);
        filterRow.setOrientation(LinearLayout.HORIZONTAL);
        filterRow.setGravity(android.view.Gravity.CENTER_VERTICAL);
        filterInput = new EditText(this);
        filterInput.setHint("筛选编号 / 名称");
        filterInput.setSingleLine(true);
        filterInput.setTextSize(12);
        filterRow.addView(filterInput, new LinearLayout.LayoutParams(
                0, dp(44), 1f));
        listToggleButton = makeButton("收起列表", false);
        LinearLayout.LayoutParams toggleParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, dp(44));
        toggleParams.leftMargin = dp(6);
        filterRow.addView(listToggleButton, toggleParams);
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

        statusView = new TextView(this);
        statusView.setTextSize(10);
        statusView.setTextColor(MUTED);
        statusView.setPadding(dp(2), dp(4), dp(2), dp(2));
        root.addView(statusView);

        adapter = new RowAdapter();
        listView.setAdapter(adapter);
        listView.setOnItemClickListener((parent, view, position, id) -> onRowClick(position));
        listView.setOnItemLongClickListener((parent, view, position, id) -> {
            if (position < 0 || position >= rows.size()) {
                return false;
            }
            Row row = rows.get(position);
            if (row.type != ROW_ENTRY) {
                return false;
            }
            hideKeyboard();
            loadEntry(row.entry, false);
            return true;
        });

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
        settingsButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, SettingsActivity.class);
            intent.putExtra("source", currentSource());
            startActivity(intent);
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

        statusView.setText("索引加载后，点层级打开详情页。");
        listStatusView.setText("索引加载中…");
    }

    private void toggleList() {
        boolean visible = listPanel.getVisibility() == View.VISIBLE;
        listPanel.setVisibility(visible ? View.GONE : View.VISIBLE);
        listToggleButton.setText(visible ? "显示列表" : "收起列表");
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
        expandedSections.clear();
        selectedSlug = "";
        lastEntrySlug = "";
        lastEntryTitle = "";
        lastQuery = "";
        filterInput.setText("");
        adapter.notifyDataSetChanged();
        statusView.setText("正在加载索引…");
        listStatusView.setText("索引加载中…");
    }

    private void loadIndex(boolean force) {
        final int generation = ++indexGeneration;
        final String source = currentSource();
        indexLoading = true;
        refreshIndexButton.setEnabled(false);
        listStatusView.setText(force ? "正在刷新索引…" : "索引加载中…");
        indexExecutor.execute(() -> {
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

                    JSONArray sectionArray = groupObj.optJSONArray("sections");
                    if (sectionArray != null && sectionArray.length() > 0) {
                        for (int j = 0; j < sectionArray.length(); j++) {
                            JSONObject sectionObj = sectionArray.optJSONObject(j);
                            if (sectionObj == null) {
                                continue;
                            }
                            SectionNode section = new SectionNode();
                            section.key = sectionObj.optString("key");
                            section.label = sectionObj.optString("label", section.key);
                            section.count = sectionObj.optInt("count", 0);
                            parseMains(sectionObj.optJSONArray("mains"), section.mains);
                            if (!section.mains.isEmpty()) {
                                group.sections.add(section);
                            }
                        }
                    } else {
                        parseMains(groupObj.optJSONArray("mains"), group.mains);
                    }

                    if (!group.mains.isEmpty() || !group.sections.isEmpty()) {
                        groups.add(group);
                    }
                }
            }
            rebuildRows();
            if (groups.isEmpty()) {
                rows.clear();
                adapter.notifyDataSetChanged();
                listStatusView.setText("索引为空，点「刷新列表」重试");
                statusView.setText("索引为空；可直接输入编号查询，或点「刷新列表」重试。");
                return;
            }
            int total = obj.optInt("total", allEntries.size());
            listStatusView.setText("索引 " + total + " 条 · " + groups.size() + " 个分组");
            statusView.setText("点层级打开详情页；带 ▸ 的上级先展开，长按可看该上级详情。");
        } catch (Exception error) {
            listStatusView.setText("索引解析失败");
            statusView.setText(String.valueOf(error));
        }
    }

    private void parseMains(JSONArray mainArray, List<MainNode> target) {
        if (mainArray == null) {
            return;
        }
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
            target.add(main);
            allEntries.add(main.entry);
            allEntries.addAll(main.children);
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
                if (!group.sections.isEmpty()) {
                    for (SectionNode section : group.sections) {
                        Row sectionRow = new Row();
                        sectionRow.type = ROW_SECTION;
                        sectionRow.group = group;
                        sectionRow.section = section;
                        sectionRow.depth = 1;
                        sectionRow.expanded = expandedSections.contains(sectionKey(group, section));
                        rows.add(sectionRow);
                        if (sectionRow.expanded) {
                            addMainRows(section.mains, 2);
                        }
                    }
                } else {
                    addMainRows(group.mains, 1);
                }
            }
        }
        adapter.notifyDataSetChanged();
    }

    private String sectionKey(GroupNode group, SectionNode section) {
        return group.key + "/" + section.key;
    }

    private void addMainRows(List<MainNode> mains, int parentDepth) {
        for (MainNode main : mains) {
            boolean expanded = expandedParents.contains(main.entry.slug);
            rows.add(entryRow(main.entry, parentDepth, main.children.size(), expanded));
            if (expanded) {
                for (Entry child : main.children) {
                    rows.add(entryRow(child, parentDepth + 1, 0, false));
                }
            }
        }
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
        if (row.type == ROW_SECTION) {
            String key = sectionKey(row.group, row.section);
            if (!expandedSections.add(key)) {
                expandedSections.remove(key);
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
            return;
        }
        adapter.notifyDataSetChanged();
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
            if (!group.sections.isEmpty()) {
                for (SectionNode section : group.sections) {
                    for (MainNode main : section.mains) {
                        if (main.entry.slug.equals(slug)) {
                            expandedGroups.add(group.key);
                            expandedSections.add(sectionKey(group, section));
                            rebuildRows();
                            scrollToSlug(slug);
                            return;
                        }
                        for (Entry child : main.children) {
                            if (child.slug.equals(slug)) {
                                expandedGroups.add(group.key);
                                expandedSections.add(sectionKey(group, section));
                                expandedParents.add(main.entry.slug);
                                rebuildRows();
                                scrollToSlug(slug);
                                return;
                            }
                        }
                    }
                }
                continue;
            }
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
        detailExecutor.execute(() -> {
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
        detailExecutor.execute(() -> {
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

    private void setDetailBusy(boolean busy) {
        // 加载中仍允许切换层级/重新查询；旧请求由 detailGeneration 丢弃。
        queryButton.setEnabled(true);
        randomButton.setEnabled(true);
    }

    private void showError(String message) {
        statusView.setText("查询失败：" + message);
        Toast.makeText(this, "查询失败：" + message, Toast.LENGTH_LONG).show();
    }

    private void showDetail(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            if (!obj.optBoolean("ok", false)) {
                showError(obj.optString("error", "未知错误"));
                return;
            }
            statusView.setText(obj.optBoolean("cached", false)
                    ? "已打开详情页（本地缓存）" : "已打开详情页（在线）");
            String pageKey = obj.optString("page_key", "");
            if (!pageKey.isEmpty()) {
                selectBySlug(pageKey);
            }
            openDetailPage(
                    json,
                    pageKey,
                    obj.optString("label", obj.optString("title", "")),
                    lastEntrySlug.isEmpty() ? lastQuery : ""
            );
        } catch (Exception error) {
            showError(String.valueOf(error));
        }
    }

    private void openDetailPage(String json, String slug, String title, String query) {
        Intent intent = new Intent(this, LevelDetailActivity.class);
        intent.putExtra("json", json);
        intent.putExtra("source", currentSource());
        intent.putExtra("slug", slug);
        intent.putExtra("title", title);
        intent.putExtra("query", query);
        intent.putExtra("proxy", proxyUrl());
        startActivity(intent);
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
        final List<SectionNode> sections = new ArrayList<>();
    }

    private static class SectionNode {
        String key = "";
        String label = "";
        int count = 0;
        final List<MainNode> mains = new ArrayList<>();
    }

    private static class Row {
        int type;
        GroupNode group;
        SectionNode section;
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
                view.setPadding(dp(8), dp(10), dp(8), dp(10));
            } else if (row.type == ROW_SECTION) {
                String arrow = row.expanded ? "▾ " : "▸ ";
                view.setText(arrow + row.section.label + "（" + row.section.count + "）");
                view.setTextSize(12);
                view.setTypeface(Typeface.DEFAULT_BOLD);
                view.setTextColor(Color.parseColor("#6F5B2C"));
                view.setBackgroundColor(Color.parseColor("#FAF4E4"));
                view.setPadding(dp(10 + row.depth * 15), dp(9), dp(8), dp(9));
            } else {
                String prefix = "";
                if (row.childCount > 0) {
                    prefix = row.expanded ? "▾ " : "▸ ";
                }
                view.setText(prefix + row.entry.title);
                view.setTextSize(13);
                view.setTypeface(Typeface.DEFAULT);
                view.setTextColor(INK);
                view.setBackgroundColor(row.entry.slug.equals(selectedSlug) ? SELECTED_BG : PAPER);
                view.setPadding(dp(10 + row.depth * 15), dp(10), dp(8), dp(10));
            }
            return view;
        }
    }
}
