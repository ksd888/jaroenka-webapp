import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

# --- CONFIG ---
SPREADSHEET_ID = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
SHEET_MAIN = "ตู้เย็น"
SHEET_SALES = "ยอดขาย"
SHEET_META = "Meta"

# --- AUTH ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
sheet_main = spreadsheet.worksheet(SHEET_MAIN)
sheet_sales = spreadsheet.worksheet(SHEET_SALES)
sheet_meta = spreadsheet.worksheet(SHEET_META)

# --- DATE RESET CHECK ---
now_date = datetime.datetime.now().strftime("%Y-%m-%d")
try:
    last_date = sheet_meta.acell("B1").value
except:
    last_date = ""
if last_date != now_date:
    sheet_main.batch_update([{
        "range": "C2:D",
        "values": [["0", "0"]] * len(sheet_main.get_all_values())
    }])
    sheet_meta.update("A1", [["last_date"]])
    sheet_meta.update("B1", [[now_date]])

# --- LOAD DATA ---
df = pd.DataFrame(sheet_main.get_all_records())
for col in ["เข้า", "ออก", "คงเหลือในตู้", "ราคาขาย", "ต้นทุน"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]
df["กำไร"] = df["ออก"] * df["กำไรต่อหน่วย"]

# --- UI HEADER ---
st.title("🧊 ร้านเจริญค้า: ระบบจัดการสินค้าตู้เย็น")
st.markdown("🛒 *ขายหลายรายการ / เติมสต๊อก / ใบเสร็จ / กำไรสุทธิ*")

# --- MULTI-SELL SYSTEM ---
st.subheader("🛍️ ขายสินค้าหลายรายการ")
selected_items = st.multiselect("🔍 ค้นหาและเลือกสินค้า", df["ชื่อสินค้า"].tolist())
quantities = {}
for item in selected_items:
    qty = st.number_input(f"จำนวนขาย: {item}", min_value=0, step=1, key=item)
    quantities[item] = qty

if st.button("✅ ขายและบันทึก"):
    total = 0
    profit_total = 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item, qty in quantities.items():
        idx = df[df["ชื่อสินค้า"] == item].index[0]
        if df.at[idx, "คงเหลือในตู้"] >= qty and qty > 0:
            df.at[idx, "ออก"] += qty
            profit = qty * df.at[idx, "กำไรต่อหน่วย"]
            sheet_sales.append_row([
                now, item, int(qty),
                float(df.at[idx, "ราคาขาย"]),
                float(df.at[idx, "ต้นทุน"]),
                float(df.at[idx, "กำไรต่อหน่วย"]),
                float(profit)
            ])
            df.at[idx, "คงเหลือในตู้"] -= qty
            total += qty * df.at[idx, "ราคาขาย"]
            profit_total += profit

    st.success(f"✅ ขายเสร็จ ยอดรวม: {total:,.2f} บาท | กำไร: {profit_total:,.2f} บาท")
    st.session_state["receipt"] = (now, quantities, total, profit_total)
    sheet_main.update([df.columns.tolist()] + df.values.tolist())

# --- RECEIPT ---
if "receipt" in st.session_state:
    st.subheader("🧾 ใบเสร็จล่าสุด")
    now, quantities, total, profit_total = st.session_state["receipt"]

    # สร้าง PDF ใบเสร็จ
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 800, f"ร้านเจริญค้า - ใบเสร็จ ({now})")
    y = 780
    for item, qty in quantities.items():
        if qty > 0:
            price = float(df[df["ชื่อสินค้า"] == item]["ราคาขาย"].values[0])
            c.drawString(100, y, f"{item} x{qty} = {qty*price:.2f} บาท")
            y -= 20
    c.drawString(100, y-10, f"รวม: {total:.2f} บาท | กำไร: {profit_total:.2f} บาท")
    c.save()
    buffer.seek(0)

    # แสดงปุ่มดาวน์โหลด
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="receipt.pdf">📄 ดาวน์โหลดใบเสร็จ (PDF)</a>'
    st.markdown(href, unsafe_allow_html=True)

# --- เติมสต๊อก ---
st.subheader("➕ เติมสินค้าเข้าตู้")
col1, col2 = st.columns(2)
with col1:
    add_item = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].tolist(), key="add")
with col2:
    add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("📥 เติมสต๊อก"):
    idx = df[df["ชื่อสินค้า"] == add_item].index[0]
    df.at[idx, "เข้า"] += add_qty
    df.at[idx, "คงเหลือในตู้"] += add_qty
    sheet_main.update([df.columns.tolist()] + df.values.tolist())
    st.success(f"✅ เติมแล้ว {add_item} +{add_qty} ชิ้น")

# --- แสดงยอดรวม ---
st.subheader("📊 สรุปผลกำไร")
total_sales = (df["ออก"] * df["ราคาขาย"]).sum()
total_profit = df["กำไร"].sum()
st.metric("💰 ยอดขายรวม", f"{total_sales:,.2f} บาท")
st.metric("📈 กำไรรวม", f"{total_profit:,.2f} บาท")

# --- Responsive UI Note ---
st.markdown("📱 *UI รองรับ iPad / มือถือ / เดสก์ท็อป*")
