#!/usr/bin/env python3
"""Windows terminal wrapper using ConPTY via pywinpty."""
import sys
import re
import threading
import queue
import os
import msvcrt
import time

# Pre-compile regex patterns for performance
RESIZE_RE = re.compile(rb'\x1b\]RESIZE;[0-9]+;[0-9]+\x07', re.IGNORECASE)
FOCUS_IN_RE = re.compile(rb'\x1b\[I')
FOCUS_OUT_RE = re.compile(rb'\x1b\[O')

# pywinpty.PTY.read() is non-blocking on Windows and returns immediately when
# no data is available. Without a backoff the output reader thread spins at
# 100% CPU on one core whenever the terminal is idle. 10 ms keeps interactive
# latency imperceptible while dropping idle CPU to near zero.
IDLE_SLEEP_S = 0.01

# How long to wait for the second byte of an escape sequence before deciding
# the ESC stands alone. A real escape arrives from xterm.js as a single write,
# so the follow-up byte is already in the pipe and lands in well under a
# millisecond. A human pressing Esc to interrupt sends nothing after it, and
# without this timeout that keystroke sits in the lookahead until the next key
# is pressed. 50 ms is far above the pipe latency and far below any plausible
# gap between two deliberate keystrokes.
ESC_LOOKAHEAD_S = 0.05

# stdin is read on a dedicated thread so the input loop can wait on a byte with
# a timeout. sys.stdin.buffer.read(1) has no timed variant, and msvcrt.kbhit()
# is no help here: stdin is a pipe from the plugin, not a console handle.
_stdin_queue = queue.Queue()

def _stdin_reader():
    """Feed stdin bytes into _stdin_queue, then a None sentinel at EOF."""
    while True:
        try:
            b = sys.stdin.buffer.read(1)
        except Exception:
            b = b''
        if not b:
            _stdin_queue.put(None)
            return
        _stdin_queue.put(b)

def read_stdin_byte(timeout=None):
    """Next stdin byte; b'' at EOF; None if timeout elapses first.

    Callers that must not give up pass timeout=None and block indefinitely.
    Note both EOF and timeout are falsy, so existing `if not c: break` checks
    treat a timeout as end-of-input, which is the behavior we want mid-sequence.
    """
    try:
        b = _stdin_queue.get(timeout=timeout)
    except queue.Empty:
        return None
    if b is None:
        # EOF is sticky — put the sentinel back for any later reader.
        _stdin_queue.put(None)
        return b''
    return b

