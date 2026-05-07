import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
from supabase import create_client
import uuid

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
    
    /* 月曆按鈕：強制小尺寸、橫向7欄 */
    div[data-testid="column"] {
        padding: 1px !important;
        min-width: 0 !important;
    }
    div[data-testid="column"] .stButton button {
        width: 100%;
        min-height: 42px;
        padding: 4px 0px;
        font-size: 13px;
        border-radius: 6px;
        margin: 0;
    }
    
    /* 一般按鈕 */
    .stButton button { min-height: 38px; }
    
    /* Tab 字體放大 */
    .stTabs [data-baseweb="tab"] { font-size: 16px; padding: 8px 12px; }
    
    /* 統計卡片 */
    div[data-testid="stMetricValue"] { font-size: 28px; }
</style>
""", unsafe_allow_html=True)

# ============ 19家門市清單（寫死，永不變動）============
STORES = [
    ("L07", "梧棲童綜合院內店"),
    ("L08", "向上光田一店"),
    ("L22", "大甲光田店"),
    ("L47", "沙鹿光田店"),
    ("L50", "清泉店"),
    ("L80", "梧棲童綜合店"),
    ("N05", "彰基二林店"),
    ("N06", "部立彰化店"),
    ("N08", "員榮院外店"),
    ("N09", "鹿基院外店"),
    ("N10", "員基院外店"),
    ("N15", "彰基中華店"),
    ("N33", "秀傳店"),
    ("P01", "若瑟便利店"),
    ("P03", "台大斗六院外店"),
    ("P05", "慈濟斗六院外店"),
    ("P13", "若瑟店"),
    ("R68", "彰基藥局"),
]
STORE_OPTIONS = [f"{code} - {name}" for code, name in STORES]

# ============ Supabase 連線 ============
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

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
    try:
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        supabase.storage.from_("store-photos").upload(
            unique_name, file_bytes,
            file_options={"content-type": f"image/{ext}"}
        )
        return supabase.storage.from_("store-photos").get_public_url(unique_name)
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
    if st.button("◀", use_container_width=True, key="prev_m"):
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
    if st.button("▶", use_container_width=True, key="next_m"):
        y, m = st.session_state.view_year, st.session_state.view_month
        if m == 12:
            st.session_state.view_year, st.session_state.view_month = y + 1, 1
        else:
            st.session_state.view_month = m + 1
        st.rerun()

# ============ 月曆（按鈕網格，可點擊）============
st.markdown("##### 📅 點選日期")

visits = load_visits()
visit_dates = {}
for v in visits:
    d = v.get("visit_date")
    if d:
        visit_dates[d] = visit_dates.get(d, 0) + 1

year, month = st.session_state.view_year, st.session_state.view_month
cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(year, month)
today_str = date.today().isoformat()
selected_str = st.session_state.selected_date.isoformat()

# 星期標題
week_cols = st.columns(7)
for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
    week_cols[i].markdown(f"<div style='text-align:center;color:#888;font-size:12px;font-weight:600'>{wd}</div>", unsafe_allow_html=True)

# 日期按鈕
for week in month_days:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.markdown("&nbsp;", unsafe_allow_html=True)
            else:
                d_str = f"{year}-{month:02d}-{day:02d}"
                # 標記
                label = f"{day}"
                if d_str in visit_dates:
                    label = f"{day}●"
                
                # 按鈕類型
                if d_str == selected_str:
                    btn_type = "primary"
                else:
                    btn_type = "secondary"
                
                if st.button(label, key=f"d_{d_str}", use_container_width=True, type=btn_type):
                    st.session_state.selected_date = date(year, month, day)
                    st.rerun()

st.caption("🔵 已選日期　●有記錄")
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
        code = r.get("store_code", "")
        status = r.get("status", "")
        notes = r.get("notes", "")
        photo_url = r.get("photo_url", "")
        
        with st.container(border=True):
            st.markdown(f"**🏪 {code} - {store}**")
            st.caption(f"狀態：{status}")
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
        notes = st.text_area("備註", height=120, placeholder="本次巡店重點、發現問題、改善建議...")
        
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
                fname = photo_file.name if hasattr(photo_file, 'name') else "photo.jpg"
                photo_url = upload_photo(photo_file.getvalue(), fname)
            
            data = {
                "store_code": code,
                "store_name": name,
                "visit_date": v_date.isoformat(),
                "status": status,
                "notes": notes or None,
                "photo_url": photo_url,
            }
            try:
                insert_visit(data)
                st.cache_data.clear()
                st.toast("✅ 已成功儲存！", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")

st.divider()

# ============ 本月統計 ============
st.markdown(f"### 📊 {year} 年 {month} 月統計")

month_records = [
    v for v in visits
    if v.get("visit_date", "").startswith(f"{year}-{month:02d}")
]

c1, c2 = st.columns(2)
with c1:
    st.metric("📊 巡店次數", len(month_records))
with c2:
    visited_codes = sorted(set(v.get("store_code", "") for v in month_records if v.get("store_code")))
    st.metric("🏪 巡店門市數", len(visited_codes))

# 巡店門市明細
if visited_codes:
    st.markdown("**✅ 本月已巡店門市：**")
    # 對照名稱
    code_name_map = {c: n for c, n in STORES}
    detail_lines = []
    for code in visited_codes:
        name = code_name_map.get(code, "")
        count = sum(1 for v in month_records if v.get("store_code") == code)
        detail_lines.append(f"- **{code}** {name}　（{count} 次）")
    st.markdown("\n".join(detail_lines))
    
    # 未巡店門市
    all_codes = set(c for c, _ in STORES)
    not_visited = sorted(all_codes - set(visited_codes))
    if not_visited:
        with st.expander(f"⚠️ 本月尚未巡店門市（{len(not_visited)} 家）"):
            for code in not_visited:
                name = code_name_map.get(code, "")
                st.markdown(f"- {code} {name}")
else:
    st.info("📭 本月尚無巡店記錄")

st.caption(f"📡 Supabase Cloud　|　更新時間：{datetime.now().strftime('%H:%M:%S')}")
