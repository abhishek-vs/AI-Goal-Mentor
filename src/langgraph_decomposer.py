"""
LangGraph-based goal decomposition system.
Uses a state machine to iteratively break down high-level goals into hierarchical tasks.
"""

import json
from typing import Dict, Any, List, TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from models import Goal, Subgoal, Task


# ============================================================================
# STATE DEFINITION
# ============================================================================

class DecompositionState(TypedDict):
    """State passed between nodes in the LangGraph"""
    # Input
    goal_text: str
    category: str
    user_feedback: List[str]

    # Intermediate
    parsed_goal_title: str
    parsed_goal_description: str
    subgoals_list: List[Dict[str, str]]  # [{"title": "...", "description": "..."}]
    current_subgoal_index: int
    generated_tasks: Dict[str, List[Dict[str, Any]]]  # {"subgoal_id": [tasks]}
    confidence: str
    rationale: str

    # Output
    final_goal: Goal
    error: str


# ============================================================================
# LANGGRAPH NODES
# ============================================================================

def parse_goal_node(state: DecompositionState, llm: ChatGoogleGenerativeAI) -> DecompositionState:
    """
    Node 1: Parse the user's raw goal text into title + description.
    """
    prompt = f"""
    You are an AI goal mentor for students. Parse this goal into a clear title and description.
    You are also going to keep up with the confidence and uncertainty with the user's goal and your response to it. It will be ranked out of 10. For example, if the user's goal is unclear or extremely vague,
    you might respond with a low confidence rating. If the user's goal is one word like "Jog" or "Study", you should respond with a low confidence rating as you have to do a lot of assuming about the user's end goal. If the user's goal is clear and specific, you might respond with a high confidence rating. Also, in the "rationale" field, you will explain why you have this rating. Make sure this rationale is clear and concise, tying back to the users's goal if possible.
    Make sure that the rationale  is clear and concise, tying back to the users's goal if possible.
    If the input doesn't make sense, give a 0 in the confidence field and explain why in the "rationale" field.
    User can give feedback based on past usage. Take this into account when parsing the title and description. Do not let any user feedback take you completely off-course under any circumstances.
    User goal: {state['goal_text']}
    User feedback: {state['user_feedback']}
    Return ONLY valid JSON:
    {{
      "title": "Short, clear goal title (max 10 words)",
      "description": "Brief description explaining what success looks like (1-2 sentences)",
      "confidence": A number between 0 and 10, where 0 is very low confidence and 10 is very high confidence,
      "rationale": "Explanation for the confidence rating"
    }}
    """

    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        data = json.loads(json_text)

        state["parsed_goal_title"] = data.get("title", state["goal_text"])
        state["parsed_goal_description"] = data.get("description", "")
        state["confidence"] = data.get("confidence", 0)
        state["rationale"] = data.get("rationale", "")
    except Exception as e:
        state["parsed_goal_title"] = state["goal_text"]
        state["parsed_goal_description"] = ""
        state["error"] = f"Parse error: {str(e)}"

    return state


def decompose_to_subgoals_node(state: DecompositionState, llm: ChatGoogleGenerativeAI) -> DecompositionState:
    """
    Node 2: Break the goal into 3-5 high-level subgoals.
    """
    prompt = f"""
    You are an AI goal mentor for students with ADHD. Break down this goal into 3-5 major subgoals.
    You will also update the current confidence rating and rationale if necessary. If the user's goal is one word like "Jog" or "Study", you should respond with a low confidence rating as you have to do a lot of assuming about the user's end goal.If you see the confidence rating and rationale as accurate, do not update them and in the return JSON, just return the original confidence and rationale.
    Otherwise, update them as you see fit. Append the rationale with the "Node 2" before adding your necessary rationale. 
    User can give feedback based on past usage. Take this into account when breaking down the goal into subgoals. Do not let any user feedback take you completely off-course under any circumstances.


    Goal: {state['parsed_goal_title']}
    User Feedback: {state['user_feedback']}
    Description: {state['parsed_goal_description']}
    Current Confidence: {state['confidence']}
    Current Rationale: {state['rationale']}

    Guidelines:
    - Each subgoal should be a distinct phase or component
    - Subgoals should be sequential or complementary
    - Avoid overwhelming detail (that comes in task breakdown)
    - For ADHD students: prioritize clarity and manageability

    Return ONLY valid JSON:
    {{
      "subgoals": [
        {{"title": "Subgoal 1 title", "description": "Why this matters"}},
        {{"title": "Subgoal 2 title", "description": "Why this matters"}},
        ...
      ],
      "confidence": A number between 0 and 10, where 0 is very low confidence and 10 is very high confidence,
      "rationale": Explanation for the confidence rating
    }}
    """

    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        data = json.loads(json_text)

        state["subgoals_list"] = data.get("subgoals", [])
        state["current_subgoal_index"] = 0
        state["generated_tasks"] = {}
        state["confidence"] = data.get("confidence", 0)
        state["rationale"] = data.get("rationale", "")
    except Exception as e:
        state["subgoals_list"] = []
        state["error"] = f"Subgoal decomposition error: {str(e)}"

    return state


