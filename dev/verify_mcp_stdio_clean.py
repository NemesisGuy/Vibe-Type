import os
import sys
import subprocess
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SERVER = os.path.join(PROJECT_ROOT, 'MCP', 'vibetts_mcp_server.py')


def main():
    env = os.environ.copy()
    env.setdefault('PYTHONUNBUFFERED', '1')
    env['PYTHONPATH'] = PROJECT_ROOT + os.pathsep + env.get('PYTHONPATH', '')

    proc = subprocess.Popen(
        [sys.executable, SERVER],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Read for a short time to see if any stdout appears
        start = time.time()
        stdout_data = ''
        stderr_lines = []
        while time.time() - start < 1.5:
            if proc.poll() is not None:
                break
            # Non-blocking read: use .readline with timeout-like loop
            if proc.stdout and proc.stdout.readable():
                line = proc.stdout.readline()
                if line:
                    stdout_data += line
            if proc.stderr and proc.stderr.readable():
                line = proc.stderr.readline()
                if line:
                    stderr_lines.append(line.rstrip())
            time.sleep(0.05)
    finally:
        # Terminate the process
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass

    print('STDOUT length:', len(stdout_data))
    if stdout_data:
        print('STDOUT sample:', stdout_data[:120].replace('\n', ' '))
    print('Captured STDERR lines:', len(stderr_lines))
    for l in stderr_lines[:5]:
        print('STDERR:', l)

    # Exit non-zero if stdout was polluted
    if stdout_data.strip():
        print('ERROR: MCP stdio server wrote to STDOUT unexpectedly.')
        sys.exit(1)
    print('OK: No unexpected STDOUT from MCP stdio server startup.')


if __name__ == '__main__':
    main()

