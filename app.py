import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
import json
from datetime import datetime

# ✅ โหลด service account จาก secrets และแปลงเป็น dict
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# ✅ เปิด Google Sheet
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")

# ✅ เปิดชีทหลัก (สินค้า)
worksheet = spreadsheet.worksheet("ตู้เย็น")

# ✅ โหลดข้อมูลจากชีท
data = worksheet.get_all_records()
df = pd.DataFrame(data)

st.title("📦 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# ✅ ปุ่ม: ค้นหา + แสดงสินค้า
search = st.text_input("🔍 ค้นหาสินค้า")
if search:
    filtered_df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]
else:
    filtered_df = df

# ✅ แสดงสินค้าในตาราง พร้อมปุ่ม
for index, row in filtered_df.iterrows():
    st.write(f"**{row['ชื่อสินค้า']}** (คงเหลือ: {row['คงเหลือ']})")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("ขายสินค้า", key=f"sell_{index}"):
            df.at[index, 'คงเหลือ'] = max(0, row['คงเหลือ'] - 1)
            df.at[index, 'ออก'] += 1
    
    with col2:
        if st.button("เติมสต๊อก", key=f"restock_{index}"):
            df.at[index, 'คงเหลือ'] += 1
            df.at[index, 'เข้า'] += 1
    
    with col3:
        new_value = st.number_input("แก้จำนวน", min_value=0, value=row['คงเหลือ'], step=1, key=f"edit_{index}")
        if new_value != row['คงเหลือ']:
            df.at[index, 'คงเหลือ'] = new_value

st.markdown("---")

# ✅ ปุ่มบันทึกกลับ Google Sheet
if st.button("💾 บันทึกยอดขายกลับ Google Sheet"):
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.success("บันทึกเรียบร้อยแล้ว ✅")

# ✅ ปุ่มบันทึกแยกชีท “ยอดขาย”
if st.button("🧾 บันทึกไปยังชีทยอดขาย"):
    sale_sheet = spreadsheet.worksheet("ยอดขาย")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = []

    for index, row in df.iterrows():
        if row['ออก'] > 0:
            summary.append([
                now,
                row['ชื่อสินค้า'],
                row['ออก'],
                row['ราคาขาย'],
                row['ต้นทุน'],
                row['ออก'] * (row['ราคาขาย'] - row['ต้นทุน']),
            ])
    
    if summary:
        sale_sheet.append_rows(summary)
        st.success("บันทึกยอดขายแยกสำเร็จ ✅")
    
