import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# เชื่อมต่อ Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())

# ตรวจสอบคอลัมน์
expected = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
if not all(col in data.columns for col in expected):
    st.error("❌ ขาดคอลัมน์ที่จำเป็นในชีท")
    st.stop()

# แปลงข้อมูล
for col in ["คงเหลือในตู้", "เข้า", "ออก"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

# ชื่อสินค้า + ค้นหา
st.title("🧊 ระบบขายสินค้าตู้เย็น | เจริญค้า")
st.markdown("---")

st.subheader("🔍 ค้นหาและขายหลายรายการ")
search_term = st.text_input("🔎 พิมพ์ชื่อสินค้าเพื่อค้นหา")
filtered = data[data["ชื่อสินค้า"].str.contains(search_term, case=False)] if search_term else data

quantities = {}
for i, row in filtered.iterrows():
    qty = st.number_input(f"{row['ชื่อสินค้า']} (คงเหลือ {row['คงเหลือในตู้']})", min_value=0, step=1, key=f"qty_{i}")
    if qty > 0:
        quantities[row["ชื่อสินค้า"]] = qty

st.markdown("---")
paid = st.number_input("💵 เงินที่ลูกค้าจ่าย", min_value=0.0, step=1.0)

# คำนวณยอด
total = 0
for item, qty in quantities.items():
    price = float(data.loc[data["ชื่อสินค้า"] == item, "ราคาขาย"])
    total += price * qty
change = paid - total

st.write(f"📦 ยอดรวมทั้งหมด: **{total:,.2f} บาท**")
st.write(f"💰 เงินทอน: **{change:,.2f} บาท**")

# บันทึกการขาย
if st.button("✅ บันทึกการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item, qty in quantities.items():
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        data.at[idx, "ออก"] += qty
        cost = data.at[idx, "ต้นทุน"]
        price = data.at[idx, "ราคาขาย"]
        profit = (price - cost) * qty

        # บันทึกลงชีทยอดขาย
        sheet_sales.append_row([
            now, item, qty, price, cost, price - cost, profit
        ])

    # รีเซตค่าใน UI และอัปเดตกลับชีทหลัก
    for item, qty in quantities.items():
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        data.at[idx, "คงเหลือในตู้"] = data.at[idx, "คงเหลือในตู้"] + data.at[idx, "เข้า"] - data.at[idx, "ออก"]
        data.at[idx, "เข้า"] = 0  # ล้างยอดเข้า
        data.at[idx, "ออก"] = 0  # ล้างยอดออกหลังขาย
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())

    st.success("✅ บันทึกเรียบร้อย + อัปเดตสต๊อก")

    # ใบเสร็จแบบย่อ
    st.markdown("---")
    st.subheader("🧾 ใบเสร็จ")
    for item, qty in quantities.items():
        price = float(data.loc[data["ชื่อสินค้า"] == item, "ราคาขาย"])
        st.write(f"{item} x {qty} = {qty*price:,.2f} บาท")
    st.write(f"**รวม: {total:,.2f} บาท**")
    st.write(f"**รับเงิน: {paid:,.2f} บาท | ทอน: {change:,.2f} บาท**")

# เติมสินค้าเข้าตู้
st.markdown("---")
st.subheader("➕ เติมสินค้าเข้าตู้")
item_to_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"])
qty_to_add = st.number_input("จำนวนที่เติม", min_value=0, step=1)
if st.button("📌 เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == item_to_add].index[0]
    data.at[idx, "เข้า"] += qty_to_add
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {item_to_add} แล้ว +{qty_to_add}")
        
        
