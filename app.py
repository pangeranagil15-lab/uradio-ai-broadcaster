import streamlit as st
import google.generativeai as genai
import re
import json
import os
import requests
import threading
import time
import datetime
import shutil

from pydub import AudioSegment

# --- GOOGLE DRIVE IMPORTS (OAUTH 2.0) ---
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- PERBAIKAN ERROR FFPROBE / FFMPEG ---
AudioSegment.converter = "/usr/bin/ffmpeg"
AudioSegment.ffprobe = "/usr/bin/ffprobe"

# --- ZONA WAKTU & SETTING ---
WIB = datetime.timezone(datetime.timedelta(hours=7))
WAKTU_TUNGGU_HAPUS = 600  # 10 MENIT

# --- GLOBAL SECRETS ---
WEB_USER = st.secrets["WEB_USER"]
WEB_PASS = st.secrets["WEB_PASS"]

# --- GDRIVE SETTINGS ---
GDRIVE_FOLDER_ID = "1NZu0i-jd3kgMR4SZEejhpZOXTyKeTnEG"

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
# 2. DATABASE, USERS, FILE PATHS
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
    },
    "8888": {
        "nama": "Didi Sang Gledek",
        "role": "Penyiar",
        "foto": "didi.jpg", 
        "voice_id": "z9MHmvoAUrDuC9c0yeWd",
        "prompt_system": "Ubah info berikut jadi naskah radio lisan (800-1500 huruf). Gaya bahasa: artikulasi terdengar ceria, lugas, bergaya santai dengan komunikasi keseharian menggunakan kata 'gw' dan 'elo' ala Gen Z. Buka dengan sapaan asik: 'Halo Derr!'. Tutup dengan: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown."
    },
    "9999": {
        "nama": "Arif Hari Ahmad",
        "role": "Penyiar",
        "foto": "arif.jpg", 
        "voice_id": "7F5iDVXfb9MFGQlMtTpV",
        "prompt_system": "Ubah info berikut jadi naskah radio lisan (800-1500 huruf). Gaya bahasa: artikulasi terdengar jelas, lugas, tegas, berbobot, agak serak, dan berwibawa. Buka dengan sapaan akrab namun sopan seperti: 'Halo Derr'. Tutup dengan: 'Tetap bersama kami, URadio, Membersamai Kita'. Tanpa format markdown."
    }
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if 'jumlah_jadwal' not in st.session_state:
    st.session_state.jumlah_jadwal = 1

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database_berita.json")
TIKET_FILE = os.path.join(BASE_DIR, "tiket_sapu.json")

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"status": "kosong", "info_mentah": "", "naskah": "", "penulis": "", "voice_id_penulis": "", "role_penulis": ""}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

def set_tiket(nama_file, tiket):
    data = {}
    if os.path.exists(TIKET_FILE):
        try:
            with open(TIKET_FILE, "r") as f: data = json.load(f)
        except: pass
    data[nama_file] = tiket
    with open(TIKET_FILE, "w") as f: json.dump(data, f)

def get_tiket(nama_file):
    if os.path.exists(TIKET_FILE):
        try:
            with open(TIKET_FILE, "r") as f: return json.load(f).get(nama_file)
        except: return None
    return None

db = load_db()

# ==========================================
# 3. FUNGSI-FUNGSI PENDUKUNG (AI, RADIO, GDRIVE)
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
            try:
                kaset = AudioSegment.from_mp3("berita_siaran.mp3")
                kaset_kencang = kaset + 4 
                kaset_kencang.export("berita_siaran.mp3", format="mp3")
                print("[INFO] Volume kaset berhasil dinaikkan +4 dB!", flush=True)
            except Exception as e:
                print(f"[WARNING] Melewati boost volume karena format file: {e}", flush=True)
            return True
        else:
            st.error(f"ElevenLabs Error: {res.text}")
            return False
    except Exception as e:
        st.error(f"Error Sistem ElevenLabs: {e}")
        return False

