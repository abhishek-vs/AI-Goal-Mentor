"""
Hierarchical data models for AI Goal Mentor.
Supports multi-level goal decomposition: Goal → Subgoal → Task → Subtask
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class Subtask:
    """Smallest unit of work within a Task"""

    def __init__(self, description: str, parent_task_id: str, done: bool = False, subtask_id: Optional[str] = None):
        self.id = subtask_id or str(uuid.uuid4())
        self.parent_task_id = parent_task_id
        self.description = description
        self.done = done

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_task_id": self.parent_task_id,
            "description": self.description,
            "done": self.done
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subtask':
        return cls(
            description=data["description"],
            parent_task_id=data["parent_task_id"],
            done=data.get("done", False),
            subtask_id=data.get("id")
        )


class Task:
    """Individual task within a Subgoal"""

    def __init__(
        self,
        task: str,
        parent_subgoal_id: str,
        parent_goal_id: str,
        due: Optional[str] = None,
        started: bool = False,
        done: bool = False,
        subtasks: Optional[List[Subtask]] = None,
        counted: bool = False,
        estimated_minutes: Optional[int] = None,
        task_id: Optional[str] = None
    ):
        self.id = task_id or str(uuid.uuid4())
        self.parent_subgoal_id = parent_subgoal_id
        self.parent_goal_id = parent_goal_id
        self.task = task
        self.due = due or "None"
        self.started = started
        self.done = done
        self.subtasks = subtasks or []
        self.counted = counted
        self.estimated_minutes = estimated_minutes

    def add_subtask(self, description: str) -> Subtask:
        """Add a new subtask to this task"""
        subtask = Subtask(description=description, parent_task_id=self.id)
        self.subtasks.append(subtask)
        return subtask

    def get_completion_percentage(self) -> float:
        """Calculate what % of subtasks are done"""
        if not self.subtasks:
            return 100.0 if self.done else 0.0
        completed = sum(1 for st in self.subtasks if st.done)
        return (completed / len(self.subtasks)) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_subgoal_id": self.parent_subgoal_id,
            "parent_goal_id": self.parent_goal_id,
            "task": self.task,
            "due": self.due,
            "started": self.started,
            "done": self.done,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "counted": self.counted,
            "estimated_minutes": self.estimated_minutes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        subtasks = [Subtask.from_dict(st) for st in data.get("subtasks", [])]
        return cls(
            task=data["task"],
            parent_subgoal_id=data["parent_subgoal_id"],
            parent_goal_id=data["parent_goal_id"],
            due=data.get("due"),
            started=data.get("started", False),
            done=data.get("done", False),
            subtasks=subtasks,
            counted=data.get("counted", False),
            estimated_minutes=data.get("estimated_minutes"),
            task_id=data.get("id")
        )


class Subgoal:
    """Mid-level goal component - groups related tasks"""

    def __init__(
        self,
        title: str,
        parent_goal_id: str,
        level: int = 1,
        tasks: Optional[List[Task]] = None,
        status: str = "active",
        subgoal_id: Optional[str] = None
    ):
        self.id = subgoal_id or str(uuid.uuid4())
        self.parent_goal_id = parent_goal_id
        self.title = title
        self.level = level  # Depth in hierarchy (supports nested subgoals)
        self.tasks = tasks or []
        self.status = status  # "active", "completed", "paused"

    def add_task(
        self,
        task_description: str,
        due: Optional[str] = None,
        estimated_minutes: Optional[int] = None
    ) -> Task:
        """Add a new task to this subgoal"""
        task = Task(
            task=task_description,
            parent_subgoal_id=self.id,
            parent_goal_id=self.parent_goal_id,
            due=due,
            estimated_minutes=estimated_minutes
        )
        self.tasks.append(task)
        return task

    def get_completion_percentage(self) -> float:
        """Calculate what % of tasks are done"""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.done)
        return (completed / len(self.tasks)) * 100

    def update_status(self):
        """Auto-update status based on task completion"""
        if not self.tasks:
            self.status = "active"
            return

        if all(t.done for t in self.tasks):
            self.status = "completed"
        elif any(t.started for t in self.tasks):
            self.status = "active"
        else:
            self.status = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_goal_id": self.parent_goal_id,
            "title": self.title,
            "level": self.level,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subgoal':
        tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return cls(
            title=data["title"],
            parent_goal_id=data["parent_goal_id"],
            level=data.get("level", 1),
            tasks=tasks,
            status=data.get("status", "active"),
            subgoal_id=data.get("id")
        )


class Goal:
    """Top-level goal containing subgoals and metadata"""

    def __init__(
        self, 
        title: str,
        description: str = "",
        subgoals: Optional[List[Subgoal]] = None,
        status: str = "active",
        category: str = "Academics",
        created_at: Optional[datetime] = None,
        goal_id: Optional[str] = None,
        confidence: int = 5,
        rationale: str = "",
    ):
        self.id = goal_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.subgoals = subgoals or []
        self.status = status  # "active", "completed", "paused", "archived"
        self.category = category  # Link to existing category system
        self.created_at = created_at or datetime.now()
        self.confidence = confidence
        self.rationale = rationale

    def add_subgoal(self, title: str, level: int = 1) -> Subgoal:
        """Add a new subgoal to this goal"""
        subgoal = Subgoal(
            title=title,
            parent_goal_id=self.id,
            level=level
        )
        self.subgoals.append(subgoal)
        return subgoal

    def get_completion_percentage(self) -> float:
        """Calculate overall goal completion based on all tasks"""
        if not self.subgoals:
            return 0.0

        total_tasks = sum(len(sg.tasks) for sg in self.subgoals)
        if total_tasks == 0:
            return 0.0

        completed_tasks = sum(
            sum(1 for t in sg.tasks if t.done)
            for sg in self.subgoals
        )
        return (completed_tasks / total_tasks) * 100

    def get_total_tasks(self) -> int:
        """Count all tasks across all subgoals"""
        return sum(len(sg.tasks) for sg in self.subgoals)

    def get_completed_tasks(self) -> int:
        """Count completed tasks across all subgoals"""
        return sum(
            sum(1 for t in sg.tasks if t.done)
            for sg in self.subgoals
        )

    def update_status(self):
        """Auto-update status based on subgoal completion"""
        if not self.subgoals:
            self.status = "active"
            return

        for sg in self.subgoals:
            sg.update_status()

        if all(sg.status == "completed" for sg in self.subgoals):
            self.status = "completed"
        elif any(sg.status == "active" for sg in self.subgoals):
            self.status = "active"
        else:
            self.status = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subgoals": [sg.to_dict() for sg in self.subgoals],
            "status": self.status,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "confidence": self.confidence,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        subgoals = [Subgoal.from_dict(sg) for sg in data.get("subgoals", [])]
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        return cls(
            title=data["title"],
            description=data.get("description", ""),
            subgoals=subgoals,
            status=data.get("status", "active"),
            category=data.get("category", "Academics"),
            created_at=created_at,
            goal_id=data.get("id"),
            confidence=data.get("confidence", 5),
            rationale=data.get("rationale", "")
        )


# Helper functions for working with the hierarchical model

def flatten_goal_to_legacy_tasks(goal: Goal) -> List[Dict[str, Any]]:
    """
    Convert a hierarchical Goal into flat task dictionaries
    compatible with the existing Version14 task structure.
    This maintains backward compatibility.
    """
    legacy_tasks = []

    for subgoal in goal.subgoals:
        for task in subgoal.tasks:
            # Convert Subtask objects to string list (legacy format)
            subtask_strings = [st.description for st in task.subtasks]

            legacy_task = {
                "task": f"{subgoal.title}: {task.task}",  # Prefix with subgoal
                "due": task.due,
                "started": task.started,
                "done": task.done,
                "subtasks": subtask_strings,
                "counted": task.counted,
                # Store IDs for potential reverse mapping
                "_goal_id": goal.id,
                "_subgoal_id": subgoal.id,
                "_task_id": task.id
            }
            legacy_tasks.append(legacy_task)

    return legacy_tasks
