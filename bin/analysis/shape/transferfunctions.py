from __future__ import absolute_import

from . model import expressions

from util.tvl import *


def reachable(index, secondary):
	return index.currentSet or secondary.externalReferences

def gcMerge(sys, point, context, index, secondary):
	if reachable(index, secondary):
		sys.environment.merge(sys, point, context, index, secondary)


def mapConfiguration(sys, i, slot, b0, b1):
	# e0 = e1
	# If neither points to the configuration i question, do nothing.
	# If both point to the configuration, there is no change, so do nothing.
	
	# Update reference count of index
	if b0 and not b1:
		# Left hand side
		# e0 will no longer point to the configuration.
		Si = i.decrementRef(sys, slot)
	elif not b0 and b1:
		# Right hand side
		# e0 will now point to the configuration.
		Si = i.incrementRef(sys, slot)
	else:
		Si = (i,)

	return Si
	

def updateHitMiss(sys, e0, e1, b0, b1, slot, paths):
	assert slot.isSlot(), slot

	
	# Only retain valid expressions
	# 	The value of the expression does not change
	# 	or the location is stable, and "the assigned value misses the tracked location"

	# Note: I think there is a typo in the paper, as the following functions use "b1" in the paper.

	# If the target aliases with the configuration (b0),
	# The value of the hits may change, whereas the value of the misses will not change.
	# This is because the misses cannotnot alias to the target, therefore their value will not change.	
	# The location may change for both.

	# The opisite argument applies if the target does not alias the configuration.

	# If the expression aliases the configuration (b1), this gives us no insight into what's changing.

	hitsStable = not b0
	missesStable = b0
	e0StableLocation = paths.stableLocation(e0, slot, keepHits=hitsStable, keepMisses=missesStable)
	e1StableLocation = paths.stableLocation(e1, slot, keepHits=hitsStable, keepMisses=missesStable)

	newPaths = paths.filterUnstable(slot, keepHits=hitsStable, keepMisses=missesStable)

	# For "store" like statements... 
	# These type of statements will create a new hit or miss if the LHS is stable
	# If the configuration aliases with the RHS, it's a hit.  Else, a miss.
	if e0StableLocation:
		# Does the cell hit or miss the LHS?
		# Depends on if it hits or misses the RHS
		hitmiss = ((e0,),()) if b1 else ((), (e0,))
		newPaths = newPaths.inplaceUnionHitMiss(*hitmiss)


	# Substitutes *e0 where *e1 occurs.
	# Should this occur before filtering?
	if e0StableLocation and e1StableLocation and not e1.isNull():		
		newPaths.inplaceUnify(sys, e1, e0)

	return newPaths

def assign(sys, outpoint, context, e0, e1, b0, b1, i, paths, external):	
	# b0 -> e0 aliases to i
	# b1 -> e1 aliases to i

	if b0 and b1:
		# e0 must alias i, and e1 must alias i, therefore e0 must alias e1
		# This assigment therefore does nothing.
		secondary = sys.canonical.secondary(paths, external)
		gcMerge(sys, outpoint, context, i, secondary)

		# TODO can we infer new hits/misses?
		return

	# The region being updated
	slot = e0.slot
	# TODO use the hits and misses for e0 to make stableLocation and stableValue more precise?
	# This, of course, requires figuring out what an expression can miss.

	# Map the original configuration onto the new configuration(s)
	Si = mapConfiguration(sys, i, slot, b0, b1)

	# TODO optimization: earily check for garbage collection?
	# TODO optimization: use secondary information from destination store to bound possible hits and misses?
	
	# Aliasing issues can modify the hits and misses
	newPaths = updateHitMiss(sys, e0, e1, b0, b1, slot, paths)

	# Discard "obvious" miss sets
	# All elements of Si will have the same references (but possibally different counts), so just check one.
	# TODO may not be correct if external references exist?
	#newPaths = filterTrivialMisses(sys, Si[0], newPaths)

	# Merge in the new info
	secondary = sys.canonical.secondary(newPaths, external)
	for newConf in Si:
		gcMerge(sys, outpoint, context, newConf, secondary)


def assignmentConstraint(sys, outpoint, context, e1, e0, index, paths, external):
	assert e1.isExpression(), e1
	assert e0.isExpression(), e0
	assert not e0.isNull(), "Can't assign to 'null'"
	
	v0     = e0.hit(sys, index, paths)
	e0Must = v0.mustBeTrue()

	v1     = e1.hit(sys, index, paths)
	e1Must = v1.mustBeTrue()

	assert not (v0.uncertain() and e0.isNull())
	assert not (v1.uncertain() and e1.isNull())

	if v0.certain():
		if v1.certain():
			assign(sys, outpoint, context, e0, e1, e0Must, e1Must, index, paths, external)
		else:
			assign(sys, outpoint, context, e0, e1, e0Must, True,  index, paths.unionHitMiss((e1,), ()), external)
			assign(sys, outpoint, context, e0, e1, e0Must, False, index, paths.unionHitMiss((), (e1,)), external)

	else:
		if v1.certain():
			assign(sys, outpoint, context, e0, e1, True,  e1Must, index, paths.unionHitMiss((e0,), ()), external)
			assign(sys, outpoint, context, e0, e1, False, e1Must, index, paths.unionHitMiss((), (e0,)), external)

		else:
			assert False, "This case requires heap-to-heap data transfer, which is not allowed by the IR."

			paths.unionHitMiss((), (e0,e1,))
			assign(sys, outpoint, context, e0, e1, index, True,  True,  paths.unionHitMiss((e0, e1,), ()), external)
			assign(sys, outpoint, context, e0, e1, index, True,  False, paths.unionHitMiss((e0,), (e1,)), external)
			assign(sys, outpoint, context, e0, e1, index, False, True,  paths.unionHitMiss((e1,), (e0,)), external)
			assign(sys, outpoint, context, e0, e1, index, False, False, paths.unionHitMiss((), (e0,e1,)), external)
