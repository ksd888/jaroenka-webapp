import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# ====== 🔒 ป้องกันข้อมูลผิดพลาด ======
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

# ====== 🔐 เชื่อมต่อ Google Sheets ======
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope,
)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")

# ====== 📦 โหลดข้อมูลสินค้า ======
data = sheet.get_all_records()
products = []
for row in data:
    try:
        products.append({
            "ชื่อ": row.get("ชื่อ", ""),
            "ราคาขาย": safe_float(row.get("ราคาขาย")),
            "ต้นทุน": safe_float(row.get("ต้นทุน")),
            "คงเหลือ": safe_int(row.get("คงเหลือ", 0))
        })
    except Exception as e:
        st.warning(f"พบข้อผิดพลาดในข้อมูลสินค้า: {e}")

# ====== 🛒 สร้างตะกร้าเริ่มต้น ======
if "cart" not in st.session_state:
    st.session_state["cart"] = []
if "selected_products" not in st.session_state:
    st.session_state["selected_products"] = []
if "confirm_sale" not in st.session_state:
    st.session_state["confirm_sale"] = False

# ====== 🧊 UI หลัก ======
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

st.header("🛍️ เลือกสินค้า")
selected = st.multiselect("ค้นหาสินค้า", [p["ชื่อ"] for p in products])
st.session_state["selected_products"] = selected

for p in products:
    if p["ชื่อ"] in selected:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{p['ชื่อ']}**")
        with col2:
            if f"qty_{p['ชื่อ']}" not in st.session_state:
                st.session_state[f"qty_{p['ชื่อ']}"] = 1
            if st.button("➖", key=f"dec_{p['ชื่อ']}"):
                st.session_state[f"qty_{p['ชื่อ']}"] = max(1, st.session_state[f"qty_{p['ชื่อ']}"] - 1)
        with col3:
            if st.button("➕", key=f"inc_{p['ชื่อ']}"):
                st.session_state[f"qty_{p['ชื่อ']}"] += 1

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in products:
        if p["ชื่อ"] in selected:
            qty = st.session_state.get(f"qty_{p['ชื่อ']}", 1)
            st.session_state["cart"].append({
                "ชื่อ": p["ชื่อ"],
                "จำนวน": qty,
                "ราคาขาย": p["ราคาขาย"],
                "ต้นทุน": p["ต้นทุน"]
            })
    st.success("เพิ่มสินค้าลงตะกร้าเรียบร้อยแล้ว ✅")
    st.session_state["selected_products"] = []

# ====== 🧾 แสดงตะกร้า ======
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for item in st.session_state["cart"]:
    subtotal = item["ราคาขาย"] * item["จำนวน"]
    item_profit = (item["ราคาขาย"] - item["ต้นทุน"]) * item["จำนวน"]
    st.write(f"- {item['ชื่อ']} x {item['จำนวน']} = {subtotal:.2f} บาท")
    total += subtotal
    profit += item_profit

st.info(f"🧾 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# ====== 💰 รับเงิน ======
cash = st.number_input("💰 รับเงิน", min_value=0.0, value=0.0, step=1.0)
if cash < total:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"💵 เงินทอน: {cash - total:.2f} บาท")

# ====== ✅ ยืนยันการขาย ======
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now(pytz.timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")
    for item in st.session_state["cart"]:
        sheet.append_row([
            now,
            item["ชื่อ"],
            item["จำนวน"],
            item["ราคาขาย"],
            item["ต้นทุน"],
            item["จำนวน"] * item["ราคาขาย"],
            (item["ราคาขาย"] - item["ต้นทุน"]) * item["จำนวน"]
        ])
    # ✅ รีเซ็ตตะกร้าทันทีหลังบันทึก
    st.session_state["cart"] = []
    st.session_state["selected_products"] = []
    st.session_state["confirm_sale"] = False
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าเรียบร้อยแล้ว!")

# ====== 📦 เติมสินค้า ======
with st.expander("📦 เติมสินค้า"):
    for p in products:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(p["ชื่อ"])
        with col2:
            qty = st.number_input(f"เติม {p['ชื่อ']}", min_value=0, key=f"เติม_{p['ชื่อ']}")
            if qty > 0 and st.button(f"✅ เติม {p['ชื่อ']}", key=f"btn_เติม_{p['ชื่อ']}"):
                try:
                    idx = [r["ชื่อ"] for r in data].index(p["ชื่อ"])
                    cell = f"D{idx+2}"  # คอลัมน์คงเหลือ
                    new_value = data[idx]["คงเหลือ"] + qty
                    sheet.update(cell, [[new_value]])
                    st.success(f"เติม {p['ชื่อ']} แล้ว ✅")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# ====== ✏️ แก้ไขสินค้า ======
with st.expander("✏️ แก้ไขสินค้า"):
    for p in products:
        with st.form(f"edit_{p['ชื่อ']}"):
            new_name = st.text_input("ชื่อ", value=p["ชื่อ"])
            new_price = st.number_input("ราคาขาย", value=p["ราคาขาย"])
            new_cost = st.number_input("ต้นทุน", value=p["ต้นทุน"])
            new_stock = st.number_input("คงเหลือ", value=p["คงเหลือ"], step=1)
            submitted = st.form_submit_button("💾 บันทึกการแก้ไข")
            if submitted:
                try:
                    idx = [r["ชื่อ"] for r in data].index(p["ชื่อ"])
                    sheet.update(f"A{idx+2}:D{idx+2}", [[new_name, new_price, new_cost, new_stock]])
                    st.success("บันทึกการแก้ไขเรียบร้อยแล้ว ✅")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
