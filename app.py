import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import base64
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. RESPONSIVE SHELL CONFIGURATION
# ==========================================
st.set_page_config(page_title="Aatma", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

# Elite Native Mobile App Theme UI Engine
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container {padding-top: 0.5rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold;}
        .sync-btn>div>button {background-color: #059669 !important; color: white !important; border: none;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; background-color: #F3F4F6; border-radius: 6px; font-size: 11px;}
        .file-card {
            background-color: #F8FAFC; 
            border: 1px solid #E2E8F0; 
            border-radius: 12px; 
            padding: 1.5rem; 
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# Secure Environment Infrastructure Pips (With whitespace stripping defense)
TOKEN = st.secrets.get("GITHUB_TOKEN", "").strip()
REPO = st.secrets.get("GITHUB_REPO", "").strip()
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()

# ==========================================
# ⚡ AI ENGINE — SINGLE MODEL + ONE FALLBACK
# ==========================================
def call_gemini_engine(prompt_text):
    if not API_KEY:
        return "⚠️ Gemini API Key missing in Settings -> Secrets."

    # Primary model + single fallback — no more scanning dead endpoints
    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    debug_logs = []
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                debug_logs.append(f"[{model_name}]: HTTP {response.status_code} - {response.text[:150]}")
        except Exception as e:
            debug_logs.append(f"[{model_name}]: Exception - {str(e)[:150]}")
            continue

    return "❌ Gemini request failed on all models tried. Diagnostic Log:\n" + "\n".join(debug_logs)

# ==========================================
# ⚡ VOICE-TO-TEXT ENGINE (Gemini audio transcription)
# ==========================================
def transcribe_audio_with_gemini(audio_bytes):
    if not API_KEY or not audio_bytes:
        return None
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                {"text": "Transcribe this audio recording verbatim into clean, well-punctuated text. Return ONLY the transcription itself, with no preamble, labels, or commentary."}
            ]
        }]
    }
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            continue
    return None

def voice_input_widget(target_session_key, widget_key, label="🎤 Record Voice Note"):
    """Renders a record/stop mic button. On stop, transcribes via Gemini and
    appends the text into the target text_area's session_state value, then
    reruns so the text box shows it — the user can still edit before saving."""
    audio = mic_recorder(start_prompt=label, stop_prompt="⏹️ Stop & Transcribe", just_once=True, use_container_width=True, key=widget_key)
    if audio and audio.get('bytes'):
        with st.spinner("Transcribing voice note via Gemini..."):
            transcript = transcribe_audio_with_gemini(audio['bytes'])
        if transcript:
            existing = st.session_state.get(target_session_key, "")
            st.session_state[target_session_key] = (existing.strip() + " " + transcript).strip() if existing else transcript
            st.success("Voice note transcribed — review it below before saving.")
            time.sleep(0.3)
            st.rerun()
        else:
            st.warning("Could not transcribe that recording. Please try again or type manually.")

# ==========================================
# ⚡ NATIVE LOCAL FILE TEXT EXTRACTOR
# ==========================================
def extract_raw_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        name = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()
        
        if name.endswith(".txt"):
            return file_bytes.decode("utf-8", errors="ignore")
            
        elif name.endswith(".docx"):
            wb_io = BytesIO(file_bytes)
            with zipfile.ZipFile(wb_io) as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text_pieces = [node.text for node in root.findall('.//w:t', ns) if node.text]
                return "\n".join(text_pieces)
                
        elif name.endswith(".csv"):
            return pd.read_csv(BytesIO(file_bytes)).to_string()
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(BytesIO(file_bytes)).to_string()
        else:
            return f"[Raw text content stream extracted locally for: {uploaded_file.name}]"
    except Exception as e:
        return f"[Text extraction note: {str(e)}]"

# ==========================================
# ⚡ SECURE MULTI-DEVICE DATA LOCKER PIPELINE
# ==========================================
def save_file_to_github(file_bytes, filename, folder="vault"):
    if not TOKEN or not REPO: return False
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"message": f"Cloud Upload: {filename}", "content": encoded_content}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def sync_entire_db_to_github():
    if not TOKEN or not REPO: return False
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    df_to_save = st.session_state["cached_db"]
    encoded_content = base64.b64encode(df_to_save.to_csv(index=False).encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "Database Structural Optimization Event",
        "content": encoded_content,
        "sha": sha if sha else None
    }
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def log_row_to_csv(row_dict, filename="logs.csv"):
    if not TOKEN or not REPO: return
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}?nocache={int(time.time())}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    res = requests.get(url, headers=headers)
    existing_content = ""
    sha = None
    if res.status_code == 200:
        sha = res.json().get("sha")
        existing_content = base64.b64decode(res.json().get("content")).decode("utf-8")
        df = pd.read_csv(BytesIO(existing_content.encode("utf-8")))
    else:
        df = pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID"])
    
    if "AI_Summary" not in df.columns:
        df["AI_Summary"] = ""
    if "Raw_Content" not in df.columns:
        df["Raw_Content"] = ""
    if "RowID" not in df.columns:
        df["RowID"] = ""
        
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    payload = {
        "message": "Realtime Data Sync Event",
        "content": base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("utf-8"),
        "sha": sha if sha else None
    }
    requests.put(f"https://api.github.com/repos/{REPO}/contents/{filename}", headers=headers, json=payload)

