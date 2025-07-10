import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re

# ฟังก์ชันเพื่อจัดการ key ซ้ำ
def safe_key(s):
    return re.sub(r"[^a-zA-Z0-9_]", "_", s)

# ฟังก์ชันแปลง float ปลอดภัย
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# เชื่อมต่อ Google Sheet
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)

gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")

sheet = spreadsheet.worksheet("ตู้เย็น")

# ดึงข้อมูลจาก Google Sheet
data = sheet.get_all_records()

# แปลงข้อมูลเป็น DataFrame
df = pd.DataFrame(data)

# UI
st.title("แอปร้านเจริญค้า 🍧")

# ช่องค้นหา
search = st.text_input("ค้นหาสินค้า 🔍")
filtered_df = df[df["ชื่อ"].str.contains(search, case=False)] if search else df

# แสดงสินค้า
st.subheader("รายการสินค้า")
for i, row in filtered_df.iterrows():
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        st.markdown(f"**{row['ชื่อ']}**")
    with col2:
        qty_key = safe_key(f"qty_{row['ชื่อ']}")
        if qty_key not in st.session_state:
            st.session_state[qty_key] = 1
        if st.button("-", key=safe_key(f"sub_{row['ชื่อ']}")):
            st.session_state[qty_key] = max(1, st.session_state[qty_key] - 1)
        st.write(f"{st.session_state[qty_key]} ชิ้น")
        if st.button("+", key=safe_key(f"add_{row['ชื่อ']}")):
            st.session_state[qty_key] += 1
    with col3:
        if st.button("เพิ่มใส่ตะกร้า 🛒", key=safe_key(f"cart_{row['ชื่อ']}")):
            if "cart" not in st.session_state:
                st.session_state["cart"] = {}
            st.session_state["cart"][row['ชื่อ']] = st.session_state[qty_key]

# ตะกร้าสินค้า
st.subheader("🛍️ ตะกร้าสินค้า")
if "cart" in st.session_state and st.session_state["cart"]:
    total = 0
    for name, qty in st.session_state["cart"].items():
        price = safe_float(df[df["ชื่อ"] == name]["ราคาขาย"].values[0])
        st.write(f"{name}: {qty} x {price} = {qty * price:.2f} บาท")
        total += qty * price

    st.markdown(f"**💰 รวม: {total:.2f} บาท**")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, qty in st.session_state["cart"].items():
            idx = df[df["ชื่อ"] == name].index[0]
            out_cell = f"G{idx + 2}"
            old_out = safe_float(df.at[idx, "ออก"])
            new_out = old_out + qty
            sheet.update(out_cell, [[new_out]])

        st.success("บันทึกการขายเรียบร้อย ✅")
        st.session_state["cart"] = {}
        for key in list(st.session_state.keys()):
            if key.startswith("qty_"):
                st.session_state[key] = 1
        st.experimental_rerun()
else:
    st.info("ยังไม่มีสินค้าถูกเลือกในตะกร้า")

