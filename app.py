import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO

# ✅ เชื่อม Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# ✅ รีเซ็ตรายวันอัตโนมัติ
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
    if last_date != now_date:
        sheet.batch_update([{
            "range": "ตู้เย็น!F2:G",
            "values": [["", ""] for _ in range(100)]
        }])
        sheet_meta.update("B1", [[now_date]])
except:
    sheet_meta.update("A1", [["last_date"]])
    sheet_meta.update("B1", [[now_date]])

# ✅ โหลดข้อมูลสินค้า
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ✅ ค้นหา + ขายหลายรายการ
st.title("💼 ระบบขายสินค้า | ร้านเจริญค้า")
st.markdown("## 🛒 เลือกสินค้าหลายรายการพร้อมกัน")

selected_items = []
col1, col2 = st.columns([2, 1])
with col1:
    search_query = st.text_input("🔍 ค้นหาสินค้า").strip().lower()

with col2:
    money_received = st.number_input("💵 รับเงินจากลูกค้า (บาท)", min_value=0.0, step=1.0, value=0.0)

for index, row in df.iterrows():
    name = row["ชื่อสินค้า"]
    if search_query in name.lower():
        col1, col2 = st.columns([2, 1])
        with col1:
            qty = st.number_input(f"{name} (คงเหลือ {row['คงเหลือในตู้']})", min_value=0, step=1, key=name)
        with col2:
            if qty > 0:
                selected_items.append({
                    "index": index,
                    "name": name,
                    "qty": qty,
                    "price": row["ราคาขาย"],
                    "cost": row["ต้นทุน"]
                })

# ✅ คำนวณยอดขาย
total = sum(item["qty"] * item["price"] for item in selected_items)
total_cost = sum(item["qty"] * item["cost"] for item in selected_items)
profit = total - total_cost
change = money_received - total

st.markdown(f"### 💰 ยอดรวม: {total:.2f} บาท")
st.markdown(f"### 💵 ทอนเงินลูกค้า: {change:.2f} บาท" if change >= 0 else "❌ เงินไม่พอ")

# ✅ ปุ่มยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in selected_items:
        idx = item["index"] + 2  # เพราะมี header 1 บรรทัด
        # ✅ อัปเดตยอดออก
        qty_old = df.loc[item["index"], "ออก"]
        new_qty = qty_old + item["qty"]
        sheet.update_cell(idx, 7, new_qty)
        # ✅ อัปเดตคงเหลือในตู้
        remain = df.loc[item["index"], "คงเหลือในตู้"] - item["qty"]
        sheet.update_cell(idx, 8, remain)
        # ✅ บันทึกลงยอดขาย
        sheet_sales.append_row([
            now, item["name"], item["qty"], item["price"], item["cost"],
            item["price"] - item["cost"], item["qty"] * (item["price"] - item["cost"])
        ])

    st.success("✅ บันทึกยอดขายและอัปเดตคงเหลือเรียบร้อยแล้ว")
    st.experimental_rerun()

# ✅ ปุ่มเติมสินค้า
st.markdown("---")
st.markdown("### ➕ เติมสินค้าเข้าตู้")
product_options = df["ชื่อสินค้า"].tolist()
product_selected = st.selectbox("เลือกสินค้า", product_options)
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1)
if st.button("📦 เติมสินค้า"):
    index = df[df["ชื่อสินค้า"] == product_selected].index[0]
    idx_excel = index + 2
    old_in = df.loc[index, "เข้า"]
    old_remain = df.loc[index, "คงเหลือในตู้"]
    sheet.update_cell(idx_excel, 6, old_in + add_qty)
    sheet.update_cell(idx_excel, 8, old_remain + add_qty)
    st.success(f"✅ เติมสินค้า {product_selected} สำเร็จ")
    st.experimental_rerun()

# ✅ ปุ่มพิมพ์ใบเสร็จ
if selected_items and st.button("🧾 พิมพ์ใบเสร็จ"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 800, "🧊 ใบเสร็จร้านเจริญค้า")
    y = 780
    for item in selected_items:
        c.drawString(100, y, f"{item['name']} x {item['qty']} = {item['qty'] * item['price']} บาท")
        y -= 20
    c.drawString(100, y-10, f"รวมทั้งหมด: {total} บาท")
    c.drawString(100, y-30, f"เงินรับ: {money_received} บาท")
    c.drawString(100, y-50, f"เงินทอน: {change} บาท")
    c.showPage()
    c.save()
    st.download_button("📥 ดาวน์โหลดใบเสร็จ (PDF)", data=buffer.getvalue(), file_name="receipt.pdf")
