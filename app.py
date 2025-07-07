import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# เชื่อมต่อ GCP
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูลจาก Google Sheet
data = pd.DataFrame(sheet_main.get_all_records())

expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing_columns = [col for col in expected_columns if col not in data.columns]
if missing_columns:
    st.error(f"❌ ขาดคอลัมน์ในชีท: {missing_columns}")
    st.stop()

# แปลงชนิดข้อมูล
data["เข้า"] = pd.to_numeric(data["เข้า"], errors="coerce").fillna(0).astype(int)
data["ออก"] = pd.to_numeric(data["ออก"], errors="coerce").fillna(0).astype(int)
data["คงเหลือในตู้"] = pd.to_numeric(data["คงเหลือในตู้"], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# ---------------------
# ✅ ขายหลายรายการพร้อมกัน
# ---------------------
st.subheader("🛒 ขายหลายรายการ")

selected_items = st.multiselect("🔍 ค้นหาและเลือกสินค้าที่ต้องการขาย", data["ชื่อสินค้า"].tolist())
quantities = {}

col1, col2 = st.columns(2)
with col1:
    money_received = st.number_input("💵 เงินที่รับมา (บาท)", min_value=0.0, step=1.0, format="%.2f")

for item in selected_items:
    quantities[item] = st.number_input(f"จำนวน: {item}", min_value=0, step=1, key=f"qty_{item}")

if st.button("💰 ยืนยันการขาย"):
    total_price = 0
    receipt = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in selected_items:
        qty = quantities[item]
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        if data.at[idx, "คงเหลือในตู้"] >= qty:
            price = data.at[idx, "ราคาขาย"]
            cost = data.at[idx, "ต้นทุน"]
            profit_unit = price - cost
            profit_total = profit_unit * qty

            data.at[idx, "ออก"] += qty

            # ใบเสร็จ
            line = f"{item} x{qty} @ {price:.2f} = {price*qty:.2f} บาท"
            receipt.append(line)
            total_price += price * qty

            # บันทึกลง Sheet
            sheet_sales.append_row([
                now,
                item,
                qty,
                price,
                cost,
                profit_unit,
                profit_total,
                "drink"  # สำหรับแยกประเภท
            ])
        else:
            st.error(f"❌ สินค้า {item} คงเหลือไม่พอขาย ({data.at[idx, 'คงเหลือในตู้']})")

    change = money_received - total_price
    st.success("✅ ขายสำเร็จแล้ว")
    
    st.markdown("### 🧾 ใบเสร็จ")
    for line in receipt:
        st.write(line)
    st.write(f"**รวมทั้งหมด:** {total_price:.2f} บาท")
    st.write(f"**เงินรับมา:** {money_received:.2f} บาท")
    st.write(f"**เงินทอน:** {change:.2f} บาท")

    if st.button("🔄 ล้างข้อมูลหลังขาย"):
        st.experimental_rerun()

# ---------------------
# แสดงตารางข้อมูลและกำไร
# ---------------------
st.subheader("📋 รายการสินค้า")
st.dataframe(data)

# ---------------------
# สรุปยอดขาย
# ---------------------
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.subheader("📊 สรุปยอดขายวันนี้")
st.write(f"🧾 ยอดขายรวม: {total_sales:,.2f} บาท")
st.write(f"💸 กำไรรวม: {total_profit:,.2f} บาท")

# ---------------------
# ปุ่มอัปเดตข้อมูลกลับ Google Sheet
# ---------------------
if st.button("💾 อัปเดตกลับชีทหลัก"):
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("✅ อัปเดตกลับชีทหลักสำเร็จ")
