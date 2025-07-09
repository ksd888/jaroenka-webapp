import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

st.set_page_config(page_title="ระบบขายสินค้า - ร้านเจริญค้า", layout="wide")

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูลสินค้า
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ฟังก์ชันปลอดภัยสำหรับ int
def safe_int(val):
    try:
        return int(val)
    except:
        return 0

# --- ส่วนของ UI ---

st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

# สร้าง list ชื่อสินค้า
product_names = df["ชื่อสินค้า"].tolist()

# ตะกร้าสินค้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

# --- เลือกสินค้า ---
st.header("🛒 เลือกสินค้า")
selected_products = st.multiselect("🔍 เลือกสินค้าจากชื่อ", options=product_names)

for name in selected_products:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(f"➖", key=f"remove_{name}"):
            st.session_state.cart[name] = max(0, st.session_state.cart.get(name, 0) - 1)
    with col2:
        if st.button(f"➕", key=f"add_{name}"):
            st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1

# เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for name in selected_products:
        st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1

# --- รายการขาย ---
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for name, qty in st.session_state.cart.items():
    if qty > 0:
        row = df[df["ชื่อสินค้า"] == name].iloc[0]
        price = float(row["ราคาขาย"])
        cost = float(row["ต้นทุน"])
        st.markdown(f"- {name} x {qty} = {qty * price:.2f} บาท")
        total += qty * price
        profit += qty * (price - cost)

st.info(f"💰 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# รับเงิน
received = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
change = received - total
if change < 0:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"💵 เงินทอน: {change:.2f} บาท")

# --- ยืนยันการขาย ---
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        if qty > 0:
            row_index = df[df["ชื่อสินค้า"] == name].index[0]
            current_stock = safe_int(df.loc[row_index, "คงเหลือ"])
            df.at[row_index, "คงเหลือ"] = current_stock - qty
            worksheet.update_cell(row_index + 2, df.columns.get_loc("คงเหลือ") + 1, current_stock - qty)

    # บันทึกยอดขาย
    summary_ws = spreadsheet.worksheet("ยอดขาย")
    summary_ws.append_row([now, json.dumps(st.session_state.cart, ensure_ascii=False), total, profit, "drink"])

    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")
    st.session_state.cart = {}

# --- ฟีเจอร์เพิ่มเติม ---

with st.expander("📦 เติมสินค้า"):
    product_to_fill = st.selectbox("เลือกสินค้าที่จะเติม", product_names, key="fill_product")
    qty_to_add = st.number_input("จำนวนที่เติมเข้า", min_value=1, step=1, key="fill_qty")
    if st.button("📥 ยืนยันเติมสินค้า"):
        row_index = df[df["ชื่อสินค้า"] == product_to_fill].index[0]
        current_stock = safe_int(df.loc[row_index, "คงเหลือ"])
        new_stock = current_stock + qty_to_add
        worksheet.update_cell(row_index + 2, df.columns.get_loc("คงเหลือ") + 1, new_stock)
        st.success(f"✅ เติมสินค้า {product_to_fill} จำนวน {qty_to_add} แล้ว (รวม = {new_stock})")

with st.expander("✏️ แก้ไขราคาสินค้า"):
    product_to_edit = st.selectbox("เลือกสินค้าที่จะแก้ไข", product_names, key="edit_product")
    new_price = st.number_input("ราคาขายใหม่", min_value=0.0, step=0.5, key="new_price")
    new_cost = st.number_input("ต้นทุนใหม่", min_value=0.0, step=0.5, key="new_cost")
    if st.button("💾 บันทึกการแก้ไขราคา"):
        row_index = df[df["ชื่อสินค้า"] == product_to_edit].index[0]
        worksheet.update_cell(row_index + 2, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(row_index + 2, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        st.success(f"✅ แก้ไขราคา {product_to_edit} เรียบร้อยแล้ว (ขาย: {new_price}, ต้นทุน: {new_cost})")
