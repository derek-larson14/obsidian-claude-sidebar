#!/usr/bin/env python3
"""PTY wrapper with resize support for Obsidian terminal plugin."""
import os
import sys
import pty
import struct
import fcntl
import termios
import select
import signal

# Global to track child PID for signal handler
child_pid = None

def cleanup_child(signum, frame):
    """Kill the child process when we receive a signal."""
    global child_pid
    if child_pid:
        try:
            os.kill(child_pid, signal.SIGTERM)
            # Give it a moment to exit gracefully
            for _ in range(10):
                pid, _ = os.waitpid(child_pid, os.WNOHANG)
                if pid != 0:
                    break
                import time
                time.sleep(0.1)
            else:
                # Force kill if still running
                os.kill(child_pid, signal.SIGKILL)
        except (ProcessLookupError, ChildProcessError):
            pass
    sys.exit(0)

def set_size(fd, cols, rows):
    """Set the PTY window size."""
    winsize = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def main():
    global child_pid

    # Parse args: terminal_pty.py [cols] [rows] [shell] [shell_args...]
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} cols rows shell [args...]", file=sys.stderr)
        sys.exit(1)

    cols = int(sys.argv[1])
    rows = int(sys.argv[2])
    shell = sys.argv[3]
    shell_args = sys.argv[3:]  # Include shell as argv[0]

    pid, fd = pty.fork()
    child_pid = pid  # Store for signal handler

    if pid == 0:
        # Child process - exec the shell
        os.execvp(shell, shell_args)
        sys.exit(1)

    # Parent process
    # Register signal handlers to clean up child on termination
    signal.signal(signal.SIGTERM, cleanup_child)
    signal.signal(signal.SIGHUP, cleanup_child)

    # Set initial size
    set_size(fd, cols, rows)

    stdin_fd = sys.stdin.fileno()

    # Make stdin non-blocking
    old_flags = fcntl.fcntl(stdin_fd, fcntl.F_GETFL)
    fcntl.fcntl(stdin_fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

    running = True
    try:
        while running:
            try:
                rlist, _, _ = select.select([fd, stdin_fd], [], [], 0.05)
            except select.error:
                break

            for ready_fd in rlist:
                if ready_fd == fd:
                    try:
                        data = os.read(fd, 16384)
                        if not data:
                            running = False
                            break
                        os.write(sys.stdout.fileno(), data)
                        sys.stdout.flush()
                    except OSError:
                        running = False
                        break
                elif ready_fd == stdin_fd:
                    try:
                        data = os.read(stdin_fd, 16384)
                        if not data:
                            # stdin closed - plugin terminated
                            running = False
                            break
                        if data:
                            # Check for resize escape sequence anywhere in data: \x1b]RESIZE;cols;rows\x07
                            while b'\x1b]RESIZE;' in data:
                                start = data.index(b'\x1b]RESIZE;')
                                try:
                                    end = data.index(b'\x07', start)
                                    resize_data = data[start+9:end].decode()
                                    c, r = resize_data.split(';')
                                    set_size(fd, int(c), int(r))
                                    # Remove the resize command from data
                                    data = data[:start] + data[end+1:]
                                except (ValueError, IndexError):
                                    break
                            if data:
                                os.write(fd, data)
                    except OSError:
                        running = False
                        break

            # Check if child exited
            try:
                wpid, status = os.waitpid(pid, os.WNOHANG)
                if wpid == pid:
                    sys.exit(os.waitstatus_to_exitcode(status))
            except ChildProcessError:
                break
    finally:
        fcntl.fcntl(stdin_fd, fcntl.F_SETFL, old_flags)
        # Ensure child is terminated when we exit
        if child_pid:
            try:
                os.kill(child_pid, signal.SIGTERM)
                for _ in range(10):
                    wpid, _ = os.waitpid(child_pid, os.WNOHANG)
                    if wpid != 0:
                        break
                    import time
                    time.sleep(0.1)
                else:
                    os.kill(child_pid, signal.SIGKILL)
            except (ProcessLookupError, ChildProcessError, OSError):
                pass

if __name__ == '__main__':
    main()
