import streamlit as st
import datetime
from pytz import timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt

# ✅ Apple Style CSS + ปรับสีข้อความให้เข้มขึ้น
st.markdown("""
    
    
    <style>
    *, body, .main, .block-container, .stText, .stMarkdown, .stAlert, label, span {
        color: #ffffff !important;
    }
    .stButton>button {
        color: #ffffff !important;
        background-color: #007aff !important;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.5em 1.2em;
    }
    .stTextInput>div>div>input,
    .stNumberInput input,
    .stSelectbox div,
    .stMultiSelect div {
        background-color: #f2f2f7 !important;
        color: #000000 !important;
        border-radius: 6px;
        font-size: 18px;
        font-weight: bold;
    }
    </style>


""", unsafe_allow_html=True)

# ✅ ปุ่มเมนูด้านบนแทน Sidebar
st.markdown("### 🚀 เมนูหลัก")
col1, col2, col3 = st.columns(3)
if "page" not in st.session_state:
    st.session_state.page = "ขายสินค้า"
with col1:
    if st.button("🏪 ขายสินค้า"):
        st.session_state.page = "ขายสินค้า"
with col2:
    if st.button("🧊 ขายน้ำแข็ง"):
        st.session_state.page = "ขายน้ำแข็ง"
with col3:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"

# ✅ ตั้งเวลา
now = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")

# ✅ เชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")
df = pd.DataFrame(worksheet.get_all_records())

# ✅ Helper functions
def safe_key(text): return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()
def safe_int(val): return int(pd.to_numeric(val, errors="coerce") or 0)
def safe_float(val): return float(pd.to_numeric(val, errors="coerce") or 0.0)
def safe_safe_int(val): 
    try: return safe_int(safe_float(val))
    except: return 0
def safe_safe_float(val): 
    try: return safe_float(val)
    except: return 0.0
def increase_quantity(p): st.session_state.quantities[p] += 1
def decrease_quantity(p): st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)

# ✅ รีเซ็ต Session
if st.session_state.get("reset_search_items"):
    st.session_state["search_items"] = []
    st.session_state["quantities"] = {}
    st.session_state["cart"] = []
    st.session_state["paid_input"] = 0.0
    st.session_state["last_paid_click"] = 0
    del st.session_state["reset_search_items"]

# ✅ ค่าเริ่มต้น
default_session = {
    "cart": [],
    "search_items": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "sale_complete": False
}
for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ หน้า Dashboard
if st.session_state.page == "Dashboard":
    st.title("📊 Dashboard รายวัน")
    try:
        sales_ws = sheet.worksheet("ยอดขาย")
        sales_data = pd.DataFrame(sales_ws.get_all_records())

        if "เวลา" in sales_data.columns:
            sales_data = sales_data.rename(columns={"เวลา": "timestamp"})
        else:
            st.warning("❌ ไม่พบคอลัมน์ 'เวลา' ในชีทยอดขาย")
            sales_data["timestamp"] = pd.NaT

        sales_data["timestamp"] = pd.to_datetime(sales_data["timestamp"], errors="coerce")
        today = datetime.datetime.now(timezone("Asia/Bangkok")).date()
        today_sales = sales_data[sales_data["timestamp"].dt.date == today]

        if not today_sales.empty:
            total_today_price = today_sales["total_price"].sum()
            total_today_profit = today_sales["total_profit"].sum()
            top_items = today_sales["Items"].value_counts().idxmax()

            st.success(f"✅ ยอดขายวันนี้: {total_today_price:.2f} บาท")
            st.info(f"🟢 กำไรวันนี้: {total_today_profit:.2f} บาท")
            st.warning(f"🔥 สินค้าขายดี: {top_items}")
        else:
            st.warning("⚠️ ยังไม่มีข้อมูลยอดขายวันนี้")

        # กราฟ 14 วัน
        sales_data["วันที่"] = sales_data["timestamp"].dt.date
        recent_df = sales_data.sort_values("วันที่", ascending=False).head(14)
        daily_summary = recent_df.groupby("วันที่").agg({"total_profit": "sum", "total_price": "sum"}).sort_index()

        st.subheader("📈 กราฟกำไรสุทธิรายวัน")
        fig1, ax1 = plt.subplots()
        ax1.plot(daily_summary.index, daily_summary["total_profit"], marker='o')
        ax1.set_ylabel("กำไรสุทธิ (บาท)")
        ax1.set_xlabel("วันที่")
        ax1.grid(True)
        st.pyplot(fig1)

        st.subheader("💰 ยอดขายรวมและกำไรรวม 14 วันล่าสุด")
        st.metric("ยอดขายรวม", f"{daily_summary['total_price'].sum():,.0f} บาท")
        st.metric("กำไรสุทธิรวม", f"{daily_summary['total_profit'].sum():,.0f} บาท")

        st.subheader("🔥 วันที่ขายดีสุด")
        top_day = daily_summary["total_price"].idxmax()
        top_sales = daily_summary["total_price"].max()
        st.success(f"วันที่ {top_day} มียอดขายสูงสุด {top_sales:,.0f} บาท")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด Dashboard: {e}")

