import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime

# เชื่อมต่อ Google Sheet ด้วย secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet = spreadsheet.worksheet("ตู้เย็น")
log_sheet = spreadsheet.worksheet("ยอดขาย")  # สำหรับบันทึกยอดขาย

# โหลดข้อมูลปัจจุบันจากชีท
data = sheet.get_all_records()
product_names = [row["ชื่อสินค้า"] for row in data]

st.title("🧊 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# ค้นหาและเลือกสินค้า
search = st.text_input("🔍 ค้นหาสินค้า")
filtered_products = [p for p in product_names if search.lower() in p.lower()]

if not filtered_products:
    st.warning("ไม่พบสินค้าที่ค้นหา")
else:
    selected_product = st.selectbox("เลือกสินค้า", filtered_products)
    row_index = next(i for i, row in enumerate(data) if row["ชื่อสินค้า"] == selected_product)
    product = data[row_index]
    col_index = row_index + 2  # ชดเชย header + index base 1

    st.markdown(f"**สินค้า:** {selected_product}")
    st.write(f"ราคาขาย: {product['ราคาขาย']} บาท | ต้นทุน: {product['ต้นทุน']} บาท")
    st.write(f"คงเหลือในตู้: {product['คงเหลือ']}")

    # 🔵 ปุ่มขายสินค้า
    sell_qty = st.number_input("ขายออก (จำนวน)", min_value=0, step=1)
    if st.button("📦 ขายสินค้า"):
        new_balance = max(product["คงเหลือ"] - sell_qty, 0)
        sheet.update_cell(col_index, product.keys().index("คงเหลือ") + 1, new_balance)
        st.success(f"ขาย {sell_qty} ชิ้น | คงเหลือใหม่: {new_balance}")

        # บันทึกไปชีท "ยอดขาย"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_sheet.append_row([now, selected_product, sell_qty, product["ราคาขาย"], product["ต้นทุน"], (product["ราคาขาย"] - product["ต้นทุน"]) * sell_qty])

    # 🔵 ปุ่มเติมสต๊อก
    add_qty = st.number_input("เติมสินค้าเข้า (จำนวน)", min_value=0, step=1)
    if st.button("➕ เติมสต๊อก"):
        new_balance = product["คงเหลือ"] + add_qty
        sheet.update_cell(col_index, product.keys().index("คงเหลือ") + 1, new_balance)
        st.success(f"เติม {add_qty} ชิ้น | คงเหลือใหม่: {new_balance}")

    # 🔵 ปุ่มแก้ไขจำนวน
    edit_qty = st.number_input("ระบุจำนวนใหม่ (คงเหลือ)", min_value=0, step=1)
    if st.button("✏️ แก้ไขจำนวน"):
        sheet.update_cell(col_index, product.keys().index("คงเหลือ") + 1, edit_qty)
        st.success(f"แก้ไขคงเหลือเป็น: {edit_qty}")
