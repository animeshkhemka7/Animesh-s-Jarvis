import streamlit as st
import google.generativeai as genai
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. Page & Mobile View Configuration
st.set_page_config(
    page_title="Khemka Life OS",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS to make it feel like a premium native mobile app
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em; font-weight: bold;}
        .stTabs [data-baseweb="tab-list"] {gap: 8px; justify-content: space-around;}
        .stTabs [data-baseweb="tab"] {padding: 8px 12px; background-color: #f0f2f6; border-radius: 8px;}
    </style>
""", unsafe_allow_html=True)

# Initialize AI Engine
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.warning("⚠️ Connect your Gemini API Key in Streamlit Settings -> Secrets.")
    model = None

# Master Header
st.title("🎯 Khemka Life OS")
st.caption("Master Command Center | Animesh Khemka")

# Quick Nudge System (Top of App)
st.sidebar.markdown("### ⏰ Daily Reminders & Triggers")
if st.sidebar.button("✨ Get Micro-Nudge & Quote"):
    if model:
        nudge_prompt = "Give Animesh Khemka a powerful, highly specific, 2-sentence morning motivational quote and 3 rapid health reminders (e.g., water, posture, screen-time limit) for today."
        res = model.generate_content(nudge_prompt)
        st.sidebar.info(res.text)

# 7-Section Mobile Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "❤️ Health", "🧠 Learn", "💼 Biz", "🧘 Peace", "🤝 Rel", "📉 Finance", "🚀 Goals"
])

# ==========================================
# 1. HEALTH & FITNESS
# ==========================================
with tab1:
    st.header("💪 Health & Fitness Tracker")
    h_score = st.slider("Rate your physical state today", 1, 10, 7, key="h_sl")
    h_input = st.text_area("Log meals, junk food temptations, workouts, or symptoms:", placeholder="e.g., Had a light salad for lunch, felt low energy around 4 PM.", key="h_txt")
    h_file = st.file_uploader("Upload medical reports or fitness data:", type=["pdf", "png", "jpg"], key="h_fl")
    
    if st.button("Get Expert Health Alignment Advice", use_container_width=True):
        if model:
            with st.spinner("Processing physical logs..."):
                prompt = f"Act as an elite athletic doctor. Animesh rated his health {h_score}/10. User logs: {h_input}. Give specific, targeted suggestions by body part, lifestyle tweaks, and strict habits to reach a 10/10."
                st.info(model.generate_content(prompt).text)

# ==========================================
# 2. LEARNING & DEVELOPMENT
# ==========================================
with tab2:
    st.header("📚 Knowledge Vault")
    st.subheader("Summarize New Content")
    media_name = st.text_input("Enter Book Title or Podcast Episode:", placeholder="e.g., Think and Grow Rich")
    custom_notes = st.text_area("Paste your own summaries or notes if any:", key="l_notes")
    
    if st.button("Generate Tailored Summary Bank", use_container_width=True):
        if model:
            with st.spinner("Distilling key insights..."):
                prompt = f"Provide a comprehensive, high-utility summary of '{media_name}' specifically tailored for an ambitious entrepreneur. Highlight actionable rules he can implement instantly. Supplemental notes provided: {custom_notes}"
                st.info(model.generate_content(prompt).text)
                
    st.markdown("---")
    st.subheader("🧠 The Master 20-30 Rules Blueprint")
    if st.button("Compile Master Library Synthesizer", use_container_width=True):
        if model:
            with st.spinner("Synthesizing your global library..."):
                prompt = "Analyze core wisdom from top performance books (Atomic Habits, Principles, Zero to One). Output a precise, actionable list of the 'Top 25 Absolute Rules to Live By' tailored for daily operation."
                st.success(model.generate_content(prompt).text)

# ==========================================
# 3. WORK & BUSINESS
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy & Execution")
    biz_name = st.text_input("Venture/Project Name:", placeholder="e.g., Export & Gifting Venture")
    biz_score = st.slider("Rate current execution momentum", 1, 10, 6, key="b_sl")
    biz_strategy = st.text_area("Current core challenges or strategies in mind:")
    
    if st.button("Consult Corporate Strategy Engine", use_container_width=True):
        if model:
            with st.spinner("Analyzing operational directives..."):
                prompt = f"Act as an elite McKinsey business strategist. Venture: {biz_name}. Momentum Score: {biz_score}/10. Current strategy/problem: {biz_strategy}. Provide a detailed, long-term roadmap, mitigation strategy for friction points, and unique product utility ideas to succeed globally."
                st.info(model.generate_content(prompt).text)

# ==========================================
# 4. PEACE & SUCCESS
# ==========================================
with tab4:
    st.header("🧘 Mindset & Alignment")
    st.subheader("✨ Mental Fortification & Energy Shielding")
    if st.button("Get Daily Manifestation & Focus Ritual", use_container_width=True):
        if model:
            prompt = "Provide a high-performance morning manifestation exercise, a 5-minute deep breathing technique, and explicit mental models on how to protect energy and ruthlessly block out negativity or toxic family dynamics."
            st.info(model.generate_content(prompt).text)
            
    st.markdown("---")
    st.subheader("🌌 Cosmic Alignment & Remedies")
    astro_file = st.file_uploader("Upload Astrological Birth Chart (PDF/Image):", type=["pdf", "png", "jpg"], key="astro_fl")
    if st.button("Analyze Astrological Chart", use_container_width=True):
        if model and astro_file:
            with st.spinner("Decoding chart arrays..."):
                # Pass file to model safely
                prompt = "Analyze this astrological data/chart image. Provide core personal insights, upcoming energetic shifts, and highly practical daily remedies/routines to optimize performance."
                st.info(model.generate_content([prompt, astro_file]).text)
        elif not astro_file:
            st.warning("Please upload a file or screenshot of your chart first.")

# ==========================================
# 5. RELATIONSHIPS
# ==========================================
with tab5:
    st.header("🤝 Relationship Alignment Tracker")
    r_score = st.slider("Rate core personal relationship harmony", 1, 10, 7, key="r_sl")
    r_notes = st.text_area("Log current dynamics, important dates, or friction points:", placeholder="e.g., Balancing time between high-stress work weeks and family obligations.")
    
    if st.button("Generate Relationship Growth Roadmap", use_container_width=True):
        if model:
            prompt = f"Act as a premier relationship psychologist. Animesh rates current alignment as {r_score}/10. Context: {r_notes}. Provide 3 clear, practical actions to deepen bonds, improve empathetic communication, and protect valuable connections."
            st.info(model.generate_content(prompt).text)

# ==========================================
# 6. INDIAN FINANCE ENGINE (Real-Time + AI)
# ==========================================
with tab6:
    st.header("📉 Indian Financial Markets")
    
    # Morning Snapshot Generator
    if st.button("☀️ Pull Indian Market Pre-Open Snapshot", use_container_width=True):
        if model:
            with st.spinner("Fetching live market vectors..."):
                try:
                    # Safely sample key indices via yfinance
                    nifty = yf.Ticker("^NSEI").history(period="2d")
                    sensex = yf.Ticker("^BSESN").history(period="2d")
                    nifty_close = nifty['Close'].iloc[-1] if not nifty.empty else "N/A"
                    sensex_close = sensex['Close'].iloc[-1] if not sensex.empty else "N/A"
                    
                    market_prompt = f"Generate an assertive, highly actionable morning market layout for an active Indian stock investor. Mention key trend focus points. Quick context numbers: Nifty 50 at {nifty_close}, Sensex at {sensex_close}. Provide 3 high-probability alpha investment sectors/ideas for today."
                    st.info(model.generate_content(market_prompt).text)
                except Exception as e:
                    st.error(f"Market fetch issue: {e}")

    st.markdown("---")
    st.subheader("🔍 Deep-Dive Stock Analysis Engine")
    ticker_input = st.text_input("Enter Indian Ticker Symbol (e.g., RELIANCE.NS, TCS.NS, INFY.NS):", value="RELIANCE.NS")
    
    if st.button("Run Comprehensive Fundamental + Technical Audit", use_container_width=True):
        with st.spinner(f"Scraping live execution metrics for {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                hist = stock.history(period="6mo")
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    ma_50 = hist['Close'].rolling(50).mean().iloc[-1]
                    ma_200 = hist['Close'].rolling(200).mean().iloc[-1]
                    
                    # Extract safe baseline metrics from yfinance
                    metrics_summary = f"""
                    Ticker: {ticker_input}
                    Current Price: ₹{current_price:.2f}
                    50-Day Moving Average: ₹{ma_50:.2f}
                    200-Day Moving Average: ₹{ma_200:.2f}
                    Recent Volume: {hist['Volume'].iloc[-1]}
                    """
                    
                    st.text_area("Live Extracted Metrics Data:", metrics_summary, height=120)
                    
                    if model:
                        ai_finance_prompt = f"""
                        You are a brilliant hedge fund analyst specializing in the National Stock Exchange of India (NSE). 
                        Analyze this raw price and structural tracking data for {ticker_input}:
                        {metrics_summary}
                        
                        Run a comprehensive fundamental and technical cross-examination. Output a detailed report:
                        1. Technical health assessment (Price vs 50MA/200MA trends).
                        2. Key support and resistance estimation.
                        3. Definitive Buy/Hold/Sell recommendation with explicit reasoning.
                        """
                        st.markdown("### 🤖 Deep-Dive Recommendation Report")
                        st.write(model.generate_content(ai_finance_prompt).text)
                else:
                    st.error("Could not locate ticker data. Please make sure to append '.NS' for National Stock Exchange listings.")
            except Exception as ex:
                st.error(f"Error executing market analysis: {ex}")

    st.markdown("---")
    st.subheader("📋 Master Portfolio Review")
    portfolio_file = st.file_uploader("Upload Portfolio Sheet (Excel/CSV):", type=["xlsx", "csv"], key="port_fl")
    if st.button("Execute Portfolio Audit", use_container_width=True):
        if model and portfolio_file:
            with st.spinner("Auditing risk exposures..."):
                prompt = "Review this stock portfolio data sheet. Identify heavy concentration risks, underperforming allocations, and provide structural balancing moves tailored for Indian market conditions."
                st.info(model.generate_content([prompt, portfolio_file]).text)

# ==========================================
# 7. LONG-TERM GOALS & STRATEGY
# ==========================================
with tab7:
    st.header("🚀 Macro Strategy & Vision")
    g_vision = st.text_area("Your 5-Year and 10-Year Grand Vision:", placeholder="Describe the scale of impact, businesses, and life lifestyle you are actively building towards.")
    g_score = st.slider("Rate macro execution alignment toward goals", 1, 10, 5, key="g_sl")
    
    if st.button("Synthesize Long-Term Strategy Vectors", use_container_width=True):
        if model:
            with st.spinner("Mapping long-range strategies..."):
                prompt = f"Review Animesh's long-term macro vision: '{g_vision}'. His self-rated momentum is {g_score}/10. Break down a quarterly execution framework, call out critical blind spots he must manage, and offer alternative strategic levers to accelerate his trajectory."
                st.info(model.generate_content(prompt).text)
