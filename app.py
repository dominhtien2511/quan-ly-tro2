import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import urllib.parse

# ==========================================
# 0. CÀI ĐẶT TRANG & HỆ THỐNG ĐĂNG NHẬP
# ==========================================
st.set_page_config(page_title="Hệ Sinh Thái Quản Lý Trọ (Cloud)", layout="wide")

# --- DANH SÁCH TÀI KHOẢN ---
USERS = {
    "admin": {"password": "123", "role": "Admin", "name": "Chủ Trọ (Bạn)"},
    "doitac": {"password": "456", "role": "Viewer", "name": "Cổ Đông (Đối tác)"}
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 HỆ THỐNG QUẢN LÝ TRỌ</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Tài khoản")
            p = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập"):
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state.update({"logged_in": True, "role": USERS[u]["role"], "name": USERS[u]["name"]})
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

IS_ADMIN = (st.session_state['role'] == "Admin")

# ==========================================
# 1. CẤU HÌNH KẾT NỐI GOOGLE SHEETS
# ==========================================
# THAY LINK DƯỚI ĐÂY BẰNG LINK GOOGLE SHEET CỦA BẠN (Đã bật Anyone with link can view)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1lvAwM19oi6cTuB0LbBpS3H_m1bSqfQpfwexMrOU1tqQ/edit#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    # ttl=0 để luôn lấy dữ liệu mới nhất, không dùng cache
    return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)

def save_data(df, sheet_name):
    conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=df)
    st.toast(f"✅ Đã cập nhật bảng {sheet_name} thành công!")

# --- THÔNG SỐ CỐ ĐỊNH ---
GIA_DIEN, GIA_NUOC = 4000, 30000

def tinh_thang_truoc(thang_nam):
    t, n = map(int, thang_nam.split('/'))
    return f"12/{n-1}" if t == 1 else f"{str(t-1).zfill(2)}/{n}"

def tao_link_vietqr(ngan_hang, stk, so_tien, noi_dung):
    noi_dung_encoded = urllib.parse.quote(noi_dung)
    return f"https://img.vietqr.io/image/{ngan_hang}-{stk}-compact2.png?amount={so_tien}&addInfo={noi_dung_encoded}"

# ==========================================
# 2. SIDEBAR & MENU
# ==========================================
st.sidebar.success(f"👤: {st.session_state['name']} ({st.session_state['role']})")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()

menu = st.sidebar.radio("Chức năng:", [
    "1. Quản lý Phòng & Tính tiền", 
    "2. Kiểm soát Thành viên", 
    "3. 🛠️ Quản lý Bảo Trì",
    "4. Báo Cáo Tài Chính"
])

# Chọn thời gian làm việc
c_month = str(datetime.now().month).zfill(2)
c_year = str(datetime.now().year)
sel_m = st.sidebar.selectbox("Tháng", [str(m).zfill(2) for m in range(1, 13)], index=int(c_month)-1)
sel_y = st.sidebar.selectbox("Năm", [str(y) for y in range(2024, 2030)], index=0)
current_period = f"{sel_m}/{sel_y}"

if IS_ADMIN:
    st.sidebar.markdown("---")
    st.session_state['bank_id'] = st.sidebar.text_input("Mã NH (MB, VCB...)", value="MB")
    st.session_state['bank_stk'] = st.sidebar.text_input("Số tài khoản", value="")

