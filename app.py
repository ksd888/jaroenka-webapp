import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ✅ ฟังก์ชันปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# ✅ โหลดข้อมูล
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ✅ Session State เริ่มต้น
if "cart" not in st.session_state:
    st.session_state.cart = []
if "paid" not in st.session_state:
    st.session_state.paid = 0.0
if "selected" not in st.session_state:
    st.session_state.selected = []

# ✅ Header
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

# ✅ ค้นหาและเลือกสินค้า
product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("🔍 ค้นหาสินค้า", product_names, default=st.session_state.selected)

for p in selected:
    key = f"qty_{p}"
    if key not in st.session_state:
        st.session_state[key] = 1
    cols = st.columns([3, 1, 1])
    cols[0].write(f"**{p}**")
    if cols[1].button("➖", key=f"dec_{p}"):
        st.session_state[key] = max(1, st.session_state[key] - 1)
    if cols[2].button("➕", key=f"inc_{p}"):
        st.session_state[key] += 1

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_int(st.session_state[f"qty_{p}"])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.session_state.selected = []
    st.success("✅ เพิ่มลงตะกร้าแล้ว")

# ✅ ตะกร้า
if st.session_state.cart:
    st.subheader("🛒 รายการขาย")
    total_price, total_profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        subtotal = qty * price
        profit = qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total_price:.2f} | 🟢 กำไร: {total_profit:.2f}")
    st.session_state.paid = st.number_input("💰 รับเงิน", value=st.session_state.paid, step=1.0)
    if st.session_state.paid >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid - total_price:.2f}")
    else:
        st.warning("💸 รับเงินยังไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item].index[0]
            sheet_row = idx + 2
            current_out = safe_int(df.at[idx, "ออก"])
            current_left = safe_int(df.at[idx, "คงเหลือในตู้"])
            worksheet.update_cell(sheet_row, df.columns.get_loc("ออก") + 1, current_out + qty)
            worksheet.update_cell(sheet_row, df.columns.get_loc("คงเหลือในตู้") + 1, current_left - qty)

        summary_ws.append_row([
            now,
            ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
            total_price,
            total_profit,
            st.session_state.paid,
            st.session_state.paid - total_price,
            "drink"
        ])

        st.session_state.cart = []
        st.session_state.paid = 0.0
        st.session_state.selected = []
        for p in product_names:
            st.session_state.pop(f"qty_{p}", None)
        st.success("✅ ขายเสร็จแล้ว รีเซ็ตตะกร้าเรียบร้อย")

# ✅ เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    for p in product_names:
        qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}")
        if qty > 0:
            idx = df[df["ชื่อสินค้า"] == p].index[0]
            sheet_row = idx + 2
            new_in = safe_int(df.at[idx, "เข้า"]) + qty
            new_left = safe_int(df.at[idx, "คงเหลือในตู้"]) + qty
            worksheet.update_cell(sheet_row, df.columns.get_loc("เข้า") + 1, new_in)
            worksheet.update_cell(sheet_row, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
            st.success(f"เติม {p} แล้ว {qty} ชิ้น")
            st.session_state[f"เติม_{p}"] = 0

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    product = st.selectbox("เลือกสินค้า", product_names, key="แก้ไข")
    idx = df[df["ชื่อสินค้า"] == product].index[0]
    sheet_row = idx + 2
    price = st.number_input("ราคาขาย", value=safe_float(df.at[idx, "ราคาขาย"]), key="แก้ราคา")
    cost = st.number_input("ต้นทุน", value=safe_float(df.at[idx, "ต้นทุน"]), key="แก้ต้นทุน")
    stock = st.number_input("คงเหลือในตู้", value=safe_int(df.at[idx, "คงเหลือในตู้"]), key="แก้คงเหลือ")
    if st.button("💾 บันทึกการแก้ไข"):
        worksheet.update_cell(sheet_row, df.columns.get_loc("ราคาขาย") + 1, price)
        worksheet.update_cell(sheet_row, df.columns.get_loc("ต้นทุน") + 1, cost)
        worksheet.update_cell(sheet_row, df.columns.get_loc("คงเหลือในตู้") + 1, stock)
        st.success(f"อัปเดต {product} เรียบร้อยแล้ว")
