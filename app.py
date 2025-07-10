import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime

# ตั้งชื่อ session key ล่วงหน้า
if "search_term" not in st.session_state:
    st.session_state["search_term"] = ""

# ตั้งค่าการเชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูล
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# แปลงราคาขาย/ต้นทุนให้เป็นตัวเลขเพื่อป้องกัน Error
df["ราคาขาย"] = pd.to_numeric(df["ราคาขาย"], errors='coerce')
df["ต้นทุน"] = pd.to_numeric(df["ต้นทุน"], errors='coerce')
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# 🔎 ช่องค้นหาสินค้า
search_term = st.text_input("🛒 เลือกสินค้าจากชื่อ", key="search_term")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)]

# แสดงสินค้าที่ค้นเจอ
cart = {}
for index, row in filtered_df.iterrows():
    st.markdown(f"**{row['ชื่อสินค้า']}**")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("-", key=f"minus_{index}"):
            cart[row["ชื่อสินค้า"]] = max(cart.get(row["ชื่อสินค้า"], 0) - 1, 0)
    with col2:
        if st.button("+", key=f"plus_{index}"):
            cart[row["ชื่อสินค้า"]] = cart.get(row["ชื่อสินค้า"], 0) + 1
    with col3:
        st.write(f"จำนวน: {cart.get(row['ชื่อสินค้า'], 0)}")

# ปุ่มยืนยัน
if st.button("✅ ยืนยันการขาย"):
    total_price = 0
    total_profit = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for product, qty in cart.items():
        row = df[df["ชื่อสินค้า"] == product].iloc[0]
        price = row["ราคาขาย"]
        cost = row["ต้นทุน"]
        profit = (price - cost) * qty
        total = price * qty
        total_price += total
        total_profit += profit
        spreadsheet.worksheet("ยอดขาย").append_row(
            [now, product, qty, price, cost, total, profit, "drink"]
        )
        # อัปเดตจำนวนออก
        idx = df[df["ชื่อสินค้า"] == product].index[0]
        out_val = df.loc[idx, "ออก"]
        if out_val == "":
            out_val = 0
        worksheet.update_cell(idx + 2, df.columns.get_loc("ออก") + 1, int(out_val) + qty)
        # คำนวณคงเหลือใหม่
        old_val = df.loc[idx, "เข้า"]
        remain = int(old_val) - int(out_val) - qty
        worksheet.update_cell(idx + 2, df.columns.get_loc("คงเหลือ") + 1, remain)

    st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")
    
    # ✅ เคลียร์ช่องค้นหา
    st.session_state["search_term"] = ""
