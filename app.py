import streamlit as st
import google.generativeai as genai
import re
import json
import os
import requests
import ftplib
from gtts import gTTS

# ==========================================
# 1. SETUP TEMA & HALAMAN
# ==========================================
st.set_page_config(page_title="URadio Studio", page_icon="🎙️", layout="centered")

# --- CUSTOM CSS: TEMA DEEP NAVY & NEON BLUE ---
st.markdown("""
    <style>
    /* Ubah warna background utama (opsional, karena Streamlit Dark Mode sudah bagus) */
    
    /* Tombol Utama (Neon Blue ala tombol 'Listen Live' di referensi) */
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
    
    /* Warna header */
    h1, h2, h3 {
        color: #1e90ff !important;
    }
    
    /* Membulatkan form input */
    .stTextInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #1e90ff !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE PEGAWAI & LOGIN SYSTEM
# ==========================================
# Di sinilah lu nambahin penyiar baru nantinya!
USERS = {
    "1111": {
        "nama": "Agustian",
        "role": "Pemimpin Redaksi",
        "foto": "agustian.jpg", # Pastikan file agustian.jpg ada di GitHub
        "voice_id": "" # Pemred nggak butuh Voice ID
    },
    "2222": {
        "nama": "Ki Sandi Suryadinata",
        "role": "Penyiar",
        "foto": "sandi.jpg", # Pastikan file sandi.jpg ada di GitHub
        "voice_id": "wxuHKpeHPOQlfryZit7t" # Nanti ganti dengan ID Suara ElevenLabs milik Sandi
    }
}

# Inisialisasi status login di memori
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

# ==========================================
# 3. FUNGSI-FUNGSI PENDUKUNG (DATABASE & FTP)
# ==========================================
DB_FILE = "database_berita.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"status": "kosong", "info_mentah": "", "naskah": "", "penulis": "", "voice_id_penulis": ""}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

db = load_db()

def bersihkan_untuk_audio(teks):
    teks = re.sub(r'\[.*?\]', '', teks)
    teks = re.sub(r'\(.*?\)', '', teks)
    teks = re.sub(r'[*#_~`>]', '', teks)
    teks = re.sub(r'^(Berikut|Ini).*?:\n', '', teks, flags=re.IGNORECASE)
    return teks.strip()

def kirim_ke_radio(nama_file_lokal, nama_file_di_server):
    try:
        ftp = ftplib.FTP()
        ftp.connect(st.secrets["FTP_HOST"], int(st.secrets["FTP_PORT"]))
        ftp.login(st.secrets["FTP_USER"], st.secrets["FTP_PASS"])
        with open(nama_file_lokal, 'rb') as f:
            ftp.storbinary(f'STOR {nama_file_di_server}', f)
        ftp.quit()
        return True
    except Exception as e:
        st.error(f"Gagal konek FTP: {e}")
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
# 5. HALAMAN UTAMA (SETELAH LOGIN)
# ==========================================
else:
    user = st.session_state.user_data
    
    # --- SIDEBAR (PROFIL USER) ---
    with st.sidebar:
        # Coba tampilkan foto, kalau file tidak ada, jangan error
        try:
            st.image(user["foto"], width=150, use_container_width=True)
        except:
            st.info("Foto belum diupload ke GitHub")
            
        st.title(user["nama"])
        st.caption(f"Posisi: {user['role']}")
        st.divider()
        
        if st.button("🚪 Keluar / Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()

    # --- KONTEN UTAMA BERDASARKAN ROLE ---
    st.title(f"🎙️ Meja {user['role']}")
    
    # A. JIKA YANG LOGIN ADALAH PENYIAR (KI SANDI)
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
                            db["penulis"] = user["nama"] # Catat siapa yang nulis
                            db["voice_id_penulis"] = user["voice_id"] # Catat ID suaranya
                            save_db(db)
                            
                            st.success("Terkirim ke meja Agustian!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error AI: Pastikan kunci Gemini ada di Secrets. Detail: {e}")

        if db["status"] == "approved":
            st.info("✅ Naskah terakhirmu sudah mengudara.")

    # B. JIKA YANG LOGIN ADALAH PEMRED (AGUSTIAN)
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
                
                # Pemred milih jadwal tayang MediaCP
                pilihan_jadwal = st.radio("Pilih Slot Tayang FTP:", 
                    ["Pagi (berita_pagi.mp3)", "Siang (berita_siang.mp3)", "Sore (berita_sore.mp3)"], horizontal=True)
                
                nama_file_server = re.search(r'\((.*?)\)', pilihan_jadwal).group(1)
                
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
                                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{suara_yg_dipakai}"
                                    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": elevenlabs_key}
                                    data = {"text": teks_audio, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                                    res = requests.post(url, json=data, headers=headers)
                                    
                                    if res.status_code == 200:
                                        with open("berita_siaran.mp3", 'wb') as f: f.write(res.content)
                                        
                                        # Eksekusi FTP
                                        if kirim_ke_radio("berita_siaran.mp3", nama_file_server):
                                            db["status"] = "approved"
                                            db["naskah"] = teks_audio
                                            save_db(db)
                                            st.toast('Siaaap! Audio mengudara!', icon='📡')
                                            st.rerun()
                                    else: st.error("Gagal Render ElevenLabs.")
                                except Exception as e: st.error(f"Error AI: {e}")
                            else:
                                st.error("API ElevenLabs atau Voice ID penyiar tidak ditemukan!")

                with col2:
                    if st.button("❌ Tolak Naskah", use_container_width=True):
                        db["status"] = "kosong"
                        db["info_mentah"] = ""
                        save_db(db)
                        st.rerun()
                        
        elif db["status"] == "approved":
            st.success("✅ Naskah terakhir sudah masuk server.")
            st.audio("berita_siaran.mp3")
