import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# ✅ เชื่อมต่อ GCP
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ โหลดข้อมูลจาก Google Sheet
data = pd.DataFrame(sheet_main.get_all_records())

# ✅ ตรวจสอบว่าคอลัมน์สำคัญมีครบ
required_columns = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
missing = [col for col in required_columns if col not in data.columns]
if missing:
    st.error(f"❌ ขาดคอลัมน์ในชีท: {missing}")
    st.stop()

# ✅ แปลงชนิดข้อมูล
for col in ["เข้า", "ออก", "คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย", "ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

# ✅ ฟังก์ชันช่วย
def calculate_summary(df):
    df["คงเหลือในตู้"] = df["คงเหลือในตู้"] + df["เข้า"] - df["ออก"]
    df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]
    df["กำไร"] = df["ออก"] * df["กำไรต่อหน่วย"]
    total_sales = (df["ออก"] * df["ราคาขาย"]).sum()
    total_profit = df["กำไร"].sum()
    return df, total_sales, total_profit

# ✅ ส่วน UI หลัก
st.set_page_config(page_title="เจริญค้า", layout="wide")
st.title("🧊 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# ✅ Tabs
tab1, tab2, tab3 = st.tabs(["📋 สินค้าทั้งหมด", "🛒 ขายหลายรายการ", "📊 สรุปยอด & บันทึก"])

# 🔹 หน้า 1: ดูสินค้า + แก้ไข
with tab1:
    st.subheader("📦 รายการสินค้า")
    st.dataframe(data)

    st.subheader("✏️ แก้ไขจำนวนสินค้า")
    edit_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="edit")
    new_stock = st.number_input("จำนวนใหม่", min_value=0, step=1, key="new_stock")
    if st.button("📌 อัปเดตจำนวน", key="update_stock"):
        idx = data[data["ชื่อสินค้า"] == edit_name].index[0]
        data.at[idx, "คงเหลือในตู้"] = new_stock
        st.success(f"✅ อัปเดต {edit_name} = {new_stock}")

    st.subheader("➕ เติมสินค้าเข้าตู้")
    add_name = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"], key="add")
    add_qty = st.number_input("จำนวนที่เติม", min_value=0, step=1, key="add_qty")
    if st.button("✅ เติมสต๊อก", key="add_stock"):
        idx = data[data["ชื่อสินค้า"] == add_name].index[0]
        data.at[idx, "เข้า"] += add_qty
        st.success(f"✅ เติม {add_name} +{add_qty}")

# 🔹 หน้า 2: ขายหลายรายการพร้อมกัน
with tab2:
    st.subheader("🛒 ขายสินค้าหลายรายการ")
    sale_quantities = {}
    for i, row in data.iterrows():
        qty = st.number_input(f"{row['ชื่อสินค้า']} (คงเหลือ {row['คงเหลือในตู้']})", 0, row["คงเหลือในตู้"], key=f"sale_{i}")
        if qty > 0:
            sale_quantities[i] = qty

    if st.button("💰 บันทึกการขายหลายรายการ"):
        if not sale_quantities:
            st.warning("⚠️ กรุณาเลือกสินค้าที่ต้องการขาย")
        else:
            for i, qty in sale_quantities.items():
                data.at[i, "ออก"] += qty
            st.success("✅ บันทึกการขายเรียบร้อยแล้ว")

# 🔹 หน้า 3: สรุปยอดขาย
with tab3:
    st.subheader("📊 สรุปยอดขายวันนี้")
    data, total_sales, total_profit = calculate_summary(data)
    st.metric("🧾 ยอดขายรวม", f"{total_sales:,.2f} บาท")
    st.metric("💸 กำไรรวม", f"{total_profit:,.2f} บาท")

    st.subheader("📝 บันทึกยอดขายลง Google Sheet")
    if st.button("📤 บันทึกยอดขาย"):
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
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

    if st.button("💾 อัปเดตกลับชีทหลัก"):
        sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
        st.success("✅ อัปเดตกลับชีทหลักสำเร็จ")
