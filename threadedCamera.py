from threading import Thread
import cv2
import time


class ThreadedCamera(object):
    def __init__(self, src=0):
        self.capture = cv2.VideoCapture(src)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.original_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame = None
        self.FPS = 1 / 50
        self.FPS_MS = int(self.FPS * 1000)

        # Start frame retrieval thread
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
            time.sleep(self.FPS)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.capture.release()
                cv2.destroyAllWindows()
                break

    def show_frame(self):
        cv2.imshow('frame', self.frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.capture.release()
            cv2.destroyAllWindows()

    def get_frame(self):
        if self.frame is not None:
            _, jpeg = cv2.imencode('.jpg', cv2.resize(self.frame, (self.original_width, self.original_height)))
            return jpeg.tobytes()
        else:
            return b''
