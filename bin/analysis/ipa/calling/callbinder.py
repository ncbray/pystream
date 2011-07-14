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

class CallBinder(object):
	def __init__(self, call, context):
		# Source
		self.call    = call
		self.invoke  = call.context.getInvoke(call.op, context)

		# Desination
		self.context = context
		self.params  = self.context.signature.code.codeParameters()


	def getSelfArg(self):
		return self.call.selfarg

	def getArg(self, i):
		return self.call.args[i]

	def getVArg(self, i):
		return self.call.vargSlots[i]

	def getDefault(self, i):
		return self.call.defaultSlots[i]

	def unusedSelfParam(self):
		pass

	def unusedParam(self, i):
		pass

	def unusedVParam(self, i):
		pass


	def setSelfParam(self, value):
		typeFilter = self.context.signature.selfparam
		dst = self.context.local(self.params.selfparam)
		self.copyDownFiltered(value, typeFilter, dst)

	def setParam(self, i, value):
		typeFilter = self.context.signature.params[i]
		dst = self.context.local(self.params.params[i])
		self.copyDownFiltered(value, typeFilter, dst)

	def setVParam(self, i, value):
		typeFilter = self.context.signature.vparams[i]
		dst = self.context.vparamField[i]
		self.copyDownFiltered(value, typeFilter, dst)

	def getReturnParam(self, i):
		return self.context.returns[i]

	def setReturnArg(self, i, value):
		if self.context.foldObj:
			assert i == 0
			self.call.targets[i].updateSingleValue(self.context.foldObj)
		else:
			target = self.call.targets[i]
			self.invoke.up(value, target)

	def copyDownFiltered(self, src, typeFilter, dst):
		self.invoke.down(src.getFiltered(typeFilter), dst)

def bind(call, context, info):
	binder = CallBinder(call, context)
	info.transfer(binder, binder)
	return binder.invoke
