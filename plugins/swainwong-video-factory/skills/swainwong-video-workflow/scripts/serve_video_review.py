#!/usr/bin/env python3
"""Local, file-backed review for one immutable rendered video. Python stdlib only.

Usage: python3 serve_video_review.py --video /absolute/final.mp4 --project /absolute/project
Comments remain project feedback; long_term_candidate never changes a skill or memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit
import uuid
from review_submissions import SubmissionStore, SubmissionConflict, UnavailableBridge

MAX_BODY = 64 * 1024
MAX_COMMENTS = 5000


def review_audience_status(state, video_sha256, audience):
    """Separate an internal diagnostic surface from an owner-acceptance surface."""
    if audience == 'internal':
        return {
            'audience': 'internal',
            'owner_review_ready': False,
            'label': 'INTERNAL DIAGNOSTIC — not owner review or delivery',
        }
    if audience != 'owner':
        raise ValueError('review audience must be internal or owner')
    readiness = state.get('stages', {}).get('owner-review-ready', {})
    if readiness.get('status') != 'READY':
        raise ValueError('owner-review-ready must be READY before starting an owner review page')
    artifacts = readiness.get('artifacts')
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ValueError('owner-review-ready must contain exactly one readiness artifact')
    path = Path(artifacts[0].get('path', ''))
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('owner-review-ready artifact is unreadable') from exc
    if report.get('schema') != 'swainwong.owner-review-ready.v1':
        raise ValueError('owner-review-ready artifact schema mismatch')
    if report.get('candidate_sha256') != video_sha256:
        raise ValueError('owner review candidate hash does not match owner-review-ready')
    return {
        'audience': 'owner',
        'owner_review_ready': True,
        'label': 'OWNER REVIEW — internal gates passed for this exact candidate',
    }


def configure_mcp_access(server):
    """Keep privileged delivery/Agent acknowledgement state off the browser API."""
    token = secrets.token_urlsafe(32)
    target = server.store.directory / '.mcp-api-token'
    if target.is_symlink(): raise ValueError('MCP token cannot be a symbolic link')
    fd, temporary = tempfile.mkstemp(prefix='.mcp-token-', dir=server.store.directory)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(token)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    server.mcp_token = token


class ReviewStore:
    def __init__(self, video: Path, project: Path):
        self.path = video.resolve(strict=True)
        if not self.path.is_file():
            raise ValueError('Video must be a regular file')
        self.project = project.resolve(strict=True)
        if not self.project.is_dir():
            raise ValueError('Project must be a directory')
        self.signature = self.file_signature()
        digest = hashlib.sha256()
        with self.path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'format=duration:stream=avg_frame_rate,duration', '-of', 'json', str(self.path)],
            check=True, capture_output=True, text=True, timeout=60)
        info = json.loads(probe.stdout)
        streams = info.get('streams', [])
        if not streams:
            raise ValueError('No video stream found')
        duration = float(info.get('format', {}).get('duration') or streams[0].get('duration', 0))
        rate = streams[0].get('avg_frame_rate', '0/1').split('/')
        fps = float(rate[0]) / float(rate[1]) if len(rate) == 2 and float(rate[1]) else 0.0
        if not math.isfinite(duration) or duration <= 0 or not math.isfinite(fps) or fps <= 0:
            raise ValueError('ffprobe did not return valid duration and frame rate')
        if self.signature != self.file_signature():
            raise ValueError('Video changed while being identified; restart after rendering finishes')
        self.video = dict(sha256=digest.hexdigest(), path=str(self.path),
                          title=self.path.stem, duration=duration, fps=fps,
                          url='/video?sha256=' + digest.hexdigest())
        self.directory = self.project / 'review-feedback' / digest.hexdigest()
        # Refuse a feedback-directory symlink escaping the intended project.
        if not self.directory.resolve().is_relative_to(self.project):
            raise ValueError('Feedback directory must remain within project')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.comments_file = self.directory / 'comments.json'
        if self.comments_file.is_symlink():
            raise ValueError('Comments file cannot be a symbolic link')
        self.lock = threading.RLock()
        self.comments = []
        if self.comments_file.exists():
            payload = json.loads(self.comments_file.read_text(encoding='utf-8'))
            if payload.get('video', {}).get('sha256') != self.video['sha256']:
                raise ValueError('Stored feedback belongs to a different video')
            self.comments = payload['comments']
            if not isinstance(self.comments, list) or len(self.comments) > MAX_COMMENTS:
                raise ValueError('Invalid stored comments')

    def file_signature(self):
        stat = self.path.stat()
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def snapshot(self):
        with self.lock:
            return dict(schema_version=1, project=str(self.project), comments_file=str(self.comments_file), video=dict(self.video), comments=list(self.comments), review_access=dict(getattr(self, 'review_access', {})))

    def persist(self):
        fd, temporary = tempfile.mkstemp(prefix='.comments-', suffix='.tmp', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.snapshot(), stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.comments_file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add(self, incoming):
        if not isinstance(incoming, dict):
            raise ValueError('Comment must be a JSON object')
        comment = {}
        for field in ('start', 'end'):
            value = incoming.get(field)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f'{field} must be finite seconds')
            comment[field] = float(value)
        if not 0 <= comment['start'] <= comment['end'] <= self.video['duration']:
            raise ValueError('Time range must satisfy 0 <= start <= end <= video duration')
        for field, limit in [('observation', 8000), ('suggestion', 8000),
                             ('general_preference', 8000), ('category', 80)]:
            value = incoming.get(field, '')
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError(f'{field} must be text, at most {limit} characters')
            comment[field] = value.strip()
        if not comment['observation']:
            raise ValueError('observation is required')
        comment['harness_target'] = incoming.get('harness_target', 'auto')
        from harness_feedback import LABELS
        if not isinstance(comment['harness_target'], str) or comment['harness_target'] not in LABELS:
            raise ValueError('Invalid harness_target')
        comment['scope'] = incoming.get('scope', 'project')
        if comment['scope'] not in ('project', 'long_term_candidate'):
            raise ValueError('scope must be project or long_term_candidate')
        comment.update(id=str(uuid.uuid4()), created_at=datetime.now(timezone.utc).isoformat())
        with self.lock:
            if len(self.comments) >= MAX_COMMENTS:
                raise ValueError('Comment limit reached; export feedback before continuing')
            self.comments.append(comment)
            try:
                self.persist()
            except Exception:
                self.comments.pop()
                raise
        return comment

    def delete(self, comment_id):
        with self.lock:
            previous = self.comments
            self.comments = [c for c in previous if c['id'] != comment_id]
            if len(previous) == len(self.comments):
                return False
            try:
                self.persist()
            except Exception:
                self.comments = previous
                raise
            return True


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = 'LocalVideoReview/1.0'
    protocol_version = 'HTTP/1.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def common_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    def respond(self, status, data=b'', content_type='application/json; charset=utf-8', headers=None):
        self.send_response(status)
        self.common_headers()
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def json_response(self, status, data, headers=None):
        self.respond(status, json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8'), headers=headers)

    def reject(self, status, message, error_code=None):
        self.close_connection = True
        payload = {'error': message}
        if error_code: payload['error_code'] = error_code
        self.json_response(status, payload)

    def allowed_request(self):
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host', '').lower() not in allowed:
            self.reject(403, 'Only this local server host is allowed')
            return False
        origin = self.headers.get('Origin')
        if origin and origin.lower() not in {f'http://{host}' for host in allowed}:
            self.reject(403, 'Cross-origin requests are not allowed')
            return False
        # Opening the review link is safe; cross-site API/media requests remain blocked.
        document_navigation = (self.command in ('GET', 'HEAD') and urlsplit(self.path).path in ('/', '/video-review.html')
                               and self.headers.get('Sec-Fetch-Mode') == 'navigate'
                               and self.headers.get('Sec-Fetch-Dest') == 'document')
        if self.headers.get('Sec-Fetch-Site') == 'cross-site' and not document_navigation:
            self.reject(403, 'Cross-site requests are not allowed')
            return False
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or '\\' in unquote(parsed.path) or '..' in unquote(parsed.path).split('/'):
            self.reject(400, 'Invalid request path')
            return False
        return True

    def version_matches(self, expected):
        store = self.server.store
        if not isinstance(expected, str) or expected != store.video['sha256']:
            self.reject(409, 'Video version mismatch. Refresh and review the current video before submitting feedback.', 'video_version_mismatch')
            return False
        try:
            unchanged = store.file_signature() == store.signature
        except OSError:
            unchanged = False
        if not unchanged:
            self.reject(409, 'Video file changed or disappeared. Restart the review server and review the new version.', 'video_version_mismatch')
            return False
        return True

    def query_value(self, name):
        values = parse_qs(urlsplit(self.path).query, keep_blank_values=True).get(name, [])
        return values[0] if len(values) == 1 else None

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.allowed_request():
            return
        path = urlsplit(self.path).path
        if path in ('/', '/video-review.html'):
            try:
                self.respond(200, self.server.frontend.read_bytes(), 'text/html; charset=utf-8')
            except FileNotFoundError:
                self.reject(503, 'Review frontend is not installed')
        elif path in ('/api/review', '/api/export'):
            headers = {'Content-Disposition': f'attachment; filename="review-{self.server.store.video["sha256"][:12]}.json"'} if path.endswith('/export') else None
            data = self.server.store.snapshot()
            data['submission_info'] = self.server.submissions.info()
            self.json_response(200, data, headers)
        elif re.fullmatch(r'/api/submissions/[0-9a-f-]{36}', path):
            try:
                self.json_response(200, {'submission': self.server.submissions.get(path.rsplit('/', 1)[1])})
            except KeyError:
                self.reject(404, 'Submission not found')
        elif re.fullmatch(r'/api/evidence/[0-9a-f-]{36}/[0-9]{3}-(frame.jpg|clip.mp4)', path):
            sid, name = path.split('/')[-2:]
            try:
                record = self.server.submissions.get(sid)
                allowed = {Path(f['path']).name: f for item in record.get('harness', {}).get('items', [])
                           for f in item['evidence']['files']}
                if name not in allowed: raise KeyError(name)
                evidence = self.server.submissions.directory / sid / 'evidence' / name
                from harness_feedback import sha
                if evidence.is_symlink() or not evidence.resolve().is_relative_to(self.server.submissions.directory.resolve()):
                    raise KeyError(name)
                if sha(evidence) != allowed[name]['sha256']:
                    self.reject(409, 'Evidence changed', 'evidence_changed'); return
                self.respond(200, evidence.read_bytes(), 'image/jpeg' if name.endswith('.jpg') else 'video/mp4')
            except (KeyError, OSError): self.reject(404, 'Evidence not found')
        elif path == '/video':
            self.serve_video()
        else:
            self.reject(404, 'Not found')

    def serve_video(self):
        store = self.server.store
        if not self.version_matches(self.query_value('sha256')):
            return
        size = store.signature[2]
        start, end, status = 0, size - 1, 200
        etag = '"' + store.video['sha256'] + '"'
        requested_range = self.headers.get('Range')
        if requested_range and self.headers.get('If-Range', etag) == etag:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested_range.strip())
            if not match or not any(match.groups()):
                self.respond(416, headers={'Content-Range': f'bytes */{size}'})
                return
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            else:
                count = int(last)
                start, end = max(0, size - count), size - 1
                if count == 0:
                    start = size
            if start >= size or start > end:
                self.respond(416, headers={'Content-Range': f'bytes */{size}'})
                return
            status = 206
        self.send_response(status)
        self.common_headers()
        self.send_header('Content-Type', mimetypes.guess_type(store.path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('ETag', etag)
        self.send_header('Content-Length', str(end - start + 1))
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with store.path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = stream.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass  # Seeking commonly cancels the previous media request.

    def do_POST(self):
        if not self.allowed_request():
            return
        path = urlsplit(self.path).path
        if path not in ('/api/comments', '/api/submissions/preview', '/api/submissions', '/api/submissions/begin-host', '/api/submissions/host-result', '/api/submissions/acknowledge'):
            self.reject(404, 'Not found')
            return
        if path in ('/api/submissions/begin-host', '/api/submissions/host-result', '/api/submissions/acknowledge'):
            token = getattr(self.server, 'mcp_token', None)
            if not token or not secrets.compare_digest(self.headers.get('X-Video-Review-MCP', ''), token):
                self.reject(403, 'This delivery endpoint is available only through the bound MCP App')
                return
        if self.headers.get('Transfer-Encoding'):
            self.reject(400, 'Transfer-Encoding is not supported')
            return
        if self.headers.get_content_type() != 'application/json':
            self.reject(415, 'Content-Type must be application/json')
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            self.reject(413, 'JSON body must be between 1 and 65536 bytes')
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Incomplete request body')
            incoming = json.loads(raw)
            if not isinstance(incoming, dict):
                raise ValueError('Comment must be a JSON object')
            if not self.version_matches(incoming.get('expected_video_sha256')):
                return
            if path == '/api/comments':
                result = {'comment': self.server.store.add(incoming)}
                status = 201
            elif path == '/api/submissions/preview':
                result = self.server.submissions.preview(incoming.get('comment_ids'))
                status = 201
            elif path == '/api/submissions/begin-host':
                result = {'submission': self.server.submissions.submit(incoming.get('preview_id'), incoming.get('idempotency_key'), 'mcp_ui_message')}
                status = 202 if result['submission']['status'] == 'sending' else 200
            elif path == '/api/submissions/host-result':
                result = {'submission': self.server.submissions.record_host_result(incoming.get('id'), incoming.get('status'), incoming.get('receipt'), incoming.get('error'))}
                status = 200
            elif path == '/api/submissions/acknowledge':
                result = {'submission': self.server.submissions.acknowledge(incoming.get('id'))}
                status = 200
            else:
                result = {'submission': self.server.submissions.submit(incoming.get('preview_id'), incoming.get('idempotency_key'))}
                status = 202 if result['submission']['status'] == 'sending' else 200
        except SubmissionConflict as exc:
            self.reject(422, str(exc), 'submission_conflict')
            return
        except (ValueError, UnicodeError) as exc:
            self.reject(400, str(exc))
            return
        except OSError:
            self.reject(500, 'Could not save feedback to project')
            return
        self.json_response(status, result)

    def do_DELETE(self):
        if not self.allowed_request():
            return
        path = urlsplit(self.path).path
        match = re.fullmatch(r'/api/comments/([0-9a-f-]{36})', path)
        if not match:
            self.reject(404, 'Not found')
            return
        # This endpoint never consumes a body, preventing HTTP request desynchronization.
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Length', '0') != '0':
            self.reject(400, 'DELETE does not accept a body')
            return
        if not self.version_matches(self.query_value('expected_video_sha256')):
            return
        try:
            deleted = self.server.store.delete(match[1])
        except OSError:
            self.reject(500, 'Could not save feedback to project')
            return
        self.json_response(200 if deleted else 404, {'deleted': match[1]} if deleted else {'error': 'Comment not found'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--audience', choices=('internal', 'owner'), default='internal',
                        help='Internal is diagnostic only; owner requires the hash-bound owner-review-ready gate')
    parser.add_argument('--thread-id', help='Trusted target Codex thread; never accepted from the browser')
    parser.add_argument('--delivery-mode', choices=('codex-queue', 'native-mcp-app', 'official-bridge'), default='codex-queue',
                        help='Official Codex CLI queue by default; no desktop pipe probing')
    args = parser.parse_args()
    if not args.video.is_absolute() or not args.project.is_absolute():
        parser.error('--video and --project must be absolute paths')
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    try:
        store = ReviewStore(args.video, args.project)
        if args.audience == 'owner':
            from workflow_state import get_state
            store.review_access = review_audience_status(get_state(args.project), store.video['sha256'], args.audience)
        else:
            store.review_access = review_audience_status({}, store.video['sha256'], args.audience)
        bridge = UnavailableBridge()
        bridge.reason = '普通浏览器页面支持保存和预览；请在对应 Codex 对话打开原生审片页面提交评论。'
        if args.thread_id and args.delivery_mode == 'codex-queue':
            from codex_queue_bridge import CodexQueueBridge
            bridge = CodexQueueBridge(args.thread_id)
        elif args.thread_id and args.delivery_mode == 'official-bridge':
            from codex_review_bridge import CodexReviewBridge
            bridge = CodexReviewBridge(args.thread_id)
        submissions = SubmissionStore(store, args.thread_id, bridge, api_url=f'http://127.0.0.1:{args.port}')
        server = ReviewServer(('127.0.0.1', args.port), Handler)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'Unable to start video review: {exc}\n')
    server.store = store
    try:
        configure_mcp_access(server)
    except (OSError, ValueError) as exc:
        server.server_close()
        parser.exit(1, f'Unable to initialize MCP App access: {exc}\n')
    server.submissions = submissions
    server.frontend = Path(__file__).resolve().parent.parent / 'assets' / 'video-review.html'
    print(f'Video review: http://127.0.0.1:{args.port}/', flush=True)
    print(f'Review audience: {store.review_access["label"]}', flush=True)
    print(f'Video SHA256: {store.video["sha256"]}\nFeedback: {store.comments_file}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
