#!/usr/bin/env python3
"""Run only after the bound Agent actually receives the marked review message."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def acknowledge(origin, project, video_sha256, thread_id, submission_id):
    # Only the actual receiving conversation may acknowledge; child agents cannot
    # substitute CODEX_SESSION_ID (their parent's ID) for their own thread identity.
    if os.environ.get('CODEX_THREAD_ID') != thread_id:
        raise ValueError('Current CODEX_THREAD_ID does not match the receiving conversation; acknowledgement refused')
    parsed = urlsplit(origin)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path not in ('','/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('API URL must be http://127.0.0.1:PORT')
    import re
    if not re.fullmatch('[0-9a-f]{64}', video_sha256) or not re.fullmatch('[0-9a-f-]{36}', submission_id):
        raise ValueError('Invalid video or submission identity')
    project = Path(project).resolve(strict=True)
    origin = origin.rstrip('/')
    def get(path):
        with urlopen(origin+path,timeout=10) as response: return json.load(response)
    state = get('/api/review')
    if state.get('project') != str(project) or state.get('video',{}).get('sha256') != video_sha256 or state.get('submission_info',{}).get('thread_id') != thread_id:
        raise ValueError('Project, video or thread differs from the received message')
    submission = get('/api/submissions/'+submission_id)['submission']
    if submission.get('thread_id') != thread_id or submission.get('video',{}).get('sha256') != video_sha256:
        raise ValueError('Submission identity differs from the received message')
    token_path = project/'review-feedback'/video_sha256/'.mcp-api-token'
    if token_path.is_symlink() or not token_path.resolve().is_relative_to(project): raise ValueError('Invalid local acknowledgement token')
    req = Request(origin+'/api/submissions/acknowledge',method='POST',
        data=json.dumps({'id':submission_id,'expected_video_sha256':video_sha256}).encode(),
        headers={'Content-Type':'application/json','X-Video-Review-MCP':token_path.read_text().strip()})
    with urlopen(req,timeout=10) as response: return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-url',default='http://127.0.0.1:8767')
    parser.add_argument('--project',required=True)
    parser.add_argument('--video-sha256',required=True)
    parser.add_argument('--thread-id',required=True)
    parser.add_argument('--submission-id',required=True)
    args = parser.parse_args()
    try:
        result = acknowledge(args.api_url,args.project,args.video_sha256,args.thread_id,args.submission_id)
    except Exception as exc:
        parser.exit(1, f'Acknowledgement failed: {exc}\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
