"""Sweta's synthetic integration of existing model predictions and rule scores."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from .hazim_training import synthetic_cohort, train_candidates
from .rule_score import PROPOSED_SETTINGS, score_application
from .validation_review import review_validation


def matched_review(validation, predictions, *, max_reviews):
    """Require identical validation IDs/labels across models; points stay points."""
    source = {}
    for row in validation:
        loan = row.get('loan_id')
        if not isinstance(loan, str) or not loan.strip() or loan != loan.strip() or loan in source:
            raise ValueError('Unique canonical validation IDs required')
        if row.get('split') != 'validation':
            raise ValueError('Only validation cohort accepted')
        if row.get('target') is not None and (type(row['target']) is not int or row['target'] not in (0, 1)):
            raise ValueError('Invalid cohort target')
        source[loan] = row
    if not source:
        raise ValueError('Empty cohort')
    models = {}
    for row in predictions:
        name = row.get('model')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Named model required')
        models.setdefault(name, []).append(row)
    if not models:
        raise ValueError('No model predictions')
    diagnostics = {}
    for name, rows in sorted(models.items()):
        if len(rows) != len(source) or {r['loan_id'] for r in rows} != set(source):
            raise ValueError('Models must share exact validation cohort')
        if any(r['target'] != source[r['loan_id']]['target'] for r in rows):
            raise ValueError('Model labels differ from validation cohort')
        diagnostics[name] = review_validation(rows, max_reviews=max_reviews)
    scores = []
    for loan, row in source.items():
        result = score_application(row)
        scores.append({'loan_id': loan, 'split': 'validation', 'target': row['target'],
                       'score': result['score'], 'eligible': row['target'] is not None and result['score'] is not None,
                       'settings_sha256': result['settings_sha256']})
    eligible = [r for r in scores if r['eligible']]
    # Compare ranking at the same capacity, retaining whole tied score groups.
    ranked = []
    for threshold in sorted({r['score'] for r in eligible}, reverse=True):
        group = [r for r in eligible if r['score'] == threshold]
        if len(ranked) + len(group) > max_reviews:
            break
        ranked.extend(group)
    tp = sum(r['target'] for r in ranked)
    report = {'synthetic': True, 'accepted_for_final_test': False, 'final_test_used': False,
              'calibration_fitted': False, 'capacity': max_reviews, 'models': diagnostics,
              'rule_ranking': {'labelled_scored': len(eligible), 'excluded': len(scores)-len(eligible),
                               'reviewed': len(ranked), 'tp': tp, 'fp': len(ranked)-tp,
                               'precision': tp/len(ranked) if ranked else None,
                               'recall': tp/sum(r['target'] for r in eligible) if sum(r['target'] for r in eligible) else None},
              'limitations': ['Invented cohort: software evidence only.',
                             'Cutoffs are validation proposals, not accepted policy or risk bands.',
                             'Rule ranking uses all scoreable observed rows; compare cohort counts before interpreting.',
                             'Same-cohort model selection and cutoff proposals are optimistic.',
                             'No calibration fitting or final-test evaluation performed.']}
    return report, scores


def chart(models):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="500" viewBox="0 0 720 500">',
             '<rect width="720" height="500" fill="white"/>',
             '<text x="40" y="28" font-size="18">SYNTHETIC — model reliability diagnostics</text>',
             '<path d="M70 420 L450 40" stroke="#777" stroke-dasharray="5 5" fill="none"/>',
             '<text x="120" y="465">Mean predicted probability (0–1)</text>',
             '<text x="15" y="490">Y: observed event rate (0–1); bars: descriptive 95% Wilson intervals</text>']
    for index, (name, report) in enumerate(models.items()):
        color = ['#0072B2', '#D55E00'][index % 2]
        # Escape model names even though the integrated runner generates fixed names.
        from html import escape
        parts.append(f'<text x="470" y="{70+index*30}" fill="{color}">{escape(name)}</text>')
        for b in report['reliability_bins']:
            if not b['count']:
                continue
            x = 70+380*b['mean_probability']; y = 420-380*b['observed_rate']
            lo, hi = b['observed_rate_wilson95']
            parts.append(f'<path d="M{x} {420-380*lo} V{420-380*hi}" stroke="{color}"/>')
            if index % 2:
                parts.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="{color}"/>')
            else:
                parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')
            parts.append(f'<text x="{x+6}" y="{y-5}" font-size="10">n={b["count"]}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--max-reviews', type=int, required=True)
    parser.add_argument('--out', type=Path, default=Path('results/sweta-model-review'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.synthetic or not args.out.resolve().is_relative_to(root/'results'):
        parser.error('Synthetic mode and ignored repository results/ output required')
    train, validation, review = synthetic_cohort()
    _, model_report, predictions = train_candidates(train, validation, review, synthetic=True)
    report, scores = matched_review(validation, predictions, max_reviews=args.max_reviews)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'diagnostics.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (args.out/'reliability.svg').write_text(chart(report['models']))
    with (args.out/'rule_scores.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(scores[0])); writer.writeheader(); writer.writerows(scores)
    manifest = {'synthetic': True, 'review': review, 'training_report': model_report,
                'rule_settings': PROPOSED_SETTINGS,
                'prediction_sha256': hashlib.sha256(json.dumps(predictions, sort_keys=True).encode()).hexdigest(),
                'output_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir()
                                  if p.name in {'diagnostics.json', 'rule_scores.csv', 'reliability.svg'}}}
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'counts': model_report['counts'], 'rule_ranking': report['rule_ranking'],
                      'models': {n: {'brier': d['brier_score'], 'proposal': d['proposed_cutoff']} for n,d in report['models'].items()}}, indent=2))

if __name__ == '__main__':
    main()
