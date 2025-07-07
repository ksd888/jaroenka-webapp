import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2 import service_account
from datetime import datetime

# ✅ โหลด service account จาก secrets
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# ✅ เชื่อมต่อ Google Sheet
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
worksheet = spreadsheet.worksheet("ตู้เย็น")

# ✅ โหลดข้อมูลจากชีท
data = worksheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()  # ลบช่องว่างชื่อคอลัมน์

st.title("🧊 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# ✅ ค้นหาสินค้า
search_query = st.text_input("🔍 ค้นหาสินค้า")
if search_query:
    df_filtered = df[df["ชื่อสินค้า"].str.contains(search_query, case=False, na=False)]
else:
    df_filtered = df.copy()

st.dataframe(df_filtered, use_container_width=True)

# ✅ เลือกสินค้า
selected_item = st.selectbox("🛒 เลือกสินค้าที่ต้องการจัดการ", df["ชื่อสินค้า"].unique())

# หาค่าของสินค้านั้น ๆ
item_row = df[df["ชื่อสินค้า"] == selected_item].iloc[0]
คงเหลือ = item_row["คงเหลือ"]
ราคาขาย = item_row["ราคาขาย"]
ต้นทุน = item_row["ต้นทุน"]
กำไรต่อหน่วย = ราคาขาย - ต้นทุน

# ✅ ฟีเจอร์ขายสินค้า
sell_qty = st.number_input("จำนวนที่ขาย", min_value=0, step=1)
if st.button("✅ ขายสินค้า"):
    df.loc[df["ชื่อสินค้า"] == selected_item, "ออก"] += sell_qty
    df.loc[df["ชื่อสินค้า"] == selected_item, "คงเหลือ"] -= sell_qty
    st.success(f"ขาย {selected_item} ออก {sell_qty} ชิ้น")

# ✅ ฟีเจอร์เติมสินค้า
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1)
if st.button("➕ เติมสต๊อก"):
    df.loc[df["ชื่อสินค้า"] == selected_item, "เข้า"] += add_qty
    df.loc[df["ชื่อสินค้า"] == selected_item, "คงเหลือ"] += add_qty
    st.success(f"เติม {selected_item} เข้า {add_qty} ชิ้น")

# ✅ ฟีเจอร์แก้ไขจำนวนคงเหลือ
new_stock = st.number_input("ปรับจำนวนคงเหลือ", min_value=0, step=1, value=int(คงเหลือ))
if st.button("✏️ แก้ไขจำนวนคงเหลือ"):
    df.loc[df["ชื่อสินค้า"] == selected_item, "คงเหลือ"] = new_stock
    st.success(f"แก้ไขคงเหลือของ {selected_item} เป็น {new_stock}")

# ✅ ปุ่มบันทึกกลับ Google Sheet
if st.button("📤 บันทึกยอดขายกลับไป Google Sheet"):
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.success("บันทึกข้อมูลกลับไปยัง Google Sheet สำเร็จแล้ว!")

# ✅ แสดงกำไรสุทธิรวม
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]
df["กำไร"] = df["ออก"] * df["กำไรต่อหน่วย"]
total_profit = df["กำไร"].sum()
total_sales = (df["ออก"] * df["ราคาขาย"]).sum()

st.markdown("---")
st.subheader("📊 สรุปยอดรวมทั้งหมด")
st.markdown(f"**💰 กำไรสุทธิรวม:** {total_profit:,.2f} บาท")
st.markdown(f"**🧾 ยอดขายรวม:** {total_sales:,.2f} บาท")
