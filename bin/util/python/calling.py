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

__all__ = ['CallerArgs', 'CalleeParams', 'CallInfo', 'Maybe', 'callStackToParamsInfo']

from util.tvl import *

class CallerArgs(object):
	__slots__ = 'selfarg', 'args', 'kwds', 'vargs', 'kargs', 'returnargs'

	def __init__(self, selfarg, args, kwds, vargs, kargs, returnargs):
		assert isinstance(args, (list, tuple)), args
		assert isinstance(returnargs, (list, tuple)) or returnargs is None, returnargs

		self.selfarg   = selfarg
		self.args      = args
		self.kwds      = kwds
		self.vargs     = vargs
		self.kargs     = kargs
		self.returnargs = returnargs

	def __repr__(self):
		return "args(self=%r, args=%r, kwds=%r, vargs=%r, kargs=%r)" % (self.selfarg, self.args, self.kwds, self.vargs, self.kargs)

	def map(self, callback):
		selfarg = callback(self.selfarg)
		args = [callback(arg) for arg in self.args]
		assert not self.kwds
		kwds = []
		vargs = callback(self.vargs)
		kargs = callback(self.kargs)

		# HACK returnargs are by nature different?
		returnargs = self.returnargs

		return CallerArgs(selfarg, args, kwds, vargs, kargs, returnargs)

class CalleeParams(object):
	__slots__ = 'selfparam', 'params', 'paramnames', 'defaults', 'vparam', 'kparam', 'returnparams'

	def __init__(self, selfparam, params, paramnames, defaults, vparam, kparam, returnparams):
		assert isinstance(params, (list, tuple))
		assert isinstance(paramnames, (list, tuple))
		assert isinstance(returnparams, (list, tuple))

		self.selfparam   = selfparam
		self.params      = params
		self.paramnames  = paramnames
		self.defaults    = defaults
		self.vparam      = vparam
		self.kparam      = kparam
		self.returnparams = returnparams

	def __repr__(self):
		return "params(self=%r, params=%r, names=%r, vparam=%r, kparam=%r)" % (self.selfparam, self.params, self.paramnames, self.vparam, self.kparam)

# arg  -> param / vparam
# varg -> param / vparam
# kwd  -> param / kparam
# karg -> param / kparam

class PositionalTransfer(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.active = False
		self.sourceBegin = 0
		self.sourceEnd = 0
		self.destinationBegin = 0
		self.destinationEnd = 0
		self.count = 0

	def transfer(self, src, dst, count):
		assert count > 0, count

		self.active = True
		self.sourceBegin = src
		self.sourceEnd = src+count

		self.destinationBegin = dst
		self.destinationEnd = dst+count

		self.count = count

	def __iter__(self):
		assert self.active or self.count == 0
		for i in range(self.count):
			yield self.sourceBegin+i, self.destinationBegin+i

	def __len__(self):
		return self.count

class CallInfo(object):
	def __init__(self):
		self.willSucceed = TVLMaybe

		self.selfTransfer = False

		self.argParam   = PositionalTransfer()
		self.argVParam  = PositionalTransfer()

		self.exceptions = set()

		self.uncertainParam = False
		self.uncertainParamStart = 0

		self.uncertainVParam = False
		self.uncertainVParamStart = 0

		self.certainKeywords = set()
		self.defaults = set()

	def isBound(self, param):
		if param < self.argParam.count:
			return TVLTrue
		elif param in self.certainKeywords:
			return TVLTrue
		elif param in self.defaults:
			return TVLTrue
		elif self.uncertainParam:
			return TVLMaybe
		else:
			return TVLFalse

	def _mustFail(self):
		self.willSucceed = TVLFalse

		self.selfTransfer = False

		self.argParam.reset()
		self.argVParam.reset()

		self.uncertainParam  = False
		self.uncertainVParam = False

		self.certainKeywords.clear()
		self.defaults.clear()

		return self

def bindDefaults(callee, info):
	### Handle default values ###
	numDefaults = len(callee.defaults)
	numParams   = len(callee.params)
	defaultOffset = numParams-numDefaults
	for i in range(defaultOffset, numParams):
		bound = info.isBound(i)
		# If it isn't bound for sure, it may default.
		if bound.maybeFalse():
			info.defaults.add(i)

def isDoNotCare(node):
	return hasattr(node, 'isDoNotCare') and node.isDoNotCare() # HACK oh my, yes.

def callStackToParamsInfo(callee, selfarg, numArgs, uncertainVArgs, certainKwds, isUncertainKwds):
	assert isinstance(callee, CalleeParams), callee
	assert isinstance(numArgs, int) and numArgs >= 0, numArgs

	assert not isUncertainKwds, isUncertainKwds

	info = CallInfo()

	if isDoNotCare(callee.selfparam):
		info.selfTransfer = False
	elif callee.selfparam and selfarg:
		info.selfTransfer = True
	elif callee.selfparam is None and not selfarg:
		info.selfTransfer = False
	else:
		info.exceptions.add(TypeError)
		return info._mustFail()

	# Exactly known parameters [0, exact)
	numParams = len(callee.params)

	arg    = 0
	param  = 0
	vparam = 0

	cleanTransfer = TVLTrue

	# arg -> param
	count = min(numArgs, numParams)
	if count > 0:
		info.argParam.transfer(arg, param, count)
		arg   += count
		param += count

	# arg -> vparam
	count = numArgs-arg
	if count > 0:
		if callee.vparam is not None:
			assert param == numParams
			info.argVParam.transfer(arg, vparam, count)
			arg += count
			vparam  += count
		else:
			# Can't put extra args into vparam.
			info.exceptions.add(TypeError)
			return info._mustFail()

	# Parameters to fill with uncertain values [uncertain, inf)
	if param < numParams and uncertainVArgs:
		info.uncertainParam = True
		info.uncertainParamStart = param

	# Uncertain args will spill into vargs.
	if uncertainVArgs:
		if callee.vparam is not None:
			info.uncertainVParam = True
			info.uncertainVParamStart = vparam
		else:
			# Without a vparam, the uncertain arguments may overflow.
			info.exceptions.add(TypeError)
			cleanTransfer &= TVLMaybe

	### Handle keywords that we are certain will be passed ###
	if certainKwds:
		paramMap = {}
		for i, name in enumerate(callee.paramnames):
			paramMap[name] = i

		for kwd in certainKwds:
			if kwd in paramMap:
				param = paramMap[kwd]
				bound = info.isBound(param)
				if bound.mustBeFalse():
					info.certainKeywords.add(param)
				elif bound.mustBeTrue():
					# got multiple values for keyword argument '%s'
					info.exceptions.add(TypeError)
					return info._mustFail()
				else:
					# POSSIBLE: got multiple values for keyword argument '%s'
					info.certainKeywords.add(param)
					cleanTransfer &= TVLMaybe
					# TODO may no fail
			elif callee.kparam is None:
				# got an unexpected keyword argument '%s'
				info.exceptions.add(TypeError)
				return info._mustFail()
			else:
				assert False, "Temporary limitation: cannot handle kparams"

	bindDefaults(callee, info)

	# Validate binding
	completelyBound = TVLTrue
	for i in range(numParams):
		completelyBound &= info.isBound(i)


	info.willSucceed = completelyBound & cleanTransfer

	if info.willSucceed.maybeFalse():
		info.exceptions.add(TypeError)

	if info.willSucceed.mustBeFalse():
		info._mustFail()

	return info
