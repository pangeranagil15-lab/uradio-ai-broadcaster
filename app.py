import streamlit as st
import google.generativeai as genai
import re
import json
import os
import requests
from gtts import gTTS

st.set_page_config(page_title="URadio AI Dashboard", page_icon="🎙️", layout="centered")

# --- DATABASE SEDERHANA ---
DB_FILE = "database_berita.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"status": "kosong", "info_mentah": "", "naskah": ""}

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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Login Sistem")
    role = st.selectbox("Masuk Sebagai:", ["Penyiar", "Pemimpin Redaksi"])
    gemini_key = st.text_input("Gemini API Key", type="password")

st.title(f"🎙️ Meja {role} URadio")

# ==========================================
# 1. TAMPILAN PENYIAR
# ==========================================
if role == "Penyiar":
    st.subheader("Buat Draft Berita")
    info_mentah = st.text_area("Masukkan info mentah berita:", value=db.get("info_mentah", ""))
    
    if st.button("🚀 Buat Naskah & Kirim ke Redaksi", type="primary"):
        if not gemini_key:
            st.error("Masukkan Gemini API Key di sidebar terlebih dahulu!")
        elif not info_mentah.strip():
            st.warning("Masukkan informasi berita terlebih dahulu!")
        else:
            with st.spinner("AI sedang menyusun gaya bahasa URadio (800-1500 karakter)..."):
                genai.configure(api_key=gemini_key)
                
                system_prompt = """
                Anda adalah penyiar radio profesional untuk 'URadio'.
                Tugas: Ubah informasi mentah menjadi naskah siaran radio lisan (spoken words) yang siap dibaca mengudara.
                
                ATURAN WAJIB FORMAT SIARAN:
                1. Salam Pembuka WAJIB diawali dengan kalimat persis: "Hai Derr."
                2. Penutup Siaran WAJIB diakhiri dengan kalimat persis: "Tetap bersama kami, URadio, Membersamai Kita"
                3. Gaya Bahasa: Bahasa tutur radio (spoken language) yang ramah, berwibawa, dan enak didengar.
                4. PANJANG NASKAH: WAJIB antara 800 hingga 1500 karakter huruf. Elaborasi dan jabarkan informasi mentah dengan detail yang mengalir agar panjang naskah mencapai target ini, namun jangan terdengar bertele-tele.
                
                ATURAN SANGAT KETAT:
                1. HANYA keluarkan kalimat yang diucapkan langsung oleh penyiar dari awal sampai akhir.
                2. JANGAN gunakan tanda format markdown (DILARANG menggunakan bintang **, ***, tanda pagar #, atau bullet points).
                3. JANGAN tuliskan instruksi panggung/teknis seperti 'SFX', 'Musik', 'Fade in', 'Fade out', atau '[Penyiar]'.
                4. JANGAN tambahkan kalimat pembuka/basa-basi seperti 'Berikut adalah naskah...'.
                5. Tuliskan angka dalam bentuk kata ejaan (misal: 'empat puluh dua', 'seratus dua puluh tahun').
                """
                
                model = genai.GenerativeModel(model_name="gemini-3.6-flash", system_instruction=system_prompt)
                response = model.generate_content(info_mentah)
                
                naskah_murni = bersihkan_untuk_audio(response.text)
                
                db["status"] = "menunggu_validasi"
                db["info_mentah"] = info_mentah
                db["naskah"] = naskah_murni
                save_db(db)
                st.success("Draft ala URadio terkirim ke Pemimpin Redaksi!")

    if db["status"] == "approved":
        st.divider()
        st.success("✅ Naskah telah disetujui Pemimpin Redaksi!")
        st.text_area("Naskah Final:", value=db["naskah"], height=250)
        st.audio("berita_siaran.mp3")