def load_live_database_uncached():
    if not TOKEN or not REPO: return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID"])
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv?t={int(time.time())}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "If-None-Match": ""
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content_b64 = res.json().get("content", "")
            content_str = base64.b64decode(content_b64).decode("utf-8")
            loaded_df = pd.read_csv(BytesIO(content_str.encode("utf-8")))
            if "AI_Summary" not in loaded_df.columns:
                loaded_df["AI_Summary"] = ""
            if "Raw_Content" not in loaded_df.columns:
                loaded_df["Raw_Content"] = ""
            if "RowID" not in loaded_df.columns:
                loaded_df["RowID"] = ""

            # Backfill missing/blank RowIDs so every row — including legacy rows
            # that share an identical Timestamp from a bulk upload — gets a
            # genuinely unique key to update or delete against.
            missing_id_mask = loaded_df["RowID"].isna() | (loaded_df["RowID"].astype(str).str.strip() == "")
            if missing_id_mask.any():
                loaded_df.loc[missing_id_mask, "RowID"] = [uuid.uuid4().hex for _ in range(int(missing_id_mask.sum()))]
            return loaded_df
    except:
        pass
    return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID"])

def commit_new_log(row_dict):
    if "AI_Summary" not in row_dict:
        row_dict["AI_Summary"] = ""
    if "Raw_Content" not in row_dict:
        row_dict["Raw_Content"] = ""
    if not row_dict.get("RowID"):
        row_dict["RowID"] = uuid.uuid4().hex
        
    if st.session_state["cached_db"].empty:
        st.session_state["cached_db"] = pd.DataFrame([row_dict])
    else:
        st.session_state["cached_db"] = pd.concat([st.session_state["cached_db"], pd.DataFrame([row_dict])], ignore_index=True)
    log_row_to_csv(row_dict)

def regenerate_summary_for_row(row_id, section, raw_text, prompt_template):
    """Regenerates and persists a summary for exactly one row, matched by its
    unique RowID — never touches any other row, even ones sharing a Timestamp."""
    resolved_summary = call_gemini_engine(prompt_template)
    st.session_state["cached_db"].loc[
        (st.session_state["cached_db"]["RowID"] == row_id) &
        (st.session_state["cached_db"]["Section"] == section),
        "AI_Summary"
    ] = resolved_summary
    sync_entire_db_to_github()

def delete_row(row_id, section):
    """Permanently removes exactly one entry (matched by RowID + Section) from
    the log database and persists that removal to GitHub. Does not delete the
    original file blob from the /vault folder in the repo — only the index
    entry that makes it show up as a card in the app."""
    st.session_state["cached_db"] = st.session_state["cached_db"][
        ~((st.session_state["cached_db"]["RowID"] == row_id) & (st.session_state["cached_db"]["Section"] == section))
    ].reset_index(drop=True)
    sync_entire_db_to_github()

def get_existing_filenames(section):
    """Returns the set of filenames already logged in a given section, parsed
    out of the Notes field (format: '📄 {filename} | ...'), so bulk uploads
    can skip re-adding a file that's already present."""
    if history_df.empty:
        return set()
    section_notes = history_df[history_df["Section"] == section]["Notes"].astype(str)
    existing = set()
    for note in section_notes:
        if "📄" in note:
            try:
                fname = note.split("📄", 1)[1].split("|", 1)[0].strip()
                existing.add(fname)
            except Exception:
                pass
    return existing

# ==========================================
# MASTER DATA INITIALIZATION
# ==========================================
if "cached_db" not in st.session_state:
    st.session_state["cached_db"] = load_live_database_uncached()

if "AI_Summary" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["AI_Summary"] = ""
if "Raw_Content" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["Raw_Content"] = ""
if "RowID" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["RowID"] = ""

st.title("🎯 Khemka Life OS")

st.markdown('<div class="sync-btn">', unsafe_allow_html=True)
if st.button("🔄 FORCE SYNC ALL DEVICES NOW", use_container_width=True):
    with st.spinner("Downloading fresh database arrays from cloud..."):
        st.session_state["cached_db"] = load_live_database_uncached()
        st.success("Synchronized! All laptop and mobile entries are up to date.")
        time.sleep(0.5)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

history_df = st.session_state["cached_db"]
st.caption(f"Last Hard Synchronization Check: {datetime.now().strftime('%H:%M:%S')}")
st.write("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "❤️ Health", "🧠 Learn", "💼 Biz", "🧘 Peace", "🤝 Rel", "📉 Finance", "🚀 Goals"
])

