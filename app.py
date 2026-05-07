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
        khach_thue_ngay_sinh TEXT, khach_thue_cccd TEXT, khach_thue_que_quan TEXT, khach_thue_img_truoc TEXT, khach_thue_img_sau TEXT,
        phi_dich_vu INTEGER DEFAULT 0
    )''')
    try: c.execute("ALTER TABLE phong_tro ADD COLUMN phi_dich_vu INTEGER DEFAULT 0")
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
# 2. MENU SIDEBAR
# ==========================================
st.sidebar.title("🏢 MENU QUẢN LÝ")
st.sidebar.success(f"👤: **{st.session_state['name']}**\n🔑: **{st.session_state['role']}**")

if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state['logged_in'] = False
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio("Chọn chức năng:", ["1. Quản lý Phòng & Tính tiền", "2. Kiểm soát Thành viên", "3. 🛠️ Quản lý Bảo Trì", "4. Báo Cáo Tài Chính Tháng", "5. Báo Cáo Tài Chính Năm"])

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

def hien_thi_header_chot_ky(tieu_de):
    col_title, col_chon_thang, col_chon_nam = st.columns([2.5, 0.5, 0.5])
    with col_title: st.title(tieu_de)
    with col_chon_thang:
        thang_chon = st.selectbox("Tháng:", danh_sach_thang_don, index=danh_sach_thang_don.index(current_month))
    with col_chon_nam:
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
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, gia, dien_cu, nuoc_cu, trang_thai, thanh_toan, phi_dich_vu) VALUES (?,?,?,?,?,?,?,?,?)''', (selected_month, p, "", 2500000, 0, 0, "Trống", "Chưa", 0))
                conn.commit(); st.rerun()
        with c_b:
            ky_truoc = tinh_thang_truoc(selected_month)
            if st.button(f"✨ Sao chép từ kỳ trước ({ky_truoc})"):
                df_truoc = load_phong(ky_truoc)
                for _, r in df_truoc.iterrows():
                    d_c = r['dien_moi'] if r['dien_moi'] > r['dien_cu'] else r['dien_cu']
                    n_c = r['nuoc_moi'] if r['nuoc_moi'] > r['nuoc_cu'] else r['nuoc_cu']
                    c.execute('''INSERT INTO phong_tro (thang_nam, phong, khach_thue, ngay_vao, han_hd, gia, tien_coc, dien_cu, nuoc_cu, trang_thai, thanh_toan, phi_dich_vu) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (selected_month, r['phong'], r['khach_thue'], r['ngay_vao'], r['han_hd'], r['gia'], r['tien_coc'], d_c, n_c, r['trang_thai'], "Chưa", 0))
                conn.commit(); st.rerun()

    if not df_thang_nay.empty:
        df_display = df_thang_nay.sort_values(by='phong').copy()
        if IS_ADMIN:
            st.info("💡 Sửa nhanh trực tiếp trên bảng và nhấn 'Lưu Thay Đổi Bảng'.")
            edited_df = st.data_editor(
                df_display.rename(columns={"phong": "Phòng", "khach_thue": "Khách thuê", "ngay_vao": "Ngày Vào", "han_hd": "Hạn HĐ", "gia": "Giá thuê", "tien_coc": "Tiền Cọc", "dien_cu": "Đầu(Điện)", "nuoc_cu": "Đầu(Nước)", "trang_thai": "Trạng thái", "thanh_toan": "Thanh Toán"}).drop(columns=['id', 'thang_nam', 'dien_moi', 'nuoc_moi', 'khach_thue_ngay_sinh', 'khach_thue_cccd', 'khach_thue_que_quan', 'khach_thue_img_truoc', 'khach_thue_img_sau', 'phi_dich_vu'], errors='ignore'),
                column_config={"Trạng thái": st.column_config.SelectboxColumn(options=["Trống", "Đã thuê"]), "Thanh Toán": st.column_config.SelectboxColumn(options=["Chưa", "Đã thanh toán"])},
                use_container_width=True, height=(len(df_display)*35)+40, hide_index=True
            )
            if st.button("💾 Lưu Thay Đổi Bảng", type="primary"):
                for idx, row in edited_df.iterrows():
                    orig_id = df_display.iloc[idx]['id']
                    def to_int(val): return int(val) if pd.notnull(val) else 0
                    c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, dien_cu=?, nuoc_cu=?, trang_thai=?, thanh_toan=? WHERE id=?''', 
                              (str(row['Khách thuê']), str(row['Ngày Vào']), str(row['Hạn HĐ']), to_int(row['Giá thuê']), to_int(row['Tiền Cọc']), to_int(row['Đầu(Điện)']), to_int(row['Đầu(Nước)']), str(row['Trạng thái']), str(row['Thanh Toán']), int(orig_id)))
                conn.commit(); st.success("Đã cập nhật!"); st.rerun()
        else:
            st.dataframe(df_display.drop(columns=['id','thang_nam','dien_moi','nuoc_moi','phi_dich_vu'], errors='ignore'), use_container_width=True, hide_index=True)

        st.markdown("---")
        selected_room = st.selectbox("👉 Chọn phòng thao tác:", ["-- Chọn phòng --"] + df_thang_nay["phong"].tolist())
        if selected_room != "-- Chọn phòng --":
            r_data = df_thang_nay[df_thang_nay["phong"] == selected_room].iloc[0]
            col_L, col_R = st.columns(2)
            with col_L:
                st.markdown("### 🖊️ Cập nhật Thông tin")
                with st.form("edit_f"):
                    e_cus = st.text_input("Khách thuê", value=r_data["khach_thue"])
                    cd1, cd2 = st.columns(2)
                    v_vao, v_han = format_date_input(r_data["ngay_vao"]), format_date_input(r_data["han_hd"])
                    e_vao = cd1.date_input("Ngày vào", value=v_vao, format="DD/MM/YYYY")
                    e_han = cd2.date_input("Hạn HĐ", value=v_han, format="DD/MM/YYYY")
                    cg1, cg2 = st.columns(2)
                    e_gia = cg1.number_input("Giá thuê", value=int(r_data["gia"]), step=100000)
                    e_coc = cg2.number_input("Tiền cọc", value=int(r_data["tien_coc"]), step=100000)
                    e_st = st.selectbox("Trạng thái", ["Trống", "Đã thuê"], index=1 if r_data["trang_thai"]=="Đã thuê" else 0)
                    ce1, cw1 = st.columns(2)
                    e_dc = ce1.number_input("Điện ĐẦU THÁNG", value=int(r_data["dien_cu"]))
                    e_nc = cw1.number_input("Nước ĐẦU THÁNG", value=int(r_data["nuoc_cu"]))
                    if st.form_submit_button("Lưu thông tin cơ bản"):
                        if IS_ADMIN:
                            c.execute('''UPDATE phong_tro SET khach_thue=?, ngay_vao=?, han_hd=?, gia=?, tien_coc=?, trang_thai=?, dien_cu=?, nuoc_cu=? WHERE id=?''', 
                                      (str(e_cus), e_vao.strftime("%d/%m/%Y") if e_vao else "", e_han.strftime("%d/%m/%Y") if e_han else "", int(e_gia), int(e_coc), str(e_st), int(e_dc), int(e_nc), int(r_data['id'])))
                            conn.commit(); st.rerun()

            with col_R:
                st.markdown("### 💸 Bước 1: Chốt Số & Xem Hóa Đơn")
                if f"temp_bill_{selected_room}" not in st.session_state: st.session_state[f"temp_bill_{selected_room}"] = None

                with st.form("calc_bill_f"):
                    ce2, cw2 = st.columns(2)
                    n_e = ce2.number_input("Điện CUỐI THÁNG", min_value=int(r_data["dien_cu"]), value=max(int(r_data["dien_cu"]), int(r_data["dien_moi"])))
                    n_w = cw2.number_input("Nước CUỐI THÁNG", min_value=int(r_data["nuoc_cu"]), value=max(int(r_data["nuoc_cu"]), int(r_data["nuoc_moi"])))
                    fee = st.number_input("Phí dịch vụ (Rác, Net...)", value=int(r_data["phi_dich_vu"]) if r_data["phi_dich_vu"] > 0 else 0)
                    if st.form_submit_button("🔔 XUẤT HÓA ĐƠN & QR"):
                        st.session_state[f"temp_bill_{selected_room}"] = {"e": int(n_e), "w": int(n_w), "f": int(fee)}

                if st.session_state[f"temp_bill_{selected_room}"]:
                    bill = st.session_state[f"temp_bill_{selected_room}"]
                    s_dien, s_nuoc = bill['e'] - int(r_data["dien_cu"]), bill['w'] - int(r_data["nuoc_cu"])
                    tong = int(r_data["gia"]) + (s_dien * GIA_DIEN) + (s_nuoc * GIA_NUOC) + bill['f']
                    
                    st.success(f"HÓA ĐƠN P.{selected_room}")
                    col_t, col_q = st.columns([1.5, 1])
                    with col_t:
                        st.code(f"Tiền nhà: {int(r_data['gia']):,} đ\nĐiện: {s_dien} x {GIA_DIEN:,} = {s_dien*GIA_DIEN:,} đ\nNước: {s_nuoc} x {GIA_NUOC:,} = {s_nuoc*GIA_NUOC:,} đ\nDịch vụ: {bill['f']:,} đ\n>> TỔNG: {tong:,} VNĐ")
                    with col_q:
                        if db_bank_id and db_bank_stk:
                            st.image(tao_link_vietqr(db_bank_id, db_bank_stk, tong, f"P{selected_room} TT THANG {selected_month.replace('/','')}"), width=160)
                    
                    st.markdown("### 💸 Bước 2: Xác nhận thu tiền")
                    with st.form("final_confirm_f"):
                        e_tt = st.radio("Trạng thái thu tiền thực tế:", ["Chưa thanh toán ❌", "Đã thanh toán ✅"], index=1 if r_data["thanh_toan"]=="Đã thanh toán" else 0, horizontal=True)
                        if st.form_submit_button("🚀 XÁC NHẬN HOÀN TẤT & CHỐT SỔ"):
                            if IS_ADMIN:
                                status_db = "Đã thanh toán" if "Đã" in e_tt else "Chưa"
                                c.execute('''UPDATE phong_tro SET dien_moi=?, nuoc_moi=?, phi_dich_vu=?, thanh_toan=? WHERE id=?''', (bill['e'], bill['w'], bill['f'], status_db, int(r_data['id'])))
                                conn.commit(); st.session_state[f"temp_bill_{selected_room}"] = None; st.success("Đã cập nhật!"); st.rerun()

