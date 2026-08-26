import streamlit as st
import google.generativeai as genai
import re
import json
import os
import requests
import threading
import time
import datetime
from pydub import AudioSegment # Mixer Audio Virtual

# --- ZONA WAKTU INDONESIA (WIB) ---
WIB = datetime.timezone(datetime.timedelta(hours=7))

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
# 2. DATABASE & SESSION STATE
# ==========================================
USERS = {
    "1111": {
        "nama": "Agustian",
        "role": "Pemimpin Redaksi",
        "foto": "agustian.jpg", 
        "voice_id": "",
        "prompt_system": "" 
    },
    "2222": {
        "nama": "Ki Sandi Suryadinata",
        "role": "Penyiar",
        "foto": "sandi.jpg", 
        "voice_id": "wxuHKpeHPOQlfryZit7t",
        "prompt_system": "Ubah info berikut jadi naskah radio lisan (800-1500 huruf). Gaya santai, akrab, lisan. Buka dengan: 'Hai Derr.' Tutup dengan: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown."
    },
    "3333": {
        "nama": "Sem Haesy",
        "role": "Narasumber",
        "foto": "sem_haesy.jpg", 
        "voice_id": "ry35IfPkrTNFBXaZzaPc",
        "prompt_system": "Ubah info berikut jadi naskah pernyataan/opini lisan (800-1500 huruf). Gaya bahasa: artikulasi jelas, lugas, tegas, berbobot, dan berwibawa. INSTRUKSI PENTING: Buat tempo bacanya LAMBAT dan BERPENEKANAN dengan cara WAJIB menyisipkan banyak tanda koma (,) dan titik-titik (...) di antara kalimat agar seolah-olah sedang mengambil jeda napas yang panjang. Wajib tutup dengan kalimat: 'Billahi fi sabilil haq, wassalamualaikum warahmatullahi wabarakatuh.' Tanpa format markdown."
    },
    "4444": {
        "nama": "Ferry Juliantono",
        "role": "Narasumber",
        "jabatan": "Menteri Koperasi",
        "foto": "ferry.jpg", 
        "voice_id": "3lMUf1sc9Hxjzmjo8tSX",
        "prompt_system": "Ubah info berikut jadi naskah pernyataan lisan (800-1500 huruf) sebagai Menteri Koperasi. Gaya bahasa: artikulasi jelas, lugas, tegas, berbobot, dan berwibawa. INSTRUKSI PENTING: Buat tempo bacanya LAMBAT dan BERPENEKANAN dengan cara WAJIB menyisipkan banyak tanda koma (,) dan titik-titik (...) di antara kalimat agar seolah-olah sedang mengambil jeda napas yang panjang. Wajib tutup dengan kalimat: 'Billahi fi sabilil haq, wassalamualaikum warahmatullahi wabarakatuh.' Tanpa format markdown."
    },
    "5555": {
        "nama": "Hamdan Zulva",
        "role": "Narasumber",
        "jabatan": "Pakar Hukum Tata Negara",
        "foto": "hamdan.jpg", 
        "voice_id": "JZGBWv46XHdJuPtv4WuY",
        "prompt_system": "Ubah info berikut jadi naskah opini lisan (800-1500 huruf) sebagai Pakar Hukum Tata Negara. Gaya bahasa: artikulasi jelas, lugas, agak lambat (slow), berbobot tajam, dan berwibawa. INSTRUKSI PENTING: Buat tempo bacanya SANGAT LAMBAT dengan cara WAJIB menyisipkan banyak tanda koma (,) dan titik-titik (...) di antara kalimat agar seolah-olah sedang mengambil jeda napas yang panjang. Wajib tutup dengan kalimat: 'Fattaqullaha mastatoktum, Billahi fi sabilil haq, wassalamualaikum warahmatullahi wabarakatuh.' Tanpa format markdown."
    },
    "6666": {
        "nama": "Agus",
        "role": "Penyiar",
        "foto": "agus.jpg", 
        "voice_id": "hXNnLf1MfUhNAIH9BYw9",
        "prompt_system": "Ubah info berikut jadi naskah radio lisan (800-1500 huruf). Gaya bahasa: artikulasi jelas, lugas, tegas, berbobot, dan berwibawa. Buka dengan sapaan akrab namun sopan seperti: 'Halo Derr'. Tutup dengan: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown."
    },
    "7777": {
        "nama": "Abe Langit",
        "role": "Penyiar",
        "foto": "abe_langit.jpg", 
        "voice_id": "0dLMJJSLFRTNRgiys70E",
        "prompt_system": "Ubah info berikut jadi naskah radio lisan (800-1500 huruf). Gaya bahasa: sangat ceria, lugas, asik, bergaya santai ala Gen Z. WAJIB menggunakan kata ganti 'gw' dan 'elo'/'lo'. Buka dengan sapaan energik: 'Halo Derr!'. Tutup dengan: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown."
    }
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if 'jumlah_jadwal' not in st.session_state:
    st.session_state.jumlah_jadwal = 1

# === GLOBAL TICKET SYSTEM (Smart Reset Timer) ===
if 'upload_tickets' not in st.session_state:
    st.session_state.upload_tickets = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database_berita.json")

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"status": "kosong", "info_mentah": "", "naskah": "", "penulis": "", "voice_id_penulis": "", "role_penulis": ""}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

