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
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูล
data = pd.DataFrame(sheet_main.get_all_records())

# ตรวจสอบคอลัมน์
required_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing = [col for col in required_columns if col not in data.columns]
if missing:
    st.error(f"❌ ขาดคอลัมน์: {missing}")
    st.stop()

# แปลงข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# UI
st.set_page_config(page_title="เจริญค้า", layout="wide")
st.title("🧊 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

tab1, tab2, tab3 = st.tabs(["📋 สินค้า", "🛒 ขายหลายรายการ", "📊 สรุปยอด"])

# หน้า 1: สินค้า
with tab1:
    st.subheader("📦 รายการสินค้า")
    st.dataframe(data)

    st.subheader("✏️ แก้ไขสินค้า")
    edit_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="edit")
    new_stock = st.number_input("จำนวนใหม่", min_value=0, step=1)
    if st.button("📌 อัปเดตจำนวน"):
        idx = data[data["ชื่อสินค้า"] == edit_name].index[0]
        data.at[idx, "คงเหลือในตู้"] = new_stock
        st.success(f"✅ อัปเดต {edit_name} = {new_stock}")

    st.subheader("➕ เติมสินค้า")
    add_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add")
    add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
    if st.button("✅ เติมสต๊อก"):
        idx = data[data["ชื่อสินค้า"] == add_name].index[0]
        data.at[idx, "เข้า"] += add_qty
        st.success(f"✅ เติม {add_name} +{add_qty}")

# หน้า 2: ขายหลายรายการ
with tab2:
    st.subheader("🛒 ขายหลายรายการ")

    selected_products = st.multiselect("🔍 ค้นหาและเลือกสินค้า", options=data["ชื่อสินค้า"].tolist())

    sale_inputs = {}
    col1, col2 = st.columns(2)
    with col1:
        st.write("📦 รายการที่เลือก")
        for product in selected_products:
            idx = data[data["ชื่อสินค้า"] == product].index[0]
            max_qty = int(data.at[idx, "คงเหลือในตู้"])
            qty = st.number_input(f"{product} (เหลือ {max_qty})", 0, max_qty, key=f"qty_{product}")
            if qty > 0:
                sale_inputs[product] = qty

    with col2:
        st.write("💵 รับเงินและคิดเงิน")
        total_price = 0
        for name, qty in sale_inputs.items():
            idx = data[data["ชื่อสินค้า"] == name].index[0]
            price = float(data.at[idx, "ราคาขาย"])
            total_price += price * qty
        st.write(f"🧾 ยอดรวม: **{total_price:,.2f}** บาท")
        received = st.number_input("💰 รับเงินมา", min_value=0.0, step=1.0, format="%.2f")
        change = received - total_price
        if received > 0:
            if change < 0:
                st.error(f"❌ เงินไม่พอ: ขาด {-change:,.2f} บาท")
            else:
                st.success(f"✅ เงินทอน: {change:,.2f} บาท")

    if st.button("💰 บันทึกการขายทั้งหมด"):
        if not sale_inputs:
            st.warning("⚠️ ยังไม่ได้เลือกสินค้า")
        else:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, qty in sale_inputs.items():
                idx = data[data["ชื่อสินค้า"] == name].index[0]
                if data.at[idx, "คงเหลือในตู้"] >= qty:
                    data.at[idx, "ออก"] += qty
                    profit_per_unit = data.at[idx, "ราคาขาย"] - data.at[idx, "ต้นทุน"]
                    profit_total = profit_per_unit * qty
                    sheet_sales.append_row([
                        now,
                        name,
                        int(qty),
                        float(data.at[idx, "ราคาขาย"]),
                        float(data.at[idx, "ต้นทุน"]),
                        float(profit_per_unit),
                        float(profit_total)
                    ])
                else:
                    st.error(f"❌ {name} เหลือไม่พอขาย")

            st.success("✅ บันทึกการขายเรียบร้อยแล้ว")

# หน้า 3: สรุปยอดขาย
with tab3:
    st.subheader("📊 สรุปยอดขาย")
    data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]
    data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
    data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

    total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
    total_profit = data["กำไร"].sum()

    st.metric("🧾 ยอดขายรวม", f"{total_sales:,.2f} บาท")
    st.metric("💸 กำไรรวม", f"{total_profit:,.2f} บาท")

    if st.button("💾 อัปเดตข้อมูลกลับไปที่ชีท"):
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
        st.success("✅ อัปเดตกลับชีทหลักสำเร็จ")
