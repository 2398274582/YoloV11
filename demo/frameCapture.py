import cv2
import time
import queue
from threading import Thread, Lock
import threading

import cv2
import time

# TODO: PROBLEMS WITH BUFFER SIZE BECAUSE IT HAS DELAY AND IT IS NOT REAL TIME AND FILL UP THE BUFFER
class FrameCaptureBuffer:
    def __init__(self, source=0, buffer_size=1):
        self.source = source  # default is 0 for primary camera
        self.vcap = cv2.VideoCapture(self.source)
        if not self.vcap.isOpened():
            print("[Exiting]: Error accessing webcam stream.")
            exit(0)
        self.fps = int(self.vcap.get(cv2.CAP_PROP_FPS))
        print("FPS of cam/video stream: {}".format(self.fps))
        w = int(self.vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_size = (w, h)

        self.buffer_size = buffer_size
        self.frame_queue = queue.Queue(maxsize=self.buffer_size)
        self.grabbed, self.frame = self.vcap.read()
        if not self.grabbed:
            print('[Exiting] No more frames to read')
            exit(0)

        self.stopped = False
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.frame_count = 0
        self.frame = None
        self.ret = None

    def start(self):
        self.stopped = False
        self.frame_count = 0
        self.thread.start()

    def update(self):
        while not self.stopped:
            self.ret, frame = self.vcap.read()
            if not self.ret:
                self.stop()
                break
            if self.frame_queue.qsize() > self.frame_queue.qsize() * 0.9:
                time.sleep(0.001)
            self.frame_queue.put(frame)

    def read(self):
        if not self.frame_queue.empty():
            self.frame = self.frame_queue.get()
            self.frame_count += 1
            print(f"Read frame {self.frame_count}")
            print(f"Queue size: {self.frame_queue.qsize()}")
        return self.frame

    def get_frame_count(self):
        return self.frame_count
    def stop(self):
        self.stopped = True
        if threading.current_thread() != self.thread:
            self.thread.join()
        self.vcap.release()
        self.frame_count = 0

class FrameCapture:
    def __init__(self, source=0, buffer_size=10):
        self.source = source
        self.is_live_stream = isinstance(source, int)
        self.vcap = cv2.VideoCapture(source)
        if not self.vcap.isOpened():
            print("[Exiting]: Error accessing video stream.")
            exit(0)

        self.buffer_size = buffer_size
        self.frame_queue = queue.Queue(maxsize=self.buffer_size if not self.is_live_stream else 1)
        self.stopped = False
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.frame_count = 0
        self.ret = None
        self.frame = None

        print(f"Is live stream: {self.is_live_stream}")

    def start(self):
        self.stopped = False
        self.thread.start()

    def update(self):
        while not self.stopped:
            if self.is_live_stream:
                self.ret, self.frame = self.vcap.read()
            else:
                if not self.is_live_stream and self.frame_queue.full():
                    time.sleep(0.01)  # Espera activa para videos si el buffer está lleno
                    continue
                ret, frame = self.vcap.read()
                if not ret:
                    self.stop()
                    break
                self.frame_queue.put((ret, frame))
                if self.is_live_stream:
                    time.sleep(1 / self.vcap.get(cv2.CAP_PROP_FPS))  # Controle la velocidad para stream en vivo

    def read(self):
        if self.is_live_stream:
            return self.ret, self.frame
        if not self.frame_queue.empty():
            self.ret, self.frame = self.frame_queue.get()
            self.frame_count += 1
            return self.ret, self.frame
        return False, None

    def get_frame_count(self):
        return self.frame_count

    def stop(self):
        self.stopped = True
        if threading.current_thread() != self.thread:
            self.thread.join()
        self.vcap.release()
        self.clear_queue()

    def clear_queue(self):
        while not self.frame_queue.empty():
            self.frame_queue.get()


"""

class FrameCapture:
    def __init__(self, source=0):
        self.source = source
        self.vcap = cv2.VideoCapture(self.source)
        if not self.vcap.isOpened():
            print("[Exiting]: Error accessing webcam stream.")
            exit(0)

        self.fps = int(self.vcap.get(cv2.CAP_PROP_FPS))
        self.frame_size = (
            int(self.vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )

        print(f"FPS of cam/video stream: {self.fps}")
        print(f"Frame size: {self.frame_size}")
        self.frame_count = 0

        self.stopped = False
        self.vcap.set(cv2.CAP_PROP_FPS, 1)
        self.thread = threading.Thread(target=self.update)
        self.thread.daemon = True
        self.frame = None
        self.ret = None

    def start(self):
        self.stopped = False
        self.frame_count = 0
        self.thread.start()

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.vcap.read()
            self.frame_count += 1
            if not self.ret:
                self.stop()
                break
    def read(self):
        return self.ret, self.frame

    def get_frame_count(self):
        return self.frame_count
    def stop(self):
        self.stopped = True
        if threading.current_thread() != self.thread:
            self.thread.join()
        self.vcap.release()
        self.frame_count = 0
"""

if __name__ == '__main__':
    # Example usage:
    stream = FrameCapture(0)  # 0 for default webcam
    stream.start()

    try:
        input("Press Enter to stop...")
    finally:
        stream.stop()
        print("Exiting program")

if __name__ == '__main__':
    stream = FrameCapture('./videos/2.mp4')
    stream.start()
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            frame = stream.read()
            if frame is not None:
                frame_count += 1
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    fps = frame_count / elapsed_time
                    print(f"FPS: {fps:.2f}")
                    cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.imshow('Webcam', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break
    finally:
        cv2.destroyAllWindows()
        stream.stop()
        print("Exiting program")
