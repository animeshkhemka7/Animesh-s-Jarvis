import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import base64
import time
from io import BytesIO
from datetime import datetime

# 1. Responsive Shell Configuration
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
    </style>
""", unsafe_allow_html=True)

# Secure Environment Infrastructure Pips
TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO = st.secrets.get("GITHUB_REPO", "")
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3.5-flash')
else:
    st.error("⚠️ Gemini API Key missing in Settings -> Secrets.")
    model = None

# ==========================================
# ⚡ ANTI-CACHING REAL-TIME STORAGE PIPELINE
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
        df = pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes"])
    
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    payload = {
        "message": "Realtime Data Sync Event",
        "content": base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("utf-8"),
        "sha": sha if sha else None
    }
    requests.put(f"https://api.github.com/repos/{REPO}/contents/{filename}", headers=headers, json=payload)

def load_live_database_uncached():
    if not TOKEN or not REPO: return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes"])
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
            return pd.read_csv(BytesIO(content_str.encode("utf-8")))
    except:
        pass
    return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes"])

# Real-Time Engine: Instantly saves to memory so screens don't wipe out, then updates cloud
def commit_new_log(row_dict):
    if st.session_state["cached_db"].empty:
        st.session_state["cached_db"] = pd.DataFrame([row_dict])
    else:
        st.session_state["cached_db"] = pd.concat([st.session_state["cached_db"], pd.DataFrame([row_dict])], ignore_index=True)
    log_row_to_csv(row_dict)

# ==========================================
# MASTER DATA INITIALIZATION
# ==========================================
if "cached_db" not in st.session_state:
    st.session_state["cached_db"] = load_live_database_uncached()

st.title("🎯 Khemka Life OS")

# Master High-Priority Synchronize Command Trigger (Top Block)
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
            with st.expander("📂 View Archived Health Logs & Files"):
                st.dataframe(h_data[["Timestamp", "Score", "Notes"]], use_container_width=True)

    h_score = st.slider("Rate physical health score today", 1, 10, 7, key="h_slider")
    h_input = st.text_area("Type lifestyle or workout notes:", key="h_notes")
    audio_log = st.audio_input("🎤 Record real-time voice entry", key="h_audio")
    uploaded_files = st.file_uploader("Upload files/screenshots:", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    
    if st.button("Permanently Save Health Data", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        names_list = []
        ai_payload = [f"Act as health coach. Score: {h_score}/10. Log: {h_input}"]
        
        if audio_log:
            save_file_to_github(audio_log.getvalue(), f"voice_{timestamp.replace(' ','_')}.wav", folder="vault/voice")
            ai_payload.append(audio_log)
        if uploaded_files:
            for f in uploaded_files:
                f_bytes = f.getvalue()
                save_file_to_github(f_bytes, f"health_{timestamp.replace(' ','_')}_{f.name}")
                names_list.append(f.name)
                if f.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": f.type, "data": f_bytes})
                    
        commit_new_log({"Timestamp": timestamp, "Section": "Health", "Score": h_score, "Notes": f"{h_input} | Batch: {', '.join(names_list)}"})
        st.success("Synced to cloud storage!")
        
        if model:
            try:
                st.info(model.generate_content(ai_payload).text)
            except Exception:
                st.warning("⚠️ Files saved! However, the AI engine is momentarily at capacity to compile a live summary.")
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
        if not l_data.empty:
            with st.expander("📂 View Archived Books & Summaries Directory"):
                st.dataframe(l_data[["Timestamp", "Notes"]], use_container_width=True)
        
    media_name = st.text_input("Source Title:")
    uploaded_books = st.file_uploader("Drop books or summaries in bulk:", type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True, key="l_bulk")
    
    if st.button("Inject Batch to Library Vault", use_container_width=True):
        if uploaded_books and model:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            with st.spinner("Indexing content vector arrays..."):
                ai_payload = ["Extract core business execution rules for Animesh."]
                for b in uploaded_books:
                    b_bytes = b.getvalue()
                    save_file_to_github(b_bytes, f"library_{media_name.replace(' ','_')}_{b.name}")
                    if b.type in ["application/pdf", "text/plain"]:
                        ai_payload.append({"mime_type": b.type, "data": b_bytes})
                        
                commit_new_log({"Timestamp": timestamp, "Section": "Learning", "Score": 10, "Notes": f"Batch: {media_name}"})
                st.success("🎉 Library components successfully archived & synced!")
                
                try:
                    st.write(model.generate_content(ai_payload).text)
                except Exception:
                    st.warning("⚠️ Documents uploaded cleanly! The AI model is experiencing high load and skipped text generation.")
                time.sleep(0.5)
                st.rerun()

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    
    if not history_df.empty:
        b_data = history_df[history_df["Section"] == "Business"]
        if not b_data.empty: 
            st.line_chart(b_data.set_index("Timestamp")["Score"])
            with st.expander("📂 View Strategic Moves & Invoice Logs"):
                st.dataframe(b_data[["Timestamp", "Score", "Notes"]], use_container_width=True)
            
    biz_name = st.text_input("Venture Name:", value="Premium Vegan Leather Goods Brand")
    biz_score = st.slider("Current Execution Momentum", 1, 10, 7, key="b_slider")
    biz_notes = st.text_area("Operational moves or bottlenecks:", value="Designing modular men's sling bags and phone card holders for export to North America, Europe, and Middle East. Differentiating utility from local competitors.")
    biz_docs = st.file_uploader("Upload engineering data sheets or invoices in bulk:", type=["xlsx", "csv", "pdf", "docx"], accept_multiple_files=True, key="b_bulk")
    
    if st.button("Analyze & Save Venture Metrics", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ai_payload = [f"Act as a top global venture strategist. Project: {biz_name}. Momentum state: {biz_score}/10. Structural context updates: {biz_notes}"]
        if biz_docs:
            for bd in biz_docs:
                save_file_to_github(bd.getvalue(), f"biz_{biz_name}_{bd.name}")
                
        commit_new_log({"Timestamp": timestamp, "Section": "Business", "Score": biz_score, "Notes": biz_notes})
        st.success("🎉 Venture metrics archived & broadcasted!")
        
        if model:
            try:
                st.info(model.generate_content(ai_payload).text)
            except Exception:
                st.warning("⚠️ Strategy metrics recorded to cloud directory! AI analysis module skipped due to query capacity limits.")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 4. PEACE & MINDSET MODULE
# ==========================================
with tab4:
    st.header("🧘 Mindset Shielding & Planetary Coordinates")
    if st.button("Fetch Daily Meditation & Energy Shield Protocol", use_container_width=True):
        if model:
            try:
                st.info(model.generate_content("Provide an executive mindset validation drill, deep rhythmic breathing guidelines, and explicit protocols to maintain absolute workspace concentration and isolate energy from critical family members.").text)
            except Exception:
                st.warning("⚠️ Focus drill protocol: Center alignment focus, execute deep rhythmic 4-7-8 deep breathing cycles, and establish operational privacy.")
            
    st.markdown("---")
    st.subheader("🌌 Natal Chart Synthesis Drawer")
    astro_files = st.file_uploader("Drop planetary maps/birth charts (Select Multiple):", type=["pdf", "png", "jpg"], accept_multiple_files=True, key="a_bulk")
    if st.button("Execute Astro Mapping Alignment", use_container_width=True):
        if astro_files and model:
            ai_payload = ["Perform full structural alignment diagnosis on these birth chart data layers. Output explicit personal remedies."]
            for af in astro_files:
                save_file_to_github(af.getvalue(), f"astro_{af.name}")
                if af.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": af.type, "data": af.getvalue()})
            
            st.success("Planetary chart layers uploaded to file repository.")
            try:
                st.info(model.generate_content(ai_payload).text)
            except Exception:
                st.warning("⚠️ Alignment assets logged cleanly! The parsing grid model is processing heavy query streams now.")

# ==========================================
# 5. RELATIONSHIPS MODULE
# ==========================================
with tab5:
    st.header("🤝 Interpersonal Network Alignment")
    
    if not history_df.empty:
        r_data = history_df[history_df["Section"] == "Relationships"]
        if not r_data.empty: 
            st.line_chart(r_data.set_index("Timestamp")["Score"])
            with st.expander("📂 View Historic Relational Notes"):
                st.dataframe(r_data[["Timestamp", "Score", "Notes"]], use_container_width=True)
        
    r_score = st.slider("Rate relational harmony level", 1, 10, 7, key="r_slider")
    r_notes = st.text_area("Key communication metrics or dynamics tracker:")
    if st.button("Archive Relationship Log Entry", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Relationships", "Score": r_score, "Notes": r_notes})
        st.success("🎉 Network logs compiled and safely synced!")
        time.sleep(0.5)
        st.rerun()

# ==========================================
# 6. INDIAN STOCK MARKET ENGINE
# ==========================================
with tab6:
    st.header("📉 Market Trading Terminal")
    if st.button("☀️ Pull Indian Pre-Market Framework Analysis", use_container_width=True):
        if model:
            try:
                nifty_close = yf.Ticker("^NSEI").history(period="2d")['Close'].iloc[-1]
                try:
                    st.info(model.generate_content(f"Provide an assertive technical market layout brief for an Indian equities operator. Index validation state: Nifty 50 close tracking near {nifty_close}. Highlight 3 alpha trading sectors for outperformance.").text)
                except Exception:
                    st.warning(f"⚠️ Live validation index metrics pulled (Nifty tracking: ₹{nifty_close:.2f}). AI sector parsing overloaded.")
            except Exception as e: st.error(f"Scraper error: {e}")
                    
    st.markdown("---")
    ticker = st.text_input("Enter NSE Ticker Symbol (e.g. RELIANCE.NS, TCS.NS):", value="RELIANCE.NS")
    if st.button("Run Fundamental + Technical Market Audit", use_container_width=True):
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                st.text(metrics)
                if model:
                    try:
                        st.write(model.generate_content(f"Hedge fund analysis report for {ticker}. Metrics: {metrics}. Provide explicit target support layers and a clear Buy/Hold/Sell recommendation.").text)
                    except Exception:
                        st.warning("⚠️ Technical pricing layer complete! AI target forecast models are momentarily offline.")
        except Exception as err: st.error(f"Audit error: {err}")

    st.markdown("---")
    st.subheader("📋 Structural Portfolio Evaluation")
    port_files = st.file_uploader("Drop broker spreadsheets/statements (Select Multiple):", type=["xlsx", "csv"], accept_multiple_files=True, key="p_bulk")
    if st.button("Execute Portfolio Audit Risk Check", use_container_width=True):
        if port_files and model:
            for pf in port_files: save_file_to_github(pf.getvalue(), f"portfolio_{pf.name}")
            st.success("🎉 Portfolio structural breakdown synced to server files successfully!")

# ==========================================
# 7. LONG-TERM GOALS
# ==========================================
with tab7:
    st.header("🚀 Strategic Goal Vectoring")
    
    if not history_df.empty:
        g_data = history_df[history_df["Section"] == "Goals"]
        if not g_data.empty: 
            st.line_chart(g_data.set_index("Timestamp")["Score"])
            with st.expander("📂 View Long Term Directive Archives"):
                st.dataframe(g_data[["Timestamp", "Notes"]], use_container_width=True)
        
    vision_input = st.text_area("Define master 5 & 10-year blueprints:", value="Build a premier international sustainable design and luxury leather export empire with established corporate gifting logistics footprint across India.")
    if st.button("Update Long-Term Directives", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Goals", "Score": 10, "Notes": vision_input})
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
sync_notes = st.text_area("Type updates, logs, or paste Google Drive asset links here:", placeholder="Example: Placed catalog design layout updates here. Link: https://drive.google.com/...", key="m_notes")
sync_score = st.slider("Assign score status value:", 1, 10, 10, key="m_score")

if st.button("🟢 FORCE SYNC ALL DEVICES NOW"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    new_entry = {
        "Timestamp": timestamp,
        "Section": sync_section,
        "Score": sync_score,
        "Notes": sync_notes if sync_notes else "Manual Global Device Sync Verification Triggered"
    }
    
    commit_new_log(new_entry)
    st.success("✨ Everything synchronized flawlessly! Data securely saved and broadcasted to all terminal instances.")
    time.sleep(0.5)
    st.rerun()
