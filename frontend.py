import streamlit as st
import requests
import uuid

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Inter:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hero */
    .hero {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        border-radius: 16px;
        padding: 48px 40px 36px;
        margin-bottom: 32px;
        text-align: center;
    }
    .hero h1 {
        font-family: 'Syne', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        color: #fff;
        margin: 0 0 8px;
        letter-spacing: -1px;
    }
    .hero p {
        color: #FFD700 ;
        font-size: 1.1rem;
        margin: 0;
    }

    /* Result cards */
    .result-card {
        background: #1e1e2e;
        border: 1px solid #2d2d44;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
    }
    .result-card h3 {
        font-family: 'Syne', sans-serif;
        color: #a78bfa;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 0 0 12px;
    }
    .result-card p {
        color: #FFD700;
        white-space: pre-wrap;
        line-height: 1.7;
        margin: 0;
        font-size: 0.95rem;
    }

    /* Stats row */
    .stat-pill {
        display: inline-block;
        background: #FFD700;
        border-radius: 20px;
        padding: 4px 14px;
        color: #a78bfa;
        font-size: 0.82rem;
        font-weight: 500;
        margin-right: 8px;
    }

    /* Thread badge */
    .thread-badge {
        font-size: 0.78rem;
        color: #64748b;
        font-family: monospace;
    }

    /* Streamlit button override */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        width: 100%;
        transition: opacity 0.2s;
    }
    .stButton > button:hover {
        opacity: 0.88;
        color: white;
    }

    /* Input */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1e1e2e;
        border: 1px solid #2d2d44;
        border-radius: 8px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* Hide default streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())[:8]

if "history" not in st.session_state:
    st.session_state.history = []   # list of (query, result_dict)


# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>✈️ AI Travel Planner</h1>
    <p>Flights · Hotels · Weather · Full Itinerary — powered by multi-agent AI</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Session")
    st.markdown(f'<span class="thread-badge">Thread: {st.session_state.thread_id}</span>', unsafe_allow_html=True)

    if st.button("🔄 New Session"):
        st.session_state.thread_id = str(uuid.uuid4())[:8]
        st.session_state.history = []
        st.rerun()

    st.divider()
    st.markdown("### 🕘 Past Queries")
    if st.session_state.history:
        for i, (q, _) in enumerate(reversed(st.session_state.history)):
            st.markdown(f"**{len(st.session_state.history) - i}.** {q[:50]}{'...' if len(q)>50 else ''}")
    else:
        st.caption("No queries yet.")

    st.divider()
    st.markdown("### 🔗 API Status")
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        if r.status_code == 200:
            st.success("Backend online")
        else:
            st.error("Backend error")
    except:
        st.error("Backend offline")


# ── Main Input ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input(
        "Where do you want to go?",
        placeholder="e.g. Plan a 5-day trip to Tokyo in December",
        label_visibility="collapsed"
    )
with col2:
    plan_btn = st.button("Plan Trip")


# ── API Call ───────────────────────────────────────────────────────────────────
if plan_btn and query.strip():
    with st.spinner("🤖 Agents working — flights, hotels, weather, itinerary..."):
        try:
            response = requests.post(
                f"{API_URL}/plan",
                json={
                    "query": query,
                    "thread_id": st.session_state.thread_id
                },
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                st.session_state.history.append((query, data))

                # Stats
                st.markdown(
                    f'<div style="margin-bottom:16px">'
                    f'<span class="stat-pill">🤖 {data.get("llm_calls", 0)} LLM calls</span>'
                    f'<span class="stat-pill">💬 {data.get("message_count", 0)} messages</span>'
                    f'<span class="stat-pill">🔖 thread: {data.get("thread_id","")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Results in tabs
                tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Itinerary", "✈️ Flights", "🏨 Hotels", "🌤️ Weather"])

                with tab1:
                    st.markdown(f"""
                    <div class="result-card">
                        <h3>Full Itinerary</h3>
                        <p>{data.get("itinerary", "No itinerary generated.")}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with tab2:
                    st.markdown(f"""
                    <div class="result-card">
                        <h3>Flight Information</h3>
                        <p>{data.get("flight_results", "No flight data.")}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with tab3:
                    st.markdown(f"""
                    <div class="result-card">
                        <h3>Hotel Recommendations</h3>
                        <p>{data.get("hotel_results", "No hotel data.")}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with tab4:
                    st.markdown(f"""
                    <div class="result-card">
                        <h3>Weather Forecast</h3>
                        <p>{data.get("weather_result", "No weather data.")}</p>
                    </div>
                    """, unsafe_allow_html=True)

            else:
                st.error(f"API error {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend. Run: `uvicorn backend:app --reload --port 8000`")
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. The agents might be taking longer than usual.")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")

elif plan_btn and not query.strip():
    st.warning("Enter a travel query first.")


# ── History viewer ─────────────────────────────────────────────────────────────
if st.session_state.history and not plan_btn:
    st.divider()
    st.markdown("### 🕘 Previous Result")
    last_query, last_data = st.session_state.history[-1]
    st.caption(f"Query: *{last_query}*")

    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Itinerary", "✈️ Flights", "🏨 Hotels", "🌤️ Weather"])
    with tab1:
        st.markdown(f"""<div class="result-card"><h3>Full Itinerary</h3><p>{last_data.get("itinerary","")}</p></div>""", unsafe_allow_html=True)
    with tab2:
        st.markdown(f"""<div class="result-card"><h3>Flights</h3><p>{last_data.get("flight_results","")}</p></div>""", unsafe_allow_html=True)
    with tab3:
        st.markdown(f"""<div class="result-card"><h3>Hotels</h3><p>{last_data.get("hotel_results","")}</p></div>""", unsafe_allow_html=True)
    with tab4:
        st.markdown(f"""<div class="result-card"><h3>Weather</h3><p>{last_data.get("weather_result","")}</p></div>""", unsafe_allow_html=True)



        # streamlit run frontend.py