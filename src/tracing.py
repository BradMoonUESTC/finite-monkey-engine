from loguru import logger 
from sys import stdout
import functools
# Configure local logging to output both to a file and to the console.
logger.add("local_trace.log", format="{time} {level}: {message}", level="DEBUG")
logger.add(stdout, format="{time} {level}: {message}", level="DEBUG")

def trace(func):
    """
    A decorator for local code tracing that logs the entry, exit, and result of the function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Entering {func.__name__} with args={args} kwargs={kwargs}")
        logger = func(*args, **kwargs)
        logger.debug(f"Exiting {func.__name__} with result={result}")
        return result
    return wrapper

# Example usage:
@trace
def example_function(x, y):
    return x + y

if __name__ == "__main__":
    result = example_function(2, 3)
    print("Result:", result)
