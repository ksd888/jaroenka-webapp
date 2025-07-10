import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่า scope และ credentials
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)

# 🔗 เปิด Google Sheet โดยใช้ Spreadsheet ID
spreadsheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sh = gc.open_by_key(spreadsheet_id)
worksheet = sh.worksheet("ตู้เย็น")

# 🔁 ดึงข้อมูลสินค้า
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 💡 คำนวณกำไรต่อหน่วย
df["กำไรต่อหน่วย"] = pd.to_numeric(df["ราคาขาย"], errors="coerce") - pd.to_numeric(df["ต้นทุน"], errors="coerce")

# 🛒 Session state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "search_selection" not in st.session_state:
    st.session_state["search_selection"] = []

# ✅ UI: ค้นหาและเลือกสินค้า
st.title("🧊 ระบบร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้าจากชื่อ")

search = st.multiselect("🛒 เลือกสินค้าจากชื่อ", df["ชื่อสินค้า"].tolist(), key="search_selection")

# 📌 แสดงสินค้า
for item in search:
    st.markdown(f"**{item}**")
    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("➖", key=f"dec_{item}"):
            if item in st.session_state.cart and st.session_state.cart[item] > 0:
                st.session_state.cart[item] -= 1
    with col2:
        if st.button("➕", key=f"inc_{item}"):
            if item in st.session_state.cart:
                st.session_state.cart[item] += 1
            else:
                st.session_state.cart[item] = 1
    with col3:
        st.write(f"จำนวน: {st.session_state.cart.get(item, 0)}")

# 🔻 ปุ่มเพิ่มตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 🧺 ตะกร้าสินค้า
if st.session_state.cart:
    st.markdown("### 🧺 ตะกร้าสินค้า")
    total = 0
    profit = 0
    for item, qty in st.session_state.cart.items():
        item_row = df[df["ชื่อสินค้า"] == item]
        if not item_row.empty:
            price = float(item_row["ราคาขาย"].values[0])
            gain = float(item_row["กำไรต่อหน่วย"].values[0])
            st.markdown(f"- {item} x {qty} = {qty * price:.2f} บาท")
            total += qty * price
            profit += qty * gain

    st.markdown(f"💰 **ยอดรวม: {total:.2f} บาท**")
    st.markdown(f"📈 **กำไร: {profit:.2f} บาท**")

    if st.button("✅ ยืนยันการขาย"):
        # 👉 เพิ่มข้อมูลลงชีท
        sale_sheet = sh.worksheet("ยอดขาย")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart.items():
            item_row = df[df["ชื่อสินค้า"] == item]
            if not item_row.empty:
                price = float(item_row["ราคาขาย"].values[0])
                cost = float(item_row["ต้นทุน"].values[0])
                sale_sheet.append_row([now, item, qty, price, cost, qty*price, qty*(price-cost)], value_input_option="USER_ENTERED")
        st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")

        # ✅ รีเซ็ตตะกร้าและช่องค้นหา
        st.session_state.cart = {}
        st.session_state["search_selection"] = []

# 🔧 โหมดเติมหรือแก้ไขสินค้าสามารถเพิ่มต่อได้ในส่วนอื่น
