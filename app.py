import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime

# ✅ อ่าน service account จาก secrets + แก้ private_key
raw_key = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
raw_key["private_key"] = raw_key["private_key"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(
    raw_key,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)

# ✅ เชื่อมต่อ Google Sheet
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
main_sheet = spreadsheet.worksheet("ตู้เย็น")
log_sheet = spreadsheet.worksheet("ยอดขาย")

# ✅ ดึงข้อมูลตารางหลัก
data = pd.DataFrame(main_sheet.get_all_records())

st.title("📦 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# ✅ แสดงรายการสินค้า
for i, row in data.iterrows():
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}**")
    with col2:
        if col2.button("🛒 ขาย", key=f"sell_{i}"):
            data.at[i, "ออก"] += 1
            st.success(f"ขาย {row['ชื่อสินค้า']} 1 ชิ้น")

    with col3:
        if col3.button("➕ เติม", key=f"add_{i}"):
            data.at[i, "เข้า"] += 1
            st.success(f"เติมสต๊อก {row['ชื่อสินค้า']} 1 ชิ้น")

    with col4:
        if col4.button("✏️ แก้ไข", key=f"edit_{i}"):
            new_val = st.number_input(f"ใส่จำนวนใหม่ของ \"{row['ชื่อสินค้า']}\"", min_value=0, value=int(row["คงเหลือในตู้"]), key=f"edit_input_{i}")
            if st.button(f"ยืนยันการแก้ไข {row['ชื่อสินค้า']}", key=f"confirm_edit_{i}"):
                data.at[i, "คงเหลือในตู้"] = new_val
                st.success(f"แก้ไขคงเหลือของ {row['ชื่อสินค้า']} เป็น {new_val}")

    # ✅ อัปเดตคงเหลืออัตโนมัติ
    data.at[i, "คงเหลือในตู้"] = data.at[i, "คงเหลือในตู้"] + data.at[i, "เข้า"] - data.at[i, "ออก"]
    data.at[i, "กำไร"] = data.at[i, "ออก"] * data.at[i, "กำไรต่อหน่วย"]

# ✅ ปุ่มบันทึกยอดขาย
if st.button("📤 บันทึกยอดขายลง Google Sheet"):
    today = datetime.now().strftime("%Y-%m-%d")
    records_to_save = []

    for _, row in data.iterrows():
        if row["ออก"] > 0:
            records_to_save.append([
                today,
                row["ชื่อสินค้า"],
                int(row["ออก"]),
                float(row["กำไรต่อหน่วย"]),
                float(row["กำไร"]),
                float(row["ราคาขาย"]),
                float(row["ต้นทุน"]),
            ])

    if records_to_save:
        log_sheet.append_rows(records_to_save)
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
    else:
        st.info("ไม่มีรายการที่มีการขาย")

# ✅ อัปเดตข้อมูลตารางหลักกลับไป
main_sheet.update([data.columns.values.tolist()] + data.values.tolist())