# ==========================================
# 2. TAMPILAN PEMIMPIN REDAKSI
# ==========================================
elif role == "Pemimpin Redaksi":
    st.subheader("Meja Redaksi (Validasi)")
    
    if db["status"] == "kosong":
        st.info("Belum ada draft berita baru dari penyiar.")
        
    elif db["status"] == "menunggu_validasi":
        st.warning("⚠️ Ada naskah baru yang perlu divalidasi!")
        
        jumlah_karakter = len(db["naskah"])
        st.caption(f"Panjang Naskah Saat Ini: {jumlah_karakter} karakter")
        
        naskah_edit = st.text_area("Review / Edit Naskah:", value=db["naskah"], height=300)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ YES (Approve)", type="primary"):
                with st.spinner("Merender Audio URadio..."):
                    teks_audio = bersihkan_untuk_audio(naskah_edit)
                    
                    # Logika Tarik API Key dari Streamlit Secrets (Aman)
                    elevenlabs_key = ""
                    try:
                        elevenlabs_key = st.secrets["ELEVENLABS_API_KEY"]
                    except:
                        pass
                    
                    if elevenlabs_key:
                        try:
                            # ---> GANTI TULISAN DI BAWAH INI DENGAN VOICE ID KAMU <---
                            voice_id = "3rL9ZxRgBgIkh4tcbrEH" 
                            
                            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                            headers = {
                                "Accept": "audio/mpeg",
                                "Content-Type": "application/json",
                                "xi-api-key": elevenlabs_key
                            }
                            data = {
                                "text": teks_audio,
                                "model_id": "eleven_multilingual_v2",
                                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
                            }
                            
                            response = requests.post(url, json=data, headers=headers)
                            
                            # CEK APAKAH ELEVENLABS MENERIMA ATAU MENOLAK
                            if response.status_code == 200:
                                with open("berita_siaran.mp3", 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=1024):
                                        if chunk:
                                            f.write(chunk)
                                
                                db["status"] = "approved"
                                db["naskah"] = teks_audio
                                save_db(db)
                                st.success("Naskah disetujui! Audio siap diputar.")
                                st.rerun()
                            else:
                                # Jika ditolak, tampilkan pesan error aslinya agar kita tahu penyakitnya
                                st.error(f"❌ ElevenLabs Error: {response.text}")
                                
                        except Exception as e:
                            st.error(f"Gagal terhubung ke jaringan: {e}")
                    else:
                        st.info("API ElevenLabs di Secrets tidak ditemukan. Menggunakan suara Google.")
                        tts = gTTS(text=teks_audio, lang='id', slow=False)
                        tts.save("berita_siaran.mp3")
                        
                        db["status"] = "approved"
                        db["naskah"] = teks_audio
                        save_db(db)
                        st.success("Naskah disetujui! Audio siap diputar.")
                        st.rerun()
                    
        with col2:
            if st.button("🔄 Generate Ulang"):
                if not gemini_key:
                    st.error("Isi API Key di Sidebar!")
                else:
                    with st.spinner("AI meracik ulang naskah..."):
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel(model_name="gemini-3.6-flash")
                        prompt_ulang = f"Tulis ulang informasi ini menjadi naskah radio lisan. Buka dengan 'Hai Derr.' Tutup dengan 'Tetap bersama kami, URadio, Membersamai Kita'. Gunakan bahasa ramah dan berwibawa. Panjang naskah WAJIB 800 hingga 1500 karakter. TANPA format markdown, TANPA instruksi SFX, tulis angka dengan huruf: {db['info_mentah']}"
                        response = model.generate_content(prompt_ulang)
                        db["naskah"] = bersihkan_untuk_audio(response.text)
                        save_db(db)
                        st.rerun()

        with col3:
            if st.button("❌ NO (Tolak)"):
                db["status"] = "kosong"
                db["info_mentah"] = ""
                db["naskah"] = ""
                save_db(db)
                st.error("Naskah ditolak.")
                st.rerun()
                
    elif db["status"] == "approved":
        st.success("Berita sudah disetujui dan siap siar.")
        st.text_area("Naskah Final:", value=db["naskah"], height=250)
        st.audio("berita_siaran.mp3")
