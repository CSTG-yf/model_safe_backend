from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from .models import RedTeamAttempt


class RedTeamGraphState(TypedDict, total=False):
    run_id: int
    objective: dict[str, Any]
    round_index: int
    max_rounds: int
    used_strategy_ids: list[int]
    parent_attempt_id: int | None
    latest_attempt_id: int | None
    completed: int
    scores: list[float]
    should_stop: bool


class RedTeamGraphAgent:
    """LangGraph-backed red-team agent.

    The graph keeps orchestration explicit while delegating domain work to
    RedTeamOrchestrator._execute_round so persistence, Trace, mitigation, and
    regression behavior remain centralized.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.graph = self._build_graph()

    def run_objective(self, run, objective):
        initial_state: RedTeamGraphState = {
            "run_id": run.id,
            "objective": {
                "objective": objective.objective,
                "seed_prompt": objective.seed_prompt,
                "risk_code": objective.risk_code,
            },
            "round_index": 0,
            "max_rounds": self.orchestrator.max_rounds,
            "used_strategy_ids": [],
            "parent_attempt_id": None,
            "latest_attempt_id": None,
            "completed": 0,
            "scores": [],
            "should_stop": False,
        }
        return self.graph.invoke(initial_state)

    def _build_graph(self):
        builder = StateGraph(RedTeamGraphState)
        builder.add_node("execute_round", self._execute_round_node)
        builder.add_node("update_state", self._update_state_node)
        builder.add_edge(START, "execute_round")
        builder.add_edge("execute_round", "update_state")
        builder.add_conditional_edges(
            "update_state",
            self._route_after_update,
            {
                "continue": "execute_round",
                "end": END,
            },
        )
        return builder.compile()

    def _execute_round_node(self, state: RedTeamGraphState):
        objective = self.orchestrator._normalize_objective(state["objective"])
        parent_attempt = None
        if state.get("parent_attempt_id"):
            parent_attempt = RedTeamAttempt.objects.filter(id=state["parent_attempt_id"]).first()
        attempt = self.orchestrator._execute_round(
            run_id=state["run_id"],
            objective=objective,
            round_index=state.get("round_index", 0),
            parent_attempt=parent_attempt,
            used_strategy_ids=state.get("used_strategy_ids", []),
        )
        return {"latest_attempt_id": attempt.id}

    def _update_state_node(self, state: RedTeamGraphState):
        attempt = RedTeamAttempt.objects.get(id=state["latest_attempt_id"])
        used_strategy_ids = list(state.get("used_strategy_ids", []))
        if attempt.strategy_id:
            used_strategy_ids.append(attempt.strategy_id)
        scores = list(state.get("scores", []))
        if attempt.score is not None:
            scores.append(float(attempt.score))
        round_index = state.get("round_index", 0) + 1
        should_stop = bool(attempt.success or round_index >= state.get("max_rounds", 1))
        return {
            "used_strategy_ids": used_strategy_ids,
            "parent_attempt_id": attempt.id,
            "completed": state.get("completed", 0) + 1,
            "scores": scores,
            "round_index": round_index,
            "should_stop": should_stop,
        }

    @staticmethod
    def _route_after_update(state: RedTeamGraphState) -> Literal["continue", "end"]:
        return "end" if state.get("should_stop") else "continue"
