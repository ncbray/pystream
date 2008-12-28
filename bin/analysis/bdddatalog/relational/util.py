from __future__ import absolute_import

import pycudd
import copy

from . domain import PhysicalStructure


from . managerhack import intarray

cache = {}

def __makePermutation(m, lut):
	p = range(m.ReadSize())

	for src, dst in lut.iteritems():
		assert src.logical == dst.logical
		for a, b in zip(src.index, dst.index):
			p[a] = b
	return intarray(p)

def permutation(m, lut):
	# HACK
	key = tuple(lut.iteritems())

	if not key in cache:	
		cache[key] = __makePermutation(m, lut)
	return cache[key]

def swap(a, b):
	return permutation(m, {a:b, b:a})


# The following "create" functions calculate the
# resulting types and auxilary data structures
# for relation operations.
def createRename(m, attr, rdict):
	rn = {}
	for name, t in attr.iteritems():
		name = rdict.get(name, name)
		rn[name] = t
	return rn

def createRelocate(m, attr, lut):
	perm = {}
	rn = copy.copy(attr)
	rn.update(lut)
	
	for name, pd in lut.iteritems():
		perm[attr[name]] = pd

	p = permutation(m, perm)
	return rn, p

def createModify(m, attr, lut):
	rn = {}
	perm = {}

	# TODO validate
	
	for name, t in attr.iteritems():
		if name in lut:
			rn[lut[name][0]] = lut[name][1]
			perm[t] = lut[name][1]
		else:
			rn[name] = t
	p = permutation(m, perm)

	return rn, p


def restrictMask(m, attributes, restrictLUT):
	e = m.ReadOne()

	for name, domain in attributes:
		if name in restrictLUT:
			if isinstance(restrictLUT[name], dict):
				e &= restrictMask(m, domain.attributes, restrictLUT[name])
			else:
				value = restrictLUT[name]
				#print "Masking", name, domain, value
				e &= domain.encode(value)
	return e

def restrictMaskOrdered(m, attributes, values):
	e = m.ReadOne()

	assert len(attributes) == len(values)

	for (name, domain), value in zip(attributes, values):
		e &= domain.encode(value)

	return e

	
def restrictMaskOrderedSorted(m, attributes, values):

	assert len(attributes) == len(values)

	bits = []

	for (name, domain), value in zip(attributes, values):
		domain.getBits(value, bits)

	bits.sort(key=lambda e: e[0], reverse=True)

	e = m.ReadOne()
	for index, bit in bits:
		e &= domain.encode(value)
	return e


def createRestrict(m, attr, restrict):
	names = set(restrict.keys())
	attrNames = set([name for name, domain in attr])

	rn = []
	
	for name, pd in attr:
		if name in restrict:
			if isinstance(restrict[name], dict):
				sub = createRestrict(m, pd.attributes, restrict[name])
				if sub: rn.append((name, PhysicalStructure(pd.name, sub)))
		else:
			rn.append((name, pd))

	return tuple(rn)

def forget(m, f):
	cube = m.ReadOne()
	
	for pd in f:
		cube &= pd.cube

	return cube

def forgetMask(names):
	mask = {}
	for name in names:
		parts = name.split('.')
		current = mask
		for part in parts[:-1]:
			if part not in current:
				current[part] = {}
			elif current[part] == '*':
				break

			current = current[part]
		else:
			current[parts[-1]] = '*'

	return mask

def createForgetMasked(m, attr, mask):
	attrNames = set([name for name, domain in attr])
	for name in mask.iterkeys():
		assert name in attrNames, "Cannot forget a field that does not exist: %s." % name

	rn = []
	f = []
	
	for name, pd in attr:
		if name in mask:
			if mask[name] == '*':
				f.append(pd)
			else:
				rrn, rf = createForgetMasked(m, pd.attributes, mask[name])
				if rrn: rn.append((name, PhysicalStructure(pd.name, rrn)))
				if rf: f.extend(rf)
		else:
			rn.append((name, pd))

	
	return rn, f



def createForget(m, attr, names):
	mask = forgetMask(names)
	rn, f = createForgetMasked(m, attr, mask)
	cube = forget(m, f)
	return rn, cube

def attrLUT(attr):
	lut = {}
	for name, domain in attr:
		lut[name] = domain
	return lut

def createJoin(m, a, b):
	canJoin = False

	alut = attrLUT(a)
	blut = attrLUT(b)


	output = []

	canJoin = False
	for name, domain in a:
		if name in blut:
			assert blut[name] == domain
			canJoin = True
			
		output.append((name, domain))

	assert canJoin, "No attributes in common."

	for name, domain in b:
		if not name in alut:
			output.append((name, domain))

	return tuple(output)

##def createCompose(m, a, b):
##	rn = createJoin(m, a, b)
##	common = set(a.keys()).intersection(b.keys())
##	assert common, "Cannot compose relations that do not share fields."
##	rn, cube = createForget(m, rn, common)
##	return rn, cube


def createCompose(m, a, b):
	canJoin = False

	alut = attrLUT(a)
	blut = attrLUT(b)

	output = []
	common = []

	for name, domain in a:
		if name in blut:
			assert blut[name] == domain
			common.append(domain)
		else:
			output.append((name, domain))

	assert common, "No attributes in common."

	for name, domain in b:
		if not name in alut:
			output.append((name, domain))

	return tuple(output), forget(m, common)
