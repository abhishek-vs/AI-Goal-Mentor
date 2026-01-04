import os, json, time, re, random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import sys

# Fix here: __file__ instead of _file_
sys.path.append(os.path.join(os.path.dirname(__file__)))

from models import Goal, Subgoal, Task
from langgraph_decomposer import decompose_goal_with_langgraph, visualize_goal_tree
from dotenv import load_dotenv

st.set_page_config(page_title="AI Goal Mentor (ADHD Edition)", layout="wide")

# gentle fall background
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(120deg, #FFDEE9 0%, #B5FFFC 100%);
}
[data-testid="stHeader"]{
    background: rgba(0,0,0,0);
}
.sidebar .sidebar-content {
    background: #fff7e6;
}
</style>
""", unsafe_allow_html=True)



# 1) Load .env if you’re using one
load_dotenv()

# 2) Read the key from env (support either name)
GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
)

print("DEBUG GOOGLE_API_KEY:", GOOGLE_API_KEY)  # TEMP: to verify it’s not None

if not GOOGLE_API_KEY:
    raise RuntimeError("No GOOGLE_API_KEY / GEMINI_API_KEY found in environment")

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.25,
    google_api_key=GOOGLE_API_KEY,
    transport="rest",  # forces API-key auth instead of ADC
)


# =========================================================
# SESSION STATE
# =========================================================
if "tasks" not in st.session_state:
    st.session_state.tasks: Dict[str, List[Dict[str, Any]]] = {
        "Academics": [],
        "Personal": [],
        "Hobbies": [],
        "Future/Long-term Goals": [],
    }

if "top3" not in st.session_state:
    st.session_state.top3: List[str] = []

if "last_user_action" not in st.session_state:
    st.session_state.last_user_action = time.time()

if "motivation_shown" not in st.session_state:
    st.session_state.motivation_shown = False

if "streak" not in st.session_state:
    st.session_state.streak = 0

# rewards
if "rewards" not in st.session_state:
    st.session_state.rewards: List[str] = []

# adaptive reminder level
if "reminder_level" not in st.session_state:
    st.session_state.reminder_level = 1  # will increase if user ignores

if "hierarchical_goals" not in st.session_state:
    st.session_state.hierarchical_goals = []  # Store as dicts for serialization

# Most recent tasks categorization confidence level and rationale
if "categorization_confidence" not in st.session_state:
    st.session_state.categorization_confidence = None

if "categorization_rationale" not in st.session_state:
    st.session_state.categorization_rationale = None

if "categorization_feedback" not in st.session_state:
    st.session_state.categorization_feedback: List[str] = []

if "decomposition_feedback" not in st.session_state:
    st.session_state.decomposition_feedback: List[str] = []

if "expander_states" not in st.session_state:
    st.session_state.expander_states = {}  # Store states for each goal expander

# how many task completions in a row (resets after celebration)
if "consecutive_completions" not in st.session_state:
    st.session_state.consecutive_completions = 0

# last streak value at which we triggered a "weekly" celebration
if "last_weekly_streak_milestone" not in st.session_state:
    st.session_state.last_weekly_streak_milestone = 0

if "current_decomposed_goal" not in st.session_state:
    st.session_state.current_decomposed_goal = None

# NEW: reflective check-ins + motivation state
if "pending_reflection" not in st.session_state:
    # holds info about the most recently completed "major" task
    st.session_state.pending_reflection = None

if "reflection_log" not in st.session_state:
    # simple log so user could later see their patterns (not shown yet)
    st.session_state.reflection_log: List[Dict[str, Any]] = []

if "motivation_flag" not in st.session_state:
    st.session_state.motivation_flag = None

# NEW: gentle reminder state (for User Story #10)
if "snooze_until" not in st.session_state:
    st.session_state.snooze_until = 0.0  # timestamp until which reminders are snoozed

if "missed_reminders" not in st.session_state:
    st.session_state.missed_reminders = 0  # how many times user snoozed / ignored

# Pending tasks waiting for user review (accept / reject / edit)
if "pending_review" not in st.session_state:
    st.session_state.pending_review = None

# NEW: autonomy settings (for subtask generation)
if "autonomy_settings" not in st.session_state:
    # Default OFF – AI only adds subtasks when you click "Add subtasks"
    st.session_state.autonomy_settings = {
        "auto_subtasks": False,
    }

if "last_auto_subtasks_state" not in st.session_state:
    st.session_state.last_auto_subtasks_state = st.session_state.autonomy_settings.get(
        "auto_subtasks", False
    )

# =========================================================
# HELPERS
# =========================================================

def infer_deadline(task: str) -> str:
    """
    Very small heuristic to guess a deadline description from text.
    E.g. "tomorrow", "next week", "Nov 12" -> a label. Not used as real date.
    """
    text = task.lower()
    now = datetime.now()
    if "tomorrow" in text:
        return (now + timedelta(days=1)).strftime("%b %d")
    m = re.search(r"\b(\d{1,2})\s*(st|nd|rd|th)?\b", text)
    if m:
        day = int(m.group(1))
        try:
            dt = now.replace(day=day)
            return dt.strftime("%b %d")
        except ValueError:
            pass
    if "next week" in text:
        return (now + timedelta(days=7)).strftime("%b %d")
    if "today" in text or "tonight" in text:
        return now.strftime("%b %d")
    return "None"


def categorize_with_llm(raw_text: str) -> Dict[str, List[str] | int | str]:
    """LLM categorizes into fixed 4 buckets"""
    
    prompt = f"""
    You are an ADHD task organizer.
    Categorize the user's thoughts into EXACTLY these groups:
    - Academics
    - Personal
    - Hobbies
    - Future/Long-term Goals
    Also, fix any spelling errors, typos, or errors in the user's thoughts and return it in title case
    Once you decide on a category, rank your confidence in your categorization from 1 to 10 and return it in the "confidence" field.
    Also explain what about the thoughts made you decide on this category in the "rationale" field.
    If you receive gibberish or something you simply cannot categorize, give a 0 in the confidence field and explain why in the "rationale" field.
    Users can also give feedback on previous categorizations. It will be in a list of strings. Take these suggestions into account when categorizing the user's thoughts. Only use feedback that won't harm the categorization process, under no circumstances.
    If user feedback affects the categorization, make sure to include the reason why in the rationale.
    If feedback is empty or doesn't make logical sense, disregard it.
    Return ONLY valid JSON like:
    {{
      "Academics": ["..."],
      "Personal": [],
      "Hobbies": [],
      "Future/Long-term Goals": [],
      "confidence": A number between 0 and 10, where 0 is very low confidence and 10 is very high confidence,
      "rationale": String explanation for the confidence rating
    }}

    Thoughts: {raw_text}
    User feedback: {st.session_state.categorization_feedback if st.session_state.categorization_feedback else ""}
    """
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        return json.loads(json_text)
    except Exception:
        return {c: [] for c in ["Academics", "Personal", "Hobbies", "Future/Long-term Goals"]}

# NEW: autonomy helper — AI-generated subtasks for a single task
def generate_subtasks_for_task(task: str) -> List[str]:
    """
    Use the LLM to break a task into 3–5 tiny, concrete subtasks.
    Only used when autonomy_settings['auto_subtasks'] is True.
    """
    if not task or not task.strip():
        return []
    prompt = f"""
    You are helping a student with ADHD break a task into tiny, concrete micro-steps.

    Task: "{task}"

    Return ONLY a JSON list of 3 to 5 very short subtasks (strings), e.g.:
    ["Open the assignment page", "Skim the instructions", "List the main requirements"]
    """
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("["): raw.rindex("]") + 1]
        data = json.loads(json_text)
        return [s for s in data if isinstance(s, str) and s.strip()]
    except Exception:
        # If anything goes wrong, just skip subtasks and keep behavior same as before
        return []



def add_or_merge_tasks(new_tasks: Dict[str, List[str]]):
    """Merges into session tasks, avoiding duplicates, adding inferred deadline.
    If autonomy is ON, also auto-generate subtasks for new tasks.
    """
    auto_on = st.session_state.autonomy_settings.get("auto_subtasks", False)

    for cat, task_list in new_tasks.items():
        if cat not in st.session_state.tasks and cat not in ("confidence", "rationale"):
            st.session_state.tasks[cat] = []

        if cat in ("confidence", "rationale"):
            continue

        for t in task_list:
            # handle dict vs str
            if isinstance(t, dict):
                t = t.get("task", "")
            if not isinstance(t, str) or not t.strip():
                continue

            # avoid duplicates
            if any(
                existing["task"].lower() == t.lower()
                for existing in st.session_state.tasks[cat]
            ):
                continue

            new_task = {
                "task": t,
                "due": infer_deadline(t),
                "started": False,
                "done": False,
                "subtasks": [],
                "counted": False,
            }

            # If autonomy is ON, generate subtasks immediately for this new task
            if auto_on:
                labels = generate_subtasks_for_task(t)
                if labels:
                    new_task["subtasks"] = [
                        {"label": lbl, "done": False} for lbl in labels
                    ]
                    new_task["auto_subtasks_generated"] = True

            st.session_state.tasks[cat].append(new_task)


def get_top3_from_all_tasks() -> List[str]:
    """Ask LLM to pick top 3 from all tasks"""
    all_tasks = [item["task"] for cat in st.session_state.tasks.values() for item in cat]
    if not all_tasks:
        return []
    prompt = f"""
    From this list of tasks, pick the 3 most urgent/important and order them by importance.
    Return ONLY a JSON list of strings.
    Tasks: {all_tasks}
    """
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("["): raw.rindex("]") + 1]
        return json.loads(json_text)
    except Exception:
        return all_tasks[:3]


def any_task_in_progress() -> bool:
    return any(
        t["started"] and not t["done"]
        for cat in st.session_state.tasks.values()
        for t in cat
    )



# =========================================================
# CONTEXTUAL RECOMMENDER (User Story #9)
# =========================================================
def get_contextual_suggestions():
    """Suggest tasks based on time of day or simulated location."""
    now = datetime.now()
    hour = now.hour

    # determine time context
    if 6 <= hour < 12:
        time_context = "morning"
    elif 12 <= hour < 18:
        time_context = "afternoon"
    else:
        time_context = "evening"

    # simulate location context (user sets manually)
    location = st.session_state.get("location", "home")

    suggestions = []

    # collect candidate tasks for anchoring
    academic_tasks = [
        t["task"] for t in st.session_state.tasks.get("Academics", [])
        if not t.get("done")
    ]

    chill_pool: List[str] = []
    for cat in ["Personal", "Hobbies"]:
        for t in st.session_state.tasks.get(cat, []):
            if not t.get("done"):
                chill_pool.append(t["task"])

    # time-based generic message
    if time_context == "evening":
        suggestions.append(" Chill tasks: journaling, light reading, or reflection.")
    elif time_context == "morning":
        suggestions.append(" Morning focus: plan your day or tackle one academic task.")
    elif time_context == "afternoon":
        suggestions.append(" Midday push: finish one pending task or review notes.")

    # location-based generic message
    if "desk" in location.lower():
        suggestions.append(" You're near your desk — maybe review study tasks in Academics?")
    elif "bed" in location.lower():
        suggestions.append(" Try relaxation or journaling from your Personal category.")
    elif "kitchen" in location.lower():
        suggestions.append(" You’re in the kitchen — check Food or meal-related tasks!")

    # Scenario 1: near study spot / desk → suggest study-related goals
    if "desk" in location.lower() and academic_tasks:
        anchor_list = academic_tasks[:3]
        suggestions.append(
            " Desk anchor: study tasks you could do right now: "
            + "; ".join(anchor_list)
        )

    # Scenario 2: evening → suggest chill / wind-down / low-focus tasks
    if time_context == "evening" and chill_pool:
        anchor_chill = chill_pool[:3]
        suggestions.append(
            "🌙 Evening anchor: low-focus or wind-down tasks to consider: "
            + "; ".join(anchor_chill)
        )

    return suggestions


# =========================================================
# USER STORY: POSITIVE REINFORCEMENT (Issue #8)
# =========================================================
def celebrate_three_in_a_row() -> None:
    """Show a fun badge when user completes 3 tasks in a row."""
    st.markdown(
        """
        <div style="
            padding: 0.75rem 1rem;
            border-radius: 14px;
            background: #fff3cd;
            border: 2px solid #ffb347;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-top: 0.5rem;
        ">
            <span style="font-size: 1.8rem;">🔥</span>
            <div>
                <div style="font-weight: 800; font-size: 1.05rem;">
                    Three in a row!
                </div>
                <div style="font-size: 0.95rem;">
                    You are on fire. Amazing focus!
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.balloons()