# ==========================================
# 1. HEALTH & FITNESS MODULE
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Vault")
    
    if not history_df.empty:
        h_data = history_df[history_df["Section"] == "Health"]
        if not h_data.empty: 
            st.line_chart(h_data.set_index("Timestamp")["Score"])
            st.write("### 📜 Health Analysis Feed:")
            for idx, (_, row) in enumerate(h_data.iloc[::-1].iterrows()):
                ai_sum = str(row.get('AI_Summary', ''))
                raw_text = str(row.get("Raw_Content", ""))
                timestamp_str = str(row['Timestamp'])
                row_id = str(row.get('RowID', '') or f"legacy_{timestamp_str}_{idx}")
                title_slug = str(row.get('Notes', 'Health Item')).split('|')[0]
                
                is_corrupted = any(err in ai_sum.lower() for err in ["unable to compile", "ceiling met", "v1beta", "historical document", "engine error", "timeout", "connection", "status 404", "❌", "error"]) or ai_sum.strip() == ""
                has_clean_raw = raw_text.strip() != "" and not any(err in raw_text.lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])
                
                st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
                st.markdown(f"### {title_slug}")
                st.caption(f"Logged at: {timestamp_str}")
                
                if is_corrupted:
                    st.warning("📋 Summary uncompiled due to historical error text blocks.")
                else:
                    st.markdown(ai_sum)

                if has_clean_raw:
                    btn_label = "✨ Generate Missing 8-10 Line Summary Now" if is_corrupted else "🔄 Regenerate this summary"
                    if st.button(btn_label, key=f"repair_h_{row_id}"):
                        with st.spinner("Extracting content metrics directly from raw data layer..."):
                            repair_prompt = f"Provide a clean, comprehensive 8-to-10 line deep-dive content summary detailing the exact key findings and what this health document states. Focus on vital data, tracking metrics, and recommendations. Your entire output response must be strictly between 8 and 10 lines long:\n\n{raw_text[:20000]}"
                            regenerate_summary_for_row(row_id, "Health", raw_text, repair_prompt)
                        st.success("Summary generated and saved permanently!")
                        time.sleep(0.5)
                        st.rerun()
                    with st.expander("📂 Click to view original raw file text"):
                        st.text_area("Original Content Stream", value=raw_text, height=200, disabled=True, key=f"raw_h_{row_id}")

                if st.button("🗑️ Delete this entry", key=f"delete_h_{row_id}"):
                    delete_row(row_id, "Health")
                    st.success("Entry deleted.")
                    time.sleep(0.3)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    h_score = st.slider("Rate physical health score today", 1, 10, 7, key="h_slider")
    voice_input_widget("h_notes", "voice_h")
    h_input = st.text_area("Type lifestyle or workout notes:", key="h_notes")
    uploaded_files = st.file_uploader("Upload files/screenshots:", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    
    if st.button("Permanently Save Health Data", use_container_width=True):
        if uploaded_files:
            existing_names = get_existing_filenames("Health")
            skipped = []
            for f in uploaded_files:
                if f.name in existing_names:
                    skipped.append(f.name)
                    continue
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                f_bytes = f.getvalue()
                save_file_to_github(f_bytes, f"health_{timestamp.replace(' ','_').replace(':','-')}_{f.name}")
                single_file_text = extract_raw_text(f)
                
                prompt_input = f"Analyze the text extracted from this specific file ({f.name}). Provide a clean, deep-dive content summary detailing the key findings and exactly what this health document states. Focus on core observations, parameters, and notes. Your entire output response must be strictly between 8 and 10 lines long:\n\nUser Context: {h_input}\n\nDocument Contents:\n{single_file_text[:15000]}"
                ai_summary = call_gemini_engine(prompt_input)
                
                commit_new_log({
                    "Timestamp": timestamp, 
                    "Section": "Health", 
                    "Score": h_score, 
                    "Notes": f"📄 {f.name} | Context: {h_input}",
                    "AI_Summary": ai_summary,
                    "Raw_Content": single_file_text if single_file_text else h_input
                })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already logged here: {', '.join(skipped)}. Delete the existing card first if you want to re-process one.")
        else:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_new_log({
                "Timestamp": timestamp, 
                "Section": "Health", 
                "Score": h_score, 
                "Notes": h_input,
                "AI_Summary": "Manual metrics profile entry saved successfully.",
                "Raw_Content": h_input
            })
            
        st.success("Synced to cloud storage!")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 2. LEARNING & DEVELOPMENT MODULE
# ==========================================
with tab2:
    st.header("📚 Master Knowledge Bank")
    
    if not history_df.empty:
        l_data = history_df[history_df["Section"] == "Learning"]
        st.metric(label="Total Library Assets Stacked", value=len(l_data))
        
        # 🎯 50-60 LINE GROUPED MASTER RULES ENGINE
        st.markdown("### ⚡ Master Life Implementation Sheet")
        if st.button("✨ GENERATE 50-60 LINE TAILORMADE BLUEPRINT FROM ALL FILES", use_container_width=True, key="gen_l_rules"):
            valid_contents = [str(r['Raw_Content']) for _, r in l_data.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "ceiling met", "v1beta", "connection refused", "engine error", "timeout", "status 404", "rejected the request"])]
            
            if valid_contents:
                combined_text = "\n\n".join(valid_contents)
                with st.spinner(f"Compiling content from {len(valid_contents)} files across your library..."):
                    prompt = f"""You are an elite high-performance mentor working for Animesh, an entrepreneur running Life Agro, WellWorld Foods, Jiva Leathers, and Khemka Woodcraft. Review the FULL text content below from ALL books and records in his library — there may be several distinct documents. Pull the best, most varied insights from EACH document, not just the first or most prominent one, so the final output genuinely represents the whole library rather than a single source.

Organize the output into 4-6 clearly labeled categories relevant to his situation (for example: 'Mindset & Psychology', 'Execution & Discipline', 'Relationships & Influence', 'Decision-Making Under Pressure', 'Leadership & Delegation') — pick categories that actually fit the content present. Under each category header, list specific, actionable, tailor-made points.

Your complete output must total between 50 and 60 lines across all categories combined. Prioritize variety — draw distinct points from as many different source documents as possible rather than concentrating on one:

{combined_text[:50000]}"""
                    st.session_state["l_master_rules"] = call_gemini_engine(prompt)
            else:
                st.warning("No clean book text fields found in your history log matrix yet. Upload a fresh document down below first!")
                
        if "l_master_rules" in st.session_state:
            st.info(st.session_state["l_master_rules"])
            st.write("---")
            
        if not l_data.empty:
            st.write("### 📜 Library Summaries & Document Reader:")
            for idx, (_, row) in enumerate(l_data.iloc[::-1].iterrows()):
                ai_sum = str(row.get('AI_Summary', ''))
                raw_text = str(row.get("Raw_Content", ""))
                timestamp_str = str(row['Timestamp'])
                row_id = str(row.get('RowID', '') or f"legacy_{timestamp_str}_{idx}")
                title_slug = str(row.get('Notes', 'Book File')).split('|')[0]
                
                is_corrupted = any(err in ai_sum.lower() for err in ["unable to compile", "ceiling met", "v1beta", "historical document", "engine error", "timeout", "connection", "status 404", "❌", "error"]) or ai_sum.strip() == ""
                has_clean_raw = raw_text.strip() != "" and not any(err in raw_text.lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])
                
                st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
                st.markdown(f"### {title_slug}")
                st.caption(f"Archived on: {timestamp_str}")
                
                if is_corrupted:
                    st.warning("📋 Summary missing or corrupted due to historical endpoint connection errors.")
                else:
                    st.markdown(ai_sum)

                if has_clean_raw:
                    btn_label = "✨ Generate Missing 8-10 Line Summary Now" if is_corrupted else "🔄 Regenerate this summary"
                    if st.button(btn_label, key=f"repair_l_{row_id}"):
                        with st.spinner("Extracting book content directly from text matrix..."):
                            repair_prompt = f"Analyze the text content of this book document. Provide a clean, thorough summary detailing the exact key findings and what this specific document states. Focus on central lessons, actionable business insights, and execution frameworks. Your entire output response must be strictly between 8 and 10 lines long:\n\n{raw_text[:25000]}"
                            regenerate_summary_for_row(row_id, "Learning", raw_text, repair_prompt)
                        st.success("Summary generated and saved permanently!")
                        time.sleep(0.5)
                        st.rerun()
                    with st.expander("📂 Click to view original raw file text"):
                        st.text_area("Original Extracted Content", value=raw_text, height=250, disabled=True, key=f"raw_l_{row_id}")

                if st.button("🗑️ Delete this entry", key=f"delete_l_{row_id}"):
                    delete_row(row_id, "Learning")
                    st.success("Entry deleted.")
                    time.sleep(0.3)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
    media_name = st.text_input("Source Batch Reference Title:")
    uploaded_books = st.file_uploader("Drop books or summaries in bulk:", type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True, key="l_bulk")
    
    if st.button("Inject Batch to Library Vault", use_container_width=True):
        if uploaded_books:
            existing_names = get_existing_filenames("Learning")
            skipped = []
            for b in uploaded_books:
                if b.name in existing_names:
                    skipped.append(b.name)
                    continue
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                with st.spinner(f"Extracting text parameters for: {b.name}..."):
                    save_file_to_github(b.getvalue(), f"library_{media_name.replace(' ','_')}_{b.name}")
                    single_book_text = extract_raw_text(b)
                    
                    prompt = f"Analyze the text extracted from this specific document ({b.name}). Provide a clean, deep-dive content summary detailing the key findings and exactly what this document states. Cover all central themes, workflows, and actionable workflows explicitly. Your entire output response must be strictly between 8 and 10 lines long:\n\n{single_book_text[:28000]}"
                    ai_summary = call_gemini_engine(prompt)
                    
                    commit_new_log({
                        "Timestamp": timestamp, 
                        "Section": "Learning", 
                        "Score": 10, 
                        "Notes": f"📄 {b.name} | Batch: {media_name}",
                        "AI_Summary": ai_summary,
                        "Raw_Content": single_book_text
                    })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already in your library: {', '.join(skipped)}. Delete the existing card first if you want to re-process one.")
            st.success("🎉 All new documents successfully isolated, analyzed, and synced!")
            time.sleep(0.5)
            st.rerun()

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    
    if not history_df.empty:
        b_data = history_df[history_df["Section"] == "Business"]
        
        st.markdown("### ⚡ Master Business Strategy Rules")
        if st.button("✨ GENERATE 50-60 LINE STRATEGIC BLUEPRINT FROM ALL VENTURE FILES", use_container_width=True, key="gen_b_rules"):
            valid_contents = [str(r['Raw_Content']) for _, r in b_data.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "ceiling met", "v1beta", "connection refused", "engine error", "timeout", "status 404", "rejected the request"])]
            if valid_contents:
                combined_text = "\n\n".join(valid_contents)
                with st.spinner(f"Compiling production directives from {len(valid_contents)} files..."):
                    prompt = f"""You are an elite strategy consultant working for Animesh across Life Agro (fortified rice kernels), WellWorld Foods (exports), Jiva Leathers (vegan leather/corporate gifting), and Khemka Woodcraft (timber import). Review the FULL text content below from ALL venture documents — there may be several distinct files. Pull the best, most varied strategic points from EACH document, not just one, so the output reflects the whole set rather than a single source.

Organize the output into 4-6 clearly labeled categories relevant to his ventures (for example: 'Export & Compliance', 'Manufacturing & Supply Chain', 'Design & Differentiation', 'Distribution & Logistics', 'Brand & Positioning') — pick categories that actually fit the content present. Under each category header, list specific, actionable rules.

Your complete output must total between 50 and 60 lines across all categories combined. Prioritize variety — draw distinct points from as many different source documents as possible rather than concentrating on one:

{combined_text[:50000]}"""
                    st.session_state["b_master_rules"] = call_gemini_engine(prompt)
            else:
                st.warning("No active corporate strategy text content files found in database archives yet.")
                
        if "b_master_rules" in st.session_state:
            st.info(st.session_state["b_master_rules"])
            st.write("---")
            
        if not b_data.empty: 
            st.write("### 📜 Corporate Summaries & Specifications:")
            for idx, (_, row) in enumerate(b_data.iloc[::-1].iterrows()):
                ai_sum = str(row.get('AI_Summary', ''))
                raw_text = str(row.get("Raw_Content", ""))
                timestamp_str = str(row['Timestamp'])
                row_id = str(row.get('RowID', '') or f"legacy_{timestamp_str}_{idx}")
                title_slug = str(row.get('Notes', 'Venture File')).split('|')[0]
                
                is_corrupted = any(err in ai_sum.lower() for err in ["unable to compile", "ceiling met", "v1beta", "historical document", "engine error", "timeout", "connection", "status 404", "❌", "error"]) or ai_sum.strip() == ""
                has_clean_raw = raw_text.strip() != "" and not any(err in raw_text.lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])
                
                st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
                st.markdown(f"### {title_slug}")
                st.caption(f"Entry Timestamp: {timestamp_str}")
                
                if is_corrupted:
                    st.warning("📋 Summary uncompiled due to a structural API connection block.")
                else:
                    st.markdown(ai_sum)

                if has_clean_raw:
                    btn_label = "✨ Generate Missing 8-10 Line Summary Now" if is_corrupted else "🔄 Regenerate this summary"
                    if st.button(btn_label, key=f"repair_b_{row_id}"):
                        with st.spinner("Extracting blueprints from original text matrix..."):
                            repair_prompt = f"Provide a clean, comprehensive 8-to-10 line deep-dive content summary detailing the key findings and exactly what this document states. Focus on manufacturing supply chains, parameters, and design execution specs. Your entire output response must be strictly between 8 and 10 lines long:\n\n{raw_text[:22000]}"
                            regenerate_summary_for_row(row_id, "Business", raw_text, repair_prompt)
                        st.success("Summary generated and saved permanently!")
                        time.sleep(0.5)
                        st.rerun()
                    with st.expander("📂 Click to view original raw file text"):
                        st.text_area("Original File Contents", value=raw_text, height=200, disabled=True, key=f"raw_b_{row_id}")

                if st.button("🗑️ Delete this entry", key=f"delete_b_{row_id}"):
                    delete_row(row_id, "Business")
                    st.success("Entry deleted.")
                    time.sleep(0.3)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
    biz_name = st.text_input("Venture Name:", value="Premium Vegan Leather Goods Brand")
    biz_score = st.slider("Current Execution Momentum", 1, 10, 7, key="b_slider")
    voice_input_widget("biz_notes", "voice_biz")
    biz_notes = st.text_area("Operational moves or bottlenecks:", value="Designing modular men's sling bags and phone card holders for export to North America, Europe, and Middle East. Differentiating utility from local competitors.", key="biz_notes")
    biz_docs = st.file_uploader("Upload engineering data sheets or invoices in bulk:", type=["xlsx", "csv", "pdf", "docx"], accept_multiple_files=True, key="b_bulk")
    
    if st.button("Analyze & Save Venture Metrics", use_container_width=True):
        if biz_docs:
            existing_names = get_existing_filenames("Business")
            skipped = []
            for bd in biz_docs:
                if bd.name in existing_names:
                    skipped.append(bd.name)
                    continue
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                with st.spinner(f"Analyzing specifications text layer for: {bd.name}..."):
                    save_file_to_github(bd.getvalue(), f"biz_{biz_name}_{bd.name}")
                    single_doc_text = extract_raw_text(bd)
                    
                    prompt = f"Act as an elite luxury brand design strategist. Analyze this specific corporate document ({bd.name}). Provide a clean, deep-dive content summary detailing the key findings and exactly what this document states. Focus on specifications, design geometry, and logistics. Your entire output response must be strictly between 8 and 10 lines long:\n\nOperational Context Notes: {biz_notes}\n\nDocument Text Data:\n{single_doc_text[:20000]}"
                    ai_summary = call_gemini_engine(prompt)
                    
                    commit_new_log({
                        "Timestamp": timestamp, 
                        "Section": "Business", 
                        "Score": biz_score, 
                        "Notes": f"📄 {bd.name} | Project: {biz_name}",
                        "AI_Summary": ai_summary,
                        "Raw_Content": single_doc_text
                    })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already logged here: {', '.join(skipped)}. Delete the existing card first if you want to re-process one.")
        else:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_new_log({
                "Timestamp": timestamp, 
                "Section": "Business", 
                "Score": biz_score, 
                "Notes": f"Log Update for {biz_name}",
                "AI_Summary": f"Venture execution parameters cataloged. Strategic update summary notes: {biz_notes}",
                "Raw_Content": biz_notes
            })
            
        st.success("🎉 Venture metrics archived & broadcasted!")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 4. PEACE & MINDSET MODULE
