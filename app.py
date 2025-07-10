
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === ฟังก์ชันเสริม ===
def safe_int(value):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# === เชื่อมต่อ Google Sheet ===
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope,
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# === โหลดข้อมูล ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

# === แปลงคอลัมน์ที่ต้องการด้วย safe_int และ safe_float ===
df["ราคาขาย"] = df["ราคาขาย"].apply(safe_float)
df["ต้นทุน"] = df["ต้นทุน"].apply(safe_float)
df["คงเหลือ"] = df["คงเหลือ"].apply(safe_int)
df["ออก"] = df["ออก"].apply(safe_int)

# === UI ค้นหาและขายสินค้า ===
st.title("ขายสินค้า • ร้านเจริญค้า")
search_term = st.text_input("ค้นหาสินค้า")

filtered_df = df[df["ชื่อ"].str.contains(search_term, case=False, na=False)]

cart = []
for index, row in filtered_df.iterrows():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**{row['ชื่อ']}**")
    with col2:
        qty = st.number_input(f"จำนวน ({row['ชื่อ']})", min_value=0, step=1, key=f"qty_{row['ชื่อ']}")
    with col3:
        if st.button("➕ เพิ่ม", key=f"add_{row['ชื่อ']}"):
            if qty > 0:
                cart.append((row["ชื่อ"], qty, row["ราคาขาย"], row["ต้นทุน"]))

if cart:
    st.subheader("🛒 ตะกร้าสินค้า")
    total_price = 0
    total_cost = 0
    for name, qty, price, cost in cart:
        st.markdown(f"- {name} x {qty} = {qty * price:.2f} บาท")
        total_price += qty * price
        total_cost += qty * cost
    st.markdown(f"**รวมทั้งหมด: {total_price:.2f} บาท**")
    st.markdown(f"**กำไรสุทธิ: {total_price - total_cost:.2f} บาท**")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, qty, price, cost in cart:
            idx = df[df["ชื่อ"] == name].index[0]
            old_out = safe_int(df.loc[idx, "ออก"])
            sheet.update_cell(idx + 2, df.columns.get_loc("ออก") + 1, old_out + qty)
            old_balance = safe_int(df.loc[idx, "คงเหลือ"])
            sheet.update_cell(idx + 2, df.columns.get_loc("คงเหลือ") + 1, max(0, old_balance - qty))
        st.success("ขายสินค้าเรียบร้อยแล้ว 🎉")
        st.experimental_rerun()
