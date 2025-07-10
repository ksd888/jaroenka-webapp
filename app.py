
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่าการเชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)

# เปิดไฟล์ Google Sheet
sheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sh = gc.open_by_key(sheet_id)
worksheet = sh.worksheet("ตู้เย็น")
sales_sheet = sh.worksheet("ยอดขาย")

# โหลดข้อมูลตาราง
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# แปลงตัวเลขให้ปลอดภัย
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# เตรียมคอลัมน์
df["ราคาขาย"] = df["ราคาขาย"].apply(safe_float)
df["ต้นทุน"] = df["ต้นทุน"].apply(safe_float)
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# สร้างตะกร้าสินค้าใน session
if "cart" not in st.session_state:
    st.session_state["cart"] = []

if "search_term" not in st.session_state:
    st.session_state["search_term"] = ""

# UI ค้นหาและเลือกสินค้า
st.title("🛒 ระบบขายสินค้า - เจริญค้า")
st.text_input("ค้นหาสินค้า", key="search_term")
search_term = st.session_state["search_term"]
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)]

# แสดงสินค้าให้เลือกพร้อมปุ่มเพิ่ม
for _, row in filtered_df.iterrows():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}**")
    with col2:
        if st.button("➕", key=f"add_{row['ชื่อสินค้า']}"):
            st.session_state["cart"].append(row["ชื่อสินค้า"])
    with col3:
        count = st.session_state["cart"].count(row["ชื่อสินค้า"])
        st.markdown(f"**{count}** ชิ้น")

# แสดงตะกร้า
st.subheader("🧺 ตะกร้าสินค้า")
if st.session_state["cart"]:
    cart_df = pd.DataFrame(st.session_state["cart"], columns=["ชื่อสินค้า"])
    summary = cart_df.value_counts().reset_index(name="จำนวน")
    summary = summary.rename(columns={0: "ชื่อสินค้า"})
    merged = pd.merge(summary, df, on="ชื่อสินค้า", how="left")
    merged["ยอดขาย"] = merged["จำนวน"] * merged["ราคาขาย"]
    merged["กำไร"] = merged["จำนวน"] * merged["กำไรต่อหน่วย"]

    st.table(merged[["ชื่อสินค้า", "จำนวน", "ราคาขาย", "ยอดขาย", "กำไร"]])
    total_sales = merged["ยอดขาย"].sum()
    total_profit = merged["กำไร"].sum()
    st.success(f"💰 ยอดขายรวม: {total_sales:.2f} บาท | กำไร: {total_profit:.2f} บาท")

    # ปุ่มยืนยันขาย
    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for _, row in merged.iterrows():
            sales_sheet.append_row([
                now,
                row["ชื่อสินค้า"],
                row["จำนวน"],
                row["ราคาขาย"],
                row["ยอดขาย"],
                row["ต้นทุน"],
                row["กำไรต่อหน่วย"],
                row["กำไร"]
            ])
        st.session_state["cart"] = []  # รีเซ็ตตะกร้า
        st.session_state["search_term"] = ""  # ✅ รีเซ็ตช่องค้นหา
        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
        st.experimental_rerun()
else:
    st.info("ยังไม่มีสินค้าในตะกร้า")
