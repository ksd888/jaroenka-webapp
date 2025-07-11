import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# --- Setup Theme Toggle ---
if "theme" not in st.session_state:
    st.session_state.theme = "light"

theme = st.session_state.theme
is_dark = theme == "dark"

# --- Page Config ---
st.set_page_config(page_title="เจริญค้า", layout="wide")
st.markdown(f"""
<style>
html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
    background-color: {'#000' if is_dark else '#fff'} !important;
    color: {'#fff' if is_dark else '#000'} !important;
}}
.stButton>button {{
    background-color: {'#fff' if is_dark else '#000'} !important;
    color: {'#000' if is_dark else '#fff'} !important;
    padding: 8px 20px;
    border: none;
    border-radius: 12px;
    font-weight: 600;
}}
</style>
""", unsafe_allow_html=True)

# --- Show Logo ---
st.image("logo.png", width=100)

# --- Theme Toggle ---
toggle = st.radio("Theme", options=["Light", "Dark"], index=0 if theme == "light" else 1, horizontal=True)
st.session_state.theme = toggle.lower()

# --- Connect to Google Sheet ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# --- Read Inventory Data ---
df = pd.DataFrame(worksheet.get_all_records())
summary_df = pd.DataFrame(summary_ws.get_all_records())

# --- Navigation ---
page = st.sidebar.radio("📂 เลือกหน้า", ["🛒 ระบบขายสินค้า", "📊 Dashboard"])

# --- Safe Conversions ---
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# -----------------------------
# PAGE 1: ระบบขายสินค้า
# -----------------------------
if page == "🛒 ระบบขายสินค้า":
    if "cart" not in st.session_state:
        st.session_state.cart = []
    if "quantities" not in st.session_state:
        st.session_state.quantities = {}
    if "paid_input" not in st.session_state:
        st.session_state.paid_input = 0.0

    st.header("🧊 ระบบขายสินค้า")
    product_names = df["ชื่อสินค้า"].tolist()
    selected = st.multiselect("🔍 ค้นหาสินค้า", product_names)

    for p in selected:
        if p not in st.session_state.quantities:
            st.session_state.quantities[p] = 1
        st.markdown(f"**{p}**")
        cols = st.columns([1, 1, 1])
        with cols[0]:
            if st.button("➖", key=f"dec_{p}"):
                st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
        with cols[1]:
            st.markdown(f"<div style='text-align:center; font-size:20px; font-weight:bold'>{st.session_state.quantities[p]}</div>", unsafe_allow_html=True)
        with cols[2]:
            if st.button("➕", key=f"inc_{p}"):
                st.session_state.quantities[p] += 1

    if st.button("➕ เพิ่มลงตะกร้า"):
        for p in selected:
            qty = st.session_state.quantities[p]
            st.session_state.cart.append((p, qty))
        st.success("เพิ่มลงตะกร้าแล้ว ✅")

    if st.session_state.cart:
        st.subheader("📋 รายการขาย")
        total, profit = 0, 0
        for p, qty in st.session_state.cart:
            row = df[df["ชื่อสินค้า"] == p].iloc[0]
            price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
            total += qty * price
            profit += qty * (price - cost)
            st.write(f"- {p} x {qty} = {qty * price:.2f} บาท")
        st.info(f"💵 ยอดรวม: {total:.2f} บาท | กำไร: {profit:.2f} บาท")

        st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input)
        if st.session_state.paid_input >= total:
            st.success(f"เงินทอน: {st.session_state.paid_input - total:.2f} บาท")
        if st.button("✅ ยืนยันการขาย"):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            summary_ws.append_row([
                now,
                ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
                total,
                profit,
                st.session_state.paid_input,
                st.session_state.paid_input - total,
                "drink"
            ])
            st.session_state.cart = []
            st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

# -----------------------------
# PAGE 2: Dashboard
# -----------------------------
elif page == "📊 Dashboard":
    st.header("📊 Dashboard รายงานยอดขาย")

    today = datetime.datetime.now().date()
    summary_df["วันที่"] = pd.to_datetime(summary_df["วันที่"], errors='coerce')
    today_sales = summary_df[summary_df["วันที่"].dt.date == today]

    total_sales = today_sales["ยอดขาย"].sum()
    total_profit = today_sales["กำไร"].sum()

    st.metric("💰 ยอดขายวันนี้", f"{total_sales:.2f} บาท")
    st.metric("📈 กำไรสุทธิ", f"{total_profit:.2f} บาท")

    if not today_sales.empty:
        st.subheader("📦 รายการขายวันนี้")
        st.dataframe(today_sales[["เวลา", "รายการ", "ยอดขาย", "กำไร"]])

        st.subheader("📊 กราฟยอดขาย")
        fig = px.bar(
            today_sales,
            x="เวลา",
            y="ยอดขาย",
            title="ยอดขายรายรายการ",
            color_discrete_sequence=["#4da6ff"] if not is_dark else ["#00ffff"]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลยอดขายสำหรับวันนี้")
