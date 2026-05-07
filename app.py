import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# ==========================================
# 0. CÀI ĐẶT TRANG & HỆ THỐNG ĐĂNG NHẬP
# ==========================================
st.set_page_config(page_title="Hệ Sinh Thái Quản Lý Trọ", layout="wide", initial_sidebar_state="expanded")

# --- DANH SÁCH TÀI KHOẢN ---
USERS = {
    "admin": {"password": "123", "role": "Admin", "name": "Chủ Trọ (Bạn)"},
    "doitac": {"password": "456", "role": "Viewer", "name": "Cổ Đông (Đối tác)"}
}

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
# 1. CÀI ĐẶT & DATABASE
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
        trang_thai TEXT, thanh_toan TEXT DEFAULT 'Chưa'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS thanh_vien (
        id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, ten TEXT, vai_tro TEXT, cccd TEXT, sdt TEXT, que_quan TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chi_phi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, thang_nam TEXT, loai TEXT, hang_muc TEXT, so_tien INTEGER, ngay_nhap TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bao_tri (
        id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, van_de TEXT, ngay_bao TEXT, trang_thai TEXT DEFAULT '🔴 Chưa sửa', chi_phi INTEGER DEFAULT 0, da_hach_toan TEXT DEFAULT 'Chưa'
    )''')
    conn.commit()
    return conn, c

conn, c = get_db_connection()

def load_phong(thang_nam): return pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_nam}'", conn)
def load_thanh_vien(phong): return pd.read_sql_query(f"SELECT * FROM thanh_vien WHERE phong = '{phong}' ORDER BY vai_tro ASC", conn)
def load_chi_phi(thang_nam): return pd.read_sql_query(f"SELECT * FROM chi_phi WHERE thang_nam = '{thang_nam}'", conn)
def load_bao_tri(): return pd.read_sql_query("SELECT * FROM bao_tri ORDER BY id DESC", conn)

def tinh_thang_truoc(thang_nam_hien_tai):
    t, n = map(int, thang_nam_hien_tai.split('/'))
    return f"12/{n-1}" if t == 1 else f"{str(t-1).zfill(2)}/{n}"

def tao_link_vietqr(ngan_hang, stk, so_tien, noi_dung):
    noi_dung_encoded = urllib.parse.quote(noi_dung)
    return f"https://img.vietqr.io/image/{ngan_hang}-{stk}-compact2.png?amount={so_tien}&addInfo={noi_dung_encoded}"

# ==========================================
# 2. SIDEBAR
# ==========================================
st.sidebar.title("🏢 MENU QUẢN LÝ")
st.sidebar.success(f"👤 Xin chào: **{st.session_state['name']}**\n\n🔑 Quyền: **{st.session_state['role']}**")

if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.markdown("---")

menu = st.sidebar.radio("Chọn chức năng:", ["1. Quản lý Phòng & Tính tiền", "2. Kiểm soát Thành viên", "3. 🛠️ Quản lý Bảo Trì", "4. Báo Cáo Tài Chính Tháng", "5. Báo Cáo Tài Chính Năm"])

if IS_ADMIN:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🏦 Cài đặt Nhận Tiền (Chỉ Admin)**")
    if 'bank_id' not in st.session_state: st.session_state['bank_id'] = "MB"
    if 'bank_stk' not in st.session_state: st.session_state['bank_stk'] = ""
    st.session_state['bank_id'] = st.sidebar.text_input("Mã Ngân Hàng", value=st.session_state['bank_id'])
    st.session_state['bank_stk'] = st.sidebar.text_input("Số Tài Khoản", value=st.session_state['bank_stk'])

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
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, gia, trang_thai) VALUES (?, ?, ?, ?, ?)''', (selected_month, p, "", 2500000, "Trống"))
                conn.commit(); st.rerun()
        with c_b:
            ky_thang_truoc = tinh_thang_truoc(selected_month)
            if st.button(f"✨ Sao chép từ kỳ trước ({ky_thang_truoc})"):
                df_truoc = load_phong(ky_thang_truoc)
                if not df_truoc.empty:
                    for _, r in df_truoc.iterrows():
                        dien_cu_new = r['dien_moi'] if r['dien_moi'] > r['dien_cu'] else r['dien_cu']
                        nuoc_cu_new = r['nuoc_moi'] if r['nuoc_moi'] > r['nuoc_cu'] else r['nuoc_cu']
                        c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, trang_thai) VALUES (?,?,?,?,?,?,?,?,?,?)''', (selected_month, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], dien_cu_new, nuoc_cu_new, r['trang_thai']))
                    conn.commit(); st.rerun()

    if not df_thang_nay.empty:
        # Metric tổng quan
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng phòng", len(df_thang_nay))
        c2.metric("Đã thuê", len(df_thang_nay[df_thang_nay["trang_thai"] == "Đã thuê"]))
        so_thu = len(df_thang_nay[df_thang_nay["thanh_toan"] == "Đã thanh toán"])
        c3.metric("Đã thu", f"{so_thu} phòng")
        c4.metric("Chưa thu", f"{len(df_thang_nay[df_thang_nay['trang_thai'] == 'Đã thuê']) - so_thu} phòng")

        # Hiển thị bảng
        df_display = df_thang_nay.sort_values(by='phong').copy()
        # Sửa lỗi tính toán nếu dữ liệu rỗng (NaN)
        for col in ['dien_cu', 'dien_moi', 'nuoc_cu', 'nuoc_moi']:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).astype(int)
        
        df_display['SD_Dien'] = df_display.apply(lambda x: max(0, x['dien_moi'] - x['dien_cu']), axis=1)
        df_display['SD_Nuoc'] = df_display.apply(lambda x: max(0, x['nuoc_moi'] - x['nuoc_cu']), axis=1)
        df_display['thanh_toan'] = df_display['thanh_toan'].apply(lambda x: '✅ Đã Đóng' if x == 'Đã thanh toán' else '❌ Chưa')
        
        st.dataframe(df_display.rename(columns={
            "phong": "Phòng", "khach_thue": "Khách thuê", "ngay_vao": "Ngày Vào", "han_hd": "Hạn HĐ", "gia": "Giá thuê", "tien_coc": "Tiền Cọc",
            "dien_cu": "Chốt Đầu(Điện)", "nuoc_cu": "Chốt Đầu(Nước)", "SD_Dien": "Đã dùng(Điện)", "SD_Nuoc": "Đã dùng(Nước)",
            "trang_thai": "Trạng thái", "thanh_toan": "Thanh Toán"
        }).drop(columns=['id', 'thang_nam', 'dien_moi', 'nuoc_moi']), use_container_width=True, height=(len(df_display)*35)+40, hide_index=True)
        
        st.markdown("---")
        if IS_ADMIN:
            selected_room = st.selectbox("👉 Chọn phòng thao tác:", ["-- Chọn phòng --"] + df_thang_nay["phong"].tolist())
            if selected_room != "-- Chọn phòng --":
                r_data = df_thang_nay[df_thang_nay["phong"] == selected_room].iloc[0]
                col_L, col_R = st.columns(2)
                with col_L:
                    st.markdown("#### ✏️ Cập nhật Thông tin")
                    with st.form("edit_f"):
                        e_cus = st.text_input("Khách thuê (Chủ HĐ)", value=r_data["khach_thue"])
                        cd1, cd2 = st.columns(2)
                        v_vao = datetime.strptime(r_data["ngay_vao"], "%d/%m/%Y").date() if r_data["ngay_vao"] else None
                        v_han = datetime.strptime(r_data["han_hd"], "%d/%m/%Y").date() if r_data["han_hd"] else None
                        e_vao = cd1.date_input("Ngày vào", value=v_vao, format="DD/MM/YYYY")
                        e_han = cd2.date_input("Hạn HĐ", value=v_han, format="DD/MM/YYYY")
                        cg1, cg2 = st.columns(2)
                        e_gia = cg1.number_input("Giá thuê", value=int(r_data["gia"]), step=100000)
                        e_coc = cg2.number_input("Tiền cọc", value=int(r_data["tien_coc"]), step=100000)
                        e_st = st.selectbox("Trạng thái", ["Trống", "Đã thuê"], index=0 if r_data["trang_thai"]=="Trống" else 1)
                        ce1, cw1 = st.columns(2)
                        e_dc = ce1.number_input("Điện ĐẦU THÁNG", value=int(r_data["dien_cu"]))
                        e_nc = cw1.number_input("Nước ĐẦU THÁNG", value=int(r_data["nuoc_cu"]))
                        if st.form_submit_button("Lưu thông tin"):
                            c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, trang_thai=?, dien_cu=?, nuoc_cu=? WHERE id=?''', 
                                      (str(e_cus), e_vao.strftime("%d/%m/%Y") if e_vao else "", e_han.strftime("%d/%m/%Y") if e_han else "", int(e_gia), int(e_coc), str(e_st), int(e_dc), int(e_nc), int(r_data['id'])))
                            conn.commit(); st.rerun()
                with col_R:
                    st.markdown("#### 💸 Trạng thái & Hóa Đơn")
                    e_tt = st.radio("Đánh dấu Thu Tiền:", ["Chưa thanh toán ❌", "Đã thanh toán ✅"], index=1 if r_data["thanh_toan"]=="Đã thanh toán" else 0, horizontal=True)
                    if st.button("LƯU THANH TOÁN", type="primary"):
                        c.execute('''UPDATE phong_tro SET thanh_toan=? WHERE id=?''', ("Đã thanh toán" if "Đã" in e_tt else "Chưa", int(r_data['id'])))
                        conn.commit(); st.rerun()
                    st.markdown("---")
                    with st.form("bill_f"):
                        ce2, cw2 = st.columns(2)
                        n_e = ce2.number_input("Điện CUỐI THÁNG", min_value=int(r_data["dien_cu"]), value=int(r_data["dien_moi"] or r_data["dien_cu"]))
                        n_w = cw2.number_input("Nước CUỐI THÁNG", min_value=int(r_data["nuoc_cu"]), value=int(r_data["nuoc_moi"] or r_data["nuoc_cu"]))
                        fee = st.number_input("Phí dịch vụ", value=100000)
                        if st.form_submit_button("Lưu chốt số & Xuất Hóa Đơn QR"):
                            c.execute('''UPDATE phong_tro SET dien_moi=?, nuoc_moi=? WHERE id=?''', (int(n_e), int(n_w), int(r_data['id'])))
                            conn.commit()
                            s_dien, s_nuoc = int(n_e) - int(r_data["dien_cu"]), int(n_w) - int(r_data["nuoc_cu"])
                            tong = int(r_data["gia"]) + (s_dien * GIA_DIEN) + (s_nuoc * GIA_NUOC) + int(fee)
                            col_t, col_q = st.columns([1.5, 1])
                            with col_t:
                                st.code(f"HÓA ĐƠN P.{selected_room}\nTiền nhà: {int(r_data['gia']):,} đ\nĐiện: {s_dien} x {GIA_DIEN:,} = {s_dien*GIA_DIEN:,} đ\nNước: {s_nuoc} x {GIA_NUOC:,} = {s_nuoc*GIA_NUOC:,} đ\nDịch vụ: {int(fee):,} đ\n>> TỔNG: {tong:,} VNĐ")
                            with col_q:
                                if st.session_state.get('bank_stk'):
                                    link_qr = tao_link_vietqr(st.session_state['bank_id'], st.session_state['bank_stk'], tong, f"P{selected_room} TT THANG {selected_month.replace('/','')}")
                                    st.image(link_qr, width=200)

