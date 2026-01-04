import os, json, time, re
from datetime import datetime, timedelta
from typing import List, Dict, Any
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI

# =========================================================
# PAGE + MODEL
# =========================================================
st.set_page_config(page_title="ADHD Life Mentor", layout="wide")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.warning("⚠️ Please set your GOOGLE_API_KEY environment variable.")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.25)

# =========================================================
# SESSION STATE
# =========================================================
if "tasks" not in st.session_state:
    st.session_state.tasks: Dict[str, List[Dict[str, Any]]] = {
        "Academics": [],
        "Personal": [],
        "Hobbies": [],
        "Future/Long-term goals": [],
    }
if "top3" not in st.session_state:
    st.session_state.top3: List[str] = []
if "last_user_action" not in st.session_state:
    st.session_state.last_user_action = time.time()
if "motivation_shown" not in st.session_state:
    st.session_state.motivation_shown = False


# =========================================================
# HELPERS
# =========================================================
def infer_deadline(text: str) -> str:
    lower = text.lower()
    today = datetime.now()
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
        "nov": 11, "dec": 12,
    }
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})", lower)
    if m:
        month = month_map[m.group(1)]
        day = int(m.group(2))
        year = today.year if month >= today.month else today.year + 1
        return datetime(year, month, day).strftime("%Y-%m-%d")
    if "tomorrow" in lower:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in lower or "tonight" in lower:
        return today.strftime("%Y-%m-%d")
    if "next week" in lower:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    if "exam" in lower:
        return (today + timedelta(days=5)).strftime("%Y-%m-%d")
    if "assignment" in lower or "submission" in lower or "submit" in lower:
        return (today + timedelta(days=3)).strftime("%Y-%m-%d")
    return "None"


def add_or_merge_tasks(new_tasks: Dict[str, List[str]]):
    for cat, task_list in new_tasks.items():
        if cat not in st.session_state.tasks:
            st.session_state.tasks[cat] = []

        for t in task_list:
            # 🔹 Handle both dicts and strings safely
            if isinstance(t, dict):
                t = t.get("task", "")
            if not isinstance(t, str) or not t.strip():
                continue  # Skip invalid entries

            # 🔹 Check if task already exists
            if not any(existing["task"].lower() == t.lower() for existing in st.session_state.tasks[cat]):
                st.session_state.tasks[cat].append({
                    "task": t,
                    "due": infer_deadline(t) if isinstance(t, str) else "None",
                    "started": False,
                    "done": False,
                    "subtasks": []
                })



def get_top3_from_all_tasks() -> List[str]:
    all_tasks = [item["task"] for cat in st.session_state.tasks.values() for item in cat]
    if not all_tasks:
        return []
    prompt = f"""
    Pick the 3 most urgent/important tasks from this list.
    Return ONLY a JSON list of strings.
    Tasks: {all_tasks}
    """
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("["): raw.rindex("]") + 1]
        return json.loads(json_text)
    except:
        return all_tasks[:3]


def categorize_with_llm(raw_text: str) -> Dict[str, List[str]]:
    prompt = f"""
    Categorize into:
    - Academics
    - Personal
    - Hobbies
    - Future/Long-term goals
    Return valid JSON only.
    Thoughts: {raw_text}
    """
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        return json.loads(json_text)
    except:
        return {c: [] for c in ["Academics", "Personal", "Hobbies", "Future/Long-term goals"]}


# =========================================================
# INPUT
# =========================================================
st.markdown("## 🌻 ADHD Life Mentor — Dump & Organize Agent")

raw_thoughts = st.text_area(
    "Dump your thoughts here:",
    height=120,
    placeholder="E.g. study for exam, buy groceries, start learning guitar..."
)

if st.button("✨ Organize / Merge"):
    if raw_thoughts.strip():
        categorized = categorize_with_llm(raw_thoughts)
        add_or_merge_tasks(categorized)
        st.session_state.top3 = get_top3_from_all_tasks()
        st.session_state.last_user_action = time.time()
        st.session_state.motivation_shown = False
        st.success("✅ Dashboard updated!")
    else:
        st.warning("Please write some thoughts first 🙂")


# =========================================================
# DASHBOARD (TASKS INSIDE BOXES)
# =========================================================
st.markdown("### 🧠 Your Organized Dashboard")

cats = ["Academics", "Personal", "Hobbies", "Future/Long-term goals"]
cols = st.columns(4)

for idx, cat in enumerate(cats):
    with cols[idx]:
        box = st.container(border=True)
        with box:
            st.markdown(f"#### {cat}")
            current_tasks = st.session_state.tasks.get(cat, [])
            if not current_tasks:
                st.markdown("<p style='color:gray;'>➕ No tasks yet</p>", unsafe_allow_html=True)
            else:
                for i, task_obj in enumerate(current_tasks):
                    task_label = task_obj["task"]
                    due_label = f" (due: {task_obj['due']})" if task_obj["due"] != "None" else ""
                    start_key = f"start_{cat}_{i}"
                    done_key = f"done_{cat}_{i}"
                    sub_key = f"subs_{cat}_{i}"

                    started = st.checkbox(f"▶️ Start: {task_label}{due_label}", key=start_key, value=task_obj["started"])
                    task_obj["started"] = started
                    if started:
                        st.session_state.last_user_action = time.time()
                        st.session_state.motivation_shown = False

                    done = st.checkbox("✅ Done", key=done_key, value=task_obj["done"])
                    task_obj["done"] = done
                    if done:
                        st.session_state.last_user_action = time.time()
                        st.session_state.motivation_shown = False

                    new_subs = st.text_input("sub-tasks (comma separated)",
                                             value=", ".join(task_obj["subtasks"]),
                                             key=sub_key,
                                             label_visibility="collapsed")
                    task_obj["subtasks"] = [x.strip() for x in new_subs.split(",") if x.strip()]

                    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

                done_count = sum(1 for t in current_tasks if t["done"])
                total = len(current_tasks)
                st.markdown(f"<b>📊 Progress:</b> {done_count}/{total} completed", unsafe_allow_html=True)


# =========================================================
# TOP 3 PRIORITY
# =========================================================
st.markdown("### 🔥 Top 3 Priority Tasks")
if st.session_state.top3:
    for i, t in enumerate(st.session_state.top3, 1):
        st.write(f"{i}. {t}")
else:
    st.write("No tasks yet — dump something above!")


# =========================================================
# MOTIVATIONAL REMINDER (2 MIN)
# =========================================================
def any_task_in_progress() -> bool:
    return any(t["started"] and not t["done"] for cat in st.session_state.tasks.values() for t in cat)

now = time.time()
elapsed = now - st.session_state.last_user_action

if elapsed > 120 and not any_task_in_progress() and not st.session_state.motivation_shown:
    st.warning("⏰ Hey, it's been 2 minutes! Haven’t seen progress — want to share what's blocking you? 💛")
    st.session_state.motivation_shown = True

st.info("💬 Tip: even 5 minutes on ONE task counts as progress!")


##  