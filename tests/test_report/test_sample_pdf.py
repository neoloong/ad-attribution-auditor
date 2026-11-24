"""Financial decision thresholds and the actual rendered report contract."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

import pytest

from agent_native.audit_service import render_markdown
from scripts.gate1_pdf import action_for_interval, label_action_note, margin_threshold, render_report


@pytest.mark.parametrize('margin,threshold', [(None, 2.5), (.4, 2.5), (.25, 4), (.5, 2), (1, 1)])
def test_profit_break_even_is_inverse_contribution_margin(margin, threshold):
    actual_margin, actual_threshold = margin_threshold(margin)
    assert actual_margin == (.4 if margin is None else margin)
    assert actual_threshold == threshold


@pytest.mark.parametrize('margin', [0, -.1, 1.01, float('nan'), float('inf')])
def test_invalid_margin_rejected(margin):
    with pytest.raises(ValueError, match='Contribution margin'):
        margin_threshold(margin)


@pytest.mark.parametrize('ci,threshold,expected', [
    ((3, 3.5), 4, 'KILL'), ((3, 3.5), 2, 'SCALE'),
    ((2, 3), 2.5, 'KEEP'), ((2.5, 3), 2.5, 'KEEP'),
    ((1, 2.5), 2.5, 'KEEP'), (None, 2.5, 'KEEP'),
])
def test_interval_action_uses_margin_threshold_including_boundaries(ci, threshold, expected):
    assert action_for_interval(ci, threshold)[0] == expected


def sample_data():
    return json.loads((Path(__file__).resolve().parents[2] / 'validation/gate1-repair-2026-11-08/results.json').read_text())


def pdf_text(path):
    # The local renderer uses uncompressed Helvetica text streams.
    chunks = re.findall(rb'\(((?:\\.|[^\\)])*)\) Tj', path.read_bytes())
    return ' '.join(re.sub(rb'\\([\\()])', rb'\1', v).decode('cp1252') for v in chunks)


def test_unknown_margin_pdf_prints_assumption_and_priority_limitation(tmp_path):
    path = tmp_path/'unknown.pdf'
    render_report(sample_data(), path)
    text = pdf_text(path)
    assert 'Assumed contribution margin: 40%' in text
    assert 'Break-even iROAS = 1/margin = 2.50x' in text
    assert 'They are not profit decisions.' in text
    assert 'v2 supersedes the five-seed Gate-1 PASS' in text
    assert '1.0x revenue break-even' not in text
    assert 'Evidence label: inconclusive' in text


def test_customer_margin_pdf_recomputes_actions_instead_of_using_stale_values(tmp_path):
    data = deepcopy(sample_data())
    data['gate'] = 'PASS'
    row = data['campaign_results'][0]
    row['action'] = 'STALE'
    row['action_reason'] = 'Stale 1.0x rule'
    row['incremental_roas']['confidence_interval'] = [3, 3.5]
    for margin, action in [(.25, 'kill (provisional)'), (.5, 'keep (provisional)')]:
        path = tmp_path/f'{margin}.pdf'
        render_report(data, path, contribution_margin=margin)
        text = pdf_text(path)
        assert f'Customer-supplied contribution margin: {margin:.0%}' in text
        assert f'Break-even iROAS = 1/margin = {1/margin:.2f}x' in text
        assert action in text
        assert 'STALE' not in text and 'Stale 1.0x rule' not in text
        assert 'Customer margin unknown' not in text


def test_validation_hold_pdf_shows_each_campaign_priority(tmp_path):
    data = sample_data()
    data['gate'] = 'FAIL'
    kill, hold, inconclusive = data['campaign_results']
    kill['incremental_roas']['confidence_interval'] = [0.5, 1.2]
    hold['incremental_roas']['confidence_interval'] = [1.83, 3.58]
    inconclusive['incremental_roas']['confidence_interval'] = [-1.54, 1.26]

    path = tmp_path / 'validation-hold.pdf'
    render_report(data, path)
    text = pdf_text(path)
    assert f"{kill['campaign']} kill (provisional)" in text
    assert f"{hold['campaign']} hold (provisional)" in text
    assert f"{inconclusive['campaign']} kill (provisional)" in text
    assert 'Validation hold. Provisional priority: kill.' in text
    assert 'Validation hold. Provisional priority: hold.' in text
    assert label_action_note([0.5, 1.2], 2.5) in text
    assert label_action_note([-1.54, 1.26], 2.5) in text


def test_pdf_footer_uses_generation_date(tmp_path):
    path = tmp_path / 'prepared-date.pdf'
    render_report(sample_data(), path)
    footers = re.findall(r'Prepared \d{4}-\d{2}-\d{2}  \|  Local synthetic demonstration', pdf_text(path))
    assert footers == [f'Prepared {date.today().isoformat()}  |  Local synthetic demonstration'] * 4
    assert all('2026-11-09' not in footer for footer in footers)


@pytest.mark.parametrize('ci,label,upper_bound', [
    ([-1.54, 1.26], 'inconclusive', '1.26x'),
    ([0.5, 1.2], 'positive', '1.20x'),
])
def test_kill_note_explains_evidence_label_and_break_even(ci, label, upper_bound):
    note = label_action_note(ci, 2.5)
    assert note.startswith(f'The label is {label} because')
    assert '2.50x break-even' in note
    assert upper_bound in note


@pytest.mark.parametrize('ci', [[1.83, 3.58], [-2.0, -0.5], None, [-0.1, 0.1], [-1.54, 3.58]])
def test_label_action_note_omits_other_combinations(ci):
    assert label_action_note(ci, 2.5) == ''


def test_markdown_appends_shared_note_to_campaign_reason():
    metrics = {
        'total_spend': 100,
        'reported_roas': 2.8,
        'true_incremental_roas': -0.14,
        'confidence_interval': [-1.54, 1.26],
        'effect_label': 'inconclusive',
    }
    reason = 'Entire 95% interval is below the 2.50x margin threshold. Consider stopping only if a holdout confirms it.'
    report = {
        'report_id': 'sample',
        'dataset': {'start': '2026-11-01', 'end': '2026-11-03', 'days': 3, 'shopify_granularity': 'daily'},
        'store': {**metrics, 'reported_revenue': 280, 'incremental_revenue': -14},
        'engine': {'method': 'OLS', 'model_status': 'estimated', 'validation_gate': 'FAIL'},
        'decision_rule': {'rule': 'Break-even rule', 'action_notice': 'Provisional priorities',
                          'break_even_iroas': 2.5, 'practical_zero_delta': 0.2},
        'campaigns': [{**metrics, 'platform': 'Google', 'campaign_name': 'Search', 'mde80': None,
                       'action_display': 'kill (provisional)', 'engine_action_reason': reason}],
        'warnings': {'identification_limitations': []},
        'model_diagnostics': {},
        'mde80_definition': 'Minimum detectable effect at 80% power',
    }
    note = label_action_note(metrics['confidence_interval'], 2.5)
    assert note
    assert f'- **Search** — kill (provisional): {reason} {note}' in render_markdown(report).splitlines()
