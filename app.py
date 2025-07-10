import streamlit as st
import gspread
import datetime
import pandas as pd
from google.oauth2.service_account import Credentials

# ✅ ตั้งค่าการเชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

sheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# ✅ ฟังก์ชันปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ โหลดข้อมูล
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ✅ ตัวแปรเริ่มต้น
if "cart" not in st.session_state:
    st.session_state.cart = []
if "paid_input" not in st.session_state:
    st.session_state.paid_input = 0.0

st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

# ✅ เลือกสินค้า
product_names = df["ชื่อสินค้า"].tolist()
selected_products = st.multiselect("เลือกสินค้า", product_names)

for p in selected_products:
    if f"qty_{p}" not in st.session_state:
        st.session_state[f"qty_{p}"] = 1
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**{p}**")
    with col2:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state[f"qty_{p}"] = max(1, st.session_state[f"qty_{p}"] - 1)
    with col3:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state[f"qty_{p}"] += 1

if st.button("🛒 เพิ่มเข้าตะกร้า"):
    for p in selected_products:
        qty = safe_int(st.session_state[f"qty_{p}"])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("เพิ่มสินค้าลงตะกร้าแล้ว")

# ✅ แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 รายการขาย")
    total_price = 0.0
    total_profit = 0.0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        subtotal = qty * price
        profit = qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")
    st.info(f"💵 รวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
    if st.session_state.paid_input >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            idx_in_sheet = index + 2
            out_cell = worksheet.cell(idx_in_sheet, df.columns.get_loc("ออก") + 1)
            left_cell = worksheet.cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1)
            new_out = safe_int(out_cell.value) + qty
            new_left = safe_int(left_cell.value) - qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

        summary_ws.append_row([
            now,
            ", ".join([f"{item} x {qty}" for item, qty in st.session_state.cart]),
            total_price,
            total_profit,
            st.session_state.paid_input,
            st.session_state.paid_input - total_price,
            "drink"
        ])

        # ✅ รีเซ็ต
        st.session_state.cart = []
        st.session_state.paid_input = 0.0
        for p in product_names:
            qty_key = f"qty_{p}"
            if qty_key in st.session_state:
                del st.session_state[qty_key]
        st.success("✅ บันทึกเรียบร้อยและรีเซ็ตตะกร้าแล้ว")

# ✅ เติมสินค้า
with st.expander("📥 เติมสินค้า"):
    for p in product_names:
        qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}")
        if qty > 0:
            index = df[df["ชื่อสินค้า"] == p].index[0]
            idx_in_sheet = index + 2
            current_in = safe_int(df.loc[index, "เข้า"])
            current_stock = safe_int(df.loc[index, "คงเหลือในตู้"])
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, current_in + qty)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, current_stock + qty)
            st.success(f"✅ เติม {p} แล้ว")
