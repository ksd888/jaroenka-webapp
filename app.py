import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

st.set_page_config(page_title="เจริญค้า - จัดการตู้เย็น", layout="wide")

# ✅ เชื่อมต่อ Google Sheet
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

# ✅ โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())
required_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
for col in required_columns:
    if col not in data.columns:
        st.error(f"❌ ขาดคอลัมน์ {col}")
        st.stop()

# ✅ แปลงข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# ✅ ฟีเจอร์: เติมสินค้า
st.header("➕ เติมสินค้าเข้าตู้")
with st.form("เติมสินค้า"):
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_add = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"].unique())
    with col2:
        qty_add = st.number_input("จำนวนที่เติม", min_value=0, step=1)
    submitted_add = st.form_submit_button("✅ เติมเลย")
    if submitted_add and qty_add > 0:
        idx = data[data["ชื่อสินค้า"] == selected_add].index[0]
        data.at[idx, "เข้า"] += qty_add
        st.success(f"✅ เติม {selected_add} +{qty_add}")
        sheet_main.update([data.columns.tolist()] + data.values.tolist())

# ✅ ฟีเจอร์: ขายหลายรายการพร้อมกัน
st.header("🛒 ขายหลายรายการ")
with st.form("ขายหลายรายการ"):
    selected_items = st.multiselect("ค้นหาและเลือกสินค้า", data["ชื่อสินค้า"].unique())
    qty_inputs = {}
    for item in selected_items:
        qty_inputs[item] = st.number_input(f"จำนวน: {item}", min_value=0, step=1, key=f"qty_{item}")
    money_received = st.number_input("💵 เงินที่รับมา", min_value=0.0, step=1.0)
    submitted_sell = st.form_submit_button("💰 บันทึกการขาย")

    if submitted_sell and any(qty_inputs[item] > 0 for item in selected_items):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        receipt = []
        total = 0
        profit_total = 0

        for item in selected_items:
            qty = qty_inputs[item]
            if qty > 0:
                idx = data[data["ชื่อสินค้า"] == item].index[0]
                if data.at[idx, "คงเหลือในตู้"] >= qty:
                    data.at[idx, "ออก"] += qty
                    price = data.at[idx, "ราคาขาย"]
                    cost = data.at[idx, "ต้นทุน"]
                    profit = (price - cost) * qty
                    line_total = price * qty
                    total += line_total
                    profit_total += profit
                    receipt.append(f"- {item} x{qty} = {line_total:.2f}฿")
                    sheet_sales.append_row([
                        now, item, qty, price, cost, price - cost, profit
                    ])
                else:
                    st.warning(f"❗ {item} คงเหลือไม่พอขาย ({data.at[idx, 'คงเหลือในตู้']} ชิ้น)")

        # ✅ อัปเดตคอลัมน์คงเหลือ
        data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
        sheet_main.update([data.columns.tolist()] + data.values.tolist())

        # ✅ ใบเสร็จ
        change = money_received - total
        st.success("✅ ขายเรียบร้อยแล้ว!")
        st.subheader("🧾 ใบเสร็จ")
        st.markdown("\n".join(receipt))
        st.markdown(f"**รวมทั้งหมด: {total:,.2f} บาท**")
        st.markdown(f"**รับเงินมา: {money_received:,.2f} บาท**")
        st.markdown(f"**เงินทอน: {change:,.2f} บาท**")

# ✅ สรุปยอดวันนี้
st.header("📊 สรุปยอดขาย")
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()
st.write(f"🧾 ยอดขายรวม: {total_sales:,.2f} บาท")
st.write(f"💸 กำไรรวม: {total_profit:,.2f} บาท")

# ✅ ปุ่มบันทึกยอดขายและรีเซต
if st.button("📝 บันทึกยอดขาย & 🔄 รีเซตเข้า/ออก"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in data.iterrows():
        if row["ออก"] > 0:
            sheet_sales.append_row([
                now,
                row["ชื่อสินค้า"],
                int(row["ออก"]),
                float(row["ราคาขาย"]),
                float(row["ต้นทุน"]),
                float(row["กำไรต่อหน่วย"]),
                float(row["กำไร"])
            ])
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_main.update([data.columns.tolist()] + data.values.tolist())
    st.success("✅ บันทึกและรีเซตสำเร็จแล้ว")

# ✅ ตารางสินค้า
st.header("📋 รายการสินค้า")
st.dataframe(data, use_container_width=True)
