import streamlit as st
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import requests
import base64
from io import BytesIO

# 1. Page Configuration for Dual-Device Real-Time Sync
st.set_page_config(page_title="Khemka Life OS", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

# Premium Mobile Theme Stylesheet
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold; background-color: #4F46E5; color: white;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; background-color: #F3F4F6; border-radius: 6px; font-size: 12px;}
    </style>
""", unsafe_allow_html=True)

# Secure Key Pulls
TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO = st.secrets.get("GITHUB_REPO", "")
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3.5-flash')
else:
    st.error("⚠️ Gemini API Key missing in Secrets.")
    model = None

# ==========================================
# BACKEND CORE PIPELINES
# ==========================================
def save_file_to_github(file_bytes, filename, folder="vault"):
    if not TOKEN or not REPO: return False
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"message": f"Sync: {filename}", "content": encoded_content}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def log_row_to_csv(row_dict, filename="logs.csv"):
    if not TOKEN or not REPO: return
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
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
    payload = {"message": "Database Append", "content": base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("utf-8")}
    if sha: payload["sha"] = sha
    requests.put(url, headers=headers, json=payload)

def load_history_raw():
    if not TOKEN or not REPO: return pd.DataFrame()
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    if res.status_code == 200:
        return pd.read_csv(BytesIO(base64.b64decode(res.json().get("content")).decode("utf-8").encode("utf-8")))
    return pd.DataFrame()

# ==========================================
# 🔄 REAL-TIME CROSS-DEVICE SYNC ENGINE
# ==========================================
# This native fragment runs independently every 10 seconds to auto-refresh metrics
@st.fragment(run_every="10s")
def render_realtime_charts(section_name, chart_type="line"):
    """Quietly polls the database and updates phone visualization in near real-time"""
    current_df = load_history_raw()
    if not current_df.empty:
        filtered_df = current_df[current_df["Section"] == section_name]
        if not filtered_df.empty:
            if chart_type == "line":
                st.caption(f"🔄 Real-Time Updated {section_name} Chart (Synced)")
                st.line_chart(filtered_df.set_index("Timestamp")["Score"])
            elif chart_type == "metric":
                st.metric(label="Total Library Assets Stacked", value=len(filtered_df))

# Master Interface Layout
st.title("🎯 Khemka Life OS")
st.caption("Real-Time Multi-Device Synchronization Enabled")
st.write("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "❤️ Health", "🧠 Learn", "💼 Biz", "🧘 Peace", "🤝 Rel", "📉 Finance", "🚀 Goals"
])

# ==========================================
# 1. HEALTH & FITNESS
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Vault")
    
    # Live Synchronized Chart Drawer
    render_realtime_charts("Health", chart_type="line")

    h_score = st.slider("Rate physical health score today", 1, 10, 7, key="health_slider_widget")
    h_input = st.text_area("Type lifestyle or workout notes:", key="h_notes")
    audio_log = st.audio_input("🎤 Tap to record voice entry", key="h_audio")
    uploaded_files = st.file_uploader("Upload medical files/screenshots:", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    
    if st.button("Permanently Process & Save Health Data", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        names_list = []
        ai_payload = [f"Act as Animesh's health coach. Score: {h_score}/10. Log: {h_input}"]
        
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
                    
        log_row_to_csv({"Timestamp": timestamp, "Section": "Health", "Score": h_score, "Notes": f"{h_input} | Batch: {', '.join(names_list)}"})
        st.success("Synced to cloud array!")
        if model: st.info(model.generate_content(ai_payload).text)

# ==========================================
# 2. LEARNING & DEVELOPMENT
# ==========================================
with tab2:
    st.header("📚 Master Knowledge Bank")
    
    # Live Total Count Tracker
    render_realtime_charts("Learning", chart_type="metric")
    
    media_name = st.text_input("Source Title:")
    uploaded_books = st.file_uploader("Drop books or transcripts in bulk:", type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True, key="l_bulk")
    
    if st.button("Inject Batch to Permanent Library Vault", use_container_width=True):
        if uploaded_books and model:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            with st.spinner("Indexing content..."):
                ai_payload = ["Extract core frameworks for Animesh."]
                for b in uploaded_books:
                    b_bytes = b.getvalue()
                    save_file_to_github(b_bytes, f"library_{media_name.replace(' ','_')}_{b.name}")
                    if b.type in ["application/pdf", "text/plain"]:
                        ai_payload.append({"mime_type": b.type, "data": b_bytes})
                log_row_to_csv({"Timestamp": timestamp, "Section": "Learning", "Score": 10, "Notes": f"Batch: {media_name}"})
                st.success("Library components safely updated!")
                st.write(model.generate_content(ai_payload).text)

# ==========================================
# 3. WORK & BUSINESS
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    render_realtime_charts("Business", chart_type="line")
            
    biz_name = st.text_input("Business Venture Name:")
    biz_score = st.slider("Current Momentum", 1, 10, 5, key="biz_slider_widget")
    biz_notes = st.text_area("Operational challenges:")
    biz_docs = st.file_uploader("Upload business sheets in bulk:", type=["xlsx", "csv", "pdf", "docx"], accept_multiple_files=True, key="b_bulk")
    
    if st.button("Analyze & Update Business Directives", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ai_payload = [f"Business Strategist. Project: {biz_name}. State: {biz_score}/10. Notes: {biz_notes}"]
        if biz_docs:
            for bd in biz_docs:
                save_file_to_github(bd.getvalue(), f"biz_{biz_name}_{bd.name}")
        log_row_to_csv({"Timestamp": timestamp, "Section": "Business", "Score": biz_score, "Notes": biz_notes})
        st.success("Directives processed successfully.")
        if model: st.info(model.generate_content(ai_payload).text)

# ==========================================
# 4. PEACE & MINDSET
# ==========================================
with tab4:
    st.header("🧘 Energy Protection & Cosmic Metrics")
    if st.button("Fetch Daily Manifestation & Focus Routine", use_container_width=True):
        if model: st.info(model.generate_content("Provide a morning focus routine for an entrepreneur to shield concentration from negative environments.").text)
            
    st.markdown("---")
    st.subheader("🌌 Natal Astrology Reading Vault")
    astro_files = st.file_uploader("Drop birth charts (Select Multiple):", type=["pdf", "png", "jpg"], accept_multiple_files=True, key="astro_bulk")
    if st.button("Process Astrological Profiles", use_container_width=True):
        if astro_files and model:
            ai_payload = ["Analyze these structural chart layers and map core remedies."]
            for af in astro_files:
                save_file_to_github(af.getvalue(), f"astro_{af.name}")
                if af.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": af.type, "data": af_bytes})
            st.info(model.generate_content(ai_payload).text)

# ==========================================
# 5. RELATIONSHIPS
# ==========================================
with tab5:
    st.header("🤝 Network Alignment Logs")
    render_realtime_charts("Relationships", chart_type="line")
    r_score = st.slider("Rate relational harmony level", 1, 10, 7, key="rel_slider_widget")
    r_notes = st.text_area("Enter key milestones or communication notes:")
    if st.button("Archive Relationship Log Entry", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Relationships", "Score": r_score, "Notes": r_notes})
        st.success("CRM updated.")

# ==========================================
# 6. INDIAN STOCK MARKET
# ==========================================
with tab6:
    st.header("📉 Market Engine Terminal")
    if st.button("☀️ Generate Live Pre-Market Report", use_container_width=True):
        if model:
            try:
                nifty_close = yf.Ticker("^NSEI").history(period="2d")['Close'].iloc[-1]
                st.info(model.generate_content(f"Provide a morning index overview briefing. Nifty 50 close tracking near {nifty_close}. State 3 high-probability alpha stock sectors.").text)
            except Exception as e: st.error(f"Data pull issue: {e}")
                    
    st.markdown("---")
    ticker = st.text_input("Enter NSE Stock Ticker (e.g. RELIANCE.NS):", value="RELIANCE.NS")
    if st.button("Run Fundamental + Technical Market Audit", use_container_width=True):
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50-Day MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f}"
                st.text(metrics)
                if model: st.write(model.generate_content(f"Technical audit for {ticker}: {metrics}. Provide clear entry parameters and a final Buy/Hold/Sell decision.").text)
        except Exception as err: st.error(f"Audit failed: {err}")

# ==========================================
# 7. LONG-TERM GOALS
# ==========================================
with tab7:
    st.header("🚀 Macro Strategy Vectoring")
    render_realtime_charts("Goals", chart_type="line")
    vision_input = st.text_area("Define core 5 & 10-year blueprints:")
    if st.button("Update Long-Term Directives", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Goals", "Score": 10, "Notes": vision_input})
        st.success("Blueprints saved to system cloud array.")
