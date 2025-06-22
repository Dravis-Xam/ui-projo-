from dotenv import load_dotenv
import os
from openai import OpenAI
import streamlit as st
import re
from datetime import datetime

# Load environment variables
load_dotenv()


def is_potentially_dangerous(prompt):
    """Check if message contains potentially dangerous commands"""
    dangerous_patterns = [
        r'\b(rm\s+-|del\s+|erase\s+|format\s+)',  # File deletion
        r'\b(mv\s+.*\s+/|move\s+.*\s+/)',  # Moving system files
        r'\b(chmod\s+[0-7]{3,4}\s+)',  # Permission changes
        r'\b(wget\s+|curl\s+)\S*(\.sh|\.exe|\.bat)',  # Downloading executables
        r'\b(\./|sh\s+|bash\s+|python\s+)\S*\.(sh|py)',  # Executing scripts
        r'\b(ssh\s+|scp\s+)',  # Remote connections
        r'\b(sudo\s+|su\s+)',  # Privilege escalation
        r'\b(echo\s+[^>]*>\s*\/)',  # Writing to system files
        r'\b(dd\s+if=)',  # Disk operations
        r'\b(kill\s+-9|taskkill\s+)',  # Process termination
        r'`.*`',  # Backtick commands
        r'\$(\(|{).*(\)|})',  # Command substitution
        r'<\s*\(.*\)'  # Process substitution
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return True
    return False


def extract_topic(prompt):
    """Extract the main topic from the user's first question"""
    topics = {
        r'\b(study|learn|education|school|university|exam|test|teach|class)\b': '📚 Education',
        r'\b(code|programming|python|java|c\+\+|algorithm|script|developer)\b': '💻 Programming',
        r'\b(math|algebra|calculus|geometry|equation|formula|theorem)\b': '🧮 Mathematics',
        r'\b(science|physics|chemistry|biology|experiment|research)\b': '🔬 Science',
        r'\b(business|finance|money|invest|stock|market|startup|entrepreneur)\b': '💼 Business',
        r'\b(health|medicine|doctor|hospital|diet|fitness|nutrition|exercise)\b': '🏥 Health',
        r'\b(art|music|paint|draw|design|creative|photography|film)\b': '🎨 Arts',
        r'\b(sport|game|football|basketball|tennis|soccer|olympics)\b': '⚽ Sports',
        r'\b(history|historical|past|war|empire|civilization)\b': '🏛️ History',
        r'\b(tech|technology|computer|software|hardware|ai|machine learning)\b': '🤖 Technology'
    }

    for pattern, topic in topics.items():
        if re.search(pattern, prompt, re.IGNORECASE):
            return topic
    return "💬 General Chat"


def clean_response(response):
    """Remove content between <think> tags and trim whitespace"""
    cleaned = re.sub(r'◁think▷.*?◁/think▷', '', response, flags=re.DOTALL)
    return cleaned.strip()


def ask_ai(user_message):
    """Call OpenRouter API and return cleaned response"""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Streamlit Chat App",
        },
        model="moonshotai/kimi-dev-72b:free",
        messages=[{"role": "user", "content": user_message}]
    )
    return type(completion.choices[0].message.content) and completion.choices[0].message.content


def main():
    # Page setup
    st.set_page_config(
        page_title="AI Chat",
        page_icon="💬",
        layout="wide"
    )

    # Custom CSS for styling
    st.markdown("""
    <style>
        /* Main chat container */
        .stChatMessage {
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 8px;
            max-width: 85%;
        }

        /* User messages */
        [data-testid="stChatMessage"] {
            background-color: #f0f2f6;
        }

        /* Assistant messages */
        [data-testid="stChatMessage"]:has(> div > [data-testid="stMarkdownContainer"] > div > img) {
            background-color: #e3f2fd;
        }

        /* Input area */
        .stTextInput > div > div > input {
            border-radius: 20px !important;
            padding: 10px 15px !important;
        }

        /* Timestamps */
        .message-time {
            font-size: 0.75rem;
            color: #666;
            margin-top: 4px;
        }

        /* Sidebar */
        .st-emotion-cache-6qob1r {
            background: linear-gradient(135deg, #6e8efb, #a777e3);
        }

        /* Typing indicator */
        .typing {
            display: inline-block;
            width: 10px;
            height: 10px;
            margin-right: 4px;
            background-color: #8e8e8e;
            border-radius: 50%;
            animation: typing 1s infinite ease-in-out;
        }
        .typing:nth-child(1) { animation-delay: 0s; }
        .typing:nth-child(2) { animation-delay: 0.2s; }
        .typing:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Header styling */
        .header-box {
            background: linear-gradient(135deg, #6e8efb, #a777e3);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Warning message */
        .warning-message {
            background-color: #fff3cd;
            color: #856404;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #ffeeba;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "chat_topic" not in st.session_state:
        st.session_state.chat_topic = "💬 General Chat"

    # Display header with topic
    st.markdown(f"""
    <div class="header-box">
        <h1 style="margin:0;padding:0;">{st.session_state.chat_topic}</h1>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Chat Settings")
        st.selectbox("Chat mode", ["Casual", "Professional", "Friendly"], key="chat_mode")
        st.color_picker("Theme color", "#6e8efb", key="theme_color")
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.chat_topic = "💬 General Chat"
            st.rerun()
        st.markdown("---")
        st.markdown("**Model:** moonshotai/kimi-dev-72b")
        st.markdown("**Powered by:** [OpenRouter](https://openrouter.ai)")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("warning"):
                st.markdown(f'<div class="warning-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(message["content"])
            if "time" in message:
                st.caption(message["time"])

    # User input
    if prompt := st.chat_input("Type your message...", disabled=st.session_state.processing):
        # Check for dangerous commands
        if is_potentially_dangerous(prompt):
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.messages.append({
                "role": "system",
                "content": "⚠️ For security reasons, I can't execute or discuss commands that might affect system operations.",
                "time": timestamp,
                "warning": True
            })
            st.rerun()

        # Set chat topic if first message
        if len(st.session_state.messages) == 0:
            st.session_state.chat_topic = extract_topic(prompt)

        # Add user message to history
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "time": timestamp
        })
        st.session_state.processing = True
        st.rerun()

    # Process AI response if needed
    if st.session_state.processing:
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            # Get last user message
            user_message = st.session_state.messages[-1]["content"]

            # Display temporary thinking indicator
            with st.chat_message("assistant"):
                with st.status("Thinking..."):
                    # Get AI response
                    res = ask_ai(user_message)
                    response = clean_response(res) if res is not None else 'Failed to generate your response'
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": clean_response(response),
                        "time": timestamp
                    })

            st.session_state.processing = False
            st.rerun()


if __name__ == "__main__":
    main()