#!/usr/bin/env python3
"""Check report evidence completeness, NOT natural motion or honest observation."""
import argparse, hashlib, json, math, pathlib, sys
CHECKS = ('force_chain', 'articulation', 'contacts', 'trajectory_timing', 'normal_speed_readability')
VISUAL = ('rendered_frame', 'normal_speed', 'slow_motion')
def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
def time_range(value):
    return isinstance(value, list) and len(value)==2 and all(finite_number(x) for x in value) and 0 <= value[0] < value[1]

def evaluate(d):
    blocked, partial, failures = [], [], []
    if d.get('schema_version') != 'animal-motion-review/1': blocked.append('unsupported_or_missing_schema')
    artifact = d.get('artifact', {})
    try:
        actual = hashlib.sha256(pathlib.Path(artifact['path']).read_bytes()).hexdigest()
        if actual != artifact.get('sha256'): blocked.append('artifact_hash_mismatch')
    except (KeyError, OSError, TypeError): blocked.append('artifact_unreadable')
    reviewer, producers = d.get('reviewer_id'), d.get('producer_ids')
    if not isinstance(reviewer, str) or not reviewer.strip(): blocked.append('missing_reviewer')
    if not isinstance(producers, list) or not producers or not all(isinstance(x, str) and x for x in producers): blocked.append('missing_producer_identity'); producers=[]
    if reviewer in producers: blocked.append('reviewer_is_producer')
    interval = d.get('action', {}).get('time_range_seconds')
    valid_interval = time_range(interval)
    if not valid_interval: blocked.append('invalid_action_range')
    if not d.get('action', {}).get('actor') or not d.get('action', {}).get('kind'): blocked.append('missing_action_identity')
    evidence = d.get('evidence', [])
    if not isinstance(evidence, list): blocked.append('invalid_evidence'); evidence=[]
    by_id = {}
    for e in evidence:
        if not isinstance(e, dict) or not e.get('id'): blocked.append('evidence_missing_id'); continue
        if e['id'] in by_id: blocked.append('duplicate_evidence_id')
        by_id[e['id']]=e
        if 'time_range_seconds' in e and not time_range(e['time_range_seconds']): blocked.append('invalid_evidence_range:'+e['id'])
        if 'sample_times_seconds' in e and (not isinstance(e['sample_times_seconds'],list) or not all(finite_number(x) and x>=0 for x in e['sample_times_seconds'])): blocked.append('invalid_evidence_sample_times:'+e['id'])
        if 'playback_rate' in e and (not finite_number(e['playback_rate']) or e['playback_rate']<=0): blocked.append('invalid_playback_rate:'+e['id'])
    def observed(e):
        return e.get('observed') is True and e.get('reviewer_id')==reviewer and reviewer not in producers and bool(e.get('observation','').strip()) and (e.get('kind') not in VISUAL or e.get('artifact_sha256')==artifact.get('sha256'))
    checks=d.get('checks', {})
    if not isinstance(checks,dict): blocked.append('invalid_checks'); checks={}
    for key in CHECKS:
        c=checks.get(key,{})
        result=c.get('status') if isinstance(c,dict) else None
        if result not in ('PASS','FAIL','UNREVIEWED'): blocked.append('missing_or_invalid_check:'+key); continue
        if result=='FAIL': failures.append(key)
        if result=='UNREVIEWED': partial.append('unreviewed:'+key); continue
        ids=c.get('evidence_ids',[])
        if not isinstance(ids,list) or not ids or not all(isinstance(i,str) and i in by_id for i in ids): blocked.append('missing_check_evidence:'+key); continue
        if not c.get('observation','').strip(): blocked.append('missing_check_observation:'+key)
        if result=='PASS' and any(by_id[i].get('kind') in VISUAL and by_id[i].get('artifact_sha256')!=artifact.get('sha256') for i in ids): blocked.append('cross_version_visual_evidence:'+key)
        if result=='PASS' and not any(observed(by_id[i]) and by_id[i].get('kind') in VISUAL for i in ids): partial.append('no_independent_visual_evidence:'+key)
    normal=[]
    for e in evidence:
        if not isinstance(e,dict) or e.get('kind')!='normal_speed' or not observed(e): continue
        r=e.get('time_range_seconds')
        if time_range(r) and finite_number(e.get('playback_rate')) and e.get('playback_rate')==1 and e.get('artifact_sha256')==artifact.get('sha256'):
            normal.append(r)
    if valid_interval:
        cursor=interval[0]
        for a,b in sorted(normal):
            if a > cursor+1e-6: break
            if b>cursor: cursor=b
        if cursor < interval[1]-1e-6: partial.append('normal_speed_action_coverage_incomplete')
    issues=d.get('issues',[])
    if not isinstance(issues,list): blocked.append('invalid_issues'); issues=[]
    for issue in issues:
        if not isinstance(issue,dict): blocked.append('invalid_issue'); continue
        if issue.get('severity') in ('Critical','Important') and issue.get('status')!='CLOSED': failures.append('open_issue:'+str(issue.get('id','unnamed')))
        if issue.get('severity') in ('Critical','Important') and issue.get('status')=='CLOSED':
            closure=issue.get('closure',{})
            if closure.get('artifact_sha256')!=artifact.get('sha256') or closure.get('reviewer_id')!=reviewer or not closure.get('evidence_ids') or not all(i in by_id and observed(by_id[i]) for i in closure.get('evidence_ids',[])):
                blocked.append('unsupported_issue_closure:'+str(issue.get('id','unnamed')))
    status='BLOCKED' if blocked else 'REVISE' if failures else 'PARTIAL' if partial else 'PASS'
    return {'status':status,'release_allowed':status=='PASS','blocking_record_errors':sorted(set(blocked)),'known_failures':sorted(set(failures)),'missing_review_coverage':sorted(set(partial)),'scope':'Report consistency and evidence coverage only; does not assess biological accuracy, naturalness, or whether claimed viewing really occurred.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('review');p.add_argument('--output');a=p.parse_args()
    try: result=evaluate(json.loads(pathlib.Path(a.review).read_text()))
    except (OSError, ValueError, TypeError) as exc: result={'status':'BLOCKED','release_allowed':False,'blocking_record_errors':[str(exc)]}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: pathlib.Path(a.output).write_text(text+'\n')
    print(text);return 0 if result['status']=='PASS' else 1
if __name__=='__main__': sys.exit(main())
