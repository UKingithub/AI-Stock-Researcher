from app.demo import snapshots
from app.learning import propose
from app.models import ScreeningConfig
from app.scoring import score


def test_config_weights_must_total_one():
    try: ScreeningConfig(technical_weight=.9)
    except ValueError: return
    raise AssertionError("invalid weights accepted")


def test_confluent_candidate_is_eligible():
    result = score(snapshots()[-1], ScreeningConfig())
    assert result.eligible
    assert result.total > 80
    assert len(result.reasons) >= 2


def test_tradingview_filters_are_hard_eligibility_rules():
    config = ScreeningConfig()
    candidate = snapshots()[-1]
    assert score(candidate, config).eligible
    assert not score(candidate.model_copy(update={"average_volume_30d": 500_000}), config).eligible
    assert not score(candidate.model_copy(update={"roc_9": 0}), config).eligible
    assert not score(candidate.model_copy(update={"net_margin": 0}), config).eligible
    assert not score(candidate.model_copy(update={"revenue_growth": 5}), config).eligible
    assert not score(candidate.model_copy(update={"debt_to_equity": 2}), config).eligible


def test_learning_waits_for_sufficient_evidence():
    proposal = propose([])
    assert proposal.status == "insufficient_data"
    assert proposal.proposed_weights is None

