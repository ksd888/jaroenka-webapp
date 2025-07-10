
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------- ฟังก์ชันป้องกัน ----------
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def safe_int(val):
    try:
        return int(val)
    except:
        return 0

# ---------- เชื่อม Google Sheet ----------
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

spreadsheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sheet = client.open_by_key(spreadsheet_id).worksheet("ตู้เย็น")

# ---------- โหลดข้อมูลสินค้า ----------
data = sheet.get_all_records()
products = []
for row in data:
    try:
        products.append({
            "ชื่อ": row.get("ชื่อ", ""),
            "ราคาขาย": safe_float(row.get("ราคาขาย")),
            "ต้นทุน": safe_float(row.get("ต้นทุน")),
            "คงเหลือ": safe_int(row.get("คงเหลือ", 0)),
            "ออก": safe_int(row.get("ออก", 0)),
        })
    except Exception as e:
        st.warning(f"พบข้อผิดพลาดในข้อมูลสินค้า: {e}")

# ---------- UI ----------
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

st.subheader("🛒 เลือกสินค้า")
selected_names = st.multiselect("🔍 เลือกสินค้าที่จะขาย", [p["ชื่อ"] for p in products])
quantity_dict = {}

for name in selected_names:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(name)
    with col2:
        quantity = st.number_input(f"จำนวน - {name}", min_value=0, step=1, key=f"qty_{name}")
        quantity_dict[name] = quantity

# ---------- คำนวณยอด ----------
st.markdown("## 📋 รายการขาย")
total = 0.0
profit = 0.0
for name, qty in quantity_dict.items():
    if qty > 0:
        product = next((p for p in products if p["ชื่อ"] == name), None)
        if product:
            line_total = product["ราคาขาย"] * qty
            line_profit = (product["ราคาขาย"] - product["ต้นทุน"]) * qty
            total += line_total
            profit += line_profit
            st.write(f"- {name} x {qty} = {line_total:.2f} บาท")

st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

money_received = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
change = money_received - total
if change < 0:
    st.warning("🧾 ยอดเงินไม่พอ")
else:
    st.success(f"เงินทอน: {change:.2f} บาท")

# ---------- บันทึกการขาย ----------
if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in quantity_dict.items():
        if qty > 0:
            try:
                cell = sheet.find(name)
                out_cell = f"G{cell.row}"
                out_value = safe_int(sheet.acell(out_cell).value)
                new_out = out_value + qty
                sheet.update(out_cell, [[new_out]])

                remain_cell = f"E{cell.row}"
                remain_value = safe_int(sheet.acell(remain_cell).value)
                new_remain = remain_value - qty
                sheet.update(remain_cell, [[new_remain]])
            except Exception as e:
                st.warning(f"❗ อัปเดต {name} ไม่สำเร็จ: {e}")

    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")
    st.experimental_rerun()
