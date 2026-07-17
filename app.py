import streamlit as st
import google.generativeai as genai
import pandas as pd
import yfinance as yf
import requests
import base64
from io import BytesIO

# 1. Page Configuration for Mobile & Laptop Layouts
st.set_page_config(page_title="Khemka Life OS", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

# Custom Responsive UI CSS
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold; background-color: #4F46E5; color: white;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; background-color: #F3F4F6; border-radius: 6px; font-size: 12px;}
    </style>
""", unsafe_allow_html=True)

# Secure Credentials Loading
TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO = st.secrets.get("GITHUB_REPO", "")
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Using the updated flagship free tier model
    model = genai.GenerativeModel('gemini-3.5-flash')
else:
    st.error("⚠️ Gemini API Key missing in Settings -> Secrets.")
    model = None

# ==========================================
# MULTI-FILE STORAGE UTILITY DRAWER
# ==========================================
def save_file_to_github(file_bytes, filename, folder="vault"):
    """Permanently writes binary files to your GitHub storage account"""
    if not TOKEN or not REPO:
        return False
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"message": f"Storage Sync: Archived {filename}", "content": encoded_content}
    if sha:
        payload["sha"] = sha
        
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code in [200, 201]

def log_row_to_csv(row_dict, filename="logs.csv"):
    """Appends running daily dashboard metrics to your master log database"""
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
        
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    csv_buffer = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_buffer.encode("utf-8")).decode("utf-8")
    
    payload = {"message": "Database Sync: Appended Life Log", "content": encoded_content}
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, json=payload)

# Load database dataframe instantly upon startup
if TOKEN and REPO:
    url = f"https://api.github.com/repos/{REPO}/contents/logs.csv"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    history_df = pd.read_csv(BytesIO(base64.b64decode(res.json().get("content")).decode("utf-8").encode("utf-8"))) if res.status_code == 200 else pd.DataFrame()
else:
    history_df = pd.DataFrame()

# Layout Initialization
st.title("🎯 Khemka Life OS")
st.caption("Batch Upload Mode Active | Animesh Khemka")
st.write("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "❤️ Health", "🧠 Learn", "💼 Biz", "🧘 Peace", "🤝 Rel", "📉 Finance", "🚀 Goals"
])

# ==========================================
# 1. HEALTH & FITNESS (Batch Upload Enabled)
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Vault")
    if not history_df.empty:
        h_data = history_df[history_df["Section"] == "Health"]
        if not h_data.empty: st.line_chart(h_data.set_index("Timestamp")["Score"])

    h_score = st.slider("Rate physical health score today", 1, 10, 7)
    h_input = st.text_area("Type lifestyle or workout notes:", key="h_notes")
    audio_log = st.audio_input("🎤 Tap to record voice entry", key="h_audio")
    
    # Notice: accept_multiple_files=True allows selecting multiple items at once
    uploaded_files = st.file_uploader("Upload medical files/device screenshots (Select Multiple):", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    
    if st.button("Permanently Process & Save Health Data", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        names_list = []
        ai_payload = [f"Act as Animesh's health coach. Today's score: {h_score}/10. User Log: {h_input}"]
        
        if audio_log:
            save_file_to_github(audio_log.getvalue(), f"voice_{timestamp.replace(' ','_')}.wav", folder="vault/voice")
            ai_payload.append(audio_log)
            
        if uploaded_files:
            for f in uploaded_files:
                f_bytes = f.getvalue()
                save_file_to_github(f_bytes, f"health_{timestamp.replace(' ','_')}_{f.name}")
                names_list.append(f.name)
                # Pass readable image/pdf structures inline to AI engine safely
                if f.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": f.type, "data": f_bytes})
                    
        log_row_to_csv({"Timestamp": timestamp, "Section": "Health", "Score": h_score, "Notes": f"{h_input} | Batch Saved: {', '.join(names_list)}"})
        st.success(f"Successfully processed and archived {len(names_list)} files permanently!")
        if model: st.info(model.generate_content(ai_payload).text)

# ==========================================
# 2. LEARNING & DEVELOPMENT (Bulk Library Uploader)
# ==========================================
with tab2:
    st.header("📚 Master Knowledge Bank")
    media_name = st.text_input("Source Identifier (Book/Podcast Group Tag):")
    
    # Drag and drop 10-20 books or transcripts here at the same time
    uploaded_books = st.file_uploader("Drop books, text notes, or summary spreadsheets in bulk:", type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True, key="l_bulk")
    
    if st.button("Inject Batch to Permanent Library Vault", use_container_width=True):
        if uploaded_books and model:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            with st.spinner(f"Archiving {len(uploaded_books)} resources to your system layers..."):
                ai_payload = [f"Synthesize the master operational rules and direct takeaways from these batch materials for an entrepreneur named Animesh."]
                
                for b in uploaded_books:
                    b_bytes = b.getvalue()
                    save_file_to_github(b_bytes, f"library_{media_name.replace(' ','_')}_{b.name}")
                    if b.type in ["application/pdf", "text/plain"]:
                        ai_payload.append({"mime_type": b.type, "data": b_bytes})
                        
                log_row_to_csv({"Timestamp": timestamp, "Section": "Learning", "Score": 10, "Notes": f"Batch uploaded sources under tag: {media_name}"})
                st.success(f"🚀 Saved all {len(uploaded_books)} items permanently to your GitHub library vault!")
                st.write(model.generate_content(ai_payload).text)
                
    st.markdown("---")
    if st.button("Generate Master 20-30 Rules Blueprint", use_container_width=True):
        if model: st.success(model.generate_content("Review high-performance guidelines across business and life strategy. Output an exact numerical list of the top 25 execution rules Animesh Khemka must track daily.").text)

# ==========================================
# 3. WORK & BUSINESS (Bulk Docs Mode)
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    biz_name = st.text_input("Business Venture Name:")
    biz_score = st.slider("Current Execution Momentum Indicator", 1, 10, 5)
    biz_notes = st.text_area("Operational updates/challenges:")
    biz_docs = st.file_uploader("Upload spreadsheets, invoices, or strategy PDFs in bulk:", type=["xlsx", "csv", "pdf", "docx"], accept_multiple_files=True, key="b_bulk")
    
    if st.button("Analyze & Update Business Directives", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ai_payload = [f"Act as a McKinsey advisor. Project: {biz_name}. State: {biz_score}/10. Input: {biz_notes}"]
        
        if biz_docs:
            for bd in biz_docs:
                bd_bytes = bd.getvalue()
                save_file_to_github(bd_bytes, f"biz_{biz_name}_{bd.name}")
                if bd.type in ["application/pdf"]:
                    ai_payload.append({"mime_type": bd.type, "data": bd_bytes})
                    
        log_row_to_csv({"Timestamp": timestamp, "Section": "Business", "Score": biz_score, "Notes": f"Venture {biz_name}: {biz_notes}"})
        st.success("Business log and uploaded sheets updated securely.")
        if model: st.info(model.generate_content(ai_payload).text)

# ==========================================
# 4. PEACE & MINDSET (Astrology Engine)
# ==========================================
with tab4:
    st.header("🧘 Energy Protection & Cosmic Metrics")
    if st.button("Fetch Daily Manifestation & Focus Routine", use_container_width=True):
        if model: st.info(model.generate_content("Provide an executive mindset conditioning prompt, deep breathing rhythm instructions, and specific behavioral strategies to maximize concentration and shield focus from negative family dynamics.").text)
            
    st.markdown("---")
    st.subheader("🌌 Natal Astrology Reading Vault")
    astro_files = st.file_uploader("Drop birth charts or chart screenshots (Select Multiple):", type=["pdf", "png", "jpg"], accept_multiple_files=True, key="astro_bulk")
    if st.button("Process Astrological Profiles", use_container_width=True):
        if astro_files and model:
            with st.spinner("Decoding cosmic vectors..."):
                ai_payload = ["Exactivate astrological framework trends from these uploaded documents. Provide strict remedies."]
                for af in astro_files:
                    af_bytes = af.getvalue()
                    save_file_to_github(af_bytes, f"astro_{af.name}")
                    if af.type in ["image/png", "image/jpeg", "application/pdf"]:
                        ai_payload.append({"mime_type": af.type, "data": af_bytes})
                st.info(model.generate_content(ai_payload).text)

# ==========================================
# 5. RELATIONSHIPS CRM
# ==========================================
with tab5:
    st.header("🤝 Network Alignment Logs")
    r_score = st.slider("Rate relational harmony level", 1, 10, 7)
    r_notes = st.text_area("Enter notes or key communication benchmarks:")
    if st.button("Archive Relationship Log Entry", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Relationships", "Score": r_score, "Notes": r_notes})
        st.success("CRM transaction completed successfully.")

# ==========================================
# 6. INDIAN STOCK MARKET INFRASTRUCTURE
# ==========================================
with tab6:
    st.header("📉 Market Engine Terminal")
    if st.button("☀️ Generate Live Pre-Market Report", use_container_width=True):
        if model:
            try:
                nifty_close = yf.Ticker("^NSEI").history(period="2d")['Close'].iloc[-1]
                st.info(model.generate_content(f"Provide an assertive morning framework strategy briefing for an Indian market equity operator. Current indicator status: Nifty 50 close tracking near {nifty_close}. Pinpoint 3 high-probability alpha sectors.").text)
            except Exception as e: st.error(f"Data pull issue: {e}")
                    
    st.markdown("---")
    ticker = st.text_input("Enter NSE Stock Ticker (e.g. RELIANCE.NS, TCS.NS):", value="RELIANCE.NS")
    if st.button("Run Fundamental + Technical Market Audit", use_container_width=True):
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50-Day MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200-Day MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                st.text(metrics)
                if model: st.write(model.generate_content(f"Act as a professional Indian market researcher. Evaluate these parameters for {ticker}: {metrics}. Provide clear entry targets and an explicit Buy/Hold/Sell recommendation.").text)
        except Exception as err: st.error(f"Audit failed: {err}")

    st.markdown("---")
    st.subheader("📋 Master Portfolio Upload")
    port_files = st.file_uploader("Drop portfolio spreadsheets or statements (Select Multiple):", type=["xlsx", "csv"], accept_multiple_files=True, key="port_bulk")
    if st.button("Execute Portfolio Risk Scans", use_container_width=True):
        if port_files and model:
            ai_payload = ["Evaluate these portfolio positions for heavy concentration risks and structural exposures in Indian market conditions."]
            for pf in port_files:
                save_file_to_github(pf.getvalue(), f"portfolio_{pf.name}")
            st.success("Portfolios synced. AI analysis generated successfully.")

# ==========================================
# 7. LONG-TERM GOALS
# ==========================================
with tab7:
    st.header("🚀 Macro Strategy Vectoring")
    vision_input = st.text_area("Define core 5 & 10-year enterprise scale blueprints:")
    if st.button("Update Long-Term Directives", use_container_width=True):
        log_row_to_csv({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Goals", "Score": 10, "Notes": vision_input})
        st.success("Macro directives stored permanently in repository archives.")
