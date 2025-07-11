import streamlit as st
import datetime
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ✅ ฟังก์ชันปลอดภัย
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)

# ✅ Apple-style Theme (ขาว-ฟอนต์ดำ)
st.markdown('''
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: black;
        background-color: #ffffff;
    }
    .stButton > button {
        background-color: #0071e3;
        color: white;
        border-radius: 8px;
        padding: 8px 16px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #005bb5;
    }
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
    }
    .product-card {
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        padding: 16px;
        text-align: center;
        font-size: 16px;
    }
    </style>
''', unsafe_allow_html=True)

# 🔐 เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# 📦 โหลดข้อมูลสินค้า
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 🧠 ตั้งค่า session_state
for key in ["cart", "search_items", "quantities", "paid_input", "sale_complete", "sale_trigger"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["cart", "search_items"] else {} if key == "quantities" else 0.0 if key == "paid_input" else False

# 🔁 รีเซ็ตหลังขายเสร็จ
if st.session_state.sale_complete:
    st.session_state["cart"] = []
    st.session_state["search_items"] = []
    st.session_state["quantities"] = {}
    st.session_state["paid_input"] = 0.0
    st.session_state["sale_complete"] = False
    st.success("✅ รีเซ็ตหน้าหลังบันทึกแล้ว")

# 🛍️ เริ่มหน้าจอ
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names, default=st.session_state["search_items"], key="search_items")

# ➕➖ ปรับจำนวนพร้อมแสดงคงเหลือแบบ Grid
grid_html = '<div class="card-grid">'
for p in st.session_state["search_items"]:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    row = df[df["ชื่อสินค้า"] == p]
    stock = safe_int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
    qty = st.session_state.quantities[p]

    grid_html += f'''
    <div class="product-card">
        <b>{p}</b><br>
        คงเหลือ: {stock}<br>
        จำนวน: {qty}<br>
    </div>
    '''
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# ➖➕ ปุ่มควบคุม
for p in st.session_state["search_items"]:
    cols = st.columns([1, 1, 2])
    with cols[0]:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
            st.rerun()
    with cols[1]:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1
            st.rerun()

# ✅ เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for p in st.session_state["search_items"]:
        qty = st.session_state.quantities[p]
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มลงตะกร้าแล้ว")

# 🧾 แสดงตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0.0, 0.0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        total_price += qty * price
        total_profit += qty * (price - cost)
        st.write(f"- {item} x {qty} = {qty * price:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")

    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
    if st.session_state.paid_input >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("💸 เงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        st.session_state.sale_trigger = True

# ✅ บันทึกข้อมูล
if st.session_state.sale_trigger:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item, qty in st.session_state.cart:
        index = df[df["ชื่อสินค้า"] == item].index[0]
        idx_in_sheet = index + 2
        old_out = safe_int(df.at[index, "ออก"])
        old_left = safe_int(df.at[index, "คงเหลือในตู้"])
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, old_out + qty)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, old_left - qty)

    summary_ws.append_row([
        now,
        ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
        total_price,
        total_profit,
        st.session_state.paid_input,
        st.session_state.paid_input - total_price,
        "drink"
    ])
    st.session_state.sale_complete = True
    st.session_state.sale_trigger = False
    st.rerun()
