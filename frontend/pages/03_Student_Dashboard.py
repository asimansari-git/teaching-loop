import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import streamlit.components.v1 as components
from utils import (
    send_chat_message, create_chat_session, get_chat_sessions, get_session_history_by_id,
    validate_subject, create_learning_plan, generate_quiz, submit_quiz, get_subjects,
    get_certificate, get_student_reports, decode_jwt_payload, logout, API_URL,
    generate_textbook_article, get_socratic_hint, save_highlight, get_highlights,
    compile_review_sheet, get_micro_credential, generate_refresher_quiz
)

st.set_page_config(page_title="Student Dashboard", page_icon="🧑‍🎓", layout="wide")

if "token" not in st.session_state or st.session_state.get("role") != "student":
    st.warning("Please login as a student first.")
    st.stop()

# Ensure user_id is populated from token claims if missing
if "user_id" not in st.session_state:
    claims = decode_jwt_payload(st.session_state.get("token", ""))
    st.session_state["user_id"] = claims.get("user_id", 0)

# --- Sidebar: User Profile & Session Controls ---
with st.sidebar:
    st.markdown(f"### 🧑‍🎓 **{st.session_state.get('username', 'Student')}**")
    st.caption("Role: Enrolled Student")
    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
    
    st.divider()
    st.title("Chat History")
    if st.button("➕ New Chat Session", use_container_width=True):
        st.session_state["active_session_id"] = None
        st.session_state.pop("learning_plan", None)
        st.session_state.pop("current_quiz", None)
        st.session_state.pop("quiz_result", None)
        st.rerun()

    sessions = get_chat_sessions(st.session_state["token"])
    if sessions:
        for s in sessions:
            label = s.get("title", f"Session {s.get('session_id', '')[:8]}")
            is_active = st.session_state.get("active_session_id") == s["session_id"]
            prefix = "👉 " if is_active else "💬 "
            if st.button(f"{prefix}{label}", key=f"sess_{s['session_id']}", use_container_width=True):
                st.session_state["active_session_id"] = s["session_id"]
                st.session_state.pop("current_quiz", None)
                st.session_state.pop("quiz_result", None)
                st.rerun()
    else:
        st.caption("No past sessions found.")

# --- Header ---
st.title(f"Welcome back, {st.session_state.get('username', 'Student')}! 👋")
st.caption("Your personalized AI-driven learning and evaluation environment.")

# --- Session Loading & Metadata ---
active_session_id = st.session_state.get("active_session_id")
session_data = {}
selected_subject = "General"

if active_session_id:
    session_data = get_session_history_by_id(active_session_id, st.session_state["token"])
    if isinstance(session_data, dict):
        selected_subject = session_data.get("subject", "General")
        if "learning_plan" in session_data and session_data["learning_plan"]:
            st.session_state["learning_plan"] = session_data["learning_plan"]

