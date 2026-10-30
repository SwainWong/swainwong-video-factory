#!/usr/bin/env python3
"""Evidence-backed feedback intake and auditable harness candidates. No model calls."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1] / 'harness'
GROUPS = {'must': '01-must', 'should': '02-should', 'must_not': '03-must-not', 'verification': '04-verification'}
LABELS = {'auto': '由 Agent 判断', 'project_only': '仅返修，不沉淀', 'must': '一定要做', 'should': '推荐做', 'must_not': '一定不能做', 'verification': '验收与失败处理'}


def now(): return datetime.now(timezone.utc).isoformat()

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.feedback-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.feedback.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(stream, fcntl.LOCK_UN)


def build_intake(snapshot, review, folder=None):
    """Capture bounded evidence during preview; extraction failure never loses comments."""
    folder = Path(folder) if folder else Path(snapshot['snapshot_file']).parent
    folder.mkdir(parents=True, exist_ok=True)
    evidence_dir = folder / 'evidence'; evidence_dir.mkdir()
    rows, clip_budget = [], 60.0
    source_ok = False
    try:
        source_ok = review.file_signature() == review.signature and Path(snapshot['video']['path']).is_file()
    except OSError: pass
    for n, comment in enumerate(snapshot['comments']):
        evidence = {'status': 'unavailable', 'source_sha256': snapshot['video']['sha256'],
                    'selected_interval': [comment['start'], comment['end']], 'files': [],
                    'note': '证据只用于定位，不能代替连续视听验收。'}
        row = {'comment_id': comment['id'], 'requested_target': comment.get('harness_target', 'auto'),
               'scope': comment['scope'], 'status': 'awaiting_agent', 'evidence': evidence}
        rows.append(row)
        if not source_ok or n >= 50:
            evidence['error'] = '原视频不可用／已变化，或本轮超过 50 条自动取证预算；Agent 须补核原视频。'
            continue
        try:
            start, end = comment['start'], comment['end']
            # A click exactly at EOF refers to the last decodable frame, not a nonexistent next frame.
            capture_at = min(start, max(0, snapshot['video']['duration'] - 1 / snapshot['video'].get('fps', 30)))
            image = evidence_dir / f'{n:03d}-frame.jpg'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(capture_at), '-i', snapshot['video']['path'],
                            '-frames:v', '1', '-vf', 'scale=min(1280\\,iw):-2', '-q:v', '2', str(image)],
                           check=True, capture_output=True, timeout=20)
            if not image.is_file() or image.stat().st_size == 0: raise ValueError('未解码出画面')
            evidence['files'].append({'kind': 'frame', 'path': str(image), 'sha256': sha(image), 'at_seconds': capture_at})
            evidence['status'] = 'captured'
            if end > start:
                length = min(end - start, 30.0, clip_budget)
                evidence['status'] = 'partial'
                if length > 0:
                    clip = evidence_dir / f'{n:03d}-clip.mp4'
                    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(start), '-i', snapshot['video']['path'],
                                    '-t', str(length), '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=min(960\\,iw):-2',
                                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-c:a', 'aac', '-movflags', '+faststart', str(clip)],
                                   check=True, capture_output=True, timeout=45)
                    evidence['files'].append({'kind': 'clip', 'path': str(clip), 'sha256': sha(clip), 'interval': [start, start + length]})
                    clip_budget -= length
                    if length >= end - start: evidence['status'] = 'captured'
                if evidence['status'] == 'partial': evidence['note'] += ' 自动片段限每条 30 秒、每轮共 60 秒；未覆盖区间须查看原视频。'
            if review.file_signature() != review.signature: raise ValueError('取证期间原视频发生变化')
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            evidence.update(status='unavailable', files=[], error=f'取证失败：{type(exc).__name__}；保留原评论，Agent 补核。')
    intake = {'schema_version': 1, 'submission_id': snapshot['id'], 'video_sha256': snapshot['video']['sha256'],
              'snapshot_file': snapshot['snapshot_file'], 'harness_entry': str(ROOT / 'HARNESS.md'),
              'created_at': now(), 'items': rows}
    path = folder / 'harness-intake.json'; write_json(path, intake)
    return {'intake_file': str(path), 'entry': str(ROOT / 'HARNESS.md'), 'items': rows}


def load_snapshot(path):
    path = Path(path).resolve(strict=True)
    s = json.loads(path.read_text())
    if Path(s['snapshot_file']).resolve() != path: raise ValueError('快照路径不一致')
    uuid.UUID(s['id'])
    expected = Path(s['project']).resolve() / 'review-feedback' / s['video']['sha256'] / 'submissions' / s['id'] / 'snapshot.json'
    if expected.resolve() != path: raise ValueError('快照项目／视频／提交号不一致')
    return path, s


def text(value, name):
    if not isinstance(value, str) or not value.strip(): raise ValueError(f'缺少 {name}')
    return value.strip()


def record_analysis(snapshot_path, analysis, root=ROOT):
    """Agent supplies semantic decisions after viewing evidence; never infer rules by keywords."""
    path, s = load_snapshot(snapshot_path)
    if analysis.get('submission_id') != s['id'] or analysis.get('video_sha256') != s['video']['sha256']:
        raise ValueError('分析必须绑定本轮提交及视频哈希')
    author = text(analysis.get('agent_id'), 'agent_id')
    comments = {c['id']: c for c in s['comments']}
    decisions = analysis.get('decisions', [])
    if not isinstance(decisions, list) or sorted(d.get('comment_id', '') for d in decisions) != sorted(comments):
        raise ValueError('每条评论必须有且只有一个分析结果')
    supplemental = analysis.get('evidence_manifest')
    if supplemental:
        manifest = Path(supplemental).resolve(strict=True)
        if not manifest.is_relative_to(path.parent / 'harness-evidence'):
            raise ValueError('补充取证必须来自本轮 capture 记录')
        if analysis.get('evidence_manifest_sha256') != sha(manifest): raise ValueError('补充取证哈希不一致')
        intake = json.loads(manifest.read_text())
        if intake.get('snapshot_sha256') != sha(path): raise ValueError('补充取证未绑定当前快照')
    else:
        intake = json.loads((path.parent / 'harness-intake.json').read_text())
        if intake['items'] != s.get('harness', {}).get('items'):
            raise ValueError('取证清单与不可变快照不一致')
    if intake.get('submission_id') != s['id'] or intake.get('video_sha256') != s['video']['sha256']:
        raise ValueError('取证清单与提交身份不一致')
    evidence_by_id = {i['comment_id']: i['evidence'] for i in intake['items']}
    if set(evidence_by_id) != set(comments): raise ValueError('取证评论集合不一致')
    records = []
    for d in decisions:
        cid = d['comment_id']; uuid.UUID(cid)
        comment = comments[cid]
        disposition = d.get('disposition')
        if disposition not in ('candidate', 'existing_rule', 'project_only', 'needs_evidence'):
            raise ValueError('未知分析结果')
        if comment.get('harness_target') == 'project_only' and disposition == 'candidate':
            raise ValueError('用户选择仅返修，不得建立长期候选')
        for field in ('interpretation', 'reason', 'coverage', 'repair_action'): text(d.get(field), field)
        targets = d.get('existing_rule_ids', [])
        if not isinstance(targets, list) or any(not isinstance(v, str) for v in targets): raise ValueError('existing_rule_ids 必须是列表')
        if disposition == 'existing_rule' and not targets: raise ValueError('复用已有规则需给出规则 ID')
        if disposition == 'candidate':
            if d.get('group') not in GROUPS: raise ValueError('候选必须归入四个目录之一')
            for field in ('rule', 'applies_when', 'exceptions', 'check_evidence', 'failure_action', 'conflict_check'):
                text(d.get(field), field)
            if evidence_by_id[cid]['status'] == 'unavailable': raise ValueError('取证缺失时先补证据，不得声称已形成证据充分的候选')
            for evidence in evidence_by_id[cid]['files']:
                if sha(evidence['path']) != evidence['sha256']: raise ValueError('媒体证据已变化，需重新核验')
        records.append({'comment': comment, 'analysis': d, 'evidence': evidence_by_id[cid]})
    root = Path(root).resolve()
    with locked(root):
        progress_file = path.parent / 'harness-progress.json'
        fingerprint = hashlib.sha256(json.dumps(analysis, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if progress_file.exists():
            previous = json.loads(progress_file.read_text())
            if previous.get('analysis_sha256') == fingerprint: return previous
        revision = str(uuid.uuid4())
        history = path.parent / 'harness-analysis'; history.mkdir(exist_ok=True)
        write_json(history / f'{revision}.json', analysis)
        results = []
        for item in records:
            d, c = item['analysis'], item['comment']
            result = {'comment_id': c['id'], 'disposition': d['disposition'], 'rule_ids': d.get('existing_rule_ids', [])}
            if d['disposition'] == 'candidate':
                # Stable per comment identity; revisions are immutable, old candidates remain traceable.
                folder = root / GROUPS[d['group']] / 'candidates' / f'{s["id"]}-{c["id"]}'
                folder.mkdir(parents=True, exist_ok=True)
                candidate = {**item, 'id': f'{s["id"]}-{c["id"]}', 'revision': revision, 'status': 'candidate',
                             'agent_id': author, 'snapshot_file': str(path), 'snapshot_sha256': sha(path),
                             'submission_id': s['id'], 'video_sha256': s['video']['sha256'], 'created_at': now()}
                candidate_file = folder / f'{revision}.json'; write_json(candidate_file, candidate)
                md = folder / f'{revision}.md'
                md.write_text(f'# 规则候选：{LABELS[d["group"]]}\n\n状态：候选，未生效；不得当作 MUST 或禁令执行。\n\n'
                              f'- 原评论：{c["observation"]}\n- 规则：{d["rule"]}\n- 适用：{d["applies_when"]}\n'
                              f'- 例外：{d["exceptions"]}\n- 检查证据：{d["check_evidence"]}\n- 失败处理：{d["failure_action"]}\n'
                              f'- 冲突检查：{d["conflict_check"]}\n- 观察范围：{d["coverage"]}\n'
                              f'- [原始快照]({path})\n- [完整分析与媒体证据]({candidate_file})\n', encoding='utf-8')
                result.update(candidate_file=str(candidate_file), candidate_markdown=str(md), group=d['group'])
            results.append(result)
        progress = {'schema_version': 1, 'submission_id': s['id'], 'video_sha256': s['video']['sha256'],
                    'status': 'analyzed', 'agent_id': author, 'analysis_sha256': fingerprint, 'revision': revision,
                    'updated_at': now(), 'results': results,
                    'meaning': '已解析不代表返修完成；候选不代表长期规则已确认。'}
        write_json(progress_file, progress)
        return progress


def promote(candidate_path, approval, root=ROOT):
    """Explicit, version-bound review + user confirmation; no browser promotion endpoint."""
    root = Path(root).resolve(); cp = Path(candidate_path).resolve(strict=True)
    if not cp.is_relative_to(root) or 'candidates' not in cp.parts: raise ValueError('候选必须来自本 harness')
    c = json.loads(cp.read_text()); d = c['analysis']
    if approval.get('candidate_sha256') != sha(cp): raise ValueError('确认未绑定候选当前哈希')
    reviewer = text(approval.get('reviewer_id'), '独立审核身份')
    if reviewer == c['agent_id'] or approval.get('review_status') != 'PASS': raise ValueError('需要独立审核通过')
    for field in ('review_evidence', 'confirmation_basis', 'confirmed_scope'): text(approval.get(field), field)
    if approval.get('confirmed_scope') != d['applies_when']: raise ValueError('确认范围须与候选范围完全一致；范围变化请重写候选')
    if approval.get('conflicts_resolved') is not True: raise ValueError('规则冲突尚未解决')
    path, snapshot = load_snapshot(c['snapshot_file'])
    if sha(path) != c['snapshot_sha256']: raise ValueError('原始快照已变化')
    progress_file = path.parent / 'harness-progress.json'
    with locked(root):
        progress = json.loads(progress_file.read_text())
        current = next((x for x in progress['results'] if x['comment_id'] == c['comment']['id']), None)
        if not current or current.get('candidate_file') != str(cp): raise ValueError('候选已被较新的分析替代')
        if current.get('status') == 'confirmed': return current
        # Stable comment identity prevents duplicate promotion of this candidate.
        rid = 'F-' + c['id']
        folder = root / GROUPS[d['group']] / 'confirmed'; folder.mkdir(exist_ok=True)
        target = folder / (rid + '.md')
        approved = folder / (rid + '.json')
        if approved.exists() and json.loads(approved.read_text()).get('candidate_sha256') != sha(cp):
            raise ValueError('此评论已有生效规则；须明确修订旧规则，不能再追加相互冲突的规则')
        write_json(approved, {'candidate_sha256': sha(cp), 'candidate': c, 'approval': approval, 'promoted_at': now()})
        target.write_text(f'# {rid} · {LABELS[d["group"]]}\n\n状态：已确认。\n\n'
                          f'- 适用：{d["applies_when"]}\n- 规则：{d["rule"]}\n- 例外：{d["exceptions"]}\n'
                          f'- 检查证据：{d["check_evidence"]}\n- 失败处理：{d["failure_action"]}\n'
                          f'- [候选及原始评论]({cp})\n- [审核与确认记录]({approved})\n', encoding='utf-8')
        index = root / GROUPS[d['group']] / 'index.md'
        link = f'\n- [{rid}](confirmed/{rid}.md)\n'
        existing = index.read_text()
        if link not in existing:
            # Atomic replacement prevents truncation on interruption.
            fd, tmp = tempfile.mkstemp(dir=index.parent, prefix='.index-')
            with os.fdopen(fd, 'w') as out: out.write(existing + link)
            os.replace(tmp, index)
        current.update(status='confirmed', rule_id=rid, rule_file=str(target))
        progress['updated_at'] = now(); write_json(progress_file, progress)
        return current


def recapture(snapshot_path):
    path, s = load_snapshot(snapshot_path)
    from serve_video_review import ReviewStore
    review = ReviewStore(Path(s['video']['path']), Path(s['project']))
    if review.video['sha256'] != s['video']['sha256']: raise ValueError('原视频已变化，不能拿新视频补旧版证据')
    folder = path.parent / 'harness-evidence' / str(uuid.uuid4())
    result = build_intake(s, review, folder)
    manifest = Path(result['intake_file']); intake = json.loads(manifest.read_text())
    intake['snapshot_sha256'] = sha(path); write_json(manifest, intake)
    return {'evidence_manifest': str(manifest), 'evidence_manifest_sha256': sha(manifest)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture'); capture.add_argument('--snapshot', type=Path, required=True)
    record = sub.add_parser('record'); record.add_argument('--snapshot', type=Path, required=True); record.add_argument('--analysis', type=Path, required=True)
    confirm = sub.add_parser('promote'); confirm.add_argument('--candidate', type=Path, required=True); confirm.add_argument('--approval', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture': result = recapture(args.snapshot)
    elif args.command == 'record': result = record_analysis(args.snapshot, json.loads(args.analysis.read_text()))
    else: result = promote(args.candidate, json.loads(args.approval.read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
