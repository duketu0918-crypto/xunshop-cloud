import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
from supabase import create_client
import uuid
import os

# ============ 頁面設定 ============
st.set_page_config(
    page_title="督導巡店管理系統",
    page_icon="🏪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============ RWD CSS ============
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 100%; }
    
    /* 月曆表格樣式 - 強制橫向7欄 */
    .calendar-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 2px;
        table-layout: fixed;
    }
    .calendar-table th {
        text-align: center;
        padding: 6px 2px;
        font-size: 12px;
        color: #666;
        font-weight: 600;
    }
    .calendar-table td {
        text-align: center;
        padding: 0;
        width: 14.28%;
    }
    .cal-day {
        display: block;
        padding: 8px 2px;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        font-size: 13px;
        text-decoration: none;
        color: #333;
        background: #fff;
        min-height: 36px;
    }
    .cal-day-today {
        background: #ffebee !important;
        border-color: #f44336 !important;
        font-weight: bold;
        color: #d32f2f;
    }
    .cal-day-has {
        background: #e3f2fd !important;
        border-color: #2196f3 !important;
        color: #1565c0;
        font-weight: 600;
    }
    .cal-day-empty {
        background: transparent;
        border: none;
    }
    
    /* 按鈕在手機放大 */
    .stButton button { width: 100%; min-height: 38px; }
    
    /* Tab 字體放大 */
    .stTabs [data-baseweb="tab"] { font-size: 16px; padding: 8px 12px; }
