import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# 🔐 เชื่อมต่อ Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ Sheet สำหรับจัดการวันที่รีเซต
try:
    sheet_meta = spreadsheet.worksheet("Meta")
except:
    sheet_meta = spreadsheet.add_worksheet(title="Meta", rows="10", cols="5")
    sheet_meta.update("A1", "last_date")
    sheet_meta.update("B1", datetime.date.today().isoformat())

# 🗓 รีเซตข้อมูลเมื่อวันใหม่
now_date = datetime.date.today().isoformat()
last_date = sheet_meta.acell("B1").value

if last_date != now_date:
    data = pd.DataFrame(sheet_main.get_all_records())
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    sheet_meta.update("B1", now_date)

# 📦 โหลดข้อมูลสินค้า
data = pd.DataFrame(sheet_main.get_all_records())
for col in ["เข้า", "ออก", "คงเหลือในตู้", "ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# 🖼 UI
st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")
st.title("🧊 ระบบขายสินค้าตู้เย็น - ร้านเจริญค้า")

# 🛒 ขายหลายรายการ
st.header("🛍 ขายหลายรายการ")
selected_items = st.multiselect("ค้นหาและเลือกสินค้า", data["ชื่อสินค้า"].tolist())
quantities = {}

if selected_items:
    for item in selected_items:
        qty = st.number_input(f"จำนวนที่ขาย - {item}", min_value=0, step=1, key=f"sell_{item}")
        quantities[item] = qty

amount_paid = st.number_input("💵 รับเงินจากลูกค้า (บาท)", min_value=0.0, step=1.0)

if st.button("✅ บันทึกการขาย"):
    total_price = 0
    total_profit = 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item, qty in quantities.items():
        if qty == 0:
            continue
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        if data.at[idx, "คงเหลือในตู้"] >= qty:
            data.at[idx, "ออก"] += qty
            data.at[idx, "คงเหลือในตู้"] -= qty
            profit_unit = data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]
            profit = qty * profit_unit
            total_price += qty * data.at[idx, "ราคาขาย"]
            total_profit += profit
            sheet_sales.append_row([
                now, item, qty,
                float(data.at[idx, "ราคาขาย"]),
                float(data.at[idx, "ต้นทุน"]),
                float(profit_unit),
                float(profit)
            ])
        else:
            st.warning(f"❗ สินค้า {item} ไม่พอขาย (เหลือ {data.at[idx, 'คงเหลือในตู้']})")

    change = amount_paid - total_price
    st.success(f"✅ ยอดรวม: {total_price:,.2f} บาท | 💸 ทอนเงิน: {change:,.2f} บาท")

    # อัปเดตกลับชีท
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())

    # 🧾 ใบเสร็จ PDF
    pdf = BytesIO()
    c = canvas.Canvas(pdf)
    c.setFont("Helvetica", 12)
    c.drawString(200, 800, "🧊 ใบเสร็จร้านเจริญค้า")
    c.drawString(100, 780, f"วันที่: {now}")
    y = 750
    for item, qty in quantities.items():
        if qty > 0:
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            price = data.at[idx, "ราคาขาย"]
            c.drawString(100, y, f"{item} x {qty} = {qty * price:.2f} บาท")
            y -= 20
    c.drawString(100, y - 20, f"รวมทั้งสิ้น: {total_price:.2f} บาท")
    c.drawString(100, y - 40, f"เงินทอน: {change:.2f} บาท")
    c.save()
    b64 = base64.b64encode(pdf.getvalue()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="receipt.pdf">🖨 ดาวน์โหลดใบเสร็จ</a>'
    st.markdown(href, unsafe_allow_html=True)

# ➕ เติมสินค้า
st.header("📦 เติมสินค้าเข้าตู้")
col1, col2 = st.columns(2)
with col1:
    item_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add_select")
with col2:
    qty_add = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")

if st.button("📌 เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == item_add].index[0]
    data.at[idx, "เข้า"] += qty_add
    data.at[idx, "คงเหลือในตู้"] += qty_add
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {item_add} แล้ว +{qty_add}")

# 📊 สรุปยอดขาย
st.header("📊 สรุปวันนี้")
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()
st.metric("ยอดขายรวม", f"{total_sales:,.2f} บาท")
st.metric("กำไรรวม", f"{total_profit:,.2f} บาท")

# 📋 แสดงตาราง
st.dataframe(data, use_container_width=True)