# ✅ (อื่น ๆ เช่นหน้าขายสินค้า / น้ำแข็ง ให้นำมาต่อเติมตรงนี้ได้เลย)

# ✅ หน้า "ขายสินค้า"
elif st.session_state.page == "ขายสินค้า":
    st.title("🧃 ขายสินค้าตู้เย็น")
    product_names = df["ชื่อสินค้า"].tolist()
    st.multiselect("เลือกสินค้าจากชื่อ", product_names, key="search_items")
    selected = st.session_state["search_items"]

    for p in selected:
        if p not in st.session_state.quantities:
            st.session_state.quantities[p] = 1
        qty = st.session_state.quantities[p]
        st.markdown(f"**{p}**")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1: st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
        with col2: st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
        with col3: st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
        row = df[df["ชื่อสินค้า"] == p]
        stock = int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
        st.markdown(f"<span style='color:{'red' if stock < 3 else 'black'}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)

    if st.button("➕ เพิ่มลงตะกร้า"):
        for p in selected:
            qty = safe_safe_int(st.session_state.quantities[p])
            if qty > 0:
                st.session_state.cart.append((p, qty))
        st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price, cost = safe_safe_float(row["ราคาขาย"]), safe_safe_float(row["ต้นทุน"])
        subtotal, profit = qty * price, qty * (price - cost)
        total_price += subtotal
        total_profit += profit
        st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    st.session_state.paid_input = st.number_input("💰 รับเงินจากลูกค้า", value=st.session_state.paid_input, step=1.0)
    def add_money(amount: int):
        st.session_state.paid_input += amount
        st.session_state.last_paid_click = amount
    col1, col2, col3 = st.columns(3)
    with col1: st.button("20", on_click=add_money, args=(20,))
    with col2: st.button("50", on_click=add_money, args=(50,))
    with col3: st.button("100", on_click=add_money, args=(100,))
    col4, col5 = st.columns(2)
    with col4: st.button("500", on_click=add_money, args=(500,))
    with col5: st.button("1000", on_click=add_money, args=(1000,))
    if st.session_state.last_paid_click:
        if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
            st.session_state.paid_input -= st.session_state.last_paid_click
            st.session_state.last_paid_click = 0

    st.info(f"📦 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    if st.session_state.paid_input >= total_price:
        st.success(f"💰 เงินทอน: {st.session_state.paid_input - total_price:.2f} บาท")
    else:
        st.warning("💸 เงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2
            new_out = safe_safe_int(row["ออก"]) + qty
            new_left = safe_safe_int(row["คงเหลือในตู้"]) - qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

        summary_ws.append_row([
            now,
            ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
            total_price,
            total_profit,
            st.session_state.paid_input,
            st.session_state.paid_input - total_price,
            "drink"
        ])
        st.session_state.reset_search_items = True
        st.rerun()

    # 📦 เติมสินค้า
    with st.expander("📦 เติมสินค้า"):
        restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock_select")
        restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
        if st.button("📥 ยืนยันเติมสินค้า"):
            index = df[df["ชื่อสินค้า"] == restock_item].index[0]
            idx_in_sheet = index + 2
            row = df.loc[index]
            new_in = safe_safe_int(row["เข้า"]) + restock_qty
            new_left = safe_safe_int(row["คงเหลือในตู้"]) + restock_qty
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
            st.success(f"✅ เติม {restock_item} แล้ว")

    # ✏️ แก้ไขสินค้า
    with st.expander("✏️ แก้ไขสินค้า"):
        edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_select")
        index = df[df["ชื่อสินค้า"] == edit_item].index[0]
        idx_in_sheet = index + 2
        row = df.loc[index]
        new_price = st.number_input("ราคาขาย", value=safe_safe_float(row["ราคาขาย"]), key="edit_price")
        new_cost = st.number_input("ต้นทุน", value=safe_safe_float(row["ต้นทุน"]), key="edit_cost")
        new_stock = st.number_input("คงเหลือในตู้", value=safe_safe_int(row["คงเหลือในตู้"]), key="edit_stock", step=1)
        if st.button("💾 บันทึกการแก้ไข"):
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
            worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
            st.success(f"✅ อัปเดต {edit_item} แล้ว")

    # 🔁 ปุ่มรีเซ็ตยอดเข้า-ออก
    if st.button("🔁 รีเซ็ตยอดเข้า-ออก (เริ่มวันใหม่)", key="reset_io"):
        num_rows = len(df)
        worksheet.batch_update([
            {"range": f"E2:E{num_rows+1}", "values": [[0]] * num_rows},
            {"range": f"G2:G{num_rows+1}", "values": [[0]] * num_rows}
        ])
        st.success("✅ รีเซ็ตยอด 'เข้า' และ 'ออก' สำเร็จแล้วสำหรับวันใหม่")

elif st.session_state.page == "ขายสินค้า":
    st.title("🧃 ขายสินค้าตู้เย็น")
    st.multiselect("เลือกสินค้าจากชื่อ", df["ชื่อสินค้า"].tolist(), key="search_items")
    selected = st.session_state["search_items"]
    for p in selected:
        if p not in st.session_state.quantities:
            st.session_state.quantities[p] = 1
        qty = st.session_state.quantities[p]
        st.markdown(f"**{p}**")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1: st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
        with col2: st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
        with col3: st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
        row = df[df["ชื่อสินค้า"] == p]
        stock = int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
        st.markdown(f"<span style='color:{'red' if stock < 3 else 'black'}; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>", unsafe_allow_html=True)

# ✅ หน้า "ขายน้ำแข็ง"
elif st.session_state.page == "ขายน้ำแข็ง":
    st.title("🧊 ระบบขายน้ำแข็งเจริญค้า")

    iceflow_sheet = sheet.worksheet("iceflow")
    df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
    df_ice["ชนิดน้ำแข็ง"] = df_ice["ชนิดน้ำแข็ง"].astype(str).str.strip().str.lower()
    df_ice["ราคาขายต่อหน่วย"] = pd.to_numeric(df_ice["ราคาขายต่อหน่วย"], errors='coerce')
    df_ice["ต้นทุนต่อหน่วย"] = pd.to_numeric(df_ice["ต้นทุนต่อหน่วย"], errors='coerce')
    df_ice = df_ice.dropna(subset=["ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย"])

    today_str = datetime.datetime.now().strftime("%-d/%-m/%Y")
    if df_ice["วันที่"].iloc[0] != today_str:
        df_ice["วันที่"] = today_str
        df_ice["รับเข้า"] = 0
        df_ice["ขายออก"] = 0
        df_ice["จำนวนละลาย"] = 0
        df_ice["คงเหลือตอนเย็น"] = 0
        df_ice["กำไรรวม"] = 0
        df_ice["กำไรสุทธิ"] = 0
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        st.info("🔄 ระบบรีเซ็ตยอดใหม่สำหรับวันนี้แล้ว")

    ice_types = ["โม่", "หลอดใหญ่", "หลอดเล็ก", "ก้อน"]
    st.markdown("### 📦 โซนรับเข้าน้ำแข็ง")
    in_values = {}
    col1, col2, col3, col4 = st.columns(4)
    for i, k in enumerate(ice_types):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(k)]
        if not row.empty:
            idx = row.index[0]
            old_val = int(df_ice.at[idx, "รับเข้า"])
            with [col1, col2, col3, col4][i]:
                in_values[k] = st.number_input(f"📥 {k}", min_value=0, value=old_val, key=f"in_{k}")
                df_ice.at[idx, "รับเข้า"] = in_values[k]
        else:
            st.warning(f"❌ ไม่พบข้อมูลน้ำแข็งชนิด '{k}' ในชีท iceflow")

    st.markdown("### 💸 โซนขายออกน้ำแข็ง")
    total_income = 0
    total_profit = 0
    for k in ice_types:
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(k)]
        if not row.empty:
            idx = row.index[0]
            price = float(df_ice.at[idx, "ราคาขายต่อหน่วย"])
            cost = float(df_ice.at[idx, "ต้นทุนต่อหน่วย"])
            profit_unit = price - cost
            old_out = int(df_ice.at[idx, "ขายออก"])
            out_val = st.number_input(f"🧊 ขายออก {k}", min_value=0, value=old_out, key=f"out_{k}")
            income = out_val * price
            profit = out_val * profit_unit

            df_ice.at[idx, "ขายออก"] = out_val
            df_ice.at[idx, "คงเหลือตอนเย็น"] = int(df_ice.at[idx, "รับเข้า"]) - out_val
            df_ice.at[idx, "กำไรรวม"] = profit
            df_ice.at[idx, "กำไรสุทธิ"] = profit
            df_ice.at[idx, "วันที่"] = today_str

            total_income += income
            total_profit += profit
        else:
            st.warning(f"❌ ไม่สามารถขายออกน้ำแข็ง '{k}' ได้ เพราะไม่มีข้อมูลในชีท")

    if st.button("📥 บันทึกยอดเติมน้ำแข็ง"):
        for k in ice_types:
            row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(k)]
            if not row.empty:
                idx = row.index[0]
                df_ice.at[idx, "วันที่"] = today_str
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        st.success("✅ บันทึกยอดเติมน้ำแข็งแล้ว")
        st.experimental_rerun()

    if st.button("✅ บันทึกการขายน้ำแข็ง"):
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        for _, row in df_ice.iterrows():
            summary_ws.append_row([
                today_str,
                row["ชนิดน้ำแข็ง"],
                int(row["ขายออก"]),
                row["ราคาขายต่อหน่วย"],
                row["ต้นทุนต่อหน่วย"],
                row["ราคาขายต่อหน่วย"] - row["ต้นทุนต่อหน่วย"],
                int(row["ขายออก"]) * row["ราคาขายต่อหน่วย"],
                int(row["ขายออก"]) * (row["ราคาขายต่อหน่วย"] - row["ต้นทุนต่อหน่วย"]),
                "ice"
            ])
        st.success(f"✅ บันทึกแล้ว | ขายรวม {total_income:.0f} บาท | กำไร {total_profit:.0f} บาท")
        st.experimental_rerun()
