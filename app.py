import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from reportlab.pdfgen import canvas
import io
import base64

# Auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)

# ใช้ Spreadsheet ID โดยตรง
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# ตรวจสอบวันใหม่ (รีเซตยอดเข้า/ออก)
now_date = datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
except:
    last_date = ""

if last_date != now_date:
    sheet.update("F2:F", [[""]]*sheet.row_count)  # ล้างคอลัมน์ 'เข้า'
    sheet.update("G2:G", [[""]]*sheet.row_count)  # ล้างคอลัมน์ 'ออก'
    sheet_meta.update("B1", [[now_date]])

# ดึงข้อมูลสินค้า
data = sheet.get_all_records()

st.set_page_config(page_title="เจริญค้า | ตู้เย็น", layout="wide")
st.title("📦 ระบบขายสินค้าตู้เย็น - เจริญค้า")

# ค้นหา
search = st.text_input("🔍 ค้นหาสินค้า", "")

# ขายหลายรายการพร้อมกัน
st.subheader("🛒 ขายสินค้าหลายรายการ")
selected = []
quantities = {}

for item in data:
    name = item["ชื่อสินค้า"]
    if search.lower() in name.lower():
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_item = st.checkbox(name)
        with col2:
            qty = st.number_input(f"จำนวน - {name}", min_value=0, step=1, key=name)
        if selected_item and qty > 0:
            selected.append(item)
            quantities[name] = qty

if selected:
    total_price = 0
    total_cost = 0
    st.markdown("### 💰 รายการที่เลือกขาย")
    for item in selected:
        name = item["ชื่อสินค้า"]
        qty = quantities[name]
        price = float(item["ราคาขาย"])
        cost = float(item["ต้นทุน"])
        total_price += price * qty
        total_cost += cost * qty
        st.write(f"{name} x {qty} = {price * qty:.2f} บาท")

    st.markdown(f"### 💵 ยอดรวม: **{total_price:.2f} บาท**")
    cash_received = st.number_input("💸 รับเงินจากลูกค้า", min_value=0.0, value=total_price, step=1.0)
    change = cash_received - total_price
    st.success(f"เงินทอน: {change:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in selected:
            name = item["ชื่อสินค้า"]
            qty = quantities[name]
            for idx, row in enumerate(data, start=2):
                if row["ชื่อสินค้า"] == name:
                    current_out = int(row["ออก"]) if row["ออก"] else 0
                    new_out = current_out + qty
                    sheet.update_cell(idx, 7, str(new_out))  # คอลัมน์ G: ออก
                    remain = int(row["คงเหลือ"]) if row["คงเหลือ"] else 0
                    sheet.update_cell(idx, 5, str(remain - qty))  # คอลัมน์ E: คงเหลือ
                    break
            sheet_sales.append_row([now, name, qty, item["ราคาขาย"], item["ต้นทุน"], total_price, total_price - total_cost, "retail"])

        st.success("✅ บันทึกยอดขายเรียบร้อย")

        # PDF ใบเสร็จ
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 800, "ใบเสร็จ - ร้านเจริญค้า")
        y = 770
        for item in selected:
            name = item["ชื่อสินค้า"]
            qty = quantities[name]
            price = float(item["ราคาขาย"])
            c.drawString(100, y, f"{name} x {qty} = {price * qty:.2f} บาท")
            y -= 20
        c.drawString(100, y - 10, f"รวมทั้งหมด: {total_price:.2f} บาท")
        c.drawString(100, y - 30, f"รับเงิน: {cash_received:.2f} บาท")
        c.drawString(100, y - 50, f"เงินทอน: {change:.2f} บาท")
        c.save()

        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="receipt.pdf">📄 ดาวน์โหลดใบเสร็จ</a>'
        st.markdown(href, unsafe_allow_html=True)
