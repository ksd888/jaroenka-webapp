import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ✅ Apple Style CSS
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
        border-radius: 10px;
        padding: 0.5em 1.2em;
        font-weight: bold;
    }
    .stTextInput>div>div>input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        background-color: #f2f2f7 !important;
        color: #000 !important;
        border-radius: 6px;
        font-size: 18px;
        font-weight: bold;
    }
    .st-expander, .st-expander>details {
        background-color: #f9f9f9 !important;
        color: #000000 !important;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ✅ ฟังก์ชันช่วย
def safe_key(text): return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)
def safe_safe_int(val): 
    try: return safe_int(safe_float(val))
    except: return 0
def safe_safe_float(val): 
    try: return safe_float(val)
    except: return 0.0

def increase_quantity(p): st.session_state.quantities[p] += 1
def decrease_quantity(p): st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)

# 🔗 เชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# ✅ ตั้งค่าเริ่มต้น
if st.session_state.get("reset_search_items"):
    st.session_state["search_items"] = []
    st.session_state["quantities"] = {}
    st.session_state["cart"] = []
    st.session_state["paid_input"] = 0.0
    st.session_state["last_paid_click"] = 0
    st.session_state["undo_last_cart"] = None
    del st.session_state["reset_search_items"]

default_session = {
    "cart": [],
    "search_items": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "undo_last_cart": None
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ UI ขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("เลือกสินค้าจากชื่อ", product_names, key="search_items")

selected = st.session_state["search_items"]
for p in selected:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    qty = st.session_state.quantities[p]
    st.markdown(f"**{p}**")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
    with col2:
        st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
    with col3:
        st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
    row = df[df['ชื่อสินค้า'] == p]
    stock = int(row['คงเหลือในตู้'].values[0]) if not row.empty else 0
    st.markdown(f"<span style='color:{'red' if stock < 3 else 'black'}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 📋 รายการขาย
st.subheader("📋 รายการขาย")
total_price, total_profit = 0, 0
updated_cart = []
for idx, (item, qty) in enumerate(st.session_state.cart):
    row = df[df["ชื่อสินค้า"] == item]
    if row.empty:
        continue
    row = row.iloc[0]
    stock = safe_safe_int(row["คงเหลือในตู้"])
    price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
    if qty > stock:
        st.warning(f"❗ สินค้า **{item}** เหลือในตู้ {stock} ชิ้น ขาย {qty} ไม่ได้")
        continue
    subtotal, profit = qty * price, qty * (price - cost)
    total_price += subtotal
    total_profit += profit
    updated_cart.append((item, qty))
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")
    with col2:
        if st.button("❌", key=f"remove_{idx}"):
            st.session_state.cart.pop(idx)
            st.experimental_rerun()

# 💰 ช่องรับเงิน
st.number_input("💰 รับเงินจากลูกค้า", key="paid_input", step=1.0)

# ปุ่มเงินลัด
def add_money(amount): st.session_state.paid_input += amount; st.session_state.last_paid_click = amount
cols = st.columns(5)
for i, v in enumerate([20, 50, 100, 500, 1000]):
    with cols[i]: st.button(f"{v}", on_click=add_money, args=(v,))
if st.session_state.last_paid_click:
    if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
        st.session_state.paid_input -= st.session_state.last_paid_click
        st.session_state.last_paid_click = 0

# ยอดรวม
st.info(f"📦 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
if st.session_state.paid_input >= total_price:
    st.success(f"💰 เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
else:
    st.warning("💸 เงินไม่พอ")

# ✅ ยืนยันการขาย
if st.button("✅ ยืนยันการขาย") and updated_cart:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates = []
    for item, qty in updated_cart:
        index = df[df["ชื่อสินค้า"] == item].index[0]
        row = df.loc[index]
        idx_in_sheet = index + 2
        new_out = safe_safe_int(row["ออก"]) + qty
        new_left = safe_safe_int(row["คงเหลือในตู้"]) - qty
        updates.append((idx_in_sheet, "ออก", new_out))
        updates.append((idx_in_sheet, "คงเหลือในตู้", new_left))

    # ใช้ batch update
    col_index = {col: i+1 for i, col in enumerate(df.columns)}
    cell_list = worksheet.range(f"A2:{chr(65+len(df.columns))}{len(df)+1}")
    for row_idx, col_name, new_val in updates:
        cell = worksheet.cell(row_idx, col_index[col_name])
        cell.value = new_val
        worksheet.update_cell(row_idx, col_index[col_name], new_val)

    summary_ws.append_row([
        now,
        ", ".join([f"{i} x {q}" for i, q in updated_cart]),
        total_price,
        total_profit,
        st.session_state.paid_input,
        st.session_state.paid_input - total_price,
        "drink"
    ])
    st.session_state.undo_last_cart = updated_cart.copy()
    st.session_state.reset_search_items = True
    st.rerun()

# 🔁 Undo การขาย
if st.session_state.undo_last_cart:
    with st.expander("↩️ ย้อนกลับการขายล่าสุด"):
        st.write(st.session_state.undo_last_cart)
        if st.button("❌ ล้าง Undo ล่าสุด"):
            st.session_state.undo_last_cart = None

# 📊 Dashboard
st.markdown("---")
st.subheader("📈 Dashboard สรุปยอดขายวันนี้")
summary_df = pd.DataFrame(summary_ws.get_all_records())
summary_df["วันที่"] = pd.to_datetime(summary_df["timestamp"]).dt.date
today = datetime.datetime.now().date()
today_df = summary_df[summary_df["วันที่"] == today]
total_today = today_df["ยอดขาย"].sum()
profit_today = today_df["กำไร"].sum()
st.info(f"🗓️ วันนี้ ({today}) | 🛒 ยอดขาย: {total_today:.2f} บาท | 💰 กำไร: {profit_today:.2f} บาท")

# กราฟแสดงยอดขายรายสินค้า
if not today_df.empty:
    item_stats = today_df["สินค้า"].str.split(", ").explode().str.extract(r"(.+?) x (\d+)")
    item_stats.columns = ["สินค้า", "จำนวน"]
    item_stats["จำนวน"] = item_stats["จำนวน"].astype(int)
    top_items = item_stats.groupby("สินค้า")["จำนวน"].sum().sort_values(ascending=False)
    st.bar_chart(top_items)
