import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import base64
import time
import uuid
import json
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. RESPONSIVE SHELL CONFIGURATION
# ==========================================
st.set_page_config(page_title="Khemka Life OS", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

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

def transcribe_number_with_gemini(audio_bytes):
    """Transcribes a spoken number (e.g. a weight or body-fat %) and returns
    it as a float, or None if no clean number could be extracted."""
    if not API_KEY or not audio_bytes:
        return None
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                {"text": "The speaker is saying a single number (possibly with a decimal), such as a body weight in kg or a percentage. Transcribe it and return ONLY that numeric value in plain digits (e.g. '78.5'), with no units, words, or commentary. If you cannot make out a clear number, return exactly: NONE"}
            ]
        }]
    }
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                raw = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
                if cleaned and cleaned != ".":
                    try:
                        return float(cleaned)
                    except ValueError:
                        return None
                return None
        except Exception:
            continue
    return None

def voice_number_input_widget(target_session_key, widget_key, label="🎤 Say the number"):
    """Records a short voice clip, transcribes it to a single number via
    Gemini, and writes it into the target number_input's session_state."""
    audio = mic_recorder(start_prompt=label, stop_prompt="⏹️ Stop & Transcribe", just_once=True, use_container_width=True, key=widget_key)
    if audio and audio.get('bytes'):
        with st.spinner("Transcribing number via Gemini..."):
            number = transcribe_number_with_gemini(audio['bytes'])
        if number is not None:
            st.session_state[target_session_key] = number
            st.success(f"Heard: {number} — review below before saving.")
            time.sleep(0.3)
            st.rerun()
        else:
            st.warning("Could not make out a clear number from that recording. Please try again or type manually.")

def get_latest_body_stat_value(field, entry_type="Current"):
    """Pulls a single field (weight/height/bmi/fat_pct) out of the most
    recent BodyStats row of the given type, so inputs can pre-fill with the
    last saved value instead of resetting to zero on every reload."""
    if history_df.empty:
        return None
    stats_rows = history_df[(history_df["Section"] == "BodyStats") & (history_df["Notes"] == entry_type)]
    if stats_rows.empty:
        return None
    try:
        latest = stats_rows.sort_values("Timestamp").iloc[-1]
        parsed = json.loads(str(latest["Raw_Content"]))
        return parsed.get(field)
    except Exception:
        return None

HEALTH_MOTIVATION_QUOTES = [
    "Discipline is choosing what you want most over what you want right now.",
    "The body achieves what the mind believes — show up before you feel ready.",
    "Small consistent habits beat occasional heroic efforts, every single time.",
    "You don't need more motivation, you need a better routine.",
    "Energy managed well compounds faster than time managed well.",
    "Every glass of water, every extra step, is a vote for the person you're becoming.",
    "Rest is not the opposite of progress — it's part of the formula.",
    "The best workout is the one you actually finish today.",
    "Strength is built in the moments you didn't feel like continuing.",
    "Your future self is watching what you choose to do right now.",
    "Progress isn't loud. It's a thousand quiet choices nobody sees.",
    "Health is the one investment that pays returns in every other area of life.",
    "Sleep on time tonight — it's the cheapest performance upgrade available.",
    "You can't out-train a bad routine, but a good routine forgives a bad day.",
    "The goal isn't perfection, it's momentum that survives a bad week.",
    "What you eat today is walking and talking as you three years from now.",
    "Discipline in the morning buys freedom for the rest of the day.",
    "A ten-minute walk you actually take beats the perfect plan you don't.",
    "You are not behind. You are exactly on the schedule you've been keeping.",
    "The version of you at your goal weight was built one boring Tuesday at a time.",
    "Fatigue lies. Consistency doesn't.",
    "Every rep, every step, every early night is a message to your nervous system: we are safe, we are strong.",
    "Comfort and growth rarely live in the same room — pick one for today.",
    "You will never regret the workout you finished, only the one you skipped.",
    "The scale is one data point. Show up regardless of what it says today.",
    "Recovery is where the actual strength gets built — respect it like training.",
    "A body that moves daily ages differently than one that doesn't. Choose daily.",
    "Your habits are voting on your future health long before symptoms show up.",
    "Standards, not moods, decide what happens before 6am.",
    "The best time to build the habit was a year ago. The second best time is today.",
]

def render_original_file_preview(file_path, original_filename):
    """Renders the original uploaded file inline, using its public raw GitHub
    URL. Images render directly; PDFs/Word/Excel render via Google's public
    document viewer (works for public repos without any extra API key).
    Assumes the repo's default branch is 'main' — adjust below if yours is
    named differently (e.g. 'master')."""
    if not file_path or not REPO:
        st.caption("Original file preview unavailable for this entry (uploaded before this feature was added).")
        return
    raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{file_path}"
    ext = original_filename.lower().split('.')[-1] if '.' in original_filename else ''
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        st.image(raw_url, use_container_width=True)
    elif ext in ['pdf', 'docx', 'xlsx', 'xls', 'doc', 'ppt', 'pptx']:
        viewer_url = f"https://docs.google.com/viewer?url={raw_url}&embedded=true"
        st.markdown(f'<iframe src="{viewer_url}" width="100%" height="500" style="border:1px solid #E2E8F0;border-radius:8px;"></iframe>', unsafe_allow_html=True)
    st.markdown(f"[⬇️ Download original file]({raw_url})")

BUSINESS_VENTURES = ["Life Agro", "WellWorld Foods", "Jiva Leathers", "Khemka Woodcraft"]

