#!/usr/bin/env python3
"""Windows terminal wrapper using ConPTY via pywinpty."""
import sys
import re
import threading
import os
import msvcrt
import select

# Pre-compile regex patterns for performance
RESIZE_RE = re.compile(rb'\x1b\]RESIZE;[0-9]+;[0-9]+\x07', re.IGNORECASE)
FOCUS_IN_RE = re.compile(rb'\x1b\[I')
FOCUS_OUT_RE = re.compile(rb'\x1b\[O')

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

        input_buffer = b''
        
        while running and pty.isalive():
            try:
                # Read available data from stdin
                data = sys.stdin.buffer.read(1)
                if not data:
                    break
                
                input_buffer += data
                
                # Check for escape sequences.
                # We identify the type by the second byte instead of reading
                # a fixed number of bytes ahead, which avoids consuming the
                # leading \x1b of a subsequent escape that happens to fall
                # within the lookahead window.
                if input_buffer.startswith(b'\x1b'):
                    # Need at least 2 bytes to identify the escape type
                    while len(input_buffer) < 2:
                        more = sys.stdin.buffer.read(1)
                        if not more:
                            break
                        input_buffer += more

                    if len(input_buffer) < 2:
                        # Bare ESC at EOF — pass through
                        pty.write(input_buffer.decode('latin-1'))
                        input_buffer = b''
                        continue

                    second = input_buffer[1:2]

                    if second == b']':
                        # OSC sequence (\x1b]...BEL) — read until BEL (\x07)
                        while b'\x07' not in input_buffer:
                            c = sys.stdin.buffer.read(1)
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
                            c = sys.stdin.buffer.read(1)
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
