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

def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

data = worksheet.get_all_records()
df = pd.DataFrame(data)

def safe_safe_int(val): 
    try:
        return safe_int(safe_float(val))
    except (TypeError, ValueError):
        return 0

def safe_safe_float(val): 
    try:
        return safe_float(val)
    except (TypeError, ValueError):
        return 0.0

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

if st.session_state.sale_complete:
    for key, default in default_session.items():
        st.session_state[key] = default
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

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
    st.markdown(f"**{p}**")
    qty_cols = st.columns([1, 1, 1])
    with qty_cols[0]:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    with qty_cols[1]:
        st.markdown(
            f"<div style='text-align:center; font-size:20px; font-weight:bold'>{st.session_state.quantities[p]}</div>",
            unsafe_allow_html=True
        )
    with qty_cols[2]:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1

    row = df[df['ชื่อสินค้า'] == p]
    stock = int(row['คงเหลือในตู้'].values[0]) if not row.empty else 0
    color = 'red' if stock < 3 else 'black'
    st.markdown(
        f"<span style='color:{color}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>",
        unsafe_allow_html=True
    )

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
        subtotal, profit = qty * price, qty * (price - cost)
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



for pname in selected:
    st.write(f"### {pname}")
    qty = st.number_input(
        f"จำนวนที่ต้องการขายสำหรับ {pname}",
        min_value=0,
        value=st.session_state["cart"].get(pname, 0),
        step=1,
        key=f"qty_{pname}"
    )
    st.session_state["cart"][pname] = qty

    remaining = df[df["ชื่อสินค้า"] == pname]["คงเหลือในตู้"].values[0]
    st.write(f"🧊 คงเหลือในตู้: {remaining}")

    if st.button(f"➕ เพิ่มลงตะกร้า", key=f"add_{pname}"):
        st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# ✅ แสดงตะกร้า
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for pname, qty in st.session_state["cart"].items():
    if qty > 0:
        row = df[df["ชื่อสินค้า"] == pname]
        price = float(row["ราคาขาย"].values[0])
        cost = float(row["ต้นทุน"].values[0])
        st.write(f"- {pname} x {qty} = {price * qty:.2f} บาท")
        total += price * qty
        profit += (price - cost) * qty

st.markdown(f"💵 ยอดรวม: {total:.2f} บาท 🟢 กำไร: {profit:.2f} บาท")

# ✅ รับเงิน
received = st.number_input("💰 รับเงิน", min_value=0.0, value=0.0, step=1.0)
change = received - total
if received > 0:
    st.markdown(f'''
    <div style="background-color:#fff8dc;padding:10px;border-radius:10px;">
        <span style="color:#000000;font-weight:bold;font-size:18px;">
        💵 เงินทอน: {change:.2f} บาท
        </span>
    </div>
    ''', unsafe_allow_html=True)

# ✅ ยืนยันขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pname, qty in st.session_state["cart"].items():
        if qty > 0:
            df.loc[df["ชื่อสินค้า"] == pname, "ออก"] += qty
            df.loc[df["ชื่อสินค้า"] == pname, "คงเหลือในตู้"] -= qty
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.session_state["cart"] = {}
    st.experimental_rerun()
