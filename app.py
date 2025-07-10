import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ⛓️ เชื่อมต่อ Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=SCOPE,
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
ws = sheet.worksheet("ตู้เย็น")

# 🔁 โหลดข้อมูล
df = pd.DataFrame(ws.get_all_records())
df["กำไรต่อหน่วย"] = pd.to_numeric(df["ราคาขาย"], errors="coerce") - pd.to_numeric(df["ต้นทุน"], errors="coerce")

# 📦 เตรียมตะกร้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

# 🔍 ค้นหา
search = st.text_input("🔎 ค้นหาสินค้า")
if search:
    filtered = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]
else:
    filtered = df.copy()

# 🛒 เลือกสินค้า
for _, row in filtered.iterrows():
    name = row["ชื่อสินค้า"]
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        if st.button("+", key=f"add_{name}"):
            st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
    with col3:
        if st.button("-", key=f"sub_{name}"):
            if name in st.session_state.cart:
                st.session_state.cart[name] = max(0, st.session_state.cart[name] - 1)
                if st.session_state.cart[name] == 0:
                    del st.session_state.cart[name]

st.divider()
st.markdown("## 🧾 ตะกร้าสินค้า")

total = 0
profit = 0
for name, qty in st.session_state.cart.items():
    item = df[df["ชื่อสินค้า"] == name].iloc[0]
    price = item["ราคาขาย"]
    cost = item["ต้นทุน"]
    st.write(f"{name} x {qty} = {qty * price} บาท")
    total += qty * price
    profit += qty * (price - cost)

st.write(f"💰 **รวมเงิน:** {total} บาท")
money_received = st.number_input("💵 เงินที่รับมา", min_value=0)
if money_received:
    st.write(f"💸 เงินทอน: {money_received - total} บาท")

# ✅ ปุ่มขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        ws.append_row([now, name, qty, total, profit, "drink"])
    st.success("ขายสำเร็จ! ✅")

    # ✅ รีเซ็ตตะกร้า + รีเซ็ตการค้นหา
    st.session_state.cart = {}
    st.session_state["💵 เงินที่รับมา"] = 0
    st.experimental_rerun()

# 🔄 ปุ่ม Undo ล่าสุด
if "last_action" in st.session_state:
    if st.button("↩️ Undo ล่าสุด"):
        st.session_state.cart = st.session_state.last_action.copy()
        st.success("เรียกคืนล่าสุดแล้ว")
else:
    st.session_state.last_action = {}

# 🛠 เติมสินค้า
st.divider()
st.markdown("### ➕ เติมสินค้าเข้า")
for i, row in df.iterrows():
    name = row["ชื่อสินค้า"]
    qty = st.number_input(f"เติม {name}", min_value=0, key=f"เติม_{name}")
    if qty > 0:
        df.at[i, "คงเหลือในตู้"] += qty
        ws.update_cell(i + 2, df.columns.get_loc("คงเหลือในตู้") + 1, df.at[i, "คงเหลือในตู้"])
        st.success(f"เติม {name} แล้ว ✅")
        st.experimental_rerun()
