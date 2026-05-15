import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import urllib.parse
import base64

# ==========================================
# 0. CÀI ĐẶT TRANG & HỆ THỐNG ĐĂNG NHẬP
# ==========================================
st.set_page_config(page_title="Hệ Sinh Thái Quản Lý Trọ", layout="wide", initial_sidebar_state="expanded")

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
# 1. DATABASE & CẤU HÌNH
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
        khach_thue_ngay_sinh TEXT, khach_thue_cccd TEXT, khach_thue_que_quan TEXT, khach_thue_img_truoc TEXT, khach_thue_img_sau TEXT,
        phi_dich_vu INTEGER DEFAULT 0, ngay_thanh_toan TEXT, tong_tien_bill INTEGER DEFAULT 0,
        sale_nhan_vien TEXT, hoa_hong INTEGER DEFAULT 0, tien_nha_status TEXT DEFAULT 'Chưa đóng'
    )''')
    
    try: c.execute("ALTER TABLE phong_tro ADD COLUMN sale_nhan_vien TEXT")
    except: pass
    try: c.execute("ALTER TABLE phong_tro ADD COLUMN hoa_hong INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE phong_tro ADD COLUMN tien_nha_status TEXT DEFAULT 'Chưa đóng'")
    except: pass
    
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

def format_date_input(date_str):
    if pd.notnull(date_str) and str(date_str).strip() not in ["None", "nan", ""]:
        try: return datetime.strptime(str(date_str), "%d/%m/%Y").date()
        except: return None
    return None

def load_phong(thang_nam): return pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_nam}'", conn)
def load_chi_phi(thang_nam): return pd.read_sql_query(f"SELECT * FROM chi_phi WHERE thang_nam = '{thang_nam}'", conn)
def load_bao_tri(): return pd.read_sql_query("SELECT * FROM bao_tri ORDER BY id DESC", conn)

def tinh_thang_truoc(thang_nam_hien_tai):
    t, n = map(int, thang_nam_hien_tai.split('/'))
    return f"12/{n-1}" if t == 1 else f"{str(t-1).zfill(2)}/{n}"

def tinh_thang_tiep_theo(thang_nam):
    t, n = map(int, thang_nam.split('/'))
    return f"01/{n+1}" if t == 12 else f"{str(t+1).zfill(2)}/{n}"

def tao_link_vietqr(ngan_hang, stk, so_tien, noi_dung, ten_chu_tk):
    noi_dung_encoded = urllib.parse.quote(noi_dung)
    ten_encoded = urllib.parse.quote(ten_chu_tk)
    return f"https://img.vietqr.io/image/{ngan_hang}-{stk}-compact2.png?amount={so_tien}&addInfo={noi_dung_encoded}&accountName={ten_encoded}"

def hien_thi_header_chot_ky(tieu_de, list_m, list_y, cur_m, cur_y):
    col_title, col_chon_thang, col_chon_nam = st.columns([2.5, 0.5, 0.5])
    with col_title: st.title(tieu_de)
    with col_chon_thang:
        thang_chon = st.selectbox("Tháng:", list_m, index=list_m.index(cur_m))
    with col_chon_nam:
        nam_chon = st.selectbox("Năm:", list_y, index=list_y.index(str(cur_y)))
    return f"{thang_chon}/{nam_chon}"

# ==========================================
# 2. MENU SIDEBAR
# ==========================================
st.sidebar.title("🏢 MENU QUẢN LÝ")
st.sidebar.success(f"👤: **{st.session_state['name']}**\n🔑: **{st.session_state['role']}**")

if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio("Chọn chức năng:", ["1. Sơ Đồ Phòng & Quản Lý", "2. 🛠️ Quản lý Bảo Trì", "3. Báo Cáo Tài Chính Tháng", "4. Báo Cáo Tài Chính Năm"])

db_bank_id = load_config("bank_id", "MB")
db_bank_stk = load_config("bank_stk", "")
db_bank_user = load_config("bank_user", "")

if IS_ADMIN:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🏦 Cài đặt Nhận Tiền**")
    new_bank_id = st.sidebar.text_input("Mã Ngân Hàng", value=db_bank_id)
    new_bank_stk = st.sidebar.text_input("Số Tài Khoản", value=db_bank_stk)
    new_bank_user = st.sidebar.text_input("Tên Chủ Tài Khoản", value=db_bank_user)
    if st.sidebar.button("💾 Lưu cấu hình ngân hàng"):
        save_config("bank_id", new_bank_id); save_config("bank_stk", new_bank_stk); save_config("bank_user", new_bank_user)
        st.sidebar.success("Đã lưu!"); st.rerun()

current_year, current_month = datetime.now().year, str(datetime.now().month).zfill(2)
danh_sach_nam = [str(y) for y in range(2024, current_year + 6)]
danh_sach_thang_don = [str(m).zfill(2) for m in range(1, 13)]

# =====================================================================
# MENU 1: SƠ ĐỒ PHÒNG & QUẢN LÝ
# =====================================================================
if menu == "1. Sơ Đồ Phòng & Quản Lý":
    selected_month = hien_thi_header_chot_ky("🏠 Quản Lý Dãy Trọ", danh_sach_thang_don, danh_sach_nam, current_month, current_year)
    df_phong = load_phong(selected_month)
    
    if IS_ADMIN:
        col_m1, col_m2, col_m3 = st.columns([1, 1, 2])
        with col_m1:
            if st.button("🗑️ Xóa dữ liệu kỳ này", type="secondary", use_container_width=True):
                c.execute(f"DELETE FROM phong_tro WHERE thang_nam = '{selected_month}'")
                conn.commit(); st.rerun()
        with col_m2:
            if st.button("🔄 Cập nhật từ tháng trước", type="primary", use_container_width=True):
                ky_truoc = tinh_thang_truoc(selected_month)
                df_truoc = load_phong(ky_truoc)
                if not df_truoc.empty:
                    c.execute(f"DELETE FROM phong_tro WHERE thang_nam = '{selected_month}'")
                    for _, r in df_truoc.iterrows():
                        d_c = max(r['dien_moi'], r['dien_cu'])
                        n_c = max(r['nuoc_moi'], r['nuoc_cu'])
                        stt_nha = r.get('tien_nha_status', 'Chưa đóng')
                        c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, trang_thai, thanh_toan, phi_dich_vu, sale_nhan_vien, hoa_hong, tien_nha_status, tong_tien_bill, dien_moi, nuoc_moi) 
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (selected_month, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], d_c, n_c, r['trang_thai'], "Chưa", 0, r['sale_nhan_vien'], 0, stt_nha, 0, 0, 0))
                    conn.commit(); st.rerun()

    if df_phong.empty and IS_ADMIN:
        ky_truoc = tinh_thang_truoc(selected_month)
        df_truoc = load_phong(ky_truoc)
        if not df_truoc.empty:
            for _, r in df_truoc.iterrows():
                d_c = max(r['dien_moi'], r['dien_cu'])
                n_c = max(r['nuoc_moi'], r['nuoc_cu'])
                stt_nha = r.get('tien_nha_status', 'Chưa đóng')
                c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, trang_thai, thanh_toan, phi_dich_vu, sale_nhan_vien, hoa_hong, tien_nha_status, tong_tien_bill, dien_moi, nuoc_moi) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (selected_month, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], d_c, n_c, r['trang_thai'], "Chưa", 0, r['sale_nhan_vien'], 0, stt_nha, 0, 0, 0))
            conn.commit(); st.rerun()
        else:
            if st.button("🆕 Khởi tạo 18 phòng"):
                for p in DANH_SACH_MAC_DINH:
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, gia, dien_cu, nuoc_cu, trang_thai, thanh_toan, phi_dich_vu, tien_nha_status) VALUES (?,?,?,?,?,?,?,?,?,?)''', (selected_month, p, "", 2500000, 0, 0, "Trống", "Chưa", 0, "Chưa đóng"))
                conn.commit(); st.rerun()

    if not df_phong.empty:
        df_phong = df_phong.sort_values('phong')
        m1, m2, m3, m4 = st.columns(4)
        rented_p = len(df_phong[df_phong['trang_thai'] == 'Đã thuê'])
        m1.metric("Tổng số phòng", len(df_phong))
        m2.metric("Đã thuê", rented_p)
        m3.metric("Phòng trống", len(df_phong) - rented_p)
        m4.metric("Đã thu tiền", len(df_phong[df_phong['thanh_toan'] == 'Đã thanh toán']))
        
        cols = st.columns(6)
        for i, (idx, r) in enumerate(df_phong.iterrows()):
            with cols[i % 6]:
                stt_text = "⚪ Trống"
                if r['trang_thai'] == "Đã thuê":
                    stt_text = "✅ Xong" if r['thanh_toan'] == "Đã thanh toán" else "🔴 Chốt"
                if st.button(f"P.{r['phong']}\n{stt_text}", key=f"btn_{r['phong']}", use_container_width=True):
                    st.session_state['selected_room'] = r['phong']

        if 'selected_room' in st.session_state:
            sel_p = st.session_state['selected_room']
            r_data = df_phong[df_phong['phong'] == sel_p].iloc[0]
            st.markdown("---")
            st.subheader(f"🏠 Điều khiển Phòng {sel_p}")
            t_money, t_people, t_history = st.tabs(["💰 Thuê & Tính Tiền", "👥 Nhân Khẩu & CCCD", "📜 Lịch sử"])
            
            with t_money:
                col_L, col_R = st.columns(2)
                with col_L:
                    st.markdown("#### 🖊️ Thông tin Hợp đồng")
                    with st.form(f"edit_f_{sel_p}"):
                        e_cus = st.text_input("Họ tên Khách thuê", value=r_data["khach_thue"])
                        cd1, cd2 = st.columns(2)
                        v_vao = format_date_input(r_data["ngay_vao"]); v_han = format_date_input(r_data["han_hd"])
                        e_vao = cd1.date_input("Ngày vào", value=v_vao)
                        e_han = cd2.date_input("Hạn HĐ", value=v_han)
                        cg1, cg2 = st.columns(2)
                        e_gia = cg1.number_input("Giá thuê", value=int(r_data["gia"]), step=100000)
                        e_coc = cg2.number_input("Tiền cọc", value=int(r_data["tien_coc"]), step=100000)
                        
                        # Ô nhập HOA HỒNG trực tiếp ở Menu 1
                        e_sale = st.text_input("Nhân viên Sale", value=r_data["sale_nhan_vien"])
                        e_hh = st.number_input("Hoa hồng Sale (đ)", value=int(r_data["hoa_hong"]), step=10000)
                        
                        e_st = st.selectbox("Trạng thái", ["Trống", "Đã thuê"], index=1 if r_data["trang_thai"]=="Đã thuê" else 0)
                        ce1, cw1 = st.columns(2)
                        e_dc = ce1.number_input("Điện ĐẦU THÁNG", value=int(r_data["dien_cu"]))
                        e_nc = cw1.number_input("Nước ĐẦU THÁNG", value=int(r_data["nuoc_cu"]))
                        
                        if st.form_submit_button("💾 Lưu hợp đồng & Đồng bộ kỳ hạn"):
                            if IS_ADMIN:
                                c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, sale_nhan_vien=?, hoa_hong=?, trang_thai=?, dien_cu=?, nuoc_cu=? WHERE id=?''', 
                                         (str(e_cus), e_vao.strftime("%d/%m/%Y"), e_han.strftime("%d/%m/%Y"), int(e_gia), int(e_coc), str(e_sale), int(e_hh), str(e_st), int(e_dc), int(e_nc), int(r_data['id'])))
                                conn.commit(); st.success("Đã lưu!"); st.rerun()

                with col_R:
                    st.markdown("#### 💸 Chốt Số & Thu Tiền")
                    is_prepaid = (r_data.get('tien_nha_status') == 'Đã đóng trước')
                    if is_prepaid: st.success("🌟 Đã đóng tiền nhà trước.")
                    if f"temp_bill_{sel_p}" not in st.session_state: st.session_state[f"temp_bill_{sel_p}"] = None
                    with st.form(f"bill_f_{sel_p}"):
                        ce2, cw2 = st.columns(2)
                        n_e = ce2.number_input("Điện CUỐI THÁNG", min_value=int(r_data["dien_cu"]), value=max(int(r_data["dien_cu"]), int(r_data["dien_moi"])))
                        n_w = cw2.number_input("Nước CUỐI THÁNG", min_value=int(r_data["nuoc_cu"]), value=max(int(r_data["nuoc_cu"]), int(r_data["nuoc_moi"])))
                        fee = st.number_input("Phí dịch vụ", value=int(r_data["phi_dich_vu"]))
                        so_thang = st.selectbox("Đóng cho mấy tháng?", [1, 2, 3, 6, 12]) if not is_prepaid else 1
                        if st.form_submit_button("🔔 XUẤT HÓA ĐƠN & QR"):
                            tien_nha = (int(r_data["gia"]) * so_thang) if not is_prepaid else 0
                            tong = tien_nha + (max(0, n_e-int(r_data["dien_cu"])) * GIA_DIEN) + (max(0, n_w-int(r_data["nuoc_cu"])) * GIA_NUOC) + fee
                            st.session_state[f"temp_bill_{sel_p}"] = {"e": int(n_e), "w": int(n_w), "f": int(fee), "so_thang": so_thang, "tong": tong, "prepaid": is_prepaid}
                    if st.session_state[f"temp_bill_{sel_p}"]:
                        bill = st.session_state[f"temp_bill_{sel_p}"]
                        st.code(f"Tổng: {bill['tong']:,} VNĐ")
                        if db_bank_id and db_bank_stk: st.image(tao_link_vietqr(db_bank_id, db_bank_stk, bill['tong'], f"P{sel_p} TT {selected_month} {r_data['khach_thue']}", db_bank_user), width=150)
                        if st.button("🚀 XÁC NHẬN THANH TOÁN"):
                            c.execute('''UPDATE phong_tro SET dien_moi=?, nuoc_moi=?, phi_dich_vu=?, thanh_toan='Đã thanh toán', ngay_thanh_toan=?, tong_tien_bill=?, tien_nha_status='Đã đóng' WHERE id=?''', (bill['e'], bill['w'], bill['f'], datetime.now().strftime("%d/%m/%Y %H:%M"), int(bill['tong']), int(r_data['id'])))
                            conn.commit(); st.rerun()
            with t_people:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.markdown("#### 👑 Chủ Hợp Đồng")
                    df_chu = pd.DataFrame([{"Họ tên": r_data['khach_thue'], "CCCD": r_data['khach_thue_cccd'], "Mặt trước": r_data['khach_thue_img_truoc'], "Mặt sau": r_data['khach_thue_img_sau']}])
                    st.data_editor(df_chu, column_config={"Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn()}, hide_index=True, disabled=True)
                with col_m2:
                    st.markdown("#### 📋 Người ở ghép")
                    df_tv = pd.read_sql_query(f"SELECT id, ten as 'Họ tên', cccd as 'CCCD', img_truoc as 'Mặt trước', img_sau as 'Mặt sau' FROM thanh_vien WHERE phong = '{sel_p}'", conn)
                    if not df_tv.empty: st.dataframe(df_tv.drop(columns=['id']), column_config={"Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn()}, hide_index=True)
            with t_history:
                df_h = pd.read_sql_query(f"SELECT thang_nam as 'Kỳ tháng', khach_thue as 'Khách thuê', ngay_thanh_toan as 'Ngày nộp tiền', tong_tien_bill as 'Số tiền (đ)' FROM phong_tro WHERE phong = '{sel_p}' AND thanh_toan = 'Đã thanh toán' ORDER BY id DESC", conn)
                if df_h.empty: st.info("Chưa có lịch sử.")
                else: df_h['Số tiền (đ)'] = df_h['Số tiền (đ)'].apply(lambda x: f"{x:,.0f}"); st.table(df_h)

# =====================================================================
# MENU 2: QUẢN LÝ BẢO TRÌ
# =====================================================================
elif menu == "2. 🛠️ Quản lý Bảo Trì":
    st.title("🛠️ Sự Cố & Sửa Chữa")
    col_t, col_p = st.columns([1, 2])
    with col_t:
        st.subheader("Ghi nhận Sự cố")
        df_p_all = pd.read_sql_query(f"SELECT DISTINCT phong FROM phong_tro ORDER BY phong", conn)
        with st.form("them_su_co"):
            sc_phong = st.selectbox("Phòng:", ["Khu vực chung"] + df_p_all['phong'].tolist())
            sc_van_de = st.text_area("Mô tả vấn đề"); sc_ngay = st.date_input("Ngày báo")
            if st.form_submit_button("Lưu sự cố") and sc_van_de:
                c.execute('''INSERT INTO bao_tri (phong, van_de, ngay_bao, trang_thai) VALUES (?, ?, ?, ?)''', (sc_phong, sc_van_de, sc_ngay.strftime("%d/%m/%Y"), '🔴 Chưa sửa'))
                conn.commit(); st.rerun()
    with col_p:
        df_bt = load_bao_tri(); t1, t2 = st.tabs(["🔴 Đang chờ", "🟢 Đã sửa & Lịch sử"])
        with t1:
            for _, r in df_bt[df_bt['trang_thai'] == '🔴 Chưa sửa'].iterrows():
                with st.expander(f"📌 {r['phong']} - {r['ngay_bao']}"):
                    st.write(r['van_de'])
                    if IS_ADMIN:
                        with st.form(f"sua_{r['id']}"):
                            cp = st.number_input("Chi phí sửa (VNĐ)", step=50000)
                            if st.form_submit_button("✅ XONG"):
                                c.execute('''UPDATE bao_tri SET trang_thai='🟢 Đã sửa', chi_phi=? WHERE id=?''', (int(cp), r['id']))
                                conn.commit(); st.rerun()

# =====================================================================
# MENU 3: BÁO CÁO TÀI CHÍNH THÁNG
# =====================================================================
elif menu == "3. Báo Cáo Tài Chính Tháng":
    thang_tk = hien_thi_header_chot_ky("📊 Quản Lý Thu Chi Tháng", danh_sach_thang_don, danh_sach_nam, current_month, current_year)
    df_raw_rooms = load_phong(thang_tk)
    df_raw_expenses = load_chi_phi(thang_tk)
    
    # 1. THỐNG KÊ SALE (Dữ liệu từ Menu 1)
    st.subheader("👤 1. Thống kê Hiệu suất Sale")
    if not df_raw_rooms.empty:
        df_sale_sum = df_raw_rooms[df_raw_rooms['trang_thai'] == 'Đã thuê'].groupby('sale_nhan_vien').agg(
            Tong_Phong=('phong', 'count'),
            Tong_HH=('hoa_hong', 'sum')
        ).reset_index()
        df_sale_sum.columns = ["Tên nhân viên", "Số phòng đã chốt", "Tổng hoa hồng (đ)"]
        st.table(df_sale_sum)
    else:
        st.info("Chưa có dữ liệu phòng tháng này.")

    # 2. BẢNG CHI PHÍ TÒA NHÀ (Nút Xóa & Chỉnh sửa)
    st.subheader("💸 2. Bảng Chi Phí Tòa Nhà")
    if not df_raw_expenses.empty:
        df_exp_edit = df_raw_expenses.copy()
        df_exp_edit['Xóa'] = False
        edited_expenses = st.data_editor(
            df_exp_edit[['Xóa', 'id', 'loai', 'hang_muc', 'so_tien']],
            column_config={
                "Xóa": st.column_config.CheckboxColumn("🗑️ Xóa"),
                "id": None, "loai": "Loại", "hang_muc": "Ghi chú", 
                "so_tien": st.column_config.NumberColumn("Số tiền (đ)")
            },
            hide_index=True, use_container_width=True, key="expense_editor"
        )
    else:
        st.info("Chưa có chi phí.")
        edited_expenses = pd.DataFrame(columns=['Xóa', 'id', 'loai', 'hang_muc', 'so_tien'])

    # TÍNH TOÁN DASHBOARD (REAL-TIME)
    total_thu = 0
    total_hh = 0
    if not df_raw_rooms.empty:
        # Tiền thu chỉ tính từ phòng đã thanh toán
        total_thu = df_raw_rooms[df_raw_rooms['thanh_toan'] == 'Đã thanh toán']['tong_tien_bill'].sum()
        # Tổng hoa hồng sale là chi phí
        total_hh = df_raw_rooms['hoa_hong'].sum()
    
    # Tiền chi tòa nhà (Chỉ tính dòng không bị tích Xóa)
    total_chi_tn = edited_expenses[edited_expenses['Xóa'] == False]['so_tien'].sum() if not edited_expenses.empty else 0

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG THU", f"{total_thu:,.0f} đ")
    c2.metric("💸 TỔNG CHI (TN + Sale)", f"{total_chi_tn + total_hh:,.0f} đ")
    c3.metric("📈 LÃI RÒNG", f"{total_thu - (total_chi_tn + total_hh):,.0f} đ")

    # NÚT LƯU CẬP NHẬT
    if IS_ADMIN:
        if st.button("🚀 LƯU THAY ĐỔI CHI PHÍ TÒA NHÀ", use_container_width=True, type="primary"):
            c.execute(f"DELETE FROM chi_phi WHERE thang_nam = '{thang_tk}'")
            for _, row in edited_expenses.iterrows():
                if not row['Xóa'] and row['so_tien'] > 0:
                    c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?,?,?,?,?)''', 
                             (thang_tk, str(row['loai']), str(row['hang_muc']), int(row['so_tien']), datetime.now().strftime("%d/%m/%Y")))
            conn.commit(); st.success("Đã cập nhật!"); st.rerun()

    with st.expander("➕ Thêm nhanh chi phí mới"):
        with st.form("quick_add"):
            cl = st.selectbox("Loại", ["Tiền Điện Toàn Nhà", "Tiền Nước Toàn Nhà", "Rác", "Net", "Sửa chữa", "Khác"])
            ch, ct = st.text_input("Ghi chú"), st.number_input("Số tiền", step=50000)
            if st.form_submit_button("Lưu nhanh"):
                c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?,?,?,?,?)''', (thang_tk, cl, ch, int(ct), datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.rerun()

# =====================================================================
# MENU 4: BÁO CÁO TÀI CHÍNH NĂM (GIỮ NGUYÊN)
# =====================================================================
elif menu == "4. Báo Cáo Tài Chính Năm":
    nam_n = st.selectbox("📅 Chọn Năm:", danh_sach_nam, index=danh_sach_nam.index(str(current_year)))
    y_thu_nha, y_thu_dien, y_thu_nuoc, y_thu_dv = 0, 0, 0, 0
    y_chi_dien, y_chi_nuoc, y_chi_dv, y_chi_sua, y_chi_khac, y_chi_hh = 0, 0, 0, 0, 0, 0
    data_nam_detailed = []; all_rented_rooms = []
    for t in range(1, 13):
        ts = f"{str(t).zfill(2)}/{nam_n}"
        df_p, df_c = load_phong(ts), load_chi_phi(ts)
        df_paid = df_p[df_p['thanh_toan'] == 'Đã thanh toán']; df_rented = df_p[df_p['trang_thai'] == 'Đã thuê']
        all_rented_rooms.append(df_rented)
        m_thu_dien = sum([(max(0, r['dien_moi']-r['dien_cu']) * GIA_DIEN) for _, r in df_paid.iterrows()])
        m_thu_nuoc = sum([(max(0, r['nuoc_moi']-r['nuoc_cu']) * GIA_NUOC) for _, r in df_paid.iterrows()])
        m_thu_dv = df_paid['phi_dich_vu'].sum(); m_thu_nha = df_paid['tong_tien_bill'].sum() - (m_thu_dien + m_thu_nuoc + m_thu_dv)
        m_chi_hh = df_rented['hoa_hong'].sum(); m_chi_dien = df_c[df_c['loai'] == 'Tiền Điện Toàn Nhà']['so_tien'].sum()
        m_chi_nuoc = df_c[df_c['loai'] == 'Tiền Nước Toàn Nhà']['so_tien'].sum()
        m_chi_dv = df_c[df_c['loai'].isin(['Rác', 'Net'])]['so_tien'].sum(); m_chi_sua = df_c[df_c['loai'] == 'Sửa chữa']['so_tien'].sum(); m_chi_khac = df_c[df_c['loai'] == 'Khác']['so_tien'].sum()
        y_thu_nha += m_thu_nha; y_thu_dien += m_thu_dien; y_thu_nuoc += m_thu_nuoc; y_thu_dv += m_thu_dv
        y_chi_dien += m_chi_dien; y_chi_nuoc += m_chi_nuoc; y_chi_dv += m_chi_dv; y_chi_sua += m_chi_sua; y_chi_khac += m_chi_khac; y_chi_hh += m_chi_hh
        m_total_thu = m_thu_nha + m_thu_dien + m_thu_nuoc + m_thu_dv; m_total_chi = m_chi_dien + m_chi_nuoc + m_chi_dv + m_chi_sua + m_chi_khac + m_chi_hh
        data_nam_detailed.append({"Tháng": f"Tháng {t}", "Thu": f"{m_total_thu:,.0f}", "Chi": f"{m_total_chi:,.0f}", "Lãi": f"{m_total_thu - m_total_chi:,.0f}"})
    total_y_thu, total_y_chi = y_thu_nha + y_thu_dien + y_thu_nuoc + y_thu_dv, y_chi_dien + y_chi_nuoc + y_chi_dv + y_chi_sua + y_chi_khac + y_chi_hh
    c1, c2, c3 = st.columns(3)
    c1.metric("🌟 TỔNG THU NĂM", f"{total_y_thu:,.0f} đ"); c2.metric("🔥 TỔNG CHI NĂM", f"{total_y_chi:,.0f} đ"); c3.metric("🎯 LỢI NHUẬN NĂM", f"{total_y_thu - total_y_chi:,.0f} đ")
    st.markdown("#### 🏆 Bảng Thành Tích Sale Năm")
    if all_rented_rooms:
        df_all_year = pd.concat(all_rented_rooms); df_sale_y = df_all_year[df_all_year['sale_nhan_vien'].str.strip() != ""].copy()
        if not df_sale_y.empty:
            st_sale_y = df_sale_y.groupby('sale_nhan_vien').agg(Tong_Phong=('phong', 'count'), Tong_HH=('hoa_hong', 'sum')).reset_index()
            st_sale_y.columns = ["Tên nhân viên", "Tổng phòng sale", "Tổng hoa hồng nhận (đ)"]
            st_sale_y["Tổng hoa hồng nhận (đ)"] = st_sale_y["Tổng hoa hồng nhận (đ)"].apply(lambda x: f"{x:,.0f}"); st.table(st_sale_y)
    st.markdown("#### 📝 Tổng kết năm")
    st.table(pd.DataFrame([
        {"Hạng mục": "🏡 Tiền Nhà Trọ", "Tổng Thu": f"{y_thu_nha:,.0f}", "Tổng Chi": "-", "Chênh lệch": f"{y_thu_nha:,.0f}"},
        {"Hạng mục": "⚡ Tiền Điện", "Tổng Thu": f"{y_thu_dien:,.0f}", "Tổng Chi": f"{y_chi_dien:,.0f}", "Chênh lệch": f"{y_thu_dien - y_chi_dien:,.0f}"},
        {"Hạng mục": "💧 Tiền Nước", "Tổng Thu": f"{y_thu_nuoc:,.0f}", "Tổng Chi": f"{y_chi_nuoc:,.0f}", "Chênh lệch": f"{y_thu_nuoc - y_chi_nuoc:,.0f}"},
        {"Hạng mục": "🤝 Hoa hồng Sale", "Tổng Thu": "-", "Tổng Chi": f"{y_chi_hh:,.0f}", "Chênh lệch": f"{-y_chi_hh:,.0f}"},
        {"Hạng mục": "🛠️ Phí DV / Khác", "Tổng Thu": f"{y_thu_dv:,.0f}", "Tổng Chi": f"{y_chi_dv + y_chi_khac:,.0f}", "Chênh lệch": f"{y_thu_dv - (y_chi_dv + y_chi_khac):,.0f}"},
        {"Hạng mục": "🔨 Sửa chữa", "Tổng Thu": "-", "Tổng Chi": f"{y_chi_sua:,.0f}", "Chênh lệch": f"{-y_chi_sua:,.0f}"},
    ])); st.dataframe(pd.DataFrame(data_nam_detailed), use_container_width=True, hide_index=True)
