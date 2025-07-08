import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# =================== เชื่อม Google Sheet ======================
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# =================== โหลดข้อมูลสินค้า ========================
data = pd.DataFrame(sheet_main.get_all_records())
expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing_columns = [col for col in expected_columns if col not in data.columns]
if missing_columns:
    st.error(f"❌ ขาดคอลัมน์ในชีท: {missing_columns}")
    st.stop()

data["เข้า"] = pd.to_numeric(data["เข้า"], errors="coerce").fillna(0).astype(int)
data["ออก"] = pd.to_numeric(data["ออก"], errors="coerce").fillna(0).astype(int)
data["คงเหลือในตู้"] = pd.to_numeric(data["คงเหลือในตู้"], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

# =============== รีเซตเข้า/ออก ถ้าเป็นวันใหม่ ===============
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_meta.update("B1", now_date)
    st.info("🔄 ข้อมูล 'เข้า/ออก' ถูกรีเซตสำหรับวันใหม่แล้ว")

st.title("📦 ระบบขายหน้าร้าน - เจริญค้า")

# ================ ระบบขายหลายรายการพร้อมคำนวณ ================
st.subheader("🛒 ขายหลายรายการ")
cart = []
with st.form("sell_form"):
    selected_items = st.multiselect("ค้นหาและเลือกสินค้า", options=data["ชื่อสินค้า"].tolist())
    for item in selected_items:
        qty = st.number_input(f"{item} (จำนวน)", min_value=0, step=1, key=item)
        if qty > 0:
            cart.append((item, qty))
    paid = st.number_input("💵 รับเงินมา (บาท)", min_value=0.0, step=1.0)
    submitted = st.form_submit_button("✅ ยืนยันการขาย")

if submitted:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_price = 0
    total_cost = 0
    for item, qty in cart:
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        price = data.at[idx, "ราคาขาย"]
        cost = data.at[idx, "ต้นทุน"]
        data.at[idx, "ออก"] += qty
        total_price += price * qty
        total_cost += cost * qty
        sheet_sales.append_row([
            now, item, int(qty), float(price), float(cost),
            float(price - cost), float((price - cost) * qty)
        ])
    change = paid - total_price
    st.success(f"✅ ยอดขายรวม: {total_price:.2f} บาท | เงินทอน: {change:.2f} บาท")

    # พิมพ์ใบเสร็จ PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer)
    c.drawString(100, 800, "🧾 ใบเสร็จ - ร้านเจริญค้า")
    c.drawString(100, 780, f"วันที่: {now}")
    y = 760
    for item, qty in cart:
        c.drawString(100, y, f"{item} x {qty}")
        y -= 20
    c.drawString(100, y - 10, f"รวม: {total_price:.2f} บาท | ทอน: {change:.2f} บาท")
    c.save()
    st.download_button("📄 ดาวน์โหลดใบเสร็จ", data=pdf_buffer.getvalue(), file_name="receipt.pdf")

    # อัปเดตกลับชีท
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())

# =============== เติมสินค้า ===============
st.subheader("➕ เติมสินค้าเข้าตู้")
add_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add")
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == add_name].index[0]
    data.at[idx, "เข้า"] += add_qty
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {add_name} +{add_qty} เรียบร้อย")

# =============== แสดงยอดขายรวม ===============
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.subheader("📊 สรุปยอดวันนี้")
st.metric("ยอดขายรวม (บาท)", f"{total_sales:,.2f}")
st.metric("กำไรรวม (บาท)", f"{total_profit:,.2f}")

# =============== แสดงตารางสินค้า ===============
st.subheader("📋 รายการสินค้า")
st.dataframe(data)