</style>
""", unsafe_allow_html=True)

# ============ Supabase 連線 ============
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ============ 載入門市清單 ============
@st.cache_data(ttl=60)
def load_stores():
    """從 stores.csv 載入，找不到則用預設"""
    try:
        df = pd.read_csv("stores.csv")
        return df
    except Exception:
        # 預設門市（fallback）
        return pd.DataFrame([
            {"code": "L07", "name": "梧棲童綜合院內店"},
            {"code": "L08", "name": "示範門市"},
        ])

stores_df = load_stores()
STORE_OPTIONS = [f"{r['code']} - {r['name']}" for _, r in stores_df.iterrows()]

# ============ 資料庫操作 ============
@st.cache_data(ttl=10)
def load_visits():
    try:
        res = supabase.table("visits").select("*").order("visit_date", desc=True).execute()
        return res.data or []
    except Exception as e:
        st.error(f"載入失敗：{e}")
        return []

def insert_visit(data):
    return supabase.table("visits").insert(data).execute()

def upload_photo(file_bytes, filename):
    """上傳圖片到 store-photos bucket"""
    try:
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        supabase.storage.from_("store-photos").upload(
            unique_name, file_bytes,
            file_options={"content-type": f"image/{ext}"}
        )
        url = supabase.storage.from_("store-photos").get_public_url(unique_name)
        return url
    except Exception as e:
        st.error(f"圖片上傳失敗：{e}")
        return None

# ============ Session State ============
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()
if "view_year" not in st.session_state:
    st.session_state.view_year = date.today().year
if "view_month" not in st.session_state:
    st.session_state.view_month = date.today().month

# ============ 標題 ============
st.markdown("# 🏪 督導巡店管理系統")

# ============ 月份切換 ============
col_prev, col_title, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("◀ 上月", use_container_width=True, key="prev_m"):
        y, m = st.session_state.view_year, st.session_state.view_month
        if m == 1:
            st.session_state.view_year, st.session_state.view_month = y - 1, 12
        else:
            st.session_state.view_month = m - 1
        st.rerun()
with col_title:
    st.markdown(
        f"<h3 style='text-align:center;margin:0;padding:8px 0'>{st.session_state.view_year} 年 {st.session_state.view_month} 月</h3>",
        unsafe_allow_html=True
    )
with col_next:
    if st.button("下月 ▶", use_container_width=True, key="next_m"):
        y, m = st.session_state.view_year, st.session_state.view_month
        if m == 12:
            st.session_state.view_year, st.session_state.view_month = y + 1, 1
        else:
            st.session_state.view_month = m + 1
        st.rerun()

# ============ 月曆（HTML Table 強制橫向）============
st.markdown("##### 📅 點選日期查看/新增記錄")

visits = load_visits()
visit_dates = {}
for v in visits:
    d = v.get("visit_date")
    if d:
        visit_dates[d] = visit_dates.get(d, 0) + 1

year, month = st.session_state.view_year, st.session_state.view_month
cal = calendar.Calendar(firstweekday=0)  # 週一開始
month_days = cal.monthdayscalendar(year, month)
today_str = date.today().isoformat()
selected_str = st.session_state.selected_date.isoformat()

# 建立 HTML 月曆
html = '<table class="calendar-table"><thead><tr>'
for wd in ["一", "二", "三", "四", "五", "六", "日"]:
    html += f'<th>{wd}</th>'
html += '</tr></thead><tbody>'

for week in month_days:
    html += '<tr>'
    for day in week:
        if day == 0:
            html += '<td><div class="cal-day cal-day-empty">&nbsp;</div></td>'
        else:
            d_str = f"{year}-{month:02d}-{day:02d}"
            cls = "cal-day"
            if d_str == today_str:
                cls += " cal-day-today"
            if d_str in visit_dates:
                cls += " cal-day-has"
            mark = f"<br><small>📍{visit_dates[d_str]}</small>" if d_str in visit_dates else ""
            html += f'<td><div class="{cls}">{day}{mark}</div></td>'
    html += '</tr>'
html += '</tbody></table>'

st.markdown(html, unsafe_allow_html=True)

# ============ 日期選擇器（補充：方便點擊）============
st.markdown("##### 🎯 選擇日期")
picked = st.date_input(
    "選擇日期",
    value=st.session_state.selected_date,
    label_visibility="collapsed",
    key="date_picker"
)
if picked != st.session_state.selected_date:
    st.session_state.selected_date = picked
    st.rerun()

st.divider()

# ============ 當日記錄 ============
sel_date = st.session_state.selected_date
sel_str = sel_date.isoformat()
day_records = [v for v in visits if v.get("visit_date") == sel_str]

st.markdown(f"### 📝 {sel_str} 巡店記錄")

if not day_records:
    st.info("📭 這天還沒有巡店記錄")
else:
    for r in day_records:
        store = r.get("store_name", "未知門市")
        status = r.get("status", "")
        manager = r.get("manager", "—")
        notes = r.get("notes", "")
        photo_url = r.get("photo_url", "")
        
        with st.container(border=True):
            st.markdown(f"**🏪 {store}**")
            st.caption(f"狀態：{status}　|　督導：{manager}")
            if notes:
                st.write(notes)
            if photo_url:
                st.image(photo_url, width=300)

# ============ 新增記錄 ============
with st.expander("➕ 新增巡店記錄", expanded=False):
    with st.form("add_visit", clear_on_submit=True):
        store_sel = st.selectbox("選擇門市 *", STORE_OPTIONS)
        v_date = st.date_input("日期 *", value=sel_date)
        status = st.radio("狀態 *", ["計畫", "已巡店"], horizontal=True)
        manager = st.text_input("督導姓名", placeholder="請輸入您的姓名")
        notes = st.text_area("備註", height=120)
        
        st.markdown("**📷 上傳照片**（選填）")
        tab1, tab2 = st.tabs(["📁 從相簿", "📸 拍照"])
        photo_file = None
        with tab1:
            photo_file = st.file_uploader("選擇照片", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        with tab2:
            cam = st.camera_input("拍照", label_visibility="collapsed")
            if cam:
                photo_file = cam
        
        submit = st.form_submit_button("💾 儲存到雲端", use_container_width=True, type="primary")
        
        if submit:
            code, name = store_sel.split(" - ", 1)
            photo_url = None
            if photo_file:
                photo_url = upload_photo(photo_file.getvalue(), photo_file.name if hasattr(photo_file, 'name') else "photo.jpg")
            
            data = {
                "store_code": code,
                "store_name": name,
                "visit_date": v_date.isoformat(),
                "status": status,
                "manager": manager or None,
                "notes": notes or None,
                "photo_url": photo_url,
            }
            try:
                insert_visit(data)
                st.cache_data.clear()
                st.toast("✅ 已成功儲存！", icon="✅")
                st.success("✅ 已儲存到雲端")
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")

st.divider()

# ============ 本月儀表板 ============
st.markdown("### 📊 本月統計")

month_records = [
    v for v in visits
    if v.get("visit_date", "").startswith(f"{year}-{month:02d}")
]

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("📊 本月巡店次數", len(month_records))
with c2:
    unique_stores = len(set(v.get("store_code", "") for v in month_records if v.get("store_code")))
    st.metric("🏪 巡店門市數", unique_stores)
with c3:
    # 安全處理：用 .get() 避免 KeyError
    managers = [v.get("manager") for v in month_records if v.get("manager")]
    st.metric("👤 督導人數", len(set(managers)))

st.caption(f"📡 資料來源：Supabase Cloud　|　更新時間：{datetime.now().strftime('%H:%M:%S')}")
