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

from analysis.storegraph import storegraph

class LinkManager(object):
	def __init__(self):
		self.functionFile = {}
		self.objectFile = {}

		self.contextName = {}
		self.cid = 0

	def contextRef(self, context):
		if not context in self.contextName:
			self.contextName[context] = "c%d" % self.cid
			self.cid += 1
			assert context in self.contextName
		return self.contextName[context]

	def objectRef(self, obj):
		context = None
		xtype   = None

		if isinstance(obj, storegraph.ObjectNode):
			context = obj
			xtype   = obj.xtype
			obj     = xtype.obj

		if obj not in self.objectFile: return None

		fn = self.objectFile[obj]

		if context:
			cn = self.contextRef(context)
			fn = "%s#%s" % (fn, cn)

		return fn


	def codeRef(self, code, context):
		if code not in self.functionFile:
			return None

		link = self.functionFile[code]

		if context is not None:
			link = "%s#%s" % (link,  self.contextRef(context))

		return link

def paramName(p, noName=False):
	if p is None:
		return None
	elif p.isDoNotCare():
		return '-'
	elif noName:
		return '!'
	else:
		return p.name

def codeShortName(code):
	if isinstance(code, str):
		name = code
		args = []
		vargs = None
		kargs = None
	elif code is None:
		name = 'external'
		args = []
		vargs = None
		kargs = None
	else:
		name = code.codeName()
		callee = code.codeParameters()

		args = [paramName(p, n is None) for p, n in zip(callee.params, callee.paramnames)]
		vargs = paramName(callee.vparam)
		kargs = paramName(callee.kparam)

	if vargs is not None: args.append("*"+vargs)
	if kargs is not None: args.append("**"+kargs)

	return "%s(%s)" % (name, ", ".join(args))

def objectShortName(obj):
	if isinstance(obj, storegraph.ObjectNode):
		context = obj
		xtype   = obj.xtype
		obj     = xtype.obj
		return repr(xtype)

	return repr(obj)
