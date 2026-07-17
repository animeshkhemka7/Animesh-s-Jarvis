import streamlit as st
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import requests
import base64
import json
from io import BytesIO

# 1. Page Configuration for Mobile
st.set_page_config(page_title="Khemka Life OS", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

# Premium Mobile UI Theme
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold; background-color: #4F46E5; color: white;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; background-color: #F3F4F6; border-radius: 6px; font-size: 12px;}
    </style>
""", unsafe_allow_html=True)

# Credentials Verification
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
# GITHUB PERMANENT STORAGE ENGINE FUNCTIONS
# ==========================================
def save_file_to_github(file_bytes, filename, folder="vault"):
    """Permanently saves any file uploaded from mobile directly to GitHub Repository"""
    if not TOKEN or not REPO:
        return False
    
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # Check if file already exists to get its unique tracking ID (sha)
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"message": f"App Log: Saved {filename}", "content": encoded_content}
    if sha:
        payload["sha"] = sha
        
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code in [200, 201]

def log_row_to_csv(row_dict, filename="logs.csv"):
    """Appends structural daily metrics data to a running CSV file on GitHub"""
    if not TOKEN or not REPO:
        return
    
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
        
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    
    csv_buffer = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_buffer.encode("utf-8")).decode("utf-8")
    
    payload = {"message": "App Log: Updated Metrics Tracker", "content": encoded_content}
    if sha:
        payload["sha"] = sha
        
    requests.put(url, headers=headers, json=payload)

def load_history_from_github(filename="logs.csv"):
    """Reads all historical tracking information to render dashboards"""
    if not TOKEN or not REPO:
        return pd.DataFrame()
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json().get("content")).decode("utf-8")
        return pd.read_csv(BytesIO(content.encode("utf-8")))
    return pd.DataFrame()

# Fetch baseline data history
history_df = load_history_from_github()

# Master Application Interface
st.title("🎯 Khemka Life OS")
st.caption("Permanent Storage Enabled Command Center")
st.write("---")

# Navigation Hub
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "❤️ Health", "🧠 Learn", "💼 Biz", "🧘 Peace", "🤝 Rel", "📉 Finance", "🚀 Goals"
])

# ==========================================
# 1. HEALTH & FITNESS MODULE (With File & Voice Persistence)
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Vault")
    
    # Render historic alignment trend directly from saved records
    if not history_df.empty:
        health_history = history_df[history_df["Section"] == "Health"]
        if not health_history.empty:
            st.caption("📈 Historical Health Alignment Trend")
            st.line_chart(health_history.set_index("Timestamp")["Score"])

    h_score = st.slider("Rate physical alignment today", 1, 10, 7)
    h_input = st.text_area("Log data, meals, workout insights, or daily metrics:", key="h_notes_field")
    
    st.caption("🎤 Record real-time voice updates:")
    audio_log = st.audio_input("Tap to speak your health logs", key="h_audio_input")
    
    uploaded_file = st.file_uploader("Upload permanent medical documents/images:", type=["pdf", "png", "jpg", "xlsx", "docx"])
    
    if st.button("Permanently Save & Analyze Logs", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        saved_file_name = ""
        
        # Save heavy assets to GitHub repository storage drawer automatically
        if uploaded_file:
            bytes_data = uploaded_file.getvalue()
            if save_file_to_github(bytes_data, f"health_{timestamp.replace(' ', '_')}_{uploaded_file.name}"):
                st.success(f"📁 {uploaded_file.name} saved permanently to vault!")
                saved_file_name = uploaded_file.name
                
        if audio_log:
            audio_bytes = audio_log.getvalue()
            save_file_to_github(audio_bytes, f"voice_log_{timestamp.replace(' ', '_')}.wav", folder="vault/voice")
            st.success("🎤 Voice note filed securely in history logs.")

        # Save metrics rows permanently to CSV
        log_row_to_csv({"Timestamp": timestamp, "Section": "Health", "Score": h_score, "Notes": f"{h_input} | Attached file: {saved_file_name}"})
        
        if model:
            with st.spinner("AI analyzing timeline records..."):
                prompt = f"Act as an elite personal health advisor. Animesh logged a status score of {h_score}/10 today. Context: {h_input}. Review details and provide immediate optimization updates."
                payload = [prompt]
                if audio_log:
                    payload.append(audio_log)
                if uploaded_file:
                    payload.append(uploaded_file)
                st.info(model.generate_content(payload).text)

# ==========================================
# 2. LEARNING & DEVELOPMENT MODULE (Growing Summary Bank)
# ==========================================
with tab2:
    st.header("📚 Knowledge & Library Vault")
    
    # Display running total of library entries if history exists
    if not history_df.empty:
        learn_history = history_df[history_df["Section"] == "Learning"]
        if not learn_history.empty:
            st.markdown(f"📊 **Total custom summaries compiled in library:** {len(learn_history)}")
    
    media_name = st.text_input("Enter Book Name or Podcast Ticker:")
    uploaded_book = st.file_uploader("Upload core summary document or audio source (PDF/Word/Excel):", type=["pdf", "docx", "xlsx", "txt"])
    
    if st.button("Commit Summary to Permanent Library", use_container_width=True):
        if media_name and model:
            with st.spinner("Indexing content vector layers..."):
                timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                
                # Execute permanent file sync to cloud repository
                if uploaded_book:
                    save_file_to_github(uploaded_book.getvalue(), f"library_{media_name.replace(' ', '_')}_{uploaded_book.name}")
                
                prompt = f"Analyze structural inputs for '{media_name}'. Provide an deep-dive summary containing core entrepreneurial takeaways tailored specifically for Animesh's day-to-day deployment."
                summary_output = model.generate_content([prompt, uploaded_book] if uploaded_book else [prompt]).text
                
                # Append text data permanently to history tracking logs
                log_row_to_csv({"Timestamp": timestamp, "Section": "Learning", "Score": 10, "Notes": f"Book: {media_name} Summary archived."})
                st.success("Archived to permanent cloud library!")
                st.info(summary_output)

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Hub")
    if not history_df.empty:
        biz_hist = history_df[history_df["Section"] == "Business"]
        if not biz_hist.empty:
            st.caption("📉 Strategic Operations Momentum Track")
            st.line_chart(biz_hist.set_index("Timestamp")["Score"])
            
    biz_name = st.text_input("Target Venture Name:")
    biz_score = st.slider("Rate operational speed/momentum", 1, 10, 5)
    biz_notes = st.text_area("Log current strategic moves or challenges:")
    biz_doc = st.file_uploader("Upload operational data sheets (Excel/Word/PDF):", type=["xlsx", "csv", "pdf", "docx"], key="biz_uploader")
    
    if st.button("Save & Consult Strategy Engine", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        if biz_doc:
            save_file_to_github(biz_doc.getvalue(), f"biz_{biz_name}_{biz_doc.name}")
        
        log_row_to_csv({"Timestamp": timestamp, "Section": "Business", "Score": biz_score, "Notes": f"Venture: {biz_name} | {biz_notes}"})
        
        if model:
            with st.spinner("Analyzing operational trends..."):
                prompt = f"Act as a premier business strategist. Venture: {biz_name}. Momentum: {biz_score}/10. Current alignment constraints: {biz_notes}. Review inputs and deliver direct tactical advice."
                st.info(model.generate_content([prompt, biz_doc] if biz_doc else [prompt]).text)

# ==========================================
# 4. PEACE & SUCCESS MODULE
# ==========================================
with tab4:
    st.header("🧘 Mindset & Cosmic Alignment")
    if st.button("Fetch Daily Manifestation & Protection Blueprint", use_container_width=True):
        if model:
            st.info(model.generate_content("Provide an executive mindset conditioning prompt, deep breathing rhythm instructions, and specific behavioral strategies to maximize concentration and shield energy from disruptive environments.").text)
            
    st.markdown("---")
    st.subheader("🌌 Natal Astrology Reading Vault")
    astro_file = st.file_uploader("Upload astrological birth chart (PDF/Image/Screenshot):", type=["pdf", "png", "jpg"])
    if st.button("Analyze & Update Astro Remedies", use_container_width=True):
        if astro_file and model:
            with st.spinner("Decoding alignments..."):
                save_file_to_github(astro_file.getvalue(), f"astro_chart_{pd.Timestamp.now().strftime('%Y%m%d')}.png")
                prompt = "Examine this birth chart deployment sheet. Outline the absolute best personal performance windows and standard daily grounding routine fixes."
                st.info(model.generate_content([prompt, astro_file]).text)

# ==========================================
# 5. RELATIONSHIPS MODULE
# ==========================================
with tab5:
    st.header("🤝 Interpersonal Network CRM")
    r_score = st.slider("Rate general relational health", 1, 10, 7)
    r_notes = st.text_area("Track updates, friction elements, or milestones:")
    if st.button("Log Matrix Records", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Relationships", "Score": r_score, "Notes": r_notes})
        st.success("Relational metrics log synced permanently.")

# ==========================================
# 6. INDIAN STOCK MARKET ENGINE
# ==========================================
with tab6:
    st.header("📉 Market Trading Terminal")
    if st.button("☀️ Compile Alpha Market Briefing", use_container_width=True):
        if model:
            with st.spinner("Scraping index layers..."):
                try:
                    nifty = yf.Ticker("^NSEI").history(period="2d")
                    nifty_close = nifty['Close'].iloc[-1] if not nifty.empty else "N/A"
                    prompt = f"Generate an assertive pre-market framework brief for an Indian equity operator. Baseline indicator check: Nifty 50 at {nifty_close}. Pinpoint 3 high-probability actionable sectors."
                    st.info(model.generate_content(prompt).text)
                except Exception as e:
                    st.error(f"Scraper error: {e}")
                    
    st.markdown("---")
    st.subheader("🔍 Equities Audit Deep-Dive")
    ticker = st.text_input("Enter Ticker Code (e.g., RELIANCE.NS, INFYS.NS):", value="RELIANCE.NS")
    if st.button("Execute Strategic Asset Audit", use_container_width=True):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                st.text(metrics)
                if model:
                    st.write(model.generate_content(f"Act as a professional technical equity researcher. Evaluate these conditions for {ticker}: {metrics}. Provide clear entry/exit points and clear Buy/Hold/Sell actions.").text)
        except Exception as err:
            st.error(f"Analysis error: {err}")

# ==========================================
# 7. LONG-TERM GOALS
# ==========================================
with tab7:
    st.header("🚀 Strategic Goal Vectoring")
    vision_input = st.text_area("Current 5/10 Year Trajectory Blueprints:")
    if st.button("Update Core Milestones", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Goals", "Score": 10, "Notes": vision_input})
        st.success("Macro directives stored permanently in repository archives.")
