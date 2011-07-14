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

from . astcollector import getOps

def codeOps(code):
	ops, lcls = getOps(code)
	return ops

def codeLocals(code):
	ops, lcls = getOps(code)
	return lcls

def codeOpsLocals(code):
	return getOps(code)

def mightHaveSideEffect(op):
	modifies = op.annotation.modifies
	if modifies and not modifies[0]:
		return False
	return True

def singleObject(lcl):
	references = lcl.annotation.references
	if references:
		refs = references[0]
		if len(refs) == 1:
			obj = refs[0].xtype.obj
			if obj.isPreexisting():
				return obj
	return None

def singleCall(op):
	invokes = op.annotation.invokes

	if invokes and invokes[0]:
		targets = set([code for code, context in invokes[0]])
		if len(targets) == 1:
			return targets.pop()

	return None


emptySet = frozenset()

def opInvokesContexts(code, op, opContext):
	invokes = op.annotation.invokes

	if invokes:
		cindex = code.annotation.contexts.index(opContext)
		if invokes[1][cindex]:
			return frozenset([context for func, context in invokes[1][cindex]])

	return emptySet
