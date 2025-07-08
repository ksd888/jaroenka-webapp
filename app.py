import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials จาก secrets.toml
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# ✅ เปิด Google Sheet
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ รีเซ็ตยอดเข้า/ออกเมื่อวันใหม่
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# ✅ โหลดข้อมูลจาก Google Sheet
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ✅ UI Streamlit
st.title("📦 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# -------------------
# 🛒 ขายสินค้า
# -------------------
st.header("🛒 ขายสินค้า")
search = st.text_input("ค้นหาสินค้า")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)] if search else df

quantities = {}
for idx, row in filtered_df.iterrows():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"{row['ชื่อสินค้า']} ({row['ราคาขาย']} บาท)")
    with col2:
        qty = st.number_input(f"จำนวน - {row['ชื่อสินค้า']}", min_value=0, step=1, key=row["ชื่อสินค้า"])
        quantities[row["ชื่อสินค้า"]] = qty

# ✅ คำนวณยอดรวมและทอน
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
    st.subheader(f"💵 ยอดรวม: {total:.2f} บาท")
    paid = st.number_input("💰 รับเงินจากลูกค้า", min_value=0.0, step=1.0)
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินยังไม่พอชำระ")

    if st.button("✅ ยืนยันการขาย"):
        for name, qty, subtotal, profit in summary:
            idx = df[df["ชื่อสินค้า"] == name].index[0] + 2
            out_val = int(sheet.cell(idx, 7).value or 0) + qty
            left_val = int(sheet.cell(idx, 5).value or 0) - qty
            sheet.update_cell(idx, 7, out_val)
            sheet.update_cell(idx, 5, left_val)
            sheet_sales.append_row([
                now_date, name, qty,
                round(float(subtotal), 2),
                round(float(profit), 2)
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

# -------------------
# ➕ เติมสินค้า
# -------------------
st.header("➕ เติมสินค้า")
with st.form("เติมสินค้า"):
    item_to_add = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].tolist())
    amount_to_add = st.number_input("จำนวนที่เติม", min_value=1, step=1)
    submitted = st.form_submit_button("เติมเข้า")
    if submitted:
        idx = df[df["ชื่อสินค้า"] == item_to_add].index[0] + 2
        in_val = int(sheet.cell(idx, 6).value or 0) + amount_to_add
        left_val = int(sheet.cell(idx, 5).value or 0) + amount_to_add
        sheet.update_cell(idx, 6, in_val)
        sheet.update_cell(idx, 5, left_val)
        st.success(f"✅ เติมสินค้า {item_to_add} จำนวน {amount_to_add} เรียบร้อยแล้ว")

# -------------------
# ✏️ แก้ไขสินค้า
# -------------------
st.header("✏️ แก้ไขสินค้า")
edit_item = st.selectbox("เลือกรายการ", df["ชื่อสินค้า"].tolist())
with st.form("edit_form"):
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    new_price = st.number_input("ราคาขายใหม่", value=float(df.loc[idx-2, "ราคาขาย"]))
    new_cost = st.number_input("ต้นทุนใหม่", value=float(df.loc[idx-2, "ต้นทุน"]))
    new_stock = st.number_input("คงเหลือใหม่", value=int(df.loc[idx-2, "คงเหลือ"]), step=1)
    confirm = st.form_submit_button("💾 บันทึก")
    if confirm:
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ อัปเดตรายการ {edit_item} เรียบร้อย")
