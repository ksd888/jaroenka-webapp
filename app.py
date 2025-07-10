import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ======================
# 🔒 ใช้ Service Account
# ======================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# ======================
# 🧠 ฟังก์ชันเสริม
# ======================
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def safe_key(name):
    return name.replace(" ", "_").replace(".", "_")

# ======================
# 📦 โหลดข้อมูลสินค้า
# ======================
rows = sheet.get_all_records()
df = pd.DataFrame(rows)

# ตรวจสอบคอลัมน์
required_cols = ["ชื่อ", "ราคาขาย", "ต้นทุน", "กำไรต่อหน่วย", "คงเหลือ", "เข้า", "ออก", "คงเหลือในตู้", "กำไร", "สต๊อกสำรอง"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ ไม่พบคอลัมน์: {col}")
        st.stop()

# สร้าง session_state สำหรับตะกร้าสินค้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

# ======================
# 🔍 ค้นหาสินค้า
# ======================
st.title("🧃 ระบบขายสินค้า - ร้านเจริญค้า")
search_term = st.text_input("🔍 ค้นหาสินค้า", "")
filtered_df = df[df["ชื่อ"].str.contains(search_term, case=False, na=False)] if search_term else df

# ======================
# 🛒 เพิ่มสินค้าเข้าตะกร้า
# ======================
st.subheader("🛒 ตะกร้าสินค้า")
for index, row in filtered_df.iterrows():
    name = row["ชื่อ"]
    price = safe_float(row["ราคาขาย"])
    key_add = f"add_{safe_key(name)}"
    key_qty = f"qty_{safe_key(name)}"

    col1, col2, col3 = st.columns([4, 1, 2])
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        if st.button("+", key=key_add):
            st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
    with col3:
        if name in st.session_state.cart:
            st.markdown(f"x {st.session_state.cart[name]}")

# ======================
# 🧾 สรุปรายการขาย
# ======================
st.markdown("---")
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for name, qty in st.session_state.cart.items():
    row = df[df["ชื่อ"] == name].iloc[0]
    price = safe_float(row["ราคาขาย"])
    cost = safe_float(row["ต้นทุน"])
    line_total = price * qty
    line_profit = (price - cost) * qty
    st.write(f"- {name} x {qty} = {line_total:.0f} บาท (กำไร {line_profit:.0f})")
    total += line_total
    profit += line_profit

st.markdown(f"💵 **รวมทั้งหมด: {total:.0f} บาท**")
st.markdown(f"📈 **กำไรสุทธิ: {profit:.0f} บาท**")

# ======================
# ✅ ยืนยันการขาย
# ======================
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_sales = spreadsheet.worksheet("ยอดขาย")
    for name, qty in st.session_state.cart.items():
        row = df[df["ชื่อ"] == name].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        line_total = price * qty
        line_profit = (price - cost) * qty
        sheet_sales.append_row([now, name, qty, price, cost, line_total, line_profit, "drink"])
    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.session_state.cart = {}  # รีเซ็ตตะกร้าทันที
    st.experimental_rerun()

