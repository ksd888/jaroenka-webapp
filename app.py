
import streamlit as st
import pandas as pd

# Mock product data
data = {
    "ชื่อสินค้า": ["คาราบาว", "กระทิงแดงเล็ก", "เนสกาแฟ"],
    "ราคาขาย": [15, 10, 12],
    "คงเหลือรวม": [50, 30, 40],
    "คงเหลือที่ตู้": [10, 5, 7],
}
df = pd.DataFrame(data)

st.set_page_config(page_title="เจริญค้า", layout="centered")
st.title("🧊 ระบบขายสินค้าตู้เย็น - เจริญค้า")

st.subheader("🔍 เลือกสินค้าหลายรายการ")

selected_items = {}
for i in range(5):
    col1, col2 = st.columns([3, 1])
    with col1:
        product = st.selectbox(f"สินค้า {i+1}", options=["-"] + df["ชื่อสินค้า"].tolist(), key=f"item_{i}")
    with col2:
        if product and product != "-":
            qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{i}")
            selected_items[product] = qty

if selected_items:
    st.markdown("---")
    st.subheader("📊 สรุปยอดขาย")
    total = 0
    for product, qty in selected_items.items():
        price = df[df["ชื่อสินค้า"] == product]["ราคาขาย"].values[0]
        subtotal = price * qty
        total += subtotal
        st.write(f"- {product} x {qty} = {subtotal} บาท")
    st.write(f"**💰 รวมทั้งหมด: {total} บาท**")

    paid = st.number_input("💵 เงินที่ลูกค้าชำระ", min_value=0, value=total)
    if paid >= total:
        st.success(f"เงินทอน: {paid - total} บาท")
    else:
        st.error("เงินไม่พอจ่าย")

    if st.button("✅ ยืนยันการขาย"):
        st.success("บันทึกการขาย (จำลอง)")
