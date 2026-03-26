import streamlit as st
import requests
import json
import time

# --- CONFIGURATION ---
# We now pull the key from Streamlit's secure storage
try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except:
    st.error("API Key not found! Please add it to your secrets.")
    st.stop()

MODEL_NAME = "openrouter/free"

st.set_page_config(page_title="Athlan AI - Your AI Fitness Coach", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    div[data-baseweb="select"] div, button { cursor: pointer !important; }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4CAF50, #8BC34A, #4CAF50);
        background-size: 200% 100%;
        animation: progressAnimation 2s linear infinite;
    }
    @keyframes progressAnimation {
        0% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
</style>
""", unsafe_allow_html=True)

# --- TRANSLATIONS ---
translations = {
    "English": {
        "title": "Athlan", "subtitle": "Create your personalized training plan",
        "sport": "Sport", "sport_placeholder": "e.g., Football",
        "skill_level": "Skill Level", "skill_levels": ["Beginner", "Amateur", "Intermediate", "Advanced", "Professional"],
        "duration": "Training duration (days)", "disabilities": "Disabilities",
        "equipment": "Equipment", "culture": "Cultural Prefs", "diet": "Diet Plan",
        "generate_btn": "Generate Plan", "plan_title": "Your Training Plan ({} - {})",
        "save_btn": "Save Plan", "translate_btn": "Translate Plan", "prompt_instruction": "Respond in English.",
        "cooldown": "Rate limit hit. Waiting 10s to retry..."
    },
    "Русский": {
        "title": "Athlan", "subtitle": "Создайте свой персональный план тренировок",
        "sport": "Спорт", "sport_placeholder": "напр., Футбол",
        "skill_level": "Уровень подготовки", "skill_levels": ["Новичок", "Любитель", "Средний", "Опытный", "Профессионал"],
        "duration": "Продолжительность", "disabilities": "Ограничения",
        "equipment": "Оборудование", "culture": "Предпочтения", "diet": "Питание",
        "generate_btn": "Создать план", "plan_title": "Ваш план тренировок ({} - {})",
        "save_btn": "Сохранить", "translate_btn": "Перевести", "prompt_instruction": "Отвечайте на русском языке.",
        "cooldown": "Лимит превышен. Ожидание 10с..."
    },
    "O`zbek": {
        "title": "Athlan", "subtitle": "Shaxsiy mashq rejangizni yarating",
        "sport": "Sport", "sport_placeholder": "masalan, Futbol",
        "skill_level": "Mahorat darajasi", "skill_levels": ["Boshlang`ich", "Havaskor", "O`rta", "Yuqori", "Professional"],
        "duration": "Davomiyligi (kun)", "disabilities": "Nogironliklar",
        "equipment": "Jihozlar", "culture": "Madaniyat", "diet": "Parhez",
        "generate_btn": "Reja yaratish", "plan_title": "Mashq rejangiz ({} - {})",
        "save_btn": "Saqlash", "translate_btn": "Tarjima qilish", "prompt_instruction": "Javobni o`zbek tilida bering.",
        "cooldown": "Limitga yetildi. 10s kutilmoqda..."
    }
}

# --- SESSION STATE ---
if 'original_plan' not in st.session_state: st.session_state.original_plan = None
if 'current_plan' not in st.session_state: st.session_state.current_plan = None
if 'current_language' not in st.session_state: st.session_state.current_language = "English"

# --- SIDEBAR ---
with st.sidebar:
    language = st.radio("Language Selection", ["English", "O`zbek", "Русский"])
lang = translations[language]

# --- UI CONTENT ---
st.title(lang["title"])
st.caption(lang["subtitle"])

with st.form("inputs"):
    col1, col2 = st.columns(2)
    with col1:
        sport = st.text_input(lang["sport"], placeholder=lang["sport_placeholder"])
        difficulty = st.select_slider(lang["skill_level"], lang["skill_levels"])
        duration = st.slider(lang["duration"], 1, 30, 7)
    with col2:
        disability = st.text_input(lang["disabilities"])
        equipment = st.text_input(lang["equipment"])
        culture = st.text_input(lang["culture"])
        diet = st.text_input(lang["diet"])
    generate_btn = st.form_submit_button(lang["generate_btn"], type="primary")

# --- STREAMING API HELPER ---
def call_llm_stream(prompt, container, retries=1, is_translation=False):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Athlan AI"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3 if is_translation else 0.7,
        "stream": True
    }
    
    full_response = ""
    progress_bar = st.progress(0)
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code == 429 and retries > 0:
            st.warning(lang["cooldown"])
            time.sleep(10)
            return call_llm_stream(prompt, container, retries - 1, is_translation)
            
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith("data: "):
                    data_str = line_text[6:]
                    if data_str == "[DONE]": break
                    try:
                        data_json = json.loads(data_str)
                        chunk = data_json['choices'][0]['delta'].get('content', '')
                        full_response += chunk
                        container.markdown(full_response + "▌")
                        
                        prog = min(len(full_response) / (duration * 500), 1.0)
                        progress_bar.progress(prog)
                    except: continue
        
        progress_bar.progress(1.0)
        time.sleep(0.5)
        progress_bar.empty()
        return full_response
    except Exception as e:
        st.error(f"Error: {str(e)}")
        progress_bar.empty()
        return None

# --- MAIN LOGIC ---
if generate_btn and sport:
    prompt = f"""{lang['prompt_instruction']}
    Create a {difficulty} level {duration}-day {sport} training plan for:
    - Disabilities: {disability if disability else "None"}
    - Cultural: {culture if culture else "None"}
    - Equipment: {equipment if equipment else "None"}
    - Diet: {diet if diet else "None"}
    Format in markdown. Include EVERY day (Day 1 to Day {duration})."""

    with st.container(border=True):
        st.subheader(lang["plan_title"].format(sport, difficulty))
        text_placeholder = st.empty()
        result = call_llm_stream(prompt, text_placeholder)
        
        if result:
            st.session_state.original_plan = result
            st.session_state.current_plan = result
            st.session_state.current_language = language
            text_placeholder.markdown(result)

# --- DISPLAY & ACTIONS ---
if st.session_state.current_plan:
    if not generate_btn:
        st.subheader(lang["plan_title"].format(sport if sport else "Sport", difficulty if difficulty else ""))
        st.markdown(st.session_state.current_plan)

    st.divider()
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        translate_options = [l for l in translations.keys() if l != st.session_state.current_language]
        target_lang = st.selectbox(lang["translate_btn"], translate_options)
        if st.button("Confirm Translation"):
            trans_prompt = f"Translate this plan to {target_lang}. Keep markdown formatting:\n\n{st.session_state.original_plan}"
            with st.container(border=True):
                trans_placeholder = st.empty()
                translated = call_llm_stream(trans_prompt, trans_placeholder, is_translation=True)
                if translated:
                    st.session_state.current_plan = translated
                    st.session_state.current_language = target_lang
                    st.rerun()

    with col_b:
        st.download_button(
            label=lang["save_btn"],
            data=st.session_state.current_plan,
            file_name=f"athlan_plan_{st.session_state.current_language}.txt",
            mime="text/plain"
        )
