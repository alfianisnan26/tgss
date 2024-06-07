import concurrent.futures
import logging
import queue
import threading
import asyncio

class ThreadManager:
    def __init__(self, consumer_func, queue_size=5, consumer_size=3, ):
        self.queue_size = queue_size
        self.consumer_size = consumer_size
        self.consumer_func = consumer_func

    def consumer(self, pipeline, event, consumer_id, consumer_func):
        logging.info(f"Consumer [{consumer_id}] is running...")
        while not event.is_set() or not pipeline.empty():
            try:
                message = pipeline.get_nowait()
                if message is not None:
                    logging.info(f"Consumer [{consumer_id}] start to process the queue")
                    consumer_func(message)
                    logging.info(f"Consumer [{consumer_id}] finished processing the queue")
            except queue.Empty:
                pass
            except Exception as e:
                logging.error(f"Consumer [{consumer_id}] has error :{e}")

        logging.info(f"Consumer [{consumer_id}] received event. Exiting")

    def run(self):
        self.threads = []
        self.pipeline = queue.Queue(maxsize=self.queue_size)
        self.stop_event = threading.Event()

        for i in range(3):  # start 3 workers
            thread = threading.Thread(target=self.consumer, args=(self.pipeline, self.stop_event, i, self.consumer_func))
            thread.start()
            self.threads.append(thread)

    def send(self, msg):
        self.pipeline.put(msg)

    def stop(self):
        logging.info("Thread set event to stop")
        self.stop_event.set()

        for thread in self.threads:
            logging.info("Waiting thread to stop")
            thread.join()

    
