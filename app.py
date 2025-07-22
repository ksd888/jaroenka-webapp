import streamlit as st
import datetime
from pytz import timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt
import time
import numpy as np
import logging

# ตั้งค่าการบันทึกข้อผิดพลาด
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ice_types = ["โม่", "หลอดใหญ่", "หลอดเล็ก", "ก้อน"]

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

/* กล่องข้อมูลน้ำแข็ง */
.ice-box {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
    background-color: #f8f9fa;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* หัวข้อกล่องน้ำแข็ง */
.ice-header {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 10px;
    border-bottom: 2px solid #007aff;
    padding-bottom: 5px;
}

/* เมตริกน้ำแข็ง */
.ice-metric {
    background-color: white;
    border-radius: 10px;
    padding: 10px;
    margin: 5px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* ปุ่มน้ำแข็ง */
.ice-button {
    width: 100%;
    margin: 5px 0;
}

/* สถานะสต็อก */
.stock-low {
    color: #e74c3c;
    font-weight: bold;
}
.stock-ok {
    color: #27ae60;
    font-weight: bold;
}
.stock-high {
    color: #2980b9;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ฟังก์ชันรีเซ็ตค่าเข้าออกละลายหลังบันทึก
def reset_ice_input_states():
    """รีเซ็ตเฉพาะค่าที่ป้อนเข้าและออก"""
    for key in list(st.session_state.keys()):
        if any(k in key for k in ["เข้า_", "ออก_", "ละลาย_"]):
            st.session_state[key] = 0

# คำนวณคงเหลือและกำไรสะสม
def calculate_ice_totals(df_ice):
    """คำนวณยอดคงเหลือและกำไรจาก DataFrame น้ำแข็ง"""
    try:
        df_ice["คงเหลือ"] = df_ice["เข้า"] - df_ice["ออก"] - df_ice["ละลาย"]
        df_ice["กำไร"] = (df_ice["ราคาขายต่อหน่วย"] - df_ice["ต้นทุนต่อหน่วย"]) * df_ice["ออก"]
        total_profit = df_ice["กำไร"].sum()
        return df_ice, total_profit
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณยอดน้ำแข็ง: {str(e)}")
        logger.error(f"Error calculating ice totals: {e}")
        return df_ice, 0

# เริ่มต้น session state
def initialize_session_state():
    """Initialize all required session state variables"""
    default_values = {
        'page': "ขายสินค้า",
        'cart': [],
        'quantities': {},
        'paid_input': 0.0,
        'last_paid_click': 0,
        'reset_search_items': False,
        'prev_paid_input': 0.0,
        'last_update': time.time(),
        'force_rerun': False
    }
    
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# เชื่อมต่อ Google Sheets
@st.cache_resource
def connect_google_sheets():
    """เชื่อมต่อกับ Google Sheets API"""
    try:
        if 'GCP_SERVICE_ACCOUNT' not in st.secrets:
            st.error("ไม่พบข้อมูลการเชื่อมต่อ Google Sheets ใน secrets")
            logger.error("Google Sheets connection info not found in secrets")
            return None
            
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(
            st.secrets["GCP_SERVICE_ACCOUNT"],
            scopes=scope
        )
        gc = gspread.authorize(credentials)
        logger.info("Connected to Google Sheets successfully")
        return gc
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {str(e)}")
        logger.error(f"Error connecting to Google Sheets: {e}")
        return None

# โหลดข้อมูลและทำความสะอาด
@st.cache_data(ttl=60)
def load_and_clean_data():
    """โหลดและทำความสะอาดข้อมูลสินค้าจาก Google Sheets"""
    try:
        gc = connect_google_sheets()
        if not gc:
            st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
            return pd.DataFrame()
            
        sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
        worksheet = sheet.worksheet("ตู้เย็น")
        df = pd.DataFrame(worksheet.get_all_records())
        
        if df.empty:
            return pd.DataFrame()
            
        # ทำความสะอาดข้อมูล
        df["ชื่อสินค้า"] = df["ชื่อสินค้า"].str.strip()
        numeric_cols = ["ราคาขาย", "ต้นทุน", "เข้า", "ออก", "คงเหลือในตู้"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
        logger.info("Loaded and cleaned product data successfully")
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}")
        logger.error(f"Error loading product data: {e}")
        return pd.DataFrame()

# Helper functions
def safe_key(text):
    """สร้างคีย์ที่ปลอดภัยจากข้อความ"""
    return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()

def safe_int(val):
    """แปลงค่าเป็น integer อย่างปลอดภัย"""
    try:
        return int(float(val))
    except:
        return 0

def safe_float(val):
    """แปลงค่าเป็น float อย่างปลอดภัย"""
    try:
        return float(val)
    except:
        return 0.0

def increase_quantity(p):
    """เพิ่มจำนวนสินค้าในตะกร้า"""
    if p in st.session_state.quantities:
        st.session_state.quantities[p] += 1
    else:
        st.session_state.quantities[p] = 1

def decrease_quantity(p):
    """ลดจำนวนสินค้าในตะกร้า"""
    if p in st.session_state.quantities:
        st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    else:
        st.session_state.quantities[p] = 1

def add_money(amount: int):
    """เพิ่มจำนวนเงินที่ลูกค้าจ่าย"""
    try:
        current = float(st.session_state.get('paid_input', 0.0))
        st.session_state.paid_input = current + amount
        st.session_state.last_paid_click = amount
        st.session_state.prev_paid_input = current + amount
    except Exception as e:
        st.error(f"Error adding money: {str(e)}")
        logger.error(f"Error adding money: {e}")

# เมนูหลัก
st.markdown("### 🚀 เมนูหลัก")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏪 ขายสินค้า"):
        st.session_state.page = "ขายสินค้า"
        st.rerun()
with col2:
    if st.button("🧊 ขายน้ำแข็ง"):
        st.session_state.page = "ขายน้ำแข็ง"
        st.rerun()
with col3:
    if st.button("📊 Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()

now = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")

# หน้า Dashboard
if st.session_state.page == "Dashboard":
    st.title("📊 Dashboard สถิติการขาย")
    
    # โหลดข้อมูลยอดขาย
    @st.cache_data(ttl=60)
    def load_sales_data():
        """โหลดข้อมูลยอดขายจาก Google Sheets"""
        try:
            gc = connect_google_sheets()
            if not gc:
                st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                return pd.DataFrame()
                
            sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
            summary_ws = sheet.worksheet("ยอดขาย")
            sales_df = pd.DataFrame(summary_ws.get_all_records())
            
            if sales_df.empty:
                return pd.DataFrame()
                
            # ทำความสะอาดข้อมูล
            sales_df['วันที่'] = pd.to_datetime(sales_df['วันที่'], errors='coerce')
            sales_df['รายการ'] = sales_df['รายการ'].astype(str)
            sales_df['ยอดขาย'] = pd.to_numeric(sales_df['ยอดขาย'], errors='coerce').fillna(0)
            sales_df['กำไร'] = pd.to_numeric(sales_df['กำไร'], errors='coerce').fillna(0)
            sales_df['ประเภท'] = sales_df['ประเภท'].astype(str)
            
            logger.info("Loaded sales data successfully")
            return sales_df
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลยอดขาย: {str(e)}")
            logger.error(f"Error loading sales data: {e}")
            return pd.DataFrame()

    sales_df = load_sales_data()
    
    if not sales_df.empty:
        # แสดงสถิติการขาย
        col1, col2, col3 = st.columns(3)
        with col1:
            total_sales = sales_df['ยอดขาย'].sum()
            st.metric("💰 ยอดขายรวม", f"{total_sales:,.2f} บาท")
        with col2:
            total_profit = sales_df['กำไร'].sum()
            st.metric("🟢 กำไรรวม", f"{total_profit:,.2f} บาท")
        with col3:
            avg_sale = total_sales / len(sales_df) if len(sales_df) > 0 else 0
            st.metric("📊 ยอดขายเฉลี่ยต่อรายการ", f"{avg_sale:,.2f} บาท")
        
        # กราฟยอดขายรายวัน
        st.subheader("📈 ยอดขายรายวัน")
        try:
            daily_sales = sales_df.groupby(sales_df['วันที่'].dt.date)['ยอดขาย'].sum().reset_index()
            
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(daily_sales['วันที่'], daily_sales['ยอดขาย'], marker='o', color='#007aff')
            ax.set_title('ยอดขายรายวัน')
            ax.set_xlabel('วันที่')
            ax.set_ylabel('ยอดขาย (บาท)')
            ax.grid(True)
            st.pyplot(fig)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้างกราฟ: {str(e)}")
            logger.error(f"Error creating sales chart: {e}")
        
        # สินค้าขายดี
        st.subheader("🏆 สินค้าขายดี")
        try:
            if 'รายการ' in sales_df.columns:
                top_products = sales_df['รายการ'].value_counts().head(10)
                st.bar_chart(top_products)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการแสดงสินค้าขายดี: {str(e)}")
            logger.error(f"Error showing top products: {e}")
    else:
        st.warning("ไม่มีข้อมูลยอดขาย")

# หน้าขายสินค้า
elif st.session_state.page == "ขายสินค้า":
    st.title("🧃 ขายสินค้าตู้เย็น")
    
    df = load_and_clean_data()
    if df.empty:
        st.error("ไม่สามารถโหลดข้อมูลสินค้าได้")
        st.stop()
    
    product_names = df["ชื่อสินค้า"].tolist()
    
    # ระบบค้นหาสินค้า
    search_term = st.text_input("🔍 ค้นหาสินค้า", help="พิมพ์ชื่อสินค้าเพื่อค้นหา", key="search_term")
    filtered_products = [p for p in product_names if search_term.lower() in p.lower()] if search_term else product_names
    
    selected_product = st.selectbox("เลือกสินค้า", [""] + filtered_products, key="product_select")
    
    if selected_product:
        if selected_product not in st.session_state.quantities:
            st.session_state.quantities[selected_product] = 1
        
        qty = st.session_state.quantities[selected_product]
        row = df[df["ชื่อสินค้า"] == selected_product]
        stock = int(row["คงเหลือในตู้"].values[0]) if not row.empty else 0
        
        st.markdown(f"**{selected_product}**")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1: 
            st.button("➖", key=f"dec_{safe_key(selected_product)}", on_click=decrease_quantity, args=(selected_product,))
        with col2: 
            st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", unsafe_allow_html=True)
        with col3: 
            st.button("➕", key=f"inc_{safe_key(selected_product)}", on_click=increase_quantity, args=(selected_product,))
        with col4:
            stock_color = "red" if stock < 3 else "green"
            st.markdown(f"<span style='color:{stock_color}; font-size:18px; font-weight:bold'>📦 คงเหลือ: {stock} ชิ้น</span>", unsafe_allow_html=True)

        if st.button("➕ เพิ่มลงตะกร้า", type="primary", key="add_to_cart"):
            qty = safe_int(st.session_state.quantities[selected_product])
            if qty > 0:
                if stock >= qty:
                    st.session_state.cart.append((selected_product, qty))
                    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")
                    st.session_state.quantities[selected_product] = 1
                    st.rerun()
                else:
                    st.error(f"⚠️ สินค้ามีไม่พอในสต็อก (เหลือ {stock} ชิ้น)")

    # แสดงรายการในตะกร้า
    st.subheader("📋 รายการขาย")
    total_price, total_profit = 0, 0
    
    if not st.session_state.cart:
        st.info("ℹ️ ยังไม่มีสินค้าในตะกร้า")
    else:
        for idx, (item, qty) in enumerate(st.session_state.cart):
            row = df[df["ชื่อสินค้า"] == item]
            if not row.empty:
                row = row.iloc[0]
                price, cost = safe_float(row["ราคาขาย"]), safe_float(row["ต้นทุน"])
                subtotal, profit = qty * price, qty * (price - cost)
                total_price += subtotal
                total_profit += profit
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"- {item} x {qty} = {subtotal:.2f} บาท")
                with col2:
                    if st.button("🗑️", key=f"remove_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.rerun()

    # ระบบรับเงิน
    st.subheader("💰 การชำระเงิน")
    paid_input = st.number_input(
        "รับเงินจากลูกค้า", 
        value=float(st.session_state.get('paid_input', 0.0)), 
        step=1.0,
        min_value=0.0,
        key="paid_input_widget"
    )

    # Update session state only if the value changed
    if paid_input != st.session_state.prev_paid_input:
        try:
            st.session_state.paid_input = paid_input
            st.session_state.prev_paid_input = paid_input
        except Exception as e:
            st.error(f"Error updating payment amount: {str(e)}")
            logger.error(f"Error updating payment: {e}")
    
    # ปุ่มเงินด่วน
    st.write("เพิ่มเงินด่วน:")
    col1, col2, col3 = st.columns(3)
    with col1: st.button("20", on_click=lambda: add_money(20), key="add_20")
    with col2: st.button("50", on_click=lambda: add_money(50), key="add_50")
    with col3: st.button("100", on_click=lambda: add_money(100), key="add_100")
    col4, col5 = st.columns(2)
    with col4: st.button("500", on_click=lambda: add_money(500), key="add_500")
    with col5: st.button("1000", on_click=lambda: add_money(1000), key="add_1000")
    
    if st.session_state.last_paid_click:
        if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}", key="cancel_last"):
            try:
                st.session_state.paid_input -= st.session_state.last_paid_click
                st.session_state.prev_paid_input = st.session_state.paid_input
                st.session_state.last_paid_click = 0
                st.rerun()
            except Exception as e:
                st.error(f"Error canceling last payment: {str(e)}")
                logger.error(f"Error canceling payment: {e}")

    # สรุปยอด
    st.info(f"📦 ยอดรวม: {total_price:,.2f} บาท | 🟢 กำไร: {total_profit:,.2f} บาท")
    if st.session_state.paid_input >= total_price:
        st.success(f"💰 เงินทอน: {st.session_state.paid_input - total_price:,.2f} บาท")
    else:
        st.warning(f"💸 เงินไม่พอ (ขาด: {total_price - st.session_state.paid_input:,.2f} บาท)")

    # ยืนยันการขาย
    if st.button("✅ ยืนยันการขาย", type="primary", disabled=not st.session_state.cart, key="confirm_sale"):
        try:
            with st.spinner("กำลังบันทึกการขาย..."):
                gc = connect_google_sheets()
                if not gc:
                    st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                    return
                    
                sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
                worksheet = sheet.worksheet("ตู้เย็น")
                summary_ws = sheet.worksheet("ยอดขาย")
                
                # อัปเดตสต็อกสินค้า
                for item, qty in st.session_state.cart:
                    index = df[df["ชื่อสินค้า"] == item].index[0]
                    row = df.loc[index]
                    idx_in_sheet = index + 2
                    new_out = safe_int(row["ออก"]) + qty
                    new_left = safe_int(row["คงเหลือในตู้"]) - qty
                    
                    # อัปเดตเซลล์ใน Google Sheets
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)

                # บันทึกการขาย
                summary_ws.append_row([
                    now,
                    ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
                    total_price,
                    total_profit,
                    st.session_state.paid_input,
                    st.session_state.paid_input - total_price,
                    "drink"
                ])
                
                # อัปเดตข้อมูลใน cache
                st.cache_data.clear()
                
                # รีเซ็ตตะกร้าและการชำระเงิน
                st.session_state.cart = []
                st.session_state.paid_input = 0.0
                st.session_state.prev_paid_input = 0.0
                st.session_state.last_paid_click = 0
                
                st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
                logger.info(f"Sale recorded: {total_price} THB, Profit: {total_profit} THB")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Error confirming sale: {str(e)}")
            logger.error(f"Error confirming sale: {e}")

    # ระบบจัดการสินค้า
    with st.expander("📦 การจัดการสินค้า", expanded=False):
        tab1, tab2, tab3 = st.tabs(["เติมสินค้า", "แก้ไขสินค้า", "รีเซ็ตยอด"])
        
        with tab1:
            restock_item = st.selectbox("เลือกสินค้า", product_names, key="restock_select")
            restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
            if st.button("📥 ยืนยันเติมสินค้า", key="confirm_restock"):
                try:
                    index = df[df["ชื่อสินค้า"] == restock_item].index[0]
                    idx_in_sheet = index + 2
                    row = df.loc[index]
                    new_in = safe_int(row["เข้า"]) + restock_qty
                    new_left = safe_int(row["คงเหลือในตู้"]) + restock_qty
                    
                    gc = connect_google_sheets()
                    if not gc:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                        return
                        
                    sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
                    worksheet = sheet.worksheet("ตู้เย็น")
                    
                    # อัปเดตข้อมูล
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("เข้า") + 1, new_in)
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
                    
                    st.success(f"✅ เติม {restock_item} จำนวน {restock_qty} ชิ้นเรียบร้อย")
                    logger.info(f"Restocked: {restock_item} x {restock_qty}")
                    
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการเติมสินค้า: {str(e)}")
                    logger.error(f"Error restocking: {e}")
        
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
            
            if st.button("💾 บันทึกการแก้ไข", key="save_edit"):
                try:
                    gc = connect_google_sheets()
                    if not gc:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                        return
                        
                    sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
                    worksheet = sheet.worksheet("ตู้เย็น")
                    
                    # อัปเดตข้อมูล
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ราคาขาย") + 1, new_price)
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ต้นทุน") + 1, new_cost)
                    worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_stock)
                    
                    st.success(f"✅ อัปเดต {edit_item} เรียบร้อย")
                    logger.info(f"Updated product: {edit_item}")
                    
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอัปเดตสินค้า: {str(e)}")
                    logger.error(f"Error updating product: {e}")
        
        with tab3:
            st.warning("⚠️ การรีเซ็ตจะตั้งค่ายอด 'เข้า' และ 'ออก' เป็น 0 ทั้งหมด")
            if st.button("🔁 รีเซ็ตยอดเข้า-ออก (เริ่มวันใหม่)", type="secondary", key="reset_counts"):
                try:
                    gc = connect_google_sheets()
                    if not gc:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                        return
                        
                    sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
                    worksheet = sheet.worksheet("ตู้เย็น")
                    num_rows = len(df)
                    
                    # รีเซ็ตข้อมูลแบบ batch
                    worksheet.batch_update([
                        {"range": f"E2:E{num_rows+1}", "values": [[0]] * num_rows},
                        {"range": f"G2:G{num_rows+1}", "values": [[0]] * num_rows}
                    ])
                    
                    st.success("✅ รีเซ็ตยอด 'เข้า' และ 'ออก' สำเร็จแล้วสำหรับวันใหม่")
                    logger.info("Reset product counts for new day")
                    
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการรีเซ็ตยอด: {str(e)}")
                    logger.error(f"Error resetting counts: {e}")

