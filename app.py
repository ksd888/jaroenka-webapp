# Standard library
import datetime
import time
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

# Third-party
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import gspread
from pytz import timezone
from google.oauth2.service_account import Credentials

# Local/Try imports
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    st.warning("⚠️ โมดูล pyperclip ไม่ติดตั้ง การคัดลอกข้อผิดพลาดจะไม่ทำงาน")
    
# ตั้งค่าการบันทึกข้อผิดพลาด
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ค่าคงที่
ICE_TYPES = ['โม่', 'หลอดเล็ก', 'หลอดใหญ่', 'ก้อน']
SHEET_ID = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
TIMEZONE = "Asia/Bangkok"

def set_custom_css():
    """ตั้งค่า CSS แบบกำหนดเองสำหรับแอปพลิเคชัน"""
    st.markdown("""
    <style>
    /* พื้นหลังและตัวหนังสือหลัก */
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

    /* Input fields */
    input, textarea, .stTextInput > div > div > input, .stNumberInput input {
        background-color: #f2f2f7 !important;
        color: #000000 !important;
        font-weight: bold !important;
        font-size: 18px;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    /* Custom Checkbox */
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

    /* Alert messages */
    .stMarkdown span[style*="color:red"] {
        font-size: 20px !important;
        font-weight: bold !important;
        padding: 5px;
        border-radius: 5px;
    }

    /* Data boxes */
    .css-1kyxreq {
        background-color: #f9f9f9 !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
    }

    /* Ice box styles */
    .ice-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .ice-header {
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 10px;
        color: #007aff;
        text-align: center;
    }
    .ice-metric {
        font-size: 16px;
        line-height: 1.6;
    }
    .stock-high {
        color: #28a745;
        font-weight: bold;
    }
    .stock-ok {
        color: #ffc107;
        font-weight: bold;
    }
    .stock-low {
        color: #dc3545;
        font-weight: bold;
    }

    /* Metric cards */
    .stMetric {
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
        padding: 15px !important;
        border: 1px solid #e0e0e0 !important;
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #007aff !important;
    }

    /* Select boxes */
    .stSelectbox > div > div > select {
        font-size: 16px !important;
        padding: 8px 12px !important;
    }

    /* Tooltips */
    .stTooltip {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

def safe_int(val: str | float | None) -> int:
    """แปลงค่าเป็น integer อย่างปลอดภัย"""
    if val is None or pd.isna(val) or val == '':
        return 0
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return int(float(val))
    except (ValueError, TypeError):
        return 0

def safe_float(val):
    """แปลงค่าเป็น float อย่างปลอดภัย"""
    if val is None or pd.isna(val) or val == '':
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def safe_key(text):
    """สร้างคีย์ที่ปลอดภัยจากข้อความ"""
    return text.replace(" ", "_").replace(".", "_").replace("/", "_").lower()

def initialize_session_state():
    """Initialize all required session state variables"""
    if 'page' not in st.session_state:
        st.session_state.page = "ขายสินค้า"
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'quantities' not in st.session_state:
        st.session_state.quantities = {}
    if 'paid_input' not in st.session_state:
        st.session_state.paid_input = 0.0
    if 'last_paid_click' not in st.session_state:
        st.session_state.last_paid_click = 0
    if 'reset_search_items' not in st.session_state:
        st.session_state.reset_search_items = False
    if 'prev_paid_input' not in st.session_state:
        st.session_state.prev_paid_input = 0.0
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    if 'force_rerun' not in st.session_state:
        st.session_state.force_rerun = False
    if 'ice_data' not in st.session_state:  
        st.session_state.ice_data = {}
    if 'ice_sales' not in st.session_state:  
        st.session_state.ice_sales = {}

def clear_cart():
    """ล้างตะกร้าสินค้าทั้งหมด"""
    st.session_state.cart = []
    st.session_state.quantities = {}
    st.session_state.paid_input = 0.0
    st.session_state.last_paid_click = 0
    st.session_state.prev_paid_input = 0.0

def reset_ice_session_state():
    """รีเซ็ตเฉพาะค่าที่ป้อนเข้าและออกสำหรับระบบน้ำแข็ง"""
    try:
        # แก้ไข: ลบเฉพาะ input fields ไม่ลบข้อมูลน้ำแข็ง
        for ice_type in ICE_TYPES:
            keys_to_delete = [
                f"increase_{ice_type}",
                f"add_sell_{ice_type}",
                f"divided_{ice_type}",
                f"melted_{ice_type}"  # เพิ่มคีย์สำหรับน้ำแข็งที่ละลาย
            ]
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
        
        st.session_state.force_rerun = True
        logger.info("Ice form inputs reset successfully")
    except Exception as e:
        logger.error(f"Error resetting ice session state: {e}")
        st.error(f"เกิดข้อผิดพลาดในการรีเซ็ตข้อมูลน้ำแข็ง: {str(e)}")

# การเชื่อมต่อ Google Sheets
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
        handle_error(e, "การเชื่อมต่อ Google Sheets")
        return None

@st.cache_data(ttl=60)
def load_product_data():
    """โหลดและทำความสะอาดข้อมูลสินค้าจาก Google Sheets"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return pd.DataFrame()
            
        sheet = gc.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("ตู้เย็น")
        df = pd.DataFrame(worksheet.get_all_records())
        
        if df.empty:
            return pd.DataFrame()
        
        # ✅ ตรวจสอบคอลัมน์ที่จำเป็น
        required_cols = ["ชื่อสินค้า", "ราคาขาย", "ต้นทุน", "เข้า", "ออก", "คงเหลือในตู้"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ โครงสร้างข้อมูลไม่ครบ: ขาดคอลัมน์ {', '.join(missing)}")
            st.write("คอลัมน์ที่มี:", list(df.columns))
            return pd.DataFrame()

        # ✅ ทำความสะอาดข้อมูล
        df["ชื่อสินค้า"] = df["ชื่อสินค้า"].astype(str).str.strip()
        for col in required_cols[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลสินค้า: {str(e)}")
        logger.error(f"Error loading product data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_customer_debt_data():
    """โหลดข้อมูลลูกค้าค้างเงิน"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return pd.DataFrame()
            
        sheet = gc.open_by_key(SHEET_ID)
        try:
            worksheet = sheet.worksheet("ลูกค้าค้างเงิน")
            df = pd.DataFrame(worksheet.get_all_records())
        except gspread.WorksheetNotFound:
            # สร้างชีทใหม่หากไม่พบ
            worksheet = sheet.add_worksheet(title="ลูกค้าค้างเงิน", rows=100, cols=10)
            df = pd.DataFrame(columns=[
                "วันที่",
                "ชื่อลูกค้า",
                "สายส่ง",
                "ยอดค้าง",
                "ชำระแล้ว",
                "คงค้าง",
                "หมายเหตุ"
            ])
            worksheet.update([df.columns.tolist()] + df.values.tolist())
            return df
        
        return df
    except Exception as e:
        handle_error(e, "การโหลดข้อมูลลูกค้าค้างเงิน")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_sales_data() -> pd.DataFrame:
    """โหลดข้อมูลยอดขายจาก Google Sheets"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return pd.DataFrame()
            
        sheet = gc.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("ยอดขาย")
        df = pd.DataFrame(worksheet.get_all_records())
        
        if df.empty:
            return pd.DataFrame()

        # ✅ ทำความสะอาดคอลัมน์ตัวเลข (ใช้ชื่อจริงจาก Sheet)
        numeric_cols = ["ยอดขาย", "กำไร"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    except Exception as e:
        handle_error(e, "การโหลดข้อมูลยอดขาย")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_ice_data():
    """โหลดและทำความสะอาดข้อมูลน้ำแข็งจาก Google Sheets"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return pd.DataFrame()
            
        sheet = gc.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("iceflow")
        df_ice = pd.DataFrame(worksheet.get_all_records())
        
        if df_ice.empty:
            return pd.DataFrame()
            
        # ตรวจสอบและเพิ่มคอลัมน์ที่จำเป็นหากไม่มี
        required_cols = {
            "ชนิดน้ำแข็ง": "",
            "ราคาขายต่อหน่วย": 0,
            "ต้นทุนต่อหน่วย": 0,
            "รับเข้า": 0,
            "ขายออก": 0,
            "จำนวนละลาย": 0,
            "กำไรสุทธิ": 0,
            "ยอดขายรวม": 0,
            "วันที่": datetime.datetime.now(timezone(TIMEZONE)).strftime("%-d/%-m/%Y")
        }
        
        for col, default_val in required_cols.items():
            if col not in df_ice.columns:
                df_ice[col] = default_val
                
        # ทำความสะอาดข้อมูล
        df_ice["ชนิดน้ำแข็ง"] = df_ice["ชนิดน้ำแข็ง"].astype(str).str.strip().str.lower()
        numeric_cols = ["ราคาขายต่อหน่วย", "ต้นทุนต่อหน่วย", "รับเข้า", "ขายออก", "จำนวนละลาย", "กำไรสุทธิ", "ยอดขายรวม"]
        for col in numeric_cols:
            df_ice[col] = pd.to_numeric(df_ice[col], errors='coerce').fillna(0)
            
        return df_ice
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลน้ำแข็ง: {str(e)}")
        logger.error(f"Error loading ice data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_delivery_data(chain_name: str) -> pd.DataFrame:
    """โหลดข้อมูลการส่งน้ำแข็งสำหรับสายส่งที่ระบุ"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return pd.DataFrame()
            
        sheet = gc.open_by_key(SHEET_ID)
        try:
            worksheet = sheet.worksheet(chain_name)
            df = pd.DataFrame(worksheet.get_all_records())
        except gspread.WorksheetNotFound:
            # สร้างชีทใหม่หากไม่พบ
            worksheet = sheet.add_worksheet(title=chain_name, rows=100, cols=20)
            df = pd.DataFrame(columns=[
                "วันที่",
                "น้ำแข็งโม่_ใช้",
                "น้ำแข็งโม่_เหลือ",
                "น้ำแข็งโม่_ค้าง",
                "น้ำแข็งโม่_ละลาย",
                "น้ำแข็งหลอดเล็ก_ใช้",
                "น้ำแข็งหลอดเล็ก_เหลือ",
                "น้ำแข็งหลอดเล็ก_ค้าง",
                "น้ำแข็งหลอดเล็ก_ละลาย",
                "น้ำแข็งหลอดใหญ่_ใช้",
                "น้ำแข็งหลอดใหญ่_เหลือ",
                "น้ำแข็งหลอดใหญ่_ค้าง",
                "น้ำแข็งหลอดใหญ่_ละลาย",
                "น้ำแข็งก้อน_ใช้",
                "น้ำแข็งก้อน_เหลือ",
                "น้ำแข็งก้อน_ค้าง",
                "น้ำแข็งก้อน_ละลาย",
                "ยอดขายสุทธิ"
            ])
            worksheet.update([df.columns.tolist()] + df.values.tolist())
            return df
        
        if df.empty:
            return pd.DataFrame()
            
        return df
    except Exception as e:
        handle_error(e, f"การโหลดข้อมูลการส่งน้ำแข็งสำหรับสาย {chain_name}")
        return pd.DataFrame()
        
        # คำนวณยอดขายสุทธิ
        net_sales = 0
        ice_data = load_ice_data()
        for ice_type in ICE_TYPES:
            # หาราคาขายต่อถุง
            price = 0
            row = ice_data[ice_data["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
            if not row.empty:
                price = safe_float(row.iloc[0]["ราคาขายต่อหน่วย"])
            
            # คำนวณยอดขาย
            used = data.get(f"{ice_type}_ใช้", 0)
            returned = data.get(f"{ice_type}_เหลือ", 0)
            melted = data.get(f"{ice_type}_ละลาย", 0)
            debt = data.get(f"{ice_type}_ค้าง", 0)
            
            actual_sold = used - returned - melted
            net_sales += (actual_sold * price) - debt
        
        new_row["ยอดขายสุทธิ"] = net_sales
        
        # เพิ่มข้อมูลใหม่ลง DataFrame
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # บันทึกลง Google Sheets
        worksheet.update([df.columns.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        handle_error(e, f"การบันทึกข้อมูลการส่งน้ำแข็งสำหรับสาย {chain_name}")
        return False

def handle_error(e, context):
    """จัดการและบันทึกข้อผิดพลาด"""
    error_msg = f"เกิดข้อผิดพลาดใน {context}: {str(e)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    st.error(f"⚠️ เกิดข้อผิดพลาดใน {context}: {str(e)}")
    
    if PYPERCLIP_AVAILABLE:
        try:
            pyperclip.copy(error_msg)
            st.info("📋 ข้อผิดพลาดถูกคัดลอกไปยังคลิปบอร์ดแล้ว")
        except:
            st.warning("ไม่สามารถคัดลอกข้อผิดพลาดได้")

def show_dashboard():
    st.title("📊 Dashboard สถิติการขาย")
    
    # แสดงสถานะการเชื่อมต่อ
    conn_status = st.empty()
    try:
        gc = connect_google_sheets()
        if gc:
            conn_status.success("✅ เชื่อมต่อกับ Google Sheets แล้ว")
        else:
            conn_status.error("❌ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
    except Exception as e:
        conn_status.error(f"❌ ข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")
        logger.error(f"Connection error: {e}")
    
    sales_df = load_sales_data()
    df_ice = load_ice_data()

    # ปุ่มรีเฟรชข้อมูล
    if st.button("🔄 โหลดข้อมูลใหม่", key="refresh_data"):
        st.cache_data.clear()
        st.rerun()

    # ตรวจสอบข้อมูลก่อนแสดงผล
    if sales_df.empty:
        st.warning("ไม่มีข้อมูลยอดขาย")
    else:
        # แสดงเมตริกหลัก
        col1, col2, col3 = st.columns(3)
        with col1:
            total_sales = sales_df['ยอดขาย'].sum()
            st.metric("💰 ยอดขายรวม", f"{total_sales:,.2f} บาท")

        with col2:
            total_profit = sales_df['กำไร'].sum() if 'กำไร' in sales_df.columns else 0
            st.metric("🟢 กำไรรวม", f"{total_profit:,.2f} บาท")

        with col3:
            avg_sale = total_sales / len(sales_df) if len(sales_df) > 0 else 0
            st.metric("📊 ยอดขายเฉลี่ยต่อรายการ", f"{avg_sale:,.2f} บาท")

        # แสดงกราฟยอดขายรายวัน
        st.subheader("📈 ยอดขายรายวัน")
        if not sales_df.empty and 'วันที่' in sales_df.columns and 'ยอดขาย' in sales_df.columns:
            try:
                sales_df['วันที่'] = pd.to_datetime(sales_df['วันที่'], errors='coerce')
                sales_df = sales_df.dropna(subset=['วันที่'])
                
                if not sales_df.empty:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    daily_sales = sales_df.groupby(sales_df['วันที่'].dt.date)['ยอดขาย'].sum().reset_index()
                    
                    if not daily_sales.empty:
                        ax.plot(daily_sales['วันที่'], daily_sales['ยอดขาย'], marker='o', color='#007aff')
                        ax.set_title('ยอดขายรายวัน')
                        ax.set_xlabel('วันที่')
                        ax.set_ylabel('ยอดขาย (บาท)')
                        ax.grid(True)
                        st.pyplot(fig)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้างกราฟ: {str(e)}")
        else:
            st.warning("ไม่มีข้อมูลยอดขายเพื่อแสดงกราฟ")
            
        # สินค้าขายดี
        st.subheader("🏆 สินค้าขายดี")
        try:
            if 'รายการ' in sales_df.columns:
                top_products = sales_df['รายการ'].value_counts().head(10)
                st.bar_chart(top_products)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการแสดงสินค้าขายดี: {str(e)}")
            logger.error(f"Error showing top products: {e}")

def increase_quantity(product_name):
    """เพิ่มจำนวนสินค้าใน session_state"""
    if product_name in st.session_state.quantities:
        st.session_state.quantities[product_name] += 1
    else:
        st.session_state.quantities[product_name] = 1

def decrease_quantity(product_name):
    """ลดจำนวนสินค้าใน session_state"""
    if product_name in st.session_state.quantities and st.session_state.quantities[product_name] > 1:
        st.session_state.quantities[product_name] -= 1

def add_money(amount: float):
    """เพิ่มจำนวนเงินรับจากลูกค้า"""
    st.session_state.paid_input += amount
    st.session_state.prev_paid_input = st.session_state.paid_input
    st.session_state.last_paid_click = amount

def show_product_sale_page():
    st.title("🛒 ระบบขายสินค้า")
    
    df = load_product_data()
    if df.empty:
        st.error("ไม่สามารถโหลดข้อมูลสินค้าได้")
        return

    # ส่วนค้นหาสินค้า
    st.subheader("🔍 ค้นหาสินค้า")
    search_term = st.text_input("ค้นหาสินค้า:", key="search_product")
    
    if search_term:
        filtered_products = df[df["ชื่อสินค้า"].str.contains(search_term, case=False)]["ชื่อสินค้า"].tolist()
    else:
        filtered_products = df["ชื่อสินค้า"].tolist()

    # ส่วนเลือกสินค้า
    if not filtered_products:
        st.warning("ไม่พบสินค้าที่ตรงกับคำค้นหา")
    else:
        selected_product = st.selectbox("เลือกสินค้า", filtered_products, key="product_select")

        if selected_product:
            # ตั้งค่าจำนวนเริ่มต้นหากยังไม่มีใน session
            if selected_product not in st.session_state.quantities:
                st.session_state.quantities[selected_product] = 1
            
            qty = st.session_state.quantities[selected_product]
            row = df[df["ชื่อสินค้า"] == selected_product]
            
            if not row.empty:
                stock = safe_int(row["คงเหลือในตู้"].values[0])
                price = safe_float(row["ราคาขาย"].values[0])
                
                # แสดงข้อมูลสินค้า
                st.markdown(f"### {selected_product}")
                st.markdown(f"**ราคา:** {price:,.2f} บาท")

                # ปุ่มปรับจำนวน
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                with col1: 
                    st.button("➖", key=f"dec_{safe_key(selected_product)}", 
                            on_click=decrease_quantity, args=(selected_product,))
                with col2: 
                    st.markdown(f"<div style='text-align:center; font-size:24px'>{qty}</div>", 
                               unsafe_allow_html=True)
                with col3: 
                    st.button("➕", key=f"inc_{safe_key(selected_product)}", 
                            on_click=increase_quantity, args=(selected_product,))
                with col4:
                    # แสดงสถานะสต็อก
                    if stock >= 10:
                        status = "🟢 พอ"
                        color = "#28a745"
                    elif stock >= 5:
                        status = "🟡 ใกล้หมด"
                        color = "#ffc107"
                    elif stock > 0:
                        status = "⚠️ น้อยมาก"
                        color = "#fd7e14"
                    else:
                        status = "🔴 หมด"
                        color = "#dc3545"
                    
                    st.markdown(
                        f"<div style='display: flex; align-items: center;'>"
                        f"<div style='margin-right: 10px;'>"
                        f"<strong>สต็อก:</strong> {stock} ชิ้น"
                        f"</div>"
                        f"<div style='color: {color}; font-weight: bold;'>{status}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
            # ปุ่มเพิ่มลงตะกร้า
            if st.button("➕ เพิ่มลงตะกร้า", type="primary", key="add_to_cart"):
                if qty > 0:
                    if stock >= qty:
                        st.session_state.cart.append((selected_product, qty, price))
                        st.success(f"✅ เพิ่ม {selected_product} จำนวน {qty} ชิ้นลงตะกร้าแล้ว")
                        st.session_state.quantities[selected_product] = 1  # รีเซ็ตจำนวนหลังเพิ่ม
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"⚠️ สินค้ามีไม่พอในสต็อก (เหลือ {stock} ชิ้น)")

    # แสดงรายการในตะกร้า
    st.subheader("📋 รายการขาย")
    total_price = 0.0
    total_profit = 0.0
    
    if not st.session_state.cart:
        st.info("ℹ️ ยังไม่มีสินค้าในตะกร้า")
    else:
        for idx, (item, qty, price) in enumerate(st.session_state.cart):
            row = df[df["ชื่อสินค้า"] == item]
            if not row.empty:
                row = row.iloc[0]
                cost = safe_float(row["ต้นทุน"])
                subtotal = qty * price
                profit = qty * (price - cost)
                total_price += subtotal
                total_profit += profit
                
                col1, col2, col3 = st.columns([6, 1, 1])
                with col1:
                    st.write(f"- {item} x {qty} = {subtotal:,.2f} บาท")
                with col2:
                    st.write(f"({profit:,.2f} บาท)")
                with col3:
                    if st.button("🗑️", key=f"remove_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.success("ลบรายการออกจากตะกร้าแล้ว")
                        time.sleep(0.5)
                        st.rerun()
                        
        if st.button("🗑️ ล้างตะกร้าทั้งหมด", type="secondary", key="clear_cart"):
            clear_cart()
            st.success("ล้างตะกร้าเรียบร้อยแล้ว")
            time.sleep(0.5)
            st.rerun()

        # ระบบรับเงิน
        st.subheader("💰 การชำระเงิน")
        
        # แสดงยอดรวม
        st.markdown(f"""
        <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:15px;'>
            <h4 style='margin-bottom:0;'>ยอดรวม: {total_price:,.2f} บาท</h4>
            <p style='margin-top:5px; color:#28a745;'>กำไรประมาณการ: {total_profit:,.2f} บาท</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ปุ่มเงินด่วน
        st.write("เพิ่มเงินด่วน:")
        col1, col2, col3 = st.columns(3)
        with col1: st.button("+20", on_click=lambda: add_money(20), key="add_20")
        with col2: st.button("+50", on_click=lambda: add_money(50), key="add_50")
        with col3: st.button("+100", on_click=lambda: add_money(100), key="add_100")
        col4, col5 = st.columns(2)
        with col4: st.button("+500", on_click=lambda: add_money(500), key="add_500")
        with col5: st.button("+1000", on_click=lambda: add_money(1000), key="add_1000")
        
        # ฟิลด์รับเงิน
        paid_input = st.number_input(
            "รับเงินจากลูกค้า (บาท)", 
            value=float(st.session_state.get('paid_input', 0.0)), 
            step=1.0,
            min_value=0.0,
            format="%.2f",
            key="paid_input_widget"
        )
        
        # อัปเดต session state เมื่อค่าเปลี่ยน
        if paid_input != st.session_state.get('prev_paid_input', 0.0):
            st.session_state.paid_input = paid_input
            st.session_state.prev_paid_input = paid_input
        
        # แสดงเงินทอนหรือเงินขาด
        if paid_input > 0:
            change = paid_input - total_price
            if change >= 0:
                st.success(f"💰 เงินทอน: {change:,.2f} บาท")
            else:
                st.error(f"💸 เงินไม่พอ (ขาด: {-change:,.2f} บาท)")
        
        # ปุ่มยกเลิกเงินล่าสุด
        if st.session_state.last_paid_click > 0:
            if st.button(f"➖ ยกเลิก {st.session_state.last_paid_click}", key="cancel_last"):
                st.session_state.paid_input -= st.session_state.last_paid_click
                st.session_state.prev_paid_input = st.session_state.paid_input
                st.session_state.last_paid_click = 0
                st.rerun()

        # ปุ่มยืนยันการขาย
        if st.button("✅ ยืนยันการขาย", type="primary", 
                    disabled=not st.session_state.cart or paid_input < total_price,
                    key="confirm_sale"):
            try:
                with st.spinner("กำลังบันทึกการขาย..."):
                    gc = connect_google_sheets()
                    if not gc:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                        return
                    
                    sheet = gc.open_by_key(SHEET_ID)
                    worksheet = sheet.worksheet("ตู้เย็น")
                    summary_ws = sheet.worksheet("ยอดขาย")
                    
                    # อัปเดตสต็อกสินค้า
                    for item, qty, _ in st.session_state.cart:
                        index = df[df["ชื่อสินค้า"] == item].index[0]
                        row = df.loc[index]
                        idx_in_sheet = index + 2  # +2 เพราะ header และ index เริ่มที่ 1
                        
                        # คำนวณยอดใหม่
                        new_out = safe_int(row["ออก"]) + qty
                        new_left = safe_int(row["คงเหลือในตู้"]) - qty
                        
                        # อัปเดตใน Google Sheets
                        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("ออก") + 1, new_out)
                        worksheet.update_cell(idx_in_sheet, df.columns.get_loc("คงเหลือในตู้") + 1, new_left)
                    
                    # บันทึกรายการขาย
                    now = datetime.datetime.now(timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
                    items_sold = ", ".join([f"{i} x {q}" for i, q, _ in st.session_state.cart])
                    
                    summary_ws.append_row([
                        now,
                        items_sold,
                        total_price,
                        total_profit,
                        paid_input,
                        paid_input - total_price,
                        "drink"
                    ])
                    
                    # รีเซ็ตข้อมูลหลังขายสำเร็จ
                    clear_cart()
                    
                    # ล้าง cache เพื่อโหลดข้อมูลใหม่
                    st.cache_data.clear()
                    
                    st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
                    logger.info(f"Sale recorded: {total_price} THB, Profit: {total_profit} THB")
                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการบันทึกการขาย: {str(e)}")
                logger.error(f"Error confirming sale: {e}")

def show_ice_sale_page():
    st.title("🧊 ระบบขายน้ำแข็งเจริญค้า")
    
    df_ice = load_ice_data()
    today_str = datetime.datetime.now(timezone(TIMEZONE)).strftime("%-d/%-m/%Y")

    # เก็บยอดเริ่มต้นของทุกค่าที่จำเป็น
    initial_sales = {}
    initial_income = {}
    initial_profit = {}
    
    for ice_type in ICE_TYPES:
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            initial_sales[ice_type] = safe_float(df_ice.at[idx, "ขายออก"])
            initial_income[ice_type] = safe_float(df_ice.at[idx, "ยอดขายรวม"])
            initial_profit[ice_type] = safe_float(df_ice.at[idx, "กำไรสุทธิ"])
            
    if df_ice.empty:
        st.error("ไม่สามารถโหลดข้อมูลน้ำแข็งได้ กรุณาตรวจสอบการเชื่อมต่อ")
        return

    # ตรวจสอบและรีเซ็ตข้อมูลหากเป็นวันใหม่
    latest_date = df_ice["วันที่"].max() if "วันที่" in df_ice.columns else today_str
    if latest_date != today_str:
        try:
            with st.spinner("กำลังรีเซ็ตข้อมูลสำหรับวันใหม่..."):
                gc = connect_google_sheets()
                if not gc:
                    return
                    
                sheet = gc.open_by_key(SHEET_ID)
                iceflow_sheet = sheet.worksheet("iceflow")
                
                # รีเซ็ตข้อมูลใน DataFrame
                for ice_type in ICE_TYPES:
                    mask = df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)
                    if mask.any():
                        idx = df_ice[mask].index[0]
                        df_ice.at[idx, "วันที่"] = today_str
                        df_ice.at[idx, "รับเข้า"] = 0
                        df_ice.at[idx, "ขายออก"] = 0
                        df_ice.at[idx, "จำนวนละลาย"] = 0
                        df_ice.at[idx, "คงเหลือตอนเย็น"] = 0
                        df_ice.at[idx, "ยอดขายรวม"] = 0
                        df_ice.at[idx, "กำไรสุทธิ"] = 0
                
                # อัปเดต Google Sheets
                iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
                
                st.success("🔄 ระบบรีเซ็ตยอดใหม่สำหรับวันนี้แล้ว")
                logger.info("Reset ice data for new day")
                
                # รีเซ็ต session state และรีเฟรชหน้า
                reset_ice_session_state()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการรีเซ็ตข้อมูล: {str(e)}")
            logger.error(f"Error resetting ice data: {e}")

    # ส่วน UI การขายน้ำแข็ง
    st.markdown("### 📥 โซนเติมสต็อกน้ำแข็ง")
    cols = st.columns(4)
    
    for i, ice_type in enumerate(ICE_TYPES):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            received = safe_float(df_ice.at[idx, "รับเข้า"])  # ใช้ float เพื่อรองรับค่าทศนิยม
            sold = safe_float(df_ice.at[idx, "ขายออก"])
            melted = safe_float(df_ice.at[idx, "จำนวนละลาย"])
            remaining = max(0, received - sold - melted)  # ป้องกันค่าติดลบ
            
            # แสดงผลแบบมีทศนิยมเมื่อจำเป็น
            received_display = f"{received:.1f}" if received % 1 != 0 else f"{int(received)}"
            remaining_display = f"{remaining:.1f}" if remaining % 1 != 0 else f"{int(remaining)}"
            
            with cols[i]:
                st.markdown(f"""
                <div class="ice-box">
                    <div class="ice-header">น้ำแข็ง{ice_type}</div>
                    <div class="ice-metric">
                        <div>📥 ยอดรับเข้า: <strong>{received_display}</strong> ถุง</div>
                        <div class="{'stock-low' if remaining < 5 else 'stock-ok' if remaining < 15 else 'stock-high'}">
                            📦 คงเหลือ: <strong>{remaining_display}</strong> ถุง
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
                    df_ice.at[idx, "รับเข้า"] = received + added_value
                    st.success(f"✅ รวมเป็น {received + added_value} ถุง")

    if st.button("📥 บันทึกยอดเติมน้ำแข็ง", type="primary", key="save_restock_ice"):
        try:
            with st.spinner("กำลังบันทึกข้อมูล..."):
                gc = connect_google_sheets()
                if not gc:
                    st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                    return
                    
                sheet = gc.open_by_key(SHEET_ID)
                iceflow_sheet = sheet.worksheet("iceflow")
                iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
                
                # รีเซ็ตเฉพาะฟอร์มเติมสต็อก
                for ice_type in ICE_TYPES:
                    if f"increase_{ice_type}" in st.session_state:
                        del st.session_state[f"increase_{ice_type}"]
                
                st.cache_data.clear()
                st.success("✅ บันทึกยอดเติมน้ำแข็งแล้ว")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
            logger.error(f"Error saving ice restock: {e}")

    # ส่วนขายออกน้ำแข็ง
    st.markdown("### 💸 โซนขายออกน้ำแข็ง")
    total_income = 0
    total_profit = 0

    cols = st.columns(4)
    for i, ice_type in enumerate(ICE_TYPES):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            # ใช้ initial_sales ที่เก็บไว้ตอนต้น ไม่ต้องเก็บใหม่
            price_per_bag = safe_float(df_ice.at[idx, "ราคาขายต่อหน่วย"])
            cost_per_bag = safe_float(df_ice.at[idx, "ต้นทุนต่อหน่วย"])
            current_sold = safe_float(df_ice.at[idx, "ขายออก"])
            current_profit = safe_float(df_ice.at[idx, "กำไรสุทธิ"])
            
            # แสดงผลแบบมีทศนิยมเมื่อจำเป็น
            current_sold_display = f"{current_sold:.1f}" if current_sold % 1 != 0 else f"{int(current_sold)}"
            
            with cols[i]:
                st.markdown(f"""
                <div class="ice-box">
                    <div class="ice-header">ขายน้ำแข็ง{ice_type}</div>
                    <div class="ice-metric">
                        <div>💰 ราคา: <strong>{price_per_bag:,.2f}</strong> บาท/ถุง</div>
                        <div>📤 ยอดขาย: <strong>{current_sold_display}</strong> ถุง</div>
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
                    stock_decrease = full_bag_sold
                    
                    # ขายแบบแบ่ง
                    if divided_amount > 0:
                        if ice_type == "ก้อน":
                            pieces_sold = divided_amount / 5  # 5 บาทต่อก้อน
                            divided_income = divided_amount
                            # 1 ถุงมี 10 ก้อน, ต้นทุนต่อก้อน = cost_per_bag / 10
                            divided_profit = divided_amount - (pieces_sold * (cost_per_bag / 10))
                            stock_decrease += pieces_sold / 10  # 1 ถุง = 10 ก้อน
                        else:
                            divided_income = divided_amount
                            # คำนวณจำนวนถุงที่ขาย (ทศนิยม)
                            partial_bags = divided_amount / price_per_bag
                            divided_profit = divided_amount - (partial_bags * cost_per_bag)
                            stock_decrease += partial_bags
                        
                        income += divided_income
                        profit += divided_profit
                    
                    # อัปเดตข้อมูลใน DataFrame
                    # แก้ไข: บวกเพิ่มจากค่าปัจจุบัน ไม่ใช่ตั้งค่าใหม่
                    df_ice.at[idx, "ขายออก"] = current_sold + stock_decrease
                    df_ice.at[idx, "คงเหลือตอนเย็น"] = safe_float(df_ice.at[idx, "รับเข้า"]) - df_ice.at[idx, "ขายออก"] - safe_float(df_ice.at[idx, "จำนวนละลาย"])
                    df_ice.at[idx, "ยอดขายรวม"] += income  # บวกเพิ่มจากยอดเดิม
                    df_ice.at[idx, "กำไรสุทธิ"] += profit  # บวกเพิ่มจากยอดเดิม
                    
                    total_income += income
                    total_profit += profit
    
    # ส่วนจัดการน้ำแข็งที่ละลาย
    st.markdown("### 🧊 การจัดการน้ำแข็งที่ละลาย")
    melted_cols = st.columns(4)
    
    for i, ice_type in enumerate(ICE_TYPES):
        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            idx = row.index[0]
            with melted_cols[i]:
                # ลบ session state ที่มีอยู่เพื่อหลีกเลี่ยงข้อผิดพลาด
                melted_key = f"melted_{ice_type}"
                if melted_key in st.session_state:
                    del st.session_state[melted_key]
                    
                melted_qty = st.number_input(
                    f"ละลาย {ice_type}", 
                    min_value=0.0,  # เปลี่ยนเป็นทศนิยม
                    value=safe_float(df_ice.at[idx, "จำนวนละลาย"]),
                    step=0.1,       # อนุญาตให้ป้อนทศนิยม
                    key=melted_key
                )
                df_ice.at[idx, "จำนวนละลาย"] = melted_qty
                df_ice.at[idx, "คงเหลือตอนเย็น"] = safe_float(df_ice.at[idx, "รับเข้า"]) - safe_float(df_ice.at[idx, "ขายออก"]) - melted_qty

    # สรุปยอดขาย (แก้ไขใหม่)
    st.markdown("### 📊 สรุปยอดขาย (วันนี้)")
    
    # คำนวณยอดขายรวมและกำไรสุทธิจากชีท iceflow
    today_str = datetime.datetime.now(timezone(TIMEZONE)).strftime("%-d/%-m/%Y")
    df_ice_today = df_ice[df_ice['วันที่'] == today_str]
    
    total_sales_today = 0.0
    total_profit_today = 0.0
    
    if not df_ice_today.empty:
        total_sales_today = df_ice_today['ยอดขายรวม'].sum()  # คอลัมน์ O (ยอดขายรวม)
        total_profit_today = df_ice_today['กำไรสุทธิ'].sum()  # คอลัมน์ N (กำไรสุทธิ)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 ยอดขายรวม", f"{total_sales_today:,.2f} บาท")
    with col2:
        st.metric("🟢 กำไรสุทธิ", f"{total_profit_today:,.2f} บาท")

   # ส่วนบันทึกการขายน้ำแข็ง
    if st.button("✅ บันทึกการขายน้ำแข็ง", type="primary", key="save_ice_sale"):
        # ประกาศตัวแปรสำหรับตรวจสอบ
        validation_passed = True
        error_messages = []
        
        # ตรวจสอบข้อมูลน้ำแข็งทุกประเภท
        for ice_type in ICE_TYPES:
            row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
            if not row.empty:
                idx = row.index[0]
                received = safe_float(df_ice.at[idx, "รับเข้า"])
                sold = safe_float(df_ice.at[idx, "ขายออก"])
                melted = safe_float(df_ice.at[idx, "จำนวนละลาย"])
                remaining = received - sold - melted
            
                if remaining < 0:
                    validation_passed = False
                    error_messages.append(f"น้ำแข็ง{ice_type}: ยอดคงเหลือติดลบ ({remaining:.2f} ถุง)")
                
                if sold > received:
                    validation_passed = False
                    error_messages.append(f"น้ำแข็ง{ice_type}: ยอดขาย ({sold:.2f} ถุง) เกินยอดรับเข้า ({received:.2f} ถุง)")
                
                if melted > received:
                    validation_passed = False
                    error_messages.append(f"น้ำแข็ง{ice_type}: ยอดละลาย ({melted:.2f} ถุง) เกินยอดรับเข้า ({received:.2f} ถุง)")

        if not validation_passed:
            st.error("⚠️ พบข้อผิดพลาดในการตรวจสอบข้อมูล:")
            for msg in error_messages:
                st.error(msg)
            st.warning("กรุณาตรวจสอบข้อมูลก่อนบันทึกอีกครั้ง")
        else:
            try:
                with st.spinner("กำลังบันทึกการขาย..."):
                    gc = connect_google_sheets()
                    if not gc:
                        st.error("❌ ไม่สามารถเชื่อมต่อ Google Sheet ได้")
                        return
                    
                    sheet = gc.open_by_key(SHEET_ID)
                    iceflow_sheet = sheet.worksheet("iceflow")
                    summary_ws = sheet.worksheet("ยอดขาย")
                    
                    # บันทึกข้อมูลน้ำแข็ง
                    iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
                    
                    # บันทึกรายการขาย
                    for ice_type in ICE_TYPES:
                        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
                        if not row.empty:
                            idx = row.index[0]
                            current_sold = safe_float(df_ice.at[idx, "ขายออก"])
                            
                            # คำนวณยอดที่ขายในรอบนี้
                            sold_in_this_session = max(0, current_sold - initial_sales.get(ice_type, 0))
                            
                            if sold_in_this_session > 0:
                                # คำนวณยอดขายและกำไรเฉพาะในรอบนี้
                                income_in_this_session = df_ice.at[idx, "ยอดขายรวม"] - initial_income.get(ice_type, 0)
                                profit_in_this_session = df_ice.at[idx, "กำไรสุทธิ"] - initial_profit.get(ice_type, 0)
                                
                                summary_ws.append_row([
                                    today_str,
                                    f"น้ำแข็ง{ice_type} (ขาย {sold_in_this_session:.2f} ถุง)",
                                    float(income_in_this_session),
                                    float(profit_in_this_session),
                                    "ice"
                                ])
                    
                    st.cache_data.clear()
                    st.success("✅ บันทึกการขายน้ำแข็งเรียบร้อย")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
                logger.error(f"Error saving ice sale: {e}")

def save_customer_debt(customer_name, chain, amount, note=""):
    """บันทึกข้อมูลการชำระค้างของลูกค้า"""
    try:
        gc = connect_google_sheets()
        if not gc:
            return False
            
        sheet = gc.open_by_key(SHEET_ID)
        try:
            worksheet = sheet.worksheet("ลูกค้าค้างเงิน")
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="ลูกค้าค้างเงิน", rows=100, cols=10)
        
        df = pd.DataFrame(worksheet.get_all_records())
        
        # คำนวณยอดคงค้าง
        current_debt = 0
        if not df.empty:
            customer_history = df[(df["ชื่อลูกค้า"] == customer_name) & (df["สายส่ง"] == chain)]
            if not customer_history.empty:
                current_debt = customer_history.iloc[-1]["คงค้าง"]
        
        new_debt = current_debt - amount
        
        # เพิ่มข้อมูลใหม่
        new_row = {
            "วันที่": datetime.datetime.now(timezone(TIMEZONE)).strftime("%-d/%-m/%Y"),
            "ชื่อลูกค้า": customer_name,
            "สายส่ง": chain,
            "ยอดค้าง": current_debt,
            "ชำระแล้ว": amount,
            "คงค้าง": new_debt,
            "หมายเหตุ": note
        }
        
        # เพิ่มข้อมูลใหม่ลง DataFrame
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # บันทึกลง Google Sheets
        worksheet.update([df.columns.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        handle_error(e, "การบันทึกข้อมูลลูกค้าค้างเงิน")
        return False

def show_delivery_page():
    st.title("🚚 ระบบจัดการการส่งน้ำแข็ง")
    
    # Define delivery chains
    DELIVERY_CHAINS = ["สาย 1", "สาย 2", "สาย 3", "สาย 4", "สาย 5"]
    
    # เลือกสายส่ง
    selected_chain = st.selectbox("เลือกสายส่ง", DELIVERY_CHAINS, key="delivery_chain")
    
    # ดึงข้อมูลราคาน้ำแข็ง
    ice_data = load_ice_data()
    ice_prices = {}
    for ice_type in ICE_TYPES:
        row = ice_data[ice_data["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
        if not row.empty:
            ice_prices[ice_type] = safe_float(row.iloc[0]["ราคาขายต่อหน่วย"])
        else:
            ice_prices[ice_type] = 0
            st.warning(f"ไม่พบราคาน้ำแข็ง{ice_type} ในระบบ")
    
    # สร้างฟอร์มกรอกข้อมูล
    delivery_data = {}
    
    st.subheader("📝 กรอกข้อมูลการส่งน้ำแข็ง")
    st.write(f"สำหรับสาย: **{selected_chain}**")
    
    # สร้างตารางสำหรับน้ำแข็งแต่ละชนิด
    for ice_type in ICE_TYPES:
        st.markdown(f"### น้ำแข็ง{ice_type}")
        cols = st.columns(4)
        with cols[0]:
            delivery_data[f"{ice_type}_ใช้"] = st.number_input(
                f"จำนวนที่ใช้ (ถุง)", 
                min_value=0, 
                step=1, 
                key=f"used_{ice_type}_{selected_chain}"
            )
        with cols[1]:
            delivery_data[f"{ice_type}_เหลือ"] = st.number_input(
                f"เหลือกลับ (ถุง)", 
                min_value=0, 
                step=1, 
                key=f"returned_{ice_type}_{selected_chain}"
            )
        with cols[2]:
            delivery_data[f"{ice_type}_ค้าง"] = st.number_input(
                f"ค้างจ่าย (บาท)", 
                min_value=0.0, 
                step=10.0,
                format="%.2f",
                key=f"debt_{ice_type}_{selected_chain}"
            )
        with cols[3]:
            delivery_data[f"{ice_type}_ละลาย"] = st.number_input(
                f"ละลาย (ถุง)", 
                min_value=0, 
                step=1, 
                key=f"melted_{ice_type}_{selected_chain}"
            )
    
    # ส่วนจัดการลูกค้าค้างเงิน (แก้ไข)
    st.subheader("🧾 การจัดการลูกค้าค้างเงิน")
    
    # โหลดข้อมูลลูกค้าค้างเงิน
    debt_df = load_customer_debt_data()
    
    # ค้นหาลูกค้า
    customer_options = []
    if not debt_df.empty:
        customer_options = debt_df["ชื่อลูกค้า"].unique().tolist()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        customer_name = st.selectbox(
            "ค้นหาลูกค้า",
            options=[""] + customer_options,
            index=0,
            key=f"customer_search_{selected_chain}",
            help="เลือกลูกค้าจากรายการหรือป้อนชื่อใหม่"
        )
    
    with col2:
        new_customer = st.checkbox("ลูกค้าใหม่", key=f"new_customer_{selected_chain}")
    
    if new_customer:
        customer_name = st.text_input("ชื่อลูกค้า", key=f"new_customer_name_{selected_chain}")
    
    # ฟิลด์กรอกข้อมูลการชำระ (แก้ไขใหม่)
    if customer_name:
        # คำนวณยอดค้างปัจจุบัน
        current_debt = 0
        if not debt_df.empty and customer_name in customer_options:
            customer_history = debt_df[debt_df["ชื่อลูกค้า"] == customer_name]
            if not customer_history.empty:
                current_debt = customer_history.iloc[-1]["คงค้าง"]
        
        st.markdown(f"**ยอดค้างปัจจุบัน:** {current_debt:,.2f} บาท")
        
        # ใช้แบบฟอร์มเพื่อจัดการสถานะการรีเซ็ต
        with st.form(key=f"payment_form_{selected_chain}"):
            payment_amount = st.number_input(
                "จำนวนที่ชำระ (บาท)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                value=0.0,  # ค่าเริ่มต้น 0
                key=f"payment_amount_{selected_chain}"
            )
            
            payment_note = st.text_input(
                "หมายเหตุ",
                value="",  # ค่าเริ่มต้นว่าง
                key=f"payment_note_{selected_chain}",
                help="เช่น วันที่ชำระ, วิธีการชำระ"
            )
            
            submitted = st.form_submit_button("💳 บันทึกการชำระ")
            
            if submitted:
                if payment_amount > 0:
                    if save_customer_debt(customer_name, selected_chain, payment_amount, payment_note):
                        st.success(f"✅ บันทึกการชำระ {payment_amount:,.2f} บาทสำหรับ {customer_name} เรียบร้อย")
                        # รีเซ็ตแคชข้อมูลหนี้
                        st.cache_data.clear()
                    else:
                        st.error("❌ ไม่สามารถบันทึกข้อมูลได้ กรุณาลองอีกครั้ง")
                else:
                    st.warning("⚠️ กรุณากรอกจำนวนเงินที่ชำระ")
    
    # คำนวณยอดขายสุทธิ
    net_sales = 0
    for ice_type in ICE_TYPES:
        used = delivery_data.get(f"{ice_type}_ใช้", 0)
        returned = delivery_data.get(f"{ice_type}_เหลือ", 0)
        melted = delivery_data.get(f"{ice_type}_ละลาย", 0)
        debt = delivery_data.get(f"{ice_type}_ค้าง", 0)
        
        actual_sold = used - returned - melted
        net_sales += (actual_sold * ice_prices[ice_type]) - debt
    
    st.subheader("📊 สรุปยอดขาย")
    st.markdown(f"""
    <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:15px;'>
        <h4 style='margin-bottom:5px;'>ยอดขายสุทธิสำหรับสาย {selected_chain}</h4>
        <p style='font-size:24px; color:#007aff; font-weight:bold;'>{net_sales:,.2f} บาท</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ปุ่มบันทึก
    if st.button("💾 บันทึกข้อมูล", type="primary", key=f"save_delivery_{selected_chain}"):
        if save_delivery_data(selected_chain, delivery_data):
            st.success(f"✅ บันทึกข้อมูลการส่งน้ำแข็งสำหรับสาย {selected_chain} เรียบร้อยแล้ว")
            
            # อัปเดตข้อมูลน้ำแข็งหลัก
            try:
                gc = connect_google_sheets()
                if gc:
                    sheet = gc.open_by_key(SHEET_ID)
                    iceflow_sheet = sheet.worksheet("iceflow")
                    df_ice = pd.DataFrame(iceflow_sheet.get_all_records())
                    
                    for ice_type in ICE_TYPES:
                        row = df_ice[df_ice["ชนิดน้ำแข็ง"].str.contains(ice_type, na=False)]
                        if not row.empty:
                            idx = row.index[0]
                            # เพิ่มยอดขายในข้อมูลหลัก
                            used = delivery_data.get(f"{ice_type}_ใช้", 0)
                            returned = delivery_data.get(f"{ice_type}_เหลือ", 0)
                            melted = delivery_data.get(f"{ice_type}_ละลาย", 0)
                            
                            # คำนวณยอดขายใหม่
                            sold_main = safe_float(df_ice.at[idx, "ขายออก"])
                            df_ice.at[idx, "ขายออก"] = sold_main + (used - returned)
                            
                            # เพิ่มน้ำแข็งที่ละลาย
                            melted_main = safe_float(df_ice.at[idx, "จำนวนละลาย"])
                            df_ice.at[idx, "จำนวนละลาย"] = melted_main + melted
                            
                    # อัปเดต Google Sheets
                    iceflow_sheet.update([df_ice.columns.tolist()] + df_ice.values.tolist())
                    st.cache_data.clear()
                    logger.info(f"อัปเดตข้อมูลน้ำแข็งหลักสำหรับสาย {selected_chain} เรียบร้อย")
            except Exception as e:
                st.error(f"⚠️ ไม่สามารถอัปเดตข้อมูลน้ำแข็งหลักได้: {str(e)}")
                logger.error(f"Error updating main ice data: {e}")
            
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ ไม่สามารถบันทึกข้อมูลได้ กรุณาลองอีกครั้ง")
    
    # แสดงข้อมูลย้อนหลัง
    st.subheader("📜 ประวัติการส่ง")
    delivery_history = load_delivery_data(selected_chain)
    if not delivery_history.empty:
        # กรองคอลัมน์ที่สำคัญ
        display_cols = ["วันที่"]
        for ice_type in ICE_TYPES:
            display_cols.extend([
                f"น้ำแข็ง{ice_type}_ใช้",
                f"น้ำแข็ง{ice_type}_เหลือ",
                f"น้ำแข็ง{ice_type}_ค้าง",
                f"น้ำแข็ง{ice_type}_ละลาย"
            ])
        display_cols.append("ยอดขายสุทธิ")
        
        # แสดงตารางข้อมูล
        st.dataframe(
            delivery_history[display_cols].rename(columns=lambda x: x.replace("น้ำแข็ง", "")),
            height=300,
            use_container_width=True
        )
        
        # แสดงกราฟยอดขาย
        st.subheader("📈 กราฟยอดขายย้อนหลัง")
        if "ยอดขายสุทธิ" in delivery_history.columns and "วันที่" in delivery_history.columns:
            try:
                # คัดลอกข้อมูลเพื่อป้องกันการแก้ไขข้อมูลต้นฉบับ
                plot_df = delivery_history.copy()
                
                # แปลงคอลัมน์วันที่
                plot_df["วันที่"] = pd.to_datetime(plot_df["วันที่"], errors='coerce', dayfirst=True)
                plot_df = plot_df.dropna(subset=["วันที่"])
                plot_df = plot_df.sort_values("วันที่")
                
                # สร้างกราฟ
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(plot_df["วันที่"], plot_df["ยอดขายสุทธิ"], marker='o', color='#007aff')
                ax.set_title(f'ยอดขายสุทธิสำหรับสาย {selected_chain}')
                ax.set_xlabel('วันที่')
                ax.set_ylabel('ยอดขาย (บาท)')
                ax.grid(True)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้างกราฟ: {str(e)}")
    else:
        st.info("ℹ️ ยังไม่มีข้อมูลประวัติการส่งสำหรับสายนี้")
def main():
    try:
        # ตั้งค่าพื้นฐาน
        set_custom_css()
        initialize_session_state()
            
        # แสดงสถานะการเชื่อมต่อ
        conn_status = st.empty()
        try:
            gc = connect_google_sheets()
            if gc:
                conn_status.success("✅ เชื่อมต่อกับ Google Sheets แล้ว")
            else:
                conn_status.error("❌ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
        except Exception as e:
            conn_status.error(f"❌ ข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")
            logger.error(f"Connection error in main: {e}")

        # แสดงเมนูหลัก
        st.markdown("### 🚀 เมนูหลัก")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("🏪 ขายสินค้า", use_container_width=True):
                st.session_state.page = "ขายสินค้า"
                st.rerun()
        with col2:
            if st.button("🧊 ขายน้ำแข็ง", use_container_width=True):
                st.session_state.page = "ขายน้ำแข็ง"
                st.rerun()
        with col3:
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
        with col4:
            if st.button("🚚 ส่งน้ำแข็ง", use_container_width=True):
                st.session_state.page = "ส่งน้ำแข็ง"
                st.rerun()

        # แสดงหน้าเว็บตามสถานะปัจจุบัน
        if st.session_state.page == "Dashboard":
            show_dashboard()
        elif st.session_state.page == "ขายสินค้า":
            show_product_sale_page()
        elif st.session_state.page == "ขายน้ำแข็ง":
            show_ice_sale_page()
        elif st.session_state.page == "ส่งน้ำแข็ง":
            show_delivery_page()
            
    except Exception as page_error:
        logger.error(f"Page error in {st.session_state.page}: {str(page_error)}", exc_info=True)
        st.error(f"⚠️ เกิดข้อผิดพลาดในการโหลดหน้า {st.session_state.page}")
        with st.expander("รายละเอียดข้อผิดพลาด"):
            st.error(str(page_error))
            st.text(traceback.format_exc())
        
        # แสดงข้อความผิดพลาดแบบอ่านง่ายให้ผู้ใช้
        st.error("""
        ⚠️ เกิดข้อผิดพลาดร้ายแรงในระบบ
        กรุณาทำตามขั้นตอนต่อไปนี้:
        1. รีเฟรชหน้าเว็บ
        2. ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต
        3. ติดต่อผู้ดูแลระบบ
        """)
        
        # แสดงรายละเอียดข้อผิดพลาดแบบเต็ม (สำหรับ debugging)
        error_msg = f"""
        ข้อผิดพลาดหลัก:
        {str(page_error)}
        
        Traceback:
        {traceback.format_exc()}
        """
        with st.expander("รายละเอียดข้อผิดพลาด (สำหรับผู้ดูแลระบบ)"):
            st.code(error_msg, language='text')
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 รีเฟรชหน้า", help="ลองรีเฟรชหน้าเว็บหากเกิดข้อผิดพลาด"):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if PYPERCLIP_AVAILABLE and st.button("📋 คัดลอกข้อผิดพลาด"):
                pyperclip.copy(error_msg)
                st.success("คัดลอกข้อผิดพลาดไปยังคลิปบอร์ดแล้ว")

        st.markdown("""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <h4>❓ วิธีแก้ไขปัญหาเบื้องต้น</h4>
            <ol>
                <li>ลองรีเฟรชหน้าเว็บ</li>
                <li>ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต</li>
                <li>ติดต่อผู้ดูแลระบบ พร้อมส่งรายละเอียดข้อผิดพลาด</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
            
if __name__ == "__main__":
    try:
        # ตั้งค่าเริ่มต้น
        set_custom_css()
        initialize_session_state()
        
        # เริ่มการทำงานหลัก
        main()
        
    except Exception as e:
        # จัดการข้อผิดพลาดในการเริ่มต้นแอป
        logger.critical(f"แอปเริ่มต้นไม่สำเร็จ: {e}\n{traceback.format_exc()}")
        
        # แสดงข้อความผิดพลาดแบบอ่านง่าย
        st.error("""
        ⚠️ เกิดข้อผิดพลาดร้ายแรงในการเริ่มต้นแอปพลิเคชัน
        กรุณาทำตามขั้นตอนต่อไปนี้:
        1. รีเฟรชหน้าเว็บ
        2. ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต
        3. ติดต่อผู้ดูแลระบบ
        """)
        
        # คัดลอกข้อผิดพลาด (ถ้าใช้งานได้)
        if PYPERCLIP_AVAILABLE:
            try:
                error_details = f"""ข้อผิดพลาด:
{e}

Traceback:
{traceback.format_exc()}"""
                pyperclip.copy(error_details)
                st.info("📋 ข้อผิดพลาดถูกคัดลอกไปยังคลิปบอร์ดแล้ว")
            except:
                st.warning("ไม่สามารถคัดลอกข้อผิดพลาดได้")
