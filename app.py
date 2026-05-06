import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import calendar
import time

# ==================== 頁面設定 ====================
st.set_page_config(
    page_title="中二區區督導巡店系統",
    page_icon="🏪",
    layout="wide"
)

# ==================== Supabase 連線 ====================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()


# ==================== 自訂樣式 ====================
st.markdown("""
<style>
/* 放大 Tab 標籤字體 */
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 1.4rem !important;
    font-weight: bold !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 30px;
}
.stTabs [data-baseweb="tab"] {
    height: 60px;
    padding: 0 25px;
}
/* 放大主標題 */
h1 {
    font-size: 2.5rem !important;
}
/* 放大子標題 */
h2, h3 {
    font-size: 1.6rem !important;
}
/* 放大一般文字 */
.stMarkdown, .stSelectbox label, .stRadio label, .stDateInput label, .stTextInput label {
    font-size: 1.1rem !important;
}
/* 放大按鈕 */
.stButton button {
    font-size: 1.2rem !important;
    height: 50px;
}
/* 行動裝置適配 */
@media (max-width: 768px) {
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem !important;
    }
    h1 {
        font-size: 1.8rem !important;
    }
}
</style>
""", unsafe_allow_html=True)
# ==================== 店家清單（完整版）====================
STORES = {
    # 中區（光田/童綜合/清泉系列）
    "L07": "梧棲童綜合院內店",
    "L08": "向上光田一店",
    "L22": "大甲光田店",
    "L47": "沙鹿光田店",
    "L50": "清泉店",
    "L80": "梧棲童綜合店",
    # 彰化區
    "N05": "彰基二林店",
    "N06": "部立彰化店",
    "N08": "員榮院外店",
    "N09": "鹿基院外店",
    "N10": "員基院外店",
    "N15": "彰基中華店",
    "N33": "秀傳店",
    # 雲林區
    "P01": "若瑟便利店",
    "P03": "台大斗六院外店",
    "P05": "慈濟斗六院外店",
    "P13": "若瑟店",
    # 藥局
    "R68": "彰基藥局",
}

# ==================== 美化 CSS ====================
st.markdown("""
<style>
/* 月曆美化 */
.calendar-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.cal-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 6px;
    table-layout: fixed;
}
.cal-header {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    font-weight: 700;
    text-align: center;
    padding: 12px 0;
    border-radius: 8px;
    font-size: 15px;
    letter-spacing: 1px;
}
.cal-header.weekend {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}
.cal-cell {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px;
    height: 110px;
    vertical-align: top;
    transition: all 0.2s;
}
.cal-cell:hover {
    border-color: #6366f1;
    box-shadow: 0 0 12px rgba(99,102,241,0.4);
}
.cal-cell.weekend {
    background: #292524;
}
.cal-cell.today {
    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
    border: 2px solid #3b82f6;
    box-shadow: 0 0 18px rgba(59,130,246,0.5);
}
.cal-cell.empty {
    background: transparent;
    border: 1px dashed #374151;
}
.day-num {
    font-size: 18px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.day-num.weekend { color: #fca5a5; }
.day-num.today {
    color: #fbbf24;
    text-shadow: 0 0 10px rgba(251,191,36,0.6);
}
.store-tag {
    display: block;
    font-size: 11px;
    padding: 3px 6px;
    border-radius: 4px;
    margin-top: 3px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.store-done {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
}
.store-plan {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
}

/* 置中提示視窗 */
.center-toast {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 30px 60px;
    border-radius: 16px;
    font-size: 22px;
    font-weight: 700;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    z-index: 9999;
    animation: fadeOut 2s ease-in-out forwards;
}
@keyframes fadeOut {
    0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
    20% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    80% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    100% { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
}
</style>
""", unsafe_allow_html=True)

# ==================== 資料庫操作 ====================
def load_visits():
    try:
        res = supabase.table("visits").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        return pd.DataFrame()

