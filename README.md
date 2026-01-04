# AI Goal Mentor (ADHD Edition)

> "Don't fight your thoughts — let AI help you organize, reflect, and focus."

---

## Project Overview

**AI Goal Mentor** is an intelligent, web-based productivity application designed specifically for individuals with ADHD and those who face challenges with focus, motivation, and mental organization. Rather than enforcing rigid planning structures, this tool embraces thought spontaneity, allowing users to freely "dump" ideas, distractions, or tasks into the system.

The application leverages Google Gemini 2.5 Flash AI to automatically transform unstructured thoughts into organized, actionable task plans. It then maintains user engagement through reflective check-ins, motivation support, positive reinforcement, and gentle reminders, all while respecting user autonomy and providing transparent explanations for every AI decision.

**Core Philosophy:** This tool acts as a personal executive-function co-pilot, helping users plan, act, reflect, and grow — one focused session at a time, with full transparency about AI confidence and reasoning.

### Primary Objectives

- Simplify task management for people with ADHD or scattered thought patterns
- Reduce overwhelm by transforming chaos into clarity through AI-powered organization
- Build trust through transparent confidence indicators and explainable AI decisions
- Empower users with autonomy controls over AI behavior
- Encourage reflection to identify patterns that impact productivity
- Support users during motivation dips with actionable guidance
- Build sustainable productivity habits using positive reinforcement

---

## Trust, Predictability, and Autonomy Boundaries

This application prioritizes user trust and control through transparent AI decision-making and explicit autonomy boundaries.

### Visual Clues for Confidence and Uncertainty

The system provides clear indicators of AI confidence to help users make informed decisions:

**Confidence Scoring System:**
- All AI decisions (task categorization and goal decomposition) include a confidence score on a 0-10 scale
- Confidence ratings are displayed directly in the UI in "X/10" format
- Scores of 7-10 indicate high confidence in the AI's analysis
- Scores of 4-6 indicate moderate confidence with some assumptions made
- Scores of 0-3 indicate low confidence, suggesting the input may be too vague
- A confidence score of 0 triggers an explicit warning: "Categorization failed due to vague or unclear thoughts. Clarify thoughts and try again."

**Rationale Text:**
- Every AI decision includes a text explanation of the reasoning
- Rationale explains what aspects of the input influenced the categorization or decomposition
- When confidence is low, the rationale explicitly states what was unclear or ambiguous
- Users can reference these explanations to understand AI behavior and improve future inputs

**Visual Indicators in the Interface:**
- Progress bars showing task and goal completion percentages
- Status badges for task states (not started, in progress, completed)
- Checkboxes for subtask completion tracking
- Color-coded categories for different task types
- Expandable sections for hierarchical goal structures

### Explainability Features

**Transparent Decision-Making:**
- All task categorizations display both confidence score and rationale
- Goal decomposition shows confidence tracking at each level (goal, subgoal, task)
- Users can see exactly why the AI made specific choices
- Clear error messages provide actionable guidance when inputs are unclear

**User Review Before Acceptance:**
- Tasks are NOT automatically added to the dashboard
- After AI categorization, users see a review screen where they can:
  - Accept tasks (by keeping checkboxes selected)
  - Reject tasks (by unchecking boxes)
  - Edit individual task text before accepting
- This review workflow ensures users maintain control over what enters their task list

**Feedback Mechanism:**
- Users can provide feedback on past categorizations
- Feedback influences future AI behavior and improves accuracy
- The system acknowledges when user feedback affected a decision in the rationale

### Autonomy Level Control

Users have explicit control over when and how the AI generates content:

**Sidebar Toggle Controls:**
- "Add subtasks" button: Enables AI autonomy to auto-generate subtasks for ALL tasks
- "Clear subtasks" button: Disables autonomy and removes all auto-generated subtasks
- Status indicator displays current "Autonomy status: ON/OFF"

**Subtask Generation:**
- When autonomy is OFF (default): No automatic subtask generation
- When autonomy is ON: AI automatically breaks each task into 3-5 micro-steps
- Users can manually add, edit, or remove subtasks at any time regardless of autonomy setting
- Auto-generated subtasks are marked with metadata to distinguish them from manual entries

**No Auto-Acceptance:**
- The system NEVER automatically accepts AI suggestions without user approval
- All AI outputs require explicit user action (clicking accept, checking boxes, etc.)
- Users maintain final authority over their task list and goal structure

### Clarification for Vague Goals

**Vague Input Detection:**
- The system detects vague input through low confidence scores
- Single-word inputs like "Study" or "Jog" trigger low confidence ratings (typically 0-3)
- The AI explicitly notes in the rationale that assumptions had to be made

**Explicit Messaging:**
- When confidence is 0: "Categorization failed due to vague or unclear thoughts. Clarify thoughts and try again."
- When confidence is low (1-3): Rationale explains what additional detail would help
- Users receive actionable guidance on how to improve their input

**Category Selection Requirement:**
- For hierarchical goal decomposition, users must select a category before processing
- This provides context that helps the AI make better decisions
- Categories include: Academics, Personal, Hobbies, Future/Long-term Goals

**Feedback Loops:**
- Users can submit feedback about past categorizations
- This feedback trains the system to better understand user intent over time
- The system acknowledges in the rationale when user feedback influenced a decision

---

## Key Features

### 1. Dump and Organize Agent

The core feature that transforms unstructured thoughts into organized tasks.

**How It Works:**
- Users freely type their thoughts without worrying about structure or organization
- Google Gemini 2.5 Flash analyzes the raw text using natural language understanding
- AI categorizes tasks into four fixed buckets: Academics, Personal, Hobbies, Future/Long-term Goals
- Each categorization includes a confidence score (0-10) and detailed rationale
- Users can provide feedback on categorizations to improve future accuracy

**Review Screen Functionality:**
1. After categorization, users see a review screen with all suggested tasks
2. Each task has a checkbox (checked by default)
3. Users can:
   - Uncheck boxes to reject tasks
   - Click "Edit" to modify task text
   - Click "Accept" to add only checked tasks to dashboard
4. Only accepted tasks appear on the main dashboard

**Example:**

*Input:* "Finish report, call mom, revise notes, maybe learn guitar someday"

*AI Output:*
- Academics: "Finish Report", "Revise Notes" (Confidence: 8/10, Rationale: "Clear academic tasks with action verbs")
- Personal: "Call Mom" (Confidence: 9/10, Rationale: "Specific personal relationship task")
- Future/Long-term Goals: "Learn Guitar" (Confidence: 7/10, Rationale: "Exploratory language 'maybe someday' indicates long-term aspiration")

### 2. Hierarchical Goal Decomposition

Break down large, overwhelming goals into manageable hierarchical structures using LangGraph.

**LangGraph State Machine:**

The system uses a 4-node state machine to decompose goals:

1. **Parse Goal Node**: Extracts clear title and description from raw input, assigns initial confidence
2. **Decompose to Subgoals Node**: Breaks goal into 3-5 major components
3. **Generate Tasks Node**: Creates 5-7 actionable tasks per subgoal (loops for each subgoal)
4. **Finalize Node**: Assembles complete hierarchical Goal object with all metadata

**Hierarchical Structure:**
```
Goal (title, description, confidence, rationale, category)
  └── Subgoal (title, tasks, status, level)
      └── Task (task, due_date, started, done, estimated_minutes)
          └── Subtask (description, done status)
```

**Confidence Tracking at Each Level:**
- Initial confidence assigned during goal parsing
- Updated during subgoal decomposition if assumptions change
- Rationale annotated with node information showing where confidence changed
- Final confidence score represents overall certainty in the decomposition

**Time Estimates:**
- Each task includes an estimated_minutes field
- Helps users plan their day and set realistic expectations
- Aggregated time estimates shown at subgoal and goal levels

**Tree Visualization:**
- Optional tree view displays the entire hierarchy visually
- Expandable sections show goal → subgoals → tasks → subtasks
- Progress indicators at each level
- Helps users understand the full scope of their goal

### 3. Autonomy Control System

Explicit user control over AI-generated content.

**Sidebar Toggle Controls:**
- Located in the sidebar for easy access
- "Add subtasks" button: Enables AI to auto-generate subtasks for all tasks
- "Clear subtasks" button: Removes all auto-generated subtasks and disables autonomy
- Visual status indicator shows "Autonomy status: ON" or "Autonomy status: OFF"

**Auto-Subtask Generation (When Enabled):**
- AI breaks each task into 3-5 tiny, concrete micro-steps
- Designed for ADHD-friendly task breakdown
- Example: "Write essay" → ["Open assignment page", "Skim instructions", "List main requirements", "Create outline", "Write introduction"]
- Subtasks are marked with metadata to track their origin

**Manual Subtask Management:**
- Users can always manually add subtasks in comma-separated format
- Manual and auto-generated subtasks coexist
- Checkboxes track completion for both types
- Editing preserves manual subtasks while clearing only auto-generated ones

**Clear Visual Feedback:**
- Status indicator updates immediately when toggling autonomy
- Subtasks appear/disappear with clear animations
- Toast notifications confirm autonomy state changes

### 4. Reflective Check-ins

Post-task reflection prompts help users understand their focus patterns.

**How It Works:**
- After completing a task, the system displays: "You recently completed: [task name]"
- Reflective prompt appears: "How did you feel about your focus during this task?"
- Users write free-form reflections about their experience
- Reflections are logged with timestamps for pattern analysis

**Focus Pattern Tracking:**
- All reflections stored in session_state.reflection_log
- Includes task name, reflection text, and timestamp
- Data structure supports future analytics and trend visualization
- Users can identify what conditions support their best focus

**Example Reflections:**
- "Felt distracted at first, but music helped regain focus."
- "Breaking into chunks made it easier."
- "Short and satisfying task. Good momentum boost."

### 5. Motivation Support System

Context-aware motivation check-ins and suggested strategies.

**Motivation Check-in Prompts:**
- System asks: "How are you feeling about working on your tasks right now?"
- Two options: "I'm doing fine" or "I'm struggling with motivation"
- Non-intrusive design respects user mental state

**Suggested Strategies (When Struggling):**

1. **Pomodoro Technique**: 25 minutes of focus + 5-minute break
2. **Short Movement Break**: Stand, stretch, walk briefly to reset
3. **2-Minute Starter**: Promise to work for just 2 minutes on the easiest part
4. **Switch to Lighter Task**: Build momentum with a simpler task first

**Context-Aware Suggestions:**
- Location-based recommendations (see Contextual Task Suggestions)
- Time-of-day awareness (morning energy vs. evening wind-down)
- Integrates with existing task categorization

### 6. Positive Reinforcement

Streak tracking, celebrations, and reward badges to build sustainable habits.

**Streak Tracking:**
- Increments with each completed task
- Displayed prominently on Page 3 (Progress & Rewards)
- Visual streak counter motivates continued engagement
- Resets do not punish — system focuses on forward momentum

**Consecutive Completions:**
- Tracks tasks completed in a row within the same session
- Every 3 consecutive completions triggers animated badge celebration
- Animations include confetti, balloons, or snow effects
- Celebrates "3 in a row!" achievements

**Weekly Milestones:**
- Every 7-task increment (7, 14, 21, etc.) triggers special celebration
- Larger animated effects (balloons and snow)
- Milestone counter displayed on rewards page
- Encourages long-term engagement

**Reward Badges:**
- System awards badges throughout the session
- Examples: "Task finisher", "Focus champion", "Momentum builder"
- Accumulated rewards shown on Page 3
- Visual feedback reinforces positive behaviors

### 7. Gentle Reminder System

Non-intrusive reminders that respect user mental state.

**Inactivity Detection:**
- Monitors time since last user action
- Tracks when user last interacted with the application
- Does not activate during active work sessions

