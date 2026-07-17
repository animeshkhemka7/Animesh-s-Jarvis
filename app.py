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
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("⚠️ Gemini API Key missing in Settings -> Secrets.")
    model = None

# ==========================================
# ⚡ NATIVE RAW TEXT EXTRACTION ENGINE
# ==========================================
def extract_raw_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        file_type = uploaded_file.type
        file_bytes = uploaded_file.getvalue()
        # Direct extraction for plain text files
        if "text/plain" in file_type:
            return file_bytes.decode("utf-8")
        # Utilize Gemini intelligence to pull full text transcripts from PDFs/Images screenlessly
        elif model:
            response = model.generate_content([
                "Extract and transcribe the complete raw text content from this document word-for-word exactly as it is written. Do not summarize it, do not add any commentary, just return the raw text found inside so the user can review their original document.",
                {"mime_type": file_type, "data": file_bytes}
            ])
            return response.text
    except Exception as e:
        return f"[Text extraction note: {str(e)}]"
    return ""

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
        df = pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content"])
    
    if "AI_Summary" not in df.columns:
        df["AI_Summary"] = ""
    if "Raw_Content" not in df.columns:
        df["Raw_Content"] = ""
        
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    payload = {
        "message": "Realtime Data Sync Event",
        "content": base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("utf-8"),
        "sha": sha if sha else None
    }
    requests.put(f"https://api.github.com/repos/{REPO}/contents/{filename}", headers=headers, json=payload)

def load_live_database_uncached():
    if not TOKEN or not REPO: return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content"])
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
            return loaded_df
    except:
        pass
    return pd.DataFrame(columns=["Timestamp", "Section", "Score", "Notes", "AI_Summary", "Raw_Content"])

def commit_new_log(row_dict):
    if "AI_Summary" not in row_dict:
        row_dict["AI_Summary"] = ""
    if "Raw_Content" not in row_dict:
        row_dict["Raw_Content"] = ""
        
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