# ==========================================
with tab4:
    st.header("🧘 Mindset Shielding & Planetary Coordinates")
    
    if not history_df.empty:
        m_data = history_df[history_df["Section"] == "Mindset"]
        if not m_data.empty:
            st.write("### 🌌 Active Mindset Summaries & Astro Maps:")
            for idx, (_, row) in enumerate(m_data.iloc[::-1].iterrows()):
                title_slug = str(row.get('Notes', 'Mindset Item')).split('|')[0]
                timestamp_str = str(row['Timestamp'])
                row_id = str(row.get('RowID', '') or f"legacy_{timestamp_str}_{idx}")
                ai_sum = str(row.get('AI_Summary', ''))
                raw_text = str(row.get("Raw_Content", ""))
                
                is_corrupted = any(err in ai_sum.lower() for err in ["unable to compile", "ceiling met", "v1beta", "historical document", "engine error", "timeout", "connection", "status 404", "❌", "error"]) or ai_sum.strip() == ""
                has_clean_raw = raw_text.strip() != "" and not any(err in raw_text.lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])
                
                st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
                st.markdown(f"### {title_slug}")
                st.caption(f"Alignment Window: {timestamp_str}")
                
                if is_corrupted:
                    st.warning("📋 Summary data row uncompiled due to a server connection failure.")
                else:
                    st.markdown(ai_sum)

                if has_clean_raw:
                    btn_label = "✨ Generate Missing 8-10 Line Summary Now" if is_corrupted else "🔄 Regenerate this summary"
                    if st.button(btn_label, key=f"repair_m_{row_id}"):
                        with st.spinner("Extracting coordinates from chart data..."):
                            repair_prompt = f"Provide a clean, comprehensive 8-to-10 line deep-dive content summary detailing the key findings and exactly what this document states. Focus on alignment rules, remedies, and instructions. Your entire output response must be strictly between 8 and 10 lines long:\n\n{raw_text[:20000]}"
                            regenerate_summary_for_row(row_id, "Mindset", raw_text, repair_prompt)
                        st.success("Summary generated and saved permanently!")
                        time.sleep(0.5)
                        st.rerun()
                    with st.expander("📂 Click to view original raw file text"):
                        st.text_area("Original Content Stream", value=raw_text, height=200, disabled=True, key=f"raw_m_{row_id}")

                if st.button("🗑️ Delete this entry", key=f"delete_m_{row_id}"):
                    delete_row(row_id, "Mindset")
                    st.success("Entry deleted.")
                    time.sleep(0.3)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Fetch Daily Meditation & Energy Shield Protocol", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        ai_summary = call_gemini_engine("Provide an executive mindset validation drill, deep rhythmic breathing guidelines, and explicit protocols to maintain absolute workspace concentration and isolate energy from critical family members.")
        commit_new_log({
            "Timestamp": timestamp,
            "Section": "Mindset",
            "Score": 10,
            "Notes": "Meditation Shield Request",
            "AI_Summary": ai_summary,
            "Raw_Content": "Natively generated inside AI memory matrix coordinates."
        })
        st.rerun()
            
    st.markdown("---")
    st.subheader("🌌 Natal Chart Synthesis Drawer")
    astro_files = st.file_uploader("Drop planetary maps/birth charts (Select Multiple):", type=["pdf", "png", "jpg"], accept_multiple_files=True, key="a_bulk")
    if st.button("Execute Astro Mapping Alignment", use_container_width=True):
        if astro_files:
            existing_names = get_existing_filenames("Mindset")
            skipped = []
            for af in astro_files:
                if af.name in existing_names:
                    skipped.append(af.name)
                    continue
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(af.getvalue(), f"astro_{af.name}")
                single_chart_text = extract_raw_text(af)
                
                prompt = f"Analyze this structural natal data layer ({af.name}). Provide a clean, deep-dive content summary detailing the exact key findings and what this chart text states. Extract direct personal alignment remedies. Your entire output response must be strictly between 8 and 10 lines long:\n\n{single_chart_text[:20000]}"
                ai_summary = call_gemini_engine(prompt)
                
                commit_new_log({
                    "Timestamp": timestamp,
                    "Section": "Mindset",
                    "Score": 10,
                    "Notes": f"📄 {af.name} | Astro Coordinates Mapping",
                    "AI_Summary": ai_summary,
                    "Raw_Content": single_chart_text
                })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already logged here: {', '.join(skipped)}.")
            st.rerun()

