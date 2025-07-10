import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === ฟังก์ชันป้องกัน error ===
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def safe_int(val):
    try:
        return int(val)
    except:
        return 0

def safe_key(name):
    return "".join(c if c.isalnum() else "_" for c in name)

# === เชื่อม Google Sheet ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# === โหลดข้อมูลจากชีท ===
rows = sheet.get_all_records()
products = []
for row in rows:
    products.append({
        "ชื่อ": row.get("ชื่อ", ""),
        "ราคาขาย": safe_float(row.get("ราคาขาย")),
        "ต้นทุน": safe_float(row.get("ต้นทุน")),
        "คงเหลือ": safe_int(row.get("คงเหลือ")),
        "เข้า": safe_int(row.get("เข้า")),
        "ออก": safe_int(row.get("ออก")),
    })

# === ตัวแปรสถานะ ===
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.title("🧊 ระบบขายหน้าร้านเจริญค้า")

# === ค้นหา + เพิ่มสินค้า ===
search = st.text_input("🔍 ค้นหาสินค้า")
for p in products:
    if search.lower() in p["ชื่อ"].lower():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"🧃 {p['ชื่อ']}")
        with col2:
            qty_key = f"qty_{safe_key(p['ชื่อ'])}"
            if qty_key not in st.session_state:
                st.session_state[qty_key] = 1
            if st.button("-", key=f"sub_{safe_key(p['ชื่อ'])}"):
                st.session_state[qty_key] = max(1, st.session_state[qty_key] - 1)
            st.write(st.session_state[qty_key])
            if st.button("+", key=f"add_{safe_key(p['ชื่อ'])}"):
                st.session_state[qty_key] += 1
        with col3:
            if st.button("➕ ใส่ตะกร้า", key=f"addcart_{safe_key(p['ชื่อ'])}"):
                st.session_state.cart[p["ชื่อ"]] = st.session_state.cart.get(p["ชื่อ"], 0) + st.session_state[qty_key]

st.markdown("---")
st.subheader("🧺 ตะกร้าสินค้า")

total_price = 0
total_profit = 0

for name, qty in st.session_state.cart.items():
    for p in products:
        if p["ชื่อ"] == name:
            price = p["ราคาขาย"] * qty
            profit = (p["ราคาขาย"] - p["ต้นทุน"]) * qty
            st.write(f"{name} × {qty} = {price:.2f} บาท (กำไร {profit:.2f})")
            total_price += price
            total_profit += profit
            break

st.write(f"💰 ยอดรวม: {total_price:.2f} บาท | 🧾 กำไรสุทธิ: {total_profit:.2f} บาท")

# === ยืนยันการขาย ===
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        for i, p in enumerate(products):
            if p["ชื่อ"] == name:
                new_out = p["ออก"] + qty
                out_cell = f"G{i+2}"
                new_balance = p["คงเหลือ"] - qty
                bal_cell = f"E{i+2}"
                sheet.update(out_cell, [[new_out]])
                sheet.update(bal_cell, [[new_balance]])
                # บันทึกยอดขาย
                sale_sheet = spreadsheet.worksheet("ยอดขาย")
                sale_sheet.append_row([now, name, qty, p["ราคาขาย"], p["ต้นทุน"], p["ราคาขาย"] * qty, (p["ราคาขาย"] - p["ต้นทุน"]) * qty, "drink"])
    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.session_state.cart = {}
    st.rerun()
