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

def set_size(fd, cols, rows):
    """Set the PTY window size."""
    winsize = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def main():
    # Parse args: terminal_pty.py [cols] [rows] [shell] [shell_args...]
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} cols rows shell [args...]", file=sys.stderr)
        sys.exit(1)

    cols = int(sys.argv[1])
    rows = int(sys.argv[2])
    shell = sys.argv[3]
    shell_args = sys.argv[3:]  # Include shell as argv[0]

    pid, fd = pty.fork()

    if pid == 0:
        # Child process - exec the shell
        os.execvp(shell, shell_args)
        sys.exit(1)

    # Parent process
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

if __name__ == '__main__':
    main()
