import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ===== เชื่อมต่อ Google Sheet =====
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ===== โหลดข้อมูลสินค้าทั้งหมด =====
@st.cache_data(ttl=60)
def load_items():
    records = sheet.get_all_records()
    return records

items = load_items()

# ===== กำหนด session state =====
if "cart" not in st.session_state:
    st.session_state.cart = []

# ===== ค้นหาสินค้าและเพิ่มลงตะกร้า =====
st.title("🛒 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = [item["ชื่อสินค้า"] for item in items]
product_lookup = {item["ชื่อสินค้า"]: item for item in items}

col1, col2 = st.columns([3, 1])
with col1:
    selected_product = st.selectbox("เลือกสินค้า", [""] + product_names)
with col2:
    quantity = st.number_input("จำนวน", min_value=1, step=1, value=1)

if st.button("➕ เพิ่มลงตะกร้า") and selected_product:
    product = product_lookup[selected_product]
    st.session_state.cart.append({
        "name": selected_product,
        "price": float(product["ราคาขาย"]),
        "cost": float(product["ต้นทุน"]),
        "qty": quantity
    })
    st.success(f"เพิ่ม {selected_product} จำนวน {quantity} ชิ้นเรียบร้อยแล้ว ✅")

# ===== แสดงรายการในตะกร้า =====
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for item in st.session_state.cart:
    line = f"- {item['name']} x {item['qty']} = {item['price'] * item['qty']:.2f} บาท"
    st.write(line)
    total += item["price"] * item["qty"]
    profit += (item["price"] - item["cost"]) * item["qty"]

st.markdown(f"""<div style="background-color:#1f3b57;padding:10px;border-radius:10px;color:white">
💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท
</div>""", unsafe_allow_html=True)

# ===== รับเงินและคำนวณเงินทอน =====
received = st.number_input("💰 รับเงิน", min_value=0.00, step=1.0, value=0.00)
if received < total:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    change = received - total
    st.success(f"เงินทอน: {change:.2f} บาท")

# ===== ยืนยันการขาย =====
if st.button("✅ ยืนยันการขาย") and st.session_state.cart:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in st.session_state.cart:
        product = product_lookup[item["name"]]
        row = [
            now,
            item["name"],
            item["qty"],
            item["price"],
            item["cost"],
            item["price"] * item["qty"],
            (item["price"] - item["cost"]) * item["qty"],
            "drink"  # ระบุประเภท
        ]
        sheet_sales.append_row(row)
        
        # อัปเดตยอดในชีทตู้เย็น
        cell = sheet.find(item["name"])
        if cell:
            row_idx = cell.row
            out_cell = f"H{row_idx}"
            remain_cell = f"I{row_idx}"
            prev_out = sheet.acell(out_cell).value or "0"
            prev_remain = sheet.acell(remain_cell).value or "0"
            new_out = int(prev_out) + item["qty"]
            new_remain = int(prev_remain) - item["qty"]
            sheet.update(out_cell, new_out)
            sheet.update(remain_cell, new_remain)
    
    # เคลียร์ตะกร้าโดยตรงโดยไม่ใช้ rerun
    st.session_state.cart = []
    st.success("✅ บันทึกและรีเซ็ตเรียบร้อย")

# ===== เพิ่มเติมฟีเจอร์ในอนาคต =====
with st.expander("📦 เติมสินค้า"):
    st.info("⚙️ อยู่ระหว่างพัฒนา...")

with st.expander("✏️ แก้ไขสินค้า"):
    st.info("⚙️ อยู่ระหว่างพัฒนา...")
