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

def elapsedTime(t):
	if t < 1.0:
		return "%5.4g ms" % (t*1000.0)
	elif t < 60.0:
		return "%5.4g s" % (t)
	elif t < 3600.0:
		return "%5.4g m" % (t/60.0)
	else:
		return "%5.4g h" % (t/3600.0)

def memorySize(sz):
	fsz = float(sz)
	if sz < 1024:
		return "%5g B" % fsz
	elif sz < 1024**2:
		return "%5.4g KB" % (fsz/(1024))
	elif sz < 1024**3:
		return "%5.4g MB" % (fsz/(1024**2))
	elif sz < 1024**4:
		return "%5.4g GB" % (fsz/(1024**3))
	else:
		return "%5.4g TB" % (fsz/(1024**4))
