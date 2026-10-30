#!/usr/bin/env python3
"""Small acceptance-gate regression fixtures; no animation-quality claim."""
import copy, hashlib, json, pathlib, tempfile
from check_animal_motion_review import CHECKS, evaluate
with tempfile.TemporaryDirectory() as folder:
    artifact=pathlib.Path(folder)/'fixture.bin';artifact.write_bytes(b'gate fixture; not a real video')
    sha=hashlib.sha256(artifact.read_bytes()).hexdigest()
    base={'schema_version':'animal-motion-review/1','artifact':{'path':str(artifact),'sha256':sha},'action':{'actor':'rabbit','kind':'hop','time_range_seconds':[7,10]},'producer_ids':['producer'],'reviewer_id':'reviewer','evidence':[{'id':'watch','kind':'normal_speed','reviewer_id':'reviewer','observed':True,'artifact_sha256':sha,'time_range_seconds':[7,10],'playback_rate':1,'observation':'SYNTHETIC fixture for validator only'}],'checks':{key:{'status':'PASS','evidence_ids':['watch'],'observation':'SYNTHETIC fixture only'} for key in CHECKS},'issues':[]}
    cases=[]
    cases.append(('record_complete_fixture',base,'PASS'))
    still=copy.deepcopy(base);still['evidence'][0]['kind']='rendered_frame';cases.append(('stills_cannot_release',still,'PARTIAL'))
    selfreview=copy.deepcopy(base);selfreview['reviewer_id']='producer';cases.append(('producer_cannot_self_release',selfreview,'BLOCKED'))
    known=copy.deepcopy(still);known['checks']['force_chain']['status']='FAIL';known['issues']=[{'id':'old-seated-hop','severity':'Important','status':'OPEN'}];cases.append(('known_seated_hop_rejected',known,'REVISE'))
    gap=copy.deepcopy(base);gap['evidence'][0]['time_range_seconds']=[8,10];cases.append(('watching_only_airborne_insufficient',gap,'PARTIAL'))
    stale=copy.deepcopy(base);stale['artifact']['sha256']='0'*64;cases.append(('stale_output_blocked',stale,'BLOCKED'))
    missing=copy.deepcopy(base);del missing['checks']['articulation'];cases.append(('trajectory_alone_insufficient',missing,'BLOCKED'))
    crossed=copy.deepcopy(base);oldframe=copy.deepcopy(crossed['evidence'][0]);oldframe.update({'id':'oldframe','kind':'rendered_frame','artifact_sha256':'f'*64});crossed['evidence'].append(oldframe);crossed['checks']['articulation']['evidence_ids']=['oldframe','watch'];cases.append(('old_frame_plus_new_watch_blocked',crossed,'BLOCKED'))
    crossedslow=copy.deepcopy(crossed);crossedslow['evidence'][1]['kind']='slow_motion';cases.append(('old_slowmotion_plus_new_watch_blocked',crossedslow,'BLOCKED'))
    boolean=copy.deepcopy(base);boolean['evidence'][0]['playback_rate']=True;cases.append(('boolean_is_not_playback_rate',boolean,'BLOCKED'))
    nonfinite=copy.deepcopy(base);nonfinite['action']['time_range_seconds']=[7,float('inf')];cases.append(('infinite_action_time_blocked',nonfinite,'BLOCKED'))
    nanrange=copy.deepcopy(base);nanrange['evidence'][0]['time_range_seconds']=[float('nan'),10];cases.append(('nan_evidence_time_blocked',nanrange,'BLOCKED'))
    results=[]
    for name,record,expected in cases:
        result=evaluate(record);assert result['status']==expected,(name,result)
        results.append({'case':name,'expected':expected,'actual':result['status']})
    print(json.dumps({'tests':'PASS','count':len(results),'scope':'validator behavior only; synthetic positive fixture is not a video review','results':results},indent=2))
