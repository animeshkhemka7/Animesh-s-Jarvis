import streamlit as st
import google.generativeai as genai
import pandas as pd

st.set_page_config(
    page_title="Animesh Life OS",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    
""", unsafe_allow_html=True)

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.warning("⚠️ Please connect your Gemini API Key in the settings.")
    model = None

st.title("🎯 Khemka Life OS")
st.caption("The Master Hub for Animesh Khemka")
st.write("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["❤️ Health", "🧠 Learning", "💼 Business", "📉 Finance", "✨ Peace"])

with tab1:
    st.header("💪 Health & Fitness")
    st.subheader("Today's Vitals")
    health_score = st.slider("Rate your physical alignment today (1 = Poor, 10 = Peak)", 1, 10, 7)
    
    st.subheader("Log Data")
    input_mode = st.radio("Choose Input Type:", ["Text/Voice Note", "Upload File/Image"], horizontal=True)
    
    user_notes = ""
    uploaded_file = None
    
    if input_mode == "Text/Voice Note":
        user_notes = st.text_area("Type your meal updates, workout summaries, or voice transcripts here:", 
                                  placeholder="e.g., Had a heavy business lunch today. Tracked back pain on lower right side.")
    else:
        uploaded_file = st.file_uploader("Drop gym Excel sheets, medical PDFs, or fitness device screenshots here:", type=["pdf", "png", "jpg", "xlsx"])

    if st.button("Generate Expert Health Analysis", use_container_width=True):
        if model:
            with st.spinner("Analyzing data against expert benchmarks..."):
                prompt = f"""
                You are Animesh Khemka's elite personal health and medical AI advisor. 
                Animesh has rated his physical well-being today as {health_score}/10.
                
                Recent input logs/data: {user_notes}
                
                Provide a hyper-tailored, concise, actionable assessment. 
                1. Break down advice by specific body parts if relevant.
                2. Give him specific mitigation tips if his score is low.
                3. Outline 3 specific optimization steps for his day.
                Keep it direct, high-level, and formatted beautifully for a mobile screen.
                """
                
                try:
                    response = model.generate_content(prompt)
                    st.success("Analysis Complete")
                    st.info(response.text)
                except Exception as e:
                    st.error(f"Error communicating with AI Brain: {e}")
        else:
            st.error("AI Brain disconnected. Please configure your API key.")

with tab2:
    st.header("📚 Learning & Development")
    st.write("Coming up next: The book and podcast summary bank with your core 30 rules to live by.")

with tab3:
    st.header("🏢 Work & Business")
    st.write("Coming up next: Venture tracking, SWOT, and long-term business advisory models.")

with tab4:
    st.header("📊 Indian Market Finance")
    st.write("Coming up next: Real-time NSE/BSE stock pulling, fundamental analysis, and automated morning trading strategies.")

with tab5:
    st.header("🧘 Peace & Success")
    st.write("Coming up next: Mindset blocks, manifestation trackers, and PDF birth chart reading engines.")
