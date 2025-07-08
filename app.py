import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
from reportlab.pdfgen import canvas
import io

# Auth
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"]
)
gc = gspread.authorize(credentials)

# ใช้ Spreadsheet ID
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")  # ใช้เก็บวันที่ล่าสุด

# ตรวจสอบวันใหม่ และรีเซตยอดเข้าออก
now_date = datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
    if last_date != now_date:
        sheet.update("F2:F", [[""]]*1000)  # รีเซตเข้า
        sheet.update("G2:G", [[""]]*1000)  # รีเซตออก
        sheet_meta.update("B1", [[now_date]])
except:
    sheet_meta.update("A1", [[ "last_date" ]])
    sheet_meta.update("B1", [[now_date]])

# ดึงรายการสินค้า
data = sheet.get_all_records()
product_names = [row["ชื่อสินค้า"] for row in data]

st.title("💼 ร้านเจริญค้า (ตู้เย็น)")

st.markdown("### 🛒 ขายสินค้าหลายรายการ")

selected_items = st.multiselect("🔍 ค้นหาสินค้า", product_names)
quantities = {}
for item in selected_items:
    qty = st.number_input(f"จำนวนที่ขาย: {item}", min_value=1, step=1, key=f"qty_{item}")
    quantities[item] = qty

customer_paid = st.number_input("💵 ลูกค้าชำระเงิน (บาท)", min_value=0.0, step=1.0)

# ปุ่มขายสินค้า
if st.button("✅ ขายสินค้า"):
    total = 0
    total_cost = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_lines = []

    for item, qty in quantities.items():
        for row_idx, row in enumerate(data, start=2):
            if row["ชื่อสินค้า"] == item:
                price = row["ราคาขาย"]
                cost = row["ต้นทุน"]
                profit = (price - cost) * qty
                total += price * qty
                total_cost += cost * qty

                # อัปเดตคอลัมน์ 'ออก' และ 'คงเหลือในตู้'
                new_out = row["ออก"] + qty if isinstance(row["ออก"], int) else qty
                remaining = row["คงเหลือ"] + row["เข้า"] - new_out

                sheet.update(f"G{row_idx}", new_out)
                sheet.update(f"H{row_idx}", remaining)

                # บันทึกลงชีทยอดขาย
                sheet_sales.append_row([
                    now, item, qty, price, cost, price - cost, profit
                ])
                summary_lines.append(f"{item} x{qty} = {price * qty} บาท")
                break

    change = customer_paid - total
    st.success(f"✅ ยอดรวม: {total:.2f} บาท / เงินทอน: {change:.2f} บาท")

    # พิมพ์ใบเสร็จ PDF
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 800, f"ใบเสร็จร้านเจริญค้า")
    pdf.drawString(100, 780, f"วันที่: {now}")
    y = 750
    for line in summary_lines:
        pdf.drawString(100, y, line)
        y -= 20
    pdf.drawString(100, y-20, f"รวมทั้งสิ้น: {total:.2f} บาท")
    pdf.drawString(100, y-40, f"เงินทอน: {change:.2f} บาท")
    pdf.save()

    st.download_button("📄 ดาวน์โหลดใบเสร็จ PDF", data=buffer.getvalue(), file_name="receipt.pdf")

    # รีเฟรชหน้า
    st.experimental_rerun()

# เติมสินค้า
st.markdown("### ➕ เติมสินค้าเข้าตู้")
with st.expander("📦 เลือกสินค้าเพื่อเติม"):
    for i, row in enumerate(data, start=2):
        qty = st.number_input(f"เติม {row['ชื่อสินค้า']}", min_value=0, step=1, key=f"in_{i}")
        if qty > 0:
            new_in = row["เข้า"] + qty if isinstance(row["เข้า"], int) else qty
            sheet.update(f"F{i}", new_in)
            remaining = row["คงเหลือ"] + new_in - row["ออก"]
            sheet.update(f"H{i}", remaining)
            st.success(f"✅ เติม {row['ชื่อสินค้า']} จำนวน {qty} แล้ว")
