import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่าการเข้าถึง Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)

gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# อ่านข้อมูลจากชีท
data = sheet.get_all_records()

# แปลงข้อมูลให้อยู่ในรูปแบบลิสต์ของ dict พร้อมใช้
products = []
for row in data:
    products.append({
        "ชื่อ": row.get("ชื่อ", ""),
        "ราคาขาย": float(row.get("ราคาขาย", 0)),
        "ต้นทุน": float(row.get("ต้นทุน", 0)),
        "คงเหลือ": int(row.get("คงเหลือ", 0)),
        "เข้า": int(row.get("เข้า", 0)),
        "ออก": int(row.get("ออก", 0))
    })

st.title("ระบบขายสินค้า - เจริญค้า")

# ฟังก์ชันสำหรับแปลง key ให้ปลอดภัย
def safe_key(name):
    return name.replace(" ", "_").replace(".", "_").replace("/", "_").replace("(", "").replace(")", "")

# ค้นหาสินค้า
search_query = st.text_input("ค้นหาสินค้า")
filtered_products = [p for p in products if search_query.lower() in p["ชื่อ"].lower()] if search_query else []

# ตะกร้าสินค้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

# แสดงสินค้าค้นหา
st.subheader("ผลลัพธ์สินค้า")
for p in filtered_products:
    pname = p["ชื่อ"]
    key_qty = f"qty_{safe_key(pname)}"
    key_add = f"add_{safe_key(pname)}"
    key_sub = f"sub_{safe_key(pname)}"
    st.session_state.setdefault(key_qty, 1)

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**{pname}**")
    with col2:
        if st.button("-", key=key_sub):
            st.session_state[key_qty] = max(1, st.session_state[key_qty] - 1)
    with col3:
        st.markdown(f"{st.session_state[key_qty]}")
    with col4:
        if st.button("+", key=key_add):
            st.session_state[key_qty] += 1

    if st.button("เพิ่มลงตะกร้า", key=f"add_to_cart_{safe_key(pname)}"):
        st.session_state.cart[pname] = st.session_state.cart.get(pname, 0) + st.session_state[key_qty]
        st.success(f"เพิ่ม {pname} แล้ว ({st.session_state.cart[pname]})")

# แสดงตะกร้าสินค้า
st.subheader("ตะกร้าสินค้า")
total = 0
profit = 0
for pname, qty in st.session_state.cart.items():
    item = next((x for x in products if x["ชื่อ"] == pname), None)
    if item:
        price = item["ราคาขาย"]
        cost = item["ต้นทุน"]
        total += price * qty
        profit += (price - cost) * qty
        st.write(f"{pname} × {qty} = {price * qty:.2f} บาท")

st.markdown(f"**ยอดรวม: {total:.2f} บาท**")
st.markdown(f"**กำไร: {profit:.2f} บาท**")

# ปุ่มยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pname, qty in st.session_state.cart.items():
        try:
            cell = sheet.find(pname)
            row = cell.row
            out_cell = f"G{row}"  # คอลัมน์ 'ออก'
            current_out = int(sheet.acell(out_cell).value or 0)
            sheet.update(out_cell, current_out + qty)

            remain_cell = f"E{row}"  # คอลัมน์ 'คงเหลือ'
            current_remain = int(sheet.acell(remain_cell).value or 0)
            sheet.update(remain_cell, max(0, current_remain - qty))

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดกับ {pname}: {e}")
    st.success("บันทึกการขายเรียบร้อยแล้ว ✅")
    st.session_state.cart.clear()
    st.experimental_rerun()
