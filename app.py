import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# ==========================================
# 0. CÀI ĐẶT TRANG & HỆ THỐNG ĐĂNG NHẬP
# ==========================================
st.set_page_config(page_title="Quản Lý Trọ V16", layout="wide", initial_sidebar_state="expanded")

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
                    st.session_state.update({'logged_in':True, 'role':USERS[u]["role"], 'name':USERS[u]["name"]})
                    st.rerun()
                else: st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

IS_ADMIN = (st.session_state['role'] == "Admin")

# ==========================================
# 1. DATABASE & CẤU HÌNH (V16)
# ==========================================
GIA_DIEN = 4000
GIA_NUOC = 30000
DANH_SACH_MAC_DINH = ["101", "102", "103", "104", "105", "106", "201", "202", "203", "204", "205", "301", "302", "303", "304", "305", "401", "402"]

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('dulieu_tro_v16.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS phong_tro (id INTEGER PRIMARY KEY AUTOINCREMENT, thang_nam TEXT, phong TEXT, khach_thue TEXT, ngay_vao TEXT, han_hd TEXT, gia INTEGER, tien_coc INTEGER DEFAULT 0, dien_cu INTEGER, nuoc_cu INTEGER, dien_moi INTEGER DEFAULT 0, nuoc_moi INTEGER DEFAULT 0, trang_thai TEXT, thanh_toan TEXT DEFAULT "Chưa")')
    c.execute('CREATE TABLE IF NOT EXISTS thanh_vien (id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, ten TEXT, vai_tro TEXT, cccd TEXT, sdt TEXT, que_quan TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS chi_phi (id INTEGER PRIMARY KEY AUTOINCREMENT, thang_nam TEXT, loai TEXT, hang_muc TEXT, so_tien INTEGER, ngay_nhap TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS bao_tri (id INTEGER PRIMARY KEY AUTOINCREMENT, phong TEXT, van_de TEXT, ngay_bao TEXT, trang_thai TEXT DEFAULT "🔴 Chưa sửa", chi_phi INTEGER DEFAULT 0)')
    conn.commit()
    return conn, c

conn, c = get_db_connection()

def load_phong(thang_nam): return pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_nam}'", conn)
def load_thanh_vien(phong): return pd.read_sql_query(f"SELECT * FROM thanh_vien WHERE phong = '{phong}' ORDER BY vai_tro ASC", conn)
def load_chi_phi(thang_nam): return pd.read_sql_query(f"SELECT * FROM chi_phi WHERE thang_nam = '{thang_nam}'", conn)

def tinh_thang_truoc(thang_nam_hien_tai):
    t, n = map(int, thang_nam_hien_tai.split('/'))
    return f"12/{n-1}" if t == 1 else f"{str(t-1).zfill(2)}/{n}"

# ==========================================
# 2. MENU SIDEBAR
# ==========================================
st.sidebar.title("🏢 MENU QUẢN LÝ")
st.sidebar.success(f"👤 **{st.session_state['name']}** ({st.session_state['role']})")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()

menu = st.sidebar.radio("Chọn chức năng:", ["1. Quản lý Phòng & Tính tiền", "2. Kiểm soát Thành viên", "3. 🛠️ Quản lý Bảo Trì", "4. Báo Cáo Tài Chính Tháng", "5. Báo Cáo Tài Chính Năm"])

current_year, current_month = datetime.now().year, str(datetime.now().month).zfill(2)
d_nam = [str(y) for y in range(2024, current_year + 5)]
d_thang = [str(m).zfill(2) for m in range(1, 13)]

def get_header(tieu_de):
    c1, c2, c3 = st.columns([2.5, 0.5, 0.5])
    with c1: st.title(tieu_de)
    with c2: t = st.selectbox("Tháng", d_thang, index=d_thang.index(current_month))
    with c3: n = st.selectbox("Năm", d_nam, index=d_nam.index(str(current_year)))
    return f"{t}/{n}"

