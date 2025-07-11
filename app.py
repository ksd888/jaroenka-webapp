import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Debug เจริญค้า", layout="wide")

st.title("🛠️ Debug Mode: Google Sheet เชื่อมต่อ")

# Theme แบบเรียบ
st.markdown("""
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
}
</style>
""", unsafe_allow_html=True)

# Step 1: ลองเชื่อมต่อกับ Google Sheet
st.header("🔐 เชื่อมต่อ Google Sheet")
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
    gc = gspread.authorize(credentials)
    st.success("✅ เชื่อมต่อ GSpread สำเร็จ")
except Exception as e:
    st.error("❌ เชื่อมต่อ GSpread ไม่สำเร็จ")
    st.exception(e)
    st.stop()

# Step 2: ลองเปิดไฟล์ Google Sheet
try:
    sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
    st.success("✅ เปิด Spreadsheet สำเร็จ")
except Exception as e:
    st.error("❌ เปิด Spreadsheet ไม่ได้")
    st.exception(e)
    st.stop()

# Step 3: ลองเลือก worksheet
try:
    worksheet = sheet.worksheet("ตู้เย็น")
    st.success("✅ เปิดชีท 'ตู้เย็น' สำเร็จ")
except Exception as e:
    st.error("❌ ไม่พบชีทชื่อ 'ตู้เย็น'")
    st.exception(e)
    st.stop()

# Step 4: ลองโหลดข้อมูล
try:
    data = worksheet.get_all_records()
    st.success(f"✅ โหลดข้อมูลสำเร็จ: พบ {len(data)} แถว")
    df = pd.DataFrame(data)
    st.dataframe(df)
except Exception as e:
    st.error("❌ โหลดข้อมูลจากชีทไม่สำเร็จ")
    st.exception(e)
    st.stop()
