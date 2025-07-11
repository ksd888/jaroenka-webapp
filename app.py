
import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ✅ Light Theme Style แบบ Apple
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
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stTextInput>div>div>input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        background-color: #f5f5f5 !important;
        color: #000 !important;
    }
    .st-expander, .st-expander>details {
        background-color: #f8f8f8 !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🔐 เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

data = worksheet.get_all_records()
df = pd.DataFrame(data)

def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ⚙️ ค่าตั้งต้น
if "cart" not in st.session_state:
    st.session_state.cart = {}

if "sale_complete" not in st.session_state:
    st.session_state.sale_complete = False

if st.session_state.sale_complete:
    st.session_state.cart = {}
    st.session_state.sale_complete = False
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

# 🔍 ค้นหา
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names)

for p in selected:
    if p not in st.session_state.cart:
        st.session_state.cart[p] = 1

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.cart[p] = max(1, st.session_state.cart[p] - 1)
    with col2:
        st.markdown(f"<div style='text-align:center;font-size:20px;font-weight:bold'>{st.session_state.cart[p]}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.cart[p] += 1

    row = df[df['ชื่อสินค้า'] == p]
    stock = int(row['คงเหลือในตู้'].values[0]) if not row.empty else 0
    st.markdown(f"🧊 คงเหลือในตู้: {stock}")

if st.button("🛒 เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มลงตะกร้าแล้ว")

# 🧾 แสดงรายการในตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price = 0
    total_profit = 0
    for item, qty in st.session_state.cart.items():
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        subtotal = qty * price
        profit = qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    paid = st.number_input("💰 รับเงิน", value=0.0, step=1.0)
    if paid >= total_price:
        st.success(f"เงินทอน: {paid - total_price:.2f} บาท")
    else:
        st.warning("💸 ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart.items():
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2
            new_out = safe_int(row["ออก"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) - qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

        summary_ws.append_row([
            now,
            ", ".join([f"{i} x {q}" for i, q in st.session_state.cart.items()]),
            total_price,
            total_profit,
            paid,
            paid - total_price,
            "drink"
        ])
        st.session_state.sale_complete = True
        st.rerun()