**Adaptive Messaging:**
- Tone changes based on how many reminders have been ignored
- First reminder: "Hey, gentle nudge. Want to try one tiny step on any task?"
- Second reminder: "Totally okay if last time wasn't right. Want to try again..."
- Later reminders: "No worries, you can still restart now with one tiny step."
- Never guilt-trips or uses harsh language

### 8. Contextual Task Suggestions

Smart task recommendations based on location and time of day.

**Location-Based Recommendations:**
- Users select current location: Desk, Bed, Kitchen, Outside
- At Desk → suggests academic tasks and focused work
- In Bed → suggests personal relaxation or wind-down tasks
- In Kitchen → suggests meal-related or light tasks
- Outside → suggests movement-based or creative tasks

**Time-of-Day Awareness:**
- Morning (6am-12pm): "Morning focus: plan your day or tackle one academic task"
- Afternoon (12pm-6pm): "Midday push: finish one pending task or review notes"
- Evening (6pm-12am): "Chill tasks: journaling, light reading, or reflection"

**Smart Task Anchoring:**
- Combines location and time for intelligent suggestions
- Example: Desk + Morning → prioritizes academic tasks from dashboard
- Example: Bed + Evening → highlights personal/hobby tasks for wind-down
- Shows top 3 tasks from relevant categories
- Helps overcome decision paralysis by narrowing choices

---

## Repository Structure

```
project-zapzone/
├── src/
│   ├── Version14.py              # Main Streamlit application (latest version)
│   ├── Version12.py              # Previous version (simpler implementation)
│   ├── models.py                 # Hierarchical data models (Goal, Subgoal, Task, Subtask)
│   └── langgraph_decomposer.py   # LangGraph state machine for goal decomposition
├── tests/
│   └── test_goal_manager.py      # Unit tests for goal management
├── docs/
│   └── iteration1_report.md      # Development iteration documentation
├── README.md                      # Main project documentation (this file)
├── requirements.txt               # Python dependencies
└── .env                          # Environment variables 
```

**File Descriptions:**

- **Version14.py**: Main application entry point containing all UI logic, session state management, and feature implementations 
- **models.py**: Defines the hierarchical data structure (Goal → Subgoal → Task → Subtask) with serialization methods and completion tracking
- **langgraph_decomposer.py**: Implements the 4-node LangGraph state machine for intelligent goal decomposition with confidence tracking
- **test_goal_manager.py**: Pytest-based unit tests for goal management functionality
- **iteration1_report.md**: Development documentation tracking implementation progress and decisions
- **requirements.txt**: Python package dependencies with pinned versions
- **.env**: User-created file storing GOOGLE_API_KEY (not tracked by Git for security)

---

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|----------|
| **Frontend** | Streamlit | 1.49.1 | Interactive web-based UI |
| **AI/LLM** | Google Gemini 2.5 Flash | API | Natural language understanding, task categorization, goal decomposition |
| **AI Framework** | LangChain | (via langchain-google-genai 3.2.0) | LLM integration and prompt management |
| **Orchestration** | LangGraph | 1.0.4 | State machine for multi-step goal decomposition |
| **Language** | Python | 3.13 | Core application logic |
| **Environment Management** | python-dotenv | (included) | Secure API key management |
| **Testing** | pytest | 9.0.1 | Unit and integration testing |

**Dependencies:**
```
langchain_google_genai==3.2.0
langgraph==1.0.4
pytest==9.0.1
streamlit==1.49.1
```

---

## Setup Instructions

### Prerequisites

