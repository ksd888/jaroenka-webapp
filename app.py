import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2 import service_account

# ===== 1. Authen Google Sheet =====
raw_secrets = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
raw_secrets["private_key"] = raw_secrets["private_key"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(
    raw_secrets,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet = spreadsheet.worksheet("ตู้เย็น")
sales_sheet = spreadsheet.worksheet("ยอดขาย")

# ===== 2. Load Data =====
data = pd.DataFrame(sheet.get_all_records())

st.title("📦 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# ===== 3. ค้นหาสินค้า =====
search = st.text_input("🔍 ค้นหาชื่อสินค้า", "")
filtered = data[data["ชื่อสินค้า"].str.contains(search, case=False, na=False)] if search else data

# ===== 4. แสดงสินค้าและปุ่มจัดการ =====
for i, row in filtered.iterrows():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}** (คงเหลือ: {row['คงเหลือในตู้']})")
    with col2:
        if st.button("🛒 ขาย", key=f"sell_{i}"):
            data.at[i, "ออก"] += 1
    with col3:
        if st.button("➕ เติม", key=f"fill_{i}"):
            data.at[i, "เข้า"] += 1
    with col4:
        if st.button("✏️ แก้ไข", key=f"edit_{i}"):
            new_value = st.number_input("ระบุจำนวนใหม่", min_value=0, value=row["คงเหลือในตู้"], key=f"new_{i}")
            if st.button("✅ บันทึก", key=f"save_{i}"):
                data.at[i, "คงเหลือในตู้"] = new_value

# ===== 5. คำนวณคงเหลือและกำไร =====
data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

# ===== 6. ปุ่มบันทึกยอดขายไปยัง Sheet "ยอดขาย" =====
if st.button("💾 บันทึกยอดขายวันนี้"):
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in data.iterrows():
        if row["ออก"] > 0:
            sales_sheet.append_row([
                today,
                row["ชื่อสินค้า"],
                row["ออก"],
                row["ราคาขาย"],
                row["ต้นทุน"],
                row["กำไรต่อหน่วย"],
                row["กำไร"]
            ])
    st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

# ===== 7. บันทึกข้อมูลกลับไปที่ชีท "ตู้เย็น" =====
sheet.update([data.columns.values.tolist()] + data.values.tolist())
