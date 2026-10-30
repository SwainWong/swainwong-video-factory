#!/usr/bin/env python3
"""Native MCP App for a fixed video-review service; never connects to desktop pipes."""
import argparse
import json
from pathlib import Path
import secrets
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode

RESOURCE = 'ui://video-review/review.html'
MIME = 'text/html;profile=mcp-app'


def caller_thread(meta):
    if not isinstance(meta, dict): return None
    for key in ('codexThreadId', 'codex_thread_id', 'openai/threadId', 'openai/thread_id', 'threadId', 'thread_id'):
        if isinstance(meta.get(key), str) and meta[key].strip(): return meta[key]
    nested = meta.get('x-codex-turn-metadata')
    if isinstance(nested, str):
        try: nested = json.loads(nested)
        except ValueError: nested = None
    if isinstance(nested, dict) and isinstance(nested.get('thread_id'), str): return nested['thread_id']
    return None


def schema(properties=None, required=None):
    return {'type': 'object', 'properties': {'review_session': {'type': 'string'}, **(properties or {})},
            'required': required or [], 'additionalProperties': False}


class ReviewMCP:
    def __init__(self, origin, project, sha256, thread_id, frontend=None):
        parsed = urlsplit(origin)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path not in ('', '/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Review URL must be a fixed http://127.0.0.1:PORT origin')
        self.origin = origin.rstrip('/')
        self.project = str(Path(project).resolve(strict=True))
        self.sha256, self.thread_id = sha256, thread_id
        self.frontend = frontend or Path(__file__).resolve().parent.parent / 'assets/video-review-mcp.html'
        self.sessions = set()

    def http(self, method, path, payload=None):
        headers = {'Content-Type': 'application/json'}
        if path in ('/api/submissions/begin-host','/api/submissions/host-result','/api/submissions/acknowledge'):
            token_path = Path(self.project) / 'review-feedback' / self.sha256 / '.mcp-api-token'
            if token_path.is_symlink() or not token_path.resolve().is_relative_to(Path(self.project)):
                raise ValueError('Invalid local MCP token path')
            headers['X-Video-Review-MCP'] = token_path.read_text().strip()
        req = Request(self.origin + path, data=None if payload is None else json.dumps(payload).encode(), method=method, headers=headers)
        try:
            with urlopen(req, timeout=15) as response: return json.load(response)
        except HTTPError as exc:
            try: detail = json.load(exc)
            except Exception: detail = {'error': str(exc)}
            raise ValueError(detail.get('error', str(exc))) from exc

    def identity(self):
        state = self.http('GET', '/api/review')
        if state.get('video', {}).get('sha256') != self.sha256:
            raise ValueError('固定视频版本与审片服务不一致，请重新绑定。')
        if state.get('project') != self.project:
            raise ValueError('审片服务项目不匹配。')
        if state.get('submission_info', {}).get('thread_id') != self.thread_id:
            raise ValueError('审片服务绑定的对话不匹配。')
        return state

    def context(self, args, meta, create=False):
        actual = caller_thread(meta)
        if actual is not None and actual != self.thread_id:
            raise ValueError('此审片项目绑定到另一条 Codex 对话，拒绝跨对话提交。')
        token = args.get('review_session')
        verified = actual == self.thread_id or (isinstance(token, str) and token in self.sessions)
        if verified and create and token not in self.sessions:
            token = secrets.token_urlsafe(32); self.sessions.add(token)
        return {'caller_thread_verified': verified, 'expected_thread_id': self.thread_id,
                'review_session': token if verified else None,
                'reason': '' if verified else '宿主未提供可核实的当前对话身份；可审片和预览，暂不能从此页面提交。'}

    def require_session(self, args, meta):
        context = self.context(args, meta)
        if not context['caller_thread_verified']: raise ValueError(context['reason'])

    def tools(self):
        string = {'type': 'string'}
        base = {'expected_video_sha256': string}
        defs = [
            ('open_video_review', '打开绑定项目的视频审片页面；必须从该项目对应的 Codex 对话调用。', schema(), None),
            ('review_get_state', '刷新审片状态。', schema(), 'app'),
            ('review_add_comment', '保存一条视频评论。', schema({**base, 'start': {'type': 'number'}, 'end': {'type': 'number'},
                **{key: string for key in ('observation', 'suggestion', 'general_preference', 'category', 'scope')}}, ['expected_video_sha256','start','end','observation']), 'app'),
            ('review_delete_comment', '删除尚可编辑的评论原件；提交快照不受影响。', schema({**base, 'id': string}, ['id','expected_video_sha256']), 'app'),
            ('review_preview_submission', '汇总选择的评论为不可变消息预览。', schema({**base, 'comment_ids': {'type': 'array', 'items': string}}, ['expected_video_sha256','comment_ids']), 'app'),
            ('review_begin_host_submission', '锁定本轮评论准备由原生页面 ui/message 发送；本工具不会发送消息。', schema({**base, 'preview_id': string, 'idempotency_key': string}, ['expected_video_sha256','preview_id','idempotency_key']), 'app'),
            ('review_record_host_result', '记录 ui/message 宿主响应；不代表 Agent 已收到或完成。', schema({**base, 'id': string, 'status': {'enum':['host_accepted','failed','unknown']}, 'receipt': {'type':['object','null']}, 'error': {'type':['string','null']}}, ['expected_video_sha256','id','status']), 'app'),
            ('review_get_submission', '查询本轮评论提交状态。', schema({'id': string}, ['id']), 'app'),
            ('review_acknowledge_submission', '仅在当前对话实际收到带提交号的审片用户消息后调用，确认 Agent 已收到；不代表修订完成。', schema({**base,'id':string}, ['id','expected_video_sha256']), 'model'),
        ]
        out = []
        for name, description, input_schema, visibility in defs:
            item = dict(name=name, description=description, inputSchema=input_schema)
            if name == 'open_video_review': item['_meta'] = {'ui': {'resourceUri': RESOURCE}}
            elif visibility: item['_meta'] = {'ui': {'visibility': [visibility]}}
            out.append(item)
        return out

    def call(self, name, args, meta):
        if name not in {item['name'] for item in self.tools()}: raise ValueError('Unknown review tool')
        if not isinstance(args, dict): raise ValueError('Tool arguments must be an object')
        state = self.identity()
        context = self.context(args, meta, create=name in ('open_video_review','review_get_state'))
        if name in ('open_video_review','review_get_state'):
            state['video']['url'] = self.origin + '/video?' + urlencode({'sha256': self.sha256})
            state['mcp_context'] = context
            state['mcp_context']['review_origin'] = self.origin
            return state
        if name in ('review_begin_host_submission','review_record_host_result'):
            self.require_session(args, meta)
        if name == 'review_acknowledge_submission' and caller_thread(meta) != self.thread_id:
            raise ValueError('Agent 接收确认必须具有匹配的当前对话元数据。')
        if name != 'review_get_submission' and args.get('expected_video_sha256') != self.sha256:
            raise ValueError('视频版本不匹配。')
        clean = {k:v for k,v in args.items() if k != 'review_session'}
        routes = {'review_add_comment':'/api/comments','review_preview_submission':'/api/submissions/preview',
                  'review_begin_host_submission':'/api/submissions/begin-host','review_record_host_result':'/api/submissions/host-result',
                  'review_acknowledge_submission':'/api/submissions/acknowledge'}
        if name in routes: return self.http('POST', routes[name], clean)
        sid = args.get('id')
        import re
        if not isinstance(sid, str) or not re.fullmatch('[0-9a-f-]{36}', sid): raise ValueError('无效记录编号。')
        if name == 'review_delete_comment':
            return self.http('DELETE', '/api/comments/' + sid + '?' + urlencode({'expected_video_sha256': self.sha256}))
        return self.http('GET', '/api/submissions/' + sid)

    def handle(self, request):
        method, params = request.get('method'), request.get('params') or {}
        if method == 'initialize':
            version = params.get('protocolVersion')
            if version not in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25'): version = '2024-11-05'
            return {'protocolVersion':version,'capabilities':{'tools':{},'resources':{}},
                    'serverInfo':{'name':'video-review','version':'1.0.0'},
                    'instructions':'审片项目绑定到一个对话和视频版本。仅在实际收到审片用户消息后使用 review_acknowledge_submission。'}
        if method == 'ping': return {}
        if method == 'tools/list': return {'tools':self.tools()}
        if method == 'resources/list': return {'resources':[{'uri':RESOURCE,'name':'Video review','mimeType':MIME}]}
        if method == 'resources/read':
            if params.get('uri') != RESOURCE: raise ValueError('Unknown resource')
            return {'contents':[{'uri':RESOURCE,'mimeType':MIME,'text':self.frontend.read_text(),
                     '_meta':{'ui':{'csp':{'resourceDomains':[self.origin], 'connectDomains':[self.origin]}, 'prefersBorder':True}}}]}
        if method == 'tools/call':
            try:
                result = self.call(params.get('name'), params.get('arguments',{}), params.get('_meta',{}))
                return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False)}],'structuredContent':result,'isError':False}
            except Exception as exc:
                return {'content':[{'type':'text','text':str(exc)}],'isError':True}
        raise ValueError('Unsupported MCP method')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-url', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--video-sha256', required=True)
    parser.add_argument('--thread-id', required=True)
    args = parser.parse_args()
    app = ReviewMCP(args.review_url, args.project, args.video_sha256, args.thread_id)
    for line in sys.stdin:
        request = None
        try:
            request = json.loads(line)
            if 'id' not in request: continue
            response = {'jsonrpc':'2.0','id':request['id'],'result':app.handle(request)}
        except Exception as exc:
            response = {'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,
                        'error':{'code':-32602,'message':str(exc)}}
        print(json.dumps(response,ensure_ascii=False),flush=True)


if __name__ == '__main__': main()
