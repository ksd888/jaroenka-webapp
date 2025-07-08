# app.py (เวอร์ชันเต็มล่าสุด)
import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# เชื่อมต่อ Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
try:
    sheet_meta = spreadsheet.worksheet("Meta")
except:
    sheet_meta = spreadsheet.add_worksheet(title="Meta", rows="1", cols="2")
    sheet_meta.update("A1:B1", [["last_date", datetime.date.today().isoformat()]])

# ตรวจสอบวันใหม่
last_date = sheet_meta.acell("B1").value
today = datetime.date.today().isoformat()
if last_date != today:
    df_reset = pd.DataFrame(sheet_main.get_all_records())
    if "เข้า" in df_reset.columns and "ออก" in df_reset.columns:
        df_reset["เข้า"] = 0
        df_reset["ออก"] = 0
        sheet_main.update([df_reset.columns.values.tolist()] + df_reset.values.tolist())
    sheet_meta.update("B1", today)

# โหลดข้อมูลสินค้า
data = pd.DataFrame(sheet_main.get_all_records())
for col in ["เข้า", "ออก", "คงเหลือในตู้", "ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# UI
st.set_page_config(layout="wide")
st.title("📦 ระบบขายสินค้าตู้เย็นเจริญค้า")

# ช่องขายหลายรายการ
st.subheader("🛒 ขายหลายรายการ")
selected_items = st.multiselect("ค้นหาสินค้า", data["ชื่อสินค้า"].tolist())
sales = []
total = 0

for item in selected_items:
    col1, col2 = st.columns([2, 1])
    with col1:
        qty = st.number_input(f"จำนวน {item}", min_value=0, step=1, key=f"qty_{item}")
    with col2:
        price = data.loc[data["ชื่อสินค้า"] == item, "ราคาขาย"].values[0]
        st.write(f"ราคาขาย: {price} บาท")
    sales.append({"name": item, "qty": qty, "price": price})
    total += qty * price

# สรุปยอดขาย
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"💰 ยอดรวม: {total:,.2f} บาท")
with col2:
    cash = st.number_input("รับเงินมา", min_value=0.0, step=1.0)
    if cash >= total:
        change = cash - total
        st.subheader(f"💸 เงินทอน: {change:,.2f} บาท")

# ปุ่มบันทึกยอดขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for s in sales:
        if s["qty"] > 0:
            idx = data[data["ชื่อสินค้า"] == s["name"]].index[0]
            data.at[idx, "ออก"] += s["qty"]
            profit_unit = data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]
            profit = s["qty"] * profit_unit
            # บันทึกยอดขาย
            sheet_sales.append_row([
                now, s["name"], s["qty"], s["price"],
                float(data.at[idx, "ต้นทุน"]),
                float(profit_unit),
                float(profit)
            ])
    # อัปเดตข้อมูลหลังขาย
    data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
    sheet_main.update([data.columns.tolist()] + data.values.tolist())
    st.success("✅ บันทึกและอัปเดตยอดขายเรียบร้อยแล้ว")
    st.experimental_rerun()

# เติมสินค้า
st.subheader("➕ เติมสินค้า")
with st.form("เติมสินค้า"):
    item_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"])
    qty_add = st.number_input("จำนวนที่เติม", min_value=1, step=1)
    submitted = st.form_submit_button("เติมสินค้า")
    if submitted:
        idx = data[data["ชื่อสินค้า"] == item_add].index[0]
        data.at[idx, "เข้า"] += qty_add
        data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
        sheet_main.update([data.columns.tolist()] + data.values.tolist())
        st.success(f"✅ เติมสินค้า {item_add} จำนวน {qty_add} สำเร็จ")

# พิมพ์ใบเสร็จ
if st.button("🧾 พิมพ์ใบเสร็จ"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.drawString(100, height - 50, "🧾 ใบเสร็จร้านเจริญค้า")
    y = height - 100
    for s in sales:
        if s["qty"] > 0:
            c.drawString(100, y, f"{s['name']} x{s['qty']} = {s['qty'] * s['price']} บาท")
            y -= 20
    c.drawString(100, y - 20, f"รวมทั้งหมด: {total:,.2f} บาท")
    if cash >= total:
        c.drawString(100, y - 40, f"รับเงิน: {cash:,.2f} บาท")
        c.drawString(100, y - 60, f"เงินทอน: {change:,.2f} บาท")
    c.showPage()
    c.save()
    st.download_button("📥 ดาวน์โหลดใบเสร็จ (PDF)", data=buffer.getvalue(), file_name="receipt.pdf")

# ตารางข้อมูล
st.markdown("---")
st.subheader("📊 สรุปข้อมูลสินค้า")
st.dataframe(data)