def save_visit(store_code, store_name, visit_date, status, note):
    try:
        data = {
            "store_code": store_code,
            "store_name": store_name,
            "visit_date": str(visit_date),
            "status": status,
            "note": note or "",
        }
        supabase.table("visits").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False

def show_center_toast(message):
    """置中提示視窗（2秒後自動消失）"""
    placeholder = st.empty()
    placeholder.markdown(
        f'<div class="center-toast">✅ {message}</div>',
        unsafe_allow_html=True
    )
    time.sleep(2)
    placeholder.empty()

# ==================== 側邊欄 ====================
with st.sidebar:
    st.markdown("### 📊 本月統計")
    df_all = load_visits()
    today = date.today()

    if not df_all.empty:
        df_all['visit_date'] = pd.to_datetime(df_all['visit_date'])
        df_month = df_all[
            (df_all['visit_date'].dt.year == today.year) &
            (df_all['visit_date'].dt.month == today.month)
        ]
        done = len(df_month[df_month['status'] == '已巡店'])
        plan = len(df_month[df_month['status'] == '計畫'])
        unique_stores = df_month['store_code'].nunique() if len(df_month) else 0
    else:
        done = plan = unique_stores = 0

    c1, c2 = st.columns(2)
    c1.metric("✅ 已巡店", done)
    c2.metric("📋 計畫", plan)
    st.metric("🏬 涵蓋店數", unique_stores)

    st.markdown("---")
    if st.button("🔄 重新整理資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("💡 資料儲存於雲端，所有裝置即時同步")

# ==================== 主畫面 ====================
st.title("🏪 中二區區督導巡店系統（雲端同步版）")

tab1, tab2, tab3, tab4 = st.tabs(["📅 月曆檢視", "➕ 新增紀錄", "🔁 週期排程", "📋 月度計畫"])

# ---------- Tab 1：月曆檢視 ----------
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("年", range(2024, 2031), index=2)
    with col2:
        month = st.selectbox("月", range(1, 13), index=today.month - 1)

    st.markdown(f"### 📅 {year} 年 {month} 月")

    df_v = load_visits()
    visits_map = {}
    if not df_v.empty:
        df_v['visit_date'] = pd.to_datetime(df_v['visit_date'])
        df_m = df_v[(df_v['visit_date'].dt.year == year) & (df_v['visit_date'].dt.month == month)]
        for _, r in df_m.iterrows():
            d = r['visit_date'].day
            visits_map.setdefault(d, []).append((r['store_name'], r['status']))

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]

    html = '<div class="calendar-container"><table class="cal-table"><tr>'
    for i, w in enumerate(weekdays):
        cls = "cal-header weekend" if i >= 5 else "cal-header"
        html += f'<td class="{cls}">{w}</td>'
    html += '</tr>'

    for week in weeks:
        html += '<tr>'
        for i, day in enumerate(week):
            if day == 0:
                html += '<td class="cal-cell empty"></td>'
            else:
                classes = ["cal-cell"]
                num_classes = ["day-num"]
                if i >= 5:
                    classes.append("weekend")
                    num_classes.append("weekend")
                if day == today.day and month == today.month and year == today.year:
                    classes.append("today")
                    num_classes.append("today")

                cell = f'<td class="{" ".join(classes)}">'
                cell += f'<div class="{" ".join(num_classes)}">{day}</div>'

                if day in visits_map:
                    for sname, status in visits_map[day][:3]:
                        css = "store-done" if status == "已巡店" else "store-plan"
                        icon = "✅" if status == "已巡店" else "📋"
                        cell += f'<span class="store-tag {css}">{icon} {sname}</span>'
                    if len(visits_map[day]) > 3:
                        cell += f'<span class="store-tag" style="background:#475569;color:white;">+{len(visits_map[day])-3}</span>'

                cell += '</td>'
                html += cell
        html += '</tr>'
    html += '</table></div>'

    st.markdown(html, unsafe_allow_html=True)

    # 圖例
    st.markdown("""
    <div style="margin-top:20px; display:flex; gap:20px; justify-content:center;">
        <span style="padding:6px 14px; background:linear-gradient(135deg,#10b981,#059669); color:white; border-radius:6px; font-weight:600;">✅ 已巡店</span>
        <span style="padding:6px 14px; background:linear-gradient(135deg,#f59e0b,#d97706); color:white; border-radius:6px; font-weight:600;">📋 計畫</span>
        <span style="padding:6px 14px; background:linear-gradient(135deg,#1e3a8a,#1e40af); color:white; border-radius:6px; font-weight:600; border:2px solid #3b82f6;">📍 今天</span>
    </div>
    """, unsafe_allow_html=True)

