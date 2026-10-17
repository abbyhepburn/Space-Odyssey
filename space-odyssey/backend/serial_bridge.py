"""Single thread owns serial reads AND queued writes, including reconnects."""
import queue
import threading
from protocol import LineBuffer, command_line

class SerialBridge(threading.Thread):
    def __init__(self, port, incoming, status):
        super().__init__(daemon=True)
        self.port=port; self.incoming=incoming; self.status=status
        self.writes=queue.Queue(maxsize=256); self.stop_event=threading.Event()
    def send(self, line): self.writes.put_nowait(command_line(line).encode('ascii'))
    def close(self): self.stop_event.set(); self.join(timeout=3)
    def run(self):
        import serial
        while not self.stop_event.is_set():
            try:
                # No other module may construct a Serial object.
                with serial.Serial(self.port,115200,timeout=.05,write_timeout=.5) as port:
                    self.status(True, 'USB connected'); buf=LineBuffer()
                    port.write(b'GET_STATE\n')
                    while not self.stop_event.is_set():
                        for _ in range(16):
                            try: port.write(self.writes.get_nowait())
                            except queue.Empty: break
                        for line in buf.feed(port.read(port.in_waiting or 1)): self.incoming(line)
            except (serial.SerialException, OSError, TypeError) as exc:
                self.status(False,str(exc))
                # Never replay stale run/jump/mission commands after reconnect.
                while True:
                    try: self.writes.get_nowait()
                    except queue.Empty: break
                self.stop_event.wait(1)
