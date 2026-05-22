from dataclasses import dataclass

from .models import AttackStrategy, StrategyStat


@dataclass(frozen=True)
class StrategySelection:
    strategy: AttackStrategy
    score: float
    reason: str


class StrategySelector:
    """History-aware but deterministic strategy selector for the MVP."""

    def select(self, risk_code="", exclude_strategy_ids=None):
        exclude_strategy_ids = exclude_strategy_ids or []
        queryset = AttackStrategy.objects.filter(enabled=True).exclude(id__in=exclude_strategy_ids)
        candidates = list(queryset)
        if risk_code:
            risk_matched = [
                strategy
                for strategy in candidates
                if not strategy.applicable_risks or risk_code in strategy.applicable_risks
            ]
            candidates = risk_matched
        if not candidates:
            candidates = list(AttackStrategy.objects.filter(enabled=True).exclude(id__in=exclude_strategy_ids))
        if not candidates:
            raise ValueError("No enabled attack strategies are available.")

        best = None
        for strategy in candidates:
            stat = StrategyStat.objects.filter(strategy=strategy, risk_code=risk_code or "").first()
            score = self._score(stat)
            reason = self._reason(strategy, stat, score)
            if best is None or score > best.score:
                best = StrategySelection(strategy=strategy, score=score, reason=reason)
        return best

    @staticmethod
    def _score(stat):
        if not stat:
            return 0.10
        success_rate = stat.success_rate
        average_risk = min(max(stat.average_score / 10, 0), 1)
        novelty = stat.novelty_score
        cost = min((stat.average_latency_ms or 0) / 30000, 1)
        return success_rate * 0.45 + average_risk * 0.35 + novelty * 0.10 - cost * 0.10

    @staticmethod
    def _reason(strategy, stat, score):
        if not stat:
            return f"选择 {strategy.name}：该策略尚无历史记录，保留探索新颖度。"
        return (
            f"选择 {strategy.name}：历史成功率 {stat.success_rate:.2%}，"
            f"平均风险分 {stat.average_score:.2f}，综合得分 {score:.3f}。"
        )
