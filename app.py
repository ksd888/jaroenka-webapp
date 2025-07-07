
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- SETUP -----------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
JSON_KEYFILE = "speedy-aurora-464900-h3-2ec652a721df.json"  # ชื่อไฟล์ Service Account
SHEET_NAME = "สินค้าตู้เย็นปลีก_GS"
WORKSHEET_NAME = "ตู้เย็น"

# ----------------- GOOGLE SHEET -----------------
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, SCOPE)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
data = sheet.get_all_records()

# ----------------- STREAMLIT UI -----------------
st.set_page_config(page_title="ระบบขายสินค้าตู้เย็น", layout="wide")
st.title("🧊 เจริญค้า - ระบบขายสินค้าตู้เย็น")
search_query = st.text_input("🔍 ค้นหาสินค้า", "")

for row in data:
    name = row["ชื่อสินค้า              ตู้แช่"]
    if search_query.strip() == "" or search_query.lower() in name.lower():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(name)
            st.write(f"💰 ราคาขาย: {row['ราคาขาย']} บาท")
            st.write(f"📦 คงเหลือรวม: {row['คงเหลือ']} | คงเหลือในตู้: {row['คงเหลือในตู้']}")
        with col2:
            if st.button(f"ขาย {name}"):
                try:
                    cell = sheet.find(name)
                    row_idx = cell.row
                    col_out = sheet.find("ออก").col
                    col_stock = sheet.find("คงเหลือ").col
                    col_freezer = sheet.find("คงเหลือในตู้").col

                    current_out = int(sheet.cell(row_idx, col_out).value or 0)
                    current_stock = int(sheet.cell(row_idx, col_stock).value or 0)
                    current_freezer = int(sheet.cell(row_idx, col_freezer).value or 0)

                    sheet.update_cell(row_idx, col_out, current_out + 1)
                    sheet.update_cell(row_idx, col_stock, max(current_stock - 1, 0))
                    sheet.update_cell(row_idx, col_freezer, max(current_freezer - 1, 0))

                    st.success(f"✅ ขาย {name} เรียบร้อยแล้ว")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
