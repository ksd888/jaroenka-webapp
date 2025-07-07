import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# เชื่อมต่อ GCP
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")

# โหลดชีทหลัก
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ตรวจสอบหรือสร้าง Meta sheet
try:
    sheet_meta = spreadsheet.worksheet("Meta")
except gspread.exceptions.WorksheetNotFound:
    sheet_meta = spreadsheet.add_worksheet(title="Meta", rows=2, cols=1)
    sheet_meta.update("A1", "last_date")
    sheet_meta.update("A2", datetime.date.today().isoformat())

# ตรวจสอบวันล่าสุด หากเปลี่ยนวันให้เคลียร์ 'เข้า' และ 'ออก'
today = datetime.date.today().isoformat()
last_date = sheet_meta.acell("A2").value
if last_date != today:
    df = pd.DataFrame(sheet_main.get_all_records())
    if "เข้า" in df.columns and "ออก" in df.columns:
        df["เข้า"] = 0
        df["ออก"] = 0
        sheet_main.update([df.columns.values.tolist()] + df.values.tolist())
    sheet_meta.update("A2", today)

# โหลดข้อมูลใหม่
data = pd.DataFrame(sheet_main.get_all_records())
expected_cols = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
if not all(col in data.columns for col in expected_cols):
    st.error("❌ คอลัมน์ไม่ครบ กรุณาตรวจสอบชีท")
    st.stop()

# แปลงชนิดข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0.0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0.0)

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# 🔍 ขายหลายรายการแบบค้นหา
st.subheader("🛒 ขายสินค้าหลายรายการ")
selected_items = st.multiselect("ค้นหาสินค้า", options=data["ชื่อสินค้า"])
quantities = {}
for item in selected_items:
    quantities[item] = st.number_input(f"จำนวน: {item}", min_value=0, step=1, key=f"qty_{item}")

amount_received = st.number_input("💵 รับเงินมา", min_value=0.0, step=1.0)
if st.button("✅ ขายและบันทึกยอด"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_price = 0.0
    receipt_lines = []

    for item, qty in quantities.items():
        if qty <= 0:
            continue
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        if data.at[idx, "คงเหลือในตู้"] >= qty:
            data.at[idx, "ออก"] += qty
            total = data.at[idx, "ราคาขาย"] * qty
            profit = (data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]) * qty
            sheet_sales.append_row([
                now, item, int(qty),
                float(data.at[idx, "ราคาขาย"]),
                float(data.at[idx, "ต้นทุน"]),
                float(data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]),
                float(profit)
            ])
            total_price += total
            receipt_lines.append(f"{item} x {qty} = {total:.2f} บาท")
        else:
            st.warning(f"❗ สินค้า {item} คงเหลือไม่พอ")

    # คำนวณเงินทอน
    change = amount_received - total_price
    st.success("✅ บันทึกการขายเรียบร้อย")
    st.info(f"💰 ยอดรวม: {total_price:.2f} บาท\n💵 รับมา: {amount_received:.2f} บาท\n💸 เงินทอน: {change:.2f} บาท")

    # พิมพ์ใบเสร็จ
    with st.expander("🧾 ใบเสร็จ"):
        st.markdown(f"🕓 วันที่: `{now}`")
        for line in receipt_lines:
            st.write(line)
        st.write(f"💵 รวมทั้งสิ้น: `{total_price:.2f}` บาท")
        st.write(f"💸 รับเงิน: `{amount_received:.2f}` บาท")
        st.write(f"💵 เงินทอน: `{change:.2f}` บาท")

    # อัปเดตยอดในชีทหลักและรีเซต
    data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("✅ อัปเดตชีทสำเร็จแล้ว")
    st.experimental_rerun()

# ➕ เติมสินค้า
st.subheader("📥 เติมสินค้าเข้าตู้")
fill_item = st.selectbox("เลือกสินค้า", options=data["ชื่อสินค้า"], key="fill")
fill_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="fill_qty")
if st.button("📌 เติม"):
    idx = data[data["ชื่อสินค้า"] == fill_item].index[0]
    data.at[idx, "เข้า"] += fill_qty
    data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {fill_item} แล้ว +{fill_qty}")
    st.experimental_rerun()

# 📋 แสดงรายการสินค้า
st.subheader("📊 รายการสินค้าในระบบ")
st.dataframe(data)
