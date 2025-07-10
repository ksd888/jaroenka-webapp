import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- เชื่อมต่อ Google Sheets ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sales_sheet = spreadsheet.worksheet("ยอดขาย")

# --- โหลดข้อมูล ---
data = sheet.get_all_records()
df = pd.DataFrame(data)
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# --- เริ่ม App ---
st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")
st.title("🛒 เลือกสินค้าจากชื่อ")

# --- ตัวแปร session สำหรับตะกร้าและยอดขาย ---
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []

# --- Autocomplete ค้นหาสินค้าแบบหลายรายการ ---
selected = st.multiselect("🛒 เลือกสินค้าจากชื่อ", df["ชื่อสินค้า"].tolist(), default=st.session_state.selected_items)

# --- แสดงปุ่มเพิ่มลด และจัดการจำนวน ---
for item in selected:
    st.markdown(f"### {item}")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("➖", key=f"minus_{item}"):
            st.session_state.cart[item] = max(st.session_state.cart.get(item, 0) - 1, 0)
    with col2:
        if st.button("➕", key=f"plus_{item}"):
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
    with col3:
        st.write(f"จำนวน: {st.session_state.cart.get(item, 0)}")

# --- เพิ่มลงตะกร้า ---
if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# --- แสดงตะกร้า ---
if st.session_state.cart:
    st.markdown("### 🧺 ตะกร้าสินค้า")
    total_price = 0
    total_profit = 0
    for item, qty in st.session_state.cart.items():
        if qty > 0:
            price = float(df[df["ชื่อสินค้า"] == item]["ราคาขาย"].values[0])
            profit = float(df[df["ชื่อสินค้า"] == item]["กำไรต่อหน่วย"].values[0])
            st.markdown(f"- {item} x {qty} = {price * qty:.2f} บาท")
            total_price += price * qty
            total_profit += profit * qty

    st.markdown(f"💰 **ยอดรวม: {total_price:.2f} บาท**")
    st.markdown(f"📈 **กำไร: {total_profit:.2f} บาท**")

    # --- ยืนยันการขาย ---
    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart.items():
            if qty > 0:
                row = [
                    now,
                    item,
                    qty,
                    float(df[df["ชื่อสินค้า"] == item]["ราคาขาย"].values[0]),
                    float(df[df["ชื่อสินค้า"] == item]["ต้นทุน"].values[0]),
                    float(df[df["ชื่อสินค้า"] == item]["กำไรต่อหน่วย"].values[0]),
                    qty * float(df[df["ชื่อสินค้า"] == item]["ราคาขาย"].values[0]),
                    qty * float(df[df["ชื่อสินค้า"] == item]["กำไรต่อหน่วย"].values[0]),
                    "drink",
                ]
                sales_sheet.append_row([str(r) for r in row])
        st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")

        # --- รีเซ็ตตะกร้าและการค้นหา ---
        st.session_state.cart = {}
        st.session_state.selected_items = []

# --- เครดิต ---
st.markdown("---")
st.markdown("สร้างโดย ❤️ ร้านเจริญค้า")