# ==========================================
# 5. RELATIONSHIPS MODULE
# ==========================================
with tab5:
    st.header("🤝 Interpersonal Network Alignment")
    
    if not history_df.empty:
        r_data = history_df[history_df["Section"] == "Relationships"]
        if not r_data.empty: 
            st.line_chart(r_data.set_index("Timestamp")["Score"])
            st.write("### 📜 Communication Alignment Feed:")
            for _, row in r_data.iloc[::-1].iterrows():
                with st.expander(f"📝 View Summary ({row['Timestamp']})"):
                    st.write(row.get("Notes", "No notes logged."))
                st.write("---")
        
    r_score = st.slider("Rate relational harmony level", 1, 10, 7, key="r_slider")
    voice_input_widget("r_notes", "voice_r")
    r_notes = st.text_area("Key communication metrics or dynamics tracker:", key="r_notes")
    if st.button("Archive Relationship Log Entry", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Relationships", "Score": r_score, "Notes": r_notes, "AI_Summary": "Manual Entry Recorded.", "Raw_Content": r_notes})
        st.success("🎉 Network logs compiled and safely synced!")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 6. INDIAN STOCK MARKET ENGINE
# ==========================================
with tab6:
    st.header("📉 Market Trading Terminal")
    
    if not history_df.empty:
        f_data = history_df[history_df["Section"] == "Finance"]
        if not f_data.empty:
            st.write("### 📜 Market Summaries & Risk Metrics:")
            for idx, (_, row) in enumerate(f_data.iloc[::-1].iterrows()):
                title_slug = str(row.get('Notes', 'Finance Update')).split('|')[0]
                row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
                
                st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
                st.markdown(f"### {title_slug}")
                st.caption(f"Session Stamp: {row['Timestamp']}")
                if "AI_Summary" in row and pd.notna(row["AI_Summary"]) and row["AI_Summary"] != "":
                    st.markdown(row["AI_Summary"])
                
                raw_text = str(row.get("Raw_Content", ""))
                if raw_text.strip() != "" and not any(err in raw_text.lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"]):
                    with st.expander("📂 Click to view original raw spreadsheet text"):
                        st.text_area("Spreadsheet Extracted Array", value=raw_text, height=200, disabled=True, key=f"raw_f_{row_id}")

                if st.button("🗑️ Delete this entry", key=f"delete_f_{row_id}"):
                    delete_row(row_id, "Finance")
                    st.success("Entry deleted.")
                    time.sleep(0.3)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    if st.button("☀️ Pull Indian Pre-Market Framework Analysis", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        nifty_close = 0.0
        try:
            nifty_df = yf.Ticker("^NSEI").history(period="2d")
            nifty_close = nifty_df['Close'].iloc[-1] if not nifty_df.empty else 0.0
        except Exception:
            pass
        
        ai_summary = call_gemini_engine(f"Provide an assertive technical market layout brief for an Indian equities operator. Index validation state: Nifty 50 close tracking near {nifty_close}. Highlight 3 alpha trading sectors for outperformance.")
                
        commit_new_log({
            "Timestamp": timestamp,
            "Section": "Finance",
            "Score": 10,
            "Notes": f"Nifty Position Context: ₹{nifty_close:.2f}",
            "AI_Summary": ai_summary,
            "Raw_Content": f"Nifty Ticker Feed Close Value: {nifty_close}"
        })
        st.rerun()
                    
    st.markdown("---")
    ticker = st.text_input("Enter NSE Ticker Symbol (e.g. RELIANCE.NS, TCS.NS):", value="RELIANCE.NS")
    if st.button("Run Fundamental + Technical Market Audit", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                ai_summary = call_gemini_engine(f"Hedge fund analysis report for {ticker}. Metrics: {metrics}. Provide explicit target support layers and a clear Buy/Hold/Sell recommendation.")
                
                commit_new_log({
                    "Timestamp": timestamp,
                    "Section": "Finance",
                    "Score": 10,
                    "Notes": f"Equity Core Assessment: {ticker}",
                    "AI_Summary": f"**Data Metrics:** {metrics}\n\n{ai_summary}",
                    "Raw_Content": metrics
                })
                st.rerun()
        except Exception as err: st.error(f"Audit error: {err}")

    st.markdown("---")
    st.subheader("📋 Structural Portfolio Evaluation")
    port_files = st.file_uploader("Drop broker spreadsheets/statements (Select Multiple):", type=["xlsx", "csv"], accept_multiple_files=True, key="p_bulk")
    if st.button("Execute Portfolio Audit Risk Check", use_container_width=True):
        if port_files:
            existing_names = get_existing_filenames("Finance")
            skipped = []
            for pf in port_files:
                if pf.name in existing_names:
                    skipped.append(pf.name)
                    continue
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(pf.getvalue(), f"portfolio_{pf.name}")
                single_sheet_text = extract_raw_text(pf)
                
                commit_new_log({
                    "Timestamp": timestamp,
                    "Section": "Finance",
                    "Score": 10,
                    "Notes": f"📄 {pf.name} | Statement Update",
                    "AI_Summary": f"### Brokerage Log Sync Verified\nRaw statement text matrix for {pf.name} successfully registered to screen review frame layers.",
                    "Raw_Content": single_sheet_text
                })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already logged here: {', '.join(skipped)}.")
            st.success("🎉 Portfolio structural breakdown synced to server files successfully!")
            time.sleep(0.5)
            st.rerun()

# ==========================================
# 7. LONG-TERM GOALS
# ==========================================
with tab7:
    st.header("🚀 Strategic Goal Vectoring")
    
    if not history_df.empty:
        g_data = history_df[history_df["Section"] == "Goals"]
        if not g_data.empty: 
            st.line_chart(g_data.set_index("Timestamp")["Score"])
            st.write("### 📜 Active Master Targets:")
            for _, row in g_data.iloc[::-1].iterrows():
                with st.expander(f"📝 View Summary ({row['Timestamp']})"):
                    if "AI_Summary" in row and pd.notna(row["AI_Summary"]) and row["AI_Summary"] != "":
                        st.markdown(row["AI_Summary"])
                st.write("---")
        
    voice_input_widget("vision_input", "voice_vision")
    vision_input = st.text_area("Define master 5 & 10-year blueprints:", value="Build a premier international sustainable design and luxury leather export empire with established corporate gifting logistics footprint across India.", key="vision_input")
    if st.button("Update Long-Term Directives", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Goals", "Score": 10, "Notes": "Visions updated.", "AI_Summary": f"### Master Blueprint Plan:\n{vision_input}", "Raw_Content": vision_input})
        st.success("🎉 Vision matrices locked in and synchronized globally!")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 🟢 MASTER GREEN SYNC TERMINAL PANEL (BOTTOM UI)
# ==========================================
st.markdown("""
    <style>
    div.stButton > button {
        background-color: #28a745 !important; color: white !important;
        font-size: 20px !important; font-weight: bold !important;
        padding: 15px 30px !important; border-radius: 8px !important;
        width: 100% !important; border: none !important;
    }
    div.stButton > button:hover { background-color: #218838 !important; }
    </style>
""", unsafe_allow_html=True)

st.write("---") 
st.write("### 🗲 Universal Cross-Device Entry Pad")

sync_section = st.selectbox("Assign log to module:", ["Business", "Learning", "Health", "Goals", "Relationships"], key="m_sec")
voice_input_widget("m_notes", "voice_sync")
sync_notes = st.text_area("Type updates, logs, or paste Google Drive asset links here:", placeholder="Example: Placed catalog design layout updates here. Link: https://drive.google.com/...", key="m_notes")
sync_score = st.slider("Assign score status value:", 1, 10, 10, key="m_score")

if st.button("🟢 FORCE SYNC ALL DEVICES NOW"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_entry = {
        "Timestamp": timestamp,
        "Section": sync_section,
        "Score": sync_score,
        "Notes": f"Global Device Pad Log: {sync_notes}",
        "AI_Summary": f"### Direct Asset Update Record:\n{sync_notes}",
        "Raw_Content": sync_notes
    }
    
    commit_new_log(new_entry)
    st.success("✨ Everything synchronized flawlessly! Data securely saved and broadcasted to all terminal instances.")
    time.sleep(0.5)
    st.rerun()
