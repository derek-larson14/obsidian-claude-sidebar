#!/usr/bin/env python3
"""Windows terminal wrapper using ConPTY via pywinpty."""
import sys
import re
import threading

# Pre-compile regex patterns for performance
RESIZE_RE = re.compile(rb'\x1b\]RESIZE;[0-9]+;[0-9]+\x07', re.IGNORECASE)
FOCUS_IN_RE = re.compile(rb'\x1b\[I')
FOCUS_OUT_RE = re.compile(rb'\x1b\[O')

def main():
    # Parse args: terminal_win.py [cols] [rows] [shell]
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} cols rows shell", file=sys.stderr)
        sys.exit(1)

    cols = int(sys.argv[1])
    rows = int(sys.argv[2])
    shell = sys.argv[3]

    # pywinpty is required for Windows PTY support
    try:
        from winpty import PTY
    except ImportError:
        print("pywinpty not installed. Run: pip install pywinpty", file=sys.stderr)
        sys.exit(1)

    try:
        pty = PTY(cols, rows)
        pty.spawn(shell)

        running = True

        def read_output():
            nonlocal running
            while running and pty.isalive():
                try:
                    data = pty.read()
                    if data:
                        # pywinpty returns strings
                        output = data.encode('utf-8') if isinstance(data, str) else data
                        # Filter out escape sequences that get echoed back
                        output = RESIZE_RE.sub(b'', output)
                        output = FOCUS_IN_RE.sub(b'', output)
                        output = FOCUS_OUT_RE.sub(b'', output)
                        if output:
                            sys.stdout.buffer.write(output)
                            sys.stdout.buffer.flush()
                except Exception:
                    pass
            running = False

        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        while running and pty.isalive():
            try:
                data = sys.stdin.buffer.read(1)
                if not data:
                    break
                # Check for resize escape sequence
                if data == b'\x1b':
                    peek = sys.stdin.buffer.read(7)
                    if peek == b']RESIZE':
                        # Read until \x07
                        resize_data = b''
                        while True:
                            c = sys.stdin.buffer.read(1)
                            if c == b'\x07':
                                break
                            resize_data += c
                        # Parse ;cols;rows
                        parts = resize_data.decode().strip(';').split(';')
                        if len(parts) == 2:
                            try:
                                new_cols, new_rows = int(parts[0]), int(parts[1])
                                pty.set_size(new_cols, new_rows)
                            except ValueError:
                                pass
                    else:
                        pty.write((data + peek).decode('utf-8', errors='replace'))
                else:
                    pty.write(data.decode('utf-8', errors='replace'))
            except Exception:
                break

        running = False
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