def read_utf8_char(buffer):
    """Read a complete UTF-8 character from buffer, handling multi-byte sequences."""
    if not buffer:
        return None, buffer
    
    first_byte = buffer[0]
    
    # Determine the number of bytes in this UTF-8 character
    if first_byte < 0x80:
        # ASCII (1 byte)
        return buffer[0:1], buffer[1:]
    elif first_byte < 0xC0:
        # Invalid start byte (continuation byte)
        return buffer[0:1], buffer[1:]
    elif first_byte < 0xE0:
        # 2-byte sequence
        needed = 2
    elif first_byte < 0xF0:
        # 3-byte sequence (CJK characters fall here)
        needed = 3
    elif first_byte < 0xF8:
        # 4-byte sequence
        needed = 4
    else:
        # Invalid byte
        return buffer[0:1], buffer[1:]
    
    if len(buffer) >= needed:
        return buffer[0:needed], buffer[needed:]
    else:
        # Not enough bytes yet, need more data
        return None, buffer

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
        print(f"pywinpty not installed for this Python interpreter:", file=sys.stderr)
        print(f"  {sys.executable}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"Install it into THIS interpreter (not just any python on PATH):", file=sys.stderr)
        print(f'  "{sys.executable}" -m pip install pywinpty', file=sys.stderr)
        sys.exit(1)

    # Set stdin to binary mode on Windows
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    try:
        pty = PTY(cols, rows)
        pty.spawn(shell)

        running = True

        def read_output():
            nonlocal running
            while running and pty.isalive():
                try:
                    data = pty.read()
                    if not data:
                        time.sleep(IDLE_SLEEP_S)
                        continue
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
                    # Avoid a tight failure loop if something is persistently
                    # wrong; pty.isalive() will normally drop us out shortly.
                    time.sleep(IDLE_SLEEP_S)
            running = False

        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        stdin_thread = threading.Thread(target=_stdin_reader, daemon=True)
        stdin_thread.start()

        input_buffer = b''

        while running and pty.isalive():
            try:
                # Read available data from stdin
                data = read_stdin_byte()
                if not data:
                    break
                
                input_buffer += data
                
                # Check for escape sequences.
                # We identify the type by the second byte instead of reading
                # a fixed number of bytes ahead, which avoids consuming the
                # leading \x1b of a subsequent escape that happens to fall
                # within the lookahead window.
                if input_buffer.startswith(b'\x1b'):
                    # Need at least 2 bytes to identify the escape type. The
                    # timeout is what makes a lone Esc usable: without it this
                    # blocks until the user's next keystroke, so Esc-to-interrupt
                    # appears to do nothing until they type something else.
                    while len(input_buffer) < 2:
                        more = read_stdin_byte(timeout=ESC_LOOKAHEAD_S)
                        if not more:
                            break
                        input_buffer += more

                    if len(input_buffer) < 2:
                        # Lone ESC (user keypress) or bare ESC at EOF — pass through
                        pty.write(input_buffer.decode('latin-1'))
                        input_buffer = b''
                        continue

                    second = input_buffer[1:2]

                    if second == b']':
                        # OSC sequence (\x1b]...BEL or \x1b]...ST) — read until
                        # either terminator. Terminal replies to color queries
                        # (OSC 11) come back ST-terminated, and waiting on a BEL
                        # that never arrives swallows all subsequent input.
                        while b'\x07' not in input_buffer and b'\x1b\\' not in input_buffer:
                            c = read_stdin_byte()
                            if not c:
                                break
                            input_buffer += c

                        if input_buffer.startswith(b'\x1b]RESIZE') and b'\x07' in input_buffer:
                            # Parse the resize command: \x1b]RESIZE;cols;rows\x07
                            end_idx = input_buffer.index(b'\x07')
                            resize_cmd = input_buffer[8:end_idx]  # After "\x1b]RESIZE"
                            input_buffer = input_buffer[end_idx + 1:]

                            # Parse ;cols;rows
                            parts = resize_cmd.decode('utf-8', errors='ignore').strip(';').split(';')
                            if len(parts) == 2:
                                try:
                                    new_cols, new_rows = int(parts[0]), int(parts[1])
                                    pty.set_size(new_cols, new_rows)
                                except ValueError:
                                    pass
                        else:
                            # Other OSC sequence — pass through to PTY
                            pty.write(input_buffer.decode('latin-1'))
                            input_buffer = b''
                        continue

                    elif second == b'[':
                        # CSI sequence (\x1b[...final) — read until final byte (0x40–0x7E)
                        while True:
                            c = read_stdin_byte()
                            if not c:
                                break
                            input_buffer += c
                            if 0x40 <= input_buffer[-1] <= 0x7E:
                                break

                        # xterm.js sends terminal protocol responses (DA1, DA2,
                        # device status) via term.onData in reply to ConPTY
                        # capability queries. These must not reach cmd.exe.
                        #   DA1:  \x1b[?...c   (e.g. \x1b[?1;2c)
                        #   DA2:  \x1b[>...c   (e.g. \x1b[>0;0;0c)
                        #   DSR:  \x1b[...n    (e.g. \x1b[0n)
                        last = input_buffer[-1] if input_buffer else 0
                        third = input_buffer[2:3]
                        is_protocol_response = (
                            (last == ord('c') and third in (b'?', b'>')) or
                            (last == ord('n'))
                        )
                        if not is_protocol_response:
                            # Legitimate user input (cursor keys, function keys, etc.)
                            pty.write(input_buffer.decode('latin-1'))
                        input_buffer = b''
                        continue

                    else:
                        # Other two-byte escape (SS2, SS3, etc.) — pass through
                        pty.write(input_buffer.decode('latin-1'))
                        input_buffer = b''
                        continue

                # Process complete UTF-8 characters from buffer
                while input_buffer:
                    char_bytes, input_buffer = read_utf8_char(input_buffer)
                    if char_bytes is None:
                        # Need more bytes to complete the character
                        break
                    
                    # Decode and send to PTY
                    try:
                        char_str = char_bytes.decode('utf-8')
                        pty.write(char_str)
                    except UnicodeDecodeError:
                        # Invalid UTF-8, send as-is (escape sequences, etc.)
                        pty.write(char_bytes.decode('latin-1'))
                        
            except Exception as e:
                break

        running = False
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
