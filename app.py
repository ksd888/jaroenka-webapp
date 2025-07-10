import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------------- Utils ------------------------
def safe_float(value):
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return 0.0

def safe_int(value):
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0

def safe_get(row, key):
    return row[key] if key in row else ""

# ---------------------- Auth ------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

sheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sheet = client.open_by_key(sheet_id).worksheet("ตู้เย็น")
sales_sheet = client.open_by_key(sheet_id).worksheet("ยอดขาย")

# ---------------------- Load Data ------------------------
data = sheet.get_all_records()

products = []
for row in data:
    try:
        product = {
            "ชื่อ": safe_get(row, "ชื่อ"),
            "ราคาขาย": safe_float(safe_get(row, "ราคาขาย")),
            "ต้นทุน": safe_float(safe_get(row, "ต้นทุน")),
            "กำไร/หน่วย": safe_float(safe_get(row, "ราคาขาย")) - safe_float(safe_get(row, "ต้นทุน")),
            "คงเหลือ": safe_int(safe_get(row, "คงเหลือ")),
            "เข้า": safe_int(safe_get(row, "เข้า")),
            "ออก": safe_int(safe_get(row, "ออก")),
        }
        products.append(product)
    except Exception as e:
        st.warning(f"พบข้อผิดพลาดในข้อมูลสินค้า: {e}")

# ---------------------- UI ------------------------
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

st.subheader("🛒 เลือกสินค้า")
search_mode = st.toggle("🔍 เลือกสินค้าจากชื่อ")

if search_mode:
    selected_names = st.multiselect("🔍 เลือกสินค้าที่จะขาย", [p["ชื่อ"] for p in products])
    selected_products = [p for p in products if p["ชื่อ"] in selected_names]
else:
    selected_products = []
    for p in products:
        if st.checkbox(p["ชื่อ"], key=p["ชื่อ"]):
            selected_products.append(p)

quantities = {}
for p in selected_products:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(p["ชื่อ"])
    with col2:
        if f"qty_{p['ชื่อ']}" not in st.session_state:
            st.session_state[f"qty_{p['ชื่อ']}"] = 1
        if st.button("➖", key=f"dec_{p['ชื่อ']}"):
            st.session_state[f"qty_{p['ชื่อ']}"] = max(1, st.session_state[f"qty_{p['ชื่อ']}] - 1)
    with col3:
        if st.button("➕", key=f"inc_{p['ชื่อ']}"):
            st.session_state[f"qty_{p['ชื่อ']}"] += 1

    quantities[p["ชื่อ"]] = st.session_state[f"qty_{p['ชื่อ']}"]

if st.button("➕ เพิ่มลงตะกร้า"):
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    for name, qty in quantities.items():
        if name in st.session_state.cart:
            st.session_state.cart[name] += qty
        else:
            st.session_state.cart[name] = qty

# ---------------------- ตะกร้า ------------------------
st.subheader("📋 รายการขาย")

total = 0
profit = 0
lines = []

if "cart" in st.session_state:
    for name, qty in st.session_state.cart.items():
        product = next((p for p in products if p["ชื่อ"] == name), None)
        if product:
            line_total = product["ราคาขาย"] * qty
            line_profit = (product["ราคาขาย"] - product["ต้นทุน"]) * qty
            total += line_total
            profit += line_profit
            lines.append(f"- {name} x {qty} = {line_total:.2f} บาท")

for line in lines:
    st.write(line)

st.markdown(f"💵 **ยอดรวม:** {total:.2f} บาท | 🟢 **กำไร:** {profit:.2f} บาท")

# ---------------------- รับเงิน ------------------------
money = st.number_input("💰 รับเงิน", value=0.0, step=1.0)
if money < total:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    change = money - total
    st.success(f"💴 เงินทอน: {change:.2f} บาท")

# ---------------------- ยืนยันการขาย ------------------------
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        product_index = next((i for i, p in enumerate(products) if p["ชื่อ"] == name), None)
        if product_index is not None:
            row_number = product_index + 2  # บวก 2 เพราะ header + index เริ่มที่ 0
            out_cell = f"G{row_number}"
            remain_cell = f"H{row_number}"
            out_value = sheet.acell(out_cell).value
            new_out = safe_int(out_value) + qty
            new_remain = products[product_index]["คงเหลือ"] - qty
            sheet.update(out_cell, [[new_out]])
            sheet.update(remain_cell, [[new_remain]])

    # บันทึกลง Sheet 'ยอดขาย'
    sales_sheet.append_row([
        now, 
        ", ".join([f"{name} x {qty}" for name, qty in st.session_state.cart.items()]),
        total, profit
    ])

    # รีเซ็ต
    st.session_state.cart = {}
    for k in list(st.session_state.keys()):
        if k.startswith("qty_"):
            del st.session_state[k]

    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")