# ---------- Tab 2：新增紀錄 ----------
with tab2:
    st.subheader("➕ 新增單筆紀錄")
    col1, col2 = st.columns(2)
    with col1:
        store_options = [f"{c} - {n}" for c, n in STORES.items()]
        sel = st.selectbox("選擇門市 *", store_options)
        sel_code = sel.split(" - ")[0]
        sel_name = STORES[sel_code]
        v_date = st.date_input("日期 *", value=today)
    with col2:
        status = st.radio("狀態 *", ["計畫", "已巡店"], horizontal=True)
        note = st.text_input("備註", placeholder="（可選）")

    if st.button("💾 儲存到雲端", type="primary", use_container_width=True):
        if save_visit(sel_code, sel_name, v_date, status, note):
            show_center_toast("已成功存入雲端！")
            st.cache_data.clear()
            st.rerun()

# ---------- Tab 3：週期排程 ----------
with tab3:
    st.subheader("🔁 週期排程（批次新增）")
    col1, col2 = st.columns(2)
    with col1:
        store_options = [f"{c} - {n}" for c, n in STORES.items()]
        sel = st.selectbox("門市", store_options, key="cyc_store")
        sel_code = sel.split(" - ")[0]
        start_d = st.date_input("起始日期", value=today, key="cyc_start")
    with col2:
        cycle = st.number_input("週期（天）", min_value=1, max_value=180, value=14)
        times = st.number_input("產生筆數", min_value=1, max_value=50, value=6)

    if st.button("🚀 批次產生計畫", type="primary", use_container_width=True):
        ok = 0
        for i in range(times):
            d = start_d + timedelta(days=cycle * i)
            if save_visit(sel_code, STORES[sel_code], d, "計畫", f"週期{cycle}天"):
                ok += 1
        if ok > 0:
            show_center_toast(f"已新增 {ok} 筆計畫！")
            st.cache_data.clear()
            st.rerun()

# ---------- Tab 4：月度計畫 ----------
with tab4:
    st.subheader("📋 月度計畫總覽")
    df = load_visits()
    if df.empty:
        st.info("目前尚無資料")
    else:
        df['visit_date'] = pd.to_datetime(df['visit_date'])
        col1, col2 = st.columns(2)
        with col1:
            y = st.selectbox("年份", sorted(df['visit_date'].dt.year.unique(), reverse=True), key="t4y")
        with col2:
            m = st.selectbox("月份", range(1, 13), index=today.month - 1, key="t4m")
        df_f = df[(df['visit_date'].dt.year == y) & (df['visit_date'].dt.month == m)].sort_values('visit_date')
        if df_f.empty:
            st.warning(f"{y} 年 {m} 月無資料")
        else:
            df_show = df_f[['visit_date', 'store_code', 'store_name', 'status', 'note']].copy()
            df_show['visit_date'] = df_show['visit_date'].dt.strftime('%Y-%m-%d')
            df_show.columns = ['日期', '店碼', '店名', '狀態', '備註']
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            st.caption(f"共 {len(df_f)} 筆紀錄")
