import streamlit as st
import google.generativeai as genai
import re
import json
import os
import requests
import ftplib

# ==========================================
# 1. SETUP TEMA & HALAMAN
# ==========================================
st.set_page_config(page_title="URadio Studio", page_icon="🎙️", layout="centered")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #1e90ff !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #0077ea !important;
        box-shadow: 0px 4px 15px rgba(30, 144, 255, 0.4) !important;
    }
    h1, h2, h3 { color: #1e90ff !important; }
    .stTextInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #1e90ff !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE PEGAWAI & LOGIN SYSTEM
# ==========================================
USERS = {
    "1111": {
        "nama": "Agustian",
        "role": "Pemimpin Redaksi",
        "foto": "agustian.jpg", 
        "voice_id": "" 
    },
    "2222": {
        "nama": "Ki Sandi Suryadinata",
        "role": "Penyiar",
        "foto": "sandi.jpg", 
        "voice_id": "wxuHKpeHPOQlfryZit7t" 
    }
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

# ==========================================
# 3. FUNGSI-FUNGSI PENDUKUNG
# ==========================================
DB_FILE = "database_berita.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"status": "kosong", "info_mentah": "", "naskah": "", "penulis": "", "voice_id_penulis": ""}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

db = load_db()

def bersihkan_untuk_audio(teks):
    teks = re.sub(r'\[.*?\]', '', teks)
    teks = re.sub(r'\(.*?\)', '', teks)
    teks = re.sub(r'[*#_~`>]', '', teks)
    teks = re.sub(r'^(Berikut|Ini).*?:\n', '', teks, flags=re.IGNORECASE)
    return teks.strip()

# --- KURIR FTP ---
def kirim_ke_radio(file_lokal, nama_file_tujuan):
    import requests
    import streamlit as st
    
    try:
        # Buka browser virtual (session) biar cookie login kesimpan otomatis
        sesi = requests.Session()
        
        # Nyamar pake browser Chrome PC persis kayak cURL lu
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
        }
        
        # --- PROSES 1: LOGIN DIAM-DIAM ---
        url_login = "https://mediacp-eu1.arenastreaming.com:2020/login"
        data_login = {
            "username": st.secrets["WEB_USER"], 
            "password": st.secrets["WEB_PASS"]
        }
        
        # Pancing buka halaman login buat narik Cookie awal
        sesi.get(url_login, headers=headers)
        # Tembak form loginnya
        sesi.post(url_login, data=data_login, headers=headers)
        
        # --- PROSES 2: UPLOAD LANGSUNG KE PLAYLIST1 ---
        url_upload = "https://mediacp-eu1.arenastreaming.com:2020/controller/Media/8/uploadTrack"
        
        # Targetkan folder tujuan (Rahasianya ada di sini)
        payload = {'path': '/Playlist1'}
        
        # Tambahin referer biar dikira ngeklik dari dalam web
        headers_upload = headers.copy()
        headers_upload['Origin'] = 'https://mediacp-eu1.arenastreaming.com:2020'
        headers_upload['Referer'] = 'https://mediacp-eu1.arenastreaming.com:2020/controller/Media/8'
        
        # Siapin dan kirim file
        with open(file_lokal, 'rb') as f:
            # Kata 'track' diambil dari form-data cURL lu
            files = {'track': (nama_file_tujuan, f, 'audio/mpeg')}
            res = sesi.post(url_upload, data=payload, files=files, headers=headers_upload)
            
        # Kalau statusnya 200, artinya sukses nge-bypass database MediaCP!
        if res.status_code == 200:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error Jalur Bypass: {e}")
        return False

# ==========================================
# 4. HALAMAN LOGIN
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>URADIO STUDIO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Membersamai Kita - Internal Access</p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("🔐 Masukkan PIN Akses")
        pin_input = st.text_input("PIN:", type="password", placeholder="****")
        if st.button("Masuk Studio", use_container_width=True):
            if pin_input in USERS:
                st.session_state.logged_in = True
                st.session_state.user_data = USERS[pin_input]
                st.toast(f"Selamat datang, {USERS[pin_input]['nama']}!", icon="👋")
                st.rerun()
            else:
                st.error("PIN Salah atau Tidak Terdaftar!")

# ==========================================
# 5. HALAMAN UTAMA
# ==========================================
else:
    user = st.session_state.user_data
    
    # --- SIDEBAR (PROFIL) ---
    with st.sidebar:
        try: st.image(user["foto"], width=150, use_container_width=True)
        except: st.info("Foto belum diupload")
            
        st.title(user["nama"])
        st.caption(f"Posisi: {user['role']}")
        st.divider()
        if st.button("🚪 Keluar / Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()

    st.title(f"🎙️ Meja {user['role']}")
    
    # ==========================
    # A. TAMPILAN PENYIAR
    # ==========================
    if user["role"] == "Penyiar":
        with st.container(border=True):
            st.subheader("📝 Draft Berita Baru")
            info_mentah = st.text_area("Informasi Mentah:", value=db.get("info_mentah", ""), height=150)
            
            if st.button("🚀 Kirim ke Pemred", use_container_width=True):
                if not info_mentah.strip():
                    st.warning("Isi berita dulu!")
                else:
                    with st.spinner("AI Meracik Naskah..."):
                        try:
                            gemini_key = st.secrets["GEMINI_API_KEY"]
                            genai.configure(api_key=gemini_key)
                            prompt = f"Ubah jadi naskah radio lisan (800-1500 huruf). Buka: 'Hai Derr.' Tutup: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown.\n\n{info_mentah}"
                            model = genai.GenerativeModel("gemini-3.6-flash")
                            response = model.generate_content(prompt)
                            
                            db["status"] = "menunggu_validasi"
                            db["info_mentah"] = info_mentah
                            db["naskah"] = bersihkan_untuk_audio(response.text)
                            db["penulis"] = user["nama"] 
                            db["voice_id_penulis"] = user["voice_id"] 
                            save_db(db)
                            
                            st.success("Terkirim ke meja Agustian!")
                            st.balloons()
                        except Exception as e: st.error(f"Error AI: {e}")

        if db["status"] == "approved":
            st.info("✅ Naskah terakhirmu sudah mengudara.")

    # ==========================
    # B. TAMPILAN PEMRED
    # ==========================
    elif user["role"] == "Pemimpin Redaksi":
        if db["status"] == "kosong":
            st.info("Belum ada draft masuk.")
            
        elif db["status"] == "menunggu_validasi":
            st.warning(f"⚠️ Naskah Masuk dari: {db.get('penulis', 'Penyiar')}")
            
            with st.container(border=True):
                jml_kar = len(db["naskah"])
                col_met, col_prog = st.columns([1,3])
                col_met.metric(label="Karakter", value=jml_kar)
                col_prog.progress(min(jml_kar/1500, 1.0))
                
                naskah_edit = st.text_area("Review Naskah:", value=db["naskah"], height=250)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve & Siarkan", use_container_width=True):
                        with st.spinner("Memproduksi Audio Premium..."):
                            teks_audio = bersihkan_untuk_audio(naskah_edit)
                            suara_yg_dipakai = db.get("voice_id_penulis", "")
                            
                            elevenlabs_key = ""
                            try: elevenlabs_key = st.secrets["ELEVENLABS_API_KEY"]
                            except: pass
                            
                            if elevenlabs_key and suara_yg_dipakai:
                                try:
                                    # --- MESIN CUCI KARAKTER GAIB ---
                                    suara_bersih = suara_yg_dipakai.encode('ascii', 'ignore').decode().strip()
                                    kunci_bersih = elevenlabs_key.encode('ascii', 'ignore').decode().strip()
                                    
                                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{suara_bersih}"
                                    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": kunci_bersih}
                                    data = {"text": teks_audio, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                                    res = requests.post(url, json=data, headers=headers)
                                    
                                    if res.status_code == 200:
                                        with open("berita_siaran.mp3", 'wb') as f: f.write(res.content)
                                        
                                        db["status"] = "approved"
                                        db["naskah"] = teks_audio
                                        save_db(db)
                                        
                                        # Kirim FTP
                                        kirim_sukses = kirim_ke_radio("berita_siaran.mp3", "berita_terbaru.mp3")
                                        if kirim_sukses:
                                            st.toast('Siaaap! Audio langsung masuk MediaCP!', icon='📡')
                                        else:
                                            st.warning("Gagal FTP karena diblokir Server Cloud. Silakan pakai tombol Download di bawah.")
                                            
                                        st.rerun()
                                    else: st.error(f"ElevenLabs Error: {res.text}")
                                except Exception as e: st.error(f"Error Sistem: {e}")
                            else:
                                st.error("API ElevenLabs atau Voice ID penyiar tidak ditemukan!")

                with col2:
                    if st.button("❌ Tolak Naskah", use_container_width=True):
                        db["status"] = "kosong"
                        db["info_mentah"] = ""
                        save_db(db)
                        st.rerun()
                        
        elif db["status"] == "approved":
            st.success("✅ Naskah Approved dan Audio siap!")
            st.audio("berita_siaran.mp3")
            
            # --- JALUR DARURAT (DOWNLOAD MANUAL JIKA FTP DIBLOKIR) ---
            with open("berita_siaran.mp3", "rb") as file_mp3:
                st.download_button(
                    label="⬇️ Download Audio (Jalur Manual)",
                    data=file_mp3,
                    file_name="berita_terbaru.mp3",
                    mime="audio/mpeg",
                    use_container_width=True
                )