- Python 3.13 or higher
- Google API key for Gemini 2.5 Flash (get one at https://makersuite.google.com/app/apikey)
- Git (for cloning the repository)
- Internet connection (for API calls)

### Step 1: Clone the Repository

```bash
git clone https://github.com/vcu-cmsc-damevski/project-zapzone.git
cd project-zapzone
```

### Step 2: Create and Activate Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Google API Key

You have three options for setting your API key:

**Option A: Create a .env file (Recommended)**
```bash
# Create .env file in project root
echo GOOGLE_API_KEY=your_google_gemini_api_key_here > .env
```

**Option B: Set environment variable (macOS/Linux)**
```bash
export GOOGLE_API_KEY="your_google_gemini_api_key_here"
```

**Option C: Set environment variable (Windows Command Prompt)**
```cmd
set GOOGLE_API_KEY=your_google_gemini_api_key_here
```

**Option D: Set environment variable (Windows PowerShell)**
```powershell
$env:GOOGLE_API_KEY="your_google_gemini_api_key_here"
```

### Step 5: Run the Application

**IMPORTANT:** You must run the application from the `src` directory:

```bash
cd src
streamlit run Version14.py
```

The application will automatically open in your default web browser at `http://localhost:8501`

### Common Troubleshooting

**Problem:** "ModuleNotFoundError: No module named 'streamlit'" or similar

**Solution:** Make sure you activated the virtual environment and ran `pip install -r requirements.txt`

---

**Problem:** "RuntimeError: No GOOGLE_API_KEY / GEMINI_API_KEY found in environment"

**Solution:** Verify your API key is set correctly. Check that the .env file exists in the project root directory (not in src/) or that the environment variable is exported in your current terminal session.

---

**Problem:** "Cannot find module 'models'" or "Cannot find module 'langgraph_decomposer'"

**Solution:** Make sure you're running the command from the `src` directory: `cd src` then `streamlit run Version14.py`

---

**Problem:** Application starts but categorization/decomposition fails

**Solution:**
- Verify your API key is valid and has not expired
- Check your internet connection
- Verify the API key has access to Gemini 2.5 Flash model
- Look at the terminal output for specific error messages

---

**Problem:** Changes don't persist after restarting the app

**Solution:** This is expected behavior. The application currently uses Streamlit session state for storage. Data persists during a session but is cleared when you restart the app. Task and goal data can be manually saved using the "Save Progress" button (if available in your version).

---

## Application Walkthrough

The AI Goal Mentor is organized into three pages, accessible via the sidebar navigation.

### Page 1: Dashboard

The main hub for task management and daily productivity features.

**Task Input and Categorization:**
1. Locate the text area labeled "Dump your thoughts here"
2. Type unstructured thoughts, tasks, or ideas (e.g., "finish essay, call dentist, start learning Python")
3. Click "Organize my thoughts"
4. AI analyzes text and categorizes into: Academics, Personal, Hobbies, Future/Long-term Goals

**Confidence Display:**
- After categorization, see confidence score (e.g., "Confidence: 8/10")
- Read the rationale explaining why the AI made its decisions
- Low confidence (0-3) triggers warning to clarify input

**Review Screen Workflow:**
1. After categorization, review screen appears with all suggested tasks
2. Each task has a checkbox (checked by default)
3. Click "Edit" next to any task to modify its text
4. Uncheck boxes to reject tasks you don't want to add
5. Click "Accept" to add only checked tasks to your dashboard
6. Only accepted tasks appear in the flat task display

**Flat Task Display:**
- Four-column layout showing tasks by category
- Each task shows: task name, due date (if inferred), status
- Actions available:
  - Play button: Mark task as "started"
  - Checkmark: Mark task as "done"
  - Delete button: Remove task

**Hierarchical Goal Tracking:**
- If you've created goals on Page 2, they appear in "Your Big Goals (Hierarchical)" section
- Click to expand and see full goal structure
- Shows subgoals, tasks, and subtasks with completion percentages
- Progress bar visualizes overall goal completion

**Subtask Management:**
- Each task can have subtasks (manually added or auto-generated)
- Enter subtasks as comma-separated values
- Check off individual subtasks as you complete them
- Use sidebar autonomy controls to enable/disable auto-generation

**Reflective Check-ins:**
- After completing a task, see: "You recently completed: [task name]"
- Prompt asks: "How did you feel about your focus during this task?"
- Write free-form reflection
- Helps identify focus patterns over time

**Motivation Check-in:**
- Radio buttons ask: "How are you feeling about working on your tasks right now?"
- Select "I'm doing fine" or "I'm struggling with motivation"
- If struggling, system suggests strategies (Pomodoro, movement break, 2-minute starter, lighter task)

**Gentle Reminder System:**
- If inactive for extended period, gentle reminder appears
- Message tone adapts based on how many reminders ignored
- Options: "Snooze 10 minutes" or "I'm ready to restart"
- Non-intrusive and supportive approach

**Contextual Suggestions:**
- Select your current location from dropdown (Desk, Bed, Kitchen, Outside)
- System suggests relevant tasks based on location and time of day
- Shows top 3 anchored tasks for your current context
- Helps overcome decision paralysis

**Categorization Feedback:**
- Text area to provide feedback on past categorizations
- Feedback influences future AI behavior
- Helps train the system to understand your preferences

### Page 2: Large Goal Decomposition

Break down overwhelming goals into hierarchical structures.

**Category Selection:**
- Dropdown menu with options: Academics, Personal, Hobbies, Future/Long-term Goals
- Category provides context for better AI decomposition
- Required before processing

**Goal Input:**
- Text area for entering your large goal
- Examples: "Prepare for Python programming exam on Dec 15", "Learn web development", "Complete thesis research"
- Can be high-level — AI will add detail

**LangGraph Decomposition Process:**
1. Click "Break into hierarchical plan (LangGraph)" button
2. Wait 10-30 seconds while the 4-node state machine processes:
   - Parse Goal: Extract title and description
   - Decompose to Subgoals: Create 3-5 major components
   - Generate Tasks: Create 5-7 tasks per subgoal (loops)
   - Finalize: Assemble complete Goal object
3. Progress updates show which node is currently processing

**Hierarchical Output Display:**
- Goal title and description with confidence score and rationale
- Each subgoal shown in expandable section
- Under each subgoal: 5-7 tasks with estimated time
- Under each task: 3-5 subtasks (micro-steps)
- Total statistics: X subgoals, Y tasks, ~Z minutes

**Tree View Option:**
- Click "Show Tree View" for visual hierarchy
- Displays goal structure as expandable tree
- Includes completion status indicators
- Helps understand big picture

**Adding to Dashboard:**
- Click "Add latest goal to Dashboard" button
- Goal transfers to Page 1 "Your Big Goals (Hierarchical)" section
- Progress tracking enabled
- Can start checking off tasks immediately

**Goal Breakdown Feedback:**
- Text area to provide feedback on decomposition quality
- Feedback influences future goal processing
- Helps improve AI understanding of your preferences

### Page 3: Progress and Rewards

Track achievements and celebrate progress.

**Task Completion Metrics:**
- Total tasks created
- Total tasks completed
- Completion percentage
- Visual progress indicators

**Streak Counter:**
- Displays current task completion streak
- Increments with each completed task
- Motivates consistent engagement

**Earned Rewards:**
- List of all badges earned during session
- Examples: "Task finisher", "Focus champion", "Momentum builder"
- Visual representation of achievements

**Celebratory Animations:**
- Triggered at milestone completions (3 in a row, 7 tasks total, etc.)
- Balloons, snow, or confetti effects
- Positive reinforcement for sustained effort

**Encouragement Messages:**
- Dynamic messages based on streak level
- Examples: "You're building momentum!", "Impressive focus today!"
- Adaptive tone supports continued engagement

---

## Think-Aloud Study Insights

*This section will be updated with findings from upcoming user studies examining how users interact with the trust, predictability, and autonomy features.*

**Planned Study Focus:**
- User comprehension of confidence indicators and their impact on decision-making
- How users interpret and utilize rationale explanations
- Patterns in autonomy control usage (when users enable/disable AI features)
- Effectiveness of the clarification request system for vague inputs
- User perception of AI transparency and trustworthiness
- Impact of visual feedback on task completion rates

---

## License and Team

**Project:** AI Goal Mentor (ADHD Edition)

**Team:** Team ZapZone @ VCU CMSC-691

**Copyright:** 2025 Team ZapZone, Virginia Commonwealth University

**Repository:** https://github.com/vcu-cmsc-damevski/project-zapzone

---

*Built with care to support focus, reduce overwhelm, and empower users through transparent AI assistance.*
