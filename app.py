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
def s_int(v):      # safe_safe_int
    try: return safe_int(safe_float(v))
    except: return 0
def s_float(v):    # safe_safe_float
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
}
for k, v in default_session.items():
    st.session_state.setdefault(k, v)

if st.session_state.sale_complete:
    for k, v in default_session.items():
        st.session_state[k] = v
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

# ---------- 🛒 เลือกสินค้า ----------
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
st.multiselect("🔍 เลือกสินค้า", product_names, key="search_items")

for p in st.session_state.search_items:
    st.session_state.quantities.setdefault(p, 1)
    qty = st.session_state.quantities[p]

    st.markdown(f"**{p}**")
    col1, col2, col3 = st.columns([1,1,1])
    with col1: st.button("➖", key=f"dec_{safe_key(p)}", on_click=dec, args=(p,))
    with col2: st.markdown(f"<div style='text-align:center;font-size:22px'>{qty}</div>", unsafe_allow_html=True)
    with col3: st.button("➕", key=f"inc_{safe_key(p)}", on_click=inc, args=(p,))

    stock = int(df.loc[df["ชื่อสินค้า"]==p, "คงเหลือในตู้"].values[0])
    color = "red" if stock < 3 else "black"
    st.markdown(f"<span style='color:{color};font-size:18px'>คงเหลือ: {stock}</span>", unsafe_allow_html=True)

# ---------- ➕ เพิ่มลงตะกร้า ----------
if st.button("➕ เพิ่มลงตะกร้า"):
    for p in st.session_state.search_items:
        qty = s_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

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

    # ---------- 💰 รับเงิน (number_input ผูกกับ key) ----------
    st.number_input("💰 รับเงิน", key="paid_input", step=1.0, format="%.2f")

    # ---------- 💸 ปุ่มเงินลัด ----------
    def add_money(amount: int):
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

    # ---------- เงินทอน realtime ----------
    change = st.session_state.paid_input - total_price
    if change >= 0:
        st.success(f"เงินทอน: {change:.2f} บาท")
    else:
        st.warning("💸 เงินรับยังไม่พอ")

    # ---------- ✅ ยืนยันการขาย ----------
    if change >= 0 and st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            ws_summary.append_row([now, item, qty])
        st.session_state.sale_complete = True
        st.success("✅ บันทึกเรียบร้อยแล้ว กำลังรีเซ็ต...")
