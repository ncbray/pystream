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
