import threading


class Worker:
    """
    Generic background worker.
    Runs any task in a separate thread.
    """

    def __init__(
        self,
        task,
        on_finished=None,
        on_error=None,
        *args,
        **kwargs
    ):
        self.task = task
        self.args = args
        self.kwargs = kwargs

        self.on_finished = on_finished
        self.on_error = on_error

    def start(self):

        threading.Thread(
            target=self._run,
            daemon=True
        ).start()

    def _run(self):

        try:

            self.task(
                *self.args,
                **self.kwargs
            )

        except Exception as e:

            print(e)

            if self.on_error:
                self.on_error(e)

        finally:

            if self.on_finished:
                self.on_finished()