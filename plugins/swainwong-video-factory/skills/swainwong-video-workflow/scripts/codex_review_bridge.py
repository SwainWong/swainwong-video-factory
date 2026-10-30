"""Use only the official desktop MCP entry point; never resume in another daemon.

No extra Python packages. The caller must inherit CODEX_APP_TOOLS_PIPE_PATH
from Codex. Only server-bound thread IDs are accepted. Capability probing is
read-only. A host success receipt is required; ambiguous sends never retry.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
from datetime import datetime, timezone

PLUGIN = Path('/Applications/ChatGPT.app/Contents/Resources/plugins/openai-bundled/plugins/codex-app-tools')


class MCPError(Exception):
    pass


class OfficialMCP:
    def __init__(self, timeout=8):
        self.timeout = timeout
        self.number = 0
        self.buffer = b''
        if not os.environ.get('CODEX_APP_TOOLS_PIPE_PATH'):
            raise MCPError('缺少 Codex 提供的官方连接环境 CODEX_APP_TOOLS_PIPE_PATH')
        command = [str(PLUGIN / 'scripts/launch_codex_app_tools_mcp'), str(PLUGIN / 'server.mjs')]
        if not all(Path(p).is_file() for p in command):
            raise MCPError('未找到官方 Codex App Tools MCP 启动器')
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=os.environ.copy())
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            self.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                   'clientInfo': {'name': 'video-review', 'version': '1.0.0'}})
            self.write({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        except Exception:
            self.close()
            raise

    def write(self, value):
        self.process.stdin.write((json.dumps(value, ensure_ascii=False) + '\n').encode())
        self.process.stdin.flush()

    def rpc(self, method, params):
        self.number += 1
        rid = self.number
        self.write({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        while True:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if not line.strip(): continue
                reply = json.loads(line)
                if reply.get('id') != rid: continue
                if 'error' in reply:
                    raise MCPError(reply['error'].get('message', '官方接口返回错误'))
                return reply['result']
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError('官方 Codex 接口未在时限内回应')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk: raise MCPError('官方 MCP 连接已关闭')
            self.buffer += chunk
            if len(self.buffer) > 8 * 1024 * 1024: raise MCPError('官方接口响应过大')

    def tools(self):
        return {item['name']: item for item in self.rpc('tools/list', {}).get('tools', [])}

    def call(self, name, arguments, thread_id):
        return self.rpc('tools/call', {'name': name, 'arguments': arguments,
                                     '_meta': {'codexThreadId': thread_id}})

    def close(self):
        self.selector.close()
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream: stream.close()


def check_tools(catalog):
    for name, required in [('send_message_to_thread', {'threadId', 'prompt'}), ('read_thread', {'threadId'})]:
        schema = catalog.get(name, {}).get('inputSchema', {})
        if not required.issubset(schema.get('properties', {})):
            raise MCPError(f'官方工具目录未提供兼容的 {name} 接口')


class CodexReviewBridge:
    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.thread_title = ''
        self.available = False
        self.reason = ''
        client = None
        try:
            client = OfficialMCP()
            check_tools(client.tools())
            result = client.call('read_thread', {'threadId': thread_id, 'turnLimit': 1, 'maxOutputCharsPerItem': 500}, thread_id)
            if result.get('isError') is not False: raise MCPError('无法验证绑定的 Codex 对话')
            self.available = True
        except Exception as exc:
            self.reason = f'无法连接此 Codex 桌面对话的官方发送接口：{str(exc)[:300]}。评论仍保存在项目，尚未发送。'
        finally:
            if client: client.close()

    def send(self, thread_id, message, submission_id):
        if thread_id != self.thread_id:
            return {'status': 'failed', 'error': '目标对话与服务器绑定不一致，未发送。'}
        client = None
        attempted = False
        try:
            client = OfficialMCP(timeout=30)
            check_tools(client.tools())
            attempted = True
            result = client.call('send_message_to_thread', {'threadId': thread_id, 'prompt': message}, thread_id)
            if result.get('isError') is not False:
                # The host may have performed a side effect before returning an error.
                return {'status': 'unknown', 'error': '官方发送工具未返回成功回执；请核对目标对话，禁止盲目重发。'}
            return {'status': 'sent', 'receipt': {
                'provider': 'official-codex-app-tools-mcp', 'thread_id': thread_id,
                'submission_id': submission_id, 'tool': 'send_message_to_thread',
                'accepted_at': datetime.now(timezone.utc).isoformat(), 'result': result,
                'meaning': '官方工具已确认消息提交成功，不代表 Agent 已完成修订。'}}
        except Exception as exc:
            return {'status': 'unknown' if attempted else 'failed',
                    'error': f'官方接口未确认发送：{str(exc)[:300]}。' + ('请核对目标对话，禁止盲目重发。' if attempted else '尚未调用发送接口。')}
        finally:
            if client: client.close()
