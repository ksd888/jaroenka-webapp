import streamlit as st
import gspread
import datetime
import pandas as pd
from google.oauth2.service_account import Credentials

# ✅ ฟังก์ชันแปลงข้อมูลปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# ✅ โหลดข้อมูลจากชีท
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ✅ รีเฟรชอัตโนมัติหากตั้งค่าไว้
if st.session_state.get("force_rerun", False):
    st.session_state["force_rerun"] = False
    st.experimental_rerun()

# ✅ กำหนดค่าเริ่มต้น
if "cart" not in st.session_state: st.session_state.cart = []
if "selected_products" not in st.session_state: st.session_state.selected_products = []
if "paid_input" not in st.session_state: st.session_state.paid_input = 0.0

# ✅ ส่วนแสดงผล
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names, default=st.session_state.selected_products)

for p in selected:
    qty_key = f"qty_{p}"
    if qty_key not in st.session_state:
        st.session_state[qty_key] = 1
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**{p}**")
    with col2:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state[qty_key] = max(1, st.session_state[qty_key] - 1)
    with col3:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state[qty_key] += 1

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_int(st.session_state[f"qty_{p}"])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# ✅ แสดงตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price = 0
    total_profit = 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        subtotal = price * qty
        profit = (price - cost) * qty
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

        # ✅ เคลียร์ตะกร้าและตั้งให้รีเฟรชรอบถัดไป
        st.session_state.cart = []
        st.session_state.selected_products = []
        st.session_state.paid_input = 0.0
        for p in product_names:
            qty_key = f"qty_{p}"
            if qty_key in st.session_state:
                del st.session_state[qty_key]

        st.session_state["force_rerun"] = True
        st.stop()

# ✅ เติมสินค้า
with st.expander("📥 เติมสินค้า"):
    for p in product_names:
        qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}")
        if st.button(f"📥 ยืนยันเติม {p}", key=f"เติมbtn_{p}"):
            index = df[df["ชื่อสินค้า"] == p].index[0]
            idx_in_sheet = index + 2
            row = df.loc[index]
            new_in = safe_int(row["เข้า"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) + qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
            st.success(f"✅ เติม {p} แล้ว")

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names)
    index = df[df["ชื่อสินค้า"] == edit_item].index[0]
    idx_in_sheet = index + 2
    row = df.loc[index]
    new_price = st.number_input("ราคาขาย", value=safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุน", value=safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือในตู้", value=safe_int(row["คงเหลือในตู้"]), key="edit_stock")
    if st.button("💾 บันทึกการแก้ไข"):
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
        st.success(f"✅ อัปเดต {edit_item} แล้ว")
