import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# เชื่อมต่อ GCP
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูลจาก Google Sheet
data = pd.DataFrame(sheet_main.get_all_records())
expected_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
if any(col not in data.columns for col in expected_columns):
    st.error("❌ คอลัมน์ในชีทไม่ครบ")
    st.stop()

# แปลงชนิดข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

# หัวเรื่อง
st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# ------------------- 📋 ขายหลายรายการ -------------------
st.subheader("🛍️ ขายหลายรายการพร้อมกัน")
search_items = st.multiselect("ค้นหาและเลือกสินค้า", options=data["ชื่อสินค้า"].tolist())

selected_items = []
for item in search_items:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**{item}**")
    with col2:
        qty = st.number_input(f"จำนวน - {item}", min_value=0, step=1, key=f"multi_{item}")
        selected_items.append((item, qty))

if selected_items:
    summary = []
    total = 0
    for item_name, qty in selected_items:
        if qty > 0:
            row = data[data["ชื่อสินค้า"] == item_name].iloc[0]
            price = row["ราคาขาย"]
            total += price * qty
            summary.append((item_name, qty, price, price * qty))

    st.markdown("### 🧾 ใบเสร็จ")
    for name, qty, price, subtotal in summary:
        st.write(f"- {name} x {qty} = {subtotal:.2f} บาท")
    st.write(f"**รวมทั้งหมด: {total:,.2f} บาท**")

    cash = st.number_input("💵 รับเงิน", min_value=0.0, step=1.0, format="%.2f")
    if cash >= total:
        change = cash - total
        st.success(f"เงินทอน: {change:,.2f} บาท")
    else:
        st.warning("⚠️ รับเงินยังไม่ครบ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item_name, qty in selected_items:
            if qty > 0:
                idx = data[data["ชื่อสินค้า"] == item_name].index[0]
                data.at[idx, "ออก"] += qty
                profit_per_unit = data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]
                profit = profit_per_unit * qty
                sheet_sales.append_row([
                    now, item_name, int(qty),
                    float(data.at[idx, "ราคาขาย"]),
                    float(data.at[idx, "ต้นทุน"]),
                    float(profit_per_unit),
                    float(profit)
                ])
        st.success("✅ บันทึกยอดขายและใบเสร็จเรียบร้อยแล้ว")
        st.experimental_rerun()

# ------------------- 🧾 สรุปและอัปเดต -------------------
st.subheader("📊 สรุปยอดขาย")
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()
st.write(f"💰 ยอดขายรวม: {total_sales:,.2f} บาท")
st.write(f"📈 กำไรรวม: {total_profit:,.2f} บาท")

if st.button("💾 อัปเดตกลับชีทหลัก"):
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("✅ อัปเดตกลับชีทหลักสำเร็จแล้ว")
