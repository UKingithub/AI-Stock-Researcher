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


def test_learning_waits_for_sufficient_evidence():
    proposal = propose([])
    assert proposal.status == "insufficient_data"
    assert proposal.proposed_weights is None