db = load_db()

# ==========================================
# 3. FUNGSI-FUNGSI PENDUKUNG (AI & KURIR)
# ==========================================
def bersihkan_untuk_audio(teks):
    teks = re.sub(r'\[.*?\]', '', teks)
    teks = re.sub(r'\(.*?\)', '', teks)
    teks = re.sub(r'[*#_~`>]', '', teks)
    teks = re.sub(r'^(Berikut|Ini).*?:\n', '', teks, flags=re.IGNORECASE)
    return teks.strip()

def produksi_audio_elevenlabs(teks_audio, voice_id):
    try:
        elevenlabs_key = st.secrets.get("ELEVENLABS_API_KEY", "")
        if not elevenlabs_key or not voice_id:
            st.error("API ElevenLabs atau Voice ID penyiar tidak ditemukan!")
            return False
            
        suara_bersih = voice_id.encode('ascii', 'ignore').decode().strip()
        kunci_bersih = elevenlabs_key.encode('ascii', 'ignore').decode().strip()
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{suara_bersih}"
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": kunci_bersih}
        data = {"text": teks_audio, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.45, "similarity_boost": 0.75}}
        
        res = requests.post(url, json=data, headers=headers, timeout=30)
        if res.status_code == 200:
            with open("berita_siaran.mp3", 'wb') as f: f.write(res.content)
            
            # Eksekusi Booster Volume (+10 dB)
            try:
                kaset = AudioSegment.from_mp3("berita_siaran.mp3")
                kaset_kencang = kaset + 10 
                kaset_kencang.export("berita_siaran.mp3", format="mp3")
                print("[INFO] Volume kaset berhasil dinaikkan +10 dB!", flush=True)
            except Exception as e:
                print(f"[WARNING] Gagal nge-boost volume: {e}", flush=True)

            return True
        else:
            st.error(f"ElevenLabs Error: {res.text}")
            return False
    except Exception as e:
        st.error(f"Error Sistem ElevenLabs: {e}")
        return False