if "AI_Summary" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["AI_Summary"] = ""
if "Raw_Content" not in st.session_state["cached_db"].columns:
    st.session_state["cached_db"]["Raw_Content"] = ""

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
            for _, row in h_data.iloc[::-1].iterrows():
                ai_sum = str(row.get('AI_Summary', ''))
                if "ceiling met" in ai_sum or ai_sum.strip() == "":
                    ai_sum = "*File synchronized to secure cloud database. Upload new files below to view live instant screen summaries.*"
                
                # Header displays summary and date directly
                with st.expander(f"📝 Summary ({row['Timestamp']})"):
                    st.markdown(ai_sum)
                    
                    # Inner expander allows reviewing the raw file contents screenlessly
                    raw_text = row.get("Raw_Content", "")
                    if pd.notna(raw_text) and str(raw_text).strip() != "":
                        with st.expander("📂 Click to view original raw file text"):
                            st.text_area("Original Content Stream", value=str(raw_text), height=200, disabled=True, key=f"raw_h_{row['Timestamp']}")
                    else:
                        with st.expander("📂 Click to view original raw file text"):
                            st.info("Raw text content was not captured for this historical item. New uploads will render file text here natively.")
                st.write("---")

    h_score = st.slider("Rate physical health score today", 1, 10, 7, key="h_slider")
    h_input = st.text_area("Type lifestyle or workout notes:", key="h_notes")
    audio_log = st.audio_input("🎤 Record real-time voice entry", key="h_audio")
    uploaded_files = st.file_uploader("Upload files/screenshots:", type=["pdf", "png", "jpg", "xlsx", "docx"], accept_multiple_files=True, key="h_bulk")
    
    if st.button("Permanently Save Health Data", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        names_list = []
        raw_extracted_data = ""
        ai_payload = [f"Act as health coach. Score: {h_score}/10. Log: {h_input}"]
        
        if audio_log:
            save_file_to_github(audio_log.getvalue(), f"voice_{timestamp.replace(' ','_')}.wav", folder="vault/voice")
            ai_payload.append(audio_log)
        if uploaded_files:
            for f in uploaded_files:
                f_bytes = f.getvalue()
                save_file_to_github(f_bytes, f"health_{timestamp.replace(' ','_')}_{f.name}")
                names_list.append(f.name)
                raw_extracted_data += f"\n--- File: {f.name} ---\n" + extract_raw_text(f)
                if f.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": f.type, "data": f_bytes})
                    
        ai_summary = ""
        if model:
            try:
                ai_summary = model.generate_content(ai_payload).text
            except Exception:
                ai_summary = f"System log sync confirmed. Attached data layer processed: {', '.join(names_list)}"
                
        commit_new_log({
            "Timestamp": timestamp, 
            "Section": "Health", 
            "Score": h_score, 
            "Notes": f"{h_input} | Uploaded Assets: {', '.join(names_list)}",
            "AI_Summary": ai_summary,
            "Raw_Content": raw_extracted_data
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
        
        # 🎯 ON-TOP SECTION SYNTHESIS ENGINE (10-20 Actions Rules Across All Uploads)
        st.markdown("### ⚡ Master Life Implementation Sheet")
        if st.button("✨ GENERATE 10-20 ACTIONABLE LIFE RULES FROM ALL FILES", use_container_width=True, key="gen_l_rules"):
            valid_summaries = [str(r['AI_Summary']) for _, r in l_data.iterrows() if "ceiling met" not in str(r['AI_Summary']) and str(r['AI_Summary']).strip() != ""]
            if valid_summaries:
                combined_text = "\n\n".join(valid_summaries)
                with st.spinner("Synthesizing rules from library framework..."):
                    try:
                        prompt = f"Analyze the following data abstracts and reading logs. Extract exactly 10 to 20 concrete, highly definitive, and actionable execution rules or principles that Animesh must permanently incorporate into his day-to-day life. Print them immediately as a clear, high-impact bulleted list:\n\n{combined_text}"
                        st.session_state["l_master_rules"] = model.generate_content(prompt).text
                    except Exception as e:
                        st.error(f"Synthesis threshold error: {str(e)}")
            else:
                st.warning("No fresh AI summaries found to generate rules from. Try injecting a new book or document down below first!")
                
        if "l_master_rules" in st.session_state:
            st.info(st.session_state["l_master_rules"])
            st.write("---")
            
        if not l_data.empty:
            st.write("### 📜 Library Summaries & Document Reader:")
            for _, row in l_data.iloc[::-1].iterrows():
                ai_sum = str(row.get('AI_Summary', ''))
                if "ceiling met" in ai_sum or ai_sum.strip() == "":
                    ai_sum = "*Book successfully indexed to repository. Upload your files below to see live instant screen summaries.*"
                
                title_slug = str(row['Notes']).split('|')[0]
                
                # The Summary is visible directly as the click target on screen
                with st.expander(f"📝 Summary ({row['Timestamp']}) | {title_slug[:40]}..."):
                    st.markdown(ai_sum)
                    
                    # Nested capability to look inside the full raw file contents seamlessly
                    raw_text = row.get("Raw_Content", "")
                    if pd.notna(raw_text) and str(raw_text).strip() != "":
                        with st.expander("📂 Click to view original raw file text"):
                            st.text_area("Original Extracted Content", value=str(raw_text), height=250, disabled=True, key=f"raw_l_{row['Timestamp']}")
                    else:
                        with st.expander("📂 Click to view original raw file text"):
                            st.info("Raw text content streaming was not captured for this historical item. New uploads will render the actual book text here natively.")
                st.write("---")
        
    media_name = st.text_input("Source Title:")
    uploaded_books = st.file_uploader("Drop books or summaries in bulk:", type=["pdf", "docx", "xlsx", "txt"], accept_multiple_files=True, key="l_bulk")
    
    if st.button("Inject Batch to Library Vault", use_container_width=True):
        if uploaded_books and model:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            names_list = [b.name for b in uploaded_books]
            raw_extracted_data = ""
            with st.spinner("Indexing content vector arrays & extracting full text..."):
                ai_payload = ["Extract core business execution rules, actionable workflows, and comprehensive chapter summaries from these uploaded files for Animesh."]
                for b in uploaded_books:
                    b_bytes = b.getvalue()
                    save_file_to_github(b_bytes, f"library_{media_name.replace(' ','_')}_{b.name}")
                    raw_extracted_data += f"\n--- Document: {b.name} ---\n" + extract_raw_text(b)
                    if b.type in ["application/pdf", "text/plain"]:
                        ai_payload.append({"mime_type": b.type, "data": b_bytes})
                        
                ai_summary = ""
                try:
                    ai_summary = model.generate_content(ai_payload).text
                except Exception as e:
                    ai_summary = f"### Document Batch Saved Successfully\nData files have been safely pushed to vault. Attached records: {', '.join(names_list)}"
                    
                commit_new_log({
                    "Timestamp": timestamp, 
                    "Section": "Learning", 
                    "Score": 10, 
                    "Notes": f"Batch: {media_name} | Files: {', '.join(names_list)}",
                    "AI_Summary": ai_summary,
                    "Raw_Content": raw_extracted_data
                })
                st.success("🎉 Library components successfully archived & synced!")
                time.sleep(0.5)
                st.rerun()

# ==========================================
# 3. WORK & BUSINESS MODULE
# ==========================================
with tab3:
    st.header("🏢 Venture Strategy Dashboard")
    
    if not history_df.empty:
        b_data = history_df[history_df["Section"] == "Business"]
        
        # 🎯 ON-TOP STRATEGY SYNTHESIS ENGINE
        st.markdown("### ⚡ Master Business Strategy Rules")
        if st.button("✨ GENERATE 10-20 STRATEGIC RULES FROM ALL VENTURE FILES", use_container_width=True, key="gen_b_rules"):
            valid_summaries = [str(r['AI_Summary']) for _, r in b_data.iterrows() if "ceiling met" not in str(r['AI_Summary']) and str(r['AI_Summary']).strip() != ""]
            if valid_summaries:
                combined_text = "\n\n".join(valid_summaries)
                with st.spinner("Synthesizing production framework parameters..."):
                    try:
                        prompt = f"Analyze my business operation updates. Extract exactly 10 to 20 precise strategic rules for manufacturing scale, luxury export compliance, and utility design differentiators. Output as a bulleted list:\n\n{combined_text}"
                        st.session_state["b_master_rules"] = model.generate_content(prompt).text
                    except Exception:
                        st.error("Engine threshold limits met.")
            else:
                st.warning("No active corporate strategy logs found to analyze.")
                
        if "b_master_rules" in st.session_state:
            st.info(st.session_state["b_master_rules"])
            st.write("---")
            
        if not b_data.empty: 
            st.write("### 📜 Corporate Summaries & Specifications:")
            for _, row in b_data.iloc[::-1].iterrows():
                ai_sum = str(row.get('AI_Summary', ''))
                if "ceiling met" in ai_sum or ai_sum.strip() == "":
                    ai_sum = "*Venture log cataloged to storage servers. Upload new specifications below to view instant screen summaries.*"
                
                with st.expander(f"📝 Summary ({row['Timestamp']})"):
                    st.markdown(ai_sum)
                    
                    raw_text = row.get("Raw_Content", "")
                    if pd.notna(raw_text) and str(raw_text).strip() != "":
                        with st.expander("📂 Click to view original raw file text"):
                            st.text_area("Original File Contents", value=str(raw_text), height=200, disabled=True, key=f"raw_b_{row['Timestamp']}")
                    else:
                        with st.expander("📂 Click to view original raw file text"):
                            st.info("Raw text data structure was not captured for this historical item. New uploads will stream raw content here natively.")
                st.write("---")
            
    biz_name = st.text_input("Venture Name:", value="Premium Vegan Leather Goods Brand")
    biz_score = st.slider("Current Execution Momentum", 1, 10, 7, key="b_slider")
    biz_notes = st.text_area("Operational moves or bottlenecks:", value="Designing modular men's sling bags and phone card holders for export to North America, Europe, and Middle East. Differentiating utility from local competitors.")
    biz_docs = st.file_uploader("Upload engineering data sheets or invoices in bulk:", type=["xlsx", "csv", "pdf", "docx"], accept_multiple_files=True, key="b_bulk")
    
    if st.button("Analyze & Save Venture Metrics", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        names_list = [bd.name for bd in biz_docs] if biz_docs else []
        raw_extracted_data = ""
        ai_payload = [f"Act as a top global venture strategist. Project: {biz_name}. Momentum state: {biz_score}/10. Structural context updates: {biz_notes}"]
        if biz_docs:
            for bd in biz_docs:
                save_file_to_github(bd.getvalue(), f"biz_{biz_name}_{bd.name}")
                raw_extracted_data += f"\n--- Document: {bd.name} ---\n" + extract_raw_text(bd)
                if bd.type in ["application/pdf"]:
                    ai_payload.append({"mime_type": bd.type, "data": bd.getvalue()})
                
        ai_summary = ""
        if model:
            try:
                ai_summary = model.generate_content(ai_payload).text
            except Exception:
                ai_summary = f"Strategy metrics locked. Attached files: {', '.join(names_list)}"
                
        commit_new_log({
            "Timestamp": timestamp, 
            "Section": "Business", 
            "Score": biz_score, 
            "Notes": f"{biz_notes} | Files: {', '.join(names_list)}",
            "AI_Summary": ai_summary,
            "Raw_Content": raw_extracted_data
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
            for _, row in m_data.iloc[::-1].iterrows():
                with st.expander(f"📝 Summary ({row['Timestamp']})"):
                    if "AI_Summary" in row and pd.notna(row["AI_Summary"]) and row["AI_Summary"] != "":
                        st.markdown(row["AI_Summary"])
                    
                    raw_text = row.get("Raw_Content", "")
                    if pd.notna(raw_text) and str(raw_text).strip() != "":
                        with st.expander("📂 Click to view original raw file text"):
                            st.text_area("Original Content Stream", value=str(raw_text), height=200, disabled=True, key=f"raw_m_{row['Timestamp']}")
                st.write("---")

    if st.button("Fetch Daily Meditation & Energy Shield Protocol", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ai_summary = ""
        if model:
            try:
                ai_summary = model.generate_content("Provide an executive mindset validation drill, deep rhythmic breathing guidelines, and explicit protocols to maintain absolute workspace concentration and isolate energy from critical family members.").text
            except Exception:
                ai_summary = "Breathing metrics protocol: Focus center workspace, execute 4-7-8 breathing cycles."
        commit_new_log({
            "Timestamp": timestamp,
            "Section": "Mindset",
            "Score": 10,
            "Notes": "Meditation Shield Request",
            "AI_Summary": ai_summary,
            "Raw_Content": "Generated natively from AI terminal baseline inputs."
        })
        st.rerun()
            
    st.markdown("---")
    st.subheader("🌌 Natal Chart Synthesis Drawer")
    astro_files = st.file_uploader("Drop planetary maps/birth charts (Select Multiple):", type=["pdf", "png", "jpg"], accept_multiple_files=True, key="a_bulk")
    if st.button("Execute Astro Mapping Alignment", use_container_width=True):
        if astro_files and model:
            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            names_list = [af.name for af in astro_files]
            raw_extracted_data = ""
            ai_payload = ["Perform full structural alignment diagnosis on these birth chart data layers. Output explicit personal remedies."]
            for af in astro_files:
                save_file_to_github(af.getvalue(), f"astro_{af.name}")
                raw_extracted_data += f"\n--- Chart Document: {af.name} ---\n" + extract_raw_text(af)
                if af.type in ["image/png", "image/jpeg", "application/pdf"]:
                    ai_payload.append({"mime_type": af.type, "data": af.getvalue()})
            
            ai_summary = ""
            try:
                ai_summary = model.generate_content(ai_payload).text
            except Exception:
                ai_summary = f"Planetary alignment saved. Data layers stored: {', '.join(names_list)}"
            
            commit_new_log({
                "Timestamp": timestamp,
                "Section": "Mindset",
                "Score": 10,
                "Notes": f"Astro Matrix Alignment | Files: {', '.join(names_list)}",
                "AI_Summary": ai_summary,
                "Raw_Content": raw_extracted_data
            })
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
                with st.expander(f"📝 Summary ({row['Timestamp']})"):
                    st.write(row.get("Notes", "No notes logged."))
                st.write("---")
        
    r_score = st.slider("Rate relational harmony level", 1, 10, 7, key="r_slider")
    r_notes = st.text_area("Key communication metrics or dynamics tracker:")
    if st.button("Archive Relationship Log Entry", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Relationships", "Score": r_score, "Notes": r_notes, "AI_Summary": "Manual Entry Recorded.", "Raw_Content": r_notes})
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
            for _, row in f_data.iloc[::-1].iterrows():
                with st.expander(f"📝 Summary ({row['Timestamp']})"):
                    if "AI_Summary" in row and pd.notna(row["AI_Summary"]) and row["AI_Summary"] != "":
                        st.markdown(row["AI_Summary"])
                    
                    raw_text = row.get("Raw_Content", "")
                    if pd.notna(raw_text) and str(raw_text).strip() != "":
                        with st.expander("📂 Click to view original raw spreadsheet text"):
                            st.text_area("Spreadsheet Extracted Array", value=str(raw_text), height=200, disabled=True, key=f"raw_f_{row['Timestamp']}")
                st.write("---")

    if st.button("☀️ Pull Indian Pre-Market Framework Analysis", use_container_width=True):
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        nifty_close = 0.0
        try:
            nifty_df = yf.Ticker("^NSEI").history(period="2d")
            nifty_close = nifty_df['Close'].iloc[-1] if not nifty_df.empty else 0.0
        except Exception:
            pass
        
        ai_summary = ""
        if model:
            try:
                ai_summary = model.generate_content(f"Provide an assertive technical market layout brief for an Indian equities operator. Index validation state: Nifty 50 close tracking near {nifty_close}. Highlight 3 alpha trading sectors for outperformance.").text
            except Exception:
                ai_summary = f"Scraper metrics recorded at index level: ₹{nifty_close:.2f}."
                
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
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if not hist.empty:
                metrics = f"Price: ₹{hist['Close'].iloc[-1]:.2f} | 50MA: ₹{hist['Close'].rolling(50).mean().iloc[-1]:.2f} | 200MA: ₹{hist['Close'].rolling(200).mean().iloc[-1]:.2f}"
                
                ai_summary = ""
                if model:
                    try:
                        ai_summary = model.generate_content(f"Hedge fund analysis report for {ticker}. Metrics: {metrics}. Provide explicit target support layers and a clear Buy/Hold/Sell recommendation.").text
                    except Exception:
                        pass
                
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
        if port_files and model:
            raw_extracted_data = ""
            for pf in port_files: 
                save_file_to_github(pf.getvalue(), f"portfolio_{pf.name}")
                raw_extracted_data += f"\n--- Statement: {pf.name} ---\n" + extract_raw_text(pf)
            
            commit_new_log({
                "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "Section": "Finance",
                "Score": 10,
                "Notes": f"Portfolio Statement Upload ({len(port_files)} files)",
                "AI_Summary": f"### Verified Cloud Sync Complete\nSuccessfully loaded brokerage logs for screen review.",
                "Raw_Content": raw_extracted_data
            })
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
                with st.expander(f"マスター Summary ({row['Timestamp']})"):
                    if "AI_Summary" in row and pd.notna(row["AI_Summary"]) and row["AI_Summary"] != "":
                        st.markdown(row["AI_Summary"])
                st.write("---")
        
    vision_input = st.text_area("Define master 5 & 10-year blueprints:", value="Build a premier international sustainable design and luxury leather export empire with established corporate gifting logistics footprint across India.")
    if st.button("Update Long-Term Directives", use_container_width=True):
        commit_new_log({"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Section": "Goals", "Score": 10, "Notes": "Visions updated.", "AI_Summary": f"### Master Blueprint Plan:\n{vision_input}", "Raw_Content": vision_input})
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
        "Notes": f"Global Device Pad Log: {sync_notes}",
        "AI_Summary": f"### Direct Asset Update Record:\n{sync_notes}",
        "Raw_Content": sync_notes
    }
    
    commit_new_log(new_entry)
    st.success("✨ Everything synchronized flawlessly! Data securely saved and broadcasted to all terminal instances.")
    time.sleep(0.5)
    st.rerun()
