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
st.set_page_config(page_title="Khemka Life OS", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container {padding-top: 0.5rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold;}
        .sync-btn>div>button {background-color: #059669 !important; color: white !important; border: none;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; background-color: #F3F4F6; border-radius: 6px; font-size: 11px;}
        .file-card {background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
        .tip-box {background-color: #ECFDF5; border-left: 4px solid #10B981; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;}
        .quote-box {background-color: #F3F4F6; border-left: 4px solid #6B7280; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; font-style: italic;}
        .guru-box {background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;}
        .tracker-header {font-size: 14px; font-weight: bold; color: #374151; margin-bottom: -10px;}
    </style>
""", unsafe_allow_html=True)

TOKEN = st.secrets.get("GITHUB_TOKEN", "").strip()
REPO = st.secrets.get("GITHUB_REPO", "").strip()
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()

# ==========================================
# ⚡ DYNAMIC DAILY CONTENT ENGINES
# ==========================================
def get_daily_content(category):
    day = datetime.now().timetuple().tm_yday
    content = {
        "health_quotes": [
            "Your body hears everything your mind says. Keep it clean and strong.",
            "Physical vitality is the ultimate launchpad for business execution.",
            "Fitness is a shield built daily. Steps, sleep, and discipline matter."
        ],
        "learning_quotes": [
            "Continuous self-development is the minimum speed required to lead global fields.",
            "An investment in deeper master skills pays the ultimate interest.",
            "Acquiring new vector parameters daily separates commodity from high-end empire."
        ],
        "biz_quotes": [
            "Vision without execution is hallucination. Delegate, ideate, dominate.",
            "Deep work blocks build empires. Distraction destroys them.",
            "Focus on the macro strategy; delegate the micro execution."
        ],
        "peace_quotes": [
            "Peace is not the absence of chaos, but the mastery of mind within it.",
            "Preserve your energy, time, and focus like the absolute treasures they are.",
            "A calm mind can navigate any market, any relationship, and any storm."
        ],
        "goals_quotes": [
            "Set the target, map the vectors, execute relentlessly.",
            "Long-term empires are built on the back of short-term discipline.",
            "Do not lower your goals to the level of your abilities. Raise your abilities to the height of your goals."
        ],
        "meditation": [
            "**Today's Technique:** 4-7-8 Breathing. Inhale for 4 seconds, hold for 7, exhale forcefully for 8. Repeat 4 times to instantly reset the nervous system.",
            "**Today's Technique:** Box Breathing. Inhale 4s, hold 4s, exhale 4s, hold 4s. Use this before entering deep work blocks.",
            "**Today's Technique:** Body Scan. Spend 5 minutes mentally scanning from toes to head, actively releasing tension in each muscle group."
        ],
        "manifestation": [
            "**Today's Practice:** Visualization. Spend 3 minutes seeing your ultimate global export empire operating at full capacity. Feel the reality of it.",
            "**Today's Practice:** Gratitude Journaling. Write down 3 micro-wins from yesterday to tune your reticular activating system to success.",
            "**Today's Practice:** Identity Affirmation. 'I am a highly disciplined, calm, and visionary operator building a legacy.' Repeat 10 times."
        ]
    }
    return content[category][day % len(content[category])]

# ==========================================
# ⚡ AI ENGINE (Upgraded for Multi-Modal Files)
# ==========================================
def call_gemini_engine(prompt_text, file_bytes=None, mime_type=None):
    if not API_KEY:
        return "⚠️ Gemini API Key missing in Settings -> Secrets."

    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']
    headers = {"Content-Type": "application/json"}
    
    parts = [{"text": prompt_text}]
    if file_bytes and mime_type:
        parts.append({
            "inline_data": {
                "mime_type": mime_type, 
                "data": base64.b64encode(file_bytes).decode("utf-8")
            }
        })
        
    payload = {"contents": [{"parts": parts}]}
    debug_logs = []
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=40)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                debug_logs.append(f"[{model_name}]: HTTP {response.status_code} - {response.text[:150]}")
        except Exception as e:
            debug_logs.append(f"[{model_name}]: Exception - {str(e)[:150]}")
            continue

    return "❌ Gemini request failed. Diagnostic Log:\n" + "\n".join(debug_logs)

# ==========================================
# ⚡ VOICE-TO-TEXT ENGINE
# ==========================================
def transcribe_audio_with_gemini(audio_bytes):
    if not API_KEY or not audio_bytes: return None
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                {"text": "Transcribe this audio recording verbatim into clean, well-punctuated text. Return ONLY the transcription itself."}
            ]
        }]
    }
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except: continue
    return None

def voice_input_widget(target_session_key, widget_key, label="🎤 Record Voice Note"):
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

# ==========================================
# ⚡ NATIVE LOCAL FILE TEXT EXTRACTOR
# ==========================================
def extract_raw_text(uploaded_file):
    if uploaded_file is None: return ""
    try:
        name = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()
        if name.endswith(".txt"): return file_bytes.decode("utf-8", errors="ignore")
        elif name.endswith(".docx"):
            wb_io = BytesIO(file_bytes)
            with zipfile.ZipFile(wb_io) as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text_pieces = [node.text for node in root.findall('.//w:t', ns) if node.text]
                return "\n".join(text_pieces)
        elif name.endswith(".csv"): return pd.read_csv(BytesIO(file_bytes)).to_string()
        elif name.endswith(".xlsx") or name.endswith(".xls"): return pd.read_excel(BytesIO(file_bytes)).to_string()
        else: return f"[Binary File Uploaded: {uploaded_file.name}]"
    except Exception as e:
        return f"[Text extraction note: {str(e)}]"

# ==========================================
# ⚡ SECURE MULTI-DEVICE DATA LOCKER PIPELINE
# ==========================================
def save_file_to_github(file_bytes, filename, folder="vault"):
    if not TOKEN or not REPO: return False
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json", "Cache-Control": "no-cache"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"message": f"Cloud Upload: {filename}", "content": encoded_content}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def sync_entire_db_to_github():
    if not TOKEN or not REPO: return False
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json", "Cache-Control": "no-cache"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    df_to_save = st.session_state["cached_db"]
    encoded_content = base64.b64encode(df_to_save.to_csv(index=False).encode("utf-8")).decode("utf-8")
    payload = {"message": "Database Sync Event", "content": encoded_content, "sha": sha if sha else None}
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def load_live_database_uncached():
    if not TOKEN or not REPO: return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID"])
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv?t={int(time.time())}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json", "Cache-Control": "no-cache"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content_b64 = res.json().get("content", "")
            loaded_df = pd.read_csv(BytesIO(base64.b64decode(content_b64).decode("utf-8")))
            if "AI_Summary" not in loaded_df.columns: loaded_df["AI_Summary"] = ""
            if "Raw_Content" not in loaded_df.columns: loaded_df["Raw_Content"] = ""
            if "RowID" not in loaded_df.columns: loaded_df["RowID"] = ""
            missing_id_mask = loaded_df["RowID"].isna() | (loaded_df["RowID"].astype(str).str.strip() == "")
            if missing_id_mask.any():
                loaded_df.loc[missing_id_mask, "RowID"] = [uuid.uuid4().hex for _ in range(int(missing_id_mask.sum()))]
            return loaded_df
    except: pass
    return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content", "RowID"])

def commit_new_log(row_dict):
    if "AI_Summary" not in row_dict: row_dict["AI_Summary"] = ""
    if "Raw_Content" not in row_dict: row_dict["Raw_Content"] = ""
    if not row_dict.get("RowID"): row_dict["RowID"] = uuid.uuid4().hex
    if st.session_state["cached_db"].empty:
        st.session_state["cached_db"] = pd.DataFrame([row_dict])
    else:
        st.session_state["cached_db"] = pd.concat([st.session_state["cached_db"], pd.DataFrame([row_dict])], ignore_index=True)
    sync_entire_db_to_github()

def regenerate_summary_for_row(row_id, section, raw_text, prompt_template):
    resolved_summary = call_gemini_engine(prompt_template)
    st.session_state["cached_db"].loc[
        (st.session_state["cached_db"]["RowID"] == row_id) & (st.session_state["cached_db"]["Section"] == section), "AI_Summary"
    ] = resolved_summary
    sync_entire_db_to_github()

def delete_row(row_id, section):
    st.session_state["cached_db"] = st.session_state["cached_db"][
        ~((st.session_state["cached_db"]["RowID"] == row_id) & (st.session_state["cached_db"]["Section"] == section))
    ].reset_index(drop=True)
    sync_entire_db_to_github()

def get_existing_filenames(section):
    if history_df.empty: return set()
    section_notes = history_df[history_df["Section"] == section]["Notes"].astype(str)
    existing = set()
    for note in section_notes:
        if "📄" in note:
            try: existing.add(note.split("📄", 1)[1].split("|", 1)[0].strip())
            except: pass
    return existing

# ==========================================
# MASTER DATA INITIALIZATION
# ==========================================
if "cached_db" not in st.session_state: st.session_state["cached_db"] = load_live_database_uncached()
for col in ["AI_Summary", "Raw_Content", "RowID"]:
    if col not in st.session_state["cached_db"].columns: st.session_state["cached_db"][col] = ""

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
# ❤️ TAB 1: HEALTH & FITNESS MODULE
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Command Center")
    
    st.markdown("### 📋 Daily Fitness Core Protocol")
    st.markdown('<div class="tip-box">', unsafe_allow_html=True)
    st.markdown("""
    **Follow these non-negotiable protocols daily:**
    1. 💧 **Hydration Engine:** Drink at least 2 liters of magic water daily.
    2. 🏃 **Daily Activity:** Exercise / run every morning targeting 20,000 steps.
    3. 🛌 **Circadian Sleep Window:** Lock down recovery cycles strictly by sleeping at 10 PM and waking at 5 AM.
    4. 🥦 **Nutritional Shielding:** Proper & healthy food only — no junk food, zero sugar, proper protein.
    5. 🫁 **Respiratory Reset:** Execute deep breathing exercises daily.
    6. 🚿 **Dopamine Reset:** Take cold showers daily.
    7. 🚶 **NEAT Activity:** Take only the stairs, never the lift.
    8. 📵 **Digital Boundaries:** No gadgets in the washroom & strictly no screens after 9:30 PM.
    9. 🧘 **Mental Clarity:** Execute a proper digital detox window daily.
    10. 🦷 **Oral Hygiene:** Brush 2 times a day properly.
    11. 🧴 **Dermatology:** Maintain proper skincare & hygiene routine.
    12. 🧬 **Hormonal Health:** Actively follow routines to increase and maintain Testosterone levels.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### 📈 Daily Habit Progress Indicators")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Proper sleep timings (10-5)", 1, 10, 7, key="tk_h1")
        st.slider("Exercise/running (20000 steps)", 1, 10, 7, key="tk_h2")
        st.slider("Drink magic water (2+ Ltrs)", 1, 10, 7, key="tk_h3")
        st.slider("Deep breathing exercises", 1, 10, 7, key="tk_h4")
        st.slider("Cold showers for dopamine", 1, 10, 7, key="tk_h5")
        st.slider("Take only stairs not lift", 1, 10, 7, key="tk_h6")
    with col2:
        st.slider("No gadgets in washroom & after 9.30PM", 1, 10, 7, key="tk_h7")
        st.slider("Digital detox", 1, 10, 7, key="tk_h8")
        st.slider("Proper food - no junk/sugar, high protein", 1, 10, 7, key="tk_h9")
        st.slider("Brush 2 times a day properly", 1, 10, 7, key="tk_h10")
        st.slider("Proper skin care & hygiene", 1, 10, 7, key="tk_h11")
        st.slider("Increase Testosterone levels", 1, 10, 7, key="tk_h12")
        
    st.markdown("### 🌌 Daily Mindset Spark")
    st.markdown(f'<div class="quote-box">"{get_daily_content("health_quotes")}"</div>', unsafe_allow_html=True)
    
    st.markdown("### 📊 Body Composition Dashboard")
    voice_input_widget("h_stats_pad", "voice_health_stats", label="🎤 Dictate Body Stats (Weight, BMI, Fat % - Current & Target)")
    stats_voice_capture = st.text_area("Metrics Command Matrix Analyzer:", key="h_stats_pad", placeholder="Example: Current Weight 75, Target Weight 70, Current Fat 14%, Target Fat 12%, Current BMI 22.4")
    
    if st.button("💾 Parse & Append Body Stats Data Stream", use_container_width=True):
        if stats_voice_capture:
            with st.spinner("Decoding layout parameter values..."):
                parse_prompt = f"Extract numerical entries for current weight, target weight, current fat, target fat, and current BMI. Output ONLY a comma-separated array string exactly matching this schema: CurrentWeight,TargetWeight,CurrentFat,TargetFat,CurrentBMI:\n\n{stats_voice_capture}"
                parsed_res = call_gemini_engine(parse_prompt).strip()
                try:
                    p = [float(val.strip()) for val in parsed_res.split(",")]
                    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    commit_new_log({
                        "Timestamp": timestamp, "Section": "Health_Stats", "Score": p[0], "Notes": f"Body Stats Update",
                        "AI_Summary": f"### Body Stat Calibration:\n* **Weight:** {p[0]}kg (Target {p[1]}kg)\n* **Fat:** {p[2]}% (Target {p[3]}%)\n* **BMI:** {p[4]}",
                        "Raw_Content": f"{p[0]},{p[1]},{p[2]},{p[3]},{p[4]}"
                    })
                    st.success("Body statistics synced cleanly!")
                    time.sleep(0.4)
                    st.rerun()
                except: st.error("Extraction unaligned. Try structuring: 'Current Weight 75, Target 70, Fat 14, Target 12, BMI 22'")

    if not history_df.empty:
        stats_history = history_df[history_df["Section"] == "Health_Stats"]
        if not stats_history.empty:
            chart_entries = []
            for _, r in stats_history.iterrows():
                try:
                    vals = [float(v.strip()) for v in str(r["Raw_Content"]).split(",")]
                    chart_entries.append({"Date": r["Timestamp"][:10], "Weight": vals[0], "Target Weight": vals[1], "Fat %": vals[2], "Target Fat %": vals[3], "BMI": vals[4]})
                except: continue
            if chart_entries:
                df_metrics = pd.DataFrame(chart_entries).set_index("Date")
                c1, c2, c3 = st.columns(3)
                with c1: st.write("**Weight**"); st.line_chart(df_metrics[["Weight", "Target Weight"]])
                with c2: st.write("**Fat %**"); st.line_chart(df_metrics[["Fat %", "Target Fat %"]])
                with c3: st.write("**BMI**"); st.line_chart(df_metrics[["BMI"]])

    st.write("---")
    st.markdown("### 📂 Health Files & Diagnostics Vault")
    uploaded_files = st.file_uploader("Upload incoming health data files / logs:", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    if st.button("Inject File Vectors to Health Vault", use_container_width=True):
        if uploaded_files:
            for f in uploaded_files:
                f_bytes = f.getvalue()
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(f_bytes, f"health_{timestamp.replace(' ','_').replace(':','-')}_{f.name}")
                
                # Check if it's an image/pdf and use multimodal engine, else raw text
                mime_type = "application/pdf" if f.name.endswith(".pdf") else ("image/jpeg" if f.name.endswith(".jpg") or f.name.endswith(".jpeg") else "image/png" if f.name.endswith(".png") else None)
                if mime_type:
                    ai_summary = call_gemini_engine("Provide a clean, deep-dive content summary detailing the key findings of this health document. Focus on core observations and parameters. Strictly 8-10 lines long.", file_bytes=f_bytes, mime_type=mime_type)
                    raw_extracted = "[Image/PDF Multi-modal File]"
                else:
                    raw_extracted = extract_raw_text(f)
                    ai_summary = call_gemini_engine(f"Provide a clean, deep-dive content summary detailing the key findings. Strictly 8-10 lines long:\n\n{raw_extracted[:15000]}")
                
                commit_new_log({"Timestamp": timestamp, "Section": "Health", "Score": 10, "Notes": f"📄 {f.name}", "AI_Summary": ai_summary, "Raw_Content": raw_extracted})
            st.success("🎉 Repository file logs indexed successfully!")
            time.sleep(0.5)
            st.rerun()

    h_data = history_df[history_df["Section"] == "Health"]
    if not h_data.empty: 
        for idx, (_, row) in enumerate(h_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            st.markdown(f"#### {str(row.get('Notes', 'Health Item')).split('|')[0]}")
            st.caption(f"Archived on: {row['Timestamp']}")
            st.markdown(str(row.get('AI_Summary', '')))
            
            with st.expander("📂 Click to view original raw file text"):
                st.text_area("Original Content Stream", value=str(row.get("Raw_Content", "")), height=200, disabled=True, key=f"raw_h_{row_id}")
            if st.button("🗑️ Delete this record", key=f"delete_h_{row_id}"):
                delete_row(row_id, "Health"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 🧠 TAB 2: LEARNING & DEVELOPMENT MODULE
# ==========================================
with tab2:
    st.header("🧠 Master Knowledge Infrastructure")
    l_data = history_df[history_df["Section"] == "Learning"]
    
    st.markdown("### ⚡ Master Life Implementation Blueprint")
    if st.button("✨ SYNTHESIZE 50-60 LINE MASTER KNOWLEDGE BLUEPRINT", use_container_width=True, key="gen_l_rules"):
        valid_contents = [str(r['Raw_Content']) for _, r in l_data.iterrows() if "unable to compile" not in str(r['Raw_Content']).lower()]
        if valid_contents:
            with st.spinner("Scanning data vectors from all stacked knowledge modules..."):
                prompt = f"""You are an elite productivity strategist working for Animesh. Review the complete text content extracted from ALL books, articles, and learning assets stored inside his master knowledge bank. Pull distinct, highly varied execution blueprints from across the different documents.
Organize your output into 4-6 visually appealing, highly sharp category frameworks (e.g., 'Cognitive Strategy & Decision Maps', 'Operational Speed & Leverage Rules'). Under each category header, list concrete, high-impact bulleted pointers covering a wide variety of topics.
Your complete output text grid must be exactly between 50 and 60 lines long total across all categories combined:
{"\n\n".join(valid_contents)[:45000]}"""
                st.session_state["l_master_rules"] = call_gemini_engine(prompt)
        else: st.warning("No clean knowledge content matrix blocks found in history layers yet.")
            
    if "l_master_rules" in st.session_state:
        st.info(st.session_state["l_master_rules"])
        st.write("---")

    st.markdown("### 📈 Strategic Learning Habit Trackers")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Read good books", 1, 10, 7, key="tk_l1")
        st.slider("Watch good content only", 1, 10, 7, key="tk_l2")
        st.slider("Proper use and learning of AI", 1, 10, 7, key="tk_l3")
    with col2:
        st.slider("Interaction & discussions with the right people", 1, 10, 7, key="tk_l4")
        st.slider("Develop good hobbies (singing, instrument, boxing etc.)", 1, 10, 7, key="tk_l5")
        
    st.markdown("### 🧠 Continuous Self-Development Catalyst")
    st.markdown(f'<div class="quote-box">"{get_daily_content("learning_quotes")}"</div>', unsafe_allow_html=True)
    
    st.markdown("### ⚡ Direct Book & Podcast Summary Injector")
    inject_title = st.text_input("Enter Book or Podcast Title for On-the-Fly Injection:", placeholder="e.g., Principals by Ray Dalio")
    if st.button("🚀 Process One-Click AI Summary Into Master Bank", use_container_width=True):
        if inject_title:
            with st.spinner(f"Synthesizing knowledge fields for '{inject_title}'..."):
                prompt = f"Provide an intensive analysis detailing the central lessons, core concepts, and key strategic findings from the book or podcast titled '{inject_title}'. Format the response entirely as highly visual, high-impact bulleted pointers and actionable workflows customized for Animesh, an ambitious entrepreneur. Strictly 8-10 lines long total."
                generated_insight = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Learning", "Score": 10, "Notes": f"📄 Book/Podcast Insight: {inject_title}", "AI_Summary": generated_insight, "Raw_Content": f"Native AI synthesis for: {inject_title}"})
                st.success(f"🎉 Successfully injected '{inject_title}'!")
                time.sleep(0.4)
                st.rerun()

    st.write("---")
    st.markdown("### 📥 Bulk File Uploader Pipeline")
    uploaded_books = st.file_uploader("Drop books, essays or article texts in bulk:", type=["pdf", "docx", "xlsx", "txt", "png", "jpg"], accept_multiple_files=True, key="l_bulk")
    if st.button("Inject Batch to Library Vault", use_container_width=True):
        if uploaded_books:
            for b in uploaded_books:
                b_bytes = b.getvalue()
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(b_bytes, f"library_{timestamp.replace(':','-')}_{b.name}")
                
                mime_type = "application/pdf" if b.name.endswith(".pdf") else ("image/jpeg" if b.name.endswith(".jpg") or b.name.endswith(".jpeg") else "image/png" if b.name.endswith(".png") else None)
                if mime_type:
                    ai_summary = call_gemini_engine("Provide a visually appealing summary structured strictly as high-impact bulleted pointers detailing the exact key findings of this document. Cover all central themes explicitly. Strictly 8-10 lines long.", file_bytes=b_bytes, mime_type=mime_type)
                    single_book_text = f"[Multimodal File: {b.name}]"
                else:
                    single_book_text = extract_raw_text(b)
                    prompt = f"Analyze the text. Provide a visually appealing summary structured strictly as high-impact bulleted pointers detailing the exact key findings. Cover central themes explicitly. Strictly 8-10 lines long:\n\n{single_book_text[:28000]}"
                    ai_summary = call_gemini_engine(prompt)
                    
                commit_new_log({"Timestamp": timestamp, "Section": "Learning", "Score": 10, "Notes": f"📄 {b.name}", "AI_Summary": ai_summary, "Raw_Content": single_book_text})
            st.success("🎉 Documents successfully isolated, analyzed, and synced!")
            time.sleep(0.5)
            st.rerun()

    st.write("### 📜 Library Summaries & Document Reader:")
    if not l_data.empty:
        for idx, (_, row) in enumerate(l_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            st.markdown(f"#### {str(row.get('Notes', 'Book File')).split('|')[0]}")
            st.caption(f"Archived on: {row['Timestamp']}")
            st.markdown(str(row.get('AI_Summary', '')))
            
            with st.expander("📂 Click to view raw file format (Text/Data)"):
                st.text_area("Original Content Stream Viewer Panel", value=str(row.get("Raw_Content", "")), height=250, disabled=True, key=f"raw_l_{row_id}")
            if st.button("🗑️ Delete this library card", key=f"delete_l_{row_id}"):
                delete_row(row_id, "Learning"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    b_data = history_df[history_df["Section"] == "Business"]
    
    # --- SUB SECTION 1: Business Snapshot ---
    st.markdown("### 📊 Active Ventures Snapshot")
    st.markdown("**(Life Agro, WellWorld Foods, Jiva Leathers, Khemka Woodcraft)**")
    voice_input_widget("biz_snapshot", "voice_biz_snap", label="🎤 Dictate Business Updates / To-Do's")
    biz_snapshot = st.text_area("Update Business State & To-Do's:", key="biz_snapshot")
    biz_snap_file = st.file_uploader("Upload context (PDF, Word, Image):", type=["pdf", "docx", "jpg", "png", "txt"], key="b_snap_file")
    
    if st.button("🚀 Analyze Business State & Generate Strategy", use_container_width=True):
        if biz_snapshot or biz_snap_file:
            with st.spinner("Generating expansion & long-term strategy suggestions..."):
                prompt = f"Act as an elite strategy consultant for Animesh's businesses. Based on these updates, provide high-level AI suggestions on what more/better he could do to expand his businesses and long-term strategy suggestions for each.\nContext: {biz_snapshot}"
                file_bytes, mime = None, None
                if biz_snap_file:
                    file_bytes = biz_snap_file.getvalue()
                    mime = "application/pdf" if biz_snap_file.name.endswith(".pdf") else "image/jpeg" if "jpg" in biz_snap_file.name else None
                    if not mime: prompt += f"\nFile Text: {extract_raw_text(biz_snap_file)[:10000]}"
                
                ai_strat = call_gemini_engine(prompt, file_bytes=file_bytes, mime_type=mime)
                commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Business", "Score": 10, "Notes": "Business Snapshot Strategy", "AI_Summary": ai_strat, "Raw_Content": biz_snapshot})
                st.success("Strategy generated!")
                time.sleep(0.5)
                st.rerun()

    # --- SUB SECTION 2: Personal Advisor ---
    st.markdown("### 🧠 AI Personal Advisor (Ideas & Strategies)")
    voice_input_widget("biz_advisor", "voice_biz_adv", label="🎤 Speak your ideas/thoughts")
    biz_advisor = st.text_area("Share ideas, thoughts, or strategies for feedback:", key="biz_advisor")
    if st.button("💡 Get Advisor Feedback", use_container_width=True):
        if biz_advisor:
            with st.spinner("Consulting advisor matrix..."):
                prompt = f"Act as a world-class personal business advisor to Animesh. He has just shared this idea/strategy. Tell him what you think of it, what he could do to make it work, and how to execute it better:\n\n{biz_advisor}"
                feedback = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Business", "Score": 10, "Notes": "Advisor Consultation", "AI_Summary": feedback, "Raw_Content": biz_advisor})
                st.rerun()

    # --- SUB SECTION 3: Progress Trackers ---
    st.markdown("### 📈 Strategic Execution Trackers")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Deep work blocks everyday without phone", 1, 10, 7, key="tk_b1")
        st.slider("Ideate & deep thinking everyday", 1, 10, 7, key="tk_b2")
    with col2:
        st.slider("Delegate daily execution tasks efficiently", 1, 10, 7, key="tk_b3")
        st.slider("Completing Things to Do diligently everyday", 1, 10, 7, key="tk_b4")

    # --- SUB SECTION 4: Daily Quotes ---
    st.markdown("### 💼 Daily Professional Catalyst")
    st.markdown(f'<div class="quote-box">"{get_daily_content("biz_quotes")}"</div>', unsafe_allow_html=True)

    # --- SUB SECTION 5: Vault ---
    st.write("---")
    st.markdown("### 📥 Venture Document Vault")
    biz_docs = st.file_uploader("Upload engineering data, sheets, or invoices:", type=["xlsx", "csv", "pdf", "docx", "png"], accept_multiple_files=True, key="b_bulk")
    if st.button("Archive Venture Metrics", use_container_width=True):
        if biz_docs:
            for bd in biz_docs:
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(bd.getvalue(), f"biz_{timestamp.replace(':','-')}_{bd.name}")
                mime = "application/pdf" if bd.name.endswith(".pdf") else "image/jpeg" if "jpg" in bd.name else "image/png" if bd.name.endswith("png") else None
                if mime:
                    ai_summary = call_gemini_engine("Provide a clean, deep-dive content summary detailing exactly what this document states. Focus on specifications and logistics. Strictly 8-10 lines long.", file_bytes=bd.getvalue(), mime_type=mime)
                    single_doc_text = "[Multi-modal File]"
                else:
                    single_doc_text = extract_raw_text(bd)
                    prompt = f"Provide a clean, deep-dive content summary detailing exactly what this document states. Strictly 8-10 lines long:\n\n{single_doc_text[:20000]}"
                    ai_summary = call_gemini_engine(prompt)
                
                commit_new_log({"Timestamp": timestamp, "Section": "Business", "Score": 10, "Notes": f"📄 {bd.name}", "AI_Summary": ai_summary, "Raw_Content": single_doc_text})
            st.rerun()

    if not b_data.empty: 
        st.write("### 📜 Corporate Summaries & Specifications:")
        for idx, (_, row) in enumerate(b_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            st.markdown(f"#### {str(row.get('Notes', 'Venture File')).split('|')[0]}")
            st.caption(f"Entry Timestamp: {row['Timestamp']}")
            st.markdown(str(row.get('AI_Summary', '')))
            with st.expander("📂 Click to view original raw file text"):
                st.text_area("Original File Contents", value=str(row.get("Raw_Content", "")), height=200, disabled=True, key=f"raw_b_{row_id}")
            if st.button("🗑️ Delete this venture card", key=f"delete_b_{row_id}"):
                delete_row(row_id, "Business"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. PEACE & MINDSET MODULE
# ==========================================
with tab4:
    st.header("🧘 Peace & Spiritual Shielding")
    
    # --- SUB SECTION 1: Progress Trackers ---
    st.markdown("### 📈 Peace & Mindset Trackers")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Meditation & Puja everyday", 1, 10, 7, key="tk_p1")
        st.slider("Manifestation routine everyday", 1, 10, 7, key="tk_p2")
        st.slider("Journalling every night", 1, 10, 7, key="tk_p3")
        st.slider("Total control of positive mindset & emotions", 1, 10, 7, key="tk_p4")
    with col2:
        st.slider("Follow astrological suggestions and remedies", 1, 10, 7, key="tk_p5")
        st.slider("Preserve energy, time & focus like treasures", 1, 10, 7, key="tk_p6")
        st.slider("Stay away from negative people & relatives", 1, 10, 7, key="tk_p7")

    # --- SUB SECTION 2: Daily Techniques & Quotes ---
    st.markdown("### 🌌 Daily Spiritual Architecture")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Motivation**")
        st.markdown(f'<div class="quote-box" style="font-size:12px;">"{get_daily_content("peace_quotes")}"</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("**Meditation Focus**")
        st.markdown(f'<div class="quote-box" style="font-size:12px;">{get_daily_content("meditation")}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown("**Manifestation**")
        st.markdown(f'<div class="quote-box" style="font-size:12px;">{get_daily_content("manifestation")}</div>', unsafe_allow_html=True)

    # --- SUB SECTION 3: Spiritual Guru (Krishna) ---
    st.write("---")
    st.markdown("### 🦚 Divine Counsel (Krishna)")
    voice_input_widget("guru_peace", "voice_guru_p", label="🎤 Speak to Krishna")
    guru_input = st.text_area("Express your feelings, doubts, or grievances here:", key="guru_peace")
    if st.button("Receive Divine Guidance", use_container_width=True):
        if guru_input:
            with st.spinner("Seeking counsel..."):
                prompt = f"Act as Lord Krishna from the Bhagavad Gita. Animesh is expressing his feelings/doubts: '{guru_input}'. Offer him deep, calming, spiritual suggestions on how to control his emotions, stay positive, and handle the situation in the best, most righteous manner. Speak with divine compassion and strategic wisdom."
                guru_response = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Peace", "Score": 10, "Notes": "Krishna Counsel", "AI_Summary": guru_response, "Raw_Content": guru_input})
                st.rerun()

    # --- SUB SECTION 4: Astrological Charts ---
    st.write("---")
    st.subheader("🌌 Astrological Chart Mapping & Remedies")
    astro_files = st.file_uploader("Upload Astrological Charts (PDF, Image, Text):", type=["pdf", "png", "jpg", "txt", "docx"], accept_multiple_files=True, key="a_bulk")
    if st.button("Execute Astro Alignment & Get Remedies", use_container_width=True):
        if astro_files:
            for af in astro_files:
                f_bytes = af.getvalue()
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                save_file_to_github(f_bytes, f"astro_{timestamp.replace(':','-')}_{af.name}")
                
                mime = "application/pdf" if af.name.endswith(".pdf") else "image/jpeg" if "jpg" in af.name else "image/png" if af.name.endswith("png") else None
                prompt = "Act as an expert Vedic Astrologer. Analyze this astrological chart data. Provide both a summarized and detailed view of predictions for short and long term. Crucially, offer specific advice and solutions (like gemstones to wear, specific daily rituals) to navigate this chart and maximize luck."
                
                if mime:
                    ai_summary = call_gemini_engine(prompt, file_bytes=f_bytes, mime_type=mime)
                    raw_text = "[Visual Astrological Chart]"
                else:
                    raw_text = extract_raw_text(af)
                    ai_summary = call_gemini_engine(prompt + f"\n\nData:\n{raw_text[:15000]}")
                
                commit_new_log({"Timestamp": timestamp, "Section": "Mindset", "Score": 10, "Notes": f"📄 {af.name} | Astro Analysis", "AI_Summary": ai_summary, "Raw_Content": raw_text})
            st.rerun()

    # Display Peace/Mindset History
    m_data = history_df[history_df["Section"].isin(["Peace", "Mindset"])]
    if not m_data.empty:
        st.write("### 🌌 Active Spiritual & Astro Logs:")
        for idx, (_, row) in enumerate(m_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            if "Krishna" in str(row.get("Notes")):
                st.markdown(f'<div class="guru-box">🦚 <b>Divine Counsel</b><br><br>{str(row.get("AI_Summary", ""))}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"#### {str(row.get('Notes')).split('|')[0]}")
                st.caption(f"Logged: {row['Timestamp']}")
                st.markdown(str(row.get('AI_Summary', '')))
                with st.expander("📂 View Raw Input/File"):
                    st.text_area("Content", value=str(row.get("Raw_Content", "")), height=150, disabled=True, key=f"raw_m_{row_id}")
            if st.button("🗑️ Delete entry", key=f"delete_m_{row_id}"):
                delete_row(row_id, row["Section"]); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. RELATIONSHIPS MODULE
# ==========================================
with tab5:
    st.header("🤝 Interpersonal Network Alignment")
    
    # --- SUB SECTION 1: Progress Trackers ---
    st.markdown("### 📈 Relationship Trackers")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Less screen time and more interaction", 1, 10, 7, key="tk_r1")
        st.slider("More personal outings & activities", 1, 10, 7, key="tk_r2")
    with col2:
        st.slider("Less reactive & more calm", 1, 10, 7, key="tk_r3")
        st.slider("Manifestation for better relationships", 1, 10, 7, key="tk_r4")
        
    # --- SUB SECTION 2: Spiritual Guru (Krishna) for Relationships ---
    st.write("---")
    st.markdown("### 🦚 Divine Counsel for Relationships (Krishna)")
    voice_input_widget("guru_rel", "voice_guru_r", label="🎤 Speak to Krishna about Relationships")
    rel_input = st.text_area("Express relationship doubts, moods, or grievances here:", key="guru_rel")
    if st.button("Seek Relationship Guidance", use_container_width=True):
        if rel_input:
            with st.spinner("Seeking counsel..."):
                prompt = f"Act as Lord Krishna. Animesh is expressing feelings about his relationships: '{rel_input}'. Offer him deep, calming suggestions on how to handle the situation in the best manner, stay calm, and resolve conflicts with love and wisdom."
                guru_response = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Relationships", "Score": 10, "Notes": "Krishna Counsel (Rel)", "AI_Summary": guru_response, "Raw_Content": rel_input})
                st.rerun()

    r_data = history_df[history_df["Section"] == "Relationships"]
    if not r_data.empty: 
        st.write("### 📜 Communication & Counsel Feed:")
        for idx, (_, row) in enumerate(r_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            if "Krishna" in str(row.get("Notes")):
                st.markdown(f'<div class="guru-box">🦚 <b>Divine Counsel</b><br><br>{str(row.get("AI_Summary", ""))}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"#### {str(row.get('Notes')).split('|')[0]}")
                st.markdown(str(row.get('AI_Summary', 'Manual Entry Recorded.')))
            if st.button("🗑️ Delete", key=f"delete_r_{row_id}"):
                delete_row(row_id, "Relationships"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. FINANCE MODULE
# ==========================================
with tab6:
    st.header("📉 Financial Intelligence Terminal")
    
    # --- SUB SECTION 1: Indian Market Update ---
    st.markdown("### 🇮🇳 Daily Market Snapshot & Recommendations")
    if st.button("☀️ Fetch Live Indian Market Update & Indicators", use_container_width=True):
        with st.spinner("Pulling global and Indian indicators..."):
            market_data = ""
            try:
                nifty = yf.Ticker("^NSEI").history(period="1d")['Close'].iloc[-1]
                sensex = yf.Ticker("^BSESN").history(period="1d")['Close'].iloc[-1]
                crude = yf.Ticker("CL=F").history(period="1d")['Close'].iloc[-1]
                usdinr = yf.Ticker("INR=X").history(period="1d")['Close'].iloc[-1]
                market_data = f"Nifty50: {nifty:.2f}, Sensex: {sensex:.2f}, Crude Oil: ${crude:.2f}, USD/INR: ₹{usdinr:.2f}"
            except: market_data = "Market data pull limited. Rely on macro AI generation."
            
            prompt = f"Provide a highly structured, visually appealing daily Indian equity market snapshot. Include key news/developments, macro analysis on global indicators (Crude, USD/INR, VIX, Geopolitics). Conclude with 2-3 specific stock investment recommendations based on technical/fundamental parameters, including exact rationale, expected return potential, and timeframe. Current data pull: {market_data}"
            ai_summary = call_gemini_engine(prompt)
            commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), "Section": "Finance", "Score": 10, "Notes": "Daily Market Snapshot", "AI_Summary": ai_summary, "Raw_Content": market_data})
            st.rerun()

    # --- SUB SECTION 2: Detailed Stock Research ---
    st.write("---")
    st.markdown("### 🔍 Deep Equity Research Tool")
    ticker = st.text_input("Enter NSE Ticker Symbol (e.g. RELIANCE.NS, TCS.NS) for Detailed Audit:")
    if st.button("Run Fundamental + Technical Market Audit", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        with st.spinner(f"Analyzing {ticker} across all parameters..."):
            try:
                hist = yf.Ticker(ticker).history(period="6mo")
                metrics = "Data unavailable"
                if not hist.empty:
                    metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                prompt = f"Act as an elite equity research analyst. Perform a deep, structured, and visually appealing research report for the Indian stock {ticker}. Analyze all technical and fundamental parameters. Conclude with a clear recommendation (BUY / SELL / HOLD), explicit rationale, expected return potential, and exact timeframe. Known metrics: {metrics}"
                ai_summary = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": timestamp, "Section": "Finance", "Score": 10, "Notes": f"Research Audit: {ticker}", "AI_Summary": ai_summary, "Raw_Content": metrics})
                st.rerun()
            except Exception as err: st.error(f"Audit error: {err}")

    # --- SUB SECTION 3: Portfolio Evaluation ---
    st.write("---")
    st.markdown("### 📋 Portfolio Structural Evaluation")
    port_files = st.file_uploader("Upload your portfolio (PDF, Excel, Word, Image) for Wealth Advisory:", type=["xlsx", "csv", "pdf", "docx", "png", "jpg"], accept_multiple_files=True, key="p_bulk")
    if st.button("Execute Portfolio Advisory & Risk Check", use_container_width=True):
        if port_files:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            for pf in port_files:
                save_file_to_github(pf.getvalue(), f"portfolio_{pf.name}")
                
                mime = "application/pdf" if pf.name.endswith(".pdf") else "image/jpeg" if "jpg" in pf.name else "image/png" if pf.name.endswith("png") else None
                prompt = "Act as a personal wealth and portfolio advisor. Analyze this uploaded portfolio. Provide detailed, stock-by-stock recommendations, asset allocation feedback, and restructuring advice to maximize returns and mitigate risk."
                
                if mime:
                    ai_summary = call_gemini_engine(prompt, file_bytes=pf.getvalue(), mime_type=mime)
                    single_sheet_text = "[Multi-modal Portfolio]"
                else:
                    single_sheet_text = extract_raw_text(pf)
                    ai_summary = call_gemini_engine(prompt + f"\n\nData:\n{single_sheet_text[:15000]}")
                
                commit_new_log({"Timestamp": timestamp, "Section": "Finance", "Score": 10, "Notes": f"📄 {pf.name} | Portfolio Advisory", "AI_Summary": ai_summary, "Raw_Content": single_sheet_text})
            st.success("🎉 Portfolio advisory generated successfully!")
            time.sleep(0.5)
            st.rerun()

    f_data = history_df[history_df["Section"] == "Finance"]
    if not f_data.empty:
        st.write("### 📜 Saved Financial Research & Updates:")
        for idx, (_, row) in enumerate(f_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            st.markdown(f"#### {str(row.get('Notes', 'Finance Update')).split('|')[0]}")
            st.caption(f"Session Stamp: {row['Timestamp']}")
            st.markdown(str(row.get('AI_Summary', '')))
            with st.expander("📂 Click to view original raw metric data"):
                st.text_area("Extracted Data", value=str(row.get("Raw_Content", "")), height=200, disabled=True, key=f"raw_f_{row_id}")
            if st.button("🗑️ Delete", key=f"delete_f_{row_id}"):
                delete_row(row_id, "Finance"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. GOALS MODULE
# ==========================================
with tab7:
    st.header("🚀 Strategic Goal Vectoring")
    
    # --- SUB SECTION 1: Progress Trackers ---
    st.markdown("### 📈 Goal Execution Trackers")
    col1, col2, col3 = st.columns(3)
    with col1: st.slider("Short-Term Goals (0-6 Months)", 1, 10, 5, key="tk_g1")
    with col2: st.slider("Medium-Term Goals (6-24 Months)", 1, 10, 5, key="tk_g2")
    with col3: st.slider("Long-Term Goals (2-10 Years)", 1, 10, 5, key="tk_g3")

    # --- SUB SECTION 2: Daily Quotes ---
    st.markdown("### 🌌 Execution Catalyst")
    st.markdown(f'<div class="quote-box">"{get_daily_content("goals_quotes")}"</div>', unsafe_allow_html=True)

    # --- SUB SECTION 3: Multi-modal Goal Input ---
    st.write("---")
    st.markdown("### 🎯 Define & Strategize Goals")
    voice_input_widget("vision_input", "voice_vision", label="🎤 Dictate your specific Goals")
    vision_input = st.text_area("Define short, medium, and long-term goals:", key="vision_input")
    goal_files = st.file_uploader("Upload Vision Boards / Docs (PDF, Word, Image):", type=["pdf", "docx", "png", "jpg"], accept_multiple_files=True, key="g_bulk")
    
    if st.button("Update Directives & Get AI Roadmap", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        with st.spinner("Synthesizing strategic execution roadmap..."):
            prompt = f"The user is setting new short, medium, and long term goals: '{vision_input}'. Provide a highly structured, step-by-step AI recommendation roadmap on exactly how to achieve these goals."
            
            if goal_files:
                for gf in goal_files:
                    mime = "application/pdf" if gf.name.endswith(".pdf") else "image/jpeg" if "jpg" in gf.name else "image/png" if gf.name.endswith("png") else None
                    if mime:
                        ai_summary = call_gemini_engine(prompt + " Take this attached vision board/document into account.", file_bytes=gf.getvalue(), mime_type=mime)
                    else:
                        ai_summary = call_gemini_engine(prompt + f"\nDocument Context: {extract_raw_text(gf)}")
                    commit_new_log({"Timestamp": timestamp, "Section": "Goals", "Score": 10, "Notes": f"🎯 Goal Asset: {gf.name}", "AI_Summary": ai_summary, "Raw_Content": "[Goal File]"})
            else:
                ai_summary = call_gemini_engine(prompt)
                commit_new_log({"Timestamp": timestamp, "Section": "Goals", "Score": 10, "Notes": "Visions updated.", "AI_Summary": ai_summary, "Raw_Content": vision_input})
                
        st.success("🎉 Goal matrices locked in and AI roadmap generated!")
        time.sleep(0.5)
        st.rerun()

    g_data = history_df[history_df["Section"] == "Goals"]
    if not g_data.empty: 
        st.write("### 📜 Active Master Targets & Roadmaps:")
        for idx, (_, row) in enumerate(g_data.iloc[::-1].iterrows()):
            row_id = str(row.get('RowID', '') or f"legacy_{row['Timestamp']}_{idx}")
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            st.markdown(f"#### {str(row.get('Notes', 'Goal')).split('|')[0]}")
            st.markdown(str(row.get('AI_Summary', '')))
            if st.button("🗑️ Delete Goal", key=f"delete_g_{row_id}"):
                delete_row(row_id, "Goals"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 🟢 MASTER GREEN SYNC TERMINAL PANEL
# ==========================================
st.write("---") 
st.write("### 🗲 Universal Cross-Device Entry Pad")
sync_section = st.selectbox("Assign log to module:", ["Business", "Learning", "Health", "Goals", "Relationships"], key="m_sec")
voice_input_widget("m_notes", "voice_sync")
sync_notes = st.text_area("Type updates, logs, or paste Google Drive asset links here:", placeholder="Example: Placed catalog design layout updates here...", key="m_notes")

if st.button("🟢 FORCE SYNC ALL DEVICES NOW", use_container_width=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_new_log({
        "Timestamp": timestamp, "Section": sync_section, "Score": 10, "Notes": f"Global Device Pad Log", "AI_Summary": f"### Direct Asset Update Record:\n{sync_notes}", "Raw_Content": sync_notes
    })
    st.success("✨ Everything synchronized flawlessly! Data securely saved and broadcasted to all terminal instances.")
    time.sleep(0.5)
    st.rerun()