BUSINESS_MOTIVATION_QUOTES = [
    ("Stay hungry, stay foolish.", "Steve Jobs"),
    ("Culture eats strategy for breakfast.", "Peter Drucker"),
    ("Price is what you pay, value is what you get.", "Warren Buffett"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Your most unhappy customers are your greatest source of learning.", "Jeff Bezos"),
    ("Do not be embarrassed by failures, learn from them and start again.", "Richard Branson"),
    ("Business opportunities are like buses — there's always another one coming.", "Richard Branson"),
    ("Take care of your employees and they'll take care of your business.", "Richard Branson"),
    ("I never dreamed about success, I worked for it.", "Estée Lauder"),
    ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
    ("The best way to predict the future is to create it.", "Peter Drucker"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford"),
    ("Quality means doing it right when no one is looking.", "Henry Ford"),
    ("There is no substitute for hard work.", "Thomas Edison"),
    ("Small opportunities are often the beginning of great enterprises.", "Demosthenes"),
    ("The customer's perception is your reality.", "Kate Zabriskie"),
    ("Growth and comfort do not coexist.", "Ginni Rometty"),
    ("The elevator to success is out of order — use the stairs.", "Zig Ziglar"),
    ("I am my own experiment, my own work of art.", "Madam C.J. Walker"),
    ("Chase the vision, not the money — the money will follow.", "Tony Hsieh"),
    ("If you don't build your dream, someone will hire you to build theirs.", "Tony Gaskins"),
    ("Focus on being productive instead of busy.", "Tim Ferriss"),
]

def render_venture_panel(venture_name):
    """Renders one venture's full panel: voice/file input for things-to-do,
    per-venture file upload with AI summaries, and an on-demand expansion &
    long-term strategy generator scoped only to that venture's own notes and
    documents (matched via the Venture field, not the whole Business section)."""
    slug = venture_name.lower().replace(" ", "_")
    st.markdown(f"#### 🏭 {venture_name}")

    voice_input_widget(f"todo_{slug}", f"voice_todo_{slug}", f"🎤 Record Things To Do — {venture_name}")
    todo_text = st.text_area(f"Things to do — {venture_name}", key=f"todo_{slug}")
    uploaded = st.file_uploader(f"Upload files for {venture_name} (PDF, Word, Excel, Image)", type=["pdf", "docx", "xlsx", "png", "jpg"], accept_multiple_files=True, key=f"upload_{slug}")

    if st.button(f"💾 Save & Analyze — {venture_name}", key=f"save_{slug}", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        if todo_text.strip():
            commit_new_log({
                "Timestamp": timestamp, "Section": "Business", "Score": 7,
                "Notes": f"📝 Things To Do | Venture: {venture_name}",
                "AI_Summary": todo_text, "Raw_Content": todo_text, "Venture": venture_name
            })
        if uploaded:
            existing_names = get_existing_filenames("Business")
            skipped = []
            for f in uploaded:
                if f.name in existing_names:
                    skipped.append(f.name)
                    continue
                vault_filename = f"biz_{slug}_{f.name}"
                save_file_to_github(f.getvalue(), vault_filename)
                single_text = extract_raw_text(f)
                prompt = f"Analyze this document ({f.name}) uploaded for the venture '{venture_name}'. Provide a clean 8-10 line markdown bullet summary of its key findings, focusing on operational, financial, or strategic relevance:\n\n{single_text[:20000]}"
                ai_summary = call_gemini_engine(prompt)
                commit_new_log({
                    "Timestamp": timestamp, "Section": "Business", "Score": 7,
                    "Notes": f"📄 {f.name} | Venture: {venture_name}",
                    "AI_Summary": ai_summary, "Raw_Content": single_text,
                    "FilePath": f"vault/{vault_filename}", "Venture": venture_name
                })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s): {', '.join(skipped)}")
        st.success(f"Saved for {venture_name}!")
        time.sleep(0.5)
        st.rerun()

    strategy_key = f"strategy_{slug}"
    if st.button(f"🚀 Generate Expansion & Long-Term Strategy — {venture_name}", key=f"gen_strategy_{slug}", use_container_width=True):
        venture_rows = history_df[(history_df["Section"] == "Business") & (history_df["Venture"] == venture_name)] if not history_df.empty else pd.DataFrame()
        valid_contents = []
        if not venture_rows.empty:
            valid_contents = [str(r['Raw_Content']) for _, r in venture_rows.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])]
        context_text = "\n\n".join(valid_contents)[:35000] if valid_contents else f"No documents or notes logged yet for {venture_name} — base this on general best practices for this type of business."
        strategy_prompt = f"""You are an elite business strategy advisor working directly for Animesh on his venture '{venture_name}'. Based on the notes and documents below, give concrete, specific suggestions on: (1) what more or better he could be doing to expand this business, and (2) a long-term strategic direction. Be specific to this venture, not generic filler. Format as clear markdown bullet points, 10-15 bullets total:

{context_text}"""
        with st.spinner(f"Analyzing {venture_name} and drafting strategy..."):
            st.session_state[strategy_key] = call_gemini_engine(strategy_prompt)

    if strategy_key in st.session_state:
        st.markdown(st.session_state[strategy_key])

    st.write("---")

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
        df = pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID", "FilePath", "Venture"])
    
    if "AI_Summary" not in df.columns:
        df["AI_Summary"] = ""
    if "Raw_Content" not in df.columns:
        df["Raw_Content"] = ""
    if "RowID" not in df.columns:
        df["RowID"] = ""
    if "FilePath" not in df.columns:
        df["FilePath"] = ""
    if "Venture" not in df.columns:
        df["Venture"] = ""
        
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    payload = {
        "message": "Realtime Data Sync Event",
        "content": base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("utf-8"),
        "sha": sha if sha else None
    }
    requests.put(f"https://api.github.com/repos/{REPO}/contents/{filename}", headers=headers, json=payload)