def kirim_ke_radio(file_lokal, nama_file_tujuan):
    try:
        # 1. Bikin nomor tiket
        current_ticket = time.time()
        st.session_state.upload_tickets[nama_file_tujuan] = current_ticket

        # 2. Login Web MediaCP (Jalur Depan / HTTP API)
        sesi = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'}
        
        url_login = "https://mediacp-eu1.arenastreaming.com:2020/index.php"
        data_login = {"username": st.secrets["WEB_USER"], "user_password": st.secrets["WEB_PASS"], "language": "default"}
        sesi.get(url_login, headers=headers)
        sesi.post(url_login, data=data_login, headers=headers)
        
        # 3. Eksekusi Upload
        url_upload = "https://mediacp-eu1.arenastreaming.com:2020/controller/Media/8/uploadTrack"
        payload = {'path': '/Berita'}
        headers_upload = headers.copy()
        headers_upload['Origin'] = 'https://mediacp-eu1.arenastreaming.com:2020'
        headers_upload['Referer'] = 'https://mediacp-eu1.arenastreaming.com:2020/controller/Media/8'
        
        with open(file_lokal, 'rb') as f:
            files = {'track': (nama_file_tujuan, f, 'audio/mpeg')}
            res = sesi.post(url_upload, data=payload, files=files, headers=headers_upload)

        if res.status_code == 200:
            print(f"[INFO] File {nama_file_tujuan} Berhasil Mengudara (Tiket: {current_ticket})! Timer On...", flush=True)
            
            # === [BARU] TUKANG SAPU JALUR DEPAN (HTTP API - ANTI GAGAL) ===
            def hapus_pakai_api_resmi(nama_target, tiket_saya):
                print(f"[TUKANG SAPU] Stanby 30 detik. Tiket: {tiket_saya}", flush=True)
                time.sleep(30)
                
                # Cek tiket dulu
                tiket_terbaru = st.session_state.upload_tickets.get(nama_target)
                if tiket_saya != tiket_terbaru:
                    print(f"[BATAL] Tukang Sapu mundur. Ada siaran baru masuk!", flush=True)
                    return 

                try:
                    print("[TUKANG SAPU] Beraksi! Membuat kaset hening untuk menimpa file...", flush=True)
                    # Bikin kaset hening (silent) durasi 1 detik pakai pydub
                    AudioSegment.silent(duration=1000).export("hening.mp3", format="mp3")
                    
                    # Login ulang API (karena sesi sebelumnya udah expired setelah 10 menit nunggu)
                    sesi_sapu = requests.Session()
                    sesi_sapu.get(url_login, headers=headers)
                    sesi_sapu.post(url_login, data=data_login, headers=headers)
                    
                    # Upload kaset hening buat NIMPA file lama di MediaCP
                    with open("hening.mp3", 'rb') as f_silent:
                        files_silent = {'track': (nama_target, f_silent, 'audio/mpeg')}
                        res_sapu = sesi_sapu.post(url_upload, data=payload, files=files_silent, headers=headers_upload)
                    
                    if res_sapu.status_code == 200:
                        print(f"[SUKSES] Kaset {nama_target} berhasil ditimpa dengan kaset hening via API resmi!", flush=True)
                    else:
                        print(f"[ERROR] MediaCP nolak kaset hening: {res_sapu.text}", flush=True)
                        
                except Exception as e:
                    print(f"[ERROR] Tukang sapu API gagal: {e}", flush=True)

            # Eksekusi timer di background
            t = threading.Thread(target=hapus_pakai_api_resmi, args=(nama_file_tujuan, current_ticket))
            t.start()

            return True
        else: return False
    except Exception as e:
        print(f"Error Upload: {e}")
        return False

# ==========================================
# 4. HALAMAN LOGIN & SIDEBAR
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
            else: st.error("PIN Salah atau Tidak Terdaftar!")

