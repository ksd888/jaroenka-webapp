import streamlit as st
import datetime
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 🎨 กำหนด Theme แบบ Apple
st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")

st.markdown("""
    <style>
    html, body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background-color: #f5f5f7;
        color: #1d1d1f;
    }
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
    }
    .stButton>button {
        border-radius: 10px;
        background-color: #0071e3;
        color: white;
        font-weight: bold;
        padding: 0.6em 1.2em;
        border: none;
    }
    .stButton>button:hover {
        background-color: #005bb5;
        color: #ffffff;
    }
    .stExpander>summary {
        font-size: 1.1rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# 🧠 ฟังก์ชันแปลงค่าปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# 🔐 เชื่อม Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# 🧊 session_state เริ่มต้น
for key in ["cart", "search_items", "quantities", "paid_input", "sale_complete"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["cart", "search_items"] else {} if key == "quantities" else 0.0 if key == "paid_input" else False

if st.session_state.sale_complete:
    st.session_state.update({"cart": [], "search_items": [], "quantities": {}, "paid_input": 0.0, "sale_complete": False})
    st.success("✅ ขายเสร็จแล้ว รีเซ็ตข้อมูลแล้ว")

# 🧊 Header
st.title("🧊 ร้านเจริญค้า")
st.subheader("ระบบขายสินค้าแบบมืออาชีพ")

# 🔍 ค้นหาและเลือกสินค้า
product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("🔍 เลือกสินค้าที่ต้องการขาย", product_names, default=st.session_state["search_items"], key="search_items")

# 🔢 แสดงจำนวนและคงเหลือ
for p in st.session_state["search_items"]:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1

    row = df[df["ชื่อสินค้า"] == p]
    stock = safe_int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
    color = "red" if stock < 3 else "black"

    cols = st.columns([3, 1, 1])
    with cols[0]:
        st.markdown(f"**{p}**<br><span style='color:{color}'>คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)
    with cols[1]:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    with cols[2]:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1

    st.markdown(f"🔢 จำนวน: **{st.session_state.quantities[p]}**")

if st.button("🛒 เพิ่มลงตะกร้า"):
    for p in st.session_state["search_items"]:
        qty = st.session_state.quantities[p]
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มเรียบร้อย")

# 🧾 รายการตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price = 0.0
    total_profit = 0.0

    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
        subtotal = qty * price
        profit = qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.info(f"💵 รวมเงิน: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)

    if st.session_state.paid_input >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("💸 เงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            idx = index + 2
            new_out = safe_int(df.at[index, "ออก"]) + qty
            new_left = safe_int(df.at[index, "คงเหลือในตู้"]) - qty
            worksheet.update_cell(idx, df.columns.get_loc("ออก") + 1, new_out)
            worksheet.update_cell(idx, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

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
    restock_qty = st.number_input("จำนวน", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติม"):
        index = df[df["ชื่อสินค้า"] == restock_item].index[0]
        idx = index + 2
        new_in = safe_int(df.at[index, "เข้า"]) + restock_qty
        new_left = safe_int(df.at[index, "คงเหลือในตู้"]) + restock_qty
        worksheet.update_cell(idx, df.columns.get_loc("เข้า") + 1, new_in)
        worksheet.update_cell(idx, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
        st.success(f"✅ เติม {restock_item} แล้ว")

# ✏️ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_select")
    index = df[df["ชื่อสินค้า"] == edit_item].index[0]
    idx = index + 2
    row = df.loc[index]
    new_price = st.number_input("ราคาขาย", value=safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุน", value=safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือในตู้", value=safe_int(row["คงเหลือในตู้"]), step=1, key="edit_stock")
    if st.button("💾 บันทึกการแก้ไข"):
        worksheet.update_cell(idx, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(idx, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        worksheet.update_cell(idx, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
        st.success(f"✅ อัปเดต {edit_item} แล้ว")
