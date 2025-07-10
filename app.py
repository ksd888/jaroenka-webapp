import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime
import json

# ใช้ Google Auth แทน oauth2client
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
sale_sheet = sheet.worksheet("ยอดขาย")

st.set_page_config(page_title="ร้านเจริญค้า - ระบบขายสินค้า", layout="centered")

st.markdown("## 🧊 ร้านเจริญค้า - ระบบขายสินค้า")

@st.cache_data
def load_data():
    df = pd.DataFrame(worksheet.get_all_records())
    return df

df = load_data()
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# ------------------- UI -------------------
search_term = st.text_input("🔍 ค้นหาสินค้า", "")

filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)]

cart = st.session_state.get("cart", {})

for _, row in filtered_df.iterrows():
    name = row["ชื่อสินค้า"]
    if name not in cart:
        cart[name] = 0

    col1, col2, col3 = st.columns([1,1,5])
    with col1:
        if st.button("-", key=f"sub_{name}"):
            if cart[name] > 0:
                cart[name] -= 1
    with col2:
        if st.button("+", key=f"add_{name}"):
            cart[name] += 1
    with col3:
        st.write(f"**{name} (จำนวน: {cart[name]})**")

st.session_state["cart"] = cart

if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# ---------------- ตะกร้าสินค้า ----------------
st.markdown("### 🧺 ตะกร้าสินค้า")

total = 0
profit = 0
sell_rows = []

for name, qty in cart.items():
    if qty > 0:
        row = df[df["ชื่อสินค้า"] == name].iloc[0]
        price = row["ราคาขาย"]
        cost = row["ต้นทุน"]
        subtotal = price * qty
        subprofit = (price - cost) * qty
        total += subtotal
        profit += subprofit
        st.write(f"- {name} x {qty} = {subtotal:.2f} บาท")
        sell_rows.append({
            "ชื่อสินค้า": name,
            "จำนวน": qty,
            "ยอดขาย": subtotal,
            "กำไร": subprofit,
            "วันที่": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

st.markdown(f"### 💰 ยอดรวม: {total:.2f} บาท")
st.markdown(f"### 📈 กำไร: {profit:.2f} บาท")

if st.button("✅ ยืนยันการขาย"):
    for r in sell_rows:
        try:
            sale_sheet.append_row(list(r.values()))
        except:
            st.error("ไม่สามารถบันทึกยอดขายได้")
    st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")
    st.session_state["cart"] = {}
    st.experimental_rerun()
