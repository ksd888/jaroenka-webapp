import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd


def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)


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

# 🧠 ฟังก์ชันช่วยอ่านค่าปลอดภัย
def safe_safe_int(val): 
    try:
        return safe_int(safe_float(val))
    except (TypeError, ValueError):
        return 0

def safe_safe_float(val): 
    try:
        return safe_float(val)
    except (TypeError, ValueError):
        return 0.0

# 🧊 ค่าเริ่มต้น session_state
default_session = {
    "cart": [],
    "selected_products": [],
    "quantities": {},
    "paid_input": 0.0,
    "sale_complete": False
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 🔁 รีเซ็ตเมื่อขายเสร็จ
if st.session_state.sale_complete:
    for key, default in default_session.items():
        st.session_state[key] = default
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

# 🔍 ค้นหาและเพิ่มสินค้าเข้าตะกร้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

product_names = df["ชื่อสินค้า"].tolist()
# selected =  # ⚠️ แก้ไข: ไม่มีค่าต่อท้าย เดิม Error
default_selected = []
if "reset_search_items" in st.session_state:
    default_selected = []
    del st.session_state["reset_search_items"]
else:
    default_selected = st.session_state.get("search_items", [])

st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names, default=default_selected, key="search_items")

for p in selected:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    cols = st.columns([2, 1, 1])
    with cols[0]: st.markdown(f"**{p}**")
    with cols[1]:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    with cols[2]:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1

if st.button("➕ เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_safe_int(st.session_state.quantities[p])
        if qty > 0:
            st.session_state.cart.append((p, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# 🧾 แสดงตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
        subtotal, profit = qty * price, qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
    if st.session_state.paid_input >= total_price:
        st.success(f"เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("💸 ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):


        st.session_state["reset_search_items"] = True  # set flag to reset multiselect on rerun


        st.session_state["search_query"] = ""  # reset search

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2  # Google Sheet starts at row 2
            new_out = safe_safe_int(row["ออก"]) + qty
            new_left = safe_safe_int(row["คงเหลือในตู้"]) - qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

        # บันทึกยอดขาย
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
        st.rerun()

# 📥 เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock_select")
    restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติมสินค้า"):
        index = df[df["ชื่อสินค้า"] == restock_item].index[0]
        idx_in_sheet = index + 2
        row = df.loc[index]
        new_in = safe_safe_int(row["เข้า"]) + restock_qty
        new_left = safe_safe_int(row["คงเหลือในตู้"]) + restock_qty
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
        st.success(f"✅ เติม {restock_item} แล้ว")

# ✏️ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_select")
    index = df[df["ชื่อสินค้า"] == edit_item].index[0]
    idx_in_sheet = index + 2
    row = df.loc[index]
    new_price = st.number_input("ราคาขาย", value=safe_safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุน", value=safe_safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือในตู้", value=safe_safe_int(row["คงเหลือในตู้"]), key="edit_stock", step=1)
    if st.button("💾 บันทึกการแก้ไข"):
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
        st.success(f"✅ อัปเดต {edit_item} แล้ว")