# =====================================================================
# MENU 2: KIỂM SOÁT THÀNH VIÊN
# =====================================================================
elif menu == "2. Kiểm soát Thành viên":
    st.title("👥 Nhân Khẩu & 2 Mặt CCCD")
    thang_ht = f"{current_month}/{current_year}"
    df_p = pd.read_sql_query(f"SELECT * FROM phong_tro WHERE thang_nam = '{thang_ht}' AND trang_thai='Đã thuê' ORDER BY phong", conn)
    if not df_p.empty:
        sel_room = st.selectbox("👉 Chọn Phòng:", df_p['phong'].tolist())
        r_data = df_p[df_p['phong'] == sel_room].iloc[0]
        st.markdown(f"### 👑 Chủ Hợp Đồng - P.{sel_room}")
        df_chu = pd.DataFrame([{"Họ tên": r_data['khach_thue'], "Ngày sinh": r_data['khach_thue_ngay_sinh'], "CCCD": r_data['khach_thue_cccd'], "Quê quán": r_data['khach_thue_que_quan'], "Mặt trước": r_data['khach_thue_img_truoc'], "Mặt sau": r_data['khach_thue_img_sau']}])
        st.data_editor(df_chu, column_config={"Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn()}, hide_index=True, use_container_width=True, disabled=["Mặt trước", "Mặt sau"])
        if IS_ADMIN:
            with st.expander("📸 Cập nhật CCCD Chủ HĐ"):
                with st.form("f_chu_2"):
                    c1, c2 = st.columns(2)
                    n_ten, n_ns = c1.text_input("Họ tên", value=r_data['khach_thue']), c1.text_input("Ngày sinh", value=r_data['khach_thue_ngay_sinh'])
                    n_cc, n_que = c2.text_input("CCCD", value=r_data['khach_thue_cccd']), c2.text_input("Quê quán", value=r_data['khach_thue_que_quan'])
                    up_t, up_s = st.file_uploader("Mặt Trước", key="ut"), st.file_uploader("Mặt Sau", key="us")
                    if st.form_submit_button("Lưu"):
                        it = convert_image_to_base64(up_t) if up_t else r_data['khach_thue_img_truoc']
                        isau = convert_image_to_base64(up_s) if up_s else r_data['khach_thue_img_sau']
                        c.execute('''UPDATE phong_tro SET khach_thue=?, khach_thue_ngay_sinh=?, khach_thue_cccd=?, khach_thue_que_quan=?, khach_thue_img_truoc=?, khach_thue_img_sau=? WHERE id=?''', (n_ten, n_ns, n_cc, n_que, it, isau, int(r_data['id'])))
                        conn.commit(); st.rerun()
        st.markdown("---")
        st.markdown(f"### 📋 Người ở ghép - P.{sel_room}")
        if IS_ADMIN:
            with st.expander("➕ Thêm thành viên"):
                with st.form("f_tv"):
                    t1, t2 = st.columns(2)
                    t_ten, t_ns = t1.text_input("Họ tên"), t1.text_input("Ngày sinh")
                    t_cc, t_que = t2.text_input("CCCD"), t2.text_input("Quê quán")
                    t_ut, t_us = st.file_uploader("Ảnh Trước"), st.file_uploader("Ảnh Sau")
                    if st.form_submit_button("Thêm"):
                        c.execute('''INSERT INTO thanh_vien (phong, ten, ngay_sinh, cccd, que_quan, img_truoc, img_sau) VALUES (?,?,?,?,?,?,?)''', (sel_room, t_ten, t_ns, t_cc, t_que, convert_image_to_base64(t_ut), convert_image_to_base64(t_us)))
                        conn.commit(); st.rerun()
        df_tv = pd.read_sql_query(f"SELECT id, ten as 'Họ tên', ngay_sinh as 'Ngày sinh', cccd as 'CCCD', que_quan as 'Quê quán', img_truoc as 'Mặt trước', img_sau as 'Mặt sau' FROM thanh_vien WHERE phong = '{sel_room}'", conn)
        if not df_tv.empty:
            if IS_ADMIN:
                df_tv['Xóa'] = False
                e_tv = st.data_editor(df_tv, column_config={"id": None, "Mặt trước": st.column_config.ImageColumn(), "Mặt sau": st.column_config.ImageColumn(), "Xóa": st.column_config.CheckboxColumn("🗑")}, hide_index=True, use_container_width=True)
                if st.button("💾 Lưu thay đổi danh sách"):
                    for _, row in e_tv.iterrows():
                        if row['Xóa']: c.execute("DELETE FROM thanh_vien WHERE id=?", (int(row['id']),))
                        else: c.execute("UPDATE thanh_vien SET ten=?, ngay_sinh=?, cccd=?, que_quan=? WHERE id=?", (row['Họ tên'], row['Ngày sinh'], row['CCCD'], row['Quê quán'], int(row['id'])))
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
                    st.write(r['van_de'])
                    if IS_ADMIN:
                        with st.form(f"sua_{r['id']}"):
                            cp = st.number_input("Chi phí sửa (VNĐ)", step=50000)
                            if st.form_submit_button("✅ XONG"):
                                c.execute('''UPDATE bao_tri SET trang_thai='🟢 Đã sửa', chi_phi=? WHERE id=?''', (int(cp), r['id']))
                                if cp > 0: c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?, ?, ?, ?, ?)''', (f"{current_month}/{current_year}", "Sửa chữa", f"P.{r['phong']}: {r['van_de']}", int(cp), datetime.now().strftime("%d/%m/%Y")))
                                conn.commit(); st.rerun()
        with tab2:
            df_da = df_bt[df_bt['trang_thai'] == '🟢 Đã sửa']
            if not df_da.empty and IS_ADMIN:
                df_da['Xóa'] = False
                ed_bt = st.data_editor(df_da, column_config={"id": None, "da_hach_toan": None, "Xóa": st.column_config.CheckboxColumn("🗑")}, hide_index=True)
                if st.button("💾 Lưu thay đổi bảo trì"):
                    for _, row in ed_bt.iterrows():
                        if row['Xóa']: c.execute("DELETE FROM bao_tri WHERE id=?", (row['id'],))
                        else: c.execute("UPDATE bao_tri SET phong=?, van_de=?, chi_phi=? WHERE id=?", (row['phong'], row['van_de'], int(row['chi_phi']), row['id']))
                    conn.commit(); st.rerun()
            else: st.dataframe(df_da.drop(columns=['id']), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 4: BÁO CÁO TÀI CHÍNH THÁNG (CẬP NHẬT CHIA KHOẢN CỤ THỂ)
# =====================================================================
elif menu == "4. Báo Cáo Tài Chính Tháng":
    thang_tk = hien_thi_header_chot_ky("📊 Báo Cáo Tài Chính Tháng")
    df_dt = load_phong(thang_tk); df_chi = load_chi_phi(thang_tk)
    
    # 1. TÍNH THU TỪ KHÁCH (CHỈ LẤY PHÒNG ĐÃ THANH TOÁN)
    thu_tien_nha, thu_dien, thu_nuoc, thu_dv = 0, 0, 0, 0
    if not df_dt.empty:
        df_paid = df_dt[df_dt['thanh_toan'] == 'Đã thanh toán']
        thu_tien_nha = df_paid['gia'].sum()
        thu_dien = sum([(max(0, r['dien_moi']-r['dien_cu']) * GIA_DIEN) for _, r in df_paid.iterrows()])
        thu_nuoc = sum([(max(0, r['nuoc_moi']-r['nuoc_cu']) * GIA_NUOC) for _, r in df_paid.iterrows()])
        thu_dv = df_paid['phi_dich_vu'].sum()

    # 2. TÍNH CHI TÒA NHÀ (LẤY TỪ BẢNG CHI PHÍ)
    chi_dien, chi_nuoc, chi_dv, chi_sua, chi_khac = 0, 0, 0, 0, 0
    if not df_chi.empty:
        chi_dien = df_chi[df_chi['loai'] == 'Tiền Điện Toàn Nhà']['so_tien'].sum()
        chi_nuoc = df_chi[df_chi['loai'] == 'Tiền Nước Toàn Nhà']['so_tien'].sum()
        chi_dv = df_chi[df_chi['loai'].isin(['Rác', 'Net'])]['so_tien'].sum()
        chi_sua = df_chi[df_chi['loai'] == 'Sửa chữa']['so_tien'].sum()
        chi_khac = df_chi[df_chi['loai'] == 'Khác']['so_tien'].sum()

    # 3. HIỂN THỊ METRICS TỔNG QUÁT
    t_thu = thu_tien_nha + thu_dien + thu_nuoc + thu_dv
    t_chi = chi_dien + chi_nuoc + chi_dv + chi_sua + chi_khac
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG THU (Đã thu)", f"{t_thu:,.0f} đ")
    c2.metric("💸 TỔNG CHI", f"{t_chi:,.0f} đ")
    c3.metric("📈 LỢI NHUẬN THỰC", f"{t_thu - t_chi:,.0f} đ", delta_color="normal")

    st.markdown("---")
    st.subheader("🔍 So sánh Kiểm soát Dòng tiền")
    
    # BẢNG SO SÁNH CHI TIẾT
    data_compare = [
        {"Khoản mục": "🏡 Tiền Nhà Trọ", "Thu từ khách": f"{thu_tien_nha:,.0f}", "Chi tòa nhà": "-", "Chênh lệch": f"{thu_tien_nha:,.0f}"},
        {"Khoản mục": "⚡ Tiền Điện", "Thu từ khách": f"{thu_dien:,.0f}", "Chi tòa nhà": f"{chi_dien:,.0f}", "Chênh lệch": f"{thu_dien - chi_dien:,.0f}"},
        {"Khoản mục": "💧 Tiền Nước", "Thu từ khách": f"{thu_nuoc:,.0f}", "Chi tòa nhà": f"{chi_nuoc:,.0f}", "Chênh lệch": f"{thu_nuoc - chi_nuoc:,.0f}"},
        {"Khoản mục": "🛠️ Phí Dịch Vụ / Khác", "Thu từ khách": f"{thu_dv:,.0f}", "Chi tòa nhà": f"{chi_dv + chi_khac:,.0f}", "Chênh lệch": f"{thu_dv - (chi_dv + chi_khac):,.0f}"},
        {"Khoản mục": "🔨 Chi phí Sửa chữa", "Thu từ khách": "-", "Chi tòa nhà": f"{chi_sua:,.0f}", "Chênh lệch": f"{-chi_sua:,.0f}"},
    ]
    st.table(pd.DataFrame(data_compare))

    st.markdown("---")
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("📉 Quản lý Chi phí Tòa nhà")
        if IS_ADMIN:
            with st.expander("➕ Thêm khoản chi mới"):
                with st.form("t_cp"):
                    cl = st.selectbox("Loại", ["Tiền Điện Toàn Nhà", "Tiền Nước Toàn Nhà", "Rác", "Net", "Sửa chữa", "Khác"])
                    ch, ct = st.text_input("Ghi chú"), st.number_input("Số tiền", step=50000)
                    if st.form_submit_button("Lưu khoản chi"):
                        c.execute('''INSERT INTO chi_phi (thang_nam, loai, hang_muc, so_tien, ngay_nhap) VALUES (?,?,?,?,?)''', (thang_tk, cl, ch, int(ct), datetime.now().strftime("%d/%m/%Y")))
                        conn.commit(); st.rerun()
            if not df_chi.empty:
                df_chi['Xóa'] = False
                ed_cp = st.data_editor(df_chi, column_config={"id": None, "thang_nam": None, "Xóa": st.column_config.CheckboxColumn("🗑")}, hide_index=True, use_container_width=True)
                if st.button("💾 Cập nhật danh sách chi"):
                    for _, r in ed_cp.iterrows():
                        if r['Xóa']: c.execute("DELETE FROM chi_phi WHERE id=?", (r['id'],))
                        else: c.execute("UPDATE chi_phi SET loai=?, hang_muc=?, so_tien=? WHERE id=?", (r['loai'], r['hang_muc'], int(r['so_tien']), r['id']))
                    conn.commit(); st.rerun()
        else: st.dataframe(df_chi.drop(columns=['id','thang_nam']), use_container_width=True, hide_index=True)

# =====================================================================
# MENU 5: BÁO CÁO TÀI CHÍNH NĂM
# =====================================================================
elif menu == "5. Báo Cáo Tài Chính Năm":
    nam_n = st.selectbox("📅 Chọn Năm:", danh_sach_nam, index=danh_sach_nam.index(str(current_year)))
    tong_thu_nam, tong_chi_nam, data_nam = 0, 0, []
    for t in range(1, 13):
        ts = f"{str(t).zfill(2)}/{nam_n}"
        df_p_n, df_c_n = load_phong(ts), load_chi_phi(ts)
        thu_t = sum([(r['gia'] + max(0, r['dien_moi']-r['dien_cu'])*GIA_DIEN + max(0, r['nuoc_moi']-r['nuoc_cu'])*GIA_NUOC + r['phi_dich_vu']) for _, r in df_p_n[df_p_n['thanh_toan'] == 'Đã thanh toán'].iterrows()]) if not df_p_n.empty else 0
        chi_t = df_c_n['so_tien'].sum() if not df_c_n.empty else 0
        tong_thu_nam += thu_t; tong_chi_nam += chi_t
        data_nam.append({"Tháng": f"Tháng {t}", "Thu": f"{thu_t:,.0f} đ", "Chi": f"{chi_t:,.0f} đ", "Lãi": f"{(thu_t-chi_t):,.0f} đ"})
    c1, c2, c3 = st.columns(3)
    c1.metric("🌟 TỔNG THU NĂM", f"{tong_thu_nam:,.0f} VNĐ"); c2.metric("🔥 TỔNG CHI NĂM", f"{tong_chi_nam:,.0f} VNĐ"); c3.metric("🎯 LỢI NHUẬN NĂM", f"{(tong_thu_nam - tong_chi_nam):,.0f} VNĐ")
    st.dataframe(pd.DataFrame(data_nam), use_container_width=True, hide_index=True)
