import streamlit as st
import datetime
from pytz import timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt

# ตั้งค่าพื้นฐาน CSS
st.markdown("""
<style>
/* พื้นหลังขาว ตัวหนังสือดำเข้ม */
body, .main, .block-container {
    background-color: #ffffff !important;
    color: #000000 !important;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* ปุ่ม */
.stButton > button {
    color: white !important;
    background-color: #007aff !important;
    font-weight: bold;
    border: none;
    border-radius: 10px;
    padding: 0.5em 1.2em;
    font-size: 16px;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background-color: #0062cc !important;
    transform: scale(1.02);
}

/* Input */
input, textarea, .stTextInput > div > div > input, .stNumberInput input {
    background-color: #f2f2f7 !important;
    color: #000000 !important;
    font-weight: bold !important;
    font-size: 18px;
    border-radius: 8px !important;
    padding: 10px !important;
}

/* Custom Checkbox UI */
.stCheckbox > div {
    display: flex;
    align-items: center;
}
.stCheckbox input[type="checkbox"] {
    display: none;
}
.stCheckbox > div > label {
    position: relative;
    padding-left: 28px;
    cursor: pointer;
    font-size: 18px;
    color: #000000 !important;
    font-weight: bold;
}
.stCheckbox > div > label::before {
    content: "";
    position: absolute;
    left: 0;
    top: 2px;
    width: 20px;
    height: 20px;
    border: 2px solid #000;
    background-color: white;
    border-radius: 4px;
}
.stCheckbox input[type="checkbox"]:checked + label::before {
    background-color: #007aff;
    border-color: #007aff;
}
.stCheckbox input[type="checkbox"]:checked + label::after {
    content: "✓";
    position: absolute;
    left: 5px;
    top: 0px;
    font-size: 16px;
    color: white;
    font-weight: bold;
}

/* Alert สินค้าใกล้หมด */
.stMarkdown span[style*="color:red"] {
    font-size: 20px !important;
    font-weight: bold !important;
    padding: 5px;
    border-radius: 5px;
}

/* กล่องข้อมูล */
.css-1kyxreq {
    background-color: #f9f9f9 !important;
    border-radius: 10px !important;
    padding: 15px !important;
    margin-bottom: 15px !important;
}
</style>
""", unsafe_allow_html=True)

# ระบบจัดการ Session State
if "force_rerun" in st.session_state and st.session_state.force_rerun:
    st.session_state.force_rerun = False
    st.rerun()

# เชื่อมต่อ Google Sheets
@st.cache_resource
def connect_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
    return sheet

sheet = connect_google_sheets()
worksheet = sheet.worksheet("ตู้เย็น")

# 🔍 ฟังก์ชันค้นหา worksheet อย่างปลอดภัย
def get_worksheet_by_name(sheet, name):
    for ws in sheet.worksheets():
        if ws.title.strip() == name.strip():
            return ws
    return None

summary_ws = get_worksheet_by_name(sheet, "ยอดขาย")
if not summary_ws:
    st.error("❌ ไม่พบชีทชื่อ 'ยอดขาย'")
    st.stop()
df = pd.DataFrame(worksheet.get_all_records())

# Helper functions
def safe_key(text): 
    return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()

def safe_int(val): 
    return int(pd.to_numeric(val, errors="coerce") or 0)

def safe_float(val): 
    return float(pd.to_numeric(val, errors="coerce") or 0.0)

def increase_quantity(p): 
    st.session_state.quantities[p] += 1

def decrease_quantity(p): 
    st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)

def add_money(amount: int):
    st.session_state.paid_input += amount
    st.session_state.last_paid_click = amount

# ระบบจัดการ Session
if st.session_state.get("reset_search_items"):
    st.session_state["search_items"] = []
    st.session_state["quantities"] = {}
    st.session_state["cart"] = []
    st.session_state["paid_input"] = 0.0
    st.session_state["last_paid_click"] = 0
    del st.session_state["reset_search_items"]