else:
    user = st.session_state.user_data
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
    # 5. MEJA KONTRIBUTOR (PENYIAR & NARASUMBER)
    # ==========================
    if user["role"] in ["Penyiar", "Narasumber"]:
        with st.container(border=True):
            st.subheader(f"📝 Draft Naskah Baru - {user['nama']}")
            info_mentah = st.text_area("Informasi Mentah / Poin Statement:", value=db.get("info_mentah", ""), height=150)
            
            if st.button("🚀 Kirim ke Pemred", use_container_width=True):
                if not info_mentah.strip(): st.warning("Isi informasi dulu!")
                else:
                    with st.spinner("AI Meracik Naskah Sesuai Karakter..."):
                        try:
                            gemini_key = st.secrets["GEMINI_API_KEY"]
                            genai.configure(api_key=gemini_key)
                            
                            prompt = f"{user['prompt_system']}\n\nInformasi Mentah:\n{info_mentah}"
                            
                            model = genai.GenerativeModel("gemini-3.6-flash")
                            response = model.generate_content(prompt)
                            
                            db["status"] = "menunggu_validasi"
                            db["info_mentah"] = info_mentah
                            db["naskah"] = bersihkan_untuk_audio(response.text)
                            db["penulis"] = user["nama"] 
                            db["role_penulis"] = user["role"]
                            db["voice_id_penulis"] = user["voice_id"] 
                            save_db(db)
                            
                            st.success("Terkirim ke meja Agustian!")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        except Exception as e: st.error(f"Error AI: {e}")

        if db["status"] == "approved":
            st.info("✅ Naskah terakhirmu sudah diproduksi / dijadwalkan.")

    # ==========================
    # 6. MEJA PEMRED
    # ==========================
    elif user["role"] == "Pemimpin Redaksi":
        if db["status"] == "kosong":
            st.info("Belum ada draft masuk.")
            
        elif db["status"] == "menunggu_validasi":
            
            st.warning(f"⚠️ Naskah Masuk dari: {db.get('penulis', 'Unknown')} ({db.get('role_penulis', 'Penyiar')})")
            
            with st.container(border=True):
                naskah_edit = st.text_area("Review Naskah:", value=db["naskah"], height=200)
                suara_yg_dipakai = db.get("voice_id_penulis", "")
                
                st.divider()
                st.markdown("### 🚀 JALUR EKSPRES (BREAKING NEWS)")
                st.caption("Kaset akan diproduksi dan langsung mengudara ke radio saat ini juga.")
                if st.button("🔥 Siarkan Sekarang", use_container_width=True):
                    with st.spinner("Memproduksi Audio & Menerobos ke Radio..."):
                        teks_bersih = bersihkan_untuk_audio(naskah_edit)
                        if produksi_audio_elevenlabs(teks_bersih, suara_yg_dipakai):
                            kirim_ke_radio("berita_siaran.mp3", "berita_terbaru_ekspres.mp3")
                            db["status"] = "approved"
                            db["naskah"] = teks_bersih
                            save_db(db)
                            st.toast('Siaaap! Audio langsung memotong lagu di MediaCP!', icon='📡')
                            st.rerun()

                st.divider()
                st.markdown("### 🗓️ JALUR TERJADWAL (CUSTOM SCHEDULE)")
                st.caption("Buat jadwal tayang. Kaset otomatis dihapus setelah 10 menit.")
                
                jadwal_list = []
                cols = st.columns(3) 
                for i in range(st.session_state.jumlah_jadwal):
                    with cols[i % 3]:
                        waktu_awal = (datetime.datetime.now(WIB) + datetime.timedelta(minutes=5 * (i+1))).time()
                        t = st.time_input(f"Jam Tayang {i+1}", value=waktu_awal, key=f"waktu_{i}")
                        jadwal_list.append(t)
                
                if st.button("➕ Tambah Jam Tayang"):
                    st.session_state.jumlah_jadwal += 1
                    st.rerun()

                if st.button("✅ Approve & Jadwalkan Waktu di Atas", use_container_width=True):
                    with st.spinner("Memproduksi Kaset Master..."):
                        teks_bersih = bersihkan_untuk_audio(naskah_edit)
                        if produksi_audio_elevenlabs(teks_bersih, suara_yg_dipakai):
                            db["status"] = "approved"
                            db["naskah"] = teks_bersih
                            save_db(db)
                            
                            def kurir_ninja(target_waktu, urutan):
                                sekarang = datetime.datetime.now(WIB)
                                waktu_target = datetime.datetime.combine(sekarang.date(), target_waktu)
                                waktu_target = waktu_target.replace(tzinfo=WIB)
                                
                                if waktu_target < sekarang:
                                    waktu_target += datetime.timedelta(days=1)
                                jeda = (waktu_target - sekarang).total_seconds()
                                
                                if jeda > 5:
                                    print(f"[INFO] Kurir {urutan} standby! OTW MediaCP {int(jeda)} detik lagi (Target: {waktu_target.strftime('%H:%M:%S')} WIB).", flush=True)
                                    time.sleep(jeda)
                                    
                                print(f"[INFO] JAM TAYANG WIB! Kurir {urutan} melempar kaset ke Radio!", flush=True)
                                kirim_ke_radio("berita_siaran.mp3", f"berita_jadwal_{urutan}.mp3")

                            for i, jam_tayang in enumerate(jadwal_list):
                                t_kurir = threading.Thread(target=kurir_ninja, args=(jam_tayang, i+1))
                                t_kurir.start()
                            
                            st.toast(f'Audio beres! {len(jadwal_list)} Kurir sudah standby untuk jam-jam tersebut.', icon='🥷')
                            st.rerun()

                st.divider()
                if st.button("❌ Tolak Naskah", type="secondary", use_container_width=True):
                    db["status"] = "kosong"
                    db["info_mentah"] = ""
                    st.session_state.jumlah_jadwal = 1
                    save_db(db)
                    st.rerun()
                        
        elif db["status"] == "approved":
            st.success("✅ Naskah Approved! Master kaset siap beroperasi.")
            st.audio("berita_siaran.mp3")
            
            with open("berita_siaran.mp3", "rb") as file_mp3:
                st.download_button(
                    label="⬇️ Download Kaset Master (Manual)",
                    data=file_mp3,
                    file_name="berita_master.mp3",
                    mime="audio/mpeg",
                    use_container_width=True
                )