def get_socratic_reader_html(session_id, article_data, token, api_url):
    article_json = json.dumps(article_data or {})
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 12px;
    color: #1e293b;
    background-color: #f8fafc;
  }}
  #reader-container {{
    max-width: 900px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 12px;
    padding: 28px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    position: relative;
  }}
  .article-title {{
    font-size: 26px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
  }}
  .article-topics {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }}
  .topic-tag {{
    background: #e0e7ff;
    color: #3730a3;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 16px;
  }}
  .article-body p {{
    font-size: 16px;
    line-height: 1.8;
    color: #334155;
    margin-bottom: 18px;
    position: relative;
    padding: 8px 12px;
    border-radius: 6px;
    transition: background-color 0.3s ease;
  }}
  .article-body span[data-span-id], .article-body span[id^="s-"] {{
    border-bottom: 1px transparent;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }}
  .article-body span:hover {{
    background-color: rgba(99, 102, 241, 0.12);
  }}

  /* Glowing pulse accent animation for Inverted Retrieval Focus */
  @keyframes pulse-glow {{
    0% {{
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7);
      background-color: rgba(99, 102, 241, 0.18);
    }}
    50% {{
      box-shadow: 0 0 0 10px rgba(99, 102, 241, 0);
      background-color: rgba(99, 102, 241, 0.28);
    }}
    100% {{
      box-shadow: 0 0 0 0 rgba(99, 102, 241, 0);
      background-color: rgba(99, 102, 241, 0.05);
    }}
  }}
  .glowing-pulse {{
    animation: pulse-glow 2.5s ease-in-out infinite;
    border-left: 4px solid #4f46e5 !important;
    border-radius: 4px;
  }}

  /* Floating Action Toolbar Popover */
  #floating-toolbar {{
    position: absolute;
    display: none;
    z-index: 1000;
    background: #1e1b4b;
    color: #ffffff;
    padding: 6px 10px;
    border-radius: 30px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    gap: 6px;
    align-items: center;
    transform: translate(-50%, -100%);
    transition: opacity 0.15s ease, transform 0.15s ease;
  }}
  #floating-toolbar.active {{
    display: flex;
  }}
  .toolbar-btn {{
    background: transparent;
    border: none;
    color: #f1f5f9;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 9px;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: background 0.2s ease, transform 0.1s ease;
  }}
  .toolbar-btn:hover {{
    background: rgba(255, 255, 255, 0.22);
    transform: translateY(-1px);
  }}

  /* Framer Motion style expanding inline card */
  .inline-card {{
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 4px solid #0284c7;
    border-radius: 8px;
    margin: 12px 0 20px 0;
    overflow: hidden;
    max-height: 0;
    opacity: 0;
    transition: max-height 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease, padding 0.3s ease;
    padding: 0 16px;
  }}
  .inline-card.expanded {{
    max-height: 500px;
    opacity: 1;
    padding: 16px;
  }}
  .inline-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 700;
    font-size: 14px;
    color: #0369a1;
    margin-bottom: 8px;
  }}
  .inline-card-body {{
    font-size: 15px;
    color: #1e293b;
    line-height: 1.6;
  }}
  .inline-card-close {{
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    font-size: 16px;
  }}

  /* Directional Reasoning Hint Accordion */
  .hint-accordion {{
    background: #fefce8;
    border: 1px solid #fef08a;
    border-left: 4px solid #eab308;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
    color: #713f12;
  }}
  .hint-title {{
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  #toast {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #0f172a;
    color: #ffffff;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 13px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    display: none;
    z-index: 2000;
  }}
</style>
</head>
<body>

<div id="reader-container">
  <div class="article-title" id="art-title">Loading Textbook...</div>
  <div class="article-topics" id="art-topics"></div>
  <hr style="border: 0; height: 1px; background: #e2e8f0; margin-bottom: 20px;">
  <div class="article-body" id="art-body"></div>
</div>

<!-- Floating Action Toolbar Popover -->
<div id="floating-toolbar">
  <button class="toolbar-btn" onclick="handleToolbarAction('Ask Doubt')">🙋 Ask Doubt</button>
  <button class="toolbar-btn" onclick="handleToolbarAction('Flag Tough')">🔴 Flag Tough</button>
  <button class="toolbar-btn" onclick="handleToolbarAction('Flag Rewind')">⏪ Flag Rewind</button>
  <button class="toolbar-btn" onclick="handleToolbarAction('Note')">📝 Add Note</button>
  <button class="toolbar-btn" onclick="handleToolbarAction('Socratic Hint')">💡 Socratic Hint</button>
</div>

<!-- Toast Notification -->
<div id="toast"></div>

