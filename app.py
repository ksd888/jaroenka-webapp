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

        # แสดงหน้าเว็บตามสถานะปัจจุบัน
        if st.session_state.page == "Dashboard":
            show_dashboard()
        elif st.session_state.page == "ขายสินค้า":
            show_product_sale_page()
        elif st.session_state.page == "ขายน้ำแข็ง":
            show_ice_sale_page()
            
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
