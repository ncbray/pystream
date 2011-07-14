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

import sys
import types

def replaceGlobals(f, g):
	# HACK closure is lost
	assert isinstance(f, types.FunctionType), type(f)
	return types.FunctionType(f.func_code, g, f.func_name, f.func_defaults)

def moduleForGlobalDict(glbls):
	assert '__file__' in glbls, "Global dictionary does not come from a module?"

	for name, module in sys.modules.iteritems():
		if module and module.__dict__ is glbls:
			assert module.__file__ == glbls['__file__']
			return (name, module)
	assert False

# Note that the unique name may change between runs, as it takes the id of a type.
def uniqueSlotName(descriptor):
	# HACK GetSetDescriptors are not really slots?
	assert isinstance(descriptor, (types.MemberDescriptorType, types.GetSetDescriptorType)), (descriptor, type(descriptor), dir(descriptor))
	name     = descriptor.__name__
	objClass = descriptor.__objclass__
	return "%s#%s#%d" % (name, objClass.__name__, id(objClass))
