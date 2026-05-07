import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import base64

# ==========================================
# 0. CÀI ĐẶT TRANG & HỆ THỐNG ĐĂNG NHẬP
# ==========================================
st.set_page_config(page_title="Hệ Sinh Thái Quản Lý Trọ", layout="wide", initial_sidebar_state="expanded")

# --- DANH SÁCH TÀI KHOẢN ---
USERS = {
    "admin": {"password": "123", "role": "Admin", "name": "Chủ Trọ (Bạn)"},
    "doitac": {"password": "456", "role": "Viewer", "name": "Cổ Đông (Đối tác)"}
}

def convert_image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            return f"data:image/png;base64,{base64.b64encode(uploaded_file.read()).decode()}"
        except Exception as e:
            st.error(f"Lỗi xử lý ảnh: {e}")
            return None
    return None

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['name'] = None

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 HỆ THỐNG QUẢN LÝ TRỌ</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.write("Vui lòng đăng nhập để tiếp tục")
            username = st.text_input("Tài khoản")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập")
            if submit:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = USERS[username]["role"]
                    st.session_state['name'] = USERS[username]["name"]
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop() 

IS_ADMIN = (st.session_state['role'] == "Admin")

# ==========================================
# 1. CẤU HÌNH & DATABASE (V15)
# ==========================================
DANH_SACH_MAC_DINH = ["101", "102", "103", "104", "105", "106", "201", "202", "203", "204", "205", "301", "302", "303", "304", "305", "401", "402"]
GIA_DIEN = 4000
GIA_NUOC = 30000

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('dulieu_tro_v15.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS phong_tro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, thang_nam TEXT, phong TEXT, khach_thue TEXT, ngay_vao TEXT, han_hd TEXT,
        gia INTEGER, tien_coc INTEGER DEFAULT 0, dien_cu INTEGER, nuoc_cu INTEGER, dien_moi INTEGER DEFAULT 0, nuoc_moi INTEGER DEFAULT 0,
        trang_thai TEXT, thanh_toan TEXT DEFAULT 'Chưa',
        khach_thue_ngay_sinh TEXT, khach_thue_cccd TEXT, khach_thue_que_quan TEXT, khach_thue_img_truoc TEXT, khach_thue_img_sau TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS thanh_vien (
        id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, ten TEXT, ngay_sinh TEXT, cccd TEXT, sdt TEXT, que_quan TEXT, img_truoc TEXT, img_sau TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chi_phi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, thang_nam TEXT, loai TEXT, hang_muc TEXT, so_tien INTEGER, ngay_nhap TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bao_tri (
        id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, van_de TEXT, ngay_bao TEXT, trang_thai TEXT DEFAULT '🔴 Chưa sửa', chi_phi INTEGER DEFAULT 0, da_hach_toan TEXT DEFAULT 'Chưa'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cau_hinh (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    return conn, c

conn, c = get_db_connection()

def save_config(key, value):
    c.execute("INSERT OR REPLACE INTO cau_hinh (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

def load_config(key, default=""):
    c.execute("SELECT value FROM cau_hinh WHERE key = ?", (key,))
    res = c.fetchone()
    return res[0] if res else default

# Hàm bổ trợ sửa lỗi ngày tháng None (Dùng chung cho toàn bộ app)
def format_date_input(date_str):
    if pd.notnull(date_str) and str(date_str).strip() not in ["None", "nan", ""]:
        try:
            return datetime.strptime(str(date_str), "%d/%m/%Y").date()
        except:
            return None
    return None

def load_phong(thang_nam): return pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_nam}'", conn)
def load_thanh_vien(phong): return pd.read_sql_query(f"SELECT * FROM thanh_vien WHERE phong = '{phong}'", conn)
def load_chi_phi(thang_nam): return pd.read_sql_query(f"SELECT * FROM chi_phi WHERE thang_nam = '{thang_nam}'", conn)
def load_bao_tri(): return pd.read_sql_query("SELECT * FROM bao_tri ORDER BY id DESC", conn)

def tinh_thang_truoc(thang_nam_hien_tai):
    t, n = map(int, thang_nam_hien_tai.split('/'))
    return f"12/{n-1}" if t == 1 else f"{str(t-1).zfill(2)}/{n}"

def tao_link_vietqr(ngan_hang, stk, so_tien, noi_dung):
    noi_dung_encoded = urllib.parse.quote(noi_dung)
    return f"https://img.vietqr.io/image/{ngan_hang}-{stk}-compact2.png?amount={so_tien}&addInfo={noi_dung_encoded}"

# ==========================================
# 2. MENU ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
# ==========================================
st.sidebar.title("🏢 MENU QUẢN LÝ")
st.sidebar.success(f"👤 Xin chào: **{st.session_state['name']}**\n\n🔑 Quyền: **{st.session_state['role']}**")

if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.markdown("---")

menu = st.sidebar.radio("Chọn chức năng:", [
    "1. Quản lý Phòng & Tính tiền", 
    "2. Kiểm soát Thành viên", 
    "3. 🛠️ Quản lý Bảo Trì",
    "4. Báo Cáo Tài Chính Tháng",
    "5. Báo Cáo Tài Chính Năm"
])

db_bank_id = load_config("bank_id", "MB")
db_bank_stk = load_config("bank_stk", "")
db_bank_user = load_config("bank_user", "")

if IS_ADMIN:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🏦 Cài đặt Nhận Tiền (Chỉ Admin)**")
    new_bank_id = st.sidebar.text_input("Mã Ngân Hàng", value=db_bank_id)
    new_bank_stk = st.sidebar.text_input("Số Tài Khoản", value=db_bank_stk)
    new_bank_user = st.sidebar.text_input("Tên Chủ Tài Khoản", value=db_bank_user)
    if st.sidebar.button("💾 Lưu cấu hình ngân hàng"):
        save_config("bank_id", new_bank_id)
        save_config("bank_stk", new_bank_stk)
        save_config("bank_user", new_bank_user)
        st.sidebar.success("Đã lưu vĩnh viễn!")
        st.rerun()

current_year, current_month = datetime.now().year, str(datetime.now().month).zfill(2)
danh_sach_nam = [str(y) for y in range(2024, current_year + 6)]
danh_sach_thang_don = [str(m).zfill(2) for m in range(1, 13)]

def hien_thi_header_chot_ky(tieu_de):
    col_title, col_chon_thang, col_chon_nam = st.columns([2.5, 0.5, 0.5])
    with col_title: st.title(tieu_de)
    with col_chon_thang:
        st.markdown("<br>", unsafe_allow_html=True)
        thang_chon = st.selectbox("Tháng:", danh_sach_thang_don, index=danh_sach_thang_don.index(current_month))
    with col_chon_nam:
        st.markdown("<br>", unsafe_allow_html=True)
        nam_chon = st.selectbox("Năm:", danh_sach_nam, index=danh_sach_nam.index(str(current_year)))
    return f"{thang_chon}/{nam_chon}"

# =====================================================================
# MENU 1: QUẢN LÝ PHÒNG & TÍNH TIỀN
# =====================================================================
if menu == "1. Quản lý Phòng & Tính tiền":
    selected_month = hien_thi_header_chot_ky("🏠 Quản Lý Dãy Trọ")
    df_thang_nay = load_phong(selected_month)
    
    if df_thang_nay.empty and IS_ADMIN:
        st.warning(f"Dữ liệu kỳ {selected_month} đang trống!")
        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("🆕 Khởi tạo 18 phòng mặc định"):
                for p in DANH_SACH_MAC_DINH:
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, dien_moi, nuoc_moi, trang_thai, thanh_toan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (selected_month, p, "", "", "", 2500000, 0, 0, 0, 0, 0, "Trống", "Chưa"))
                conn.commit(); st.rerun()
        with c_b:
            ky_truoc = tinh_thang_truoc(selected_month)
            if st.button(f"✨ Sao chép dữ liệu từ kỳ trước ({ky_truoc})"):
                df_truoc = load_phong(ky_truoc)
                for _, r in df_truoc.iterrows():
                    d_c = r['dien_moi'] if r['dien_moi'] > r['dien_cu'] else r['dien_cu']
                    n_c = r['nuoc_moi'] if r['nuoc_moi'] > r['nuoc_cu'] else r['nuoc_cu']
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, dien_moi, nuoc_moi, trang_thai, thanh_toan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (selected_month, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], d_c, n_c, 0, 0, r['trang_thai'], "Chưa"))
                conn.commit(); st.rerun()

    if not df_thang_nay.empty:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng phòng", len(df_thang_nay))
        c2.metric("Đã thuê", len(df_thang_nay[df_thang_nay["trang_thai"] == "Đã thuê"]))
        so_thu = len(df_thang_nay[df_thang_nay["thanh_toan"] == "Đã thanh toán"])
        c3.metric("Đã thu", f"{so_thu} phòng")
        c4.metric("Chưa thu", f"{len(df_thang_nay[df_thang_nay['trang_thai'] == 'Đã thuê']) - so_thu} phòng")

        # Bảng chỉnh sửa trực tiếp
        df_display = df_thang_nay.sort_values(by='phong').copy()
        if IS_ADMIN:
            st.info("💡 Bạn có thể sửa nhanh trực tiếp trên bảng và nhấn nút 'Lưu Thay Đổi Bảng' bên dưới.")
            edited_df = st.data_editor(
                df_display.rename(columns={
                    "phong": "Phòng", "khach_thue": "Khách thuê", "ngay_vao": "Ngày Vào", "han_hd": "Hạn HĐ", "gia": "Giá thuê", "tien_coc": "Tiền Cọc",
                    "dien_cu": "Chốt Đầu(Điện)", "nuoc_cu": "Chốt Đầu(Nước)", "trang_thai": "Trạng thái", "thanh_toan": "Thanh Toán"
                }).drop(columns=['id', 'thang_nam', 'dien_moi', 'nuoc_moi', 'khach_thue_ngay_sinh', 'khach_thue_cccd', 'khach_thue_que_quan', 'khach_thue_img_truoc', 'khach_thue_img_sau'], errors='ignore'),
                column_config={
                    "Trạng thái": st.column_config.SelectboxColumn(options=["Trống", "Đã thuê"]),
                    "Thanh Toán": st.column_config.SelectboxColumn(options=["Chưa", "Đã thanh toán"]),
                },
                use_container_width=True, height=(len(df_display)*35)+40, hide_index=True
            )
            
            if st.button("💾 Lưu Thay Đổi Bảng", type="primary"):
                for idx, row in edited_df.iterrows():
                    orig_id = df_display.iloc[idx]['id']
                    def to_int(val): return int(val) if pd.notnull(val) else 0
                    c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, dien_cu=?, nuoc_cu=?, trang_thai=?, thanh_toan=? WHERE id=?''', 
                              (str(row['Khách thuê']), str(row['Ngày Vào']), str(row['Hạn HĐ']), to_int(row['Giá thuê']), to_int(row['Tiền Cọc']), to_int(row['Chốt Đầu(Điện)']), to_int(row['Chốt Đầu(Nước)']), str(row['Trạng thái']), str(row['Thanh Toán']), int(orig_id)))
                conn.commit(); st.success("Đã cập nhật bảng!"); st.rerun()
        else:
            st.dataframe(df_display.drop(columns=['id', 'thang_nam', 'dien_moi', 'nuoc_moi', 'khach_thue_ngay_sinh', 'khach_thue_cccd', 'khach_thue_que_quan', 'khach_thue_img_truoc', 'khach_thue_img_sau'], errors='ignore'), use_container_width=True, hide_index=True)

        st.markdown("---")
        # Giao diện 2 cột như ảnh yêu cầu
        selected_room = st.selectbox("👉 Chọn phòng thao tác:", ["-- Chọn phòng --"] + df_thang_nay["phong"].tolist())
        if selected_room != "-- Chọn phòng --":
            r_data = df_thang_nay[df_thang_nay["phong"] == selected_room].iloc[0]
            col_L, col_R = st.columns(2)
            with col_L:
                st.markdown("### 🖊️ Cập nhật Thông tin")
                with st.form("edit_f"):
                    e_cus = st.text_input("Khách thuê (Chủ HĐ)", value=r_data["khach_thue"])
                    cd1, cd2 = st.columns(2)
                    # SỬA LỖI VALUEERROR NONE TẠI ĐÂY
                    v_vao = format_date_input(r_data["ngay_vao"])
                    v_han = format_date_input(r_data["han_hd"])
                    
                    e_vao = cd1.date_input("Ngày vào", value=v_vao, format="DD/MM/YYYY")
                    e_han = cd2.date_input("Hạn HĐ", value=v_han, format="DD/MM/YYYY")
                    cg1, cg2 = st.columns(2)
                    e_gia = cg1.number_input("Giá thuê", value=int(r_data["gia"]), step=100000)
                    e_coc = cg2.number_input("Tiền cọc", value=int(r_data["tien_coc"]), step=100000)
                    e_st = st.selectbox("Trạng thái", ["Trống", "Đã thuê"], index=1 if r_data["trang_thai"]=="Đã thuê" else 0)
                    ce1, cw1 = st.columns(2)
                    e_dc = ce1.number_input("Điện ĐẦU THÁNG", value=int(r_data["dien_cu"]))
                    e_nc = cw1.number_input("Nước ĐẦU THÁNG", value=int(r_data["nuoc_cu"]))
                    if st.form_submit_button("Lưu thông tin"):
                        if IS_ADMIN:
                            c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, trang_thai=?, dien_cu=?, nuoc_cu=? WHERE id=?''', 
                                      (str(e_cus), e_vao.strftime("%d/%m/%Y") if e_vao else "", e_han.strftime("%d/%m/%Y") if e_han else "", int(e_gia), int(e_coc), str(e_st), int(e_dc), int(e_nc), int(r_data['id'])))
                            conn.commit(); st.rerun()

            with col_R:
                st.markdown("### 💸 Trạng thái & Hóa Đơn")
                e_tt = st.radio("Đánh dấu Thu Tiền:", ["Chưa thanh toán ❌", "Đã thanh toán ✅"], index=1 if r_data["thanh_toan"]=="Đã thanh toán" else 0, horizontal=True)
                if st.button("LƯU THANH TOÁN", type="primary"):
                    if IS_ADMIN:
                        c.execute('''UPDATE phong_tro SET thanh_toan=? WHERE id=?''', ("Đã thanh toán" if "Đã" in e_tt else "Chưa", int(r_data['id'])))
                        conn.commit(); st.rerun()
                st.markdown("---")
                with st.form("bill_f"):
                    ce2, cw2 = st.columns(2)
                    n_e = ce2.number_input("Điện CUỐI THÁNG", min_value=int(r_data["dien_cu"]), value=int(r_data["dien_moi"]))
                    n_w = cw2.number_input("Nước CUỐI THÁNG", min_value=int(r_data["nuoc_cu"]), value=int(r_data["nuoc_moi"]))
                    fee = st.number_input("Phí dịch vụ", value=100000)
                    if st.form_submit_button("Lưu chốt số & Xuất Hóa Đơn QR"):
                        if IS_ADMIN:
                            c.execute('''UPDATE phong_tro SET dien_moi=?, nuoc_moi=? WHERE id=?''', (int(n_e), int(n_w), int(r_data['id'])))
                            conn.commit()
                            s_dien, s_nuoc = int(n_e) - int(r_data["dien_cu"]), int(n_w) - int(r_data["nuoc_cu"])
                            tong = int(r_data["gia"]) + (s_dien * GIA_DIEN) + (s_nuoc * GIA_NUOC) + int(fee)
                            st.info(f"HÓA ĐƠN P.{selected_room}")
                            st.code(f"Chủ TK: {load_config('bank_user')}\nTiền nhà: {int(r_data['gia']):,} đ\nĐiện: {s_dien} x {GIA_DIEN:,} = {s_dien*GIA_DIEN:,} đ\nNước: {s_nuoc} x {GIA_NUOC:,} = {s_nuoc*GIA_NUOC:,} đ\nDịch vụ: {int(fee):,} đ\n>> TỔNG: {tong:,} VNĐ")
                            b_id, b_stk = load_config('bank_id'), load_config('bank_stk')
                            if b_id and b_stk:
                                st.image(tao_link_vietqr(b_id, b_stk, tong, f"P{selected_room} TT THANG {selected_month.replace('/','')}"), width=200)

