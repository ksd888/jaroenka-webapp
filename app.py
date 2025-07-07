import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

# โหลด credentials จาก secrets.toml
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")

# โหลดข้อมูลชีทหลัก
sheet_main = spreadsheet.worksheet("ตู้เย็น")
df = pd.DataFrame(sheet_main.get_all_records())

# โหลดหรือเตรียมชีท "ยอดขาย"
try:
    sheet_sales = spreadsheet.worksheet("ยอดขาย")
except gspread.exceptions.WorksheetNotFound:
    sheet_sales = spreadsheet.add_worksheet(title="ยอดขาย", rows="1000", cols="20")
    sheet_sales.append_row(["วันที่", "ชื่อสินค้า", "จำนวนที่ขาย", "ราคาขายต่อหน่วย", "กำไรต่อหน่วย", "ยอดขายรวม", "กำไรรวม"])

# ส่วน UI
st.title("💼 ระบบขายสินค้าตู้เย็น เจริญค้า")

# ค้นหา
search = st.text_input("🔍 ค้นหาชื่อสินค้า")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]

for idx, row in filtered_df.iterrows():
    col1, col2, col3, col4 = st.columns([3, 1.2, 1.2, 1.5])
    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}**")
    with col2:
        qty = st.number_input(f"ขาย {row['ชื่อสินค้า']}", min_value=0, step=1, key=f"qty_{idx}")
    with col3:
        if st.button("📦 ขาย", key=f"sell_{idx}") and qty > 0:
            # คำนวณและอัปเดตในชีทหลัก
            new_stock = max(0, row["คงเหลือ"] - qty)
            sheet_main.update_cell(idx + 2, df.columns.get_loc("คงเหลือ") + 1, new_stock)

            # เพิ่มในชีทยอดขาย
            profit_per_unit = row["ราคาขาย"] - row["ต้นทุน"]
            total_sale = qty * row["ราคาขาย"]
            total_profit = qty * profit_per_unit
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet_sales.append_row([now, row["ชื่อสินค้า"], qty, row["ราคาขาย"], profit_per_unit, total_sale, total_profit])
            st.success(f"✅ ขาย {row['ชื่อสินค้า']} จำนวน {qty} ชิ้น เรียบร้อยแล้ว")

    with col4:
        add = st.number_input(f"เติม {row['ชื่อสินค้า']}", min_value=0, step=1, key=f"add_{idx}")
        if st.button("🔄 เติมสต๊อก", key=f"addbtn_{idx}") and add > 0:
            updated_stock = row["คงเหลือ"] + add
            sheet_main.update_cell(idx + 2, df.columns.get_loc("คงเหลือ") + 1, updated_stock)
            st.success(f"✅ เติมสต๊อก {row['ชื่อสินค้า']} เพิ่ม {add} ชิ้น")

# ✅ ปุ่มบันทึกยอดขายแยกอยู่แล้วใน `sheet_sales` ตามที่ร้องขอ
