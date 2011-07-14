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

opLUT = {'+':'add', '-':'sub',
	 '*':'mul', '//':'floordiv', '/':'div', '%':'mod',
	 '**':'pow',
	 '<<':'lshift', '>>':'rshift',
	 '&':'and', '|':'or', '^':'xor'}

compare = {'>':'gt', '<':'lt', '>=':'ge', '<=':'le', '==':'eq', '!=':'ne'}
compareRev = {'>':'lt', '<':'gt', '>=':'le', '<=':'ge', '==':'eq', '!=':'ne'}

binaryOpPrecedence = {'+':12, '-':12,
		      '*':11, '/':11, '//':11, '%':11,
		      '**':8,
		      '<<':13, '>>':13,
		      '&':14, '^':15, '|':16,
		      'in':19, 'not in':19, 'is':18, 'is not':18}


mustHaveSpace = set(('in', 'not in', 'is', 'is not'))


binaryOpName = {}

forward = {}
reverse = {}
inplace = {}

binaryOps = set()
inplaceOps = set()

inplaceFallback = {}

for op, name in opLUT.iteritems():
	iop = op+'='
	forward[op] = '__%s__'%name
	reverse[op] = '__r%s__'%name
	inplace[op] = '__i%s__'%name
	binaryOps.add(op)
	inplaceOps.add(iop)
	inplaceFallback[iop] = op

	binaryOpName[op] = '__%s__'%name
	binaryOpName[iop] = '__i%s__'%name

for op, name in compare.iteritems():
	forward[op] = '__%s__'%name
	reverse[op] = '__%s__'%compareRev[op]
	binaryOps.add(op)
	binaryOpPrecedence[op] = 17

	binaryOpName[op] = '__%s__'%name


unaryPrefixLUT = {'+':'__pos__', '-':'__neg__', '~':'__invert__'}
unaryPrefixPrecedence = {'+':10, '-':10, '~':9}
unaryOps = set(unaryPrefixLUT.iterkeys())

unaryPrefixOpName = unaryPrefixLUT


def binaryOpMethodNames(op):
	return forward[op], reverse[op]
