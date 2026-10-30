"""Queue feedback through the supported Codex CLI, without starting/resuming turns."""
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import uuid

DESKTOP_CODEX = Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex')
RECEIPT = re.compile(r'^Queued message ([0-9a-fA-F-]{36}) for thread ([0-9a-fA-F-]{36})\.$', re.MULTILINE)


class CodexQueueBridge:
    transport = 'codex_queue'
    thread_title = ''

    def __init__(self, thread_id, executable=DESKTOP_CODEX):
        self.thread_id = str(uuid.UUID(thread_id))
        self.executable = Path(executable)
        self.available = self.executable.is_file()
        self.reason = '' if self.available else '未找到官方桌面 Codex CLI，评论尚未加入对话队列。'

    def send(self, thread_id, message, submission_id):
        if thread_id != self.thread_id:
            return {'status': 'failed', 'error': '目标对话不匹配，未执行入队。'}
        try:
            result = subprocess.run([str(self.executable), 'queue', '--thread', self.thread_id, '--message', message],
                                    capture_output=True, text=True, timeout=30, check=False)
        except (FileNotFoundError, PermissionError) as exc:
            return {'status':'failed', 'error':f'无法启动官方 Codex CLI：{exc}'}
        except subprocess.TimeoutExpired:
            return {'status':'unknown', 'error':'官方入队调用超时，可能已经入队；请核对对话队列，禁止自动重试。'}
        except OSError as exc:
            return {'status':'unknown', 'error':f'官方入队结果未确认（{type(exc).__name__}），禁止自动重试。'}
        matches = RECEIPT.findall(result.stdout)
        if result.returncode != 0 or len(matches) != 1:
            return {'status':'unknown', 'error':'官方 CLI 未返回可核实的唯一入队回执，禁止自动重试。',
                    'receipt':{'exit_code':result.returncode,'stdout':result.stdout[-8000:],'stderr':result.stderr[-8000:]}}
        queue_id, returned_thread = matches[0]
        try:
            queue_id, returned_thread = str(uuid.UUID(queue_id)), str(uuid.UUID(returned_thread))
        except ValueError:
            return {'status':'unknown','error':'官方入队回执编号无效，禁止自动重试。'}
        if returned_thread != self.thread_id:
            return {'status':'unknown','error':'官方回执对话与绑定对话不一致，禁止自动重试。'}
        return {'status':'queued', 'receipt':{'provider':'official-codex-cli-queue', 'thread_id':returned_thread,
                'queue_id':queue_id, 'submission_id':submission_id, 'accepted_at':datetime.now(timezone.utc).isoformat(),
                'stdout':result.stdout[-8000:], 'meaning':'官方已持久化入队；等待当前回合结束后消费，尚不代表 Agent 已收到。'}}
