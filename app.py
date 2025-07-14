import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---------- 🎨 CSS ----------
st.markdown("""
<style>
body, .main, .block-container {background:#fff; color:#000;}
.stButton>button {background:#007aff!important; color:#fff!important; border:none; border-radius:10px; padding:0.5em 1.2em;}
.stTextInput input, .stNumberInput input {background:#f2f2f7!important; border-radius:6px; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------- 🛠️ Helper ----------
def safe_key(txt): return txt.replace(" ", "_").replace(".", "_").replace("/", "_").lower()
def safe_int(v):   return int(pd.to_numeric(v, errors="coerce") or 0)
def safe_float(v): return float(pd.to_numeric(v, errors="coerce") or 0.0)
def s_int(v):
    try: return safe_int(safe_float(v))
    except: return 0
def s_float(v):
    try: return safe_float(v)
    except: return 0.0
def inc(p): st.session_state.quantities[p] += 1
def dec(p): st.session_state.quantities[p] = max(1, st.session_state.quantities[p]-1)

# ---------- 🔗 Google Sheet ----------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
ws_items   = sheet.worksheet("ตู้เย็น")
ws_summary = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(ws_items.get_all_records())

# ---------- 💾 Session ----------
default_session = {
    "cart": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "sale_complete": False,
    "auto_add": False,
}
for k, v in default_session.items():
    st.session_state.setdefault(k, v)

if st.session_state.get("sale_complete", False):
    st.success("✅ บันทึกและรีเซ็ตหน้าสำเร็จแล้ว")
    for k in list(default_session):
        st.session_state[k] = default_session[k]
    st.stop()

# ---------- 🛒 เลือกสินค้า ----------
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("🔍 เลือกสินค้า", product_names, key="search_items")

if st.session_state.search_items and not st.session_state.auto_add:
    for p in st.session_state.search_items:
        st.session_state.quantities.setdefault(p, 1)
    st.session_state.cart = [(p, st.session_state.quantities[p]) for p in st.session_state.search_items]
    st.session_state.auto_add = True
    st.experimental_rerun()

for p in st.session_state.search_items:
    qty = st.session_state.quantities[p]
    st.markdown(f"**{p}**")
    col1, col2, col3 = st.columns([1,1,1])
    with col1: st.button("➖", key=f"dec_{safe_key(p)}", on_click=dec, args=(p,))
    with col2: st.markdown(f"<div style='text-align:center;font-size:22px'>{qty}</div>", unsafe_allow_html=True)
    with col3: st.button("➕", key=f"inc_{safe_key(p)}", on_click=inc, args=(p,))

    stock = int(df.loc[df["ชื่อสินค้า"]==p, "คงเหลือในตู้"].values[0])
    color = "red" if stock < 3 else "black"
    st.markdown(f"<span style='color:{color};font-size:18px'>คงเหลือ: {stock}</span>", unsafe_allow_html=True)

# ---------- 📋 ตะกร้า ----------
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price = total_profit = 0
    for item, qty in st.session_state.cart:
        row   = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = s_float(row["ราคาขาย"]); cost = s_float(row["ต้นทุน"])
        subtotal = qty * price;   profit = qty * (price - cost)
        total_price  += subtotal; total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")
    st.info(f"💵 ยอดรวม: {total_price:.2f} | 🟢 กำไร: {total_profit:.2f}")

    st.number_input("💰 รับเงิน", key="paid_input", step=1.0, format="%.2f")

    def add_money(amount: int):
        if not isinstance(st.session_state.paid_input, (int, float)):
            st.session_state.paid_input = 0.0
        st.session_state.paid_input += amount
        st.session_state.last_paid_click = amount

    row1 = st.columns(3); row2 = st.columns(2)
    with row1[0]: st.button("20",  on_click=add_money, args=(20,))
    with row1[1]: st.button("50",  on_click=add_money, args=(50,))
    with row1[2]: st.button("100", on_click=add_money, args=(100,))
    with row2[0]: st.button("500", on_click=add_money, args=(500,))
    with row2[1]: st.button("1000",on_click=add_money, args=(1000,))

    if st.session_state.last_paid_click:
        if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
            st.session_state.paid_input -= st.session_state.last_paid_click
            st.session_state.last_paid_click = 0

    change = st.session_state.paid_input - total_price
    if change >= 0:
        st.success(f"เงินทอน: {change:.2f} บาท")
    else:
        st.warning("💸 เงินรับยังไม่พอ")

    if change >= 0 and st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2
            new_out = safe_int(row["ออก"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) - qty
            ws_items.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
            ws_items.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

        ws_summary.append_row([
            now,
            ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
            total_price,
            total_profit,
            st.session_state.paid_input,
            change,
            "drink"
        ])

        # โหลดข้อมูลใหม่หลังอัปเดต
        df = pd.DataFrame(ws_items.get_all_records())
        st.session_state.sale_complete = True
        st.session_state.auto_add = False
        st.experimental_rerun()
