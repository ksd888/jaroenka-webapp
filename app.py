import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ----------------- เชื่อม Google Sheet ------------------
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sh.worksheet("ตู้เย็น")

# ----------------- โหลดข้อมูล ------------------
df = pd.DataFrame(worksheet.get_all_records())

# แปลงคอลัมน์ให้เป็นตัวเลข
for col in ["ราคาขาย", "ต้นทุน", "คงเหลือ", "เข้า", "ออก", "คงเหลือในตู้"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# ----------------- UI ------------------
st.markdown("## 🛒 เลือกสินค้าจากชื่อ")
if "cart" not in st.session_state:
    st.session_state.cart = {}

if "selected_items" not in st.session_state:
    st.session_state.selected_items = []

# เลือกสินค้า
selected_items = st.multiselect("🛒 เลือกสินค้าจากชื่อ", df["ชื่อ"].tolist(), default=st.session_state.selected_items)

for item in selected_items:
    st.markdown(f"### {item}")
    qty_key = f"qty_{item}"
    if qty_key not in st.session_state:
        st.session_state[qty_key] = 0

    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        if st.button("➖", key=f"dec_{item}"):
            if st.session_state[qty_key] > 0:
                st.session_state[qty_key] -= 1
    with col2:
        if st.button("➕", key=f"inc_{item}"):
            st.session_state[qty_key] += 1
    with col3:
        st.write(f"จำนวน: {st.session_state[qty_key]}")

# เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for item in selected_items:
        qty = st.session_state[f"qty_{item}"]
        if qty > 0:
            if item in st.session_state.cart:
                st.session_state.cart[item] += qty
            else:
                st.session_state.cart[item] = qty
            st.session_state[f"qty_{item}"] = 0
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

    # 👉 รีเซ็ตการค้นหาสินค้า
    st.session_state.selected_items = []
    st.experimental_rerun()

# ----------------- แสดงตะกร้า ------------------
if st.session_state.cart:
    st.markdown("### 🧺 ตะกร้าสินค้า")
    total = 0
    profit = 0
    for item, qty in st.session_state.cart.items():
        row = df[df["ชื่อ"] == item].iloc[0]
        price = row["ราคาขาย"]
        cost = row["ต้นทุน"]
        st.markdown(f"- {item} x {qty} = {qty * price:.2f} บาท")
        total += qty * price
        profit += qty * (price - cost)
    st.markdown(f"💰 **ยอดรวม: {total:.2f} บาท**")
    st.markdown(f"📈 **กำไร: {profit:.2f} บาท**")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now()
        for item, qty in st.session_state.cart.items():
            idx = df.index[df["ชื่อ"] == item][0]
            df.at[idx, "ออก"] += qty
            df.at[idx, "คงเหลือในตู้"] = df.at[idx, "คงเหลือ"] + df.at[idx, "เข้า"] - df.at[idx, "ออก"]
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")
        st.session_state.cart = {}

# ----------------- Footer ------------------
st.markdown("---")
st.markdown("สร้างโดย ❤️ ร้านเจริญค้า")
