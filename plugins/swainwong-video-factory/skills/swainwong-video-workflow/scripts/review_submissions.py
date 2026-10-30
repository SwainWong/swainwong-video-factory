"""Immutable review rounds and durable, at-most-once dispatch state."""
from __future__ import annotations
import copy
import json
import os
import shlex
from urllib.parse import urlsplit
from pathlib import Path
import tempfile
import threading
from datetime import datetime, timezone
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    fd, tmp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


class SubmissionConflict(ValueError):
    pass


class UnavailableBridge:
    available = False
    reason = '尚未连接可验证的 Codex 对话发送接口；评论仍保存在本项目。'
    thread_title = ''


class SubmissionStore:
    def __init__(self, review, thread_id=None, bridge=None, *, api_url=None):
        self.review, self.thread_id = review, thread_id
        # Bound by the server, never by browser payload or HTTP Host.
        if api_url is not None:
            parsed = urlsplit(api_url)
            if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path not in ('', '/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Review API URL must be http://127.0.0.1:PORT')
        self.api_url = api_url.rstrip('/') if api_url else None
        self.bridge = bridge or UnavailableBridge()
        self.directory = review.directory / 'submissions'
        self.directory.mkdir(exist_ok=True)
        if not self.directory.resolve().is_relative_to(review.project):
            raise ValueError('Submissions directory escapes project')
        self.lock = threading.RLock()
        self.records = {}
        for path in self.directory.glob('*/state.json'):
            if path.is_symlink() or not path.resolve().is_relative_to(self.directory):
                raise ValueError('Invalid submission state path')
            state = json.loads(path.read_text())
            snapshot = json.loads((path.parent / 'snapshot.json').read_text())
            if snapshot['video']['sha256'] != review.video['sha256']:
                raise ValueError('Submission belongs to another video')
            if state['status'] == 'sending':
                state.update(status='unknown', error='服务重启时发送尚未确认；请核对目标对话，禁止盲目重发。', updated_at=now())
                atomic_json(path, state)
            self.records[snapshot['id']] = (snapshot, state)

    def public(self, item):
        snapshot, state = item
        result = {**copy.deepcopy(snapshot), **copy.deepcopy(state)}
        progress = self.directory / snapshot['id'] / 'harness-progress.json'
        if progress.exists():
            try:
                report = json.loads(progress.read_text())
                if report.get('submission_id') == snapshot['id'] and report.get('video_sha256') == snapshot['video']['sha256']:
                    result['harness_progress'] = report
            except (OSError, ValueError): pass
        return result

    def info(self):
        with self.lock, self.review.lock:
            blocked = self.blocked_ids()
            return dict(thread_id=self.thread_id, thread_title=getattr(self.bridge, 'thread_title', ''),
                        available=bool(self.thread_id and self.bridge.available), reason=self.bridge.reason,
                        pending_comment_ids=[c['id'] for c in self.review.comments if c['id'] not in blocked],
                        submissions=[self.public(v) for v in self.records.values() if v[1]['status'] != 'preview'])

    def blocked_ids(self):
        return {i for s, t in self.records.values() if t['status'] in ('sending', 'sent', 'unknown', 'host_accepted', 'agent_received', 'queued') for i in s['comment_ids']}

    def get(self, sid):
        with self.lock:
            if sid not in self.records: raise KeyError(sid)
            return self.public(self.records[sid])

    def preview(self, ids):
        with self.lock, self.review.lock:
            if not self.thread_id: raise SubmissionConflict('未绑定目标 Codex 对话，无法组织提交。')
            if not isinstance(ids, list) or not ids or len(ids) > 500 or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
                raise SubmissionConflict('请选择 1–500 条不同的待提交评论。')
            by_id = {c['id']: c for c in self.review.comments}
            if any(i not in by_id or i in self.blocked_ids() for i in ids):
                raise SubmissionConflict('评论不存在或已经提交/正在发送，请刷新评论记录。')
            selected = sorted((copy.deepcopy(by_id[i]) for i in ids), key=lambda c: (c['start'], c['created_at']))
            sid = str(uuid.uuid4())
            folder = self.directory / sid
            folder.mkdir()
            snapshot = dict(id=sid, preview_id=sid, created_at=now(), thread_id=self.thread_id,
                            video=copy.deepcopy(self.review.video), project=str(self.review.project),
                            comments_file=str(self.review.comments_file), comment_ids=[c['id'] for c in selected], comments=selected,
                            snapshot_file=str(folder / 'snapshot.json'),
                            api_url=self.api_url, review_url=self.api_url + '/' if self.api_url else None)
            from harness_feedback import build_intake
            snapshot['harness'] = build_intake(snapshot, self.review)
            snapshot['message'] = self.compose(snapshot)
            state = dict(status='preview', updated_at=now(), idempotency_key=None, error=None, receipt=None)
            atomic_json(folder / 'snapshot.json', snapshot)
            atomic_json(folder / 'state.json', state)
            (folder / 'message.md').write_text(snapshot['message'], encoding='utf-8')
            self.records[sid] = (snapshot, state)
            return self.public(self.records[sid])

    @staticmethod
    def compose(s):
        def stamp(sec):
            minutes, seconds = divmod(sec, 60)
            return f'{int(minutes):02d}:{seconds:06.3f}'
        lines = [f'我通过视频审片页提交了本轮反馈（提交号：{s["id"]}）。',
                 '请先确认接收，再按 $swainwong-video-workflow 处理以下反馈。',
                 f'目标 Codex 对话 ID：{s["thread_id"]}。接收方请核对当前对话；不一致则停止处理。',
                 f'若 review_acknowledge_submission 工具可用，请用本提交号及视频 SHA-256 确认已收到；宿主接收或队列回执不等于 Agent 已收到。',
                 '若该工具尚未加载，可使用 skill/scripts/acknowledge_video_feedback.py，依据此快照的项目、视频哈希、目标对话和提交号执行接收确认。只有实际收到本消息后才确认。',
                 f'项目：{s["project"]}', f'视频：{s["video"]["path"]}', f'视频 SHA-256：{s["video"]["sha256"]}',
                 f'不可变反馈快照：{s["snapshot_file"]}', f'原评论文件：{s["comments_file"]}', '',
                 '请先核对视频版本，按下列时码实际查看画面/片段；需要截图时从该视频提取，无需我逐帧截图。',
                 '保持本期已锁定制作条件；将具体修改派给对应岗位，完成后重新审核并提供新版本审片入口。',
                 '“长期偏好候选”须整理成通用规则并回报，不能将普通本期意见自动写成永久偏好。',
                 '若意见含歧义、相互冲突或改变已锁定核心条件，先指出具体冲突；不要把本轮评论提交当作整片验收通过。', '']
        if s.get('api_url'):
            command = shlex.join(['python3', str(Path(__file__).resolve().with_name('acknowledge_video_feedback.py')),
                                  '--api-url', s['api_url'], '--project', s['project'],
                                  '--video-sha256', s['video']['sha256'], '--thread-id', s['thread_id'],
                                  '--submission-id', s['id']])
            lines += [f'本版审片页：{s["review_url"]}',
                      '本版接收确认命令（实际收到后执行；必须使用本版 API 地址，不能套用旧版端口）：',
                      '```sh', command, '```', '']
        if s.get('harness'):
            lines += [f'持续沉淀入口：{s["harness"]["entry"]}',
                      f'本轮证据与待解析项：{s["harness"]["intake_file"]}',
                      '请读取 skill/references/harness-feedback.md，查看已提取的截图／片段及未覆盖区间，再逐条理解反馈。',
                      '每条反馈区分：已有规则未执行／仅本期返修／新增规则候选／证据不足；候选归入一定要做、推荐做、一定不能做、验收与失败处理之一。',
                      '页面指定的类别是用户意图，不是自动生效规则。请保留原评论、范围、例外、检查证据、失败处理和冲突检查。',
                      '分析后用 skill/scripts/harness_feedback.py record 写回项目处理结果及四类候选目录；已有规则优先引用，不重复造规则。',
                      '候选经独立审核与用户明确确认具体条款及范围后才能 promote；本轮提交本身不等于确认任何新长期规则。', '']
        for n, c in enumerate(s['comments'], 1):
            position = stamp(c['start']) if c['start'] == c['end'] else f'{stamp(c["start"])}–{stamp(c["end"])}'
            scope = '长期偏好候选（仍需确认）' if c['scope'] == 'long_term_candidate' else '仅本期'
            lines += [f'{n}. [{position}] {c["category"] or "其他"}（评论 ID：{c["id"]}）',
                      f'具体观察：{c["observation"]}', f'建议修改：{c["suggestion"] or "未填写，请结合具体观察判断"}',
                      f'可沉淀的通用偏好：{c["general_preference"] or "未填写"}', f'适用范围：{scope}',
                      f'Harness 归类意向：{c.get("harness_target", "auto")}', '']
            if s.get('harness'):
                item = next(i for i in s['harness']['items'] if i['comment_id'] == c['id'])
                evidence = item['evidence']
                lines += [f'取证状态：{evidence["status"]}；原选区：{evidence["selected_interval"]}', evidence.get('error', evidence['note'])]
                for f in evidence['files']:
                    lines.append(f'证据 {f["kind"]}：{f["path"]}（SHA-256 {f["sha256"]}；时间 {f.get("interval", f.get("at_seconds"))}）')
                lines.append('')
        lines.append(f'[video-review-submission:{s["id"]}]')
        return '\n'.join(lines)

    def submit(self, preview_id, key, transport=None):
        transport = transport or getattr(self.bridge, 'transport', 'official_mcp_bridge')
        if not isinstance(key, str) or not 8 <= len(key) <= 120:
            raise SubmissionConflict('缺少有效的提交幂等编号。')
        if not isinstance(preview_id, str):
            raise SubmissionConflict('缺少有效的预览编号。')
        with self.lock, self.review.lock:
            for snapshot, state in self.records.values():
                if state.get('idempotency_key') == key:
                    if snapshot['id'] != preview_id: raise SubmissionConflict('此提交编号已用于另一轮反馈。')
                    return self.public((snapshot, state))
            if preview_id not in self.records: raise SubmissionConflict('提交预览不存在，请重新生成预览。')
            snapshot, state = self.records[preview_id]
            if state['status'] != 'preview': raise SubmissionConflict('该反馈已执行过发送，请查看提交状态，不要重复发送。')
            if snapshot['thread_id'] != self.thread_id: raise SubmissionConflict('目标对话已改变，请重新生成预览。')
            by_id = {c['id']: c for c in self.review.comments}
            if any(by_id.get(c['id']) != c or c['id'] in self.blocked_ids() for c in snapshot['comments']):
                raise SubmissionConflict('预览中的评论已改变、删除或提交，请重新生成预览。')
            state.update(idempotency_key=key, updated_at=now(), transport=transport)
            if transport != 'mcp_ui_message' and not self.bridge.available:
                state.update(status='failed', error=self.bridge.reason)
            else:
                state.update(status='sending', error=None)
            atomic_json(self.directory / preview_id / 'state.json', state)
            if state['status'] == 'sending' and transport != 'mcp_ui_message':
                threading.Thread(target=self.dispatch, args=(preview_id,), daemon=True).start()
            return self.public((snapshot, state))

    def record_host_result(self, sid, status, receipt=None, error=None):
        if status not in ('host_accepted', 'failed', 'unknown'):
            raise SubmissionConflict('不支持的宿主提交状态。')
        with self.lock:
            if not isinstance(sid, str) or sid not in self.records:
                raise SubmissionConflict('提交记录不存在。')
            snapshot, state = self.records[sid]
            if state.get('transport') != 'mcp_ui_message':
                raise SubmissionConflict('该记录不是原生审片页面提交。')
            if state['status'] in ('host_accepted', 'agent_received'):
                return self.public((snapshot, state))
            if state['status'] not in ('sending', 'unknown'):
                raise SubmissionConflict('该提交已结束，不能覆盖结果。')
            if status == 'host_accepted':
                if not isinstance(receipt, dict) or receipt.get('method') != 'ui/message' or not isinstance(receipt.get('response'), dict) or receipt['response'].get('isError') is True:
                    raise SubmissionConflict('缺少有效的 ui/message 宿主响应。')
                receipt = {**copy.deepcopy(receipt), 'meaning': '页面收到宿主接受消息的响应；尚未证实 Agent 收到或完成处理。'}
            elif status == 'failed' and state['status'] == 'unknown':
                raise SubmissionConflict('结果未知的提交不能降为失败并重发。')
            state.update(status=status, receipt=receipt, error=str(error)[:2000] if error else None, updated_at=now())
            atomic_json(self.directory / sid / 'state.json', state)
            return self.public((snapshot, state))

    def acknowledge(self, sid):
        with self.lock:
            if not isinstance(sid, str) or sid not in self.records:
                raise SubmissionConflict('提交记录不存在。')
            snapshot, state = self.records[sid]
            if snapshot['thread_id'] != self.thread_id:
                raise SubmissionConflict('提交不属于绑定对话。')
            if state['status'] not in ('sending', 'host_accepted', 'unknown', 'agent_received', 'queued'):
                raise SubmissionConflict('该提交尚未进入消息发送流程。')
            state.update(status='agent_received', agent_receipt={'thread_id': self.thread_id, 'acknowledged_at': now()}, updated_at=now())
            atomic_json(self.directory / sid / 'state.json', state)
            return self.public((snapshot, state))

    def dispatch(self, sid):
        snapshot, _ = self.records[sid]
        try:
            if self.review.signature != self.review.file_signature():
                result = dict(status='failed', error='视频文件已改变，未发送；请重启审片服务核对新版本。')
            else:
                result = self.bridge.send(snapshot['thread_id'], snapshot['message'], sid)
            if result.get('status') not in ('sent', 'failed', 'unknown', 'queued'): raise ValueError('Invalid dispatch result')
            if result['status'] in ('sent', 'queued') and not result.get('receipt'): raise ValueError('Missing Codex acceptance receipt')
        except Exception as exc:
            result = dict(status='unknown', error=f'发送结果未确认（{type(exc).__name__}）；请核对目标对话，禁止盲目重发。')
        with self.lock:
            state = self.records[sid][1]
            # An independently observed Agent receipt outranks a later queue/transport response.
            final_status = 'agent_received' if state['status'] == 'agent_received' else result['status']
            transport_error = result.get('error')
            state.update(status=final_status, error=None if final_status == 'agent_received' else transport_error,
                         transport_error=transport_error, receipt=result.get('receipt'), updated_at=now())
            atomic_json(self.directory / sid / 'state.json', state)
