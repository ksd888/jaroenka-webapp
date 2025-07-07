import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

# -----------------------
# ✅ ตั้งค่า Credentials
# -----------------------
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
main_sheet = spreadsheet.worksheet("ตู้เย็น")
sales_sheet = spreadsheet.worksheet("ยอดขาย")

# -----------------------
# ✅ โหลดข้อมูลและเตรียม DataFrame
# -----------------------
data = pd.DataFrame(main_sheet.get_all_records())

# แปลงคอลัมน์เป็นตัวเลข
numeric_cols = ["ราคาขาย", "ต้นทุน", "กำไรต่อหน่วย", "คงเหลือในตู้", "เข้า", "ออก", "กำไร"]
for col in numeric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)

# -----------------------
# ✅ UI: ค้นหา + แสดงตารางสินค้า
# -----------------------
st.title("📦 จัดการสินค้าตู้เย็น - เจริญค้า")

search = st.text_input("🔍 ค้นหาชื่อสินค้า")
filtered = data[data["ชื่อสินค้า"].str.contains(search, case=False)] if search else data

# -----------------------
# ✅ ปุ่มขายสินค้า / เติมสต๊อก / แก้ไข
# -----------------------
for i, row in filtered.iterrows():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}**")
    with col2:
        if st.button("ขาย", key=f"sell_{i}"):
            data.at[i, "ออก"] += 1
            data.at[i, "กำไร"] += data.at[i, "กำไรต่อหน่วย"]
    with col3:
        if st.button("เติม", key=f"add_{i}"):
            data.at[i, "เข้า"] += 1
    with col4:
        new_qty = st.number_input("แก้ไขจำนวน", min_value=0, value=int(data.at[i, "คงเหลือในตู้"]),
                                  key=f"edit_{i}")
        if new_qty != data.at[i, "คงเหลือในตู้"]:
            data.at[i, "คงเหลือในตู้"] = new_qty

# -----------------------
# ✅ คำนวณคงเหลืออัตโนมัติ
# -----------------------
for i in data.index:
    data.at[i, "คงเหลือในตู้"] = (
        int(data.at[i, "คงเหลือในตู้"]) +
        int(data.at[i, "เข้า"]) -
        int(data.at[i, "ออก"])
    )

# -----------------------
# ✅ ยอดรวมและกำไร
# -----------------------
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.success(f"💰 ยอดขายรวมวันนี้: {total_sales:,} บาท")
st.success(f"📈 กำไรสุทธิ: {total_profit:,} บาท")

# -----------------------
# ✅ ปุ่มบันทึกลง Sheet "ยอดขาย"
# -----------------------
if st.button("📝 บันทึกยอดขายวันนี้"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i, row in data.iterrows():
        if row["ออก"] > 0:
            sales_sheet.append_row([
                now,
                row["ชื่อสินค้า"],
                int(row["ออก"]),
                int(row["ราคาขาย"]),
                int(row["ต้นทุน"]),
                int(row["กำไรต่อหน่วย"]),
                int(row["กำไร"]),
                int(row["ออก"] * row["ราคาขาย"])
            ])
    st.success("✅ บันทึกยอดขายสำเร็จแล้ว")

# -----------------------
# ✅ อัปเดตกลับไปที่ Sheet ตู้เย็น
# -----------------------
main_sheet.update([data.columns.values.tolist()] + data.values.tolist())