def simpan_ke_gdrive(file_lokal, nama_penyiar):
    try:
        creds = Credentials(
            token=None,
            refresh_token=st.secrets.get("GDRIVE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets.get("GDRIVE_CLIENT_ID"),
            client_secret=st.secrets.get("GDRIVE_CLIENT_SECRET")
        )
        service = build('drive', 'v3', credentials=creds)

        waktu_sekarang = datetime.datetime.now(WIB).strftime("%Y-%m-%d_%H-%M-%S")
        nama_file_drive = f"{waktu_sekarang}_{nama_penyiar}_Arsip.mp3"

        file_metadata = {
            'name': nama_file_drive,
            'parents': [GDRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_lokal, mimetype='audio/mpeg', resumable=True)
        
        print(f"[GDRIVE] OTW Upload arsip: {nama_file_drive}...", flush=True)
        request = service.files().create(body=file_metadata, media_body=media, fields='id')
        response = request.execute()
        
        print(f"[GDRIVE] SUKSES! Arsip tersimpan di Drive lu.", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR GDRIVE] Gagal upload arsip: {e}", flush=True)
        return False

def kirim_ke_radio(file_lokal, nama_file_tujuan):
    try:
        current_ticket = time.time()
        set_tiket(nama_file_tujuan, current_ticket)

        sesi = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0'}
        url_login = "https://mediacp-eu1.arenastreaming.com:2020/index.php"
        data_login = {"username": WEB_USER, "user_password": WEB_PASS, "language": "default"}
        
        print("[DEBUG] Mencoba login ke MediaCP...", flush=True)
        sesi.get(url_login, headers=headers)
        login_res = sesi.post(url_login, data=data_login, headers=headers)
        print(f"[DEBUG] Status Login MediaCP: {login_res.status_code}", flush=True)
        
        url_upload = "https://mediacp-eu1.arenastreaming.com:2020/controller/Media/7/uploadTrack"
        payload = {'path': '/Berita'}
        headers_upload = headers.copy()
        headers_upload['Origin'] = 'https://mediacp-eu1.arenastreaming.com:2020'
        headers_upload['Referer'] = 'https://mediacp-eu1.arenastreaming.com:2020/controller/Media/7'
        
        print(f"[DEBUG] Mengirim file {nama_file_tujuan} ke MediaCP...", flush=True)
        with open(file_lokal, 'rb') as f:
            files = {'track': (nama_file_tujuan, f, 'audio/mpeg')}
            res = sesi.post(url_upload, data=payload, files=files, headers=headers_upload)

        print(f"[DEBUG] Status Upload MediaCP: {res.status_code}", flush=True)

        if res.status_code == 200:
            print(f"[INFO] File {nama_file_tujuan} Berhasil Mengudara! Timer {WAKTU_TUNGGU_HAPUS}s On...", flush=True)
            
            def hapus_pakai_api_resmi(nama_target, tiket_saya, file_asal):
                print(f"[TUKANG SAPU] Standby {WAKTU_TUNGGU_HAPUS} detik. Tiket: {tiket_saya}", flush=True)
                time.sleep(WAKTU_TUNGGU_HAPUS)
                
                tiket_terbaru = get_tiket(nama_target)
                if tiket_saya != tiket_terbaru:
                    print(f"[BATAL] Tukang Sapu mundur. Ada jadwal baru yang nimpa!", flush=True)
                    return 

                try:
                    print(f"[TUKANG SAPU] Beraksi buat hapus {nama_target}...", flush=True)
                    file_hening = f"hening_{nama_target}"
                    AudioSegment.silent(duration=1000).export(file_hening, format="mp3")
                    
                    sesi_sapu = requests.Session()
                    sesi_sapu.get(url_login, headers=headers)
                    sesi_sapu.post(url_login, data=data_login, headers=headers)
                    
                    with open(file_hening, 'rb') as f_silent:
                        files_silent = {'track': (nama_target, f_silent, 'audio/mpeg')}
                        res_sapu = sesi_sapu.post(url_upload, data=payload, files=files_silent, headers=headers_upload)
                    
                    if res_sapu.status_code == 200:
                        print(f"[SUKSES] Kaset {nama_target} berhasil disapu / ditimpa hening!", flush=True)
                        try:
                            os.remove(file_hening)
                            if "jadwal" in file_asal: os.remove(file_asal)
                        except: pass
                    else:
                        print(f"[ERROR] Nolak kaset hening: {res_sapu.text[:200]}", flush=True)
                except Exception as e:
                    print(f"[ERROR] Tukang sapu gagal: {e}", flush=True)

            t = threading.Thread(target=hapus_pakai_api_resmi, args=(nama_file_tujuan, current_ticket, file_lokal))
            t.start()
            return True
        else: 
            print(f"[ERROR RADIO] Gagal lempar ke MediaCP. Status code: {res.status_code}, Respon: {res.text[:200]}", flush=True)
            return False
    except Exception as e: 
        print(f"[ERROR CRITICAL RADIO SYSTEM]: {e}", flush=True)
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
        try: st.image(user["foto"], width=150)
        except: st.info("Foto belum diupload")
        st.title(user["nama"])
        st.caption(f"Posisi: {user['role']}")
        st.divider()
        if st.button("🚪 Keluar / Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_data = None
            st.rerun()

    st.title(f"🎙️ Meja {user['role']}")
    
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
                            model = genai.GenerativeModel("gemini-1.5-flash")
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

    elif user["role"] == "Pemimpin Redaksi":
        if db["status"] == "kosong":
            st.info("Belum ada draft masuk.")
            
        elif db["status"] == "menunggu_validasi":
            st.warning(f"⚠️ Naskah Masuk dari: {db.get('penulis', 'Unknown')} ({db.get('role_penulis', 'Penyiar')})")
            
            with st.container(border=True):
                naskah_edit = st.text_area("Review Naskah:", value=db["naskah"], height=200)
                suara_yg_dipakai = db.get("voice_id_penulis", "")
                nama_penulis_audio = db.get("penulis", "Unknown")
                
                st.divider()
                st.markdown("### 🚀 JALUR EKSPRES (BREAKING NEWS)")
                if st.button("🔥 Siarkan Sekarang", use_container_width=True):
                    with st.spinner("Memproduksi Audio & Menerobos ke Radio..."):
                        teks_bersih = bersihkan_untuk_audio(naskah_edit)
                        if produksi_audio_elevenlabs(teks_bersih, suara_yg_dipakai):
                            # --- TRIGGER BACKUP GDRIVE OTOMATIS (THREADING) ---
                            t_gdrive = threading.Thread(target=simpan_ke_gdrive, args=("berita_siaran.mp3", nama_penulis_audio))
                            t_gdrive.start()

                            # --- EKSEKUSI LANGSUNG KE RADIO ---
                            print("[INFO] Mengeksekusi pengiriman langsung ke MediaCP...", flush=True)
                            hasil_radio = kirim_ke_radio("berita_siaran.mp3", "berita_terbaru_ekspres.mp3")
                            print(f"[INFO] Status kirim ke radio: {hasil_radio}", flush=True)
                            
                            db["status"] = "approved"
                            db["naskah"] = teks_bersih
                            save_db(db)
                            st.toast('Siaaap! Audio mengudara & di-backup ke GDrive!', icon='📡')
                            st.rerun()

                st.divider()
                st.markdown("### 🗓️ JALUR TERJADWAL (CUSTOM SCHEDULE)")
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
                            # --- TRIGGER BACKUP GDRIVE OTOMATIS ---
                            t_gdrive = threading.Thread(target=simpan_ke_gdrive, args=("berita_siaran.mp3", nama_penulis_audio))
                            t_gdrive.start()

                            db["status"] = "approved"
                            db["naskah"] = teks_bersih
                            save_db(db)
                            
                            def kurir_ninja(target_waktu, urutan, file_master_kurir):
                                sekarang = datetime.datetime.now(WIB)
                                waktu_target = datetime.datetime.combine(sekarang.date(), target_waktu)
                                waktu_target = waktu_target.replace(tzinfo=WIB)
                                if waktu_target < sekarang:
                                    waktu_target += datetime.timedelta(days=1)
                                jeda = (waktu_target - sekarang).total_seconds()
                                
                                if jeda > 5:
                                    print(f"[INFO] Kurir {urutan} standby! OTW MediaCP {int(jeda)} detik lagi...", flush=True)
                                    time.sleep(jeda)
                                    
                                print(f"[INFO] JAM TAYANG! Kurir {urutan} lempar kaset terjadwal!", flush=True)
                                kirim_ke_radio(file_master_kurir, "berita_terjadwal_master.mp3")

                            for i, jam_tayang in enumerate(jadwal_list):
                                file_copy_khusus = f"berita_siaran_copy_{i+1}.mp3"
                                shutil.copy("berita_siaran.mp3", file_copy_khusus)
                                
                                t_kurir = threading.Thread(target=kurir_ninja, args=(jam_tayang, i+1, file_copy_khusus))
                                t_kurir.start()
                            
                            st.toast(f'Beres! {len(jadwal_list)} Kurir jalan & Master di-backup ke GDrive.', icon='🥷')
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
                st.download_button(label="⬇️ Download Kaset Master", data=file_mp3, file_name="berita_master.mp3", mime="audio/mpeg", use_container_width=True)