elif st.session_state.page == "ขายน้ำแข็ง":
    def reset_ice_session_state():
        """รีเซ็ตเฉพาะค่าที่ป้อนเข้าและออก"""
        for ice_type in ice_types:
            st.session_state.pop(f"in_{ice_type}", None)
            st.session_state.pop(f"sell_out_{ice_type}", None)
        st.session_state["force_rerun"] = True

    st.title("🧊 ระบบขายน้ำแข็งเจริญค้า")
    
    @st.cache_data(ttl=60)
    def load_ice_data():
        """โหลดข้อมูลน้ำแข็งจาก Google Sheets"""
        try:
            gc = connect_google_sheets()
            if not gc:
                st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                return pd.DataFrame()
                
            sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
            iceflow_sheet = sheet.worksheet("iceflow")
            records = iceflow_sheet.get_all_records()
            
            if not records:
                return pd.DataFrame()
                
            df_ice = pd.DataFrame(records)
            
            # ตรวจสอบคอลัมน์ที่จำเป็น
            required_cols = ["ชนิดน้ำแข็ง", "ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย", "รับเข้า", "ขายออก", "จำนวนละลาย"]
            for col in required_cols:
                if col not in df_ice.columns:
                    df_ice[col] = 0  # เพิ่มคอลัมน์ที่ขาดด้วยค่าเริ่มต้น 0
            
            # เพิ่มคอลัมน์วันที่หากไม่มี
            if "วันที่" not in df_ice.columns:
                df_ice["วันที่"] = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%-d/%-m/%Y")
            
            # ทำความสะอาดข้อมูล
            df_ice["ชนิดน้ำแข็ง"] = df_ice["ชนิดน้ำแข็ง"].astype(str).str.strip().str.lower()
            numeric_cols = ["ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย", "รับเข้า", "ขายออก", "จำนวนละลาย"]
            for col in numeric_cols:
                df_ice[col] = pd.to_numeric(df_ice[col], errors='coerce').fillna(0)
            
            logger.info("Loaded ice data successfully")
            return df_ice
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลน้ำแข็ง: {str(e)}")
            logger.error(f"Error loading ice data: {e}")
            return pd.DataFrame()

    df_ice = load_ice_data()
    
    if df_ice.empty:
        st.error("ไม่สามารถโหลดข้อมูลน้ำแข็งได้ กรุณาตรวจสอบการเชื่อมต่อ")
        st.stop()
    
    today_str = datetime.datetime.now(timezone("Asia/Bangkok")).strftime("%-d/%-m/%Y")
    
    # ตรวจสอบและรีเซ็ตข้อมูลหากเป็นวันใหม่
    if not df_ice.empty and 'วันที่' in df_ice.columns and df_ice["วันที่"].iloc[0] != today_str:
        try:
            with st.spinner("กำลังรีเซ็ตข้อมูลสำหรับวันใหม่..."):
                gc = connect_google_sheets()
                if not gc:
                    st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                    return
                    
                sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
                iceflow_sheet = sheet.worksheet("iceflow")
                
                # รีเซ็ตข้อมูล
                df_ice["วันที่"] = today_str
                df_ice["รับเข้า"] = 0
                df_ice["ขายออก"] = 0
                df_ice["จำนวนละลาย"] = 0
                df_ice["คงเหลือตอนเย็น"] = 0
                df_ice["กำไรรวม"] = 0
                df_ice["กำไรสุทธิ"] = 0
                
                # อัปเดต Google Sheets
                iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
                
                st.info("🔄 ระบบรีเซ็ตยอดใหม่สำหรับวันนี้แล้ว")
                logger.info("Reset ice data for new day")
                
                reset_ice_session_state()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการรีเซ็ตข้อมูล: {str(e)}")
            logger.error(f"Error resetting ice data: {e}")
    
    # เก็บค่าเริ่มต้นก่อนทำการขาย
    initial_sales = {}
    for ice_type in ice_types:
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            initial_sales[ice_type] = safe_int(df_ice.at[idx, "ขายออก"])

    # ส่วนรับเข้าน้ำแข็ง
    st.markdown("### 📦 โซนรับเข้าน้ำแข็ง")
    cols = st.columns(4)

    for i, ice_type in enumerate(ice_types):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            default_val = safe_int(df_ice.at[idx, "รับเข้า"])
            received = safe_int(df_ice.at[idx, "รับเข้า"])
            sold = safe_int(df_ice.at[idx, "ขายออก"])
            melted = safe_int(df_ice.at[idx, "จำนวนละลาย"])
            remaining = received - sold - melted
            
            with cols[i]:
                st.markdown(f"""
                <div class="ice-box">
                    <div class="ice-header">น้ำแข็ง{ice_type}</div>
                    <div class="ice-metric">
                        <div>📥 ยอดรับเข้า: <strong>{received}</strong> ถุง</div>
                        <div class="{'stock-low' if remaining < 5 else 'stock-ok' if remaining < 15 else 'stock-high'}">
                            📦 คงเหลือ: <strong>{remaining}</strong> ถุง
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                added_value = st.number_input(
                    f"เพิ่มเข้า {ice_type}", 
                    min_value=0, 
                    step=1, 
                    key=f"increase_{ice_type}",
                    help=f"เพิ่มจำนวนน้ำแข็ง{ice_type}ที่รับเข้า"
                )

                if added_value > 0:
                    new_total = default_val + added_value
                    df_ice.at[idx, "รับเข้า"] = new_total
                    st.success(f"✅ รวมเป็น {new_total} ถุง")
                else:
                    df_ice.at[idx, "รับเข้า"] = default_val

  if st.button("📥 บันทึกยอดเติมน้ำแข็ง", type="primary", key="unique_btn_save_restock_ice"):
    try:
        with st.spinner("กำลังบันทึกข้อมูล..."):
            gc = connect_google_sheets()
            if not gc:
                st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                st.stop()
            
            sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
            iceflow_sheet = sheet.worksheet("iceflow")
            iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
            reset_ice_session_state()
            st.cache_data.clear()
            st.success("✅ บันทึกยอดเติมน้ำแข็งแล้ว")
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
        
    # ส่วนขายออกน้ำแข็ง
    st.markdown("### 💸 โซนขายออกน้ำแข็ง")
    total_income = 0
    total_profit = 0

    if not df_ice.empty and 'ชนิดน้ำแข็ง' in df_ice.columns:
        cols = st.columns(4)
        
        for i, ice_type in enumerate(ice_types):
            row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
            if not row.empty:
                idx = row.index[0]
                price_per_bag = safe_float(df_ice.at[idx, "ราคาขายต่อหน่วย"])
                cost_per_bag = safe_float(df_ice.at[idx, "ต้นทุนต่อหน่วย"])
                current_sold = safe_int(df_ice.at[idx, "ขายออก"])
                stock_decrease = 0  # Initialize

                with cols[i]:
                    st.markdown(f"""
                    <div class="ice-box">
                        <div class="ice-header">ขายน้ำแข็ง{ice_type}</div>
                        <div class="ice-metric">
                            <div>💰 ราคา: <strong>{price_per_bag:,.2f}</strong> บาท/ถุง</div>
                            <div>📤 ยอดขาย: <strong>{current_sold}</strong> ถุง</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # ปุ่มขายแบบเต็มถุง
                    full_bag_sold = st.number_input(
                        f"เพิ่มขายออก {ice_type} (เต็มถุง)", 
                        min_value=0, 
                        step=1, 
                        key=f"add_sell_{ice_type}",
                        help=f"เพิ่มจำนวนน้ำแข็ง{ice_type}ที่ขายออกแบบเต็มถุง"
                    )
                    
                    # ส่วนแบ่งขายแบบบาท
                    st.markdown("<div style='margin-top:10px;'>หรือแบ่งขาย:</div>", unsafe_allow_html=True)
                    divided_amount = st.selectbox(
                        f"แบ่งขาย {ice_type} (บาท)",
                        [0, 5, 10, 20, 30, 40],
                        key=f"divided_{ice_type}"
                    )
                    
                    # คำนวณยอดขายและกำไร
                    if full_bag_sold > 0 or divided_amount > 0:
                        # ขายแบบเต็มถุง
                        income = full_bag_sold * price_per_bag
                        profit = full_bag_sold * (price_per_bag - cost_per_bag)
                        
                        # ขายแบบแบ่ง
                        if divided_amount > 0:
                            if ice_type == "ก้อน":
                                # น้ำแข็งก้อนแบ่งขายก้อนละ 5 บาท (1 ถุงมี 10 ก้อน)
                                pieces_sold = divided_amount / 5
                                divided_income = divided_amount
                                divided_profit = divided_amount - (pieces_sold * (cost_per_bag / 10))
                                stock_decrease = pieces_sold / 10  # 1 ถุง = 10 ก้อน
                            else:
                                # น้ำแข็งอื่นๆ แบ่งตามสัดส่วน
                                divided_income = divided_amount
                                stock_decrease = divided_amount / price_per_bag
                                divided_profit = divided_amount - (stock_decrease * cost_per_bag)
                            
                            income += divided_income
                            profit += divided_profit
                        
                        # อัปเดตข้อมูลใน DataFrame
                        df_ice.at[idx, "ขายออก"] = current_sold + full_bag_sold + stock_decrease
                        df_ice.at[idx, "คงเหลือตอนเย็น"] = safe_int(df_ice.at[idx, "รับเข้า"]) - df_ice.at[idx, "ขายออก"] - safe_int(df_ice.at[idx, "จำนวนละลาย"])
                        df_ice.at[idx, "กำไรรวม"] = income
                        df_ice.at[idx, "กำไรสุทธิ"] = profit
                        
                        total_income += income
                        total_profit += profit

   if st.button("✅ บันทึกการขายน้ำแข็ง", type="primary", key="save_ice_sale"):
    try:
        with st.spinner("กำลังบันทึกการขาย..."):
            gc = connect_google_sheets()
            if not gc:
                st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                st.stop()
                
            sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
            iceflow_sheet = sheet.worksheet("iceflow")
            summary_ws = sheet.worksheet("ยอดขาย")

            # แปลงค่า int64/float64 เป็น int/float ปกติก่อนบันทึก
            df_ice = df_ice.applymap(lambda x: int(x) if isinstance(x, (np.int64, np.float64)) and x == x else x)
            
            # บันทึกข้อมูลน้ำแข็ง
            iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
            
            # บันทึกรายการขาย
            for ice_type in ice_types:
                row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
                if not row.empty:
                    idx = row.index[0]
                    current_sold = safe_int(df_ice.at[idx, "ขายออก"])
                    sold_in_this_session = max(0, current_sold - initial_sales.get(ice_type, 0))
                    
                    if sold_in_this_session > 0:
                        summary_ws.append_row([
                            today_str,
                            f"{ice_type} (ขาย {sold_in_this_session:.2f} ถุง)",
                            float(sold_in_this_session),
                            float(df_ice.at[idx, "ราคาขายต่อหน่วย"]),
                            float(df_ice.at[idx, "ต้นทุนต่อหน่วย"]),
                            "ice"
                        ])
            
            reset_ice_session_state()
            st.cache_data.clear()
            st.success("✅ บันทึกการขายน้ำแข็งเรียบร้อย")
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
        logger.error(f"Error saving ice sale: {e}")
    # ส่วนจัดการน้ำแข็งที่ละลาย
    st.markdown("### 🧊 การจัดการน้ำแข็งที่ละลาย")
    melted_cols = st.columns(4)
    
    for i, ice_type in enumerate(ice_types):
    row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
    if not row.empty:
        idx = row.index[0]
        with melted_cols[i]:
            melted_qty = st.number_input(
                f"ละลาย {ice_type}", 
                min_value=0, 
                value=safe_int(df_ice.at[idx, "จำนวนละลาย"]),
                key=f"melted_{ice_type}"
            )
            df_ice.at[idx, "จำนวนละลาย"] = melted_qty
            # อัปเดตค่าคงเหลือตอนเย็น
            df_ice.at[idx, "คงเหลือตอนเย็น"] = safe_int(df_ice.at[idx, "รับเข้า"]) - safe_int(df_ice.at[idx, "ขายออก"]) - melted_qty
    # สรุปยอดขาย
    st.markdown("### 📊 สรุปยอดขาย")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 ยอดขายรวม", f"{total_income:,.2f} บาท")
    with col2:
        st.metric("🟢 กำไรสุทธิ", f"{total_profit:,.2f} บาท")