# =====================================================================
# MENU 1: QUẢN LÝ PHÒNG & TÍNH TIỀN
# =====================================================================
if menu == "1. Quản lý Phòng & Tính tiền":
    sel_m = get_header("🏠 Quản Lý Phòng")
    df = load_phong(sel_m)
    
    if df.empty and IS_ADMIN:
        st.warning(f"Kỳ {sel_m} chưa có dữ liệu.")
        c_a, c_b = st.columns(2)
        if c_a.button("🆕 Khởi tạo 18 phòng mặc định"):
            for p in DANH_SACH_MAC_DINH:
                c.execute('INSERT INTO phong_tro (thang_nam, phong, khach_thue, gia, trang_thai) VALUES (?,?,?,?,?)', (sel_m, p, "", 2500000, "Trống"))
            conn.commit(); st.rerun()
        k_truoc = tinh_thang_truoc(sel_m)
        if c_b.button(f"✨ Sao chép từ kỳ trước ({k_truoc})"):
            df_t = load_phong(k_truoc)
            for _, r in df_t.iterrows():
                dc_n = r['dien_moi'] if r['dien_moi'] > r['dien_cu'] else r['dien_cu']
                nc_n = r['nuoc_moi'] if r['nuoc_moi'] > r['nuoc_cu'] else r['nuoc_cu']
                c.execute('INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, trang_thai) VALUES (?,?,?,?,?,?,?,?,?,?)', (sel_m, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], dc_n, nc_n, r['trang_thai']))
            conn.commit(); st.rerun()

    if not df.empty:
        df_dis = df.sort_values('phong').copy()
        df_dis['Dùng(Đ)'] = df_dis.apply(lambda x: max(0, x['dien_moi'] - x['dien_cu']), axis=1)
        df_dis['Dùng(N)'] = df_dis.apply(lambda x: max(0, x['nuoc_moi'] - x['nuoc_cu']), axis=1)
        df_dis['TT'] = df_dis['thanh_toan'].apply(lambda x: '✅ Đóng' if x == 'Đã thanh toán' else '❌ Chưa')
        st.dataframe(df_dis.rename(columns={"phong":"Phòng","khach_thue":"Khách","gia":"Giá","dien_cu":"Số cũ(Đ)","nuoc_cu":"Số cũ(N)"}).drop(columns=['id','thang_nam','dien_moi','nuoc_moi','thanh_toan']), use_container_width=True, hide_index=True)
        
        if IS_ADMIN:
            st.markdown("---")
            sel_p = st.selectbox("👉 Chọn phòng:", ["-- Chọn --"] + df['phong'].tolist())
            if sel_p != "-- Chọn --":
                r = df[df['phong'] == sel_p].iloc[0]
                cl, cr = st.columns(2)
                with cl:
                    with st.form("edit_room"):
                        st.write("✏️ **Cập nhật thông tin**")
                        ten = st.text_input("Tên khách", value=r['khach_thue'])
                        cg1, cg2 = st.columns(2)
                        gia = cg1.number_input("Giá thuê", value=int(r['gia']), step=100000)
                        coc = cg2.number_input("Tiền cọc", value=int(r['tien_coc']), step=100000)
                        if st.form_submit_button("Lưu thay đổi"):
                            c.execute('UPDATE phong_tro SET khach_thue=?, gia=?, tien_coc=? WHERE id=?', (ten, gia, coc, int(r['id'])))
                            conn.commit(); st.rerun()
                with cr:
                    st.write("🧾 **Tính tiền & QR**")
                    with st.form("bill"):
                        ce1, ce2 = st.columns(2)
                        d_m = ce1.number_input("Điện mới", min_value=int(r['dien_cu']), value=max(int(r['dien_moi']), int(r['dien_cu'])))
                        n_m = ce2.number_input("Nước mới", min_value=int(r['nuoc_cu']), value=max(int(r['nuoc_moi']), int(r['nuoc_cu'])))
                        if st.form_submit_button("Tính tiền"):
                            c.execute('UPDATE phong_tro SET dien_moi=?, nuoc_moi=? WHERE id=?', (d_m, n_m, int(r['id'])))
                            conn.commit(); st.success("Đã chốt số!")
                            tong = int(r['gia']) + (d_m - r['dien_cu'])*GIA_DIEN + (n_m - r['nuoc_cu'])*GIA_NUOC + 100000
                            st.code(f"Phòng {sel_p}: {tong:,} VNĐ")
                            if st.session_state.get('bank_stk'):
                                link = f"https://img.vietqr.io/image/{st.session_state['bank_id']}-{st.session_state['bank_stk']}-compact2.png?amount={tong}&addInfo=P{sel_p}%20TT"
                                st.image(link, width=180)

