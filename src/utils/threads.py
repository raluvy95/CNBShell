import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

# Keep the pool for short tasks (fetching data, file I/O)
thread_pool = ThreadPoolExecutor(max_workers=4)

def thread(target: Callable, *args, **kwargs):
    """
    Submit the given function to the thread pool.
    Returns a Future. Use this for tasks that eventually finish.
    """
    return thread_pool.submit(target, *args, **kwargs)

def run_in_thread(func: Callable) -> Callable:
    """
    Decorator for short-lived background tasks.
    """
    def wrapper(*args, **kwargs):
        return thread(func, *args, **kwargs)
    return wrapper

def run_as_daemon(func: Callable) -> Callable:
    """
    Decorator for infinite loops or listeners.
    Spawns a dedicated thread so it doesn't block a pool worker.
    """
    def wrapper(*args, **kwargs):
        # daemon=True means this thread will die automatically if the main app quits
        t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return t
    return wrapper