<script>
  const SESSION_ID = "{session_id}";
  const TOKEN = "{token}";
  const API_URL = "{api_url}";
  const ARTICLE_DATA = {article_json};

  let currentSelection = null;

  function showToast(msg) {{
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.style.display = 'block';
    setTimeout(() => {{ toast.style.display = 'none'; }}, 2500);
  }}

  function initArticle() {{
    if (!ARTICLE_DATA) return;
    document.getElementById('art-title').innerText = ARTICLE_DATA.title || 'Socratic Living Textbook';
    const topicsContainer = document.getElementById('art-topics');
    topicsContainer.innerHTML = '';
    (ARTICLE_DATA.topics || []).forEach(t => {{
      const tag = document.createElement('span');
      tag.className = 'topic-tag';
      tag.innerText = t;
      topicsContainer.appendChild(tag);
    }});

    const bodyContainer = document.getElementById('art-body');
    bodyContainer.innerHTML = ARTICLE_DATA.markdown_content || '<p id="p-1"><span id="s-1-1">Welcome to Socratic Reader. Select text to highlight or ask doubts.</span></p>';
  }}

  initArticle();

  const toolbar = document.getElementById('floating-toolbar');

  function handleSelectionChange() {{
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {{
      toolbar.classList.remove('active');
      return;
    }}

    const text = sel.toString().trim();
    if (text.length < 2) {{
      toolbar.classList.remove('active');
      return;
    }}

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const container = range.commonAncestorContainer.nodeType === 3 ? range.commonAncestorContainer.parentNode : range.commonAncestorContainer;

    const spanElem = container.closest('[data-span-id]') || container.closest('span[id]');
    const pElem = container.closest('[data-paragraph-id]') || container.closest('p[id]') || container.closest('p');

    const elemId = spanElem ? spanElem.id : (pElem && pElem.id ? pElem.id : 'p-1');
    const paragraphId = pElem && pElem.id ? pElem.id : 'p-1';

    currentSelection = {{
      quotedText: text,
      elementId: elemId,
      paragraphId: paragraphId,
      rect: rect
    }};

    const containerRect = document.getElementById('reader-container').getBoundingClientRect();
    const topPos = rect.top - containerRect.top - 12;
    const leftPos = rect.left - containerRect.left + (rect.width / 2);

    toolbar.style.top = topPos + 'px';
    toolbar.style.left = leftPos + 'px';
    toolbar.classList.add('active');
  }}

  document.addEventListener('mouseup', handleSelectionChange);

  async function handleToolbarAction(actionTag) {{
    toolbar.classList.remove('active');
    if (!currentSelection) return;

    const {{ quotedText, elementId, paragraphId }} = currentSelection;

    if (actionTag === 'Flag Tough' || actionTag === 'Flag Rewind' || actionTag === 'Note') {{
      let qText = '';
      if (actionTag === 'Note') {{
        qText = prompt('Add key note / comment:', '') || '';
      }}
      try {{
        await fetch(`${{API_URL}}/chat/${{SESSION_ID}}/highlight`, {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${{TOKEN}}`
          }},
          body: JSON.stringify({{
            element_id: elementId,
            quoted_text: quotedText,
            question: qText,
            tag: actionTag.replace('Flag ', '')
          }})
        }});
        showToast(`Tagged as ${{actionTag}}!`);
      }} catch (err) {{
        console.error(err);
      }}
    }} else if (actionTag === 'Ask Doubt') {{
      const userQuestion = prompt(`Ask AI Tutor a doubt regarding:\n"${{quotedText}}"`, '');
      if (userQuestion) {{
        saveAndExpandInlineCard(elementId, paragraphId, quotedText, userQuestion, 'Ask Doubt');
      }}
    }} else if (actionTag === 'Socratic Hint') {{
      saveAndExpandSocraticHint(elementId, paragraphId, quotedText);
    }}
  }}

  async function saveAndExpandInlineCard(elementId, paragraphId, quotedText, userQuestion, tag) {{
    try {{
      await fetch(`${{API_URL}}/chat/${{SESSION_ID}}/highlight`, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${{TOKEN}}`
        }},
        body: JSON.stringify({{
          element_id: elementId,
          quoted_text: quotedText,
          question: userQuestion,
          tag: tag
        }})
      }});
    }} catch (e) {{ console.error(e); }}

    let pTarget = document.getElementById(paragraphId) || document.getElementById(elementId);
    if (!pTarget) {{
      pTarget = document.getElementById('art-body').firstElementChild;
    }}
    if (!pTarget) return;

    const card = document.createElement('div');
    card.className = 'inline-card';
    card.innerHTML = `
      <div class="inline-card-header">
        <span>💬 AI Tutor Explanation (${{elementId}})</span>
        <button class="inline-card-close" onclick="this.closest('.inline-card').remove()">✕</button>
      </div>
      <div class="inline-card-body">
        <p style="margin: 0 0 8px 0; font-size: 13px; color: #475569;"><strong>Quoted:</strong> "${{quotedText}}"</p>
        <p style="margin: 0 0 12px 0; font-weight: 600; color: #0f172a;">Q: ${{userQuestion}}</p>
        <div class="ai-response-text" style="color: #334155;"><em>AI Tutor is formulating an explanation...</em></div>
      </div>
    `;

    pTarget.after(card);
    setTimeout(() => {{ card.classList.add('expanded'); }}, 20);

    try {{
      const resp = await fetch(`${{API_URL}}/chat/${{SESSION_ID}}`, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${{TOKEN}}`
        }},
        body: JSON.stringify({{ prompt: `[Passage: "${{quotedText}}"] Student Question: ${{userQuestion}}` }})
      }});
      const data = await resp.json();
      card.querySelector('.ai-response-text').innerText = data.response || 'No explanation generated.';
    }} catch (err) {{
      card.querySelector('.ai-response-text').innerText = 'Error connecting to AI Tutor service.';
    }}
  }}

  async function saveAndExpandSocraticHint(elementId, paragraphId, quotedText) {{
    showToast('Locating Socratic reasoning hint...');

    try {{
      const resp = await fetch(`${{API_URL}}/chat/textbook/socratic-hint`, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${{TOKEN}}`
        }},
        body: JSON.stringify({{
          session_id: SESSION_ID,
          question: `Provide a socratic hint for: ${{quotedText}}`
        }})
      }});
      const data = await resp.json();
      const targetId = data.target_element_id || elementId;
      const hint = data.socratic_hint;

      scrollToHighlight(targetId, hint);
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function scrollToHighlight(targetId, hintText) {{
    let elem = document.getElementById(targetId);
    if (!elem) {{
      elem = document.getElementById('art-body').firstElementChild;
    }}
    if (!elem) return;

    elem.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    elem.classList.add('glowing-pulse');

    setTimeout(() => {{ elem.classList.remove('glowing-pulse'); }}, 3500);

    if (hintText) {{
      let existingAccordion = elem.nextElementSibling;
      if (!existingAccordion || !existingAccordion.classList.contains('hint-accordion')) {{
        const accordion = document.createElement('div');
        accordion.className = 'hint-accordion';
        accordion.innerHTML = `
          <div class="hint-title">💡 Socratic Directional Hint</div>
          <div style="margin-top: 6px;">${{hintText}}</div>
        `;
        elem.after(accordion);
      }}
    }}
  }}

  window.scrollToHighlight = scrollToHighlight;