default_session = {
    "cart": [],
    "search_items": [],
    "quantities": {},
    "paid_input": 0.0,
    "last_paid_click": 0,
    "sale_complete": False,
    "page": "ขายสินค้า"
}

for key, default in default_session.items():
    if key not in st.session_state:
        st.session_state[key] = default

# เมนูหลัก
st.markdown("### 🚀 เมนูหลัก")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏪 ขายสินค้า"):
        st.session_state.page = "ขายสินค้า"
with col2:
    if st.button("🧊 ขายน้ำแข็ง"):
        st.session_state.page = "ขายน้ำแข็ง"
with col3:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"

now = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")

# หน้า Dashboard
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

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 ยอดขายวันนี้", f"{total_today_price:,.2f} บาท")
            with col2:
                st.metric("🟢 กำไรวันนี้", f"{total_today_profit:,.2f} บาท")
            with col3:
                st.metric("🔥 สินค้าขายดี", top_items)
        else:
            st.warning("⚠️ ยังไม่มีข้อมูลยอดขายวันนี้")

        # กราฟ 14 วัน
        sales_data["วันที่"] = sales_data["timestamp"].dt.date
        recent_df = sales_data.sort_values("วันที่", ascending=False).head(14)
        daily_summary = recent_df.groupby("วันที่").agg({"total_profit": "sum", "total_price": "sum"}).sort_index()

        st.subheader("📈 กราฟกำไรสุทธิรายวัน")
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(daily_summary.index, daily_summary["total_profit"], marker='o', color='#007aff', linewidth=2)
        ax1.set_ylabel("กำไรสุทธิ (บาท)")
        ax1.set_xlabel("วันที่")
        ax1.grid(True, linestyle='--', alpha=0.7)
        st.pyplot(fig1)

        st.subheader("💰 ยอดขายรวมและกำไรรวม 14 วันล่าสุด")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ยอดขายรวม", f"{daily_summary['total_price'].sum():,.0f} บาท")
        with col2:
            st.metric("กำไรสุทธิรวม", f"{daily_summary['total_profit'].sum():,.0f} บาท")

        st.subheader("🔥 วันที่ขายดีสุด")
        top_day = daily_summary["total_price"].idxmax()
        top_sales = daily_summary["total_price"].max()
        st.success(f"วันที่ {top_day} มียอดขายสูงสุด {top_sales:,.0f} บาท")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด Dashboard: {str(e)}")