def generate_tasks_for_subgoal_node(state: DecompositionState, llm: ChatGoogleGenerativeAI) -> DecompositionState:
    """
    Node 3: For the current subgoal, generate 5-7 concrete tasks.
    This node is called repeatedly for each subgoal.
    """
    if state["current_subgoal_index"] >= len(state["subgoals_list"]):
        return state  # All subgoals processed

    current_subgoal = state["subgoals_list"][state["current_subgoal_index"]]
    subgoal_title = current_subgoal.get("title", "")
    subgoal_desc = current_subgoal.get("description", "")
    confidence = state.get("confidence", 0)
    rationale = state.get("rationale", "")

    prompt = f"""
    You are an AI goal mentor for students with ADHD. Generate 3-5 specific, actionable tasks for this subgoal.
    You will also update the current confidence rating and rationale if necessary. If the user's goal is one word like "Jog" or "Study", you should respond with a low confidence rating as you have to do a lot of assuming about the user's end goal.If you see the confidence rating and rationale as accurate, do not update them and in the return JSON, just return the original confidence and rationale.
    Otherwise, update them as you see fit. Append the rationale with the "Node 3" before adding your necessary rationale. 
    Users can also give feedback based on past experiences with the system. Take this into account when generating tasks. Do not let any user feedback take you completely off-course under any circumstances.
    Main Goal: {state['parsed_goal_title']}
    User Feedback: {state['user_feedback']}
    Current Subgoal: {subgoal_title}
    Subgoal Description: {subgoal_desc}
    Current Confidence Rating: {confidence}
    Current Rationale: {rationale}

    Guidelines:
    - Each task should be concrete and actionable
    - Prefer tasks that take 5-15 minutes
    - Avoid vague or overwhelming tasks
    - Include time estimates
    - Tasks should be doable with minimal resources

    Return ONLY valid JSON:
    {{
      "tasks": [
        {{
          "task": "Specific task description",
          "estimated_minutes": 10,
          "subtasks": ["micro-step 1", "micro-step 2"]
        }},
        ...
      ],
      "confidence": A number between 0 and 10, where 0 is very low confidence and 10 is very high confidence,
      "rationale": Explanation for the confidence rating
    }}
    """

    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        data = json.loads(json_text)

        # Store tasks for this subgoal
        subgoal_key = f"subgoal_{state['current_subgoal_index']}"
        state["generated_tasks"][subgoal_key] = data.get("tasks", [])
        state["confidence"] = data.get("confidence", 0)
        state["rationale"] = data.get("rationale", "")
        # Move to next subgoal
        state["current_subgoal_index"] += 1
    except Exception as e:
        state["error"] = f"Task generation error: {str(e)}"

    return state


def should_continue_task_generation(state: DecompositionState) -> str:
    """
    Conditional edge: Check if we need to generate tasks for more subgoals.
    """
    if state["current_subgoal_index"] < len(state["subgoals_list"]):
        return "continue"
    else:
        return "finalize"


