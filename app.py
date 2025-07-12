import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="ร้านเจริญค้า - ตะกร้าเดียว", layout="wide")

# ---------- STYLE ----------
st.markdown("""
    <style>
        body, .stApp {
            background-color: #ffffff;
            color: #000000;
            font-family: -apple-system, BlinkMacSystemFont, 'Kanit', sans-serif;
        }
        .stButton>button {
            background-color: #007aff !important;
            color: white !important;
            border-radius: 8px;
            font-weight: bold;
            padding: 0.5em 1.2em;
        }
        .stNumberInput input {
            text-align: center;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- UTILITIES ----------
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ---------- GOOGLE SHEETS ----------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ---------- SESSION ----------
if "quantities" not in st.session_state:
    st.session_state.quantities = {}
if "paid" not in st.session_state:
    st.session_state.paid = 0.0

# ---------- SEARCH & ADD ----------
st.title("🧊 ร้านเจริญค้า - ระบบตะกร้าเดียว (Unified Cart)")
product_names = df["ชื่อสินค้า"].tolist()

st.subheader("🔍 ค้นหาและเลือกสินค้า")
selected_products = st.multiselect("เลือกสินค้า", product_names)

for pname in selected_products:
    row = df[df["ชื่อสินค้า"] == pname].iloc[0]
    stock = safe_int(row["คงเหลือในตู้"])
    if pname not in st.session_state.quantities:
        st.session_state.quantities[pname] = 1
    col1, col2 = st.columns([2, 1])
    with col1:
        st.session_state.quantities[pname] = st.number_input(
            f"จำนวน {pname}", min_value=0, step=1,
            value=st.session_state.quantities[pname], key=f"qty_{pname}")
    with col2:
        st.markdown(f"🧊 คงเหลือในตู้: **{stock}**")

# ---------- CART DISPLAY ----------
cart_items = {p: q for p, q in st.session_state.quantities.items() if q > 0}
if cart_items:
    st.markdown("## 🧾 รายการขาย")
    total, profit = 0, 0
    for pname, qty in cart_items.items():
        row = df[df["ชื่อสินค้า"] == pname].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        line_total = price * qty
        line_profit = (price - cost) * qty
        total += line_total
        profit += line_profit
        st.write(f"- {pname} x {qty} = {line_total:.2f} บาท")

    st.markdown(f"💰 **ยอดรวม:** {total:.2f} บาท  🟢 **กำไร:** {profit:.2f} บาท")

    st.session_state.paid = st.number_input("💵 รับเงิน", min_value=0.0, step=1.0, format="%.2f")
    if st.session_state.paid > 0:
        change = st.session_state.paid - total
        st.markdown(f"💸 เงินทอน: **{change:.2f} บาท**")