# หน้าขายสินค้า
elif st.session_state.page == "ขายสินค้า":
    st.title("🧃 ขายสินค้าตู้เย็น")
    product_names = df["ชื่อสินค้า"].tolist()
    
    # ระบบค้นหาสินค้า
    search_term = st.text_input("🔍 ค้นหาสินค้า", help="พิมพ์ชื่อสินค้าเพื่อค้นหา")
    filtered_products = [p for p in product_names if search_term.lower() in p.lower()] if search_term else product_names
    selected = st.multiselect("เลือกสินค้าจากชื่อ", filtered_products, key="search_items")

    # แสดงสินค้าที่เลือก
    for p in selected:
        if p not in st.session_state.quantities:
            st.session_state.quantities[p] = 1
        
        qty = st.session_state.quantities[p]
        row = df[df["ชื่อสินค้า"] == p]
        stock = int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
        
        st.markdown(f"**{p}**")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1: 
            st.button("➖", key=f"dec_{safe_key(p)}", on_click=decrease_quantity, args=(p,))
        with col2: 
            st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
        with col3: 
            st.button("➕", key=f"inc_{safe_key(p)}", on_click=increase_quantity, args=(p,))
        with col4:
            stock_color = "red" if stock < 3 else "green"
            st.markdown(f"<span style='color:{stock_color}; font-size:18px; font-weight:bold'>📦 คงเหลือ: {stock} ชิ้น</span>", unsafe_allow_html=True)

    if st.button("➕ เพิ่มลงตะกร้า", type="primary"):
        for p in selected:
            qty = safe_int(st.session_state.quantities[p])
            if qty > 0:
                st.session_state.cart.append((p, qty))
        st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

    # แสดงรายการในตะกร้า
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    
    if not st.session_state.cart:
        st.info("ℹ️ ยังไม่มีสินค้าในตะกร้า")
    else:
        for item, qty in st.session_state.cart:
            row = df[df["ชื่อสินค้า"] == item].iloc[0]
            price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
            subtotal, profit = qty * price, qty * (price - cost)
            total_price += subtotal
            total_profit += profit
            st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")

    # ระบบรับเงิน
    st.subheader("💰 การชำระเงิน")
    st.session_state.paid_input = st.number_input("รับเงินจากลูกค้า", 
                                               value=st.session_state.paid_input, 
                                               step=1.0,
                                               min_value=0.0)
    
    # ปุ่มเงินด่วน
    st.write("เพิ่มเงินด่วน:")
    col1, col2, col3 = st.columns(3)
    with col1: st.button("20", on_click=lambda: add_money(20))
    with col2: st.button("50", on_click=lambda: add_money(50))
    with col3: st.button("100", on_click=lambda: add_money(100))
    col4, col5 = st.columns(2)
    with col4: st.button("500", on_click=lambda: add_money(500))
    with col5: st.button("1000", on_click=lambda: add_money(1000))
    
    if st.session_state.last_paid_click:
        if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}"):
            st.session_state.paid_input -= st.session_state.last_paid_click
            st.session_state.last_paid_click = 0

    # สรุปยอด
    st.info(f"📦 ยอดรวม: {total_price:,.2f} บาท | 🟢 กำไร: {total_profit:,.2f} บาท")
    if st.session_state.paid_input >= total_price:
        st.success(f"💰 เงินทอน: {st.session_state.paid_input - total_price:,.2f} บาท")
    else:
        st.warning(f"💸 เงินไม่พอ (ขาด: {total_price - st.session_state.paid_input:,.2f} บาท)")

    # ยืนยันการขาย
    if st.button("✅ ยืนยันการขาย", type="primary", disabled=not st.session_state.cart):
        for item, qty in st.session_state.cart:
            index = df[df["ชื่อสินค้า"] == item].index[0]
            row = df.loc[index]
            idx_in_sheet = index + 2
            new_out = safe_int(row["ออก"]) + qty
            new_left = safe_int(row["คงเหลือในตู้"]) - qty
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

    # ระบบจัดการสินค้า
    with st.expander("📦 การจัดการสินค้า", expanded=False):
        tab1, tab2, tab3 = st.tabs(["เติมสินค้า", "แก้ไขสินค้า", "รีเซ็ตยอด"])
        
        with tab1:
            restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock_select")
            restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
            if st.button("📥 ยืนยันเติมสินค้า"):
                index = df[df["ชื่อสินค้า"] == restock_item].index[0]
                idx_in_sheet = index + 2
                row = df.loc[index]
                new_in = safe_int(row["เข้า"]) + restock_qty
                new_left = safe_int(row["คงเหลือในตู้"]) + restock_qty
                worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
                worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
                st.success(f"✅ เติม {restock_item} จำนวน {restock_qty} ชิ้นเรียบร้อย")
                st.rerun()
        
        with tab2:
            edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_select")
            index = df[df["ชื่อสินค้า"] == edit_item].index[0]
            idx_in_sheet = index + 2
            row = df.loc[index]
            
            col1, col2 = st.columns(2)
            with col1:
                new_price = st.number_input("ราคาขาย", value=safe_float(row["ราคาขาย"]), key="edit_price")
            with col2:
                new_cost = st.number_input("ต้นทุน", value=safe_float(row["ต้นทุน"]), key="edit_cost")
            
            new_stock = st.number_input("คงเหลือในตู้", value=safe_int(row["คงเหลือในตู้"]), key="edit_stock", step=1)
            
            if st.button("💾 บันทึกการแก้ไข"):
                worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
                worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
                worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
                st.success(f"✅ อัปเดต {edit_item} เรียบร้อย")
                st.rerun()
        
        with tab3:
            st.warning("⚠️ การรีเซ็ตจะตั้งค่ายอด 'เข้า' และ 'ออก' เป็น 0 ทั้งหมด")
            if st.button("🔁 รีเซ็ตยอดเข้า-ออก (เริ่มวันใหม่)", type="secondary"):
                num_rows = len(df)
                worksheet.batch_update([
                    {"range": f"E2:E{num_rows+1}", "values": [[0]] * num_rows},
                    {"range": f"G2:G{num_rows+1}", "values": [[0]] * num_rows}
                ])
                st.success("✅ รีเซ็ตยอด 'เข้า' และ 'ออก' สำเร็จแล้วสำหรับวันใหม่")
                st.rerun()

