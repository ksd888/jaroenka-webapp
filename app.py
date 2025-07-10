import streamlit as st
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["GCP_SERVICE_ACCOUNT"], scope
)
client = gspread.authorize(creds)
sheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
inventory_ws = sheet.worksheet("ตู้เย็น")
sales_ws = sheet.worksheet("ยอดขาย")

# 🛡️ helper ปลอดภัย
def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0

def safe_int(value):
    try:
        return int(value)
    except:
        return 0

# 📥 โหลดข้อมูลสินค้า
data = inventory_ws.get_all_records()
products = []
for row in data:
    try:
        products.append({
            "ชื่อ": row.get("ชื่อ", ""),
            "ราคาขาย": safe_float(row.get("ราคาขาย", 0)),
            "ต้นทุน": safe_float(row.get("ต้นทุน", 0)),
            "คงเหลือ": safe_int(row.get("คงเหลือ", 0)),
        })
    except Exception as e:
        st.warning(f"พบข้อผิดพลาดในข้อมูลสินค้า: {e}")

st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛍️ เลือกสินค้า")

cart = st.session_state.get("cart", [])

# ค้นหาสินค้าแบบ multiselect
selected_names = st.multiselect("🔍 เลือกสินค้าจากชื่อ", [p["ชื่อ"] for p in products])

# ใส่จำนวนสำหรับสินค้าแต่ละตัว
for p in selected_names:
    if f"qty_{p}" not in st.session_state:
        st.session_state[f"qty_{p}"] = 1
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        st.markdown(f"**{p}**")
    with col2:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state[f"qty_{p}"] = max(1, st.session_state[f"qty_{p}"] - 1)
    with col3:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state[f"qty_{p}"] += 1

# ➕ เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected_names:
        qty = st.session_state.get(f"qty_{p}", 1)
        cart.append({"ชื่อ": p, "จำนวน": qty})
    st.session_state["cart"] = cart
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 🧾 รายการขาย
st.subheader("🧾 รายการขาย")
total = 0
profit = 0
for item in cart:
    product = next((x for x in products if x["ชื่อ"] == item["ชื่อ"]), None)
    if product:
        line_total = product["ราคาขาย"] * item["จำนวน"]
        line_profit = (product["ราคาขาย"] - product["ต้นทุน"]) * item["จำนวน"]
        st.markdown(f"- {item['ชื่อ']} x {item['จำนวน']} = {line_total:.2f} บาท")
        total += line_total
        profit += line_profit

st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# 💸 เงินรับ
receive = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
change = receive - total
if change < 0:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"💚 เงินทอน: {change:.2f} บาท")

# ✅ ยืนยันการขาย
if st.checkbox("✅ ยืนยันการขาย"):
    if cart and receive >= total:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in cart:
            row = [
                now,
                item["ชื่อ"],
                item["จำนวน"],
                next((p["ราคาขาย"] for p in products if p["ชื่อ"] == item["ชื่อ"]), 0),
                next((p["ต้นทุน"] for p in products if p["ชื่อ"] == item["ชื่อ"]), 0),
                total,
                profit,
                "drink"
            ]
            sales_ws.append_row(row)

            # 🔄 อัปเดตคงเหลือ
            cell = inventory_ws.find(item["ชื่อ"])
            if cell:
                current_qty = safe_int(inventory_ws.cell(cell.row, cell.col + 3).value)
                inventory_ws.update_cell(cell.row, cell.col + 3, current_qty - item["จำนวน"])

        # 🔄 รีเซ็ต cart
        for p in selected_names:
            del st.session_state[f"qty_{p}"]
        st.session_state["cart"] = []
        st.success("✅ บันทึกยอดขายและรีเซ็ตตะกร้าเรียบร้อยแล้ว")

        # 🔁 รีเฟรช
        st.experimental_rerun()

# 📦 เติมสินค้า
st.markdown("---")
st.subheader("📦 เติมสินค้า")
for p in [x["ชื่อ"] for x in products]:
    qty = st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}")
    if qty > 0:
        cell = inventory_ws.find(p)
        if cell:
            now_qty = safe_int(inventory_ws.cell(cell.row, cell.col + 3).value)
            inventory_ws.update_cell(cell.row, cell.col + 3, now_qty + qty)
        st.success(f"✅ เติม {p} แล้ว +{qty}")

# ✏️ แก้ไขสินค้า
st.markdown("---")
st.subheader("✏️ แก้ไขสินค้า")
edit_product = st.selectbox("เลือกสินค้า", [p["ชื่อ"] for p in products])
new_price = st.number_input("📌 ราคาขายใหม่", min_value=0.0, step=1.0, value=safe_float(
    next((x["ราคาขาย"] for x in products if x["ชื่อ"] == edit_product), 0)))
new_cost = st.number_input("💰 ต้นทุนใหม่", min_value=0.0, step=1.0, value=safe_float(
    next((x["ต้นทุน"] for x in products if x["ชื่อ"] == edit_product), 0)))
if st.button("💾 บันทึกการแก้ไข"):
    cell = inventory_ws.find(edit_product)
    if cell:
        inventory_ws.update_cell(cell.row, cell.col + 1, new_price)
        inventory_ws.update_cell(cell.row, cell.col + 2, new_cost)
        st.success("✅ แก้ไขสินค้าเรียบร้อยแล้ว")
        st.experimental_rerun()
