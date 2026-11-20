"""Project group summaries without publishing source-person ordering or individual recordings."""
import copy
import statistics

def for_release(result):
    report=copy.deepcopy(result)
    ranges=report.pop('target_distribution_per_person')
    report['target_degrees']={}
    for task in ('standing','walking'):
        values=[r[task] for r in ranges]
        report['target_degrees'][task]={
            'median_of_participant_medians':statistics.median(x['median_deg'] for x in values),
            'minimum':min(x['min_deg'] for x in values), 'maximum':max(x['max_deg'] for x in values)}
    # Apply the same permutation to all contrasts so their across-method pairing is preserved.
    order=sorted(range(report['people']),key=lambda i:tuple(report['contrasts'][k]['paired_gains_deg'][i] for k in ('shared_motion','wrong_full','linear_full','random_full','recent')))
    for record in report['contrasts'].values():
        gains=record['paired_gains_deg']
        record['paired_gains_deg']=[gains[i] for i in order]
    report['paired_order']='Anonymous participants sorted by their shared-motion gain, with the same order used across contrasts within this evaluation.'
    return report
