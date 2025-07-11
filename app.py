import streamlit as st

# ตั้งค่า page layout
st.set_page_config(page_title="เจริญค้า", layout="wide")

# กำหนดสไตล์ CSS เพื่อเลียนแบบเว็บ Apple
apple_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main {
    background-color: #ffffff;
    padding: 40px;
}

h1, h2, h3 {
    color: #1d1d1f;
    font-weight: 600;
}

.stButton>button {
    background-color: #0071e3;
    color: white;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 500;
    border: none;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.stButton>button:hover {
    background-color: #005bb5;
}

.stTextInput>div>div>input {
    border-radius: 8px;
    padding: 12px;
    border: 1px solid #d2d2d7;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

</style>
"""

st.markdown(apple_style, unsafe_allow_html=True)

# หัวข้อแอป
st.title("🍎 ร้านเจริญค้า")

# ตัวอย่าง UI สำหรับการค้นหาสินค้า
with st.container():
    st.subheader("ค้นหาสินค้า")
    search_term = st.text_input("", placeholder="ค้นหาสินค้า...")
    if st.button("ค้นหา"):
        st.success(f"คุณกำลังค้นหา: {search_term}")

# ตัวอย่าง UI ปุ่มคำสั่งต่างๆ
with st.container():
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("ขายสินค้า"):
            st.info("ฟังก์ชันขายสินค้า")

    with col2:
        if st.button("เติมสต๊อก"):
            st.info("ฟังก์ชันเติมสต๊อก")

    with col3:
        if st.button("บันทึกยอดขาย"):
            st.info("ฟังก์ชันบันทึกยอดขาย")
