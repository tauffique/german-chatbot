import streamlit as st
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS
import os
import tempfile
import base64
import json
from datetime import datetime, timedelta
import pandas as pd
import re
import random
import time
from deep_translator import GoogleTranslator
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="🇩🇪 Advanced German Learning Assistant", 
    page_icon="🇩🇪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .achievement-badge {
        background: #FFD93D;
        color: #333;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        margin: 2px;
        display: inline-block;
    }
    .streak-counter {
        background: #FF6B6B;
        color: white;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
    }
    .vocabulary-card {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 5px;
        border-left: 4px solid #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize OpenAI client
@st.cache_resource
def get_clients():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    return client

client = get_clients()

# Gamification functions (MUST be defined before initialize_session_state)
def generate_daily_challenges():
    challenges = [
        {"name": "Vocabulary Master", "description": "Learn 5 new words", "target": 5, "progress": 0, "points": 50},
        {"name": "Conversation Starter", "description": "Send 10 messages", "target": 10, "progress": 0, "points": 30},
        {"name": "Grammar Guru", "description": "Complete 3 grammar exercises", "target": 3, "progress": 0, "points": 40},
        {"name": "Translation Expert", "description": "Use translation 5 times", "target": 5, "progress": 0, "points": 35}
    ]
    return challenges

def update_daily_streak():
    today = datetime.now().strftime("%Y-%m-%d")
    last_activity = st.session_state.stats["last_activity"]
    
    if last_activity != today:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_activity == yesterday:
            st.session_state.stats["daily_streak"] += 1
        else:
            st.session_state.stats["daily_streak"] = 1
        st.session_state.stats["last_activity"] = today

def add_achievement(achievement_name):
    if achievement_name not in st.session_state.stats["achievements"]:
        st.session_state.stats["achievements"].append(achievement_name)
        st.success(f"🏆 Achievement Unlocked: {achievement_name}!")
        st.balloons()

def update_level():
    points = st.session_state.stats["total_points"]
    new_level = min(10, (points // 100) + 1)
    if new_level > st.session_state.stats["level"]:
        st.session_state.stats["level"] = new_level
        add_achievement(f"Level {new_level} Reached!")

# Initialize session state with gamification
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "stats" not in st.session_state:
        st.session_state.stats = {
            "messages_sent": 0,
            "words_learned": [],
            "session_time": 0,
            "corrections_made": 0,
            "pronunciation_score": 0,
            "grammar_exercises_completed": 0,
            "daily_streak": 0,
            "total_points": 0,
            "level": 1,
            "achievements": [],
            "last_activity": datetime.now().strftime("%Y-%m-%d")
        }
    
    if "vocabulary" not in st.session_state:
        st.session_state.vocabulary = []
    
    if "show_quiz" not in st.session_state:
        st.session_state.show_quiz = False
    
    if "daily_challenges" not in st.session_state:
        st.session_state.daily_challenges = generate_daily_challenges()
    
    if "session_start_time" not in st.session_state:
        st.session_state.session_start_time = time.time()
    
    if "interface_language" not in st.session_state:
        st.session_state.interface_language = "English"
    
    # Update daily streak
    update_daily_streak()

initialize_session_state()

# Translation functions using deep-translator
def translate_text(text, target_lang='en'):
    try:
        if target_lang == 'en':
            result = GoogleTranslator(source='auto', target='en').translate(text)
        else:
            result = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return result
    except:
        return text

def get_interface_text(key, lang="English"):
    translations = {
        "English": {
            "title": "🇩🇪 Advanced German Learning Assistant",
            "subtitle": "Master German with AI-powered conversation, gamification, and advanced learning tools",
            "settings": "Settings",
            "progress": "Your Progress",
            "daily_challenges": "Daily Challenges",
            "vocabulary": "Vocabulary",
            "achievements": "Achievements",
            "level": "Level",
            "points": "Points",
            "streak": "Day Streak"
        },
        "Deutsch": {
            "title": "🇩🇪 Fortgeschrittener Deutscher Lernassistent",
            "subtitle": "Meistere Deutsch mit KI-gestützter Konversation, Gamification und fortgeschrittenen Lernwerkzeugen",
            "settings": "Einstellungen",
            "progress": "Dein Fortschritt",
            "daily_challenges": "Tägliche Herausforderungen",
            "vocabulary": "Wortschatz",
            "achievements": "Erfolge",
            "level": "Stufe",
            "points": "Punkte",
            "streak": "Tage Strähne"
        }
    }
    return translations.get(lang, translations["English"]).get(key, key)

# Advanced sidebar with all features
with st.sidebar:
    # Language switcher
    st.session_state.interface_language = st.selectbox(
        "🌐 Interface Language / Oberflächensprache",
        ["English", "Deutsch"],
        index=0 if st.session_state.interface_language == "English" else 1
    )
    
    lang = st.session_state.interface_language
    
    st.title(f"🛠️ {get_interface_text('settings', lang)}")
    
    # Basic learning settings
    difficulty = st.selectbox(
        "Difficulty Level / Schwierigkeitsgrad",
        ["Beginner", "Intermediate", "Advanced"],
        index=1
    )
    
    topics = [
        "Free conversation", "Daily activities", "Food and cooking",
        "Travel and culture", "Work and career", "Hobbies and interests",
        "Grammar practice", "Pronunciation training", "German culture"
    ]
    selected_topic = st.selectbox("Conversation Topic / Gesprächsthema", topics)
    
    # Advanced language settings
    st.subheader("🌐 Language Settings / Spracheinstellungen")
    input_language = st.selectbox(
        "Input Language / Eingabesprache",
        ["Both (English & German)", "German only", "English only"],
        index=0
    )
    show_translation = st.checkbox("Show translations / Übersetzungen zeigen", value=True)
    grammar_correction_mode = st.selectbox(
        "Grammar Correction / Grammatikkorrektur",
        ["Gentle corrections", "Detailed explanations", "Practice exercises"],
        index=0
    )
    
    # Voice settings
    st.subheader("🎤 Audio Settings / Audio-Einstellungen")
    conversation_mode = st.radio(
        "Conversation Mode / Unterhaltungsmodus",
        ["Text with Audio Response", "Text Only"],
        index=0
    )
    auto_speak = st.checkbox("Auto-speak responses / Automatische Sprachausgabe", value=True)
    voice_speed = st.slider("Speech speed / Sprechgeschwindigkeit", 0.5, 2.0, 1.0, 0.1)
    
    # Gamification settings
    st.subheader("🎮 Gamification")
    enable_achievements = st.checkbox("Enable achievements / Erfolge aktivieren", value=True)
    enable_daily_challenges = st.checkbox("Daily challenges / Tägliche Herausforderungen", value=True)
    show_progress_analytics = st.checkbox("Progress analytics / Fortschrittsanalyse", value=True)
    
    # Progress display
    st.subheader(f"📊 {get_interface_text('progress', lang)}")
    
    # Level and points
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='streak-counter'>{get_interface_text('level', lang)} {st.session_state.stats['level']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='streak-counter'>{st.session_state.stats['total_points']} {get_interface_text('points', lang)}</div>", unsafe_allow_html=True)
    
    # Streak counter
    st.markdown(f"<div class='streak-counter'>🔥 {st.session_state.stats['daily_streak']} {get_interface_text('streak', lang)}</div>", unsafe_allow_html=True)
    
    # Quick stats
    st.metric("Messages", st.session_state.stats["messages_sent"])
    st.metric("Words learned", len(st.session_state.stats["words_learned"]))
    st.metric("Corrections", st.session_state.stats["corrections_made"])

# Main header
st.markdown(f"""
<div class='main-header'>
    <h1>{get_interface_text('title', lang)}</h1>
    <p>{get_interface_text('subtitle', lang)}</p>
</div>
""", unsafe_allow_html=True)

# Enhanced system prompt with cultural context
def get_enhanced_system_prompt(difficulty, selected_topic, input_language, show_translation, grammar_mode):
    difficulty_prompts = {
        "Beginner": "Du bist ein sehr geduldiger deutscher Lehrer. Verwende einfache Wörter und kurze Sätze.",
        "Intermediate": "Du bist ein freundlicher deutscher Muttersprachler. Verwende mittelschwere Sprache.",
        "Advanced": "Du bist ein gebildeter deutscher Muttersprachler. Verwende natürliche, komplexe Sprache."
    }
    
    # Cultural context based on topic
    cultural_context = ""
    if selected_topic == "German culture":
        cultural_context = " Teile interessante Fakten über deutsche Kultur, Traditionen und Geschichte."
    elif selected_topic == "Food and cooking":
        cultural_context = " Erwähne traditionelle deutsche Gerichte und Essgewohnheiten."
    elif selected_topic == "Travel and culture":
        cultural_context = " Beschreibe deutsche Städte, Sehenswürdigkeiten und Reisetipps."
    
    grammar_instructions = {
        "Gentle corrections": "Korrigiere Fehler sanft und kurz.",
        "Detailed explanations": "Erkläre Grammatikfehler ausführlich mit Beispielen.",
        "Practice exercises": "Gib nach Korrekturen kleine Übungen zum Üben."
    }
    
    language_instruction = ""
    if input_language == "Both (English & German)":
        language_instruction = "Akzeptiere Eingaben auf Englisch oder Deutsch. Antworte immer auf Deutsch."
        if show_translation:
            language_instruction += " Zeige Übersetzungen für schwierige Begriffe."
    elif input_language == "English only":
        language_instruction = "Der Nutzer spricht nur Englisch. Antworte auf Deutsch mit englischen Erklärungen."
    else:
        language_instruction = "Der Nutzer spricht Deutsch. Antworte nur auf Deutsch."
    
    topic_context = f" Das Gesprächsthema ist: {selected_topic}." if selected_topic != "Free conversation" else ""
    
    return f"""{difficulty_prompts[difficulty]} {language_instruction} {grammar_instructions[grammar_mode]} {topic_context} {cultural_context}
    
    Markiere neue Vokabeln mit [VOCAB: deutsches_wort - english_translation].
    Verwende manchmal deutsche Redewendungen und erkläre sie.
    Stelle interessante Folgefragen um das Gespräch lebendig zu halten.
    Sei ermutigend und positiv beim Korrigieren.
    Erwähne gelegentlich deutsche Kultur und Traditionen.
    """

# Enhanced vocabulary extraction with gamification
def extract_vocabulary_enhanced(text):
    vocab_pattern = r'\[VOCAB: ([^-]+) - ([^\]]+)\]'
    matches = re.findall(vocab_pattern, text)
    new_words_learned = 0
    
    for german, english in matches:
        vocab_entry = {
            "german": german.strip(),
            "english": english.strip(),
            "date_learned": datetime.now().strftime("%Y-%m-%d"),
            "difficulty": difficulty,
            "topic": selected_topic,
            "times_seen": 1,
            "mastery_level": "Learning"
        }
        
        existing_word = next((v for v in st.session_state.vocabulary if v["german"] == vocab_entry["german"]), None)
        if existing_word:
            existing_word["times_seen"] += 1
            if existing_word["times_seen"] >= 3:
                existing_word["mastery_level"] = "Mastered"
        else:
            st.session_state.vocabulary.append(vocab_entry)
            if vocab_entry["german"] not in st.session_state.stats["words_learned"]:
                st.session_state.stats["words_learned"].append(vocab_entry["german"])
                new_words_learned += 1
                st.session_state.stats["total_points"] += 10
    
    # Update daily challenges
    if new_words_learned > 0 and enable_daily_challenges:
        st.session_state.daily_challenges[0]["progress"] += new_words_learned
    
    return re.sub(vocab_pattern, r'\1', text)

# Enhanced chat function with OpenAI Whisper integration
@st.cache_data
def chat_with_gpt_enhanced(user_input, messages_context, system_prompt):
    try:
        full_messages = [{"role": "system", "content": system_prompt}] + messages_context + [{"role": "user", "content": user_input}]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
            temperature=0.7,
            max_tokens=400,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error communicating with OpenAI: {str(e)}")
        return "Entschuldigung, es gab einen Fehler. Bitte versuchen Sie es erneut."

# Simplified voice input - Text input with audio output only
def simplified_voice_input():
    st.markdown("### 💬 Text Input with Audio Response")
    st.info("🎤 Voice recording disabled - Using text input with audio feedback")
    return None

# Enhanced conversation processing with gamification
def process_enhanced_conversation(user_input):
    system_prompt = get_enhanced_system_prompt(
        difficulty, selected_topic, input_language, 
        show_translation, grammar_correction_mode
    )
    
    reply = chat_with_gpt_enhanced(user_input, st.session_state.messages, system_prompt)
    
    # Update conversation history
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": reply})
    
    # Enhanced statistics tracking with gamification
    st.session_state.stats["messages_sent"] += 1
    st.session_state.stats["total_points"] += 5
    
    # Update daily challenges
    if enable_daily_challenges:
        st.session_state.daily_challenges[1]["progress"] += 1
    
    # Grammar correction tracking
    if any(word in reply.lower() for word in ["korrektur", "fehler", "richtig", "falsch"]):
        st.session_state.stats["corrections_made"] += 1
        st.session_state.stats["total_points"] += 15
    
    # Grammar exercise tracking
    if "übung" in reply.lower() or "exercise" in reply.lower():
        st.session_state.stats["grammar_exercises_completed"] += 1
        st.session_state.stats["total_points"] += 20
        if enable_daily_challenges:
            st.session_state.daily_challenges[2]["progress"] += 1
    
    # Check for achievements
    if enable_achievements:
        check_achievements()
    
    # Update level
    update_level()
    
    return reply

def check_achievements():
    stats = st.session_state.stats
    
    if stats["messages_sent"] >= 10:
        add_achievement("Chatterbox")
    if len(stats["words_learned"]) >= 50:
        add_achievement("Vocabulary Collector")
    if stats["daily_streak"] >= 7:
        add_achievement("Week Warrior")
    if stats["grammar_exercises_completed"] >= 10:
        add_achievement("Grammar Master")
    if stats["total_points"] >= 500:
        add_achievement("Point Collector")

# Enhanced text-to-speech
def enhanced_speak_text(text, speed=1.0, lang='de'):
    try:
        clean_text = extract_vocabulary_enhanced(text)
        clean_text = re.sub(r'\*\*|__|~~|\[|\]|\(|\)', '', clean_text)
        
        tts = gTTS(clean_text, lang=lang, slow=(speed < 1.0))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            with open(tmp.name, 'rb') as audio_file:
                audio_bytes = audio_file.read()
            os.unlink(tmp.name)
        
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
        <audio controls autoplay style="width: 100%;">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Text-to-speech error: {str(e)}")

# Main interface with tabs
tab1, tab2, tab3, tab4 = st.tabs(["💬 Conversation", "📚 Vocabulary", "🏆 Achievements", "📊 Analytics"])

with tab1:
    # Conversation interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Simplified text input interface
        placeholder_text = {
            "Both (English & German)": "Type in German or English... / Schreibe auf Deutsch oder Englisch...",
            "German only": "Schreibe auf Deutsch...",
            "English only": "Type in English..."
        }
        
        user_input = st.text_area(
            placeholder_text[input_language], 
            height=100, 
            key="text_input",
            help="Type your message and press Send"
        )
        
        # Simplified button layout
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            submit_btn = st.button("📤 Send", use_container_width=True, type="primary")
        
        with btn_col2:
            translate_btn = st.button("🔄 Translate", use_container_width=True)
        
        with btn_col3:
            clear_btn = st.button("🗑️ Clear", use_container_width=True)
        
        # Handle interactions
        if submit_btn and user_input.strip():
            with st.spinner("🤖 GPT is thinking..."):
                reply = process_enhanced_conversation(user_input.strip())
                clean_reply = extract_vocabulary_enhanced(reply)
                
                st.success(f"**GPT:** {clean_reply}")
                
                if conversation_mode == "Text with Audio Response" and auto_speak:
                    enhanced_speak_text(reply, voice_speed)
        
        if translate_btn and user_input.strip():
            if any(char in user_input for char in "äöüß"):
                translation = translate_text(user_input, 'en')
                st.info(f"🇺🇸 **English:** {translation}")
            else:
                translation = translate_text(user_input, 'de')
                st.info(f"🇩🇪 **Deutsch:** {translation}")
            
            # Update translation challenge
            if enable_daily_challenges:
                st.session_state.daily_challenges[3]["progress"] += 1
        
        if clear_btn:
            st.session_state.messages = []
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        # Daily challenges
        if enable_daily_challenges:
            st.markdown("### 🎯 Daily Challenges")
            for i, challenge in enumerate(st.session_state.daily_challenges):
                progress = min(challenge["progress"], challenge["target"])
                completion = progress / challenge["target"]
                
                st.markdown(f"**{challenge['name']}**")
                st.progress(completion)
                st.markdown(f"{progress}/{challenge['target']} - {challenge['points']} points")
                
                if progress >= challenge["target"]:
                    st.success("✅ Completed!")
                st.markdown("---")
        
        # Quick tools
        st.markdown("### ⚡ Quick Tools")
        
        if st.button("📝 Grammar Exercise", use_container_width=True):
            grammar_exercises = [
                "Bilde einen Satz mit dem Dativ.",
                "Konjugiere das Verb 'sprechen' im Präsens.",
                "Erkläre den Unterschied zwischen 'der', 'die', 'das'.",
                "Verwende eine Präposition mit dem Akkusativ.",
                "Bilde den Plural von 'das Kind'."
            ]
            exercise = random.choice(grammar_exercises)
            reply = process_enhanced_conversation(f"Grammatikübung: {exercise}")
            st.info(reply)
        
        if st.button("🎲 Random Topic", use_container_width=True):
            topics = ["Wetter", "Familie", "Hobbys", "Reisen", "Essen", "Musik", "Sport"]
            topic = random.choice(topics)
            reply = process_enhanced_conversation(f"Lass uns über {topic} sprechen.")
            st.info(reply)
        
        if st.button("📚 Vocabulary Quiz", use_container_width=True):
            if len(st.session_state.vocabulary) >= 3:
                quiz_word = random.choice(st.session_state.vocabulary)
                st.session_state.quiz_word = quiz_word
                st.session_state.show_quiz = True
                st.rerun()
    
    # Conversation history
    if st.session_state.messages:
        st.markdown("### 💬 Recent Conversation")
        for i, msg in enumerate(st.session_state.messages[-6:]):  # Show last 6 messages
            role = "🧑 You" if msg["role"] == "user" else "🤖 GPT"
            content = extract_vocabulary_enhanced(msg["content"]) if msg["role"] == "assistant" else msg["content"]
            
            with st.expander(f"{role}: {content[:50]}..."):
                st.markdown(content)
                if msg["role"] == "assistant":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"🔊 Listen", key=f"speak_{i}"):
                            enhanced_speak_text(content, voice_speed)
                    with col2:
                        if st.button(f"🔄 Translate", key=f"translate_{i}"):
                            translation = translate_text(content, 'en')
                            st.info(f"**English:** {translation}")

with tab2:
    # Enhanced vocabulary section
    st.markdown("### 📚 Enhanced Vocabulary Manager")
    
    if st.session_state.vocabulary:
        # Vocabulary statistics
        vocab_df = pd.DataFrame(st.session_state.vocabulary)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            difficulty_filter = st.selectbox("Filter by difficulty", ["All"] + ["Beginner", "Intermediate", "Advanced"])
        with col2:
            topic_filter = st.selectbox("Filter by topic", ["All"] + topics)
        with col3:
            mastery_filter = st.selectbox("Filter by mastery", ["All", "Learning", "Mastered"])
        
        # Apply filters
        filtered_vocab = st.session_state.vocabulary
        if difficulty_filter != "All":
            filtered_vocab = [v for v in filtered_vocab if v.get("difficulty") == difficulty_filter]
        if topic_filter != "All":
            filtered_vocab = [v for v in filtered_vocab if v.get("topic") == topic_filter]
        if mastery_filter != "All":
            filtered_vocab = [v for v in filtered_vocab if v.get("mastery_level") == mastery_filter]
        
        if filtered_vocab:
            # Display vocabulary cards
            for vocab in filtered_vocab[:10]:
                mastery_color = "🟢" if vocab.get("mastery_level") == "Mastered" else "🟡"
                st.markdown(f"""
                <div class='vocabulary-card'>
                    <strong>{mastery_color} {vocab['german']}</strong> - {vocab['english']}<br>
                    <small>Topic: {vocab.get('topic', 'N/A')} | Seen: {vocab.get('times_seen', 1)} times | Date: {vocab['date_learned']}</small>
                </div>
                """, unsafe_allow_html=True)
            
            # Vocabulary analytics
            if show_progress_analytics:
                st.markdown("### 📊 Vocabulary Analytics")
                
                # Vocabulary growth chart
                dates = [v['date_learned'] for v in st.session_state.vocabulary]
                date_counts = {}
                for date in dates:
                    date_counts[date] = date_counts.get(date, 0) + 1
                
                if date_counts:
                    fig = px.bar(
                        x=list(date_counts.keys()), 
                        y=list(date_counts.values()),
                        title="Vocabulary Learning Progress",
                        labels={"x": "Date", "y": "Words Learned"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Mastery level pie chart
                mastery_counts = {}
                for vocab in st.session_state.vocabulary:
                    mastery = vocab.get("mastery_level", "Learning")
                    mastery_counts[mastery] = mastery_counts.get(mastery, 0) + 1
                
                if mastery_counts:
                    fig = px.pie(
                        values=list(mastery_counts.values()),
                        names=list(mastery_counts.keys()),
                        title="Vocabulary Mastery Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Enhanced quiz section
        if st.session_state.show_quiz and hasattr(st.session_state, 'quiz_word'):
            st.markdown("### 🎯 Enhanced Vocabulary Quiz")
            quiz_word = st.session_state.quiz_word
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**What does '{quiz_word['german']}' mean in English?**")
                
                # Multiple choice quiz
                correct_answer = quiz_word['english']
                wrong_answers = [v['english'] for v in st.session_state.vocabulary if v['english'] != correct_answer]
                if len(wrong_answers) >= 3:
                    choices = [correct_answer] + random.sample(wrong_answers, 3)
                    random.shuffle(choices)
                    
                    user_choice = st.radio("Choose the correct answer:", choices, key="quiz_choice")
                    
                    if st.button("Check Answer"):
                        if user_choice == correct_answer:
                            st.success("🎉 Correct! Well done!")
                            st.session_state.stats["total_points"] += 25
                            st.balloons()
                        else:
                            st.error(f"❌ Not quite. The correct answer is: **{correct_answer}**")
                            st.session_state.stats["total_points"] += 5  # Consolation points
                else:
                    # Fallback to text input
                    user_answer = st.text_input("Your answer:", key="quiz_answer")
                    if st.button("Check Answer"):
                        if user_answer.lower().strip() == correct_answer.lower().strip():
                            st.success("🎉 Correct! Well done!")
                            st.session_state.stats["total_points"] += 25
                            st.balloons()
                        else:
                            st.error(f"❌ Not quite. The correct answer is: **{correct_answer}**")
            
            with col2:
                if st.button("🔊 Pronounce German"):
                    enhanced_speak_text(quiz_word['german'], voice_speed)
                
                if st.button("🔊 Pronounce English"):
                    enhanced_speak_text(quiz_word['english'], voice_speed, 'en')
                
                st.markdown(f"**Topic:** {quiz_word.get('topic', 'N/A')}")
                st.markdown(f"**Difficulty:** {quiz_word.get('difficulty', 'N/A')}")
                
                if st.button("End Quiz"):
                    st.session_state.show_quiz = False
                    if 'quiz_word' in st.session_state:
                        del st.session_state.quiz_word
                    st.rerun()
    
    else:
        st.info("Start conversations to build your vocabulary! 📚")

with tab3:
    # Achievements and gamification
    st.markdown("### 🏆 Achievements & Rewards")
    
    # Level progress
    current_level = st.session_state.stats["level"]
    current_points = st.session_state.stats["total_points"]
    points_for_next_level = (current_level * 100) - current_points
    level_progress = (current_points % 100) / 100
    
    st.markdown(f"**Level {current_level}** 🎯")
    st.progress(level_progress)
    if points_for_next_level > 0:
        st.markdown(f"*{points_for_next_level} points needed for Level {current_level + 1}*")
    
    # Achievements grid
    st.markdown("### 🏅 Unlocked Achievements")
    if st.session_state.stats["achievements"]:
        achievement_cols = st.columns(3)
        for i, achievement in enumerate(st.session_state.stats["achievements"]):
            with achievement_cols[i % 3]:
                st.markdown(f"""
                <div class='achievement-badge'>
                    🏆 {achievement}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Complete challenges to unlock achievements!")
    
    # Available achievements
    st.markdown("### 🔒 Available Achievements")
    available_achievements = [
        {"name": "Chatterbox", "description": "Send 10 messages", "requirement": "10 messages"},
        {"name": "Vocabulary Collector", "description": "Learn 50 words", "requirement": "50 words"},
        {"name": "Week Warrior", "description": "7-day streak", "requirement": "7 days"},
        {"name": "Grammar Master", "description": "Complete 10 grammar exercises", "requirement": "10 exercises"},
        {"name": "Point Collector", "description": "Earn 500 points", "requirement": "500 points"},
    ]
    
    for achievement in available_achievements:
        if achievement["name"] not in st.session_state.stats["achievements"]:
            st.markdown(f"🔒 **{achievement['name']}** - {achievement['description']} (*{achievement['requirement']}*)")
    
    # Daily challenges progress
    if enable_daily_challenges:
        st.markdown("### 🎯 Today's Challenges")
        total_possible_points = sum(c["points"] for c in st.session_state.daily_challenges)
        total_earned_points = sum(c["points"] for c in st.session_state.daily_challenges if c["progress"] >= c["target"])
        
        st.markdown(f"**Daily Progress: {total_earned_points}/{total_possible_points} points**")
        
        for challenge in st.session_state.daily_challenges:
            progress = min(challenge["progress"], challenge["target"])
            completion = progress / challenge["target"]
            status = "✅" if progress >= challenge["target"] else "🔄"
            
            st.markdown(f"{status} **{challenge['name']}**")
            st.progress(completion)
            st.markdown(f"*{challenge['description']} ({progress}/{challenge['target']}) - {challenge['points']} points*")

with tab4:
    # Analytics dashboard
    st.markdown("### 📊 Learning Analytics Dashboard")
    
    if show_progress_analytics and st.session_state.messages:
        # Overall statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Messages", 
                st.session_state.stats["messages_sent"],
                delta=1 if st.session_state.stats["messages_sent"] > 0 else 0
            )
        
        with col2:
            st.metric(
                "Vocabulary Size", 
                len(st.session_state.vocabulary),
                delta=len([v for v in st.session_state.vocabulary if v['date_learned'] == datetime.now().strftime("%Y-%m-%d")])
            )
        
        with col3:
            st.metric(
                "Current Streak", 
                st.session_state.stats["daily_streak"],
                delta=1 if st.session_state.stats["daily_streak"] > 0 else 0
            )
        
        with col4:
            st.metric(
                "Total Points", 
                st.session_state.stats["total_points"],
                delta=5
            )
        
        # Learning patterns
        st.markdown("### 📈 Learning Patterns")
        
        # Message activity over time (simulated for demo)
        if st.session_state.messages:
            dates = []
            message_counts = []
            
            # Simulate daily activity for the past week
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                count = random.randint(0, 10) if i > 0 else st.session_state.stats["messages_sent"]
                dates.append(date)
                message_counts.append(count)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, 
                y=message_counts,
                mode='lines+markers',
                name='Daily Messages',
                line=dict(color='#FF6B6B', width=3)
            ))
            fig.update_layout(
                title="Message Activity (Last 7 Days)",
                xaxis_title="Date",
                yaxis_title="Messages",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Topic distribution
        if st.session_state.vocabulary:
            topic_counts = {}
            for vocab in st.session_state.vocabulary:
                topic = vocab.get('topic', 'Unknown')
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            if topic_counts:
                fig = px.bar(
                    x=list(topic_counts.keys()),
                    y=list(topic_counts.values()),
                    title="Vocabulary by Topic",
                    color=list(topic_counts.values()),
                    color_continuous_scale="Viridis"
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # Learning insights
        st.markdown("### 💡 Learning Insights")
        
        insights = []
        
        if len(st.session_state.vocabulary) > 0:
            avg_words_per_day = len(st.session_state.vocabulary) / max(1, st.session_state.stats["daily_streak"])
            insights.append(f"📚 You learn an average of {avg_words_per_day:.1f} words per day")
        
        if st.session_state.stats["corrections_made"] > 0:
            correction_rate = st.session_state.stats["corrections_made"] / max(1, st.session_state.stats["messages_sent"])
            insights.append(f"✏️ Grammar correction rate: {correction_rate:.1%}")
        
        if st.session_state.stats["daily_streak"] >= 3:
            insights.append("🔥 Great consistency! Keep up your learning streak!")
        
        if st.session_state.stats["level"] >= 3:
            insights.append("🌟 You're making excellent progress!")
        
        most_common_topic = None
        if st.session_state.vocabulary:
            topic_counts = {}
            for vocab in st.session_state.vocabulary:
                topic = vocab.get('topic', 'Unknown')
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if topic_counts:
                most_common_topic = max(topic_counts, key=topic_counts.get)
                insights.append(f"🎯 Your favorite topic: {most_common_topic}")
        
        for insight in insights:
            st.info(insight)
    
    else:
        st.info("Start learning to see your analytics! 📊")

# Data export and import
st.markdown("### 💾 Data Management")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Export All Data", use_container_width=True):
        export_data = {
            "messages": st.session_state.messages,
            "vocabulary": st.session_state.vocabulary,
            "stats": st.session_state.stats,
            "daily_challenges": st.session_state.daily_challenges,
            "settings": {
                "difficulty": difficulty,
                "topic": selected_topic,
                "input_language": input_language,
                "interface_language": st.session_state.interface_language
            },
            "export_date": datetime.now().isoformat(),
            "version": "2.0"
        }
        
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download Complete Data",
            data=json_data,
            file_name=f"german_learning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

with col2:
    uploaded_file = st.file_uploader("📤 Import Learning Data", type=['json'])
    if uploaded_file is not None:
        try:
            import_data = json.load(uploaded_file)
            
            # Import data with validation
            if "messages" in import_data:
                st.session_state.messages = import_data["messages"]
            if "vocabulary" in import_data:
                st.session_state.vocabulary = import_data["vocabulary"]
            if "stats" in import_data:
                st.session_state.stats.update(import_data["stats"])
            if "daily_challenges" in import_data:
                st.session_state.daily_challenges = import_data["daily_challenges"]
            
            st.success("✅ Data imported successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error importing data: {str(e)}")

# Footer with tips
st.markdown("---")
with st.expander("💡 Tips for Better Learning"):
    st.markdown("""
    **🚀 Pro Tips for Maximum Learning:**
    
    **Voice Features:**
    - Use a quiet environment for better voice recognition
    - Speak clearly and at moderate pace
    - Try both English and German voice input
    
    **Gamification:**
    - Complete daily challenges for bonus points
    - Maintain your streak for better rewards
    - Unlock achievements by exploring different features
    
    **Learning Strategy:**
    - Review vocabulary cards regularly
    - Practice grammar exercises daily
    - Use translation features to understand context
    - Explore different conversation topics
    
    **Advanced Features:**
    - Export your data to track long-term progress
    - Use analytics to identify learning patterns
    - Set daily goals and monitor your improvement
    - Practice pronunciation with text-to-speech
    
    **Cultural Learning:**
    - Ask about German traditions and customs
    - Learn common German expressions and idioms
    - Practice real-world conversation scenarios
    """)

# Auto-save progress (runs in background)
if st.session_state.stats["messages_sent"] % 5 == 0 and st.session_state.stats["messages_sent"] > 0:
    # Auto-save logic could be implemented here
    pass
