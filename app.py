import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

st.set_page_config(page_title="ร้านเจริญค้า - ระบบขายสินค้า", layout="centered")

# ใช้ safe float แปลงค่าที่อาจไม่เป็นตัวเลข
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# ทำให้ key ปลอดภัยสำหรับ Streamlit
def safe_key(s):
    return re.sub(r"[^\w\s]", "_", str(s))

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GCP_SERVICE_ACCOUNT"], scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")
sales_sheet = sh.worksheet("ยอดขาย")

# โหลดข้อมูลสินค้า
data = sheet.get_all_records()

# แปลงข้อมูลเป็น DataFrame
df = pd.DataFrame(data)

# แปลงราคาขาย/ต้นทุนให้ปลอดภัย
df["ราคาขาย"] = df["ราคาขาย"].apply(safe_float)
df["ต้นทุน"] = df["ต้นทุน"].apply(safe_float)

# สร้างรายการสินค้าเป็น dict
products = []
for row in df.to_dict(orient="records"):
    products.append({
        "ชื่อ": row.get("ชื่อ", ""),
        "คงเหลือ": safe_float(row.get("คงเหลือ", 0)),
        "ราคาขาย": safe_float(row.get("ราคาขาย", 0)),
        "ต้นทุน": safe_float(row.get("ต้นทุน", 0))
    })

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

# Multi-select ค้นหาสินค้า
selected_names = st.multiselect("🔍 เลือกสินค้าจากชื่อ", [p["ชื่อ"] for p in products])

# แสดงปุ่มเพิ่มสินค้าแต่ละรายการ
st.subheader("🛒 ตะกร้าสินค้า")

if "cart" not in st.session_state:
    st.session_state.cart = {}

for p in products:
    if p["ชื่อ"] in selected_names:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("-", key=f"sub_{safe_key(p['ชื่อ'])}"):
                st.session_state.cart[p["ชื่อ"]] = max(1, st.session_state.cart.get(p["ชื่อ"], 1) - 1)
        with col2:
            qty = st.session_state.cart.get(p["ชื่อ"], 1)
            st.write(f"{p['ชื่อ']} x {qty}")
        with col3:
            if st.button("+", key=f"add_{safe_key(p['ชื่อ'])}"):
                st.session_state.cart[p["ชื่อ"]] = st.session_state.cart.get(p["ชื่อ"], 1) + 1
        st.markdown("---")

# คำนวณยอดรวม
st.subheader("📋 รายการขาย")
total_price = 0
total_cost = 0
for name, qty in st.session_state.cart.items():
    product = next((p for p in products if p["ชื่อ"] == name), None)
    if product:
        line_price = product["ราคาขาย"] * qty
        line_cost = product["ต้นทุน"] * qty
        total_price += line_price
        total_cost += line_cost
        st.write(f"{name} x {qty} = {line_price:.2f} บาท")

st.info(f"💰 ยอดรวม: {total_price:.2f} บาท 🌏 กำไร: {total_price - total_cost:.2f} บาท")

# รับเงินจากลูกค้า
money = st.number_input("💸 รับเงิน", min_value=0.0, value=0.0)
if money < total_price:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    change = money - total_price
    st.success(f"✅ เงินทอน: {change:.2f} บาท")

# ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        product = next((p for p in products if p["ชื่อ"] == name), None)
        if product:
            try:
                idx = df.index[df["ชื่อ"] == name].tolist()[0]
                df.at[idx, "คงเหลือ"] = df.at[idx, "คงเหลือ"] - qty
                sheet.update_cell(idx + 2, df.columns.get_loc("คงเหลือ") + 1, df.at[idx, "คงเหลือ"])
                sales_sheet.append_row([now, name, qty, product["ราคาขาย"], product["ต้นทุน"],
                                        qty * product["ราคาขาย"], qty * product["ต้นทุน"],
                                        qty * (product["ราคาขาย"] - product["ต้นทุน"])])
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {e}")

    st.session_state.cart = {}
    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.experimental_rerun()
