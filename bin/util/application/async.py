# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = ['async', 'async_limited']

import threading
import functools

enabled = True

def async(func):
	@functools.wraps(func)
	def async_wrapper(*args, **kargs):
		t = threading.Thread(target=func, args=args, kwargs=kargs)
		t.start()
		return t

	if enabled:
		return async_wrapper
	else:
		return func

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

		if enabled:
			return limited_wrap
		else:
			return func

	return limited_func
