import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ✅ สไตล์แบบ Light Mode
st.markdown("""
    <style>
    body, .main, .block-container {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    .stButton>button {
        color: white !important;
        background-color: #007aff !important;
        border: none;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stTextInput>div>div>input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        background-color: #f5f5f5 !important;
        color: #000 !important;
    }
    .st-expander, .st-expander>details {
        background-color: #f8f8f8 !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ✅ เชื่อม Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sh.worksheet("ตู้เย็น")
df = pd.DataFrame(worksheet.get_all_records())

# ✅ ฟังก์ชันช่วย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ ตรวจสอบ cart
if "cart" not in st.session_state:
    st.session_state["cart"] = {}

# ✅ หน้า UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names)

for pname in selected:
    st.write(f"### {pname}")
    qty = st.number_input(
        f"จำนวนที่ต้องการขายสำหรับ {pname}",
        min_value=0,
        value=st.session_state["cart"].get(pname, 0),
        step=1,
        key=f"qty_{pname}"
    )
    st.session_state["cart"][pname] = qty

    remaining = df[df["ชื่อสินค้า"] == pname]["คงเหลือในตู้"].values[0]
    st.write(f"🧊 คงเหลือในตู้: {remaining}")

    if st.button(f"➕ เพิ่มลงตะกร้า", key=f"add_{pname}"):
        st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# ✅ แสดงตะกร้า
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for pname, qty in st.session_state["cart"].items():
    if qty > 0:
        row = df[df["ชื่อสินค้า"] == pname]
        price = float(row["ราคาขาย"].values[0])
        cost = float(row["ต้นทุน"].values[0])
        st.write(f"- {pname} x {qty} = {price * qty:.2f} บาท")
        total += price * qty
        profit += (price - cost) * qty

st.markdown(f"💵 ยอดรวม: {total:.2f} บาท 🟢 กำไร: {profit:.2f} บาท")

# ✅ รับเงิน
received = st.number_input("💰 รับเงิน", min_value=0.0, value=0.0, step=1.0)
change = received - total
if received > 0:
    st.markdown(f"""
    <div style="background-color:#fff8dc;padding:10px;border-radius:10px;">
        <span style="color:#000000;font-weight:bold;font-size:18px;">
        💵 เงินทอน: {change:.2f} บาท
        </span>
    </div>
    """, unsafe_allow_html=True)

# ✅ ยืนยันขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pname, qty in st.session_state["cart"].items():
        if qty > 0:
            df.loc[df["ชื่อสินค้า"] == pname, "ออก"] += qty
            df.loc[df["ชื่อสินค้า"] == pname, "คงเหลือในตู้"] -= qty
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.session_state["cart"] = {}
    st.experimental_rerun()
