import queue

class ClearQueue(queue.Queue):
    def clear(self):
        try:
            while True:
                self.get_nowait()
        except queue.Empty:
            pass

    def to_list(self):
        with self.mutex:
            return list(self.queue)
