import json

from app.models import LearningProposal


MIN_SAMPLES = 30


def propose(rows: list[dict]) -> LearningProposal:
    if len(rows) < MIN_SAMPLES:
        return LearningProposal(status="insufficient_data", sample_size=len(rows), message=f"Need at least {MIN_SAMPLES} completed outcomes before proposing changes.")
    dimensions = ["technical", "fundamental", "institutional", "insider"]
    covariance = {}
    returns = [float(r["return_pct"]) for r in rows]
    mean_return = sum(returns) / len(returns)
    for name in dimensions:
        values = [float(json.loads(r["scores"])[name]) for r in rows]
        mean_value = sum(values) / len(values)
        covariance[name] = sum((v-mean_value)*(ret-mean_return) for v,ret in zip(values,returns)) / len(rows)
    positives = {k: max(v, 0.0) for k,v in covariance.items()}
    total = sum(positives.values())
    weights = ({k: round(v/total, 3) for k,v in positives.items()} if total else {k: .25 for k in dimensions})
    return LearningProposal(status="review_required", sample_size=len(rows), message="Evidence-based weight proposal generated. It will not be applied without explicit approval.", proposed_weights=weights)


