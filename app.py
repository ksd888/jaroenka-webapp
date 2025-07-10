import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ✅ ฟังก์ชันป้องกัน Key ซ้ำ
def safe_key(text):
    return text.replace(" ", "_").replace(".", "_").replace("-", "_")

# ✅ เชื่อม Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GCP_SERVICE_ACCOUNT"], scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
stock_ws = sheet.worksheet("ตู้เย็น")
sales_ws = sheet.worksheet("ยอดขาย")
meta_ws = sheet.worksheet("Meta")

# ✅ โหลดข้อมูลสินค้า
df = pd.DataFrame(stock_ws.get_all_records())

# ✅ โหลดวันที่ล่าสุดใน Meta
last_date = meta_ws.acell("B1").value
now_date = datetime.now().strftime("%Y-%m-%d")
if now_date != last_date:
    stock_ws.batch_update([{
        "range": f"G2:G{len(df)+1}",  # อัปเดตคอลัมน์เข้า
        "values": [[0]] * len(df)
    }, {
        "range": f"H2:H{len(df)+1}",  # อัปเดตคอลัมน์ออก
        "values": [[0]] * len(df)
    }])
    meta_ws.update("B1", [[now_date]])

# ✅ session_state ตะกร้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

# ✅ ระบบค้นหาและเลือกสินค้า
selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", df["ชื่อ"].tolist())

# ✅ เพิ่มลดจำนวนสินค้าในตะกร้า
for p in selected:
    if p not in st.session_state.cart:
        st.session_state.cart[p] = 1

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("-", key=f"sub_{safe_key(p)}"):
            st.session_state.cart[p] = max(1, st.session_state.cart[p] - 1)
    with col2:
        st.markdown(f"**{p}** x {st.session_state.cart[p]}")
    with col3:
        if st.button("+", key=f"add_{safe_key(p)}"):
            st.session_state.cart[p] += 1

# ✅ แสดงตะกร้าสินค้า
st.markdown("🧾 **รายการขาย**")
total = 0
profit = 0
for p, qty in st.session_state.cart.items():
    row = df[df["ชื่อ"] == p].iloc[0]
    price = float(row["ราคาขาย"])
    cost = float(row["ต้นทุน"])
    st.write(f"- {p} x {qty} = {price*qty:.2f} บาท")
    total += price * qty
    profit += (price - cost) * qty

st.info(f"💰 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# ✅ ช่องรับเงิน
paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
if paid < total:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"✅ ยืนยันการขาย")

# ✅ ปุ่มบันทึกยอดขาย
if st.button("🧾 ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p, qty in st.session_state.cart.items():
        row_idx = df[df["ชื่อ"] == p].index[0] + 2  # +2 because sheet index starts at 1 with header
        stock_ws.update_cell(row_idx, 8, int(df.loc[row_idx-2, "ออก"]) + qty)
        stock_ws.update_cell(row_idx, 9, int(df.loc[row_idx-2, "คงเหลือ"]) - qty)
        sales_ws.append_row([now, p, qty, float(df.loc[row_idx-2, "ราคาขาย"]),
                             float(df.loc[row_idx-2, "ต้นทุน"]),
                             float(df.loc[row_idx-2, "ราคาขาย"]) * qty,
                             (float(df.loc[row_idx-2, "ราคาขาย"]) - float(df.loc[row_idx-2, "ต้นทุน"])) * qty,
                             "drink"])
    st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
    st.session_state.cart = {}
    st.experimental_rerun()

# ✅ เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    for p in df["ชื่อ"]:
        qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{safe_key(p)}")
        if qty > 0:
            row_idx = df[df["ชื่อ"] == p].index[0] + 2
            stock_ws.update_cell(row_idx, 7, int(df.loc[row_idx-2, "เข้า"]) + qty)
            stock_ws.update_cell(row_idx, 9, int(df.loc[row_idx-2, "คงเหลือ"]) + qty)
            st.success(f"✅ เติม {p} แล้ว")

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    item = st.selectbox("เลือกสินค้า", df["ชื่อ"])
    col1, col2 = st.columns(2)
    with col1:
        new_price = st.number_input("ราคาขายใหม่", value=float(df[df["ชื่อ"] == item]["ราคาขาย"].values[0]))
    with col2:
        new_cost = st.number_input("ต้นทุนใหม่", value=float(df[df["ชื่อ"] == item]["ต้นทุน"].values[0]))
    if st.button("💾 บันทึกการแก้ไข"):
        row_idx = df[df["ชื่อ"] == item].index[0] + 2
        stock_ws.update_cell(row_idx, 3, new_price)
        stock_ws.update_cell(row_idx, 4, new_cost)
        st.success("✅ แก้ไขเรียบร้อยแล้ว")
        st.experimental_rerun()
