import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# -- เชื่อมต่อ GCP --
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
sheet_meta = spreadsheet.worksheet("Meta")  # ใช้เก็บวันที่ล่าสุด

# -- โหลดข้อมูล --
data = pd.DataFrame(sheet_main.get_all_records())
meta = pd.DataFrame(sheet_meta.get_all_records())

# -- รีเซ็ตยอด "เข้า" และ "ออก" ทุกวัน --
today = datetime.date.today().isoformat()
last_date = meta.at[0, "last_date"] if not meta.empty else ""
if last_date != today:
    data["เข้า"] = 0
    data["ออก"] = 0
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    # update meta
    new_meta = pd.DataFrame([{"last_date": today}])
    sheet_meta.clear()
    sheet_meta.update([new_meta.columns.tolist()] + new_meta.values.tolist())
    st.experimental_rerun()

# -- แปลงข้อมูล --
expected_cols = ["ชื่อสินค้า", "คงเหลือในตู้", "เข้า", "ออก", "ราคาขาย", "ต้นทุน"]
for col in ["เข้า","ออก","คงเหลือในตู้"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0).astype(int)
for col in ["ราคาขาย","ต้นทุน"]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

st.set_page_config(layout="wide")
st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# -- ระบบขายหลายรายการ --
st.header("🛒 ขายหลายรายการ")
search_items = st.multiselect("ค้นหาสินค้า", options=data["ชื่อสินค้า"].tolist())
quantities = {}
if search_items:
    for item in search_items:
        qty = st.number_input(f"จำนวนขาย: {item}", min_value=0, step=1, key=f"qty_{item}")
        if qty > 0:
            quantities[item] = qty

cash = st.number_input("รับเงิน (บาท)", min_value=0.0, step=1.0, key="cash")
if st.button("💰 ยืนยันการขาย"):
    if not quantities:
        st.error("❌ ยังไม่ระบุรายการขาย")
    else:
        total_amt = sum(data.loc[data["ชื่อสินค้า"]==it, "ราคาขาย"].values[0] * q for it, q in quantities.items())
        total_profit = sum((data.loc[data["ชื่อสินค้า"]==it, "ราคาขาย"].values[0] - data.loc[data["ชื่อสินค้า"]==it, "ต้นทุน"].values[0]) * q for it, q in quantities.items())
        change = cash - total_amt

        # อัปเดตตาราง main และบันทึก sales log
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sales_rows = []
        for it, q in quantities.items():
            idx = data[data["ชื่อสินค้า"]==it].index[0]
            price = float(data.at[idx, "ราคาขาย"])
            cost = float(data.at[idx, "ต้นทุน"])
            prod_profit = (price - cost) * q
            data.at[idx, "ออก"] += q
            sales_rows.append([now, it, int(q), price, cost, price-cost, prod_profit])
        sheet_main.update([data.columns.tolist()] + data.values.tolist())
        sheet_sales.append_rows(sales_rows)

        # ใบเสร็จ
        st.success("✅ ขายสำเร็จ")
        st.subheader("🧾 ใบเสร็จ")
        receipt = pd.DataFrame({
            "สินค้า": list(quantities.keys()),
            "จำนวน": list(quantities.values()),
            "ราคาต่อหน่วย": [data.loc[data["ชื่อสินค้า"]==it,"ราคาขาย"].iloc[0] for it in quantities],
            "ยอดรวม": [quantities[it]*data.loc[data["ชื่อสินค้า"]==it,"ราคาขาย"].iloc[0] for it in quantities]
        })
        st.table(receipt)
        st.write(f"**ยอดรวม:** {total_amt:,.2f} บาท")
        st.write(f"**รับเงิน:** {cash:,.2f} บาท")
        st.write(f"**ทอนเงิน:** {change:,.2f} บาท")
        st.write(f"**กำไรรวม:** {total_profit:,.2f} บาท")

        st.experimental_rerun()

# -- เติมสินค้า --
st.header("➕ เติมสินค้าเข้าสต๊อก")
with st.form("add_form"):
    prod = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"])
    aq = st.number_input("จำนวนเติม", min_value=0, step=1)
    if st.form_submit_button("✅ เติม"):
        idx = data[data["ชื่อสินค้า"]==prod].index[0]
        data.at[idx, "เข้า"] += aq
        sheet_main.update([data.columns.tolist()] + data.values.tolist())
        st.success(f"✅ เติม {prod} +{aq}")
        st.experimental_rerun()

# -- สรุปยอดขายวันนี้ --
st.header("📊 สรุปกำไรและยอดขาย")
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]
st.write(f"ยอดขายรวม: {(data['ออก']*data['ราคาขาย']).sum():,.2f} บาท")
st.write(f"กำไรรวม: {data['กำไร'].sum():,.2f} บาท")

# -- ตารางสินค้า --
st.header("📋 รายการสินค้า")
st.dataframe(data)
