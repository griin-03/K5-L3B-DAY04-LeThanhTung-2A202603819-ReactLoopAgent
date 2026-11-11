"""Đọc kết quả gốc để so sánh; không ghi lại điểm hoặc sửa eval JSON."""
import hashlib
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def totals(report):
    agent = [usage for case in report['cases'] for usage in case['result']['usage']]
    judge = [case['grade'].get('judge_usage', {}) for case in report['cases']]
    usages = [usage for usage in agent + judge if usage]
    costs = [usage['cost'] for usage in usages if isinstance(usage.get('cost'), (int, float))]
    return {
        **report['summary'],
        'agent_model_calls': len(agent),
        'judge_calls_with_usage': sum(bool(usage) for usage in judge),
        'agent_total_tokens': sum(usage.get('total_tokens', 0) for usage in agent),
        'judge_total_tokens': sum(usage.get('total_tokens', 0) for usage in judge),
        'reported_cost_sum': round(sum(costs), 8) if costs else None,
        'cost_complete': bool(usages) and len(costs) == len(usages) and report['summary']['unscored_cases'] == 0,
        'judge_trace_truncated_cases': [case['id'] for case in report['cases']
                                        if case['grade'].get('judge_trace_truncated')],
        'source_revision_events': sum(
            event['event'] == 'validation_missing_source'
            for case in report['cases'] for event in case['result']['trace']
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-incomplete', action='store_true',
                        help='Hiển thị cả run lỗi; vẫn giữ score null và đánh dấu chưa chấm đủ.')
    args = parser.parse_args()
    before = json.loads((ROOT / 'eval_before.json').read_text())
    after = json.loads((ROOT / 'eval_after.json').read_text())
    assert before['config'] == after['config'], 'Hai lần chạy khác cấu hình.'
    expected = {case['id'] for case in json.loads((ROOT / 'evals/cases.json').read_text())}
    for report in [before, after]:
        assert len(report['cases']) == 22
        assert {case['id'] for case in report['cases']} == expected
        if not args.allow_incomplete:
            assert report['summary']['unscored_cases'] == 0, 'Còn case chưa chấm; xem trace hoặc dùng --allow-incomplete.'
            assert report['summary']['score_0_100'] is not None
    manifest = json.loads((ROOT / 'evidence/manifest.json').read_text())
    for filename, expected_hash in manifest['protected_sha256'].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected_hash, filename
    previous = {case['id']: case for case in before['cases']}
    comparison = {
        'config': before['config'],
        'full_eval_pair_scored': all(report['summary']['score_0_100'] is not None for report in [before, after]),
        'before': totals(before),
        'after': totals(after),
        'cases': [{
            'id': case['id'],
            'before': previous[case['id']]['grade']['score'],
            'after': case['grade']['score'],
            'after_status': case['result']['status'],
            'mechanical_violations': case['grade']['mechanical']['violations'],
        } for case in after['cases']],
    }
    bonus_path = ROOT / 'eval_bonus.json'
    if bonus_path.exists():
        bonus = json.loads(bonus_path.read_text())
        assert len(bonus['cases']) == 10
        if not args.allow_incomplete:
            assert bonus['summary']['bonus_points_0_15'] is not None, 'Bonus chưa chấm đủ.'
        comparison['bonus'] = totals(bonus)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