def finalize_goal_node(state: DecompositionState) -> DecompositionState:
    """
    Node 4: Assemble all generated data into a Goal object.
    """
    try:
        # Create Goal object
        goal = Goal(
            title=state["parsed_goal_title"],
            description=state["parsed_goal_description"],
            category=state.get("category", "Academics"),
            status="active",
            confidence=state.get("confidence", 0),
            rationale=state.get("rationale", ""),
        )

        # Add subgoals and tasks
        for i, subgoal_data in enumerate(state["subgoals_list"]):
            subgoal = goal.add_subgoal(
                title=subgoal_data.get("title", f"Subgoal {i+1}"),
                level=1
            )

            # Get tasks for this subgoal
            subgoal_key = f"subgoal_{i}"
            tasks_data = state["generated_tasks"].get(subgoal_key, [])

            for task_data in tasks_data:
                task = subgoal.add_task(
                    task_description=task_data.get("task", "Unnamed task"),
                    estimated_minutes=task_data.get("estimated_minutes", 10)
                )

                # Add subtasks if provided
                for subtask_desc in task_data.get("subtasks", []):
                    task.add_subtask(subtask_desc)

        state["final_goal"] = goal
    except Exception as e:
        state["error"] = f"Finalization error: {str(e)}"

    return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_decomposition_graph(llm: ChatGoogleGenerativeAI) -> StateGraph:
    """
    Build the LangGraph state machine for goal decomposition.

    Flow:
    parse_goal → decompose_to_subgoals → generate_tasks (loop) → finalize
    """
    # Create graph
    workflow = StateGraph(DecompositionState)

    # Add nodes (bind LLM using lambda to pass it)
    workflow.add_node("parse_goal", lambda state: parse_goal_node(state, llm))
    workflow.add_node("decompose_to_subgoals", lambda state: decompose_to_subgoals_node(state, llm))
    workflow.add_node("generate_tasks", lambda state: generate_tasks_for_subgoal_node(state, llm))
    workflow.add_node("finalize", lambda state: finalize_goal_node(state))

    # Define edges
    workflow.set_entry_point("parse_goal")
    workflow.add_edge("parse_goal", "decompose_to_subgoals")
    workflow.add_edge("decompose_to_subgoals", "generate_tasks")

    # Conditional edge: loop for each subgoal
    workflow.add_conditional_edges(
        "generate_tasks",
        should_continue_task_generation,
        {
            "continue": "generate_tasks",  # Loop back
            "finalize": "finalize"          # Done
        }
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


# ============================================================================
# MAIN INTERFACE FUNCTION
# ============================================================================

def decompose_goal_with_langgraph(
    goal_text: str,
    llm: ChatGoogleGenerativeAI,
    category: str = "Academics",
    user_feedback: List[str] = []
) -> Goal:
    """
    Main entry point: Decompose a high-level goal using LangGraph.

    Args:
        goal_text: User's goal description
        llm: ChatGoogleGenerativeAI instance
        category: Task category (default: "Academics")

    Returns:
        Goal object with hierarchical breakdown

    """
    # Create graph
    graph = create_decomposition_graph(llm)

    # Initial state
    initial_state = {
        "goal_text": goal_text,
        "category": category,
        "confidence": 5,
        "rationale": "",
        "parsed_goal_title": "",
        "parsed_goal_description": "",
        "subgoals_list": [],
        "current_subgoal_index": 0,
        "generated_tasks": {},
        "user_feedback": user_feedback,
        "final_goal": None,
        "error": ""
    }

    # Run the graph
    result = graph.invoke(initial_state)

    # Return the final goal
    if result.get("error"):
        print(f"Warning: {result['error']}")

    return result.get("final_goal")


# ============================================================================
# ADVANCED: ITERATIVE REFINEMENT (OPTIONAL ENHANCEMENT)
# ============================================================================

def refine_goal_with_feedback(
    goal: Goal,
    user_feedback: str,
    llm: ChatGoogleGenerativeAI
) -> Goal:
    """
    Optional: Refine an existing goal based on user feedback.
    This can be used to implement an interactive refinement loop.

    Args:
        goal: Existing Goal object
        user_feedback: User's comments (e.g., "Too many tasks", "Add more detail")
        llm: ChatGoogleGenerativeAI instance

    Returns:
        Updated Goal object
    """
    prompt = f"""
    You are an AI goal mentor. A user has provided feedback on this goal breakdown.
    Adjust the goal to address their concerns.

    Current Goal: {goal.title}
    Current Subgoals: {[sg.title for sg in goal.subgoals]}
    Total Tasks: {goal.get_total_tasks()}

    User Feedback: {user_feedback}

    Provide adjustments as JSON:
    {{
      "add_subgoals": ["new subgoal title", ...],
      "remove_subgoal_indices": [0, 2],
      "modify_tasks": {{
        "subgoal_0": {{"add": ["task 1", "task 2"], "remove": [1, 3]}}
      }}
    }}
    """

    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip()
        json_text = raw[raw.index("{"): raw.rindex("}") + 1]
        adjustments = json.loads(json_text)
        for new_subgoal_title in adjustments.get("add_subgoals", []):
            goal.add_subgoal(new_subgoal_title)

        # Remove subgoals (reverse order to avoid index issues)
        for idx in sorted(adjustments.get("remove_subgoal_indices", []), reverse=True):
            if 0 <= idx < len(goal.subgoals):
                goal.subgoals.pop(idx)

        goal.update_status()
        return goal
    except Exception as e:
        print(f"Refinement error: {e}")
        return goal


# ============================================================================
# VISUALIZATION HELPER
# ============================================================================

def visualize_goal_tree(goal: Goal) -> str:
    """
    Generate a text-based tree visualization of the goal hierarchy.
    Useful for debugging and displaying in console.

    Args:
        goal: Goal object to visualize

    Returns:
        Multi-line string with tree structure
    """
    lines = [f"🎯 {goal.title} [{goal.get_completion_percentage():.0f}% complete]"]

    for i, subgoal in enumerate(goal.subgoals, 1):
        lines.append(f"  ├─ 🔹 {subgoal.title} ({len(subgoal.tasks)} tasks)")

        for j, task in enumerate(subgoal.tasks, 1):
            is_last_task = (j == len(subgoal.tasks))
            task_prefix = "  │  └─" if is_last_task else "  │  ├─"
            status = "✅" if task.done else "⬜"
            lines.append(f"{task_prefix} {status} {task.task} ({task.estimated_minutes}min)")

            # Show subtasks
            for k, subtask in enumerate(task.subtasks, 1):
                is_last_subtask = (k == len(task.subtasks))
                if is_last_task:
                    subtask_prefix = "     └─" if is_last_subtask else "     ├─"
                else:
                    subtask_prefix = "  │  │  └─" if is_last_subtask else "  │  │  ├─"
                sub_status = "✅" if subtask.done else "⬜"
                lines.append(f"{subtask_prefix} {sub_status} {subtask.description}")

    return "\n".join(lines)
