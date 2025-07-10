import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# ตั้งค่าการเชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope,
)
gc = gspread.authorize(creds)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")

# โหลดข้อมูล
data = sheet.get_all_records()
df = pd.DataFrame(data)
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# ชื่อสินค้า
product_names = df["ชื่อสินค้า"].tolist()

# ตั้งค่าตะกร้าและจำนวนสินค้าใน session_state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "search_selection" not in st.session_state:
    st.session_state.search_selection = []

st.title("🛒 เลือกสินค้าจากชื่อ")

# ค้นหาสินค้า
search_selection = st.multiselect("🛒 เลือกสินค้าจากชื่อ", product_names, key="search_selection")

for item in search_selection:
    if item not in st.session_state.cart:
        st.session_state.cart[item] = 0

    st.subheader(f"{item}")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➖", key=f"decrease_{item}"):
            if st.session_state.cart[item] > 0:
                st.session_state.cart[item] -= 1
    with col2:
        if st.button("➕", key=f"increase_{item}"):
            st.session_state.cart[item] += 1

    st.text(f"จำนวน: {st.session_state.cart[item]}")

if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")
    st.session_state.search_selection = []  # ✅ รีเซ็ตการค้นหา

# แสดงตะกร้า
st.markdown("---")
st.subheader("🧺 ตะกร้าสินค้า")

total = 0
total_profit = 0
for item, qty in st.session_state.cart.items():
    if qty > 0:
        item_row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = item_row["ราคาขาย"]
        profit = item_row["กำไรต่อหน่วย"]
        st.write(f"- {item} x {qty} = {price * qty:.2f} บาท")
        total += price * qty
        total_profit += profit * qty

st.markdown(f"💰 **ยอดรวม: {total:.2f} บาท**")
st.markdown(f"📈 **กำไร: {total_profit:.2f} บาท**")

# ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now()
    for item, qty in st.session_state.cart.items():
        if qty > 0:
            item_row = df[df["ชื่อสินค้า"] == item].iloc[0]
            profit = item_row["กำไรต่อหน่วย"]
            sheet_to_log = sh.worksheet("ยอดขาย")
            sheet_to_log.append_row([
                now.strftime("%Y-%m-%d %H:%M:%S"),
                item,
                qty,
                item_row["ราคาขาย"],
                item_row["ต้นทุน"],
                profit,
                qty * profit,
                "drink"
            ])
            # อัปเดตคงเหลือ
            idx = df[df["ชื่อสินค้า"] == item].index[0]
            df.at[idx, "ออก"] += qty
            df.at[idx, "คงเหลือในตู้"] = df.at[idx, "เข้า"] - df.at[idx, "ออก"]
            sheet.update_cell(idx + 2, df.columns.get_loc("ออก") + 1, df.at[idx, "ออก"])
            sheet.update_cell(idx + 2, df.columns.get_loc("คงเหลือในตู้") + 1, df.at[idx, "คงเหลือในตู้"])
    st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")
    st.session_state.cart = {}  # ล้างตะกร้า
    st.session_state.search_selection = []  # ✅ ล้างช่องค้นหาอีกครั้ง
