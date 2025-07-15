
import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import uuid

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

# 🔧 Helper functions
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

# 🔗 Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# 🔁 Default session state
default_session = {
    "cart": [],
    "selected_products": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "sale_complete": False
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.sale_complete:
    for key, default in default_session.items():
        st.session_state[key] = default
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

    # ✅ เคลียร์สินค้าที่เลือกใน multiselect
    if "reset_search_items" in st.session_state:
        st.session_state["search_items"] = []
        del st.session_state["reset_search_items"]

# 🛒 ระบบขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🔍 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
default_selected = st.session_state.get("search_items", [])

st.multiselect("เลือกสินค้าจากชื่อ", product_names, default=default_selected, key="search_items")

selected = st.session_state.get("search_items", [])
for p in selected:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    qty = st.session_state.quantities[p]

    st.markdown(f"**{p}**")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
    with col2:
        st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
    with col3:
        st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))

    row = df[df['ชื่อสินค้า'] == p]
    stock = int(row['คงเหลือในตู้'].values[0]) if not row.empty else 0
    color = 'red' if stock < 3 else 'black'
    st.markdown(
        f"<span style='color:{color}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>",
        unsafe_allow_html=True
    )

# 🧺 เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 🧾 แสดงรายการขาย
suffix = str(int(time.time() * 1000))
paid_input_key = f"paid_input_{uuid.uuid4().hex}"
st.subheader("📋 รายการขาย")

# ---------- 💸 ปุ่มเงินลัด (callback ไม่ใช้ rerun) ----------
def add_money(amount: int):
    st.session_state.paid_input += amount
    st.session_state.last_paid_click = amount

row1 = st.columns(3); row2 = st.columns(2)
with row1[0]: st.button("20",  on_click=add_money, args=(20,))
with row1[1]: st.button("50",  on_click=add_money, args=(50,))
with row1[2]: st.button("100", on_click=add_money, args=(100,))
with row2[0]: st.button("500", on_click=add_money, args=(500,))
with row2[1]: st.button("1000",on_click=add_money, args=(1000,))

# ปุ่ม Undo เงินลัด
if st.session_state.last_paid_click:
    if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
        st.session_state.paid_input -= st.session_state.last_paid_click
        st.session_state.last_paid_click = 0
st.session_state.paid_input = st.number_input("💰 รับเงินจากลูกค้า (พิมพ์เอง)", value=st.session_state.paid_input, step=1.0, key=paid_input_key)

total_price, total_profit = 0, 0
for item, qty in st.session_state.cart:
    row = df[df["ชื่อสินค้า"] == item].iloc[0]
    price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
    subtotal, profit = qty * price, qty * (price - cost)
    total_price += subtotal
    total_profit += profit
    st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

st.info(f"💵 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
