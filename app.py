import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# ===== เชื่อมต่อ GCP =====
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")
sheet_meta = spreadsheet.worksheet("Meta")

# ===== โหลดข้อมูล + ตรวจสอบคอลัมน์ =====
data = pd.DataFrame(sheet_main.get_all_records())
expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
for col in expected_columns:
    if col not in data.columns:
        st.error(f"❌ ขาดคอลัมน์: {col}")
        st.stop()

# ===== แปลงชนิดข้อมูล =====
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# ===== รีเซตยอดเข้า/ออกถ้าวันใหม่ =====
now_date = datetime.date.today().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
except:
    last_date = ""

if last_date != now_date:
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_meta.update("B1", now_date)
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("🔄 เริ่มต้นวันใหม่: รีเซตค่าเข้า/ออกแล้ว")

# ===== UI =====
st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")
st.markdown("💡 *รองรับหลายรายการ, เติมสินค้า, คิดเงินทอน และพิมพ์ใบเสร็จ*")

# ===== ฟีเจอร์: ขายหลายรายการพร้อมกัน =====
st.subheader("🛒 ขายหลายรายการ")
selected_items = st.multiselect("🔍 ค้นหาสินค้า", data["ชื่อสินค้า"].tolist())
sale_dict = {}
for item in selected_items:
    qty = st.number_input(f"จำนวน {item}", min_value=0, step=1, key=f"qty_{item}")
    if qty > 0:
        sale_dict[item] = qty

if sale_dict:
    total = sum(data.loc[data["ชื่อสินค้า"] == k, "ราคาขาย"].values[0] * v for k, v in sale_dict.items())
    st.info(f"💰 ยอดรวม: {total:.2f} บาท")
    cash = st.number_input("💵 รับเงิน", min_value=0.0, step=1.0)
    if cash >= total:
        change = cash - total
        st.success(f"✅ ทอนเงิน: {change:.2f} บาท")
    else:
        st.warning("⚠️ รับเงินยังไม่พอ")

    if st.button("💾 ยืนยันขายและบันทึก"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item, qty in sale_dict.items():
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            data.at[idx, "ออก"] += qty
            data.at[idx, "คงเหลือในตู้"] -= qty
            price = data.at[idx, "ราคาขาย"]
            cost = data.at[idx, "ต้นทุน"]
            profit = (price - cost) * qty
            sheet_sales.append_row([now, item, qty, price, cost, price - cost, profit])
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
        st.success("✅ บันทึกขายเสร็จสิ้น")
        st.experimental_rerun()

# ===== เติมสินค้า =====
st.subheader("➕ เติมสินค้า")
item_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add_item")
qty_add = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("📌 เติมสินค้า"):
    idx = data[data["ชื่อสินค้า"] == item_add].index[0]
    data.at[idx, "เข้า"] += qty_add
    data.at[idx, "คงเหลือในตู้"] += qty_add
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {item_add} +{qty_add}")
    st.experimental_rerun()

# ===== พิมพ์ใบเสร็จ (PDF) =====
st.subheader("🧾 พิมพ์ใบเสร็จ")
if sale_dict:
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer)
    c.drawString(100, 800, f"ใบเสร็จร้านเจริญค้า ({datetime.datetime.now().strftime('%d/%m/%Y')})")
    y = 770
    for item, qty in sale_dict.items():
        price = data.loc[data["ชื่อสินค้า"] == item, "ราคาขาย"].values[0]
        c.drawString(100, y, f"{item} x {qty} = {qty * price:.2f} บาท")
        y -= 20
    c.drawString(100, y - 10, f"รวมทั้งสิ้น {total:.2f} บาท")
    if cash >= total:
        c.drawString(100, y - 30, f"เงินรับ: {cash:.2f} ทอน: {change:.2f}")
    c.save()
    pdf_data = pdf_buffer.getvalue()
    b64 = base64.b64encode(pdf_data).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="receipt.pdf">📄 ดาวน์โหลดใบเสร็จ</a>'
    st.markdown(href, unsafe_allow_html=True)