# หน้าขายน้ำแข็ง
elif st.session_state.page == "ขายน้ำแข็ง":
    def reset_ice_session_state():
        ice_types = ["โม่", "หลอดใหญ่", "หลอดเล็ก", "ก้อน"]
        for ice_type in ice_types:
            for prefix in ["in_", "sell_out_"]:
                for suffix in ["_value"]:  # Removed _input from reset
                    key = f"{prefix}{ice_type}{suffix}"
                    st.session_state[key] = 0
        st.session_state["force_rerun"] = True

    st.title("🧊 ระบบขายน้ำแข็งเจริญค้า")
    
    iceflow_sheet = sheet.worksheet("iceflow")
    df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
    
    # ปรับรูปแบบข้อมูล
    df_ice["ชนิดน้ำแข็ง"] = df_ice["ชนิดน้ำแข็ง"].astype(str).str.strip().str.lower()
    df_ice["ราคาขายต่อหน่วย"] = pd.to_numeric(df_ice["ราคาขายต่อหน่วย"], errors='coerce')
    df_ice["ต้นทุนต่อหน่วย"] = pd.to_numeric(df_ice["ต้นทุนต่อหน่วย"], errors='coerce')
    df_ice = df_ice.dropna(subset=["ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย"])
    
    today_str = datetime.datetime.now().strftime("%-d/%-m/%Y")
    
    # ตรวจสอบและรีเซ็ตข้อมูลวันใหม่
    if not df_ice.empty and df_ice["วันที่"].iloc[0] != today_str:
        df_ice["วันที่"] = today_str
        df_ice["รับเข้า"] = 0
        df_ice["ขายออก"] = 0
        df_ice["จำนวนละลาย"] = 0
        df_ice["คงเหลือตอนเย็น"] = 0
        df_ice["กำไรรวม"] = 0
        df_ice["กำไรสุทธิ"] = 0
        iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
        st.info("🔄 ระบบรีเซ็ตยอดใหม่สำหรับวันนี้แล้ว")
        reset_ice_session_state()
    
    ice_types = ["โม่", "หลอดใหญ่", "หลอดเล็ก", "ก้อน"]
    
    # ส่วนรับเข้าน้ำแข็ง
    st.markdown("### 📦 โซนรับเข้าน้ำแข็ง")
    in_values = {}
    cols = st.columns(4)

    for i, ice_type in enumerate(ice_types):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type)]
        if not row.empty:
            idx = row.index[0]
            old_val = safe_int(df_ice.at[idx, "รับเข้า"])
            
            # Initialize session state if not exists
            if f"in_{ice_type}_value" not in st.session_state:
                st.session_state[f"in_{ice_type}_value"] = old_val
            
            with cols[i]:
                # Use a temporary variable for the input
                current_value = st.number_input(
                    f"📥 {ice_type}", 
                    min_value=0, 
                    value=st.session_state[f"in_{ice_type}_value"], 
                    key=f"in_{ice_type}_input"
                )
                # Update the session state value separately
                st.session_state[f"in_{ice_type}_value"] = current_value
                df_ice.at[idx, "รับเข้า"] = current_value
                
                # แสดงยอดคงเหลือ
                received = safe_int(df_ice.at[idx, "รับเข้า"])
                sold = safe_int(df_ice.at[idx, "ขายออก"])
                melted = safe_int(df_ice.at[idx, "จำนวนละลาย"])
                remaining = received - sold - melted
                
                st.metric("คงเหลือ", f"{remaining} ถุง")
        else:
            st.warning(f"❌ ไม่พบข้อมูลน้ำแข็งชนิด '{ice_type}'")

     # ปุ่มบันทึกยอดเติมน้ำแข็ง
    if st.button("📥 บันทึกยอดเติมน้ำแข็ง", type="primary"):
        try:
            iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
            st.success("✅ บันทึกยอดเติมน้ำแข็งแล้ว")
            
            # รีเซ็ตค่าที่ป้อนไว้ทั้งหมด
            reset_ice_session_state()
            
            # รีเซ็ต DataFrame เพื่อโหลดข้อมูลใหม่
            df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
            
            st.session_state["force_rerun"] = True
            st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")


    # ส่วนขายออกน้ำแข็ง
    st.markdown("### 💸 โซนขายออกน้ำแข็ง")
    total_income = 0
    total_profit = 0

    cols = st.columns(4)
    for i, ice_type in enumerate(ice_types):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type)]
        if not row.empty:
            idx = row.index[0]
            price = safe_float(df_ice.at[idx, "ราคาขายต่อหน่วย"])
            cost = safe_float(df_ice.at[idx, "ต้นทุนต่อหน่วย"])
            old_out = safe_int(df_ice.at[idx, "ขายออก"])
            
            # Initialize session state if not exists
            if f"sell_out_{ice_type}_value" not in st.session_state:
                st.session_state[f"sell_out_{ice_type}_value"] = old_out
            
            with cols[i]:
                # Use a temporary variable for the input
                current_value = st.number_input(
                    f"🧊 ขายออก {ice_type}", 
                    min_value=0, 
                    value=st.session_state[f"sell_out_{ice_type}_value"], 
                    key=f"sell_out_{ice_type}_input"
                )
                # Update the session state value separately
                st.session_state[f"sell_out_{ice_type}_value"] = current_value
                
                melted = safe_int(df_ice.at[idx, "จำนวนละลาย"])
                income = current_value * price
                profit = (current_value * (price - cost)) - (melted * cost)
                
                df_ice.at[idx, "ขายออก"] = current_value
                df_ice.at[idx, "คงเหลือตอนเย็น"] = safe_int(df_ice.at[idx, "รับเข้า"]) - current_value - melted
                df_ice.at[idx, "กำไรรวม"] = income
                df_ice.at[idx, "กำไรสุทธิ"] = profit
                df_ice.at[idx, "วันที่"] = today_str
                
                total_income += income
                total_profit += profit

    # ปุ่มบันทึกการขาย
    if st.button("✅ บันทึกการขายน้ำแข็ง", type="primary"):
        try:
            iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
            
            for _, row in df_ice.iterrows():
                summary_ws.append_row([
                    today_str,
                    row["ชนิดน้ำแข็ง"],
                    safe_int(row["ขายออก"]),
                    row["ราคาขายต่อหน่วย"],
                    row["ต้นทุนต่อหน่วย"],
                    row["ราคาขายต่อหน่วย"] - row["ต้นทุนต่อหน่วย"],
                    safe_int(row["ขายออก"]) * row["ราคาขายต่อหน่วย"],
                    safe_int(row["ขายออก"]) * (row["ราคาขายต่อหน่วย"] - row["ต้นทุนต่อหน่วย"]),
                    "ice"
                ])
            
            st.success("✅ บันทึกการขายน้ำแข็งเรียบร้อย และรีเซ็ตค่าฟอร์มแล้ว")
            
            # รีเซ็ตค่าที่ป้อนไว้ทั้งหมดหลังบันทึก
            reset_ice_session_state()
            
            # รีเซ็ต DataFrame เพื่อโหลดข้อมูลใหม่
            df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
            
            st.session_state["force_rerun"] = True
            st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
        
    # สรุปยอดขาย
    st.markdown("### 📊 สรุปยอดขาย")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 ยอดขายรวม", f"{total_income:,.2f} บาท")
    with col2:
        st.metric("🟢 กำไรสุทธิ", f"{total_profit:,.2f} บาท")
