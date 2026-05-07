import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import calendar
import pandas as pd
from io import BytesIO
import uuid

# ==================== 頁面設定 ====================
st.set_page_config(
    page_title="督導巡店管理系統",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== Supabase 連線 ====================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ==================== 自訂 CSS（手機優化）====================
st.markdown("""
<style>
    /* 行事曆按鈕縮小 */
    div[data-testid="column"] .stButton button {
        padding: 0.25rem 0.3rem !important;
        font-size: 0.85rem !important;
        min-height: 2.2rem !important;
        width: 100% !important;
    }
    
    /* 手機版字體調整 */
    @media (max-width: 768px) {
        div[data-testid="column"] .stButton button {
            padding: 0.2rem 0.1rem !important;
            font-size: 0.75rem !important;
            min-height: 2rem !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
    }
    
    /* 星期標題 */
    .weekday-header {
        text-align: center;
        font-weight: bold;
        padding: 0.3rem;
        background-color: #f0f2f6;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    
    /* 主題標題 */
    .main-title {
        text-align: center;
        color: #1f77b4;
        padding: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 資料庫操作函式 ====================
def get_visits_by_month(year, month):
    """取得指定月份的所有巡店記錄"""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    
    response = supabase.table("visits").select("*").gte("visit_date", start_date).lt("visit_date", end_date).execute()
    return response.data

def get_visits_by_date(visit_date):
    """取得特定日期的所有巡店記錄"""
    response = supabase.table("visits").select("*").eq("visit_date", str(visit_date)).order("created_at", desc=True).execute()
    return response.data

def add_visit(visit_date, store_code, store_name, manager_name, notes, photo_url=None):
    """新增巡店記錄"""
    data = {
        "visit_date": str(visit_date),
        "store_code": store_code,
        "store_name": store_name,
        "manager_name": manager_name,
        "notes": notes,
        "photo_url": photo_url
    }
    response = supabase.table("visits").insert(data).execute()
    return response.data

def delete_visit(visit_id):
    """刪除巡店記錄"""
    supabase.table("visits").delete().eq("id", visit_id).execute()

def upload_photo(file_bytes, file_extension="jpg"):
    """上傳照片到 Supabase Storage"""
    try:
        # 產生唯一檔名
        file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # 上傳檔案
        supabase.storage.from_("store-photos").upload(
            file_name, 
            file_bytes,
            file_options={"content-type": f"image/{file_extension}"}
        )
        
        # 取得公開 URL
        public_url = supabase.storage.from_("store-photos").get_public_url(file_name)
        return public_url
    except Exception as e:
        st.error(f"照片上傳失敗：{str(e)}")
        return None

# ==================== Session State 初始化 ====================
if "current_year" not in st.session_state:
    st.session_state.current_year = datetime.now().year
if "current_month" not in st.session_state:
    st.session_state.current_month = datetime.now().month
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ==================== 主標題 ====================
st.markdown("<h1 class='main-title'>🏪 督導巡店管理系統</h1>", unsafe_allow_html=True)

# ==================== 月份切換 ====================
col_prev, col_title, col_next = st.columns([1, 3, 1])

with col_prev:
    if st.button("◀ 上月", use_container_width=True):
        if st.session_state.current_month == 1:
            st.session_state.current_month = 12
            st.session_state.current_year -= 1
        else:
            st.session_state.current_month -= 1
        st.rerun()

with col_title:
    st.markdown(
        f"<h2 style='text-align: center; margin: 0;'>{st.session_state.current_year} 年 {st.session_state.current_month} 月</h2>",
        unsafe_allow_html=True
    )

with col_next:
    if st.button("下月 ▶", use_container_width=True):
        if st.session_state.current_month == 12:
            st.session_state.current_month = 1
            st.session_state.current_year += 1
        else:
            st.session_state.current_month += 1
        st.rerun()

# ==================== 取得本月巡店資料 ====================
visits_this_month = get_visits_by_month(st.session_state.current_year, st.session_state.current_month)

# 整理：哪些日期有巡店記錄
visit_dates = {}
for v in visits_this_month:
    d = v["visit_date"]
    visit_dates[d] = visit_dates.get(d, 0) + 1

# ==================== 行事曆顯示 ====================
st.markdown("### 📅 點選日期查看/新增記錄")

# 星期標題
weekdays = ["一", "二", "三", "四", "五", "六", "日"]
cols = st.columns(7)
for i, day in enumerate(weekdays):
    with cols[i]:
        st.markdown(f"<div class='weekday-header'>{day}</div>", unsafe_allow_html=True)

# 產生月曆
cal = calendar.Calendar(firstweekday=0)  # 0=星期一
month_days = cal.monthdayscalendar(st.session_state.current_year, st.session_state.current_month)

today = date.today()

for week in month_days:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.markdown("&nbsp;", unsafe_allow_html=True)
            else:
                this_date = date(st.session_state.current_year, st.session_state.current_month, day)
                date_str = str(this_date)
                
                # 顯示文字
                count = visit_dates.get(date_str, 0)
                if count > 0:
                    btn_label = f"{day}\n📍{count}"
                else:
                    btn_label = f"{day}"
                
                # 今天用特殊標記
                btn_type = "primary" if this_date == today else "secondary"
                
                if st.button(btn_label, key=f"day_{date_str}", use_container_width=True, type=btn_type):
                    st.session_state.selected_date = this_date
                    st.rerun()

st.divider()

# ==================== 選定日期的詳細資料 ====================
st.markdown(f"### 📝 {st.session_state.selected_date} 巡店記錄")

# 顯示該日記錄
day_visits = get_visits_by_date(st.session_state.selected_date)

if day_visits:
    for visit in day_visits:
        with st.container(border=True):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(f"**🏪 {visit['store_code']} - {visit['store_name']}**")
                st.markdown(f"👤 督導：{visit['manager_name']}")
                if visit.get('notes'):
                    st.markdown(f"📋 備註：{visit['notes']}")
                if visit.get('photo_url'):
                    st.image(visit['photo_url'], width=300)
            with col_del:
                if st.button("🗑️", key=f"del_{visit['id']}", help="刪除此記錄"):
                    delete_visit(visit['id'])
                    st.toast("✅ 記錄已刪除", icon="🗑️")
                    st.rerun()
else:
    st.info("📭 這天還沒有巡店記錄")

st.divider()

# ==================== 新增巡店記錄表單 ====================
with st.expander("➕ 新增巡店記錄", expanded=not bool(day_visits)):
    with st.form("add_visit_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            store_code = st.text_input("🏷️ 店號", placeholder="例：A001")
        with col2:
            store_name = st.text_input("🏪 店名", placeholder="例：信義店")
        
        manager_name = st.text_input("👤 督導姓名", placeholder="例：王經理")
        
        notes = st.text_area(
            "📋 備註",
            placeholder="記錄今日巡店狀況、問題、待改善事項...",
            height=120
        )
        
        # 照片上傳
        st.markdown("**📷 照片（選填）**")
        photo_tab1, photo_tab2 = st.tabs(["📁 上傳檔案", "📸 拍照"])
        
        photo_file = None
        with photo_tab1:
            photo_file = st.file_uploader(
                "選擇照片",
                type=["jpg", "jpeg", "png"],
                key="upload_photo"
            )
        
        with photo_tab2:
            camera_photo = st.camera_input("拍攝照片", key="camera_photo")
            if camera_photo:
                photo_file = camera_photo
        
        submitted = st.form_submit_button("✅ 儲存記錄", use_container_width=True, type="primary")
        
        if submitted:
            if not store_code or not store_name or not manager_name:
                st.toast("⚠️ 請填寫店號、店名、督導姓名", icon="⚠️")
            else:
                # 處理照片上傳
                photo_url = None
                if photo_file is not None:
                    with st.spinner("📤 上傳照片中..."):
                        file_bytes = photo_file.getvalue()
                        ext = photo_file.name.split('.')[-1].lower() if hasattr(photo_file, 'name') else "jpg"
                        photo_url = upload_photo(file_bytes, ext)
                
                # 新增記錄
                add_visit(
                    st.session_state.selected_date,
                    store_code,
                    store_name,
                    manager_name,
                    notes,
                    photo_url
                )
                st.toast("✅ 記錄新增成功！", icon="🎉")
                st.rerun()

# ==================== 統計資訊 ====================
st.divider()
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.metric("📊 本月巡店次數", len(visits_this_month))
with col_s2:
    unique_stores = len(set(v['store_code'] for v in visits_this_month))
    st.metric("🏪 巡店門市數", unique_stores)
with col_s3:
    unique_managers = len(set(v['manager_name'] for v in visits_this_month))
    st.metric("👥 督導人數", unique_managers)
