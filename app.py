import streamlit as st
import datetime
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 🔐 เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# 🧠 ฟังก์ชันช่วยอ่านค่าปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# 📦 โหลดข้อมูลสินค้า
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 🧊 ค่าเริ่มต้น session_state
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

# 🔁 รีเซ็ตเมื่อขายเสร็จ
if st.session_state.sale_complete:
    for key in ["cart", "selected_products", "quantities", "paid_input"]:
        st.session_state[key] = default_session[key]
    st.session_state.sale_complete = False
    st.success("✅ บันทึกยอดขายและรีเซ็ตเรียบร้อยแล้ว")

# 🔍 ค้นหาและเพิ่มสินค้าเข้าตะกร้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names, default=st.session_state.selected_products)
st.session_state.selected_products = selected

for p in selected:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    cols = st.columns([2, 1, 1])
    with cols[0]: st.markdown(f"**{p}**")
    with cols[1]:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    with cols[2]:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 🧾 แสดงตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
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
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2
            new_out = safe_int(row["ออก"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) - qty
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

# 📥 เติมสินค้าแบบปลอดภัย (หลีกเลี่ยง key ซ้ำ)
with st.expander("📦 เติมสินค้า"):
    for i, p in enumerate(product_names):
        qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}_{i}")
        if qty > 0:
            idx = df[df["ชื่อสินค้า"] == p].index[0]
            sheet_row = idx + 2
            new_in = safe_int(df.at[idx, "เข้า"]) + qty
            new_left = safe_int(df.at[idx, "คงเหลือในตู้"]) + qty
            worksheet.update_cell(sheet_row, df.columns.get_loc("เข้า") + 1, new_in)
            worksheet.update_cell(sheet_row, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
            st.success(f"เติม {p} แล้ว {qty} ชิ้น")
            st.session_state[f"เติม_{p}_{i}"] = 0
