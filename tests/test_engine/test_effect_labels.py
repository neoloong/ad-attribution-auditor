import pytest

from ad_audit.engine.models import classify_effect_interval


@pytest.mark.parametrize('ci,label', [
    (None, 'unavailable'), ((float('nan'), 1), 'unavailable'),
    ((0, float('inf')), 'unavailable'), ((1, -1), 'unavailable'),
    ((-.2, .2), 'practically_zero'), ((.05, .15), 'practically_zero'),
    ((-.15, -.05), 'practically_zero'), ((.2, .8), 'positive'),
    ((-.8, -.2), 'negative'), ((-.5, .5), 'inconclusive'),
    ((0, .5), 'inconclusive'), ((-.5, 0), 'inconclusive'),
])
def test_effect_evidence_labels_and_equivalence_precedence(ci, label):
    assert classify_effect_interval(ci) == label
