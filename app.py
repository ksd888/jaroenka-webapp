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

# ตรวจสอบว่าคอลัมน์สำคัญมีครบ
expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing_columns = [col for col in expected_columns if col not in data.columns]
if missing_columns:
    st.error(f"❌ ขาดคอลัมน์ในชีท: {missing_columns}")
    st.stop()

# แปลงชนิดข้อมูลให้ถูกต้อง
data["เข้า"] = pd.to_numeric(data["เข้า"], errors="coerce").fillna(0).astype(int)
data["ออก"] = pd.to_numeric(data["ออก"], errors="coerce").fillna(0).astype(int)
data["คงเหลือในตู้"] = pd.to_numeric(data["คงเหลือในตู้"], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# แสดงตารางสินค้า
st.subheader("📋 รายการสินค้า")
st.dataframe(data)

# แก้ไขจำนวนสินค้า
st.subheader("✏️ แก้ไขจำนวนสินค้า")
edit_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="edit")
new_stock = st.number_input("จำนวนใหม่", min_value=0, step=1)
if st.button("📌 อัปเดตจำนวน"):
    idx = data[data["ชื่อสินค้า"] == edit_name].index[0]
    data.at[idx, "คงเหลือในตู้"] = new_stock
    st.success(f"✅ อัปเดต {edit_name} = {new_stock}")

# เติมสต๊อก
st.subheader("➕ เติมสินค้าเข้าตู้")
add_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add")
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("✅ เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == add_name].index[0]
    data.at[idx, "เข้า"] += add_qty
    st.success(f"✅ เติม {add_name} +{add_qty}")

# ขายสินค้า
st.subheader("🛒 ขายสินค้า")
sell_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="sell")
sell_qty = st.number_input("จำนวนที่ขาย", min_value=0, step=1, key="sell_qty")
if st.button("💰 บันทึกการขาย"):
    idx = data[data["ชื่อสินค้า"] == sell_name].index[0]
    if data.at[idx, "คงเหลือในตู้"] >= sell_qty:
        data.at[idx, "ออก"] += sell_qty
        st.success(f"✅ ขาย {sell_name} -{sell_qty}")
    else:
        st.error(f"❌ สินค้าในตู้ไม่พอขาย ({data.at[idx, 'คงเหลือในตู้']} เหลืออยู่)")

# คำนวณผลรวม
data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

# แสดงยอดรวม
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.subheader("📊 สรุปยอดขายวันนี้")
st.write(f"🧾 ยอดขายรวม: {total_sales:,.2f} บาท")
st.write(f"💸 กำไรรวม: {total_profit:,.2f} บาท")

# บันทึกยอดขายลงชีท "ยอดขาย"
if st.button("📝 บันทึกยอดขายไปยังชีทยอดขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in data.iterrows():
        if row["ออก"] > 0:
            sheet_sales.append_row([
                now,
                row["ชื่อสินค้า"],
                int(row["ออก"]),
                float(row["ราคาขาย"]),
                float(row["ต้นทุน"]),
                float(row["กำไรต่อหน่วย"]),
                float(row["กำไร"])
            ])
    st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

# อัปเดตกลับชีทหลัก
if st.button("💾 อัปเดตกลับชีทหลัก"):
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("✅ อัปเดตกลับชีทหลักสำเร็จ")
