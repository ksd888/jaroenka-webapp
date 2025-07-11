import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------------
# 🎨 Theme System (Apple Style)
# ---------------------
def set_theme(light=True):
    if light:
        st.markdown("""
        <style>
        body, .stApp {
            background-color: white !important;
            color: black !important;
        }
        .css-18ni7ap { background-color: white !important; }
        .st-bw, .st-cv, .st-cn, .st-em {
            background-color: white !important;
            color: black !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        body, .stApp {
            background-color: #0d0d0d !important;
            color: white !important;
        }
        .css-18ni7ap { background-color: #0d0d0d !important; }
        .st-bw, .st-cv, .st-cn, .st-em {
            background-color: #0d0d0d !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)

# ---------------------
# 🌟 UI Section
# ---------------------
theme_mode = st.radio("Theme", ["Light", "Dark"], )
set_theme(light=(theme_mode == "Light"))

st.image("logo.png", width=120)
st.markdown("## 🧊 ระบบขายสินค้า")

# ---------------------
# ✅ เชื่อม Google Sheet
# ---------------------
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sh.worksheet("ตู้เย็น")
df = pd.DataFrame(worksheet.get_all_records())

# ---------------------
# 🔍 ระบบค้นหา + ตะกร้าสินค้า
# ---------------------
cart = {}
search = st.multiselect("🔍 ค้นหาสินค้า", options=df["สินค้า"].tolist())

for item in search:
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("➖", key=f"minus_{item}"):
            cart[item] = max(cart.get(item, 0) - 1, 0)
    with col2:
        st.markdown(f"<h4 style='text-align: center'>{cart.get(item,0)}</h4>", unsafe_allow_html=True)
    with col3:
        if st.button("➕", key=f"plus_{item}"):
            cart[item] = cart.get(item, 0) + 1

# ---------------------
# 💰 สรุปยอดขาย
# ---------------------
if cart:
    st.markdown("### 🧾 ตะกร้าสินค้า")
    total = 0
    for item, qty in cart.items():
        price = df[df["สินค้า"] == item]["ราคาขาย"].values[0]
        st.write(f"- {item} × {qty} = {qty * price} บาท")
        total += qty * price
    st.markdown(f"## 💸 ยอดรวม: {total} บาท")
else:
    st.info("เลือกรายการสินค้าจากด้านบนเพื่อเริ่มขาย")

