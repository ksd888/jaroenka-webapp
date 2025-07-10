import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ----------------- CONFIG -----------------
SPREADSHEET_ID = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
SHEET_NAME = "ตู้เย็น"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ----------------- FUNCTION -----------------
def safe_int(val):
    try:
        return int(float(val))
    except:
        return 0

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def load_data():
    creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df, ws

# ----------------- UI -----------------
st.set_page_config(page_title="เจริญค้า - ตู้เย็น", layout="wide")
st.title("🧊 ระบบขายสินค้า - เจริญค้า")

df, worksheet = load_data()
product_names = df["ชื่อสินค้า"].tolist()

if "cart" not in st.session_state:
    st.session_state.cart = {}

# ----------------- 🛒 ระบบขาย -----------------
st.header("🛒 ขายสินค้า")
selected = st.multiselect("ค้นหาสินค้า", product_names, key="search_multi")
for p in selected:
    if f"qty_{p}" not in st.session_state:
        st.session_state[f"qty_{p}"] = 1
    cols = st.columns([3, 2, 1])
    with cols[0]:
        st.write(p)
    with cols[1]:
        st.number_input("จำนวน", min_value=1, key=f"qty_{p}", label_visibility="collapsed")
    with cols[2]:
        if st.button("➕", key=f"add_{p}"):
            qty = st.session_state[f"qty_{p}"]
            st.session_state.cart[p] = st.session_state.cart.get(p, 0) + qty
            st.success(f"เพิ่ม {p} จำนวน {qty}")

# ----------------- 🧾 ตะกร้าสินค้า -----------------
if st.session_state.cart:
    st.subheader("🧾 ตะกร้าสินค้า")
    total = 0
    for item, qty in st.session_state.cart.items():
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        st.write(f"{item} × {qty} = {qty * price:.2f} บาท")
        total += qty * price
    st.write(f"**ยอดรวม:** {total:.2f} บาท")

    cash = st.number_input("💰 รับเงินมา", min_value=0.0, step=1.0)
    change = cash - total if cash >= total else 0
    st.write(f"**เงินทอน:** {change:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart.items():
            idx = df[df["ชื่อสินค้า"] == item].index[0] + 2
            row = df.loc[idx - 2]
            old_out = safe_int(row["ออก"])
            old_left = safe_int(row["คงเหลือในตู้"])
            worksheet.update_cell(idx, df.columns.get_loc("ออก") + 1, old_out + qty)
            worksheet.update_cell(idx, df.columns.get_loc("คงเหลือในตู้") + 1, old_left - qty)
        worksheet.update("B1", [[now]])
        st.success("✅ บันทึกการขายแล้ว")
        st.session_state.cart = {}
        st.session_state.search_multi = []

# ----------------- 📥 เติมสินค้า -----------------
with st.expander("📥 เติมสินค้า"):
    for p in product_names:
        st.number_input(f"เติม {p}", min_value=0, key=f"เติม_{p}")
        qty = st.session_state.get(f"เติม_{p}", 0)
        if st.button(f"📥 ยืนยันเติม {p}", key=f"เติมbtn_{p}"):
            index = df[df["ชื่อสินค้า"] == p].index[0]
            idx_in_sheet = index + 2
            row = df.loc[index]
            new_in = safe_int(row["เข้า"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) + qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
            st.success(f"✅ เติม {p} แล้ว")
