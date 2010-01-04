__all__ = ['async', 'async_limited']

import threading
import functools

def async(func):
	@functools.wraps(func)
	def async_wrapper(*args, **kargs):
		t = threading.Thread(target=func, args=args, kwargs=kargs)
		t.start()
		return t
	return async_wrapper

def async_limited(count):
	def limited_func(func):
		semaphore = threading.BoundedSemaphore(count)

		# closure with func and semaphore
		def thread_wrap(*args, **kargs):
			result = func(*args, **kargs)
			semaphore.release()
			return result

		# closure with thread_wrap and semaphore
		@functools.wraps(func)
		def limited_wrap(*args, **kargs):
			semaphore.acquire()
			t = threading.Thread(target=thread_wrap, args=args, kwargs=kargs)
			t.start()
			return t

		return limited_wrap

	return limited_func
