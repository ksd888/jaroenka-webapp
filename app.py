import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 🔑 ฟังก์ชันแปลง key ให้ปลอดภัย
def safe_key(text):
    return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()

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

# 🧮 ฟังก์ชันตัวเลขปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)
def safe_safe_int(val): 
    try: return safe_int(safe_float(val))
    except: return 0
def safe_safe_float(val): 
    try: return safe_float(val)
    except: return 0.0

# 🔧 เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# 📦 โหลดข้อมูล
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 🛠 ฟังก์ชันเพิ่ม/ลด จำนวน
def increase_quantity(p):
    st.session_state.quantities[p] += 1
def decrease_quantity(p):
    st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)

# 🧠 Session State เริ่มต้น
default_session = {
    "cart": [],
    "selected_products": [],
    "quantities": {},
    "paid_input": 0.0,
    "sale_complete": False
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 🔁 รีเซ็ตหลังขาย
if st.session_state.sale_complete:
    for key, default in default_session.items():
        st.session_state[key] = default
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

# 🛒 ส่วนขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")
product_names = df["ชื่อสินค้า"].tolist()
default_selected = []
if "reset_search_items" in st.session_state:
    default_selected = []
    del st.session_state["reset_search_items"]
else:
    default_selected = st.session_state.get("search_items", [])

st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names, default=default_selected, key="search_items")
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
        st.markdown(f"<div style='text-align: center; font-size: 24px;'>{qty}</div>", unsafe_allow_html=True)
    with col3:
        st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
    row = df[df['ชื่อสินค้า'] == p]
    stock = int(row['คงเหลือในตู้'].values[0]) if not row.empty else 0
    color = 'red' if stock < 3 else 'black'
    st.markdown(f"<span style='color:{color}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price = 0
    total_profit = 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_safe_float(row["ราคาขาย"])
        cost = safe_safe_float(row["ต้นทุน"])
        subtotal = qty * price
        profit = qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
    if st.session_state.paid_input >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("💸 ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        st.session_state["reset_search_items"] = True
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        st.session_state.sale_complete = True
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