</script>
</body>
</html>
"""

# --- Main Dashboard Tabs ---
tab_reader, tab_chat, tab_quiz, tab_review, tab_reports = st.tabs([
    "📖 Socratic Reader",
    "💬 Live AI Tutor",
    "📝 Adaptive Quizzes",
    "📋 Batch Review Sheet",
    "🏆 Living Micro-Credentials & Reports"
])

def render_start_session_ui():
    st.subheader("🚀 Start a New Learning Session")
    subject_source = st.radio("Choose Subject Source", ["Preset", "Custom"], horizontal=True, key="start_subj_src")

    selected_subject_init = ""
    selected_topics_init = []

    db_subjects_list = get_subjects(st.session_state["token"])
    db_subjects = {s["name"]: s.get("topics", []) for s in db_subjects_list} if db_subjects_list else {}

    if subject_source == "Preset":
        if not db_subjects:
            st.info("No preset subjects found in the database. Choose 'Custom' to explore any topic.")
        else:
            selected_subject_name = st.selectbox("Select Subject", list(db_subjects.keys()), key="preset_subj_sel")
            if selected_subject_name:
                selected_subject_init = selected_subject_name
                available_topics = db_subjects.get(selected_subject_name, [])
                selected_topics_init = st.multiselect("Select Focus Topics", available_topics, default=available_topics[:3] if available_topics else [], key="preset_topic_sel")
    else:
        custom_input = st.text_input("Enter Subject Name (e.g., 'React.js', 'Quantum Physics', 'Calculus')", key="custom_subj_in")
        if st.button("🔍 Validate & Discover Topics", key="val_custom_btn"):
            if custom_input:
                with st.spinner("Analyzing curriculum with AI..."):
                    data = validate_subject(custom_input, st.session_state["token"])
                    if data:
                        st.session_state["custom_subject_data"] = data
                    else:
                        st.error("Could not validate subject.")

        if "custom_subject_data" in st.session_state:
            data = st.session_state["custom_subject_data"]
            st.success(f"Curriculum verified: **{data.get('name')}**")
            selected_subject_init = data.get("name")
            all_topics = data.get("topics", [])
            selected_topics_init = st.multiselect("Select Topics to Cover", all_topics, default=all_topics[:4] if all_topics else [], key="custom_topic_sel")

    if st.button("🚀 Start Learning Session", type="primary", use_container_width=True, key="start_sess_main_btn"):
        if not selected_subject_init:
            st.error("Please specify a subject.")
        elif not selected_topics_init:
            st.error("Please select at least one topic.")
        else:
            with st.spinner("Initializing session & crafting personalized curriculum..."):
                new_session_id = create_chat_session(selected_subject_init, selected_topics_init, st.session_state["token"])
                if new_session_id:
                    plan = create_learning_plan(new_session_id, st.session_state["token"])
                    st.session_state["active_session_id"] = new_session_id
                    if plan:
                        st.session_state["learning_plan"] = plan
                    st.success("Session ready! Let's begin.")
                    st.rerun()
                else:
                    st.error("Failed to start session.")

# ==========================================
# TAB 1: Socratic Reader
# ==========================================
with tab_reader:
    if not active_session_id:
        render_start_session_ui()
    else:
        col_tb_hdr, col_tb_gen = st.columns([3, 1])
        with col_tb_hdr:
            st.subheader(f"📖 Socratic Reader — {selected_subject}")
            st.caption("Active Reading Engine: Highlight text to ask doubts, flag tough passages, or receive Socratic hints.")
        with col_tb_gen:
            if st.button("🔄 Regenerate Textbook Article", key="regen_tb"):
                with st.spinner("Generating living textbook article with paragraph/sentence DOM IDs..."):
                    art = generate_textbook_article(active_session_id, None, st.session_state["token"])
                    if art:
                        st.session_state["textbook_article"] = art
                        st.success("Textbook article regenerated!")
                        st.rerun()

        if "textbook_article" not in st.session_state or st.session_state.get("textbook_article_session") != active_session_id:
            with st.spinner("Preparing living textbook article with interactive DOM anchors..."):
                art = generate_textbook_article(active_session_id, None, st.session_state["token"])
                if art:
                    st.session_state["textbook_article"] = art
                    st.session_state["textbook_article_session"] = active_session_id

        art_data = st.session_state.get("textbook_article")
        if art_data:
            reader_html = get_socratic_reader_html(active_session_id, art_data, st.session_state["token"], API_URL)
            components.html(reader_html, height=720, scrolling=True)
        else:
            st.error("Could not load textbook article.")

# ==========================================
# TAB 2: Live AI Tutor
# ==========================================
with tab_chat:
    if not active_session_id:
        render_start_session_ui()
    else:
        # Display Active Session Layout
        col_main, col_plan = st.columns([3, 1])

        with col_plan:
            st.markdown("### 🗺️ **Learning Path**")
            plan = st.session_state.get("learning_plan", {})
            modules = plan.get("modules", []) if isinstance(plan, dict) else []
            if modules:
                for idx, mod in enumerate(modules):
                    with st.expander(f"Module {idx+1}: {mod.get('title', 'Unit')}", expanded=(idx == 0)):
                        st.write(mod.get("description", ""))
                        topics_list = mod.get("topics", [])
                        if topics_list:
                            st.caption(f"**Topics:** {', '.join(topics_list)}")
            else:
                st.info("General Learning Path active.")

        with col_main:
            history = session_data.get("messages", []) if isinstance(session_data, dict) else []
            
            # Chat history container
            chat_box = st.container()
            with chat_box:
                skip_next_model = False
                for message in history:
                    role = message.get("role", "user")
                    author = message.get("author")
                    visible = message.get("visible_to_student", True)
                    
                    if not visible or author in ["teacher", "teacher_model", "teacher_assistant", "model_to_teacher"]:
                        if author == "teacher":
                            skip_next_model = True
                        continue
                    
                    if skip_next_model and role != "user":
                        skip_next_model = False
                        continue
                    skip_next_model = False
                    
                    parts = message.get("parts", [])
                    content = parts[0] if isinstance(parts, list) and parts else str(parts)
                    
                    if role == "user":
                        with st.chat_message("user"):
                            st.markdown(content)
                    else:
                        with st.chat_message("assistant", avatar="🎓"):
                            st.markdown(content)

            # Chat input
            if prompt := st.chat_input("Ask a question or explain a concept..."):
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.spinner("AI Tutor is formulating an explanation..."):
                    response_text = send_chat_message(prompt, active_session_id, st.session_state["token"])
                
                if response_text:
                    with st.chat_message("assistant", avatar="🎓"):
                        st.markdown(response_text)
                    st.rerun()
                else:
                    st.error("Failed to get response from AI tutor.")

# ==========================================
# TAB 2: Adaptive Quizzes
# ==========================================
with tab_quiz:
    if not active_session_id:
        st.info("👉 Please select or start a learning chat session first to unlock its quiz.")
    else:
        diff = st.session_state.get("quiz_difficulty", "easy")
        
        # Difficulty badges
        badge_map = {
            "easy": "🟢 **Level: Easy**",
            "mid": "🟡 **Level: Intermediate**",
            "hard": "🔴 **Level: Advanced (Hard)**"
        }
        
        col_diff, col_reset = st.columns([3, 1])
        with col_diff:
            st.markdown(f"### 📝 {badge_map.get(diff, 'Adaptive Quiz')}")
        with col_reset:
            if st.button("🔄 Reset / New Quiz"):
                st.session_state.pop("current_quiz", None)
                st.session_state.pop("quiz_result", None)
                st.rerun()

        # Quiz Generation & Rendering
        if "current_quiz" not in st.session_state or st.session_state["current_quiz"] is None:
            with st.spinner(f"Generating {diff.capitalize()}-level assessment questions..."):
                quiz_data = generate_quiz(active_session_id, diff, st.session_state["token"])
                if quiz_data and quiz_data.get("questions"):
                    st.session_state["current_quiz"] = quiz_data
                else:
                    st.session_state["current_quiz"] = None

        quiz = st.session_state.get("current_quiz")
        quiz_result = st.session_state.get("quiz_result")

        if quiz_result:
            score = quiz_result.get("score", 0)
            total = quiz_result.get("total", 0)
            pct = quiz_result.get("percentage", 0)
            passed = quiz_result.get("passed", False)
            review = quiz_result.get("review", [])
            
            st.metric(label="Quiz Score", value=f"{score}/{total}", delta=f"{pct:.1f}%")
            
            if passed:
                st.success("🎉 Outstanding work! You passed this level.")
                if diff == "easy":
                    if st.button("Proceed to Intermediate Level 🟡", type="primary"):
                        st.session_state["quiz_difficulty"] = "mid"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                elif diff == "mid":
                    if st.button("Proceed to Advanced (Hard) Level 🔴", type="primary"):
                        st.session_state["quiz_difficulty"] = "hard"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                else:
                    st.balloons()
                    st.success("🏆 Mastery Achieved! You have passed all adaptive levels.")
                    st.session_state["passed_hard"] = True
                    if st.button("📜 Generate Verified Certificate", type="primary"):
                        cert_text = get_certificate(active_session_id, selected_subject, st.session_state["token"])
                        if cert_text:
                            st.session_state["certificate_markdown"] = cert_text
                            st.rerun()
            else:
                st.error("You did not reach the 70% threshold. Review the material with your AI tutor and try again!")
                if st.button("🔄 Try Quiz Again"):
                    st.session_state.pop("current_quiz", None)
                    st.session_state.pop("quiz_result", None)
                    st.rerun()
                    
            if review:
                st.divider()
                st.markdown("### 📋 **Assessment Breakdown & Explanations**")
                for idx, item in enumerate(review):
                    status_icon = "✅" if item.get("is_correct") else "❌"
                    with st.expander(f"{status_icon} Question {idx+1}: {item.get('text', '')}", expanded=not item.get("is_correct")):
                        st.markdown(f"**Your Answer:** {item.get('user_choice_text') or '*(No answer selected)*'}")
                        if not item.get("is_correct"):
                            st.markdown(f"**Correct Answer:** `{item.get('correct_option_text')}`")
                        else:
                            st.markdown("🎯 *Correctly answered!*")

        elif quiz and quiz.get("questions"):
            with st.form(f"quiz_form_{active_session_id}_{diff}"):
                answers = {}
                for i, q in enumerate(quiz["questions"]):
                    qid = str(q.get("id", i + 1))
                    st.markdown(f"**Question {i+1}:** {q.get('text', '')}")
                    options = q.get('options', [])
                    if options:
                        choice = st.radio(
                            "Select your answer:",
                            options,
                            key=f"opt_{active_session_id}_{diff}_{qid}_{i}"
                        )
                        answers[qid] = options.index(choice) if choice in options else -1
                    st.divider()

                if st.form_submit_button("Submit Assessment", type="primary", use_container_width=True):
                    quiz_ref = quiz.get("db_id") or quiz
                    result = submit_quiz(quiz_ref, answers, st.session_state["token"])
                    if result:
                        st.session_state["quiz_result"] = result
                    else:
                        st.error("Failed to evaluate quiz.")
                    st.rerun()
        else:
            st.warning("⚠️ Quiz questions could not be prepared at this moment.")

# ==========================================
# TAB 3: My Reports & Certificates
# ==========================================
with tab_reports:
    st.subheader("📊 Performance Reports & Certificates")
    
    col_rep, col_cert = st.columns([1, 1])

    with col_rep:
        st.markdown("#### 📑 Teacher Evaluations & Feedback")
        user_id = st.session_state.get("user_id", 0)
        reports = get_student_reports(user_id, st.session_state["token"]) if user_id else []
        
        if reports:
            for rep in reports:
                with st.expander(f"Report: {rep.get('subject', 'General')} — {str(rep.get('created_at', ''))[:10]}"):
                    st.markdown(rep.get("content", ""))
                    st.download_button(
                        label="📥 Download Report (.md)",
                        data=rep.get("content", ""),
                        file_name=f"Report_{rep.get('subject', 'general')}_{rep.get('id')}.md",
                        mime="text/markdown",
                        key=f"dl_rep_{rep.get('id')}"
                    )
        else:
            st.info("No evaluations generated yet. When your teacher analyzes your sessions, reports will appear here.")

    with col_cert:
        st.markdown("#### 📜 Course Certificates")
        
        if "certificate_markdown" in st.session_state and st.session_state["certificate_markdown"]:
            st.success("Verified Certificate Available for Download!")
            st.markdown(st.session_state["certificate_markdown"])
            st.download_button(
                label="📥 Download Official Certificate",
                data=st.session_state["certificate_markdown"],
                file_name=f"Certificate_{selected_subject}.md",
                mime="text/markdown",
                key="dl_cert_btn"
            )
        else:
            if not st.session_state.get("passed_hard"):
                st.warning("🔒 **Certificate Locked**")
                st.markdown("""
                To earn an official completion certificate:
                1. Complete your learning modules.
                2. Pass the **Easy** and **Intermediate** quizzes.
                3. Score 70%+ on the **Advanced (Hard)** quiz.
                """)
            else:
                if st.button("Generate Verified Certificate Now", type="primary"):
                    cert_text = get_certificate(active_session_id, selected_subject, st.session_state["token"])
                    if cert_text:
                        st.session_state["certificate_markdown"] = cert_text
                        st.rerun()
    