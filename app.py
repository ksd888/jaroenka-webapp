
import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# เชื่อมต่อ GCP
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# ตรวจสอบวันใหม่
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
    if last_date != now_date:
        data_reset = pd.DataFrame(sheet_main.get_all_records())
        if "เข้า" in data_reset.columns and "ออก" in data_reset.columns:
            data_reset["เข้า"] = 0
            data_reset["ออก"] = 0
            sheet_main.update([data_reset.columns.values.tolist()] + data_reset.values.tolist())
        sheet_meta.update("B1", now_date)
except:
    sheet_meta.update("A1", "last_date")
    sheet_meta.update("B1", now_date)

# โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())
for col in ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]:
    if col not in data.columns:
        st.error(f"❌ ขาดคอลัมน์: {col}")
        st.stop()

for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# ✅ ขายหลายรายการ
st.subheader("🛒 ขายหลายรายการ")
selected_items = st.multiselect("ค้นหาและเลือกสินค้า", data["ชื่อสินค้า"])
quantities = {}
col1, col2 = st.columns([3, 1])
for item in selected_items:
    quantities[item] = col1.number_input(f"{item}", min_value=0, step=1, key=f"sell_{item}")

paid = col2.number_input("💰 รับเงิน (บาท)", min_value=0.0, step=1.0)

if st.button("✅ บันทึกการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_price = 0
    for item in selected_items:
        qty = quantities[item]
        if qty > 0:
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            if data.at[idx, "คงเหลือในตู้"] >= qty:
                data.at[idx, "ออก"] += qty
                data.at[idx, "คงเหลือในตู้"] -= qty
                profit = (data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]) * qty
                sheet_sales.append_row([now, item, qty, float(data.at[idx, "ราคาขาย"]),
                                        float(data.at[idx, "ต้นทุน"]), float(data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]),
                                        float(profit)])
                total_price += data.at[idx, "ราคาขาย"] * qty
            else:
                st.warning(f"สินค้า {item} ไม่พอขาย")
    change = paid - total_price
    st.success(f"💸 ยอดรวม: {total_price:.2f} บาท | เงินทอน: {change:.2f} บาท")
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.experimental_rerun()

# ✅ เติมสินค้า
st.subheader("➕ เติมสินค้าเข้าตู้")
selected_fill = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"].unique())
fill_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="fill_qty")
if st.button("📦 เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == selected_fill].index[0]
    data.at[idx, "เข้า"] += fill_qty
    data.at[idx, "คงเหลือในตู้"] += fill_qty
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {selected_fill} +{fill_qty}")
    st.experimental_rerun()

# ✅ ใบเสร็จ PDF
def generate_receipt(sales):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 800, "🧾 ใบเสร็จร้านเจริญค้า")
    y = 780
    total = 0
    for i, (item, qty) in enumerate(sales.items()):
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        price = data.at[idx, "ราคาขาย"]
        line = f"{item} x {qty} = {price * qty:.2f}"
        c.drawString(100, y - i * 20, line)
        total += price * qty
    c.drawString(100, y - (len(sales) + 1) * 20, f"รวมทั้งหมด: {total:.2f} บาท")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

st.subheader("🖨️ พิมพ์ใบเสร็จ")
if selected_items and st.button("🧾 ดาวน์โหลดใบเสร็จ"):
    sales = {item: quantities[item] for item in selected_items if quantities[item] > 0}
    if sales:
        receipt = generate_receipt(sales)
        b64 = base64.b64encode(receipt.getvalue()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="receipt.pdf">📄 ดาวน์โหลดใบเสร็จ (PDF)</a>'
        st.markdown(href, unsafe_allow_html=True)
