# app.py (เวอร์ชันสมบูรณ์ ปลอดภัย ใช้ st.secrets)
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- ตั้งค่า Credentials จาก st.secrets ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
client = gspread.authorize(credentials)

# --- เชื่อมต่อ Google Sheet ---
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# --- รีเซ็ตรายวัน ---
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    cell_list = sheet.range("F2:G1000")  # รีเซ็ต 'เข้า' และ 'ออก'
    for cell in cell_list:
        cell.value = 0
    sheet.update_cells(cell_list)
    sheet_meta.update("B1", [[now_date]])

# --- โหลดข้อมูลสินค้าลง DataFrame ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("📦 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# ========================
# 🛒 ระบบขายสินค้า
# ========================
st.header("🛒 ขายสินค้า")
search_term = st.text_input("ค้นหาสินค้า")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)] if search_term else df

quantities = {}
for idx, row in filtered_df.iterrows():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"{row['ชื่อสินค้า']} ({row['ราคาขาย']} บาท)")
    with col2:
        qty = st.number_input(f"จำนวน - {row['ชื่อสินค้า']}", min_value=0, step=1, key=row['ชื่อสินค้า'])
        quantities[row['ชื่อสินค้า']] = qty

# คำนวณยอดรวม + กำไร
total = 0
summary = []
for name, qty in quantities.items():
    if qty > 0:
        item = df[df["ชื่อสินค้า"] == name].iloc[0]
        subtotal = item["ราคาขาย"] * qty
        profit = (item["ราคาขาย"] - item["ต้นทุน"]) * qty
        total += subtotal
        summary.append((name, qty, subtotal, profit))

if total > 0:
    st.subheader(f"💰 ยอดรวม: {total} บาท")
    paid = st.number_input("รับเงินจากลูกค้า", min_value=0, step=1)
    if paid >= total:
        st.success(f"เงินทอน: {paid - total} บาท")
    else:
        st.warning("ยอดเงินยังไม่พอชำระ")

    if st.button("✅ ยืนยันการขาย"):
        for name, qty, subtotal, profit in summary:
            idx = df[df["ชื่อสินค้า"] == name].index[0] + 2
            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + qty)  # อัปเดตออก
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - qty)  # อัปเดตคงเหลือ
            sheet_sales.append_row([now_date, name, qty, subtotal, profit])

        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

# ========================
# ➕ เติมสินค้า
# ========================
st.header("➕ เติมสินค้า")
with st.form("เติมสินค้า"):
    item_to_add = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].tolist())
    amount_to_add = st.number_input("จำนวนที่เติม", min_value=1, step=1)
    submitted = st.form_submit_button("เติมเข้า")
    if submitted:
        idx = df[df["ชื่อสินค้า"] == item_to_add].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount_to_add)  # อัปเดตเข้า
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount_to_add)  # อัปเดตคงเหลือ
        st.success(f"เติม {item_to_add} แล้ว {amount_to_add} หน่วย")

# ========================
# ✏️ แก้ไขสินค้า
# ========================
st.header("✏️ แก้ไขสินค้า")
edit_item = st.selectbox("เลือกรายการ", df["ชื่อสินค้า"].tolist())
with st.form("edit_form"):
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    new_price = st.number_input("ราคาขายใหม่", value=float(df.loc[idx-2, "ราคาขาย"]))
    new_cost = st.number_input("ต้นทุนใหม่", value=float(df.loc[idx-2, "ต้นทุน"]))
    new_stock = st.number_input("คงเหลือใหม่", value=int(df.loc[idx-2, "คงเหลือ"]), step=1)
    confirm_edit = st.form_submit_button("บันทึกการแก้ไข")
    if confirm_edit:
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"อัปเดต {edit_item} แล้ว ✅")