# =====================================================================
# MENU 2: KIỂM SOÁT THÀNH VIÊN
# =====================================================================
elif menu == "2. Kiểm soát Thành viên":
    st.title("👥 Nhân Khẩu & 2 Mặt CCCD")
    thang_ht = f"{current_month}/{current_year}"
    df_p = pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_ht}' AND trang_thai='Đã thuê' ORDER BY phong", conn)

    if df_p.empty: st.info("Không có phòng đang thuê.")
    else:
        sel_room = st.selectbox("👉 Chọn Phòng:", df_p['phong'].tolist())
        r_data = df_p[df_p['phong'] == sel_room].iloc[0]
        
        st.markdown(f"### 👑 Chủ Hợp Đồng - Phòng {sel_room}")
        df_chu = pd.DataFrame([{
            "Họ tên": r_data['khach_thue'], "Ngày sinh": r_data['khach_thue_ngay_sinh'], 
            "CCCD": r_data['khach_thue_cccd'], "Quê quán": r_data['khach_thue_que_quan'],
            "Mặt trước": r_data['khach_thue_img_truoc'], "Mặt sau": r_data['khach_thue_img_sau']
        }])
        st.data_editor(df_chu, column_config={"Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn()}, hide_index=True, use_container_width=True, disabled=["Mặt trước", "Mặt sau"])
        
        if IS_ADMIN:
            with st.expander("📸 Cập nhật Thông tin & 2 Mặt CCCD Chủ HĐ"):
                with st.form("f_chu_2"):
                    c1, c2 = st.columns(2)
                    n_ten, n_ns = c1.text_input("Họ tên", value=r_data['khach_thue']), c1.text_input("Ngày sinh", value=r_data['khach_thue_ngay_sinh'])
                    n_cc, n_que = c2.text_input("CCCD", value=r_data['khach_thue_cccd']), c2.text_input("Quê quán", value=r_data['khach_thue_que_quan'])
                    up_t = st.file_uploader("Tải CCCD Mặt Trước", type=['png','jpg','jpeg'], key="up_t_c")
                    up_s = st.file_uploader("Tải CCCD Mặt Sau", type=['png','jpg','jpeg'], key="up_s_c")
                    if st.form_submit_button("Lưu thông tin Chủ HĐ"):
                        it = convert_image_to_base64(up_t) if up_t else r_data['khach_thue_img_truoc']
                        isau = convert_image_to_base64(up_s) if up_s else r_data['khach_thue_img_sau']
                        c.execute('''UPDATE phong_tro SET khach_thue=?, khach_thue_ngay_sinh=?, khach_thue_cccd=?, khach_thue_que_quan=?, khach_thue_img_truoc=?, khach_thue_img_sau=? WHERE id=?''', (n_ten, n_ns, n_cc, n_que, it, isau, int(r_data['id'])))
                        conn.commit(); st.rerun()

        st.markdown("---")
        st.markdown(f"### 📋 Người ở ghép - Phòng {sel_room}")
        if IS_ADMIN:
            with st.expander("➕ Thêm thành viên mới"):
                with st.form("f_tv_2"):
                    t1, t2 = st.columns(2)
                    t_ten, t_ns = t1.text_input("Họ tên"), t1.text_input("Ngày sinh")
                    t_cc, t_que = t2.text_input("CCCD"), t2.text_input("Quê quán")
                    t_ut, t_us = st.file_uploader("Ảnh Mặt Trước"), st.file_uploader("Ảnh Mặt Sau")
                    if st.form_submit_button("Thêm người"):
                        c.execute('''INSERT INTO thanh_vien (phong, ten, ngay_sinh, cccd, que_quan, img_truoc, img_sau) VALUES (?,?,?,?,?,?,?)''', (sel_room, t_ten, t_ns, t_cc, t_que, convert_image_to_base64(t_ut), convert_image_to_base64(t_us)))
                        conn.commit(); st.rerun()

        df_tv = pd.read_sql_query(f"SELECT id, ten as 'Họ tên', ngay_sinh as 'Ngày sinh', cccd as 'CCCD', que_quan as 'Quê quán', img_truoc as 'Mặt trước', img_sau as 'Mặt sau' FROM thanh_vien WHERE phong = '{sel_room}'", conn)
        if not df_tv.empty:
            if IS_ADMIN:
                df_tv['Xóa'] = False
                e_tv = st.data_editor(df_tv, column_config={"id": None, "Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn(), "Xóa": st.column_config.CheckboxColumn("🗑")}, hide_index=True, use_container_width=True)
                if st.button("💾 Lưu thay đổi danh sách"):
                    for _, r in e_tv.iterrows():
                        if r['Xóa']: c.execute("DELETE FROM thanh_vien WHERE id=?", (int(r['id']),))
                        else: c.execute("UPDATE thanh_vien SET ten=?, ngay_sinh=?, cccd=?, que_quan=? WHERE id=?", (r['Họ tên'], r['Ngày sinh'], r['CCCD'], r['Quê quán'], int(r['id'])))
                    conn.commit(); st.rerun()
            else: st.dataframe(df_tv.drop(columns=['id']), column_config={"Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn()}, hide_index=True)

# =====================================================================
# MENU 3: QUẢN LÝ BẢO TRÌ
# =====================================================================
elif menu == "3. 🛠️ Quản lý Bảo Trì":
    st.title("🛠️ Sự Cố & Sửa Chữa")
    col_t, col_p = st.columns([1, 2])
    with col_t:
        st.subheader("Ghi nhận Sự cố")
        if IS_ADMIN:
            df_phong_thue = pd.read_sql_query(f"SELECT DISTINCT phong FROM phong_tro ORDER BY phong", conn)
            with st.form("them_su_co"):
                sc_phong = st.selectbox("Phòng:", ["Khu vực chung"] + df_phong_thue['phong'].tolist() if not df_phong_thue.empty else ["Khu vực chung"])
                sc_van_de = st.text_area("Mô tả vấn đề")
                sc_ngay = st.date_input("Ngày báo", format="DD/MM/YYYY")
                if st.form_submit_button("Lưu sự cố") and sc_van_de:
                    c.execute('''INSERT INTO bao_tri (phong, van_de, ngay_bao, trang_thai) VALUES (?, ?, ?, ?)''', (sc_phong, sc_van_de, sc_ngay.strftime("%d/%m/%Y"), '🔴 Chưa sửa'))
                    conn.commit(); st.rerun()
    with col_p:
        df_bt = load_bao_tri()
        tab1, tab2 = st.tabs(["🔴 Đang chờ", "🟢 Đã sửa & Lịch sử"])
        with tab1:
            df_chua = df_bt[df_bt['trang_thai'] == '🔴 Chưa sửa']
            for _, r in df_chua.iterrows():
                with st.expander(f"📌 {r['phong']} - {r['ngay_bao']}"):
                    st.write(f"**Vấn đề:** {r['van_de']}")
                    if IS_ADMIN:
                        with st.form(f"sua_{r['id']}"):
                            cp = st.number_input("Chi phí sửa (VNĐ)", step=50000)
                            if st.form_submit_button("✅ ĐÃ SỬA XONG"):
                                c.execute('''UPDATE bao_tri SET trang_thai='🟢 Đã sửa', chi_phi=? WHERE id=?''', (int(cp), r['id']))
                                if cp > 0: c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?, ?, ?, ?, ?)''', (f"{current_month}/{current_year}", "Sửa chữa", f"P.{r['phong']}: {r['van_de']}", int(cp), datetime.now().strftime("%d/%m/%Y")))
                                conn.commit(); st.rerun()
        with tab2:
            df_da = df_bt[df_bt['trang_thai'] == '🟢 Đã sửa']
            if not df_da.empty and IS_ADMIN:
                df_da['Xóa'] = False
                ed_bt = st.data_editor(df_da, column_config={"id": None, "da_hach_toan": None, "Xóa": st.column_config.CheckboxColumn("🗑")}, hide_index=True, use_container_width=True)
                if st.button("💾 Lưu thay đổi bảo trì"):
                    for _, row in ed_bt.iterrows():
                        if row['Xóa']: c.execute("DELETE FROM bao_tri WHERE id=?", (row['id'],))
                        else: c.execute("UPDATE bao_tri SET phong=?, van_de=?, chi_phi=? WHERE id=?", (row['phong'], row['van_de'], int(row['chi_phi']), row['id']))
                    conn.commit(); st.rerun()
            else: st.dataframe(df_da.drop(columns=['id']), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 4: BÁO CÁO TÀI CHÍNH THÁNG
# =====================================================================
elif menu == "4. Báo Cáo Tài Chính Tháng":
    thang_tk = hien_thi_header_chot_ky("📊 Báo Cáo Tháng")
    df_dt = load_phong(thang_tk); df_chi = load_chi_phi(thang_tk)
    tong_thu, tong_coc = 0, 0
    if not df_dt.empty:
        tong_coc = df_dt[df_dt['trang_thai'] == 'Đã thuê']['tien_coc'].sum()
        tong_thu = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + 100000) for _, r in df_dt[df_dt['thanh_toan'] == 'Đã thanh toán'].iterrows()])
    tong_chi = df_chi['so_tien'].sum() if not df_chi.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 TỔNG THU", f"{tong_thu:,.0f} đ"); c2.metric("💸 TỔNG CHI", f"{tong_chi:,.0f} đ"); c3.metric("📈 LÃI", f"{tong_thu-tong_chi:,.0f} đ"); c4.metric("🔒 CỌC", f"{tong_coc:,.0f} đ")
    if IS_ADMIN:
        with st.expander("➕ Thêm khoản chi"):
            with st.form("t_cp"):
                cl = st.selectbox("Loại", ["Tiền Điện Toàn Nhà", "Tiền Nước Toàn Nhà", "Sửa chữa", "Rác", "Khác"])
                ch, ct = st.text_input("Ghi chú"), st.number_input("Tiền", step=50000)
                if st.form_submit_button("Lưu"):
                    c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?, ?, ?, ?, ?)''', (thang_tk, cl, ch, int(ct), datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.rerun()

# =====================================================================
# MENU 5: BÁO CÁO TÀI CHÍNH NĂM
# =====================================================================
elif menu == "5. Báo Cáo Tài Chính Năm":
    nam_n = st.selectbox("📅 Chọn Năm:", danh_sach_nam, index=danh_sach_nam.index(str(current_year)))
    tong_thu_nam, tong_chi_nam, data_nam = 0, 0, []
    for t in range(1, 13):
        ts = f"{str(t).zfill(2)}/{nam_n}"
        df_p_n, df_c_n = load_phong(ts), load_chi_phi(ts)
        thu_t = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + 100000) for _, r in df_p_n[df_p_n['thanh_toan'] == 'Đã thanh toán'].iterrows()]) if not df_p_n.empty else 0
        chi_t = df_c_n['so_tien'].sum() if not df_c_n.empty else 0
        tong_thu_nam += thu_t; tong_chi_nam += chi_t
        data_nam.append({"Tháng": f"Tháng {t}", "Thu": f"{thu_t:,.0f} đ", "Chi": f"{chi_t:,.0f} đ", "Lãi": f"{(thu_t-chi_t):,.0f} đ"})
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🌟 TỔNG DOANH THU NĂM", f"{tong_thu_nam:,.0f} VNĐ"); c2.metric("🔥 TỔNG CHI PHÍ NĂM", f"{tong_chi_nam:,.0f} VNĐ"); c3.metric("🎯 LỢI NHUẬN NĂM", f"{(tong_thu_nam - tong_chi_nam):,.0f} VNĐ")
    st.dataframe(pd.DataFrame(data_nam), use_container_width=True, hide_index=True)
