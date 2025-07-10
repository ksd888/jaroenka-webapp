import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ฟังก์ชันปลอดภัย
def safe_key(text):
    return text.replace(" ", "_").replace(".", "_").replace("-", "_").replace("/", "_")

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# เชื่อม Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# อ่านข้อมูลสินค้า
data = sheet.get_all_records()
products = []
for row in data:
    if row.get("ชื่อ"):
        products.append({
            "ชื่อ": row["ชื่อ"],
            "ราคาขาย": safe_float(row.get("ราคาขาย", 0)),
            "ต้นทุน": safe_float(row.get("ต้นทุน", 0)),
            "คงเหลือ": safe_float(row.get("คงเหลือ", 0)),
            "เข้า": safe_float(row.get("เข้า", 0)),
            "ออก": safe_float(row.get("ออก", 0)),
        })

# ตะกร้า session
if "cart" not in st.session_state:
    st.session_state.cart = {}

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

# ---------------------- ระบบค้นหา + ขาย --------------------
search = st.text_input("🔍 ค้นหาสินค้า")
filtered_products = [p for p in products if search in p["ชื่อ"]] if search else products

for p in filtered_products:
    qty_key = f"qty_{safe_key(p['ชื่อ'])}"
    sub_key = f"sub_{qty_key}"
    add_key = f"add_{qty_key}"
    cart_key = f"addcart_{qty_key}"

    if qty_key not in st.session_state:
        st.session_state[qty_key] = 1

    st.markdown(f"**{p['ชื่อ']}** - {p['ราคาขาย']} บาท")
    cols = st.columns([1, 1, 1, 2])
    with cols[0]:
        if st.button("-", key=sub_key):
            st.session_state[qty_key] = max(1, st.session_state[qty_key] - 1)
    with cols[1]:
        st.write(st.session_state[qty_key])
    with cols[2]:
        if st.button("+", key=add_key):
            st.session_state[qty_key] += 1
    with cols[3]:
        if st.button("➕ ใส่ตะกร้า", key=cart_key):
            st.session_state.cart[p["ชื่อ"]] = st.session_state.cart.get(p["ชื่อ"], 0) + st.session_state[qty_key]

st.divider()
st.header("🛒 ตะกร้าสินค้า")

if st.session_state.cart:
    total = 0
    cost_total = 0
    for name, qty in st.session_state.cart.items():
        prod = next((p for p in products if p["ชื่อ"] == name), None)
        if not prod:
            continue
        price = prod["ราคาขาย"] * qty
        cost = prod["ต้นทุน"] * qty
        profit = price - cost
        total += price
        cost_total += cost
        st.write(f"- {name} จำนวน {qty} ชิ้น = {price:.2f} บาท")

    st.write(f"💰 ยอดรวม: {total:.2f} บาท")
    st.write(f"📈 กำไรสุทธิ: {total - cost_total:.2f} บาท")

    confirm = st.button("✅ ยืนยันการขาย")
    if confirm:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sale_sheet = spreadsheet.worksheet("ยอดขาย")
        for name, qty in st.session_state.cart.items():
            prod = next((p for p in products if p["ชื่อ"] == name), None)
            if prod:
                sale_sheet.append_row([
                    now, name, qty, prod["ราคาขาย"], prod["ต้นทุน"],
                    prod["ราคาขาย"] * qty, (prod["ราคาขาย"] - prod["ต้นทุน"]) * qty,
                    "drink"
                ])

                # อัปเดตออกในชีทหลัก
                row_index = next((i for i, r in enumerate(data) if r.get("ชื่อ") == name), None)
                if row_index is not None:
                    out_cell = f"G{row_index + 2}"
                    new_out = data[row_index]["ออก"] + qty
                    sheet.update(out_cell, [[new_out]])

                    remain_cell = f"E{row_index + 2}"
                    new_remain = data[row_index]["คงเหลือ"] - qty
                    sheet.update(remain_cell, [[new_remain]])

        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
        st.session_state.cart.clear()
        for p in products:
            qty_key = f"qty_{safe_key(p['ชื่อ'])}"
            if qty_key in st.session_state:
                st.session_state[qty_key] = 1

# ----------------- เติมสินค้า --------------------
with st.expander("📦 เติมสินค้าเข้า"):
    for p in products:
        qty = st.number_input(f"เติม {p['ชื่อ']}", min_value=0, key=f"เติม_{safe_key(p['ชื่อ'])}")
        if qty > 0:
            idx = next((i for i, r in enumerate(data) if r["ชื่อ"] == p["ชื่อ"]), None)
            if idx is not None:
                in_cell = f"F{idx + 2}"
                new_in = data[idx]["เข้า"] + qty
                sheet.update(in_cell, [[new_in]])

                remain_cell = f"E{idx + 2}"
                new_remain = data[idx]["คงเหลือ"] + qty
                sheet.update(remain_cell, [[new_remain]])
            st.success(f"เติม {p['ชื่อ']} จำนวน {qty} เรียบร้อยแล้ว")