# =====================================================================
# MENU 2: KIỂM SOÁT THÀNH VIÊN (SỬA LỖI ĐỒNG BỘ CHỦ HỘ)
# =====================================================================
elif menu == "2. Kiểm soát Thành viên":
    st.title("👥 Quản Lý Thành Viên")
    ky_ht = f"{current_month}/{current_year}"
    df_p = pd.read_sql_query(f"SELECT phong, khach_thue FROM phong_tro WHERE thang_nam='{ky_ht}' AND trang_thai='Đã thuê'", conn)
    
    if df_p.empty: st.info("Tháng này chưa có phòng nào được thuê.")
    else:
        col1, col2 = st.columns([1, 2.5])
        with col1:
            sel_p_tv = st.selectbox("Chọn phòng:", df_p['phong'].tolist())
            # LẤY TÊN KHÁCH MỚI NHẤT TỪ MENU 1
            ten_khach_chuan = df_p[df_p['phong'] == sel_p_tv].iloc[0]['khach_thue']
            
            # --- LOGIC TỰ ĐỘNG ĐỒNG BỘ CHỦ HỘ ---
            df_tv_hien_tai = pd.read_sql_query(f"SELECT * FROM thanh_vien WHERE phong='{sel_p_tv}' AND vai_tro='👑 Chủ Hợp Đồng'", conn)
            
            if df_tv_hien_tai.empty:
                # Nếu trong bảng thành viên chưa có chủ hộ -> Thêm mới
                if ten_khach_chuan:
                    c.execute('INSERT INTO thanh_vien (phong, ten, vai_tro, cccd, sdt, que_quan) VALUES (?,?,?,?,?,?)', (sel_p_tv, ten_khach_chuan, '👑 Chủ Hợp Đồng', '', '', ''))
                    conn.commit()
            else:
                # Nếu đã có nhưng tên bị khác (do bạn vừa đổi ở Menu 1) -> Cập nhật tên
                ten_trong_db = df_tv_hien_tai.iloc[0]['ten']
                if ten_trong_db != ten_khach_chuan:
                    c.execute('UPDATE thanh_vien SET ten=? WHERE phong=? AND vai_tro=?', (ten_khach_chuan, sel_p_tv, '👑 Chủ Hợp Đồng'))
                    conn.commit()
            
            if IS_ADMIN:
                with st.form("add_tv"):
                    st.write("➕ **Thêm người ở ghép**")
                    t = st.text_input("Họ tên")
                    c_id = st.text_input("CCCD")
                    if st.form_submit_button("Thêm") and t:
                        c.execute('INSERT INTO thanh_vien (phong, ten, vai_tro, cccd, sdt, que_quan) VALUES (?,?,?,?,?,?)', (sel_p_tv, t, '👤 Người ở ghép', c_id, '', ''))
                        conn.commit(); st.rerun()

        with col2:
            st.write(f"**Nhân khẩu Phòng {sel_p_tv}**")
            df_tv = load_thanh_vien(sel_p_tv)
            if not df_tv.empty:
                if IS_ADMIN:
                    st.info("💡 Kích đúp để sửa CCCD/SĐT. Tích Xóa để xóa người ở ghép.")
                    df_edit = df_tv.copy(); df_edit['Xóa'] = False
                    res = st.data_editor(df_edit, column_config={"id":None, "phong":None, "ten":st.column_config.TextColumn(disabled=True), "vai_tro":st.column_config.TextColumn(disabled=True), "Xóa":st.column_config.CheckboxColumn()}, hide_index=True, use_container_width=True)
                    if st.button("💾 LƯU THAY ĐỔI"):
                        for _, row in res.iterrows():
                            if row['Xóa'] and row['vai_tro'] != '👑 Chủ Hợp Đồng': c.execute(f"DELETE FROM thanh_vien WHERE id={row['id']}")
                            else: c.execute('UPDATE thanh_vien SET cccd=?, sdt=?, que_quan=? WHERE id=?', (row['cccd'], row['sdt'], row['que_quan'], row['id']))
                        conn.commit(); st.rerun()
                else:
                    st.dataframe(df_tv.drop(columns=['id','phong']), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 3: BẢO TRÌ
# =====================================================================
elif menu == "3. 🛠️ Quản lý Bảo Trì":
    st.title("🛠️ Bảo Trì & Sự Cố")
    c1, c2 = st.columns([1, 2])
    with c1:
        if IS_ADMIN:
            with st.form("bt"):
                p = st.selectbox("Phòng:", ["Chung"] + DANH_SACH_MAC_DINH)
                v = st.text_area("Vấn đề")
                if st.form_submit_button("Ghi nhận") and v:
                    c.execute('INSERT INTO bao_tri (phong, van_de, ngay_bao) VALUES (?,?,?)', (p, v, datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.rerun()
    with c2:
        df_b = load_bao_tri()
        if not df_b.empty:
            tab1, tab2 = st.tabs(["🔴 Chờ sửa", "🟢 Đã xong"])
            with tab1:
                for _, r in df_b[df_b['trang_thai']=='🔴 Chưa sửa'].iterrows():
                    with st.expander(f"{r['phong']} - {r['ngay_bao']}"):
                        st.write(r['van_de'])
                        if IS_ADMIN:
                            cost = st.number_input("Phí sửa", key=f"c_{r['id']}", step=10000)
                            if st.button("Xác nhận xong", key=f"b_{r['id']}"):
                                c.execute('UPDATE bao_tri SET trang_thai="🟢 Đã sửa", chi_phi=? WHERE id=?', (cost, r['id']))
                                if cost > 0: c.execute('INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?,?,?,?,?)', (f"{current_month}/{current_year}", "Sửa chữa", f"{r['phong']}:{r['van_de']}", cost, datetime.now().strftime("%d/%m/%Y")))
                                conn.commit(); st.rerun()
            with tab2: st.dataframe(df_b[df_b['trang_thai']=='🟢 Đã sửa'].drop(columns='id'), use_container_width=True)

# =====================================================================
# MENU 4 & 5: TÀI CHÍNH (GIỮ NGUYÊN)
# =====================================================================
elif menu == "4. Báo Cáo Tài Chính Tháng":
    m = get_header("📊 Báo Cáo Tháng")
    df_p = load_phong(m)
    thu = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + 100000) for _, r in df_p[df_p['thanh_toan'] == 'Đã thanh toán'].iterrows()])
    df_c = load_chi_phi(m)
    chi = df_c['so_tien'].sum()
    c1, c2, c3 = st.columns(3); c1.metric("THU", f"{thu:,}đ"); c2.metric("CHI", f"{chi:,}đ"); c3.metric("LÃI", f"{thu-chi:,}đ")
    if IS_ADMIN:
        with st.expander("➕ Thêm khoản chi"):
            with st.form("c"):
                l = st.selectbox("Loại", ["Điện tổng","Nước tổng","Sửa chữa","Khác"])
                s = st.number_input("Số tiền", step=10000)
                if st.form_submit_button("Lưu"):
                    c.execute('INSERT INTO chi_phi (thang_nam, loai, so_tien, ngay_nhap) VALUES (?,?,?,?)', (m, l, s, datetime.now().strftime("%d/%m/%Y")))
                    conn.commit(); st.rerun()
    st.dataframe(df_c.drop(columns=['id','thang_nam']), use_container_width=True)

elif menu == "5. Báo Cáo Tài Chính Năm":
    n = st.selectbox("Năm", d_nam, index=d_nam.index(str(current_year)))
    res = []
    for i in range(1, 13):
        ts = f"{str(i).zfill(2)}/{n}"
        df_p = load_phong(ts)
        thu = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + 100000) for _, r in df_p[df_p['thanh_toan'] == 'Đã thanh toán'].iterrows()])
        chi = load_chi_phi(ts)['so_tien'].sum()
        res.append({"Tháng": i, "Thu": thu, "Chi": chi, "Lãi": thu-chi})
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
