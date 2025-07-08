import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO

# เชื่อมต่อ Google Sheet
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())
expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
for col in expected_columns:
    if col not in data.columns:
        st.error(f"❌ ขาดคอลัมน์ในชีท: {col}")
        st.stop()

for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

# ล้างยอดเข้า/ออกถ้าวันใหม่
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    sheet_meta.update("B1", now_date)

# UI
st.title("🧊 เจริญค้า | ระบบจัดการสินค้าตู้เย็น")

st.subheader("📋 รายการสินค้า")
st.dataframe(data)

st.subheader("➕ เติมสินค้าเข้าตู้")
with st.form("add_stock_form"):
    item_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"])
    qty_add = st.number_input("จำนวนที่เติม", min_value=0, step=1)
    submitted = st.form_submit_button("✅ เติมสต๊อก")
    if submitted:
        idx = data[data["ชื่อสินค้า"] == item_add].index[0]
        data.at[idx, "เข้า"] += qty_add
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
        st.success(f"เติม {item_add} แล้ว")

st.subheader("🛒 ขายสินค้า (หลายรายการ)")
selected_items = st.multiselect("ค้นหาและเลือกสินค้า", data["ชื่อสินค้า"])
sales_data = {}

for item in selected_items:
    qty = st.number_input(f"จำนวนที่ขาย: {item}", min_value=0, step=1, key=f"sell_{item}")
    if qty > 0:
        sales_data[item] = qty

if sales_data:
    total_price = sum(data.loc[data["ชื่อสินค้า"] == i, "ราคาขาย"].values[0] * q for i, q in sales_data.items())
    pay_amount = st.number_input("💵 รับเงิน", min_value=0.0)
    change = pay_amount - total_price
    st.write(f"💰 ยอดรวม: {total_price:,.2f} บาท")
    st.write(f"💸 เงินทอน: {change:,.2f} บาท")

    if st.button("📦 ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in sales_data.items():
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            data.at[idx, "ออก"] += qty
            price = data.at[idx, "ราคาขาย"]
            cost = data.at[idx, "ต้นทุน"]
            profit = (price - cost) * qty
            sheet_sales.append_row([now, item, qty, price, cost, price - cost, profit])
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")

        # พิมพ์ใบเสร็จ
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer)
        c.drawString(100, 800, "🧊 ใบเสร็จร้านเจริญค้า")
        c.drawString(100, 780, now)
        y = 760
        for item, qty in sales_data.items():
            price = data.loc[data["ชื่อสินค้า"] == item, "ราคาขาย"].values[0]
            c.drawString(100, y, f"{item} x{qty} = {qty * price:.2f} บาท")
            y -= 20
        c.drawString(100, y - 10, f"รวม {total_price:.2f} บาท  รับ {pay_amount:.2f} ทอน {change:.2f}")
        c.save()
        st.download_button("🖨️ ดาวน์โหลดใบเสร็จ", data=pdf_buffer.getvalue(), file_name="receipt.pdf")
