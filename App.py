import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import anthropic
import io
import base64

st.set_page_config(page_title="자비스", page_icon="🤖")
st.title("🤖 자비스 - AI 음성 비서")

# ── 사이드바: API 키 입력 ──────────────────────────────
with st.sidebar:
    st.header("설정")
    api_key = st.text_input("Anthropic API Key", type="password")
    st.caption("[API 키 발급받기](https://console.anthropic.com/)")
    voice_lang = st.selectbox("음성 언어", ["ko", "en"], index=0)
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

SYSTEM_PROMPT = (
    "당신은 '자비스'라는 이름의 친절하고 똑똑한 AI 비서입니다. "
    "간결하고 명확하게 한국어로 답변하세요."
)


# ── 유틸 함수 ──────────────────────────────────────────
def speech_to_text(audio_bytes: bytes) -> str | None:
    """음성 바이트를 텍스트로 변환 (구글 무료 음성인식 API 사용)"""
    recognizer = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="ko-KR")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        st.error(f"음성 인식 서비스 오류: {e}")
        return None
    except Exception as e:
        st.error(f"오디오 처리 오류: {e}")
        return None


def text_to_speech(text: str, lang: str = "ko") -> bytes:
    """텍스트를 음성(mp3)으로 변환"""
    tts = gTTS(text=text, lang=lang)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp.read()


def get_ai_response(client: anthropic.Anthropic, messages: list) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def autoplay_audio(audio_bytes: bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
        unsafe_allow_html=True,
    )


# ── 채팅 기록 표시 ─────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── 입력: 음성 or 텍스트 ───────────────────────────────
st.write("🎤 아래 버튼을 눌러 말하거나, 하단에 텍스트를 입력하세요.")
audio_value = st.audio_input("음성으로 말하기")

user_input = None

if audio_value is not None:
    with st.spinner("음성 인식 중..."):
        recognized_text = speech_to_text(audio_value.read())
    if recognized_text:
        st.success(f"인식된 텍스트: {recognized_text}")
        user_input = recognized_text
    else:
        st.warning("음성을 인식하지 못했습니다. 다시 말씀해 주세요.")

text_input = st.chat_input("메시지를 입력하세요")
if text_input:
    user_input = text_input

# ── 응답 처리 ──────────────────────────────────────────
if user_input:
    if not api_key:
        st.error("사이드바에 Anthropic API 키를 입력해주세요.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        client = anthropic.Anthropic(api_key=api_key)
        ai_messages = [
            {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
        ]

        with st.spinner("자비스가 생각 중..."):
            ai_response = get_ai_response(client, ai_messages)

        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.write(ai_response)
            with st.spinner("음성 생성 중..."):
                speech_bytes = text_to_speech(ai_response, lang=voice_lang)
            autoplay_audio(speech_bytes)
            st.audio(speech_bytes, format="audio/mp3")