# =====================================================================
# MENU 2: KIỂM SOÁT THÀNH VIÊN (FIXED: ĐỒNG BỘ CHỦ HỢP ĐỒNG)
# =====================================================================
elif menu == "2. Kiểm soát Thành viên":
    st.title("👥 Quản Lý Nhân Khẩu")
    thang_ht = f"{current_month}/{current_year}"
    df_p = pd.read_sql_query(f"SELECT phong, khach_thue FROM phong_tro WHERE thang_nam = '{thang_ht}' AND trang_thai='Đã thuê' ORDER BY phong", conn)
    
    if df_p.empty: st.info("Chưa có phòng cho thuê.")
    else:
        col1, col2 = st.columns([1, 2.5])
        with col1:
            phong_tv = st.selectbox("Chọn Phòng:", df_p['phong'].tolist())
            # Lấy tên khách thuê chuẩn từ Menu 1
            ten_khach_chuan = df_p[df_p['phong'] == phong_tv].iloc[0]['khach_thue']
            
            # --- ĐOẠN MÃ SỬA LỖI: Tự động đồng bộ Chủ Hợp Đồng ---
            check_chu = pd.read_sql_query(f"SELECT * FROM thanh_vien WHERE phong='{phong_tv}' AND vai_tro='👑 Chủ Hợp Đồng'", conn)
            
            if check_chu.empty:
                if ten_khach_chuan:
                    c.execute('INSERT INTO thanh_vien (phong, ten, vai_tro, cccd, sdt, que_quan) VALUES (?,?,?,?,?,?)', (phong_tv, ten_khach_chuan, '👑 Chủ Hợp Đồng', '', '', ''))
                    conn.commit()
            else:
                if check_chu.iloc[0]['ten'] != ten_khach_chuan:
                    c.execute('UPDATE thanh_vien SET ten=? WHERE phong=? AND vai_tro=?', (ten_khach_chuan, phong_tv, '👑 Chủ Hợp Đồng'))
                    conn.commit()
            # --------------------------------------------------

            if IS_ADMIN:
                with st.form("them_tv"):
                    st.write("**➕ Thêm Người ở ghép**")
                    t_ten, t_cccd, t_sdt = st.text_input("Tên"), st.text_input("CCCD"), st.text_input("SĐT")
                    if st.form_submit_button("Lưu người mới") and t_ten:
                        c.execute('''INSERT INTO thanh_vien (phong, ten, vai_tro, cccd, sdt, que_quan) VALUES (?, ?, ?, ?, ?, ?)''', (phong_tv, t_ten, '👤 Người ở ghép', t_cccd, t_sdt, ''))
                        conn.commit(); st.rerun()
        with col2:
            st.write(f"**Danh sách người ở Phòng {phong_tv}**")
            df_tv = load_thanh_vien(phong_tv)
            if IS_ADMIN:
                if not df_tv.empty:
                    df_edit = df_tv.copy(); df_edit['Xóa'] = False
                    res = st.data_editor(df_edit, column_config={"id": None, "phong": None, "ten": st.column_config.TextColumn("Họ Tên", disabled=True), "vai_tro": st.column_config.TextColumn("Vai Trò", disabled=True), "Xóa": st.column_config.CheckboxColumn("🗑 Xóa", default=False)}, hide_index=True, use_container_width=True)
                    if st.button("💾 LƯU THAY ĐỔI", type="primary"):
                        for _, r in res.iterrows():
                            if r['Xóa'] and r['vai_tro'] != '👑 Chủ Hợp Đồng': c.execute(f"DELETE FROM thanh_vien WHERE id = {r['id']}")
                            elif not r['Xóa']: c.execute('''UPDATE thanh_vien SET cccd=?, sdt=?, que_quan=? WHERE id=?''', (r['cccd'], r['sdt'], r['que_quan'], r['id']))
                        conn.commit(); st.rerun()
            else:
                if not df_tv.empty: st.dataframe(df_tv.drop(columns=['id', 'phong']), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 3: BẢO TRÌ
# =====================================================================
elif menu == "3. 🛠️ Quản lý Bảo Trì":
    st.title("🛠️ Sự Cố & Sửa Chữa")
    col_t, col_p = st.columns([1, 2])
    with col_t:
        if IS_ADMIN:
            with st.form("them_su_co"):
                sc_phong = st.selectbox("Phòng:", DANH_SACH_MAC_DINH)
                sc_van_de = st.text_area("Mô tả vấn đề")
                sc_ngay = st.date_input("Ngày báo")
                if st.form_submit_button("Lưu") and sc_van_de:
                    c.execute('INSERT INTO bao_tri (phong, van_de, ngay_bao) VALUES (?, ?, ?)', (sc_phong, sc_van_de, sc_ngay.strftime("%d/%m/%Y")))
                    conn.commit(); st.rerun()
    with col_p:
        df_bt = load_bao_tri()
        if not df_bt.empty:
            tab1, tab2 = st.tabs(["🔴 Đang chờ", "🟢 Đã sửa"])
            with tab1:
                for _, r in df_bt[df_bt['trang_thai'] == '🔴 Chưa sửa'].iterrows():
                    with st.expander(f"{r['phong']} - {r['ngay_bao']}"):
                        st.write(r['van_de'])
                        if IS_ADMIN:
                            t_cp = st.number_input("Phí sửa", key=f"cp_{r['id']}", step=50000)
                            if st.button("Xong", key=f"btn_{r['id']}"):
                                c.execute('UPDATE bao_tri SET trang_thai="🟢 Đã sửa", chi_phi=? WHERE id=?', (int(t_cp), r['id']))
                                if t_cp > 0: c.execute('INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?,?,?,?,?)', (f"{current_month}/{current_year}", "Sửa chữa", f"{r['phong']}:{r['van_de']}", int(t_cp), datetime.now().strftime("%d/%m/%Y")))
                                conn.commit(); st.rerun()
            with tab2: st.dataframe(df_bt[df_bt['trang_thai'] == '🟢 Đã sửa'].drop(columns='id'), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 4 & 5: TÀI CHÍNH
# =====================================================================
elif menu == "4. Báo Cáo Tài Chính Tháng":
    thang_tk = hien_thi_header_chot_ky("📊 Báo Cáo Tháng")
    df_dt = load_phong(thang_tk)
    tong_thu = 0
    if not df_dt.empty:
        df_da_thu = df_dt[df_dt['thanh_toan'] == 'Đã thanh toán']
        for _, r in df_da_thu.iterrows():
            sd = max(0, (r['dien_moi'] or 0) - (r['dien_cu'] or 0))
            sn = max(0, (r['nuoc_moi'] or 0) - (r['nuoc_cu'] or 0))
            tong_thu += (r['gia'] or 0) + (sd * GIA_DIEN) + (sn * GIA_NUOC) + 100000
    df_chi = load_chi_phi(thang_tk)
    tong_chi = df_chi['so_tien'].sum() if not df_chi.empty else 0
    st.metric("LỢI NHUẬN THÁNG", f"{tong_thu - tong_chi:,} đ")
    st.dataframe(df_chi.drop(columns=['id','thang_nam']), use_container_width=True)

elif menu == "5. Báo Cáo Tài Chính Năm":
    n_chon = st.selectbox("Năm", danh_sach_nam, index=danh_sach_nam.index(str(current_year)))
    res = []
    for t in range(1, 13):
        ts = f"{str(t).zfill(2)}/{n_chon}"
        df_p = load_phong(ts)
        thu = sum([(r['gia'] + max(0, (r['dien_moi'] or 0)-(r['dien_cu'] or 0))*GIA_DIEN + max(0, (r['nuoc_moi'] or 0)-(r['nuoc_cu'] or 0))*GIA_NUOC + 100000) for _, r in df_p[df_p['thanh_toan'] == 'Đã thanh toán'].iterrows()]) if not df_p.empty else 0
        res.append({"Tháng": t, "Thu": thu})
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
