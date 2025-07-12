import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GCP_SERVICE_ACCOUNT"], scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")

sheet = spreadsheet.worksheet("ตู้เย็น")
df = pd.DataFrame(sheet.get_all_records())

# Initialize session state
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "timestamp" not in st.session_state:
    st.session_state.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

st.subheader("🛒 เลือกสินค้า")

for idx, row in df.iterrows():
    item = row["ชื่อสินค้า"]
    price = row["ราคาขาย"]
    
    col1, col2, col3, col4 = st.columns([4, 1, 1, 2])
    with col1:
        st.markdown(f"**{item}** ({price}฿)")
    with col2:
        if st.button("➖", key=f"dec_{item}"):
            if item in st.session_state.cart and st.session_state.cart[item] > 0:
                st.session_state.cart[item] -= 1
    with col3:
        if st.button("➕", key=f"inc_{item}"):
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
    with col4:
        qty = st.session_state.cart.get(item, 0)
        st.markdown(f"**จำนวน:** {qty}")

# แสดงตะกร้าสินค้า
st.subheader("🧾 ตะกร้าสินค้า")
cart = st.session_state.cart
if cart:
    total = 0
    cart_items = []
    for item, qty in cart.items():
        if qty > 0:
            price = df[df["ชื่อสินค้า"] == item]["ราคาขาย"].values[0]
            total += price * qty
            cart_items.append((item, qty, price, qty * price))
    cart_df = pd.DataFrame(cart_items, columns=["สินค้า", "จำนวน", "ราคาต่อหน่วย", "รวม"])
    st.table(cart_df)
    st.markdown(f"### 💰 ยอดรวม: {total} บาท")

    money_received = st.number_input("💵 รับเงินมา (บาท)", min_value=0, value=total)
    change = money_received - total
    if change < 0:
        st.warning("💡 เงินไม่พอสำหรับชำระ")
    else:
        st.success(f"เงินทอน: {change} บาท")

    if st.button("✅ ยืนยันการขาย"):
        sheet_out = spreadsheet.worksheet("ยอดขาย")
        for item, qty, price, subtotal in cart_items:
            sheet_out.append_row([
                st.session_state.timestamp,
                item,
                qty,
                price,
                subtotal,
                "drink"
            ])
        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
        st.session_state.cart = {}  # Reset cart
        st.experimental_rerun()

else:
    st.info("🛒 ยังไม่มีสินค้าถูกเลือกในตะกร้า")
