import streamlit as st
import gspread
import pandas as pd
import json
from google.oauth2 import service_account

# โหลดข้อมูล key จาก secrets.toml
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# เชื่อมต่อ Google Sheets
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
worksheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูลจากชีต
data = worksheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()  # ลบช่องว่างหัวตารางเผื่อมี

# แสดงตารางสินค้า
st.title("📦 จัดการสต๊อกสินค้า - เจริญค้า")
st.dataframe(df)

# เลือกสินค้าที่จะขายหรือเติม
selected_product = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].unique())

if selected_product:
    selected_row = df[df["ชื่อสินค้า"] == selected_product].iloc[0]
    st.write(f"**คงเหลือ:** {selected_row['คงเหลือ']} ชิ้น")

    # ขายสินค้า
    sell_qty = st.number_input("จำนวนที่ขาย", min_value=0, step=1)
    if st.button("✅ ขายสินค้า"):
        new_qty = int(selected_row["คงเหลือ"]) - int(sell_qty)
        if new_qty < 0:
            st.error("❌ สินค้าไม่พอขาย")
        else:
            cell = worksheet.find(selected_product)
            row_num = cell.row
            worksheet.update_cell(row_num, df.columns.get_loc("คงเหลือ") + 1, new_qty)
            st.success(f"✅ ขาย {sell_qty} ชิ้น เรียบร้อยแล้ว")

    # เติมสต๊อก
    add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
    if st.button("➕ เติมสต๊อก"):
        new_qty = int(selected_row["คงเหลือ"]) + int(add_qty)
        cell = worksheet.find(selected_product)
        row_num = cell.row
        worksheet.update_cell(row_num, df.columns.get_loc("คงเหลือ") + 1, new_qty)
        st.success(f"🧊 เติม {add_qty} ชิ้น เรียบร้อยแล้ว")

    # บันทึกยอดขาย (ลงชีทอื่นได้ภายหลัง)
    if st.button("💾 บันทึกยอดขาย"):
        cost = selected_row["ต้นทุน"]
        price = selected_row["ราคาขาย"]
        profit = (price - cost) * sell_qty
        st.info(f"💰 กำไรจากการขาย {sell_qty} ชิ้น = {profit} บาท")
