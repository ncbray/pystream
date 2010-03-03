def clamp(x, minVal, maxVal):
	return min(max(x, minVal), maxVal)

def smoothstep(edge0, edge1, x):
	t = clamp((x-edge0)/(edge1-edge0), 0.0, 1.0)
	return t*t*(3-2*t)
