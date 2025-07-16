import streamlit as st
import datetime
from pytz import timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

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

# 📊 Dashboard รายวัน
st.title("📊 Dashboard ร้านเจริญค้า")

# ดึงข้อมูลจากชีทยอดขาย
sales_data = pd.DataFrame(summary_ws.get_all_records())
if not sales_data.empty:
    sales_data["timestamp"] = pd.to_datetime(sales_data["timestamp"], errors="coerce")
    today = datetime.now(timezone("Asia/Bangkok")).date()
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
else:
    st.warning("⚠️ ยังไม่มีข้อมูลยอดขายในระบบเลย")

# ✅ UI ขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("เลือกสินค้าจากชื่อ", product_names, key="search_items")
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

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

st.subheader("📋 รายการขาย")
total_price, total_profit = 0, 0
for item, qty in st.session_state.cart:
    row = df[df["ชื่อสินค้า"] == item].iloc[0]
    price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
    subtotal, profit = qty * price, qty * (price - cost)
    total_price += subtotal
    total_profit += profit
    st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

# 💰 ช่องรับเงิน
st.session_state.paid_input = st.number_input("💰 รับเงินจากลูกค้า", value=st.session_state.paid_input, step=1.0)
def add_money(amount: int):
    st.session_state.paid_input += amount
    st.session_state.last_paid_click = amount
col1, col2, col3 = st.columns(3)
with col1: st.button("20", on_click=add_money, args=(20,))
with col2: st.button("50", on_click=add_money, args=(50,))
with col3: st.button("100", on_click=add_money, args=(100,))
col4, col5 = st.columns(2)
with col4: st.button("500", on_click=add_money, args=(500,))
with col5: st.button("1000", on_click=add_money, args=(1000,))
if st.session_state.last_paid_click:
    if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
        st.session_state.paid_input -= st.session_state.last_paid_click
        st.session_state.last_paid_click = 0

# 💸 แสดงยอดรวม
st.info(f"📦 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
if st.session_state.paid_input >= total_price:
    st.success(f"💰 เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
else:
    st.warning("💸 เงินไม่พอ")

# ✅ ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    for item, qty in st.session_state.cart:
        index = df[df["ชื่อสินค้า"] == item].index[0]
        row = df.loc[index]
        idx_in_sheet = index + 2
        new_out = safe_safe_int(row["ออก"]) + qty
        new_left = safe_safe_int(row["คงเหลือในตู้"]) - qty
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

    summary_ws.append_row([
        now,
        ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
        total_price,
        total_profit,
        st.session_state.paid_input,
        st.session_state.paid_input - total_price,
        "drink"
    ])
    st.session_state.reset_search_items = True
    st.rerun()

# 📦 เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock_select")
    restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติมสินค้า"):
        index = df[df["ชื่อสินค้า"] == restock_item].index[0]
        idx_in_sheet = index + 2
        row = df.loc[index]
        new_in = safe_safe_int(row["เข้า"]) + restock_qty
        new_left = safe_safe_int(row["คงเหลือในตู้"]) + restock_qty
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
        st.success(f"✅ เติม {restock_item} แล้ว")

# ✏️ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_select")
    index = df[df["ชื่อสินค้า"] == edit_item].index[0]
    idx_in_sheet = index + 2
    row = df.loc[index]
    new_price = st.number_input("ราคาขาย", value=safe_safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุน", value=safe_safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือในตู้", value=safe_safe_int(row["คงเหลือในตู้"]), key="edit_stock", step=1)
    if st.button("💾 บันทึกการแก้ไข"):
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
        st.success(f"✅ อัปเดต {edit_item} แล้ว")

# 🔁 ปุ่มรีเซ็ตยอดเข้า-ออก
if st.button("🔁 รีเซ็ตยอดเข้า-ออก (เริ่มวันใหม่)", key="reset_io"):
    num_rows = len(df)
    worksheet.batch_update([
        {"range": f"E2:E{num_rows+1}", "values": [[0]] * num_rows},
        {"range": f"G2:G{num_rows+1}", "values": [[0]] * num_rows}
    ])
    st.success("✅ รีเซ็ตยอด 'เข้า' และ 'ออก' สำเร็จแล้วสำหรับวันใหม่")