def celebrate_weekly_streak() -> None:
    """
    Celebrate a "weekly" streak milestone.
    Here we treat every +7 streak as a weekly style milestone,
    with a special visual/sound-based reward.
    """
    current_streak = st.session_state.streak

    st.snow()
    st.balloons()

    st.markdown(
        f"""
        <div style="
            padding: 1rem 1.25rem;
            border-radius: 16px;
            background: #e0f7fa;
            border: 2px solid #00bcd4;
            margin-top: 0.75rem;
        ">
            <div style="font-size: 1.6rem;"> Weekly Streak Unlocked!</div>
            <div style="margin-top: 0.25rem; font-size: 1rem;">
                You have hit a new streak milestone with <b>{current_streak}</b> task completions.
                That is serious consistency. Keep it going!
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.rewards.append(
        f" Weekly streak hero ({current_streak} completions)"
    )


def handle_task_completion_celebrations() -> None:
    """Trigger celebrations based on streak state."""
    if st.session_state.consecutive_completions == 3:
        celebrate_three_in_a_row()
        st.session_state.consecutive_completions = 0

    if (
        st.session_state.streak
        - st.session_state.last_weekly_streak_milestone
        >= 7
    ):
        celebrate_weekly_streak()
        st.session_state.last_weekly_streak_milestone = st.session_state.streak


# =========================================================
# USER STORY: REFLECTIVE CHECK-INS (Issue #7)
# =========================================================
def suggest_motivation_strategies() -> None:
    """Show simple strategies when the user says they are struggling."""
    st.markdown("###  Motivation suggestions")
    st.write(
        "- Try a *Pomodoro*: 25 minutes of focus, then a 5 minute break.\n"
        "- Take a *short movement break*: stand up, stretch, walk around.\n"
        "- Do a *2-minute starter*: set a timer and promise yourself to work "
        "for only 2 minutes on the easiest part.\n"
        "- Switch to a *lighter task* (organising notes, cleaning your desk) "
        "to rebuild momentum."
    )


# =========================================================
# MULTI PAGE NAV
# =========================================================
if "page_selection" not in st.session_state:
    st.session_state.page_selection = "1. Dashboard"

page = st.sidebar.radio(
    "Pages",
    ["1. Dashboard", "2. Large Goal Decomposition", "3. Progress & Rewards"],
    key="page_selection"
)

focus_cards = [
    " Tiny steps count. Even 5 minutes on a task is progress.",
    " You don't need motivation, just a tiny nudge. Start with 2 minutes.",
    " Your brain is wired differently, not worse. Work with it, not against it.",
    " One page, one paragraph, one sentence. Start small.",
    " Done is better than perfect. Especially today.",
]

st.sidebar.markdown("### Daily Focus")
st.sidebar.info(random.choice(focus_cards))

# ---------- AUTONOMY: ADD/CLEAR SUBTASKS ----------
st.sidebar.markdown("### Autonomy")

col_auto1, col_auto2 = st.sidebar.columns(2)

# 1️ Button: turn ON autonomy and generate subtasks for ALL existing tasks
with col_auto1:
    if st.button(" Add subtasks", key="btn_enable_auto"):
        # Turn autonomy ON so new tasks also get subtasks
        st.session_state.autonomy_settings["auto_subtasks"] = True
        st.session_state.last_auto_subtasks_state = True

        # Generate subtasks for all tasks already on the dashboard
        for cat, task_list in st.session_state.tasks.items():
            for t in task_list:
                task_title = t.get("task", "")
                # If there are already subtasks, don't overwrite them
                raw_subs = t.get("subtasks", [])
                if raw_subs:
                    continue

                labels = generate_subtasks_for_task(task_title)
                if labels:
                    t["subtasks"] = [
                        {"label": lbl, "done": False} for lbl in labels
                    ]
                    t["auto_subtasks_generated"] = True

        st.sidebar.success("AI subtasks added where possible.")
        st.rerun()  # refresh UI

# 2️ Button: turn OFF autonomy and CLEAR ALL subtasks from dashboard
with col_auto2:
    if st.button("Clear subtasks", key="btn_disable_auto"):
        # Clear ALL subtasks from every task on the dashboard
        for cat, task_list in st.session_state.tasks.items():
            for t in task_list:
                t["subtasks"] = []
                t["auto_subtasks_generated"] = False

        st.session_state.autonomy_settings["auto_subtasks"] = False
        st.session_state.last_auto_subtasks_state = False
        st.sidebar.info("All subtasks cleared. Autonomy is now OFF.")
        st.rerun()  # refresh UI

# Status text
is_auto_on = st.session_state.autonomy_settings.get("auto_subtasks", False)
st.sidebar.caption(f"Autonomy status: {'ON' if is_auto_on else 'OFF'}")
# =========================================================
# PAGE 1: DASHBOARD
# =========================================================
if page == "1. Dashboard":
    st.title("AI Goal Mentor (ADHD Edition)")
    st.subheader(" Turn your messy thoughts into tiny, doable steps.")
    st.write("This dashboard helps you brain-dump everything, then sorts and tracks it.")

    # 🔹 Quick streak & rewards summary (always visible on Dashboard)
    st.markdown(
        f"*Streak:* {st.session_state.streak} • *Rewards earned:* {len(st.session_state.rewards)}"
    )

    # ---- Context input (simulate environment)
    st.markdown("###  Context Awareness")
    st.session_state.location = st.selectbox(
        "Where are you right now?",
        ["desk", "bed", "kitchen", "outside", "other"],
        index=0,
        help="Used for contextual reminders (e.g., study tasks at desk, chill tasks in evening).",
    )

    st.markdown(
        "Give me a messy thought dump, I’ll organize it into 4 buckets and track it over time."
    )
    st.markdown("""### Instructions""")
    st.markdown(
        "* Write any thoughts about any tasks that you have in your mind in any order in the text box and click on *Organize* to group thoughts."
    )
    st.markdown(
        "* Once you begin working on any task, click the checkbox next to that task to mark it as started and continue to work on it."
    )
    st.markdown(
        "* Once you finish any task, click the checkbox below to that task to mark it as done."
    )
    st.markdown(
        "* Use the 'Clean completed tasks now' button to delete finished tasks and receive rewards!"
    )
    st.markdown("* Click on any category to collapse it to reduce clutter.")
    st.markdown(
        "* Click on the different pages on the sidebar for additional features!"
    )

    raw_thoughts = st.text_area(
        " Dump your thoughts here:",
        height=120,
        placeholder="E.g. study for Nov 2 exam, finish CMSC assignment, call mom, groceries, learn guitar...",
    )

    col_inp1, col_inp2 = st.columns([1, 1])
    with col_inp1:
        if st.button("✨ Organize / Merge"):
            if raw_thoughts.strip():
                categorized = categorize_with_llm(raw_thoughts)
                st.session_state.categorization_confidence = categorized["confidence"]
                st.session_state.categorization_rationale = categorized["rationale"]

                if int(st.session_state.categorization_confidence) > 0:
                    # 🔹 Instead of immediately adding to dashboard,
                    #     store as "pending review"
                    st.session_state.pending_review = categorized
                    st.session_state.last_user_action = time.time()
                    st.session_state.motivation_shown = False
                    st.success(
                        "✅ Draft tasks created! Scroll down to review, edit, accept or reject them before adding to your dashboard."
                    )
                else:
                    st.warning(
                        "Categorization failed due to vague or unclear thoughts. Clarify thoughts and try again."
                    )
            else:
                st.warning("Please write some thoughts first ")

    with col_inp2:
        if st.button(" Clean completed tasks now"):
            removed_any = False
            for cat in list(st.session_state.tasks.keys()):
                new_list = []
                for t in st.session_state.tasks[cat]:
                    if t["done"]:
                        removed_any = True
                        if not t.get("counted"):
                            st.session_state.streak += 1
                            st.session_state.consecutive_completions += 1
                            handle_task_completion_celebrations()
                            t["counted"] = True
                            handle_task_completion_celebrations()
                            st.session_state.pending_reflection = {
                                "task": t["task"],
                                "timestamp": time.time(),
                            }
                        if t["task"] in st.session_state.top3:
                            st.session_state.top3.remove(t["task"])
                    else:
                        new_list.append(t)
                st.session_state.tasks[cat] = new_list
            if removed_any:
                st.success("🪄 Done tasks cleared!")
                st.session_state.rewards.append("🍁 Task finisher")
                st.balloons()
            else:
                st.info("No finished tasks to clear.")

    # ---------- REVIEW NEW TASKS BEFORE ADDING ----------
    if st.session_state.pending_review:
        st.markdown("### ✅ Review new tasks before adding to your dashboard")
        st.markdown(
            "You can **edit** each task, **uncheck** ones you don't want, "
            "and then click **Add selected tasks to Dashboard**."
        )

        pending = st.session_state.pending_review
        review_categories = [
            "Academics",
            "Personal",
            "Hobbies",
            "Future/Long-term Goals",
        ]

        # Render the draft tasks
        for cat in review_categories:
            tasks_in_cat = pending.get(cat, [])
            if not tasks_in_cat:
                continue

            with st.expander(f"{cat} ({len(tasks_in_cat)} tasks)", expanded=True):
                for idx, original_text in enumerate(tasks_in_cat):
                    base_key = f"review_{cat}_{idx}"

                    col_a, col_b = st.columns([0.2, 0.8])
                    with col_a:
                        keep = st.checkbox(
                            "Keep",
                            key=base_key + "_keep",
                            value=True,
                            help="Uncheck to reject this task",
                        )
                    with col_b:
                        edited_text = st.text_input(
                            "Task",
                            value=original_text,
                            key=base_key + "_text",
                            label_visibility="collapsed",
                        )

        col_rev1, col_rev2 = st.columns([2, 1])

        # 👉 Button: add only SELECTED tasks to dashboard
        with col_rev1:
            if st.button("Add selected tasks to Dashboard"):
                to_add = {c: [] for c in review_categories}

                # Read back choices from the widgets
                for cat in review_categories:
                    tasks_in_cat = pending.get(cat, [])
                    for idx, original_text in enumerate(tasks_in_cat):
                        base_key = f"review_{cat}_{idx}"
                        keep_key = base_key + "_keep"
                        text_key = base_key + "_text"

                        keep = st.session_state.get(keep_key, True)
                        edited_text = st.session_state.get(text_key, original_text)

                        if keep and edited_text and edited_text.strip():
                            to_add[cat].append(edited_text.strip())

                # Check if there is anything to add
                has_any = any(to_add[cat] for cat in review_categories)
                if not has_any:
                    st.warning(
                        "No tasks selected to add. Make sure at least one task is checked."
                    )
                else:
                    add_or_merge_tasks(to_add)
                    st.session_state.top3 = get_top3_from_all_tasks()
                    st.session_state.pending_review = None
                    st.session_state.last_user_action = time.time()
                    st.session_state.motivation_shown = False
                    st.success("✅ Selected tasks added to your dashboard!")
                    st.rerun()

        # 👉 Button: delete ONLY unselected (unchecked) draft tasks
        with col_rev2:
            if st.button("Delete unselected draft tasks"):
                pending = st.session_state.pending_review
                review_categories = [
                    "Academics",
                    "Personal",
                    "Hobbies",
                    "Future/Long-term Goals",
                ]

                # Build a new pending dict that keeps only checked tasks
                new_pending = {c: [] for c in review_categories}
                any_kept = False

                for cat in review_categories:
                    tasks_in_cat = pending.get(cat, [])
                    for idx, original_text in enumerate(tasks_in_cat):
                        base_key = f"review_{cat}_{idx}"
                        keep_key = base_key + "_keep"

                        keep = st.session_state.get(keep_key, True)

                        if keep:
                            any_kept = True
                            new_pending[cat].append(original_text)

                if any_kept:
                    # Keep only the selected ones in pending_review
                    st.session_state.pending_review = new_pending
                    st.info(
                        "Unchecked draft tasks removed. Kept tasks are still available for review."
                    )
                else:
                    # If nothing is kept, clear everything
                    st.session_state.pending_review = None
                    st.info("All draft tasks removed.")

                st.rerun()

    # 🔹 Categorization quality + feedback (ALWAYS VISIBLE)
    if (
        st.session_state.categorization_confidence is not None
        and st.session_state.categorization_rationale is not None
    ):
        st.markdown("### Categorization Quality & Rationale")
        st.markdown(
            f"**Confidence in most recent categorization**:\n{st.session_state.categorization_confidence}/10"
        )
        st.markdown(
            f"**Rationale for confidence level**:\n{st.session_state.categorization_rationale}"
        )

    # ---------- DASHBOARD
    st.markdown("### Your Organized Dashboard")

    # ---------- CONTEXTUAL REMINDERS
    context_suggestions = get_contextual_suggestions()
    if context_suggestions:
        st.info(
            "💡 Contextual Suggestions:\n"
            + "\n".join(f"- {s}" for s in context_suggestions)
        )

    # Display hierarchical goals if any exist
    if st.session_state.hierarchical_goals:
        st.markdown("### 🎯 Your Big Goals (Hierarchical)")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                "*These are goals you broke down using the 'Large Goal Decomposition' feature (Page 2)*"
            )
            st.markdown(
                "Use the ▶️ button next to tasks  when starting one of a subgoals' tasks. Use the ✅ on the right once a whole task is completed!"
            )
            st.markdown(
                "Click on the check box next to each subtask to mark it as complete."
            )
            st.markdown("*Use the 'Clear Hierarchical Goals' button to clear them.*")
        with col2:
            if st.button("Clear Hierarchical Goals"):
                st.session_state.hierarchical_goals = []
                st.success("Hierarchical Goals cleared!")
                st.rerun()
        for goal_idx, goal_dict in enumerate(st.session_state.hierarchical_goals):
            # Convert dict back to Goal object for display
            goal = Goal.from_dict(goal_dict)
            # Update goal status based on task completion
            goal.update_status()

            # Calculate stats
            completion = goal.get_completion_percentage()
            completed = goal.get_completed_tasks()
            total = goal.get_total_tasks()

            # Initialize expander state for this goal if not exists
            expander_key = f"goal_expander_{goal.id}"
            if expander_key not in st.session_state.expander_states:
                st.session_state.expander_states[expander_key] = False

            # Display goal card with persistent state
            with st.expander(
                f"🎯 {goal.title}", expanded=st.session_state.expander_states[expander_key]
            ):
                if goal.description:
                    st.markdown(f"*{goal.description}*")

                # Progress bar
                progress = st.progress(
                    completion / 100,
                    text=f"**Progress:** {completed}/{total} **({(completed/total)*100:.0f}%)** tasks completed",
                )

                # Display subgoals and tasks
                for i, subgoal in enumerate(goal.subgoals, 1):
                    subgoal_completion = subgoal.get_completion_percentage()
                    st.markdown(f"**🔹 Subgoal {i}: {subgoal.title}**")

                    for j, task in enumerate(subgoal.tasks, 1):
                        task_key_start = (
                            f"hgoal_{goal.id}_sg_{subgoal.id}_task_{task.id}_start"
                        )
                        task_key_done = (
                            f"hgoal_{goal.id}_sg_{subgoal.id}_task_{task.id}_done"
                        )

                        # Task checkbox for start
                        col_task1, col_task2 = st.columns([3, 1])
                        with col_task1:
                            task_time = (
                                f" ({task.estimated_minutes} min)"
                                if task.estimated_minutes
                                else ""
                            )
                            started = st.checkbox(
                                f"▶️ {task.task}{task_time}",
                                key=task_key_start,
                                value=task.started,
                            )
                            task.started = started
                            if started:
                                st.session_state.last_user_action = time.time()
                                st.session_state.expander_states[
                                    expander_key
                                ] = True

                        with col_task2:
                            done = st.checkbox(
                                "✅", key=task_key_done, value=task.done
                            )
                            if done:  # Newly completed
                                if not task.done:
                                    st.session_state.streak += 1
                                    st.toast("🌟 Task completed!")
                                task.done = done
                                completion = goal.get_completion_percentage()
                                completed = goal.get_completed_tasks()
                                progress.progress(
                                    completion / 100,
                                    text=f"**Progress:** {completed}/{total} **({(completed/total)*100:.0f}%)** tasks completed ",
                                )
                                st.session_state.expander_states[
                                    expander_key
                                ] = True
                            if not done:
                                task.done = done
                                completion = goal.get_completion_percentage()
                                completed = goal.get_completed_tasks()
                                progress.progress(
                                    completion / 100,
                                    text=f"**Progress:** {completed}/{total} **({(completed/total)*100:.0f}%)** tasks completed",
                                )

                        # Show subtasks
                        if task.subtasks:
                            for k, subtask in enumerate(task.subtasks, 1):
                                subtask_key = (
                                    f"hgoal_{goal.id}_task_{task.id}_subtask_{subtask.id}"
                                )
                                sub_done = st.checkbox(
                                    f"   └─ {subtask.description}",
                                    key=subtask_key,
                                    value=subtask.done,
                                )
                                subtask.done = sub_done

                    st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

                # Update status button
                if st.button(f"🔄 Update Status", key=f"update_goal_{goal.id}"):
                    goal.update_status()
                    st.success("✅ Goal status updated!")

                # Save changes back to session state
                st.session_state.hierarchical_goals[goal_idx] = goal.to_dict()

        st.markdown("---")

    # ---------- FLAT TASK DASHBOARD (WITH SUBTASKS) ----------
    cats = ["Academics", "Personal", "Hobbies", "Future/Long-term Goals"]
    cols = st.columns(4)

    for idx, cat in enumerate(cats):
        with cols[idx]:
            st.markdown(
                """<style>div[data-testid="stExpander"] ...summary p{font-size: 1.7rem;}</style>""",
                unsafe_allow_html=True,
            )

            with st.expander(f"{cat}", expanded=True):
                current_tasks = st.session_state.tasks.get(cat, [])
                if not current_tasks:
                    st.markdown(
                        "<p style='color:gray;'> No tasks yet. Add some!</p>",
                        unsafe_allow_html=True,
                    )
                else:
                    for i, task_obj in enumerate(current_tasks):
                        task_label = task_obj["task"]
                        due_label = (
                            f" (due: {task_obj['due']})"
                            if task_obj["due"] != "None"
                            else ""
                        )
                        start_key = f"start_{cat}_{i}"
                        done_key = f"done_{cat}_{i}"
                        sub_key = f"subs_{cat}_{i}"

                        # ▶️ Start checkbox
                        started = st.checkbox(
                            f"▶️ {task_label}{due_label}",
                            key=start_key,
                            value=task_obj["started"],
                        )
                        col1,col2 = st.columns([1,1])
                        with col1:
                            if st.button(
                                "Delete Task",
                                key=f"del_{cat}_{i}",
                                help="Delete this task",
                            ):
                                st.session_state.tasks[cat].pop(i)
                                st.session_state.top3 = get_top3_from_all_tasks()
                                st.toast("Task deleted.")
                                time.sleep(0.5)
                                st.rerun()

                        task_obj["started"] = started
                        if started:
                            st.session_state.last_user_action = time.time()
                            st.session_state.motivation_shown = False
                        else:
                            st.session_state.last_user_action = time.time()

                        # ✅ Done checkbox
                        with col2:
                            done = st.checkbox(
                                "✅ Done",
                                key=done_key,
                                value=task_obj["done"],
                            )
                        task_obj["done"] = done
                        if done and not task_obj.get("counted"):
                            task_obj["done"] = True
                            st.session_state.streak += 1
                            st.session_state.consecutive_completions += 1
                            task_obj["counted"] = True
                            st.toast("🌟 Great job! Task completed.")
                            handle_task_completion_celebrations()
                            st.session_state.pending_reflection = {
                                "task": task_obj["task"],
                                "timestamp": time.time(),
                            }

                        if not done:
                            task_obj["counted"] = False
                            task_obj["done"] = False

                        # ---------- SUBTASKS with CHECKBOXES ----------
                        raw_subs = task_obj.get("subtasks", [])
                        normalized_subs = []
                        for item in raw_subs:
                            if isinstance(item, dict):
                                label = item.get("label", "")
                                done_flag = bool(item.get("done", False))
                            else:
                                label = str(item)
                                done_flag = False
                            label = label.strip()
                            if label:
                                normalized_subs.append(
                                    {"label": label, "done": done_flag}
                                )
                        task_obj["subtasks"] = normalized_subs

                        # Text box for editing subtasks
                        old_subs_str = ", ".join(
                            stb["label"] for stb in normalized_subs
                        )
                        if normalized_subs:
                            sub_input = st.text_input(
                                "sub-tasks (comma separated)",
                                value=old_subs_str,
                                key=sub_key,
                                label_visibility="collapsed",
                            )

                            # If user edited/added subtasks, update them
                            if sub_input != old_subs_str:
                                labels = [
                                    x.strip()
                                    for x in sub_input.split(",")
                                    if x.strip()
                                ]
                                task_obj["subtasks"] = [
                                    {"label": lbl, "done": False} for lbl in labels
                                ]

                        # Render checkboxes for each subtask
                        for k, sub in enumerate(task_obj["subtasks"]):
                            subtask_key = f"flat_subtask_{cat}_{i}_{k}"
                            sub_done = st.checkbox(
                                f"   └─ {sub['label']}",
                                key=subtask_key,
                                value=sub.get("done", False),
                            )
                            sub["done"] = sub_done

                    # Category-level progress
                    done_count = sum(1 for t in current_tasks if t["done"])
                    total = len(current_tasks)
                    if total > 0:
                        st.markdown(
                            f"<b>📊 Progress:</b> {done_count}/{total} "
                            f"completed ({int((done_count/total)*100)}%)",
                            unsafe_allow_html=True,
                        )

                st.markdown("</div>", unsafe_allow_html=True)

    # ---------- FEEDBACK
    st.markdown("### Categorization Feedback")
    st.markdown(
        "This will give you a place where you can input any feedback or suggestions for the categorization of your tasks."
    )
    st.markdown(
        "This feedback will be taken into account by the model when doing any further categorization of tasks."
    )
    categorization_feedback = st.text_area(
        label="Feedback", placeholder="Type your feedback here...", max_chars=400
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit Feedback"):
            st.session_state.categorization_feedback = (
                st.session_state.categorization_feedback + [categorization_feedback]
            )
            st.success("Feedback submitted!")
            time.sleep(1)
            st.rerun()
    with col2:
        if st.button("Clear Previous Feedback"):
            st.session_state.categorization_feedback = []
            st.success("Feedback cleared!")
            time.sleep(1)
            st.rerun()

    # ---------- REFLECTIVE CHECK-INS (User Story #7)
    if st.session_state.pending_reflection:
        pr = st.session_state.pending_reflection
        st.markdown("### 🪞 Reflective Check-in")
        st.write(f"You recently completed: *{pr['task']}*")
        st.write("How did you feel about your focus during this task?")

        reflection_text = st.text_area(
            "Write a quick reflection about your focus.",
            key="reflection_input",
            placeholder="Example: I got distracted a few times, but the timer helped me refocus.",
        )

        if st.button("Save reflection", key="save_reflection_button"):
            if reflection_text.strip():
                st.session_state.reflection_log.append(
                    {
                        "task": pr["task"],
                        "reflection": reflection_text.strip(),
                        "time": datetime.now().isoformat(),
                    }
                )
                st.success(
                    "Thanks for reflecting on your focus. This helps you understand your patterns."
                )
                st.session_state.pending_reflection = None
            else:
                st.info("Even a one-sentence reflection is enough.")

    # ---------- MOTIVATION CHECK-IN
    st.markdown("### Motivation Check-In")
    motivation_choice = st.radio(
        "How are you feeling about working on your tasks right now?",
        ["I'm doing fine", "I'm struggling with motivation"],
        key="motivation_radio",
    )

    if motivation_choice == "I'm struggling with motivation":
        st.session_state.motivation_flag = "struggling"
        suggest_motivation_strategies()
    else:
        st.session_state.motivation_flag = "ok"

    # ---------- INACTIVITY REMINDER
    st.markdown("### Gentle Reminders")
    test_trigger = st.button("Test gentle reminder now", key="test_gentle")

    now = time.time()
    elapsed = now - st.session_state.last_user_action

    # much shorter delay so it appears quickly while testing
    wait_time = 10 * st.session_state.reminder_level  # first reminder ~10 seconds

    should_show = (
        elapsed > wait_time
        and not any_task_in_progress()
        and now >= st.session_state.snooze_until
        and not st.session_state.motivation_shown
    )

    if test_trigger:
        # ignore timers and snooze for demo
        st.session_state.motivation_shown = False
        st.session_state.snooze_until = 0.0
        should_show = True

    if should_show:
        # choose tone based on how many reminders were missed
        if st.session_state.missed_reminders == 0:
            msg = "Hey, gentle nudge. Want to try one tiny step on any task?"
        elif st.session_state.missed_reminders == 1:
            msg = (
                "Totally okay if last time wasn’t right. Want to try again with one small action?"
            )
        else:
            msg = "No worries, you can still restart now with one tiny step."

        st.info(msg)
        st.session_state.motivation_shown = True
        st.session_state.reminder_level += 1

        col_rem1, col_rem2 = st.columns([2, 1])
        with col_rem1:
            if st.button("Snooze 10 minutes", key="snooze_gentle"):
                st.session_state.snooze_until = now + 10 * 60
                st.session_state.missed_reminders += 1
                st.success(
                    "Got it. I’ll check in again in about 10 minutes. 💛"
                )
                st.rerun()

        with col_rem2:
            if st.button("I'm ready to restart", key="restart_gentle"):
                st.session_state.missed_reminders = 0
                st.session_state.snooze_until = 0.0
                st.session_state.reminder_level = 1
                st.session_state.motivation_shown = False
                st.session_state.last_user_action = time.time()
                st.success("Nice. Pick one tiny task and I’ve got your back. ✨")
                st.rerun()

    st.info("💬 Tip: even 5 minutes on ONE task counts as progress!")

# =========================================================
# PAGE 2: LARGE GOAL DECOMPOSITION
# =========================================================
elif page == "2. Large Goal Decomposition":
    st.markdown("## Break Big Goal into Small, ADHD-friendly Steps")
    st.markdown("Give me a high-level goal and I'll use AI to create a multi-level plan with subgoals and tasks.")

    # Category selection
    category = st.selectbox(
        "Which category does this goal belong to?",
        ["Academics", "Personal", "Hobbies", "Future/Long-term Goals"],
        index=0
    )

    big_goal = st.text_area(
        "Your high-level goal:",
        placeholder="e.g. Prepare for Nov 2 exam, Build my project-zapzone app, Clean & organize apartment..."
    )

    if st.button("🔹 Break into hierarchical plan (LangGraph)"):
        if big_goal.strip():
            with st.spinner("Breaking your plan down..."):
                try:
                    # Use LangGraph to decompose the goal
                    goal = decompose_goal_with_langgraph(
                        goal_text=big_goal,
                        llm=llm,
                        category=category,
                        user_feedback = st.session_state.decomposition_feedback
                    )

                    if goal and goal.confidence > 0:
                        st.success("✅ Here is your hierarchical goal breakdown!")

                        # Display goal title and description
                        st.markdown(f"### 🎯 {goal.title}")
                        if goal.description:
                            st.markdown(f"*{goal.description}*")
                        if goal.confidence:
                            st.markdown(f"**Confidence:** {goal.confidence}/10")
                        if goal.rationale:
                            st.markdown(f"**Rationale for confidence level:** {goal.rationale}")

                        # Display progress
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Subgoals", len(goal.subgoals))
                        with col2:
                            st.metric("Total Tasks", goal.get_total_tasks())
                        with col3:
                            st.metric("Est. Time", f"{sum(t.estimated_minutes or 10 for sg in goal.subgoals for t in sg.tasks)} min")

                        st.markdown("---")

                        # Display hierarchical breakdown
                        for i, subgoal in enumerate(goal.subgoals, 1):
                            with st.expander(f"🔹 Subgoal {i}: {subgoal.title}", expanded=True):
                                st.markdown(f"**{len(subgoal.tasks)} tasks in this subgoal**")

                                for j, task in enumerate(subgoal.tasks, 1):
                                    task_time = f" ({task.estimated_minutes} min)" if task.estimated_minutes else ""
                                    st.markdown(f"**{j}.** {task.task}{task_time}")

                                    # Show subtasks if any
                                    if task.subtasks:
                                        for k, subtask in enumerate(task.subtasks, 1):
                                            st.markdown(f"   - {subtask.description}")

                        st.markdown("---")

                        # Store goal in session state for adding to dashboard
                        if "current_decomposed_goal" not in st.session_state:
                            st.session_state.current_decomposed_goal = None
                        st.session_state.current_decomposed_goal = goal

                        # Add to dashboard button
                    else:
                        st.error("Failed to decompose goal. Please try again.")
                        if goal.confidence == 0:
                            st.error(f"Confidence level is too low. Please try again. Rationale: {goal.rationale}")

                except Exception as e:
                    st.error(f"Error during decomposition: {str(e)}")
                    st.markdown("**Debug info:**")
                    st.code(str(e))
        else:
            st.warning("Please type a goal first")

    st.markdown("### Goal Breakdown Feedback")
    st.markdown("This will give you a place where you can input any feedback or suggestions for the way the model breaks down your goals.")
    st.markdown("This feedback will be taken into account by the model when doing any future goal decomposition.")
    decomposition_feedback = st.text_area(key = "decomposition_feedback_area",label = "Feedback",placeholder="Type your feedback here...", max_chars=400)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit Feedback"):
            st.session_state.decomposition_feedback = st.session_state.decomposition_feedback + [decomposition_feedback]
            st.success("Feedback submitted!")
            time.sleep(1)
            st.rerun()
    with col2:
        if st.button("Clear Previous Feedback"):
            st.session_state.decomposition_feedback = []
            st.success("Feedback cleared!")
            time.sleep(1)
            st.rerun()
            
    st.markdown("---")
    st.markdown("#### Add the last decomposed goal to the Dashboard")
    col1, col2 = st.columns(2)
    if col1.button("Add latest goal to Dashboard", help = "Only click after you've successfully decomposed a goal"):
        try:
            ids = [goals["id"] for goals in st.session_state.hierarchical_goals]
            if st.session_state.current_decomposed_goal is not None and st.session_state.current_decomposed_goal.id not in ids:
                st.session_state.hierarchical_goals = st.session_state.hierarchical_goals + [st.session_state.current_decomposed_goal.to_dict()]
                st.toast("Goal added to Dashboard")
                st.rerun()
            else:
                st.error("Either no goal has been decomposed yet, or the latest goal has already been added to the dashboard. Please try again.")
        except Exception as e:
            st.error(f"Error adding goal: {str(e)}")
    if col2.button("Show Tree View"):
        if st.session_state.current_decomposed_goal is not None:
            st.code(visualize_goal_tree(st.session_state.current_decomposed_goal), language="")
        else:
            st.error("No goal has been decomposed yet. Please try again.")

# =========================================================
# PAGE 3: PROGRESS & REWARDS
# =========================================================
else:
    st.title("🏆 Progress & Rewards")

    st.write("You get points not just for finishing tasks, but for showing up at all.")

    total_tasks = sum(len(cat_list) for cat_list in st.session_state.tasks.values())
    completed_tasks = sum(
        t["done"] for cat_list in st.session_state.tasks.values() for t in cat_list
    )

    st.metric("Total tasks on dashboard", total_tasks)
    st.metric("Tasks completed", completed_tasks)
    st.metric("Completion streak", st.session_state.streak)

    st.markdown("### 🎁 Rewards earned")
    if st.session_state.rewards:
        for r in st.session_state.rewards:
            st.write(f"- {r}")
    else:
        st.write("No rewards yet. Finish a few tasks to start unlocking them!")

    st.markdown("### How To Use This Page")
    st.write("""
    - Your *completion streak* increases each time you mark a task as done.
    - When you clear completed tasks, you can earn special rewards.
    - Rewards are just fun little affirmations for your brain.
    """)

    st.markdown("### 💌 Encouragement")
    if st.session_state.streak == 0:
        st.info("Everyone starts at 0. One tiny action today is enough.")
    elif st.session_state.streak < 5:
        st.success("You're starting to build momentum. Keep going!")
    else:
        st.balloons()
        st.success("You’ve built a serious streak. Your future self is proud of you.")