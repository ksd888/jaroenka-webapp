import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# --- เชื่อมต่อ Google Sheets ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# --- โหลดข้อมูลจาก Google Sheet ---
data = pd.DataFrame(sheet_main.get_all_records())
for col in ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]:
    if col not in data.columns:
        st.error(f"❌ ขาดคอลัมน์: {col}")
        st.stop()

data["เข้า"] = pd.to_numeric(data["เข้า"], errors="coerce").fillna(0).astype(int)
data["ออก"] = pd.to_numeric(data["ออก"], errors="coerce").fillna(0).astype(int)
data["คงเหลือในตู้"] = pd.to_numeric(data["คงเหลือในตู้"], errors="coerce").fillna(0).astype(int)
data["ราคาขาย"] = pd.to_numeric(data["ราคาขาย"], errors="coerce").fillna(0)
data["ต้นทุน"] = pd.to_numeric(data["ต้นทุน"], errors="coerce").fillna(0)

st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")
st.title("🧊 ระบบขายสินค้าตู้เย็น - เจริญค้า")

# --- ค้นหาและขายหลายรายการ ---
st.subheader("🛒 ขายสินค้าหลายรายการ")

selected_items = st.multiselect("ค้นหาและเลือกสินค้า", options=data["ชื่อสินค้า"])
quantities = {}
cols = st.columns(len(selected_items)) if selected_items else []

for i, item in enumerate(selected_items):
    with cols[i]:
        quantities[item] = st.number_input(f"{item}", min_value=0, step=1, key=f"qty_{item}")

if selected_items:
    sell_button = st.button("💰 ดำเนินการขายและบันทึก")
    money_received = st.number_input("💵 รับเงิน (บาท)", min_value=0.0, step=1.0, format="%.2f", key="cash")

    if sell_button:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = 0
        receipt = f"🧾 ใบเสร็จ เจริญค้า\n{now}\n-----------------------\n"

        for item, qty in quantities.items():
            if qty <= 0:
                continue
            idx = data[data["ชื่อสินค้า"] == item].index[0]
            if data.at[idx, "คงเหลือในตู้"] < qty:
                st.error(f"❌ {item} มีไม่พอขาย (เหลือ {data.at[idx, 'คงเหลือในตู้']})")
                continue
            data.at[idx, "ออก"] += qty
            data.at[idx, "คงเหลือในตู้"] -= qty
            profit_per_unit = data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]
            profit = profit_per_unit * qty
            price = data.at[idx, "ราคาขาย"] * qty
            total += price
            sheet_sales.append_row([
                now, item, int(qty), float(data.at[idx, "ราคาขาย"]),
                float(data.at[idx, "ต้นทุน"]), float(profit_per_unit), float(profit)
            ])
            receipt += f"{item} x{qty} = {price:.2f}฿\n"

        change = money_received - total
        receipt += f"-----------------------\nรวม {total:.2f}฿\nรับเงิน {money_received:.2f}฿\nเงินทอน {change:.2f}฿"
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.text_area("🧾 ใบเสร็จ", receipt, height=250)

        # อัปเดต Google Sheet ทันที
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())

# --- เติมสินค้าเข้าตู้ ---
st.subheader("➕ เติมสินค้าเข้าตู้")
col1, col2 = st.columns(2)
with col1:
    selected_add = st.selectbox("เลือกสินค้าเพื่อเติม", data["ชื่อสินค้า"], key="add_item")
with col2:
    qty_add = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")

if st.button("✅ เติมสินค้า"):
    idx = data[data["ชื่อสินค้า"] == selected_add].index[0]
    data.at[idx, "เข้า"] += qty_add
    data.at[idx, "คงเหลือในตู้"] += qty_add
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success(f"✅ เติม {selected_add} +{qty_add} สำเร็จแล้ว")

# --- แสดงผลรวมยอดขาย ---
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.subheader("📊 สรุปยอดขายวันนี้")
col1, col2 = st.columns(2)
col1.metric("ยอดขายรวม", f"{total_sales:,.2f} บาท")
col2.metric("กำไรรวม", f"{total_profit:,.2f} บาท")

# --- แสดงข้อมูลตาราง ---
with st.expander("📦 ดูรายการสินค้าทั้งหมด"):
    st.dataframe(data, use_container_width=True)
