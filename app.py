import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account
from io import StringIO

# เชื่อมต่อ Google Sheet
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

# ตรวจสอบ / สร้าง sheet_meta
try:
    sheet_meta = spreadsheet.worksheet("Meta")
except:
    sheet_meta = spreadsheet.add_worksheet(title="Meta", rows="2", cols="2")
    sheet_meta.update("A1", "last_date")
    sheet_meta.update("B1", datetime.datetime.now().strftime("%Y-%m-%d"))

# โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())

# ตรวจสอบว่าคอลัมน์สำคัญมีครบ
required_cols = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing_cols = [col for col in required_cols if col not in data.columns]
if missing_cols:
    st.error(f"❌ คอลัมน์หาย: {missing_cols}")
    st.stop()

# แปลงชนิดข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# 🔄 ล้างยอดเมื่อวันใหม่
today = datetime.datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if today != last_date:
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_meta.update("B1", today)

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# ✅ ขายหลายรายการ
st.subheader("🛒 ขายสินค้า (หลายรายการ)")
sell_items = st.multiselect("ค้นหาและเลือกสินค้า", data["ชื่อสินค้า"].tolist())
sell_data = {}
for item in sell_items:
    qty = st.number_input(f"จำนวนที่ขาย ({item})", min_value=0, step=1, key=f"sell_{item}")
    if qty > 0:
        sell_data[item] = qty

money_received = st.number_input("💵 รับเงินจากลูกค้า", min_value=0.0, step=1.0)

if st.button("✅ ยืนยันขาย"):
    total = 0
    profit_total = 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    receipt_lines = [f"🧾 ใบเสร็จวันที่: {now}\n"]

    for item, qty in sell_data.items():
        idx = data[data["ชื่อสินค้า"] == item].index[0]
        price = data.at[idx, "ราคาขาย"]
        cost = data.at[idx, "ต้นทุน"]
        profit = (price - cost) * qty
        if data.at[idx, "คงเหลือในตู้"] >= qty:
            data.at[idx, "ออก"] += qty
            total += price * qty
            profit_total += profit
            # บันทึกไปยัง sheet_sales
            sheet_sales.append_row([
                now, item, qty, price, cost, price - cost, profit
            ])
            receipt_lines.append(f"- {item} × {qty} = {price * qty:.2f} บาท")
        else:
            st.warning(f"❌ สินค้า '{item}' ไม่พอขาย")

    change = money_received - total
    receipt_lines.append(f"\nรวม: {total:.2f} บาท")
    receipt_lines.append(f"รับเงิน: {money_received:.2f} บาท")
    receipt_lines.append(f"เงินทอน: {change:.2f} บาท")
    receipt_lines.append(f"กำไร: {profit_total:.2f} บาท")

    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
    st.download_button("📄 ดาวน์โหลดใบเสร็จ", data="\n".join(receipt_lines), file_name="receipt.txt")

    # อัปเดตกลับ Google Sheet
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.experimental_rerun()

# ✅ เติมสินค้า
st.subheader("➕ เติมสินค้าเข้าตู้")
add_item = st.selectbox("เลือกสินค้าเพื่อเติม", data["ชื่อสินค้า"].tolist(), key="add")
add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
if st.button("💼 เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == add_item].index[0]
    data.at[idx, "เข้า"] += add_qty
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {add_item} +{add_qty} เรียบร้อย")
    st.experimental_rerun()

# ✅ แสดงยอดรวม
st.subheader("📊 สรุปยอดขายวันนี้")
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()
st.metric("💰 ยอดขายรวม", f"{total_sales:,.2f} บาท")
st.metric("📈 กำไรรวม", f"{total_profit:,.2f} บาท")

# ✅ ตารางสินค้า
st.subheader("📋 รายการสินค้า")
st.dataframe(data)
