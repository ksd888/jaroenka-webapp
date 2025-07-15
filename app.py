import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

# ✅ CSS Apple Style
st.markdown("""
    <style>
    body, .main, .block-container {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    .stButton>button {
        color: white !important;
        background-color: #007aff !important;
        border-radius: 10px;
        font-weight: bold;
    }
    .stTextInput input, .stNumberInput input {
        background-color: #f2f2f7 !important;
        color: #000 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ✅ ฟังก์ชันช่วย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ เชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# ✅ ตั้งค่า session_state
if "cart" not in st.session_state: st.session_state.cart = []
if "paid_input" not in st.session_state: st.session_state.paid_input = 0.0

# ✅ POS
st.title("🧾 ระบบขายสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("เลือกสินค้า", product_names)
quantities = {p: st.number_input(f"{p} - จำนวน", min_value=1, step=1, key=p) for p in selected}

if st.button("🛒 เพิ่มลงตะกร้า"):
    for p in selected:
        st.session_state.cart.append((p, quantities[p]))
    st.success("✅ เพิ่มลงตะกร้าแล้ว")

# ✅ รายการขาย
st.subheader("📦 ตะกร้าสินค้า")
total_price = total_profit = 0
for p, qty in st.session_state.cart:
    row = df[df["ชื่อสินค้า"] == p].iloc[0]
    price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
    profit = (price - cost) * qty
    subtotal = price * qty
    st.write(f"{p} x {qty} = {subtotal:.2f} บาท")
    total_price += subtotal
    total_profit += profit

# ✅ เงินรับและเงินทอน
st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
if st.session_state.paid_input >= total_price:
    st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
else:
    st.warning("เงินไม่พอ!")

# ✅ ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p, qty in st.session_state.cart:
        index = df[df["ชื่อสินค้า"] == p].index[0]
        idx_in_sheet = index + 2
        current_out = safe_int(df.loc[index, "ออก"])
        current_left = safe_int(df.loc[index, "คงเหลือในตู้"])
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, current_out + qty)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, current_left - qty)
    summary_ws.append_row([
        now,
        ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
        total_price,
        total_profit,
        st.session_state.paid_input,
        st.session_state.paid_input - total_price,
        "drink"
    ])
    st.success("✅ บันทึกเรียบร้อยแล้ว")
    st.session_state.cart = []
    st.session_state.paid_input = 0.0

# ✅ เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock")
    restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1)
    if st.button("📥 ยืนยันเติม"):
        index = df[df["ชื่อสินค้า"] == restock_item].index[0]
        idx_in_sheet = index + 2
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, safe_int(df.loc[index, "เข้า"]) + restock_qty)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, safe_int(df.loc[index, "คงเหลือในตู้"]) + restock_qty)
        st.success(f"เติม {restock_item} แล้ว")

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit")
    index = df[df["ชื่อสินค้า"] == edit_item].index[0]
    idx = index + 2
    new_price = st.number_input("ราคาขาย", value=safe_float(df.loc[index, "ราคาขาย"]))
    new_cost = st.number_input("ต้นทุน", value=safe_float(df.loc[index, "ต้นทุน"]))
    new_stock = st.number_input("คงเหลือในตู้", value=safe_int(df.loc[index, "คงเหลือในตู้"]), step=1)
    if st.button("💾 บันทึก"):
        worksheet.update_cell(idx, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(idx, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        worksheet.update_cell(idx, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
        st.success("อัปเดตแล้ว")

# ✅ รีเซ็ตยอดเข้าออก
if st.button("🔁 รีเซ็ตยอดเข้า-ออก (เริ่มวันใหม่)"):
    num_rows = len(df)
    worksheet.batch_update([
        {"range": f"E2:E{num_rows+1}", "values": [[0]] * num_rows},
        {"range": f"G2:G{num_rows+1}", "values": [[0]] * num_rows}
    ])
    st.success("รีเซ็ตเรียบร้อยแล้ว")

# ✅ Dashboard
st.header("📊 Dashboard รายวัน")
data = pd.DataFrame(summary_ws.get_all_records())
today = datetime.datetime.now().strftime("%Y-%m-%d")
today_data = data[data["timestamp"].str.contains(today)]
if not today_data.empty:
    st.metric("ยอดขายรวม", f"{today_data['total'].sum():,.2f} บาท")
    st.metric("กำไรรวม", f"{today_data['profit'].sum():,.2f} บาท")
else:
    st.info("ยังไม่มีข้อมูลขายวันนี้")
