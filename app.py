import streamlit as st
import datetime
from pytz import timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt

# ✅ Apple Style CSS + ปรับสีข้อความให้เข้มขึ้น
st.markdown("""
    <style>
    body, .main, .block-container {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    .stButton>button {
        color: white !important;
        background-color: #007aff !important;
        border: none;
        border-radius: 10px;
        padding: 0.5em 1.2em;
        font-weight: bold;
    }
    .stTextInput>div>div>input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        background-color: #f2f2f7 !important;
        color: #000 !important;
        border-radius: 6px;
        font-size: 18px;
        font-weight: bold;
    }
    .st-expander, .st-expander>details {
        background-color: #f9f9f9 !important;
        color: #000000 !important;
        border-radius: 8px;
    }
    .stAlert > div {
        font-weight: bold;
        color: #000 !important;
    }
    .stAlert[data-testid="stAlert-success"] {
        background-color: #d4fcd4 !important;
        border: 1px solid #007aff !important;
    }
    .stAlert[data-testid="stAlert-info"] {
        background-color: #e6f0ff !important;
        border: 1px solid #007aff !important;
    }
    .stAlert[data-testid="stAlert-warning"] {
        background-color: #fff4d2 !important;
        border: 1px solid #ff9500 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ✅ ปุ่มเมนูด้านบนแทน Sidebar
st.markdown("### 🚀 เมนูหลัก")
col1, col2, col3 = st.columns(3)
if "page" not in st.session_state:
    st.session_state.page = "ขายสินค้า"
with col1:
    if st.button("🏪 ขายสินค้า"):
        st.session_state.page = "ขายสินค้า"
with col2:
    if st.button("🧊 ขายน้ำแข็ง"):
        st.session_state.page = "ขายน้ำแข็ง"
with col3:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"

# ✅ ตั้งเวลา
now = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")

# ✅ เชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# ✅ Helper functions
def safe_key(text): return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)
def safe_safe_int(val): 
    try: return safe_int(safe_float(val))
    except: return 0
def safe_safe_float(val): 
    try: return safe_float(val)
    except: return 0.0
def increase_quantity(p): st.session_state.quantities[p] += 1
def decrease_quantity(p): st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)

# ✅ รีเซ็ต Session
if st.session_state.get("reset_search_items"):
    st.session_state["search_items"] = []
    st.session_state["quantities"] = {}
    st.session_state["cart"] = []
    st.session_state["paid_input"] = 0.0
    st.session_state["last_paid_click"] = 0
    del st.session_state["reset_search_items"]

# ✅ ค่าเริ่มต้น
default_session = {
    "cart": [],
    "search_items": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "sale_complete": False
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ หน้า Dashboard
if st.session_state.page == "Dashboard":
    st.title("📊 Dashboard รายวัน")
    try:
        sales_ws = sheet.worksheet("ยอดขาย")
        sales_data = pd.DataFrame(sales_ws.get_all_records())

        if "เวลา" in sales_data.columns:
            sales_data = sales_data.rename(columns={"เวลา": "timestamp"})
        else:
            st.warning("❌ ไม่พบคอลัมน์ 'เวลา' ในชีทยอดขาย")
            sales_data["timestamp"] = pd.NaT

        sales_data["timestamp"] = pd.to_datetime(sales_data["timestamp"], errors="coerce")
        today = datetime.datetime.now(timezone("Asia/Bangkok")).date()
        today_sales = sales_data[sales_data["timestamp"].dt.date == today]

        if not today_sales.empty:
            total_today_price = today_sales["total_price"].sum()
            total_today_profit = today_sales["total_profit"].sum()
            top_items = today_sales["Items"].value_counts().idxmax()

            st.success(f"✅ ยอดขายวันนี้: {total_today_price:.2f} บาท")
            st.info(f"🟢 กำไรวันนี้: {total_today_profit:.2f} บาท")
            st.warning(f"🔥 สินค้าขายดี: {top_items}")
        else:
            st.warning("⚠️ ยังไม่มีข้อมูลยอดขายวันนี้")

        # กราฟ 14 วัน
        sales_data["วันที่"] = sales_data["timestamp"].dt.date
        recent_df = sales_data.sort_values("วันที่", ascending=False).head(14)
        daily_summary = recent_df.groupby("วันที่").agg({"total_profit": "sum", "total_price": "sum"}).sort_index()

        st.subheader("📈 กราฟกำไรสุทธิรายวัน")
        fig1, ax1 = plt.subplots()
        ax1.plot(daily_summary.index, daily_summary["total_profit"], marker='o')
        ax1.set_ylabel("กำไรสุทธิ (บาท)")
        ax1.set_xlabel("วันที่")
        ax1.grid(True)
        st.pyplot(fig1)

        st.subheader("💰 ยอดขายรวมและกำไรรวม 14 วันล่าสุด")
        st.metric("ยอดขายรวม", f"{daily_summary['total_price'].sum():,.0f} บาท")
        st.metric("กำไรสุทธิรวม", f"{daily_summary['total_profit'].sum():,.0f} บาท")

        st.subheader("🔥 วันที่ขายดีสุด")
        top_day = daily_summary["total_price"].idxmax()
        top_sales = daily_summary["total_price"].max()
        st.success(f"วันที่ {top_day} มียอดขายสูงสุด {top_sales:,.0f} บาท")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด Dashboard: {e}")

# ✅ (อื่น ๆ เช่นหน้าขายสินค้า / น้ำแข็ง ให้นำมาต่อเติมตรงนี้ได้เลย)
# ✅ หน้า "ขายสินค้า"
elif st.session_state.page == "ขายสินค้า":
    st.title("🧃 ขายสินค้าตู้เย็น")
    st.multiselect("เลือกสินค้าจากชื่อ", df["ชื่อสินค้า"].tolist(), key="search_items")
    selected = st.session_state["search_items"]
    for p in selected:
        if p not in st.session_state.quantities:
            st.session_state.quantities[p] = 1
        qty = st.session_state.quantities[p]
        st.markdown(f"**{p}**")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1: st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
        with col2: st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
        with col3: st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
        row = df[df["ชื่อสินค้า"] == p]
        stock = int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
        st.markdown(f"<span style='color:{'red' if stock < 3 else 'black'}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)

# ✅ หน้า "ขายน้ำแข็ง"
elif st.session_state.page == "ขายน้ำแข็ง":
    st.title("🧊 ขายน้ำแข็ง (แยกหน้า)")
    iceflow_sheet = sheet.worksheet("iceflow")
    df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
    df_ice["ราคาขายต่อหน่วย"] = pd.to_numeric(df_ice["ราคาขายต่อหน่วย"], errors='coerce')
    df_ice["ต้นทุนต่อหน่วย"] = pd.to_numeric(df_ice["ต้นทุนต่อหน่วย"], errors='coerce')
    df_ice = df_ice.dropna(subset=["ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย"])

    today_str = datetime.datetime.now().strftime("%-d/%-m/%Y")
    if df_ice["วันที่"].iloc[0] != today_str:
        df_ice["วันที่"] = today_str
        df_ice["รับเข้า"] = 0
        df_ice["ขายออก"] = 0
        df_ice["จำนวนละลาย"] = 0
        df_ice["คงเหลือตอนเย็น"] = 0
        df_ice["กำไรรวม"] = 0
        df_ice["กำไรสุทธิ"] = 0
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        st.info("🔄 ระบบรีเซ็ตยอดใหม่สำหรับวันนี้แล้ว")

    updates = []
    total_income = 0
    total_profit = 0
    for i, row in df_ice.iterrows():
        name = row["ชนิดน้ำแข็ง"]
        price = float(row["ราคาขายต่อหน่วย"])
        cost = float(row["ต้นทุนต่อหน่วย"])
        unit_profit = price - cost
        st.subheader(f"💼 {name}")
        in_qty = st.number_input(f"📥 รับเข้า {name}", min_value=0, value=int(row["รับเข้า"]), key=f"in_{i}")
        out_qty = st.number_input(f"🧊 ขายออก {name}", min_value=0, value=int(row["ขายออก"]), key=f"out_{i}")
        balance = in_qty - out_qty
        total = out_qty * price
        profit = out_qty * unit_profit
        df_ice.at[i, "วันที่"] = today_str
        df_ice.at[i, "รับเข้า"] = in_qty
        df_ice.at[i, "ขายออก"] = out_qty
        df_ice.at[i, "คงเหลือตอนเย็น"] = balance
        df_ice.at[i, "กำไรรวม"] = profit
        df_ice.at[i, "กำไรสุทธิ"] = profit
        updates.append({
            "name": name,
            "qty": out_qty,
            "price": price,
            "cost": cost,
            "unit_profit": unit_profit,
            "total_profit": profit,
            "total_income": total
        })
        total_income += total
        total_profit += profit

    if st.button("✅ บันทึกการขายน้ำแข็ง"):
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        for item in updates:
            summary_ws.append_row([
                today_str,
                item["name"],
                item["qty"],
                item["price"],
                item["cost"],
                item["unit_profit"],
                item["total_income"],
                item["total_profit"],
                "ice"
            ])
        st.success(f"✅ บันทึกเรียบร้อย | ขายรวม {total_income:.0f} บาท | กำไร {total_profit:.0f} บาท")
