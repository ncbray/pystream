class Body(object):
	__slots__ = 'pos', 'vel'

	def __init__(self, pos, vel):
		self.pos = pos
		self.vel = vel

	def integrate(self, dt):
		self.pos += self.vel*dt