def load_live_database_uncached():
    if not TOKEN or not REPO: return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID", "FilePath", "Venture"])
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
            if "FilePath" not in loaded_df.columns:
                loaded_df["FilePath"] = ""
            if "Venture" not in loaded_df.columns:
                loaded_df["Venture"] = ""

            # Backfill missing/blank RowIDs so every row — including legacy rows
            # that share an identical Timestamp from a bulk upload — gets a
            # genuinely unique key to update or delete against.
            missing_id_mask = loaded_df["RowID"].isna() | (loaded_df["RowID"].astype(str).str.strip() == "")
            if missing_id_mask.any():
                loaded_df.loc[missing_id_mask, "RowID"] = [uuid.uuid4().hex for _ in range(int(missing_id_mask.sum()))]
            return loaded_df
    except:
        pass
    return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID", "FilePath", "Venture"])

def commit_new_log(row_dict):
    if "AI_Summary" not in row_dict:
        row_dict["AI_Summary"] = ""
    if "Raw_Content" not in row_dict:
        row_dict["Raw_Content"] = ""
    if not row_dict.get("RowID"):
        row_dict["RowID"] = uuid.uuid4().hex
    if "FilePath" not in row_dict:
        row_dict["FilePath"] = ""
    if "Venture" not in row_dict:
        row_dict["Venture"] = ""
        
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
if "FilePath" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["FilePath"] = ""
if "Venture" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["Venture"] = ""

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

    # ---------- SUBSECTION 1: DAILY HEALTH TIPS ----------
    st.markdown("### ✅ Your Daily Health Playbook")
    tips_btn_label = "🔄 Refresh My Daily Health Tips" if "health_tips" in st.session_state else "✨ Generate My 15-20 Daily Health Tips"
    if st.button(tips_btn_label, use_container_width=True, key="gen_health_tips"):
        h_data_for_tips = history_df[history_df["Section"] == "Health"] if not history_df.empty else pd.DataFrame()
        valid_h_contents = []
        if not h_data_for_tips.empty:
            valid_h_contents = [str(r['Raw_Content']) for _, r in h_data_for_tips.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "ceiling met", "v1beta", "connection refused", "engine error", "timeout", "status 404", "rejected the request"])]
        doc_context = ("\n\n".join(valid_h_contents))[:20000] if valid_h_contents else "No uploaded health documents yet — base this purely on general expert best practices."
        tips_prompt = f"""You are a world-class health and fitness expert advising Animesh, a 34-year-old entrepreneur in Kolkata who runs multiple businesses and prefers sports over gym workouts. Give him 15 to 20 specific, practical, day-to-day health tips covering hydration, nutrition, exercise/steps, sleep timing, wake-up discipline, and recovery — the kind of tips a top health expert would give (e.g. drink enough water daily, eat clean whole foods, aim for a daily step target, keep a consistent sleep and wake-up schedule, exercise most days). Where genuinely relevant, weave in specific insights from his own uploaded health documents below — don't force it if the documents aren't relevant to daily habits.

Format as a clean numbered list from 1 to however many tips you give (between 15 and 20), one punchy, specific, actionable sentence per tip:

{doc_context}"""
        with st.spinner("Compiling your daily health playbook..."):
            st.session_state["health_tips"] = call_gemini_engine(tips_prompt)
        st.rerun()

    if "health_tips" in st.session_state:
        st.markdown(st.session_state["health_tips"])
    else:
        st.caption("Tap the button above to generate your personalized daily health tips.")
    st.write("---")

    # ---------- SUBSECTION 2: PROGRESS TRACKER (live, no history) ----------
    st.markdown("### 📊 Today's Progress Tracker")
    habit_items = [
        ("😴 Proper sleep timings (10-5)", "track_sleep_timing"),
        ("🏃 Exercise / running every morning (20000 steps)", "track_exercise"),
        ("💧 Drink magic water (at least 2 ltrs per day)", "track_water"),
        ("🌬️ Deep breathing exercises", "track_breathing"),
        ("🚿 Cold showers for dopamine", "track_cold_shower"),
        ("🪜 Take only stairs not lift", "track_stairs"),
        ("📵 No gadgets in washroom & after 9:30PM", "track_no_gadgets"),
        ("🧘 Digital detox", "track_digital_detox"),
        ("🥗 Proper & healthy food — no junk food, sugar, proper protein", "track_diet"),
        ("🦷 Brush 2 times a day properly", "track_brushing"),
        ("🧴 Proper skin care & hygiene", "track_skincare"),
        ("💪 Increase testosterone levels", "track_testosterone"),
    ]
    for label, key in habit_items:
        if key not in st.session_state:
            st.session_state[key] = 5
        st.slider(label, 1, 10, key=key)
    st.caption("Live self-ratings for today — these reset when the app reloads and aren't saved to history.")
    st.write("---")

    # ---------- SUBSECTION 3: MOTIVATIONAL QUOTE (rotates daily) ----------
    day_index = datetime.now().timetuple().tm_yday % len(HEALTH_MOTIVATION_QUOTES)
    st.markdown("### 💬 Today's Motivation")
    st.info(f"_{HEALTH_MOTIVATION_QUOTES[day_index]}_")
    st.write("---")

    # ---------- SUBSECTION 4: BODY STATS (current + target, voice-enabled, BMI auto-calc, charts) ----------
    st.markdown("### 📏 Body Stats")

    if "bodystat_height" not in st.session_state:
        st.session_state["bodystat_height"] = get_latest_body_stat_value("height", "Current") or 170.0
    if "bodystat_weight_current" not in st.session_state:
        st.session_state["bodystat_weight_current"] = get_latest_body_stat_value("weight", "Current") or 0.0
    if "bodystat_fat_current" not in st.session_state:
        st.session_state["bodystat_fat_current"] = get_latest_body_stat_value("fat_pct", "Current") or 0.0
    if "bodystat_weight_target" not in st.session_state:
        st.session_state["bodystat_weight_target"] = get_latest_body_stat_value("weight", "Target") or 0.0
    if "bodystat_fat_target" not in st.session_state:
        st.session_state["bodystat_fat_target"] = get_latest_body_stat_value("fat_pct", "Target") or 0.0

    st.number_input("Height (cm) — used to auto-calculate BMI", min_value=0.0, max_value=250.0, step=0.5, key="bodystat_height")

    col_current, col_target = st.columns(2)
    with col_current:
        st.markdown("**Current**")
        voice_number_input_widget("bodystat_weight_current", "voice_weight_cur", "🎤 Say Current Weight")
        st.number_input("Weight (kg)", min_value=0.0, max_value=300.0, step=0.1, key="bodystat_weight_current")
        voice_number_input_widget("bodystat_fat_current", "voice_fat_cur", "🎤 Say Current Body Fat %")
        st.number_input("Body Fat %", min_value=0.0, max_value=100.0, step=0.1, key="bodystat_fat_current")
    with col_target:
        st.markdown("**Target**")
        voice_number_input_widget("bodystat_weight_target", "voice_weight_tgt", "🎤 Say Target Weight")
        st.number_input("Weight (kg)", min_value=0.0, max_value=300.0, step=0.1, key="bodystat_weight_target")
        voice_number_input_widget("bodystat_fat_target", "voice_fat_tgt", "🎤 Say Target Body Fat %")
        st.number_input("Body Fat %", min_value=0.0, max_value=100.0, step=0.1, key="bodystat_fat_target")

    height_m = st.session_state["bodystat_height"] / 100.0 if st.session_state["bodystat_height"] > 0 else 0
    bmi_current = round(st.session_state["bodystat_weight_current"] / (height_m ** 2), 1) if height_m > 0 and st.session_state["bodystat_weight_current"] > 0 else 0.0
    bmi_target = round(st.session_state["bodystat_weight_target"] / (height_m ** 2), 1) if height_m > 0 and st.session_state["bodystat_weight_target"] > 0 else 0.0

    bmi_col1, bmi_col2 = st.columns(2)
    bmi_col1.metric("Current BMI", bmi_current if bmi_current > 0 else "—")
    bmi_col2.metric("Target BMI", bmi_target if bmi_target > 0 else "—")

    if st.button("💾 Save Today's Body Stats", use_container_width=True):
        stat_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_new_log({
            "Timestamp": stat_timestamp, "Section": "BodyStats", "Score": 0, "Notes": "Current",
            "AI_Summary": f"Weight: {st.session_state['bodystat_weight_current']}kg | BMI: {bmi_current} | Fat%: {st.session_state['bodystat_fat_current']}",
            "Raw_Content": json.dumps({"weight": st.session_state["bodystat_weight_current"], "height": st.session_state["bodystat_height"], "bmi": bmi_current, "fat_pct": st.session_state["bodystat_fat_current"]})
        })
        commit_new_log({
            "Timestamp": stat_timestamp, "Section": "BodyStats", "Score": 0, "Notes": "Target",
            "AI_Summary": f"Target Weight: {st.session_state['bodystat_weight_target']}kg | Target BMI: {bmi_target} | Target Fat%: {st.session_state['bodystat_fat_target']}",
            "Raw_Content": json.dumps({"weight": st.session_state["bodystat_weight_target"], "height": st.session_state["bodystat_height"], "bmi": bmi_target, "fat_pct": st.session_state["bodystat_fat_target"]})
        })
        st.success("Body stats saved — chart updated below!")
        time.sleep(0.5)
        st.rerun()

    body_stats_current_rows = history_df[(history_df["Section"] == "BodyStats") & (history_df["Notes"] == "Current")] if not history_df.empty else pd.DataFrame()
    if not body_stats_current_rows.empty:
        chart_records = []
        for _, srow in body_stats_current_rows.sort_values("Timestamp").iterrows():
            try:
                parsed = json.loads(str(srow["Raw_Content"]))
                chart_records.append({
                    "Timestamp": srow["Timestamp"],
                    "Weight (kg)": parsed.get("weight"),
                    "BMI": parsed.get("bmi"),
                    "Body Fat %": parsed.get("fat_pct")
                })
            except Exception:
                continue
        if chart_records:
            chart_df = pd.DataFrame(chart_records).set_index("Timestamp")
            st.markdown("**📈 Weight Progress**")
            st.line_chart(chart_df[["Weight (kg)"]])
            st.markdown("**📈 BMI Progress**")
            st.line_chart(chart_df[["BMI"]])
            st.markdown("**📈 Body Fat % Progress**")
            st.line_chart(chart_df[["Body Fat %"]])
    else:
        st.caption("No body stat history yet — save your first entry above to start tracking progress.")
    st.write("---")

    # ---------- SUBSECTION 5: DOCUMENT VAULT (unchanged behavior) ----------
    st.markdown("### 📂 Uploaded Health Documents")
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

    # ---------- SUBSECTION 1: 50-60 LINE GROUPED BLUEPRINT ----------
    if not history_df.empty:
        l_data = history_df[history_df["Section"] == "Learning"]
        st.metric(label="Total Library Assets Stacked", value=len(l_data))
        
        st.markdown("### ⚡ Master Life Implementation Sheet")
        if st.button("✨ GENERATE 50-60 LINE TAILORMADE BLUEPRINT FROM ALL FILES", use_container_width=True, key="gen_l_rules"):
            valid_contents = [str(r['Raw_Content']) for _, r in l_data.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "ceiling met", "v1beta", "connection refused", "engine error", "timeout", "status 404", "rejected the request"])]
            
            if valid_contents:
                combined_text = "\n\n".join(valid_contents)
                with st.spinner(f"Compiling content from {len(valid_contents)} files across your library..."):
                    prompt = f"""You are an elite high-performance mentor working for Animesh, an entrepreneur running Life Agro, WellWorld Foods, Jiva Leathers, and Khemka Woodcraft. Review the FULL text content below from ALL books and records in his library — there may be several distinct documents. Pull the best, most varied insights from EACH document, not just the first or most prominent one, so the final output genuinely represents the whole library rather than a single source.

Organize the output into 4-6 clearly labeled categories relevant to his situation (for example: 'Mindset & Psychology', 'Execution & Discipline', 'Relationships & Influence', 'Decision-Making Under Pressure', 'Leadership & Delegation') — pick categories that actually fit the content present. Under each category header, list specific, actionable, tailor-made points as bullet points for easy scanning.

Your complete output must total between 50 and 60 lines across all categories combined. Prioritize variety — draw distinct points from as many different source documents as possible rather than concentrating on one:

{combined_text[:50000]}"""
                    st.session_state["l_master_rules"] = call_gemini_engine(prompt)
            else:
                st.warning("No clean book text fields found in your history log matrix yet. Upload a fresh document down below first!")
                
        if "l_master_rules" in st.session_state:
            st.info(st.session_state["l_master_rules"])
    st.write("---")

    # ---------- SUBSECTION 2: PROGRESS TRACKER (live, no history) ----------
    st.markdown("### 📊 Today's Learning Progress Tracker")
    learning_habit_items = [
        ("📖 Read good books", "track_read_books"),
        ("🎬 Watch good content only", "track_good_content"),
        ("🤖 Proper use and learning of AI", "track_ai_learning"),
        ("🗣️ Interaction & discussions with the right people", "track_right_people"),
        ("🎵 Develop good hobbies (singing, instrument, boxing etc.)", "track_hobbies"),
    ]
    for label, key in learning_habit_items:
        if key not in st.session_state:
            st.session_state[key] = 5
        st.slider(label, 1, 10, key=key)
    st.caption("Live self-ratings for today — these reset when the app reloads and aren't saved to history.")
    st.write("---")

    # ---------- SUBSECTION 3: DOCUMENT VAULT (original file preview + bulleted summaries) ----------
    st.markdown("### 📂 Uploaded Documents")
    if not history_df.empty:
        l_data = history_df[history_df["Section"] == "Learning"]
        if not l_data.empty:
            st.write("### 📜 Library Summaries & Document Reader:")
            for idx, (_, row) in enumerate(l_data.iloc[::-1].iterrows()):
                ai_sum = str(row.get('AI_Summary', ''))
                raw_text = str(row.get("Raw_Content", ""))
                file_path = str(row.get('FilePath', '') or '')
                timestamp_str = str(row['Timestamp'])
                row_id = str(row.get('RowID', '') or f"legacy_{timestamp_str}_{idx}")
                title_slug = str(row.get('Notes', 'Book File')).split('|')[0]
                original_filename = title_slug.replace("📄", "").strip()
                
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
                            repair_prompt = f"Analyze the text content of this book document. Provide a clean, thorough summary detailing the exact key findings and what this specific document states. Focus on central lessons, actionable business insights, and execution frameworks. Format the summary as clear markdown bullet points (8-10 bullets), each a distinct, specific insight — not a prose paragraph:\n\n{raw_text[:25000]}"
                            regenerate_summary_for_row(row_id, "Learning", raw_text, repair_prompt)
                        st.success("Summary generated and saved permanently!")
                        time.sleep(0.5)
                        st.rerun()
                    with st.expander("📂 Click to view original raw file text"):
                        st.text_area("Original Extracted Content", value=raw_text, height=250, disabled=True, key=f"raw_l_{row_id}")

                if file_path:
                    with st.expander("🖼️ View original file (same format as uploaded)"):
                        render_original_file_preview(file_path, original_filename)

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
                    vault_filename = f"library_{media_name.replace(' ','_')}_{b.name}"
                    save_file_to_github(b.getvalue(), vault_filename)
                    single_book_text = extract_raw_text(b)
                    
                    prompt = f"Analyze the text extracted from this specific document ({b.name}). Provide a clean, deep-dive content summary detailing the key findings and exactly what this document states. Cover all central themes, workflows, and actionable workflows explicitly. Format the summary as clear markdown bullet points (8-10 bullets), each a distinct, specific insight — not a prose paragraph:\n\n{single_book_text[:28000]}"
                    ai_summary = call_gemini_engine(prompt)
                    
                    commit_new_log({
                        "Timestamp": timestamp, 
                        "Section": "Learning", 
                        "Score": 10, 
                        "Notes": f"📄 {b.name} | Batch: {media_name}",
                        "AI_Summary": ai_summary,
                        "Raw_Content": single_book_text,
                        "FilePath": f"vault/{vault_filename}"
                    })
            if skipped:
                st.warning(f"Skipped {len(skipped)} duplicate file(s) already in your library: {', '.join(skipped)}. Delete the existing card first if you want to re-process one.")
            st.success("🎉 All new documents successfully isolated, analyzed, and synced!")
            time.sleep(0.5)
            st.rerun()
    st.write("---")

    # ---------- SUBSECTION 4: DAILY MOTIVATIONAL QUOTE (AI-generated, cached per day) ----------
    st.markdown("### 💬 Today's Learning Motivation")
    today_str = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.get("learning_quote_date") != today_str:
        quote_prompt = "Give me one short, powerful, original motivational quote (a single sentence, under 25 words) about continuous learning, reading, curiosity, or self-development. Do not attribute it to any real named person — present it as general wisdom, unattributed. Return ONLY the quote text itself, no quotation marks, no attribution, no commentary."
        with st.spinner("Fetching today's learning motivation..."):
            st.session_state["learning_quote"] = call_gemini_engine(quote_prompt)
        st.session_state["learning_quote_date"] = today_str
    st.info(f"_{st.session_state.get('learning_quote', '')}_")
    st.write("---")

    # ---------- SUBSECTION 5: BOOK / PODCAST SUMMARIZER ----------
    st.markdown("### 🔎 Summarize Any Book or Podcast")
    book_query = st.text_input("Enter a book or podcast name:", key="book_query_input")
    if st.button("✨ Summarize Key Learnings", use_container_width=True, key="summarize_book_btn"):
        if book_query.strip():
            summarize_prompt = f"""Provide a deep-dive summary of the key learnings, frameworks, and actionable insights from '{book_query}'. If this is a well-known book or podcast you have real knowledge of, draw on that. If you are not confident you know this specific title's actual content, say so honestly rather than inventing details. Format the summary as clear markdown bullet points (8-15 bullets), each one a distinct, specific insight — not generic filler."""
            with st.spinner(f"Researching key learnings from '{book_query}'..."):
                st.session_state["book_summary_result"] = call_gemini_engine(summarize_prompt)
                st.session_state["book_summary_title"] = book_query
        else:
            st.warning("Please enter a book or podcast name first.")

    if "book_summary_result" in st.session_state:
        st.markdown(f"#### {st.session_state['book_summary_title']}")
        st.markdown(st.session_state["book_summary_result"])
        if st.button("➕ Add to My Knowledge Bank", use_container_width=True, key="add_book_to_bank"):
            commit_new_log({
                "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Section": "Learning",
                "Score": 10,
                "Notes": f"📄 {st.session_state['book_summary_title']} | AI-Researched Summary",
                "AI_Summary": st.session_state["book_summary_result"],
                "Raw_Content": st.session_state["book_summary_result"],
                "FilePath": ""
            })
            st.success("Added to your Knowledge Bank!")
            del st.session_state["book_summary_result"]
            del st.session_state["book_summary_title"]
            time.sleep(0.5)
            st.rerun()

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")

    # ---------- SUBSECTION 1: VENTURE SNAPSHOT (per-venture todos, uploads, AI strategy) ----------
    st.markdown("### 🏭 Venture Snapshot")
    for venture in BUSINESS_VENTURES:
        render_venture_panel(venture)

    # ---------- SUBSECTION 2: AI ADVISOR FOR IDEAS ----------
    st.markdown("### 🎯 Ask Your Business Advisor")
    voice_input_widget("advisor_question", "voice_advisor")
    advisor_question = st.text_area("Share a business idea, thought, or strategy question:", key="advisor_question")
    if st.button("🎯 Get My Advisor's Take", use_container_width=True, key="get_advisor_take"):
        if advisor_question.strip():
            advisor_prompt = f"""You are an elite personal business advisor to Animesh, a CA/CFA/MBA entrepreneur running Life Agro (fortified rice), WellWorld Foods (exports), Jiva Leathers (vegan leather), and Khemka Woodcraft (timber import), with prior investment banking experience. He has shared the following idea, thought, or strategy question:

"{advisor_question}"

Respond as a sharp, honest personal advisor would: give your genuine read on the idea, flag real risks or blind spots, and give concrete, specific suggestions on how to make it work or improve it. Be direct and practical, not generic cheerleading. Format as clear markdown with short paragraphs or bullet points."""
            with st.spinner("Consulting your advisor..."):
                advisor_answer = call_gemini_engine(advisor_prompt)
            if "advisor_history" not in st.session_state:
                st.session_state["advisor_history"] = []
            st.session_state["advisor_history"].insert(0, {"question": advisor_question, "answer": advisor_answer, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.rerun()
        else:
            st.warning("Please share your idea or question first.")

    if "advisor_history" in st.session_state and st.session_state["advisor_history"]:
        for i, exchange in enumerate(st.session_state["advisor_history"]):
            preview = exchange['question'][:60] + ("..." if len(exchange['question']) > 60 else "")
            with st.expander(f"💭 {preview}  ({exchange['timestamp']})", expanded=(i == 0)):
                st.markdown(exchange["answer"])
    st.write("---")

    # ---------- SUBSECTION 3: PROGRESS TRACKER (live, no history) ----------
    st.markdown("### 📊 Today's Business Progress Tracker")
    business_habit_items = [
        ("📵 Deep work blocks everyday without phone", "track_deep_work"),
        ("💡 Ideate & deep thinking everyday (stocks, new businesses)", "track_ideate"),
        ("🤝 Delegate daily execution tasks efficiently", "track_delegate"),
        ("✅ Completing Things to Do diligently everyday", "track_complete_todos"),
    ]
    for label, key in business_habit_items:
        if key not in st.session_state:
            st.session_state[key] = 5
        st.slider(label, 1, 10, key=key)
    st.caption("Live self-ratings for today — these reset when the app reloads and aren't saved to history.")
    st.write("---")

    # ---------- SUBSECTION 4: MOTIVATIONAL QUOTE (curated business leaders, rotates daily) ----------
    st.markdown("### 💬 Today's Business Motivation")
    biz_day_index = datetime.now().timetuple().tm_yday % len(BUSINESS_MOTIVATION_QUOTES)
    biz_quote_text, biz_quote_author = BUSINESS_MOTIVATION_QUOTES[biz_day_index]
    st.info(f"_{biz_quote_text}_\n\n— {biz_quote_author}")
    st.write("---")

    # ---------- SUBSECTION 5: GENERAL FILE UPLOAD, SUMMARY & RAW VIEW (unchanged behavior) ----------
    st.markdown("### 📂 General Business Documents")
    if not history_df.empty:
        b_data = history_df[history_df["Section"] == "Business"]
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
    st.header("🧘 Peace & Mindset")

    # ---------- SUBSECTION 1: PROGRESS TRACKER (live, no history) ----------
    st.markdown("### 📊 Today's Peace Progress Tracker")
    peace_habit_items = [
        ("🙏 Meditation & Puja everyday", "track_meditation_puja"),
        ("✨ Manifestation routine everyday", "track_manifestation_routine"),
        ("📓 Journalling every night", "track_journalling"),
        ("😌 Total control of positive mindset & emotions", "track_mindset_control"),
        ("🔮 Follow astrological suggestions and remedies", "track_astro_remedies"),
        ("⏳ Preserve energy, time & focus like treasures", "track_preserve_energy"),
        ("🚫 Stay away from negative people & relatives", "track_avoid_negativity"),
    ]
    for label, key in peace_habit_items:
        if key not in st.session_state:
            st.session_state[key] = 5
        st.slider(label, 1, 10, key=key)
    st.caption("Live self-ratings for today — these reset when the app reloads and aren't saved to history.")
    st.write("---")

    # ---------- SUBSECTION 2: DAILY QUOTE / MEDITATION TECHNIQUE / MANIFESTATION PRACTICE (AI-generated, cached per day) ----------
    st.markdown("### 💬 Daily Peace & Positivity")
    peace_today_str = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.get("peace_content_date") != peace_today_str:
        peace_prompt = """Provide three short sections for a daily wellness check-in, each clearly headed with a markdown bold header:

**Quote of the Day** — one short, original, unattributed motivational quote (under 25 words) about mental peace, happiness, or positivity.

**Meditation & Breathing Technique** — one specific, practical meditation or breathing technique to try today, explained in 3-4 concise sentences.

**Manifestation Practice** — one specific manifestation technique or exercise to try today, explained in 3-4 concise sentences.

Keep the whole response tight and practical, no filler."""
        with st.spinner("Fetching today's peace & positivity content..."):
            st.session_state["peace_content"] = call_gemini_engine(peace_prompt)
        st.session_state["peace_content_date"] = peace_today_str
    st.markdown(st.session_state.get("peace_content", ""))
    st.write("---")

    # ---------- SUBSECTION 3: KRISHNA — AI SPIRITUAL ADVISOR ----------
    st.markdown("### 🕉️ Ask Krishna — Your Spiritual Advisor")
    voice_input_widget("krishna_question", "voice_krishna")
    krishna_question = st.text_area("Share what's on your mind — feelings, doubts, grievances, or your current mood:", key="krishna_question")
    if st.button("🙏 Seek Guidance", use_container_width=True, key="ask_krishna"):
        if krishna_question.strip():
            krishna_prompt = f"""You are a wise, compassionate spiritual guide, drawing on the wisdom and teachings of Lord Krishna from the Bhagavad Gita, speaking personally to Animesh. He has shared the following with you:

"{krishna_question}"

Respond with warmth, wisdom, and genuine emotional insight — help him understand and process what he's feeling, offer perspective on staying calm and centered, and give practical guidance on how to handle the situation with grace and clarity, in the spirit of Krishna's teachings on duty, detachment, and inner peace. Keep it personal and grounded, not preachy or generic.

If anything in what he shared suggests he may be in real emotional crisis or having thoughts of self-harm, gently and clearly encourage him to also reach out to a mental health professional or a trusted person immediately, alongside any spiritual guidance you offer."""
            with st.spinner("Seeking guidance..."):
                krishna_answer = call_gemini_engine(krishna_prompt)
            if "krishna_history" not in st.session_state:
                st.session_state["krishna_history"] = []
            st.session_state["krishna_history"].insert(0, {"question": krishna_question, "answer": krishna_answer, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.rerun()
        else:
            st.warning("Please share what's on your mind first.")

    if "krishna_history" in st.session_state and st.session_state["krishna_history"]:
        for i, exchange in enumerate(st.session_state["krishna_history"]):
            preview = exchange['question'][:60] + ("..." if len(exchange['question']) > 60 else "")
            with st.expander(f"🙏 {preview}  ({exchange['timestamp']})", expanded=(i == 0)):
                st.markdown(exchange["answer"])
    st.write("---")

    # ---------- SUBSECTION 4: ASTROLOGICAL GUIDANCE (daily reading, cached per day + chart vault) ----------
    st.markdown("### 🔮 Astrological Guidance")

    astro_data = history_df[history_df["Section"] == "Mindset"] if not history_df.empty else pd.DataFrame()
    astro_valid_contents = []
    if not astro_data.empty:
        astro_valid_contents = [str(r['Raw_Content']) for _, r in astro_data.iterrows() if not any(err in str(r['Raw_Content']).lower() for err in ["unable to compile", "connection refused", "engine error", "rejected the request"])]

    astro_today_str = datetime.now().strftime("%Y-%m-%d")
    if astro_valid_contents:
        if st.session_state.get("astro_reading_date") != astro_today_str:
            astro_context = "\n\n".join(astro_valid_contents)[:35000]
            astro_prompt = f"""You are an expert Vedic astrologer analyzing Animesh's uploaded birth charts below. Provide today's astrological reading in this exact structure with markdown bold headers:

**Quick Summary** — 3-4 sentences giving the headline read for today.

**Short-Term Outlook (this week)** — a few practical, specific points.

**Long-Term Outlook** — a few practical, specific points on broader life themes currently in play.

**Remedies & Recommendations** — specific, actionable suggestions (e.g. gemstones to consider, favorable days or timings, practices to follow) to help maximize luck and navigate current planetary influences.

Base this on the chart data below. If the chart data is incomplete or unclear, say so honestly rather than inventing specifics:

{astro_context}"""
            with st.spinner("Consulting the charts for today's reading..."):
                st.session_state["astro_reading"] = call_gemini_engine(astro_prompt)
            st.session_state["astro_reading_date"] = astro_today_str
        st.markdown(st.session_state.get("astro_reading", ""))
        if st.button("🔄 Refresh Today's Reading", key="refresh_astro"):
            if "astro_reading_date" in st.session_state:
                del st.session_state["astro_reading_date"]
            st.rerun()
        st.write("---")
    else:
        st.caption("Upload a birth chart below to get your daily astrological reading.")

    if not astro_data.empty:
        st.write("### 📜 Uploaded Charts:")
        for idx, (_, row) in enumerate(astro_data.iloc[::-1].iterrows()):
            title_slug = str(row.get('Notes', 'Chart')).split('|')[0]
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
                if "astro_reading_date" in st.session_state:
                    del st.session_state["astro_reading_date"]
                st.success("Entry deleted.")
                time.sleep(0.3)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    astro_files = st.file_uploader("Drop planetary maps/birth charts (any format — PDF, image, Word, Excel):", type=["pdf", "png", "jpg", "docx", "xlsx"], accept_multiple_files=True, key="a_bulk")
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
            if "astro_reading_date" in st.session_state:
                del st.session_state["astro_reading_date"]
            st.rerun()

# ==========================================
# 5. RELATIONSHIPS MODULE
# ==========================================
with tab5:
    st.header("🤝 Relationships")

    # ---------- SUBSECTION 1: PROGRESS TRACKER (live, no history) ----------
    st.markdown("### 📊 Today's Relationships Progress Tracker")
    relationship_habit_items = [
        ("📵 Less screen time and more interaction", "track_less_screen_interaction"),
        ("🎉 More personal outings & activities", "track_personal_outings"),
        ("😌 Less reactive & more calm", "track_less_reactive"),
        ("✨ Manifestation for better relationships", "track_relationship_manifestation"),
    ]
    for label, key in relationship_habit_items:
        if key not in st.session_state:
            st.session_state[key] = 5
        st.slider(label, 1, 10, key=key)
    st.caption("Live self-ratings for today — these reset when the app reloads and aren't saved to history.")
    st.write("---")

    # ---------- SUBSECTION 2: KRISHNA — AI RELATIONSHIP ADVISOR ----------
    st.markdown("### 🕉️ Ask Krishna — Relationship Guidance")
    voice_input_widget("krishna_relationship_question", "voice_krishna_rel")
    krishna_relationship_question = st.text_area("Share what's on your mind about a relationship — feelings, doubts, grievances, or your current mood:", key="krishna_relationship_question")
    if st.button("🙏 Seek Guidance", use_container_width=True, key="ask_krishna_rel"):
        if krishna_relationship_question.strip():
            krishna_rel_prompt = f"""You are a wise, compassionate spiritual guide, drawing on the wisdom and teachings of Lord Krishna from the Bhagavad Gita, speaking personally to Animesh about his relationships. He has shared the following with you:

"{krishna_relationship_question}"

Respond with warmth, wisdom, and genuine emotional insight — help him understand what he's feeling, offer perspective on approaching the relationship with patience and clarity, and give practical guidance on how to handle the situation in the best possible manner, in the spirit of Krishna's teachings on duty, compassion, and right action.

If anything in what he shared suggests he may be in real emotional crisis or having thoughts of self-harm, gently and clearly encourage him to also reach out to a mental health professional or a trusted person immediately, alongside any spiritual guidance you offer."""
            with st.spinner("Seeking guidance..."):
                krishna_rel_answer = call_gemini_engine(krishna_rel_prompt)
            if "krishna_relationship_history" not in st.session_state:
                st.session_state["krishna_relationship_history"] = []
            st.session_state["krishna_relationship_history"].insert(0, {"question": krishna_relationship_question, "answer": krishna_rel_answer, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.rerun()
        else:
            st.warning("Please share what's on your mind first.")

    if "krishna_relationship_history" in st.session_state and st.session_state["krishna_relationship_history"]:
        for i, exchange in enumerate(st.session_state["krishna_relationship_history"]):
            preview = exchange['question'][:60] + ("..." if len(exchange['question']) > 60 else "")
            with st.expander(f"🙏 {preview}  ({exchange['timestamp']})", expanded=(i == 0)):
                st.markdown(exchange["answer"])

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
