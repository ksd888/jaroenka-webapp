import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# ✅ ตั้งค่าการเชื่อมต่อ Google Sheet
SPREADSHEET_ID = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# ✅ ตรวจสอบและล้างข้อมูลเข้า-ออกทุกวัน
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
except:
    sheet_meta.update("A1", "last_date")
    last_date = ""
if last_date != now_date:
    data = pd.DataFrame(sheet_main.get_all_records())
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    sheet_meta.update("B1", now_date)

# ✅ โหลดข้อมูลสินค้า
data = pd.DataFrame(sheet_main.get_all_records())
data["เข้า"] = pd.to_numeric(data["เข้า"], errors="coerce").fillna(0).astype(int)
data["ออก"] = pd.to_numeric(data["ออก"], errors="coerce").fillna(0).astype(int)
data["คงเหลือในตู้"] = pd.to_numeric(data["คงเหลือในตู้"], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

# ✅ UI
st.set_page_config(page_title="เจริญค้า", layout="wide")
st.title("🧊 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# ✅ ฟอร์มขายหลายรายการ
st.subheader("🛒 ขายหลายรายการ")
selected_items = st.multiselect("ค้นหาสินค้า", options=data["ชื่อสินค้า"].tolist())
quantities = {}
for item in selected_items:
    qty = st.number_input(f"จำนวน {item}", min_value=0, step=1, key=f"qty_{item}")
    quantities[item] = qty

cash_received = st.number_input("💵 รับเงิน (บาท)", min_value=0.0, step=1.0, format="%.2f")

if st.button("✅ บันทึกการขาย"):
    total = 0
    profit_total = 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    for item, qty in quantities.items():
        if qty > 0:
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            price = data.at[idx, "ราคาขาย"]
            cost = data.at[idx, "ต้นทุน"]
            profit = (price - cost) * qty
            total += price * qty
            profit_total += profit
            data.at[idx, "ออก"] += qty
            sheet_sales.append_row([
                now, item, int(qty), float(price), float(cost),
                float(price - cost), float(profit)
            ])
            lines.append(f"{item} x{qty} = {price * qty:.2f} บาท")

    change = cash_received - total
    st.success(f"💰 ยอดรวม: {total:.2f} บาท | เงินทอน: {change:.2f} บาท")
    st.info(f"กำไรรวม: {profit_total:.2f} บาท")
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())

    # ✅ พิมพ์ใบเสร็จ
    receipt = BytesIO()
    c = canvas.Canvas(receipt)
    c.setFont("Helvetica", 12)
    c.drawString(100, 800, "🧾 ใบเสร็จ - เจริญค้า")
    y = 770
    for line in lines:
        c.drawString(100, y, line)
        y -= 20
    c.drawString(100, y - 20, f"รวม: {total:.2f} บาท")
    c.drawString(100, y - 40, f"รับเงิน: {cash_received:.2f} บาท")
    c.drawString(100, y - 60, f"ทอนเงิน: {change:.2f} บาท")
    c.save()
    receipt.seek(0)
    b64 = base64.b64encode(receipt.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="receipt.pdf">🖨️ ดาวน์โหลดใบเสร็จ</a>'
    st.markdown(href, unsafe_allow_html=True)

# ✅ เติมสินค้าเข้าตู้
st.subheader("➕ เติมสินค้าเข้าตู้")
item_to_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add")
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("📦 เติมสินค้า"):
    idx = data[data["ชื่อสินค้า"] == item_to_add].index[0]
    data.at[idx, "เข้า"] += add_qty
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {item_to_add} +{add_qty} สำเร็จ")

# ✅ สรุปยอดขายและกำไร
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()
st.subheader("📊 สรุปยอดขายวันนี้")
st.write(f"ยอดขายรวม: {total_sales:.2f} บาท")
st.write(f"กำไรรวม: {total_profit:.2f} บาท")

# ✅ ตารางสินค้า
st.subheader("📋 สินค้าทั้งหมด")
st.dataframe(data)
