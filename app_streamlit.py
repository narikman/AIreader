#!/usr/bin/env python3
"""

import streamlit as st
import os
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup

try:
    from openai import OpenAI
except ImportError:
    st.error(" OpenAI package required. Install: pip install openai")
    sys.exit(1)

# Page configuration
st.set_page_config(
    page_title="AI Website Reader",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Main background and text */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* Card styling */
    [data-testid="stVerticalBlock"] {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #667eea;
        font-weight: 700;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 2px solid #667eea !important;
        background: #f8f9fa;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        background: rgba(102, 126, 234, 0.2);
        color: #667eea;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-left: 4px solid #667eea;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Success messages */
    .stSuccess {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 10px;
    }
    
    /* Error messages */
    .stError {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 10px;
    }
    
    /* Spinners and loading */
    .stSpinner {
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = []

# Header with gradient
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("#AI Website Reader")
    st.markdown("*Умный ИИ анализатор сайтов*")
with col2:
    st.markdown("### 🌐 v2.0")

st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.markdown("## ⚙️ Настройки")
    
    # API Key
    api_key = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        value=os.getenv('OPENAI_API_KEY', '')
    )
    
    st.markdown("---")
    
    # Settings
    st.markdown("###  Параметры")
    use_javascript = st.checkbox(" Рендеринг JavaScript", value=True)
    use_tts = st.checkbox(" Текст в речь (TTS)", value=False)
    
    st.markdown("---")
    
    # Model selection
    model = st.selectbox(
        " Модель ИИ",
        ["gpt-3.5-turbo", "gpt-4"],
        help="Выберите модель для анализа"
    )
    
    # Summary length
    max_length = st.slider(
        " Длина резюме (символы)",
        min_value=200,
        max_value=1000,
        value=500,
        step=50
    )

# Main content area
if not api_key:
    st.warning("⚠️ Пожалуйста, введите OpenAI API Key в боковой панели")
else:
    try:
        client = OpenAI(api_key=api_key)
        
        # Tab interface
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            " Резюме", 
            " Анализ", 
            " Извлечение текста",
            " История",
            " Справка"
        ])
        
        # Helper class
        class AIReader:
            def __init__(self, client):
                self.client = client
                self.headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            
            def fetch_website(self, url):
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                return response.text
            
            def extract_text(self, html_content):
                soup = BeautifulSoup(html_content, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text
            
            def get_title(self, html_content):
                soup = BeautifulSoup(html_content, 'html.parser')
                title = soup.find('title')
                return title.string if title else "Неизвестный сайт"
            
            def summarize(self, content, max_length):
                content = content[:4000]
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Вы полезный помощник, который кратко и точно резюмирует содержимое веб-сайтов на русском языке."
                        },
                        {
                            "role": "user",
                            "content": f"Пожалуйста, резюмируйте следующее содержимое в {max_length} символов или меньше:\n\n{content}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                return response.choices[0].message.content
            
            def analyze(self, content, query):
                content = content[:4000]
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Вы полезный помощник, который отвечает на вопросы о содержимом веб-сайтов. Отвечайте на русском языке."
                        },
                        {
                            "role": "user",
                            "content": f"На основе следующего содержимого веб-сайта ответьте на этот вопрос: {query}\n\nСодержимое:\n{content}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=400
                )
                return response.choices[0].message.content
            
            def text_to_speech(self, text, filename):
                tts_text = text[:3000]
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=tts_text
                )
                audio_path = f"{filename.replace(' ', '_')}_audio.mp3"
                response.stream_to_file(audio_path)
                return audio_path
        
        reader = AIReader(client)
        
        # TAB 1: SUMMARIZE
        with tab1:
            st.markdown("### 📋 Резюмирование сайта")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                url = st.text_input(
                    "Введите URL сайта",
                    placeholder="https://example.com",
                    key="url_summarize"
                )
            with col2:
                summarize_btn = st.button(" Анализировать", key="btn_summarize", use_container_width=True)
            
            if summarize_btn and url:
                if not url.startswith('http'):
                    url = 'https://' + url
                
                try:
                    with st.spinner("🔄 Загружаю сайт..."):
                        html = reader.fetch_website(url)
                        title = reader.get_title(html)
                        text = reader.extract_text(html)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 Длина текста", f"{len(text)} символов")
                    with col2:
                        st.metric("⏱️ Время", datetime.now().strftime("%H:%M:%S"))
                    with col3:
                        st.metric("✅ Статус", "Успешно")
                    
                    st.markdown("---")
                    
                    st.subheader(f"📄 {title}")
                    
                    with st.spinner("ИИ анализирует содержимое..."):
                        summary = reader.summarize(text, max_length)
                    
                    st.success("✅ Резюме готово!")
                    st.markdown(f"""
                    <div class='info-box'>
                    {summary}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if use_tts:
                        with st.spinner("🔊 Генерирую аудио..."):
                            audio_file = reader.text_to_speech(summary, title)
                            st.audio(audio_file)
                    
                    # Save to history
                    st.session_state.results.append({
                        "url": url,
                        "title": title,
                        "type": "Резюме",
                        "result": summary,
                        "time": datetime.now()
                    })
                    
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
        
        # TAB 2: ANALYZE
        with tab2:
            st.markdown("### ❓ Анализ с вопросом")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                url = st.text_input(
                    "Введите URL сайта",
                    placeholder="https://example.com",
                    key="url_analyze"
                )
            with col2:
                st.write("")  # spacing
            
            query = st.text_area(
                "Задайте вопрос о содержимом сайта",
                placeholder="Например: Какие основные преимущества компании?",
                height=80,
                key="query"
            )
            
            analyze_btn = st.button("🔍 Проанализировать", key="btn_analyze", use_container_width=True)
            
            if analyze_btn and url and query:
                if not url.startswith('http'):
                    url = 'https://' + url
                
                try:
                    with st.spinner("🔄 Загружаю сайт..."):
                        html = reader.fetch_website(url)
                        title = reader.get_title(html)
                        text = reader.extract_text(html)
                    
                    st.info(f"📄 **{title}**")
                    
                    with st.spinner("ИИ отвечает на вопрос..."):
                        analysis = reader.analyze(text, query)
                    
                    st.success("✅ Анализ завершен!")
                    st.markdown(f"""
                    <div class='info-box'>
                    <strong>❓ Вопрос:</strong> {query}<br><br>
                    <strong>📝 Ответ:</strong><br>{analysis}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if use_tts:
                        with st.spinner("🔊 Генерирую аудио..."):
                            audio_file = reader.text_to_speech(analysis, title)
                            st.audio(audio_file)
                    
                    st.session_state.results.append({
                        "url": url,
                        "title": title,
                        "type": "Анализ",
                        "query": query,
                        "result": analysis,
                        "time": datetime.now()
                    })
                    
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
        
        # TAB 3: EXTRACT TEXT
        with tab3:
            st.markdown("###  Извлечение текста")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                url = st.text_input(
                    "Введите URL сайта",
                    placeholder="https://example.com",
                    key="url_extract"
                )
            with col2:
                extract_btn = st.button(" Извлечь", key="btn_extract", use_container_width=True)
            
            if extract_btn and url:
                if not url.startswith('http'):
                    url = 'https://' + url
                
                try:
                    with st.spinner("🔄 Загружаю сайт..."):
                        html = reader.fetch_website(url)
                        title = reader.get_title(html)
                        text = reader.extract_text(html)
                    
                    st.success(f"✅ Текст извлечен из: **{title}**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(" Всего символов", len(text))
                    with col2:
                        st.metric(" Всего слов", len(text.split()))
                    
                    st.markdown("---")
                    st.markdown("###  Содержимое:")
                    st.text_area(
                        "Извлеченный текст",
                        value=text,
                        height=400,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Скачать как TXT",
                        data=text,
                        file_name=f"{title.replace(' ', '_')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")
        
        # TAB 4: HISTORY
        with tab4:
            st.markdown("### 📊 История анализов")
            
            if st.session_state.results:
                for i, result in enumerate(reversed(st.session_state.results), 1):
                    with st.expander(f"#{i} {result['type']} - {result['title']} ({result['time'].strftime('%H:%M:%S')})"):
                        st.markdown(f"**URL:** {result['url']}")
                        if 'query' in result:
                            st.markdown(f"**Вопрос:** {result['query']}")
                        st.markdown(f"**Результат:**\n{result['result']}")
                
                if st.button("🗑️ Очистить историю", use_container_width=True):
                    st.session_state.results = []
                    st.rerun()
            else:
                st.info("📭 История пуста. Проанализируйте сайты выше!")
        
        # TAB 5: HELP
        with tab5:
            st.markdown("###  Справка и инструкции")
            
            st.markdown("""
            ## Как использовать AI Website Reader?
            
            ###  **Резюмирование**
            - Введите URL сайта
            - Нажмите "Анализировать"
            - Получите краткое содержание содержимого
            
            ###  **Анализ с вопросом**
            - Введите URL и задайте вопрос
            - ИИ найдет ответ в содержимом сайта
            - Используется для поиска конкретной информации
            
            ###  **Извлечение текста**
            - Извлекает чистый текст со страницы
            - Удаляет весь HTML и скрипты
            - Можно скачать как текстовый файл
            
            ###  **Настройки**
            - **JavaScript рендеринг**: Для сайтов с динамическим контентом
            - **Текст в речь**: Преобразует результаты в аудио
            - **Модель ИИ**: Выберите между GPT-3.5 и GPT-4
            
            ###  **Советы**
            - Убедитесь, что у вас активный OpenAI API key
            - Для лучших результатов используйте GPT-4
            - Текст-в-речь работает только с английским голосом
            
            """)

    except Exception as e:
        st.error(f"Ошибка инициализации: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #667eea; padding: 20px;'>
    <p>🤖 <strong>AI Website Reader v2.0</strong> | Powered by OpenAI & Streamlit</p>
    <p style='font-size: 12px; color: #999;'>Made by infoKATATnelsya</p>
</div>
""", unsafe_allow_html=True)