# ==========================================
# MENU 1: QUẢN LÝ PHÒNG & TÍNH TIỀN
# ==========================================
if menu == "1. Quản lý Phòng & Tính tiền":
    st.title(f"🏠 Dãy Trọ - Kỳ {current_period}")
    df_all_phong = load_data("phong_tro")
    df_thang_nay = df_all_phong[df_all_phong["thang_nam"] == current_period]

    if df_thang_nay.empty and IS_ADMIN:
        st.warning("Chưa có dữ liệu kỳ này.")
        if st.button("✨ Sao chép từ tháng trước"):
            prev_p = tinh_thang_truoc(current_period)
            df_prev = df_all_phong[df_all_phong["thang_nam"] == prev_p]
            if not df_prev.empty:
                new_data = df_prev.copy()
                new_data["thang_nam"] = current_period
                new_data["dien_cu"] = new_data["dien_moi"]
                new_data["nuoc_cu"] = new_data["nuoc_moi"]
                new_data["dien_moi"], new_data["nuoc_moi"] = 0, 0
                new_data["thanh_toan"] = "Chưa"
                df_updated = pd.concat([df_all_phong, new_data], ignore_index=True)
                save_data(df_updated, "phong_tro")
                st.rerun()

    if not df_thang_nay.empty:
        st.dataframe(df_thang_nay.drop(columns=["thang_nam"]), use_container_width=True, hide_index=True)
        
        if IS_ADMIN:
            st.markdown("---")
            sel_room = st.selectbox("Chọn phòng thao tác:", df_thang_nay["phong"].tolist())
            row_idx = df_all_phong[(df_all_phong["phong"] == sel_room) & (df_all_phong["thang_nam"] == current_period)].index[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                with st.form("edit_room"):
                    st.write(f"**Chốt số P.{sel_room}**")
                    new_d = st.number_input("Điện mới", value=int(df_all_phong.at[row_idx, "dien_moi"]))
                    new_n = st.number_input("Nước mới", value=int(df_all_phong.at[row_idx, "nuoc_moi"]))
                    status = st.selectbox("Thanh toán", ["Chưa", "Đã thanh toán"], index=0 if df_all_phong.at[row_idx, "thanh_toan"] == "Chưa" else 1)
                    if st.form_submit_button("💾 Lưu dữ liệu"):
                        df_all_phong.at[row_idx, "dien_moi"] = new_d
                        df_all_phong.at[row_idx, "nuoc_moi"] = new_n
                        df_all_phong.at[row_idx, "thanh_toan"] = status
                        save_data(df_all_phong, "phong_tro")
                        st.rerun()
            with col_b:
                st.write("**Xuất hóa đơn QR**")
                r = df_all_phong.loc[row_idx]
                s_d, s_n = r['dien_moi'] - r['dien_cu'], r['nuoc_moi'] - r['nuoc_cu']
                tong = int(r['gia']) + (max(0,s_d)*GIA_DIEN) + (max(0,s_n)*GIA_NUOC) + 100000
                st.code(f"P.{sel_room}: {tong:,} VNĐ")
                if st.session_state.get('bank_stk'):
                    qr = tao_link_vietqr(st.session_state['bank_id'], st.session_state['bank_stk'], tong, f"P{sel_room} TT {current_period.replace('/','')}")
                    st.image(qr, width=200)

# ==========================================
# MENU 2: THÀNH VIÊN
# ==========================================
elif menu == "2. Kiểm soát Thành viên":
    st.title("👥 Quản Lý Thành Viên")
    df_tv = load_data("thanh_vien")
    st.dataframe(df_tv, use_container_width=True, hide_index=True)
    
    if IS_ADMIN:
        with st.expander("➕ Thêm thành viên mới"):
            with st.form("add_tv"):
                p = st.text_input("Phòng")
                t = st.text_input("Họ tên")
                v = st.selectbox("Vai trò", ["Chủ HĐ", "Ở ghép"])
                c = st.text_input("CCCD")
                if st.form_submit_button("Lưu"):
                    new_row = pd.DataFrame([{"phong":p, "ten":t, "vai_tro":v, "cccd":c, "sdt":"", "que_quan":""}])
                    df_updated = pd.concat([df_tv, new_row], ignore_index=True)
                    save_data(df_updated, "thanh_vien")
                    st.rerun()

# ==========================================
# MENU 3: BẢO TRÌ
# ==========================================
elif menu == "3. 🛠️ Quản lý Bảo Trì":
    st.title("🛠️ Sự Cố Sửa Chữa")
    df_bt = load_data("bao_tri")
    st.dataframe(df_bt, use_container_width=True, hide_index=True)
    
    if IS_ADMIN:
        with st.form("add_bt"):
            p = st.text_input("Phòng bị hỏng")
            v = st.text_input("Vấn đề")
            if st.form_submit_button("Ghi nhận"):
                new_row = pd.DataFrame([{"phong":p, "van_de":v, "ngay_bao":datetime.now().strftime("%d/%m/%Y"), "trang_thai":"🔴 Chưa sửa", "chi_phi":0, "da_hach_toan":"Chưa"}])
                df_updated = pd.concat([df_bt, new_row], ignore_index=True)
                save_data(df_updated, "bao_tri")
                st.rerun()

# ==========================================
# MENU 4: BÁO CÁO TÀI CHÍNH
# ==========================================
elif menu == "4. Báo Cáo Tài Chính":
    st.title(f"📊 Báo Cáo Kỳ {current_period}")
    df_p = load_data("phong_tro")
    df_c = load_data("chi_phi")
    
    # Tính toán
    thang_p = df_p[df_p["thang_nam"] == current_period]
    thang_c = df_c[df_c["thang_nam"] == current_period]
    
    thu = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + 100000) for _, r in thang_p[thang_p['thanh_toan'] == 'Đã thanh toán'].iterrows()])
    chi = thang_c["so_tien"].sum() if not thang_c.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng thu thực tế", f"{thu:,.0f} đ")
    c2.metric("Tổng chi phí", f"{chi:,.0f} đ")
    c3.metric("Lợi nhuận", f"{(thu-chi):,.0f} đ")
    
    st.markdown("---")
    st.subheader("Chi tiết chi phí")
    st.dataframe(thang_c, use_container_width=True)
    
    if IS_ADMIN:
        with st.expander("➕ Thêm khoản chi"):
            with st.form("add_chi"):
                l = st.selectbox("Loại", ["Điện", "Nước", "Sửa chữa", "Khác"])
                m = st.text_input("Hạng mục")
                s = st.number_input("Số tiền", step=10000)
                if st.form_submit_button("Lưu chi phí"):
                    new_row = pd.DataFrame([{"thang_nam":current_period, "loai":l, "hang_muc":m, "so_tien":int(s), "ngay_nhap":datetime.now().strftime("%d/%m/%Y")}])
                    df_updated = pd.concat([df_c, new_row], ignore_index=True)
                    save_data(df_updated, "chi_phi")
                    st.rerun()
