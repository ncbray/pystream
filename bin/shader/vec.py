import math

class vec2(object):
	__slots__ = 'x', 'y'

	def __init__(self, x, y=None):
		if isinstance(x, float):
			if isinstance(y, float):
				self.x = x
				self.y = y
			elif isinstance(y, vec2):
				self.x = x
				self.y = y.x
			elif isinstance(y, vec3):
				self.x = x
				self.y = y.x
			elif isinstance(y, vec4):
				self.x = x
				self.y = y.x
			elif y is None:
				self.x = x
				self.y = x
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec2):
			pass #assert y is None
			self.x = x.x
			self.y = x.y
		elif isinstance(x, vec3):
			pass #assert y is None
			self.x = x.x
			self.y = x.y
		elif isinstance(x, vec4):
			pass #assert y is None
			self.x = x.x
			self.y = x.y
		else:
			pass #assert False, type(x)

	def __repr__(self):
		return "vec2(%s, %s)" % (self.x, self.y,)

	def __float__(self):
		return self.x

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y


	def length(self):
		return self.dot(self)**0.5


	def distance(self, other):
		return (self-other).length()


	def normalize(self):
		return self/self.length()


	def mix(self, other, amt):
		return self*(1.0-amt)+other*amt


	def reflect(self, normal):
		return self-normal*(2*self.dot(normal))


	def refract(self, normal, eta):
		ndi = self.dot(normal)
		k = 1.0-eta*eta*(1.0-ndi*ndi)
		if k < 0:
			return vec2(0.0)
		else:	
			return self*eta-normal*(eta*ndi+k**0.5)


	def exp(self):
		return vec2(math.exp(self.x), math.exp(self.y))


	def log(self):
		return vec2(math.log(self.x), math.log(self.y))


	def __pos__(self):
		return vec2(+self.x, +self.y)


	def __neg__(self):
		return vec2(-self.x, -self.y)


	def __abs__(self):
		return vec2(abs(self.x), abs(self.y))


	def __add__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x+other.x, self.y+other.y)
		elif isinstance(other, float):
			return vec2(self.x+other, self.y+other)
		else:
			return NotImplemented

	def __radd__(self, other):
		if isinstance(other, float):
			return vec2(other+self.x, other+self.y)
		else:
			return NotImplemented


	def __sub__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x-other.x, self.y-other.y)
		elif isinstance(other, float):
			return vec2(self.x-other, self.y-other)
		else:
			return NotImplemented

	def __rsub__(self, other):
		if isinstance(other, float):
			return vec2(other-self.x, other-self.y)
		else:
			return NotImplemented


	def __mul__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x*other.x, self.y*other.y)
		elif isinstance(other, float):
			return vec2(self.x*other, self.y*other)
		else:
			return NotImplemented

	def __rmul__(self, other):
		if isinstance(other, float):
			return vec2(other*self.x, other*self.y)
		else:
			return NotImplemented


	def __div__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x/other.x, self.y/other.y)
		elif isinstance(other, float):
			return vec2(self.x/other, self.y/other)
		else:
			return NotImplemented

	def __rdiv__(self, other):
		if isinstance(other, float):
			return vec2(other/self.x, other/self.y)
		else:
			return NotImplemented


	def __pow__(self, other):
		if isinstance(other, vec2):
			return vec2(self.x**other.x, self.y**other.y)
		elif isinstance(other, float):
			return vec2(self.x**other, self.y**other)
		else:
			return NotImplemented

	def __rpow__(self, other):
		if isinstance(other, float):
			return vec2(other**self.x, other**self.y)
		else:
			return NotImplemented


	def min(self, other):
		if isinstance(other, vec2):
			return vec2(min(self.x, other.x), min(self.y, other.y))
		elif isinstance(other, float):
			return vec2(min(self.x, other), min(self.y, other))
		else:
			return NotImplemented

	def rmin(self, other):
		if isinstance(other, float):
			return vec2(min(other, self.x), min(other, self.y))
		else:
			return NotImplemented


	def max(self, other):
		if isinstance(other, vec2):
			return vec2(max(self.x, other.x), max(self.y, other.y))
		elif isinstance(other, float):
			return vec2(max(self.x, other), max(self.y, other))
		else:
			return NotImplemented

	def rmax(self, other):
		if isinstance(other, float):
			return vec2(max(other, self.x), max(other, self.y))
		else:
			return NotImplemented


	@property
	def r(self):
		return self.x
	@r.setter
	def r(self, other):
		x = other.x
		self.x = x

	@property
	def xx(self):
		return vec2(self.x, self.x)
	rr = xx

	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	rrr = xxx

	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	rrrr = xxxx

	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	rrrg = xxxy

	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	rrg = xxy

	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	rrgr = xxyx

	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	rrgg = xxyy

	@property
	def xy(self):
		return vec2(self.x, self.y)
	@xy.setter
	def xy(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.y = y
	rg = xy

	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	rgr = xyx

	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	rgrr = xyxx

	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	rgrg = xyxy

	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	rgg = xyy

	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	rggr = xyyx

	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	rggg = xyyy

	@property
	def g(self):
		return self.y
	@g.setter
	def g(self, other):
		x = other.x
		self.y = x

	@property
	def yx(self):
		return vec2(self.y, self.x)
	@yx.setter
	def yx(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.x = y
	gr = yx

	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	grr = yxx

	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	grrr = yxxx

	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	grrg = yxxy

	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	grg = yxy

	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	grgr = yxyx

	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	grgg = yxyy

	@property
	def yy(self):
		return vec2(self.y, self.y)
	gg = yy

	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	ggr = yyx

	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	ggrr = yyxx

	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	ggrg = yyxy

	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	ggg = yyy

	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	gggr = yyyx

	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	gggg = yyyy


class vec3(object):
	__slots__ = 'x', 'y', 'z'

	def __init__(self, x, y=None, z=None):
		if isinstance(x, float):
			if isinstance(y, float):
				if isinstance(z, float):
					self.x = x
					self.y = y
					self.z = z
				elif isinstance(z, vec2):
					self.x = x
					self.y = y
					self.z = z.x
				elif isinstance(z, vec3):
					self.x = x
					self.y = y
					self.z = z.x
				elif isinstance(z, vec4):
					self.x = x
					self.y = y
					self.z = z.x
				else:
					pass #assert False, type(z)
			elif isinstance(y, vec2):
				pass #assert z is None
				self.x = x
				self.y = y.x
				self.z = y.y
			elif isinstance(y, vec3):
				pass #assert z is None
				self.x = x
				self.y = y.x
				self.z = y.y
			elif isinstance(y, vec4):
				pass #assert z is None
				self.x = x
				self.y = y.x
				self.z = y.y
			elif y is None:
				self.x = x
				self.y = x
				self.z = x
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec2):
			if isinstance(y, float):
				pass #assert z is None
				self.x = x.x
				self.y = x.y
				self.z = y
			elif isinstance(y, vec2):
				pass #assert z is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
			elif isinstance(y, vec3):
				pass #assert z is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
			elif isinstance(y, vec4):
				pass #assert z is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec3):
			pass #assert y is None
			pass #assert z is None
			self.x = x.x
			self.y = x.y
			self.z = x.z
		elif isinstance(x, vec4):
			pass #assert y is None
			pass #assert z is None
			self.x = x.x
			self.y = x.y
			self.z = x.z
		else:
			pass #assert False, type(x)

	def __repr__(self):
		return "vec3(%s, %s, %s)" % (self.x, self.y, self.z,)

	def __float__(self):
		return self.x

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y+self.z*other.z


	def length(self):
		return self.dot(self)**0.5


	def distance(self, other):
		return (self-other).length()


	def normalize(self):
		return self/self.length()


	def cross(self, other):
		x = self.y*other.z-self.z*other.y
		y = self.z*other.x-self.x*other.z
		z = self.x*other.y-self.y*other.x
		return vec3(x, y, z)


	def mix(self, other, amt):
		return self*(1.0-amt)+other*amt


	def reflect(self, normal):
		return self-normal*(2*self.dot(normal))


	def refract(self, normal, eta):
		ndi = self.dot(normal)
		k = 1.0-eta*eta*(1.0-ndi*ndi)
		if k < 0:
			return vec3(0.0)
		else:	
			return self*eta-normal*(eta*ndi+k**0.5)


	def exp(self):
		return vec3(math.exp(self.x), math.exp(self.y), math.exp(self.z))


	def log(self):
		return vec3(math.log(self.x), math.log(self.y), math.log(self.z))


	def __pos__(self):
		return vec3(+self.x, +self.y, +self.z)


	def __neg__(self):
		return vec3(-self.x, -self.y, -self.z)


	def __abs__(self):
		return vec3(abs(self.x), abs(self.y), abs(self.z))


	def __add__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x+other.x, self.y+other.y, self.z+other.z)
		elif isinstance(other, float):
			return vec3(self.x+other, self.y+other, self.z+other)
		else:
			return NotImplemented

	def __radd__(self, other):
		if isinstance(other, float):
			return vec3(other+self.x, other+self.y, other+self.z)
		else:
			return NotImplemented


	def __sub__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x-other.x, self.y-other.y, self.z-other.z)
		elif isinstance(other, float):
			return vec3(self.x-other, self.y-other, self.z-other)
		else:
			return NotImplemented

	def __rsub__(self, other):
		if isinstance(other, float):
			return vec3(other-self.x, other-self.y, other-self.z)
		else:
			return NotImplemented


	def __mul__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x*other.x, self.y*other.y, self.z*other.z)
		elif isinstance(other, float):
			return vec3(self.x*other, self.y*other, self.z*other)
		else:
			return NotImplemented

	def __rmul__(self, other):
		if isinstance(other, float):
			return vec3(other*self.x, other*self.y, other*self.z)
		else:
			return NotImplemented


	def __div__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x/other.x, self.y/other.y, self.z/other.z)
		elif isinstance(other, float):
			return vec3(self.x/other, self.y/other, self.z/other)
		else:
			return NotImplemented

	def __rdiv__(self, other):
		if isinstance(other, float):
			return vec3(other/self.x, other/self.y, other/self.z)
		else:
			return NotImplemented


	def __pow__(self, other):
		if isinstance(other, vec3):
			return vec3(self.x**other.x, self.y**other.y, self.z**other.z)
		elif isinstance(other, float):
			return vec3(self.x**other, self.y**other, self.z**other)
		else:
			return NotImplemented

	def __rpow__(self, other):
		if isinstance(other, float):
			return vec3(other**self.x, other**self.y, other**self.z)
		else:
			return NotImplemented


	def min(self, other):
		if isinstance(other, vec3):
			return vec3(min(self.x, other.x), min(self.y, other.y), min(self.z, other.z))
		elif isinstance(other, float):
			return vec3(min(self.x, other), min(self.y, other), min(self.z, other))
		else:
			return NotImplemented

	def rmin(self, other):
		if isinstance(other, float):
			return vec3(min(other, self.x), min(other, self.y), min(other, self.z))
		else:
			return NotImplemented


	def max(self, other):
		if isinstance(other, vec3):
			return vec3(max(self.x, other.x), max(self.y, other.y), max(self.z, other.z))
		elif isinstance(other, float):
			return vec3(max(self.x, other), max(self.y, other), max(self.z, other))
		else:
			return NotImplemented

	def rmax(self, other):
		if isinstance(other, float):
			return vec3(max(other, self.x), max(other, self.y), max(other, self.z))
		else:
			return NotImplemented


	@property
	def r(self):
		return self.x
	@r.setter
	def r(self, other):
		x = other.x
		self.x = x

	@property
	def xx(self):
		return vec2(self.x, self.x)
	rr = xx

	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	rrr = xxx

	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	rrrr = xxxx

	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	rrrg = xxxy

	@property
	def xxxz(self):
		return vec4(self.x, self.x, self.x, self.z)
	rrrb = xxxz

	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	rrg = xxy

	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	rrgr = xxyx

	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	rrgg = xxyy

	@property
	def xxyz(self):
		return vec4(self.x, self.x, self.y, self.z)
	rrgb = xxyz

	@property
	def xxz(self):
		return vec3(self.x, self.x, self.z)
	rrb = xxz

	@property
	def xxzx(self):
		return vec4(self.x, self.x, self.z, self.x)
	rrbr = xxzx

	@property
	def xxzy(self):
		return vec4(self.x, self.x, self.z, self.y)
	rrbg = xxzy

	@property
	def xxzz(self):
		return vec4(self.x, self.x, self.z, self.z)
	rrbb = xxzz

	@property
	def xy(self):
		return vec2(self.x, self.y)
	@xy.setter
	def xy(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.y = y
	rg = xy

	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	rgr = xyx

	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	rgrr = xyxx

	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	rgrg = xyxy

	@property
	def xyxz(self):
		return vec4(self.x, self.y, self.x, self.z)
	rgrb = xyxz

	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	rgg = xyy

	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	rggr = xyyx

	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	rggg = xyyy

	@property
	def xyyz(self):
		return vec4(self.x, self.y, self.y, self.z)
	rggb = xyyz

	@property
	def xyz(self):
		return vec3(self.x, self.y, self.z)
	@xyz.setter
	def xyz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.y = y
		self.z = z
	rgb = xyz

	@property
	def xyzx(self):
		return vec4(self.x, self.y, self.z, self.x)
	rgbr = xyzx

	@property
	def xyzy(self):
		return vec4(self.x, self.y, self.z, self.y)
	rgbg = xyzy

	@property
	def xyzz(self):
		return vec4(self.x, self.y, self.z, self.z)
	rgbb = xyzz

	@property
	def xz(self):
		return vec2(self.x, self.z)
	@xz.setter
	def xz(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.z = y
	rb = xz

	@property
	def xzx(self):
		return vec3(self.x, self.z, self.x)
	rbr = xzx

	@property
	def xzxx(self):
		return vec4(self.x, self.z, self.x, self.x)
	rbrr = xzxx

	@property
	def xzxy(self):
		return vec4(self.x, self.z, self.x, self.y)
	rbrg = xzxy

	@property
	def xzxz(self):
		return vec4(self.x, self.z, self.x, self.z)
	rbrb = xzxz

	@property
	def xzy(self):
		return vec3(self.x, self.z, self.y)
	@xzy.setter
	def xzy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.z = y
		self.y = z
	rbg = xzy

	@property
	def xzyx(self):
		return vec4(self.x, self.z, self.y, self.x)
	rbgr = xzyx

	@property
	def xzyy(self):
		return vec4(self.x, self.z, self.y, self.y)
	rbgg = xzyy

	@property
	def xzyz(self):
		return vec4(self.x, self.z, self.y, self.z)
	rbgb = xzyz

	@property
	def xzz(self):
		return vec3(self.x, self.z, self.z)
	rbb = xzz

	@property
	def xzzx(self):
		return vec4(self.x, self.z, self.z, self.x)
	rbbr = xzzx

	@property
	def xzzy(self):
		return vec4(self.x, self.z, self.z, self.y)
	rbbg = xzzy

	@property
	def xzzz(self):
		return vec4(self.x, self.z, self.z, self.z)
	rbbb = xzzz

	@property
	def g(self):
		return self.y
	@g.setter
	def g(self, other):
		x = other.x
		self.y = x

	@property
	def yx(self):
		return vec2(self.y, self.x)
	@yx.setter
	def yx(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.x = y
	gr = yx

	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	grr = yxx

	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	grrr = yxxx

	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	grrg = yxxy

	@property
	def yxxz(self):
		return vec4(self.y, self.x, self.x, self.z)
	grrb = yxxz

	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	grg = yxy

	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	grgr = yxyx

	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	grgg = yxyy

	@property
	def yxyz(self):
		return vec4(self.y, self.x, self.y, self.z)
	grgb = yxyz

	@property
	def yxz(self):
		return vec3(self.y, self.x, self.z)
	@yxz.setter
	def yxz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.x = y
		self.z = z
	grb = yxz

	@property
	def yxzx(self):
		return vec4(self.y, self.x, self.z, self.x)
	grbr = yxzx

	@property
	def yxzy(self):
		return vec4(self.y, self.x, self.z, self.y)
	grbg = yxzy

	@property
	def yxzz(self):
		return vec4(self.y, self.x, self.z, self.z)
	grbb = yxzz

	@property
	def yy(self):
		return vec2(self.y, self.y)
	gg = yy

	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	ggr = yyx

	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	ggrr = yyxx

	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	ggrg = yyxy

	@property
	def yyxz(self):
		return vec4(self.y, self.y, self.x, self.z)
	ggrb = yyxz

	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	ggg = yyy

	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	gggr = yyyx

	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	gggg = yyyy

	@property
	def yyyz(self):
		return vec4(self.y, self.y, self.y, self.z)
	gggb = yyyz

	@property
	def yyz(self):
		return vec3(self.y, self.y, self.z)
	ggb = yyz

	@property
	def yyzx(self):
		return vec4(self.y, self.y, self.z, self.x)
	ggbr = yyzx

	@property
	def yyzy(self):
		return vec4(self.y, self.y, self.z, self.y)
	ggbg = yyzy

	@property
	def yyzz(self):
		return vec4(self.y, self.y, self.z, self.z)
	ggbb = yyzz

	@property
	def yz(self):
		return vec2(self.y, self.z)
	@yz.setter
	def yz(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.z = y
	gb = yz

	@property
	def yzx(self):
		return vec3(self.y, self.z, self.x)
	@yzx.setter
	def yzx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.z = y
		self.x = z
	gbr = yzx

	@property
	def yzxx(self):
		return vec4(self.y, self.z, self.x, self.x)
	gbrr = yzxx

	@property
	def yzxy(self):
		return vec4(self.y, self.z, self.x, self.y)
	gbrg = yzxy

	@property
	def yzxz(self):
		return vec4(self.y, self.z, self.x, self.z)
	gbrb = yzxz

	@property
	def yzy(self):
		return vec3(self.y, self.z, self.y)
	gbg = yzy

	@property
	def yzyx(self):
		return vec4(self.y, self.z, self.y, self.x)
	gbgr = yzyx

	@property
	def yzyy(self):
		return vec4(self.y, self.z, self.y, self.y)
	gbgg = yzyy

	@property
	def yzyz(self):
		return vec4(self.y, self.z, self.y, self.z)
	gbgb = yzyz

	@property
	def yzz(self):
		return vec3(self.y, self.z, self.z)
	gbb = yzz

	@property
	def yzzx(self):
		return vec4(self.y, self.z, self.z, self.x)
	gbbr = yzzx

	@property
	def yzzy(self):
		return vec4(self.y, self.z, self.z, self.y)
	gbbg = yzzy

	@property
	def yzzz(self):
		return vec4(self.y, self.z, self.z, self.z)
	gbbb = yzzz

	@property
	def b(self):
		return self.z
	@b.setter
	def b(self, other):
		x = other.x
		self.z = x

	@property
	def zx(self):
		return vec2(self.z, self.x)
	@zx.setter
	def zx(self, other):
		x = other.x
		y = other.y
		self.z = x
		self.x = y
	br = zx

	@property
	def zxx(self):
		return vec3(self.z, self.x, self.x)
	brr = zxx

	@property
	def zxxx(self):
		return vec4(self.z, self.x, self.x, self.x)
	brrr = zxxx

	@property
	def zxxy(self):
		return vec4(self.z, self.x, self.x, self.y)
	brrg = zxxy

	@property
	def zxxz(self):
		return vec4(self.z, self.x, self.x, self.z)
	brrb = zxxz

	@property
	def zxy(self):
		return vec3(self.z, self.x, self.y)
	@zxy.setter
	def zxy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.x = y
		self.y = z
	brg = zxy

	@property
	def zxyx(self):
		return vec4(self.z, self.x, self.y, self.x)
	brgr = zxyx

	@property
	def zxyy(self):
		return vec4(self.z, self.x, self.y, self.y)
	brgg = zxyy

	@property
	def zxyz(self):
		return vec4(self.z, self.x, self.y, self.z)
	brgb = zxyz

	@property
	def zxz(self):
		return vec3(self.z, self.x, self.z)
	brb = zxz

	@property
	def zxzx(self):
		return vec4(self.z, self.x, self.z, self.x)
	brbr = zxzx

	@property
	def zxzy(self):
		return vec4(self.z, self.x, self.z, self.y)
	brbg = zxzy

	@property
	def zxzz(self):
		return vec4(self.z, self.x, self.z, self.z)
	brbb = zxzz

	@property
	def zy(self):
		return vec2(self.z, self.y)
	@zy.setter
	def zy(self, other):
		x = other.x
		y = other.y
		self.z = x
		self.y = y
	bg = zy

	@property
	def zyx(self):
		return vec3(self.z, self.y, self.x)
	@zyx.setter
	def zyx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.y = y
		self.x = z
	bgr = zyx

	@property
	def zyxx(self):
		return vec4(self.z, self.y, self.x, self.x)
	bgrr = zyxx

	@property
	def zyxy(self):
		return vec4(self.z, self.y, self.x, self.y)
	bgrg = zyxy

	@property
	def zyxz(self):
		return vec4(self.z, self.y, self.x, self.z)
	bgrb = zyxz

	@property
	def zyy(self):
		return vec3(self.z, self.y, self.y)
	bgg = zyy

	@property
	def zyyx(self):
		return vec4(self.z, self.y, self.y, self.x)
	bggr = zyyx

	@property
	def zyyy(self):
		return vec4(self.z, self.y, self.y, self.y)
	bggg = zyyy

	@property
	def zyyz(self):
		return vec4(self.z, self.y, self.y, self.z)
	bggb = zyyz

	@property
	def zyz(self):
		return vec3(self.z, self.y, self.z)
	bgb = zyz

	@property
	def zyzx(self):
		return vec4(self.z, self.y, self.z, self.x)
	bgbr = zyzx

	@property
	def zyzy(self):
		return vec4(self.z, self.y, self.z, self.y)
	bgbg = zyzy

	@property
	def zyzz(self):
		return vec4(self.z, self.y, self.z, self.z)
	bgbb = zyzz

	@property
	def zz(self):
		return vec2(self.z, self.z)
	bb = zz

	@property
	def zzx(self):
		return vec3(self.z, self.z, self.x)
	bbr = zzx

	@property
	def zzxx(self):
		return vec4(self.z, self.z, self.x, self.x)
	bbrr = zzxx

	@property
	def zzxy(self):
		return vec4(self.z, self.z, self.x, self.y)
	bbrg = zzxy

	@property
	def zzxz(self):
		return vec4(self.z, self.z, self.x, self.z)
	bbrb = zzxz

	@property
	def zzy(self):
		return vec3(self.z, self.z, self.y)
	bbg = zzy

	@property
	def zzyx(self):
		return vec4(self.z, self.z, self.y, self.x)
	bbgr = zzyx

	@property
	def zzyy(self):
		return vec4(self.z, self.z, self.y, self.y)
	bbgg = zzyy

	@property
	def zzyz(self):
		return vec4(self.z, self.z, self.y, self.z)
	bbgb = zzyz

	@property
	def zzz(self):
		return vec3(self.z, self.z, self.z)
	bbb = zzz

	@property
	def zzzx(self):
		return vec4(self.z, self.z, self.z, self.x)
	bbbr = zzzx

	@property
	def zzzy(self):
		return vec4(self.z, self.z, self.z, self.y)
	bbbg = zzzy

	@property
	def zzzz(self):
		return vec4(self.z, self.z, self.z, self.z)
	bbbb = zzzz


class vec4(object):
	__slots__ = 'x', 'y', 'z', 'w'

	def __init__(self, x, y=None, z=None, w=None):
		if isinstance(x, float):
			if isinstance(y, float):
				if isinstance(z, float):
					if isinstance(w, float):
						self.x = x
						self.y = y
						self.z = z
						self.w = w
					elif isinstance(w, vec2):
						self.x = x
						self.y = y
						self.z = z
						self.w = w.x
					elif isinstance(w, vec3):
						self.x = x
						self.y = y
						self.z = z
						self.w = w.x
					elif isinstance(w, vec4):
						self.x = x
						self.y = y
						self.z = z
						self.w = w.x
					else:
						pass #assert False, type(w)
				elif isinstance(z, vec2):
					pass #assert w is None
					self.x = x
					self.y = y
					self.z = z.x
					self.w = z.y
				elif isinstance(z, vec3):
					pass #assert w is None
					self.x = x
					self.y = y
					self.z = z.x
					self.w = z.y
				elif isinstance(z, vec4):
					pass #assert w is None
					self.x = x
					self.y = y
					self.z = z.x
					self.w = z.y
				else:
					pass #assert False, type(z)
			elif isinstance(y, vec2):
				if isinstance(z, float):
					pass #assert w is None
					self.x = x
					self.y = y.x
					self.z = y.y
					self.w = z
				elif isinstance(z, vec2):
					pass #assert w is None
					self.x = x
					self.y = y.x
					self.z = y.y
					self.w = z.x
				elif isinstance(z, vec3):
					pass #assert w is None
					self.x = x
					self.y = y.x
					self.z = y.y
					self.w = z.x
				elif isinstance(z, vec4):
					pass #assert w is None
					self.x = x
					self.y = y.x
					self.z = y.y
					self.w = z.x
				else:
					pass #assert False, type(z)
			elif isinstance(y, vec3):
				pass #assert z is None
				pass #assert w is None
				self.x = x
				self.y = y.x
				self.z = y.y
				self.w = y.z
			elif isinstance(y, vec4):
				pass #assert z is None
				pass #assert w is None
				self.x = x
				self.y = y.x
				self.z = y.y
				self.w = y.z
			elif y is None:
				self.x = x
				self.y = x
				self.z = x
				self.w = x
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec2):
			if isinstance(y, float):
				if isinstance(z, float):
					pass #assert w is None
					self.x = x.x
					self.y = x.y
					self.z = y
					self.w = z
				elif isinstance(z, vec2):
					pass #assert w is None
					self.x = x.x
					self.y = x.y
					self.z = y
					self.w = z.x
				elif isinstance(z, vec3):
					pass #assert w is None
					self.x = x.x
					self.y = x.y
					self.z = y
					self.w = z.x
				elif isinstance(z, vec4):
					pass #assert w is None
					self.x = x.x
					self.y = x.y
					self.z = y
					self.w = z.x
				else:
					pass #assert False, type(z)
			elif isinstance(y, vec2):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
				self.w = y.y
			elif isinstance(y, vec3):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
				self.w = y.y
			elif isinstance(y, vec4):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = y.x
				self.w = y.y
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec3):
			if isinstance(y, float):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = x.z
				self.w = y
			elif isinstance(y, vec2):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = x.z
				self.w = y.x
			elif isinstance(y, vec3):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = x.z
				self.w = y.x
			elif isinstance(y, vec4):
				pass #assert z is None
				pass #assert w is None
				self.x = x.x
				self.y = x.y
				self.z = x.z
				self.w = y.x
			else:
				pass #assert False, type(y)
		elif isinstance(x, vec4):
			pass #assert y is None
			pass #assert z is None
			pass #assert w is None
			self.x = x.x
			self.y = x.y
			self.z = x.z
			self.w = x.w
		else:
			pass #assert False, type(x)

	def __repr__(self):
		return "vec4(%s, %s, %s, %s)" % (self.x, self.y, self.z, self.w,)

	def __float__(self):
		return self.x

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y+self.z*other.z+self.w*other.w


	def length(self):
		return self.dot(self)**0.5


	def distance(self, other):
		return (self-other).length()


	def normalize(self):
		return self/self.length()


	def mix(self, other, amt):
		return self*(1.0-amt)+other*amt


	def reflect(self, normal):
		return self-normal*(2*self.dot(normal))


	def refract(self, normal, eta):
		ndi = self.dot(normal)
		k = 1.0-eta*eta*(1.0-ndi*ndi)
		if k < 0:
			return vec4(0.0)
		else:	
			return self*eta-normal*(eta*ndi+k**0.5)


	def exp(self):
		return vec4(math.exp(self.x), math.exp(self.y), math.exp(self.z), math.exp(self.w))


	def log(self):
		return vec4(math.log(self.x), math.log(self.y), math.log(self.z), math.log(self.w))


	def __pos__(self):
		return vec4(+self.x, +self.y, +self.z, +self.w)


	def __neg__(self):
		return vec4(-self.x, -self.y, -self.z, -self.w)


	def __abs__(self):
		return vec4(abs(self.x), abs(self.y), abs(self.z), abs(self.w))


	def __add__(self, other):
		if isinstance(other, vec4):
			return vec4(self.x+other.x, self.y+other.y, self.z+other.z, self.w+other.w)
		elif isinstance(other, float):
			return vec4(self.x+other, self.y+other, self.z+other, self.w+other)
		else:
			return NotImplemented

	def __radd__(self, other):
		if isinstance(other, float):
			return vec4(other+self.x, other+self.y, other+self.z, other+self.w)
		else:
			return NotImplemented


	def __sub__(self, other):
		if isinstance(other, vec4):
			return vec4(self.x-other.x, self.y-other.y, self.z-other.z, self.w-other.w)
		elif isinstance(other, float):
			return vec4(self.x-other, self.y-other, self.z-other, self.w-other)
		else:
			return NotImplemented

	def __rsub__(self, other):
		if isinstance(other, float):
			return vec4(other-self.x, other-self.y, other-self.z, other-self.w)
		else:
			return NotImplemented


	def __mul__(self, other):
		if isinstance(other, vec4):
			return vec4(self.x*other.x, self.y*other.y, self.z*other.z, self.w*other.w)
		elif isinstance(other, float):
			return vec4(self.x*other, self.y*other, self.z*other, self.w*other)
		else:
			return NotImplemented

	def __rmul__(self, other):
		if isinstance(other, float):
			return vec4(other*self.x, other*self.y, other*self.z, other*self.w)
		else:
			return NotImplemented


	def __div__(self, other):
		if isinstance(other, vec4):
			return vec4(self.x/other.x, self.y/other.y, self.z/other.z, self.w/other.w)
		elif isinstance(other, float):
			return vec4(self.x/other, self.y/other, self.z/other, self.w/other)
		else:
			return NotImplemented

	def __rdiv__(self, other):
		if isinstance(other, float):
			return vec4(other/self.x, other/self.y, other/self.z, other/self.w)
		else:
			return NotImplemented


	def __pow__(self, other):
		if isinstance(other, vec4):
			return vec4(self.x**other.x, self.y**other.y, self.z**other.z, self.w**other.w)
		elif isinstance(other, float):
			return vec4(self.x**other, self.y**other, self.z**other, self.w**other)
		else:
			return NotImplemented

	def __rpow__(self, other):
		if isinstance(other, float):
			return vec4(other**self.x, other**self.y, other**self.z, other**self.w)
		else:
			return NotImplemented


	def min(self, other):
		if isinstance(other, vec4):
			return vec4(min(self.x, other.x), min(self.y, other.y), min(self.z, other.z), min(self.w, other.w))
		elif isinstance(other, float):
			return vec4(min(self.x, other), min(self.y, other), min(self.z, other), min(self.w, other))
		else:
			return NotImplemented

	def rmin(self, other):
		if isinstance(other, float):
			return vec4(min(other, self.x), min(other, self.y), min(other, self.z), min(other, self.w))
		else:
			return NotImplemented


	def max(self, other):
		if isinstance(other, vec4):
			return vec4(max(self.x, other.x), max(self.y, other.y), max(self.z, other.z), max(self.w, other.w))
		elif isinstance(other, float):
			return vec4(max(self.x, other), max(self.y, other), max(self.z, other), max(self.w, other))
		else:
			return NotImplemented

	def rmax(self, other):
		if isinstance(other, float):
			return vec4(max(other, self.x), max(other, self.y), max(other, self.z), max(other, self.w))
		else:
			return NotImplemented


	@property
	def r(self):
		return self.x
	@r.setter
	def r(self, other):
		x = other.x
		self.x = x

	@property
	def xx(self):
		return vec2(self.x, self.x)
	rr = xx

	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	rrr = xxx

	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	rrrr = xxxx

	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	rrrg = xxxy

	@property
	def xxxz(self):
		return vec4(self.x, self.x, self.x, self.z)
	rrrb = xxxz

	@property
	def xxxw(self):
		return vec4(self.x, self.x, self.x, self.w)
	rrra = xxxw

	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	rrg = xxy

	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	rrgr = xxyx

	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	rrgg = xxyy

	@property
	def xxyz(self):
		return vec4(self.x, self.x, self.y, self.z)
	rrgb = xxyz

	@property
	def xxyw(self):
		return vec4(self.x, self.x, self.y, self.w)
	rrga = xxyw

	@property
	def xxz(self):
		return vec3(self.x, self.x, self.z)
	rrb = xxz

	@property
	def xxzx(self):
		return vec4(self.x, self.x, self.z, self.x)
	rrbr = xxzx

	@property
	def xxzy(self):
		return vec4(self.x, self.x, self.z, self.y)
	rrbg = xxzy

	@property
	def xxzz(self):
		return vec4(self.x, self.x, self.z, self.z)
	rrbb = xxzz

	@property
	def xxzw(self):
		return vec4(self.x, self.x, self.z, self.w)
	rrba = xxzw

	@property
	def xxw(self):
		return vec3(self.x, self.x, self.w)
	rra = xxw

	@property
	def xxwx(self):
		return vec4(self.x, self.x, self.w, self.x)
	rrar = xxwx

	@property
	def xxwy(self):
		return vec4(self.x, self.x, self.w, self.y)
	rrag = xxwy

	@property
	def xxwz(self):
		return vec4(self.x, self.x, self.w, self.z)
	rrab = xxwz

	@property
	def xxww(self):
		return vec4(self.x, self.x, self.w, self.w)
	rraa = xxww

	@property
	def xy(self):
		return vec2(self.x, self.y)
	@xy.setter
	def xy(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.y = y
	rg = xy

	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	rgr = xyx

	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	rgrr = xyxx

	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	rgrg = xyxy

	@property
	def xyxz(self):
		return vec4(self.x, self.y, self.x, self.z)
	rgrb = xyxz

	@property
	def xyxw(self):
		return vec4(self.x, self.y, self.x, self.w)
	rgra = xyxw

	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	rgg = xyy

	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	rggr = xyyx

	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	rggg = xyyy

	@property
	def xyyz(self):
		return vec4(self.x, self.y, self.y, self.z)
	rggb = xyyz

	@property
	def xyyw(self):
		return vec4(self.x, self.y, self.y, self.w)
	rgga = xyyw

	@property
	def xyz(self):
		return vec3(self.x, self.y, self.z)
	@xyz.setter
	def xyz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.y = y
		self.z = z
	rgb = xyz

	@property
	def xyzx(self):
		return vec4(self.x, self.y, self.z, self.x)
	rgbr = xyzx

	@property
	def xyzy(self):
		return vec4(self.x, self.y, self.z, self.y)
	rgbg = xyzy

	@property
	def xyzz(self):
		return vec4(self.x, self.y, self.z, self.z)
	rgbb = xyzz

	@property
	def xyzw(self):
		return vec4(self.x, self.y, self.z, self.w)
	@xyzw.setter
	def xyzw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.y = y
		self.z = z
		self.w = w
	rgba = xyzw

	@property
	def xyw(self):
		return vec3(self.x, self.y, self.w)
	@xyw.setter
	def xyw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.y = y
		self.w = z
	rga = xyw

	@property
	def xywx(self):
		return vec4(self.x, self.y, self.w, self.x)
	rgar = xywx

	@property
	def xywy(self):
		return vec4(self.x, self.y, self.w, self.y)
	rgag = xywy

	@property
	def xywz(self):
		return vec4(self.x, self.y, self.w, self.z)
	@xywz.setter
	def xywz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.y = y
		self.w = z
		self.z = w
	rgab = xywz

	@property
	def xyww(self):
		return vec4(self.x, self.y, self.w, self.w)
	rgaa = xyww

	@property
	def xz(self):
		return vec2(self.x, self.z)
	@xz.setter
	def xz(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.z = y
	rb = xz

	@property
	def xzx(self):
		return vec3(self.x, self.z, self.x)
	rbr = xzx

	@property
	def xzxx(self):
		return vec4(self.x, self.z, self.x, self.x)
	rbrr = xzxx

	@property
	def xzxy(self):
		return vec4(self.x, self.z, self.x, self.y)
	rbrg = xzxy

	@property
	def xzxz(self):
		return vec4(self.x, self.z, self.x, self.z)
	rbrb = xzxz

	@property
	def xzxw(self):
		return vec4(self.x, self.z, self.x, self.w)
	rbra = xzxw

	@property
	def xzy(self):
		return vec3(self.x, self.z, self.y)
	@xzy.setter
	def xzy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.z = y
		self.y = z
	rbg = xzy

	@property
	def xzyx(self):
		return vec4(self.x, self.z, self.y, self.x)
	rbgr = xzyx

	@property
	def xzyy(self):
		return vec4(self.x, self.z, self.y, self.y)
	rbgg = xzyy

	@property
	def xzyz(self):
		return vec4(self.x, self.z, self.y, self.z)
	rbgb = xzyz

	@property
	def xzyw(self):
		return vec4(self.x, self.z, self.y, self.w)
	@xzyw.setter
	def xzyw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.z = y
		self.y = z
		self.w = w
	rbga = xzyw

	@property
	def xzz(self):
		return vec3(self.x, self.z, self.z)
	rbb = xzz

	@property
	def xzzx(self):
		return vec4(self.x, self.z, self.z, self.x)
	rbbr = xzzx

	@property
	def xzzy(self):
		return vec4(self.x, self.z, self.z, self.y)
	rbbg = xzzy

	@property
	def xzzz(self):
		return vec4(self.x, self.z, self.z, self.z)
	rbbb = xzzz

	@property
	def xzzw(self):
		return vec4(self.x, self.z, self.z, self.w)
	rbba = xzzw

	@property
	def xzw(self):
		return vec3(self.x, self.z, self.w)
	@xzw.setter
	def xzw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.z = y
		self.w = z
	rba = xzw

	@property
	def xzwx(self):
		return vec4(self.x, self.z, self.w, self.x)
	rbar = xzwx

	@property
	def xzwy(self):
		return vec4(self.x, self.z, self.w, self.y)
	@xzwy.setter
	def xzwy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.z = y
		self.w = z
		self.y = w
	rbag = xzwy

	@property
	def xzwz(self):
		return vec4(self.x, self.z, self.w, self.z)
	rbab = xzwz

	@property
	def xzww(self):
		return vec4(self.x, self.z, self.w, self.w)
	rbaa = xzww

	@property
	def xw(self):
		return vec2(self.x, self.w)
	@xw.setter
	def xw(self, other):
		x = other.x
		y = other.y
		self.x = x
		self.w = y
	ra = xw

	@property
	def xwx(self):
		return vec3(self.x, self.w, self.x)
	rar = xwx

	@property
	def xwxx(self):
		return vec4(self.x, self.w, self.x, self.x)
	rarr = xwxx

	@property
	def xwxy(self):
		return vec4(self.x, self.w, self.x, self.y)
	rarg = xwxy

	@property
	def xwxz(self):
		return vec4(self.x, self.w, self.x, self.z)
	rarb = xwxz

	@property
	def xwxw(self):
		return vec4(self.x, self.w, self.x, self.w)
	rara = xwxw

	@property
	def xwy(self):
		return vec3(self.x, self.w, self.y)
	@xwy.setter
	def xwy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.w = y
		self.y = z
	rag = xwy

	@property
	def xwyx(self):
		return vec4(self.x, self.w, self.y, self.x)
	ragr = xwyx

	@property
	def xwyy(self):
		return vec4(self.x, self.w, self.y, self.y)
	ragg = xwyy

	@property
	def xwyz(self):
		return vec4(self.x, self.w, self.y, self.z)
	@xwyz.setter
	def xwyz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.w = y
		self.y = z
		self.z = w
	ragb = xwyz

	@property
	def xwyw(self):
		return vec4(self.x, self.w, self.y, self.w)
	raga = xwyw

	@property
	def xwz(self):
		return vec3(self.x, self.w, self.z)
	@xwz.setter
	def xwz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.x = x
		self.w = y
		self.z = z
	rab = xwz

	@property
	def xwzx(self):
		return vec4(self.x, self.w, self.z, self.x)
	rabr = xwzx

	@property
	def xwzy(self):
		return vec4(self.x, self.w, self.z, self.y)
	@xwzy.setter
	def xwzy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.x = x
		self.w = y
		self.z = z
		self.y = w
	rabg = xwzy

	@property
	def xwzz(self):
		return vec4(self.x, self.w, self.z, self.z)
	rabb = xwzz

	@property
	def xwzw(self):
		return vec4(self.x, self.w, self.z, self.w)
	raba = xwzw

	@property
	def xww(self):
		return vec3(self.x, self.w, self.w)
	raa = xww

	@property
	def xwwx(self):
		return vec4(self.x, self.w, self.w, self.x)
	raar = xwwx

	@property
	def xwwy(self):
		return vec4(self.x, self.w, self.w, self.y)
	raag = xwwy

	@property
	def xwwz(self):
		return vec4(self.x, self.w, self.w, self.z)
	raab = xwwz

	@property
	def xwww(self):
		return vec4(self.x, self.w, self.w, self.w)
	raaa = xwww

	@property
	def g(self):
		return self.y
	@g.setter
	def g(self, other):
		x = other.x
		self.y = x

	@property
	def yx(self):
		return vec2(self.y, self.x)
	@yx.setter
	def yx(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.x = y
	gr = yx

	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	grr = yxx

	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	grrr = yxxx

	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	grrg = yxxy

	@property
	def yxxz(self):
		return vec4(self.y, self.x, self.x, self.z)
	grrb = yxxz

	@property
	def yxxw(self):
		return vec4(self.y, self.x, self.x, self.w)
	grra = yxxw

	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	grg = yxy

	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	grgr = yxyx

	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	grgg = yxyy

	@property
	def yxyz(self):
		return vec4(self.y, self.x, self.y, self.z)
	grgb = yxyz

	@property
	def yxyw(self):
		return vec4(self.y, self.x, self.y, self.w)
	grga = yxyw

	@property
	def yxz(self):
		return vec3(self.y, self.x, self.z)
	@yxz.setter
	def yxz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.x = y
		self.z = z
	grb = yxz

	@property
	def yxzx(self):
		return vec4(self.y, self.x, self.z, self.x)
	grbr = yxzx

	@property
	def yxzy(self):
		return vec4(self.y, self.x, self.z, self.y)
	grbg = yxzy

	@property
	def yxzz(self):
		return vec4(self.y, self.x, self.z, self.z)
	grbb = yxzz

	@property
	def yxzw(self):
		return vec4(self.y, self.x, self.z, self.w)
	@yxzw.setter
	def yxzw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.x = y
		self.z = z
		self.w = w
	grba = yxzw

	@property
	def yxw(self):
		return vec3(self.y, self.x, self.w)
	@yxw.setter
	def yxw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.x = y
		self.w = z
	gra = yxw

	@property
	def yxwx(self):
		return vec4(self.y, self.x, self.w, self.x)
	grar = yxwx

	@property
	def yxwy(self):
		return vec4(self.y, self.x, self.w, self.y)
	grag = yxwy

	@property
	def yxwz(self):
		return vec4(self.y, self.x, self.w, self.z)
	@yxwz.setter
	def yxwz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.x = y
		self.w = z
		self.z = w
	grab = yxwz

	@property
	def yxww(self):
		return vec4(self.y, self.x, self.w, self.w)
	graa = yxww

	@property
	def yy(self):
		return vec2(self.y, self.y)
	gg = yy

	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	ggr = yyx

	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	ggrr = yyxx

	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	ggrg = yyxy

	@property
	def yyxz(self):
		return vec4(self.y, self.y, self.x, self.z)
	ggrb = yyxz

	@property
	def yyxw(self):
		return vec4(self.y, self.y, self.x, self.w)
	ggra = yyxw

	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	ggg = yyy

	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	gggr = yyyx

	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	gggg = yyyy

	@property
	def yyyz(self):
		return vec4(self.y, self.y, self.y, self.z)
	gggb = yyyz

	@property
	def yyyw(self):
		return vec4(self.y, self.y, self.y, self.w)
	ggga = yyyw

	@property
	def yyz(self):
		return vec3(self.y, self.y, self.z)
	ggb = yyz

	@property
	def yyzx(self):
		return vec4(self.y, self.y, self.z, self.x)
	ggbr = yyzx

	@property
	def yyzy(self):
		return vec4(self.y, self.y, self.z, self.y)
	ggbg = yyzy

	@property
	def yyzz(self):
		return vec4(self.y, self.y, self.z, self.z)
	ggbb = yyzz

	@property
	def yyzw(self):
		return vec4(self.y, self.y, self.z, self.w)
	ggba = yyzw

	@property
	def yyw(self):
		return vec3(self.y, self.y, self.w)
	gga = yyw

	@property
	def yywx(self):
		return vec4(self.y, self.y, self.w, self.x)
	ggar = yywx

	@property
	def yywy(self):
		return vec4(self.y, self.y, self.w, self.y)
	ggag = yywy

	@property
	def yywz(self):
		return vec4(self.y, self.y, self.w, self.z)
	ggab = yywz

	@property
	def yyww(self):
		return vec4(self.y, self.y, self.w, self.w)
	ggaa = yyww

	@property
	def yz(self):
		return vec2(self.y, self.z)
	@yz.setter
	def yz(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.z = y
	gb = yz

	@property
	def yzx(self):
		return vec3(self.y, self.z, self.x)
	@yzx.setter
	def yzx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.z = y
		self.x = z
	gbr = yzx

	@property
	def yzxx(self):
		return vec4(self.y, self.z, self.x, self.x)
	gbrr = yzxx

	@property
	def yzxy(self):
		return vec4(self.y, self.z, self.x, self.y)
	gbrg = yzxy

	@property
	def yzxz(self):
		return vec4(self.y, self.z, self.x, self.z)
	gbrb = yzxz

	@property
	def yzxw(self):
		return vec4(self.y, self.z, self.x, self.w)
	@yzxw.setter
	def yzxw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.z = y
		self.x = z
		self.w = w
	gbra = yzxw

	@property
	def yzy(self):
		return vec3(self.y, self.z, self.y)
	gbg = yzy

	@property
	def yzyx(self):
		return vec4(self.y, self.z, self.y, self.x)
	gbgr = yzyx

	@property
	def yzyy(self):
		return vec4(self.y, self.z, self.y, self.y)
	gbgg = yzyy

	@property
	def yzyz(self):
		return vec4(self.y, self.z, self.y, self.z)
	gbgb = yzyz

	@property
	def yzyw(self):
		return vec4(self.y, self.z, self.y, self.w)
	gbga = yzyw

	@property
	def yzz(self):
		return vec3(self.y, self.z, self.z)
	gbb = yzz

	@property
	def yzzx(self):
		return vec4(self.y, self.z, self.z, self.x)
	gbbr = yzzx

	@property
	def yzzy(self):
		return vec4(self.y, self.z, self.z, self.y)
	gbbg = yzzy

	@property
	def yzzz(self):
		return vec4(self.y, self.z, self.z, self.z)
	gbbb = yzzz

	@property
	def yzzw(self):
		return vec4(self.y, self.z, self.z, self.w)
	gbba = yzzw

	@property
	def yzw(self):
		return vec3(self.y, self.z, self.w)
	@yzw.setter
	def yzw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.z = y
		self.w = z
	gba = yzw

	@property
	def yzwx(self):
		return vec4(self.y, self.z, self.w, self.x)
	@yzwx.setter
	def yzwx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.z = y
		self.w = z
		self.x = w
	gbar = yzwx

	@property
	def yzwy(self):
		return vec4(self.y, self.z, self.w, self.y)
	gbag = yzwy

	@property
	def yzwz(self):
		return vec4(self.y, self.z, self.w, self.z)
	gbab = yzwz

	@property
	def yzww(self):
		return vec4(self.y, self.z, self.w, self.w)
	gbaa = yzww

	@property
	def yw(self):
		return vec2(self.y, self.w)
	@yw.setter
	def yw(self, other):
		x = other.x
		y = other.y
		self.y = x
		self.w = y
	ga = yw

	@property
	def ywx(self):
		return vec3(self.y, self.w, self.x)
	@ywx.setter
	def ywx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.w = y
		self.x = z
	gar = ywx

	@property
	def ywxx(self):
		return vec4(self.y, self.w, self.x, self.x)
	garr = ywxx

	@property
	def ywxy(self):
		return vec4(self.y, self.w, self.x, self.y)
	garg = ywxy

	@property
	def ywxz(self):
		return vec4(self.y, self.w, self.x, self.z)
	@ywxz.setter
	def ywxz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.w = y
		self.x = z
		self.z = w
	garb = ywxz

	@property
	def ywxw(self):
		return vec4(self.y, self.w, self.x, self.w)
	gara = ywxw

	@property
	def ywy(self):
		return vec3(self.y, self.w, self.y)
	gag = ywy

	@property
	def ywyx(self):
		return vec4(self.y, self.w, self.y, self.x)
	gagr = ywyx

	@property
	def ywyy(self):
		return vec4(self.y, self.w, self.y, self.y)
	gagg = ywyy

	@property
	def ywyz(self):
		return vec4(self.y, self.w, self.y, self.z)
	gagb = ywyz

	@property
	def ywyw(self):
		return vec4(self.y, self.w, self.y, self.w)
	gaga = ywyw

	@property
	def ywz(self):
		return vec3(self.y, self.w, self.z)
	@ywz.setter
	def ywz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.y = x
		self.w = y
		self.z = z
	gab = ywz

	@property
	def ywzx(self):
		return vec4(self.y, self.w, self.z, self.x)
	@ywzx.setter
	def ywzx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.y = x
		self.w = y
		self.z = z
		self.x = w
	gabr = ywzx

	@property
	def ywzy(self):
		return vec4(self.y, self.w, self.z, self.y)
	gabg = ywzy

	@property
	def ywzz(self):
		return vec4(self.y, self.w, self.z, self.z)
	gabb = ywzz

	@property
	def ywzw(self):
		return vec4(self.y, self.w, self.z, self.w)
	gaba = ywzw

	@property
	def yww(self):
		return vec3(self.y, self.w, self.w)
	gaa = yww

	@property
	def ywwx(self):
		return vec4(self.y, self.w, self.w, self.x)
	gaar = ywwx

	@property
	def ywwy(self):
		return vec4(self.y, self.w, self.w, self.y)
	gaag = ywwy

	@property
	def ywwz(self):
		return vec4(self.y, self.w, self.w, self.z)
	gaab = ywwz

	@property
	def ywww(self):
		return vec4(self.y, self.w, self.w, self.w)
	gaaa = ywww

	@property
	def b(self):
		return self.z
	@b.setter
	def b(self, other):
		x = other.x
		self.z = x

	@property
	def zx(self):
		return vec2(self.z, self.x)
	@zx.setter
	def zx(self, other):
		x = other.x
		y = other.y
		self.z = x
		self.x = y
	br = zx

	@property
	def zxx(self):
		return vec3(self.z, self.x, self.x)
	brr = zxx

	@property
	def zxxx(self):
		return vec4(self.z, self.x, self.x, self.x)
	brrr = zxxx

	@property
	def zxxy(self):
		return vec4(self.z, self.x, self.x, self.y)
	brrg = zxxy

	@property
	def zxxz(self):
		return vec4(self.z, self.x, self.x, self.z)
	brrb = zxxz

	@property
	def zxxw(self):
		return vec4(self.z, self.x, self.x, self.w)
	brra = zxxw

	@property
	def zxy(self):
		return vec3(self.z, self.x, self.y)
	@zxy.setter
	def zxy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.x = y
		self.y = z
	brg = zxy

	@property
	def zxyx(self):
		return vec4(self.z, self.x, self.y, self.x)
	brgr = zxyx

	@property
	def zxyy(self):
		return vec4(self.z, self.x, self.y, self.y)
	brgg = zxyy

	@property
	def zxyz(self):
		return vec4(self.z, self.x, self.y, self.z)
	brgb = zxyz

	@property
	def zxyw(self):
		return vec4(self.z, self.x, self.y, self.w)
	@zxyw.setter
	def zxyw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.x = y
		self.y = z
		self.w = w
	brga = zxyw

	@property
	def zxz(self):
		return vec3(self.z, self.x, self.z)
	brb = zxz

	@property
	def zxzx(self):
		return vec4(self.z, self.x, self.z, self.x)
	brbr = zxzx

	@property
	def zxzy(self):
		return vec4(self.z, self.x, self.z, self.y)
	brbg = zxzy

	@property
	def zxzz(self):
		return vec4(self.z, self.x, self.z, self.z)
	brbb = zxzz

	@property
	def zxzw(self):
		return vec4(self.z, self.x, self.z, self.w)
	brba = zxzw

	@property
	def zxw(self):
		return vec3(self.z, self.x, self.w)
	@zxw.setter
	def zxw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.x = y
		self.w = z
	bra = zxw

	@property
	def zxwx(self):
		return vec4(self.z, self.x, self.w, self.x)
	brar = zxwx

	@property
	def zxwy(self):
		return vec4(self.z, self.x, self.w, self.y)
	@zxwy.setter
	def zxwy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.x = y
		self.w = z
		self.y = w
	brag = zxwy

	@property
	def zxwz(self):
		return vec4(self.z, self.x, self.w, self.z)
	brab = zxwz

	@property
	def zxww(self):
		return vec4(self.z, self.x, self.w, self.w)
	braa = zxww

	@property
	def zy(self):
		return vec2(self.z, self.y)
	@zy.setter
	def zy(self, other):
		x = other.x
		y = other.y
		self.z = x
		self.y = y
	bg = zy

	@property
	def zyx(self):
		return vec3(self.z, self.y, self.x)
	@zyx.setter
	def zyx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.y = y
		self.x = z
	bgr = zyx

	@property
	def zyxx(self):
		return vec4(self.z, self.y, self.x, self.x)
	bgrr = zyxx

	@property
	def zyxy(self):
		return vec4(self.z, self.y, self.x, self.y)
	bgrg = zyxy

	@property
	def zyxz(self):
		return vec4(self.z, self.y, self.x, self.z)
	bgrb = zyxz

	@property
	def zyxw(self):
		return vec4(self.z, self.y, self.x, self.w)
	@zyxw.setter
	def zyxw(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.y = y
		self.x = z
		self.w = w
	bgra = zyxw

	@property
	def zyy(self):
		return vec3(self.z, self.y, self.y)
	bgg = zyy

	@property
	def zyyx(self):
		return vec4(self.z, self.y, self.y, self.x)
	bggr = zyyx

	@property
	def zyyy(self):
		return vec4(self.z, self.y, self.y, self.y)
	bggg = zyyy

	@property
	def zyyz(self):
		return vec4(self.z, self.y, self.y, self.z)
	bggb = zyyz

	@property
	def zyyw(self):
		return vec4(self.z, self.y, self.y, self.w)
	bgga = zyyw

	@property
	def zyz(self):
		return vec3(self.z, self.y, self.z)
	bgb = zyz

	@property
	def zyzx(self):
		return vec4(self.z, self.y, self.z, self.x)
	bgbr = zyzx

	@property
	def zyzy(self):
		return vec4(self.z, self.y, self.z, self.y)
	bgbg = zyzy

	@property
	def zyzz(self):
		return vec4(self.z, self.y, self.z, self.z)
	bgbb = zyzz

	@property
	def zyzw(self):
		return vec4(self.z, self.y, self.z, self.w)
	bgba = zyzw

	@property
	def zyw(self):
		return vec3(self.z, self.y, self.w)
	@zyw.setter
	def zyw(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.y = y
		self.w = z
	bga = zyw

	@property
	def zywx(self):
		return vec4(self.z, self.y, self.w, self.x)
	@zywx.setter
	def zywx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.y = y
		self.w = z
		self.x = w
	bgar = zywx

	@property
	def zywy(self):
		return vec4(self.z, self.y, self.w, self.y)
	bgag = zywy

	@property
	def zywz(self):
		return vec4(self.z, self.y, self.w, self.z)
	bgab = zywz

	@property
	def zyww(self):
		return vec4(self.z, self.y, self.w, self.w)
	bgaa = zyww

	@property
	def zz(self):
		return vec2(self.z, self.z)
	bb = zz

	@property
	def zzx(self):
		return vec3(self.z, self.z, self.x)
	bbr = zzx

	@property
	def zzxx(self):
		return vec4(self.z, self.z, self.x, self.x)
	bbrr = zzxx

	@property
	def zzxy(self):
		return vec4(self.z, self.z, self.x, self.y)
	bbrg = zzxy

	@property
	def zzxz(self):
		return vec4(self.z, self.z, self.x, self.z)
	bbrb = zzxz

	@property
	def zzxw(self):
		return vec4(self.z, self.z, self.x, self.w)
	bbra = zzxw

	@property
	def zzy(self):
		return vec3(self.z, self.z, self.y)
	bbg = zzy

	@property
	def zzyx(self):
		return vec4(self.z, self.z, self.y, self.x)
	bbgr = zzyx

	@property
	def zzyy(self):
		return vec4(self.z, self.z, self.y, self.y)
	bbgg = zzyy

	@property
	def zzyz(self):
		return vec4(self.z, self.z, self.y, self.z)
	bbgb = zzyz

	@property
	def zzyw(self):
		return vec4(self.z, self.z, self.y, self.w)
	bbga = zzyw

	@property
	def zzz(self):
		return vec3(self.z, self.z, self.z)
	bbb = zzz

	@property
	def zzzx(self):
		return vec4(self.z, self.z, self.z, self.x)
	bbbr = zzzx

	@property
	def zzzy(self):
		return vec4(self.z, self.z, self.z, self.y)
	bbbg = zzzy

	@property
	def zzzz(self):
		return vec4(self.z, self.z, self.z, self.z)
	bbbb = zzzz

	@property
	def zzzw(self):
		return vec4(self.z, self.z, self.z, self.w)
	bbba = zzzw

	@property
	def zzw(self):
		return vec3(self.z, self.z, self.w)
	bba = zzw

	@property
	def zzwx(self):
		return vec4(self.z, self.z, self.w, self.x)
	bbar = zzwx

	@property
	def zzwy(self):
		return vec4(self.z, self.z, self.w, self.y)
	bbag = zzwy

	@property
	def zzwz(self):
		return vec4(self.z, self.z, self.w, self.z)
	bbab = zzwz

	@property
	def zzww(self):
		return vec4(self.z, self.z, self.w, self.w)
	bbaa = zzww

	@property
	def zw(self):
		return vec2(self.z, self.w)
	@zw.setter
	def zw(self, other):
		x = other.x
		y = other.y
		self.z = x
		self.w = y
	ba = zw

	@property
	def zwx(self):
		return vec3(self.z, self.w, self.x)
	@zwx.setter
	def zwx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.w = y
		self.x = z
	bar = zwx

	@property
	def zwxx(self):
		return vec4(self.z, self.w, self.x, self.x)
	barr = zwxx

	@property
	def zwxy(self):
		return vec4(self.z, self.w, self.x, self.y)
	@zwxy.setter
	def zwxy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.w = y
		self.x = z
		self.y = w
	barg = zwxy

	@property
	def zwxz(self):
		return vec4(self.z, self.w, self.x, self.z)
	barb = zwxz

	@property
	def zwxw(self):
		return vec4(self.z, self.w, self.x, self.w)
	bara = zwxw

	@property
	def zwy(self):
		return vec3(self.z, self.w, self.y)
	@zwy.setter
	def zwy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.z = x
		self.w = y
		self.y = z
	bag = zwy

	@property
	def zwyx(self):
		return vec4(self.z, self.w, self.y, self.x)
	@zwyx.setter
	def zwyx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.z = x
		self.w = y
		self.y = z
		self.x = w
	bagr = zwyx

	@property
	def zwyy(self):
		return vec4(self.z, self.w, self.y, self.y)
	bagg = zwyy

	@property
	def zwyz(self):
		return vec4(self.z, self.w, self.y, self.z)
	bagb = zwyz

	@property
	def zwyw(self):
		return vec4(self.z, self.w, self.y, self.w)
	baga = zwyw

	@property
	def zwz(self):
		return vec3(self.z, self.w, self.z)
	bab = zwz

	@property
	def zwzx(self):
		return vec4(self.z, self.w, self.z, self.x)
	babr = zwzx

	@property
	def zwzy(self):
		return vec4(self.z, self.w, self.z, self.y)
	babg = zwzy

	@property
	def zwzz(self):
		return vec4(self.z, self.w, self.z, self.z)
	babb = zwzz

	@property
	def zwzw(self):
		return vec4(self.z, self.w, self.z, self.w)
	baba = zwzw

	@property
	def zww(self):
		return vec3(self.z, self.w, self.w)
	baa = zww

	@property
	def zwwx(self):
		return vec4(self.z, self.w, self.w, self.x)
	baar = zwwx

	@property
	def zwwy(self):
		return vec4(self.z, self.w, self.w, self.y)
	baag = zwwy

	@property
	def zwwz(self):
		return vec4(self.z, self.w, self.w, self.z)
	baab = zwwz

	@property
	def zwww(self):
		return vec4(self.z, self.w, self.w, self.w)
	baaa = zwww

	@property
	def a(self):
		return self.w
	@a.setter
	def a(self, other):
		x = other.x
		self.w = x

	@property
	def wx(self):
		return vec2(self.w, self.x)
	@wx.setter
	def wx(self, other):
		x = other.x
		y = other.y
		self.w = x
		self.x = y
	ar = wx

	@property
	def wxx(self):
		return vec3(self.w, self.x, self.x)
	arr = wxx

	@property
	def wxxx(self):
		return vec4(self.w, self.x, self.x, self.x)
	arrr = wxxx

	@property
	def wxxy(self):
		return vec4(self.w, self.x, self.x, self.y)
	arrg = wxxy

	@property
	def wxxz(self):
		return vec4(self.w, self.x, self.x, self.z)
	arrb = wxxz

	@property
	def wxxw(self):
		return vec4(self.w, self.x, self.x, self.w)
	arra = wxxw

	@property
	def wxy(self):
		return vec3(self.w, self.x, self.y)
	@wxy.setter
	def wxy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.x = y
		self.y = z
	arg = wxy

	@property
	def wxyx(self):
		return vec4(self.w, self.x, self.y, self.x)
	argr = wxyx

	@property
	def wxyy(self):
		return vec4(self.w, self.x, self.y, self.y)
	argg = wxyy

	@property
	def wxyz(self):
		return vec4(self.w, self.x, self.y, self.z)
	@wxyz.setter
	def wxyz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.x = y
		self.y = z
		self.z = w
	argb = wxyz

	@property
	def wxyw(self):
		return vec4(self.w, self.x, self.y, self.w)
	arga = wxyw

	@property
	def wxz(self):
		return vec3(self.w, self.x, self.z)
	@wxz.setter
	def wxz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.x = y
		self.z = z
	arb = wxz

	@property
	def wxzx(self):
		return vec4(self.w, self.x, self.z, self.x)
	arbr = wxzx

	@property
	def wxzy(self):
		return vec4(self.w, self.x, self.z, self.y)
	@wxzy.setter
	def wxzy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.x = y
		self.z = z
		self.y = w
	arbg = wxzy

	@property
	def wxzz(self):
		return vec4(self.w, self.x, self.z, self.z)
	arbb = wxzz

	@property
	def wxzw(self):
		return vec4(self.w, self.x, self.z, self.w)
	arba = wxzw

	@property
	def wxw(self):
		return vec3(self.w, self.x, self.w)
	ara = wxw

	@property
	def wxwx(self):
		return vec4(self.w, self.x, self.w, self.x)
	arar = wxwx

	@property
	def wxwy(self):
		return vec4(self.w, self.x, self.w, self.y)
	arag = wxwy

	@property
	def wxwz(self):
		return vec4(self.w, self.x, self.w, self.z)
	arab = wxwz

	@property
	def wxww(self):
		return vec4(self.w, self.x, self.w, self.w)
	araa = wxww

	@property
	def wy(self):
		return vec2(self.w, self.y)
	@wy.setter
	def wy(self, other):
		x = other.x
		y = other.y
		self.w = x
		self.y = y
	ag = wy

	@property
	def wyx(self):
		return vec3(self.w, self.y, self.x)
	@wyx.setter
	def wyx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.y = y
		self.x = z
	agr = wyx

	@property
	def wyxx(self):
		return vec4(self.w, self.y, self.x, self.x)
	agrr = wyxx

	@property
	def wyxy(self):
		return vec4(self.w, self.y, self.x, self.y)
	agrg = wyxy

	@property
	def wyxz(self):
		return vec4(self.w, self.y, self.x, self.z)
	@wyxz.setter
	def wyxz(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.y = y
		self.x = z
		self.z = w
	agrb = wyxz

	@property
	def wyxw(self):
		return vec4(self.w, self.y, self.x, self.w)
	agra = wyxw

	@property
	def wyy(self):
		return vec3(self.w, self.y, self.y)
	agg = wyy

	@property
	def wyyx(self):
		return vec4(self.w, self.y, self.y, self.x)
	aggr = wyyx

	@property
	def wyyy(self):
		return vec4(self.w, self.y, self.y, self.y)
	aggg = wyyy

	@property
	def wyyz(self):
		return vec4(self.w, self.y, self.y, self.z)
	aggb = wyyz

	@property
	def wyyw(self):
		return vec4(self.w, self.y, self.y, self.w)
	agga = wyyw

	@property
	def wyz(self):
		return vec3(self.w, self.y, self.z)
	@wyz.setter
	def wyz(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.y = y
		self.z = z
	agb = wyz

	@property
	def wyzx(self):
		return vec4(self.w, self.y, self.z, self.x)
	@wyzx.setter
	def wyzx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.y = y
		self.z = z
		self.x = w
	agbr = wyzx

	@property
	def wyzy(self):
		return vec4(self.w, self.y, self.z, self.y)
	agbg = wyzy

	@property
	def wyzz(self):
		return vec4(self.w, self.y, self.z, self.z)
	agbb = wyzz

	@property
	def wyzw(self):
		return vec4(self.w, self.y, self.z, self.w)
	agba = wyzw

	@property
	def wyw(self):
		return vec3(self.w, self.y, self.w)
	aga = wyw

	@property
	def wywx(self):
		return vec4(self.w, self.y, self.w, self.x)
	agar = wywx

	@property
	def wywy(self):
		return vec4(self.w, self.y, self.w, self.y)
	agag = wywy

	@property
	def wywz(self):
		return vec4(self.w, self.y, self.w, self.z)
	agab = wywz

	@property
	def wyww(self):
		return vec4(self.w, self.y, self.w, self.w)
	agaa = wyww

	@property
	def wz(self):
		return vec2(self.w, self.z)
	@wz.setter
	def wz(self, other):
		x = other.x
		y = other.y
		self.w = x
		self.z = y
	ab = wz

	@property
	def wzx(self):
		return vec3(self.w, self.z, self.x)
	@wzx.setter
	def wzx(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.z = y
		self.x = z
	abr = wzx

	@property
	def wzxx(self):
		return vec4(self.w, self.z, self.x, self.x)
	abrr = wzxx

	@property
	def wzxy(self):
		return vec4(self.w, self.z, self.x, self.y)
	@wzxy.setter
	def wzxy(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.z = y
		self.x = z
		self.y = w
	abrg = wzxy

	@property
	def wzxz(self):
		return vec4(self.w, self.z, self.x, self.z)
	abrb = wzxz

	@property
	def wzxw(self):
		return vec4(self.w, self.z, self.x, self.w)
	abra = wzxw

	@property
	def wzy(self):
		return vec3(self.w, self.z, self.y)
	@wzy.setter
	def wzy(self, other):
		x = other.x
		y = other.y
		z = other.z
		self.w = x
		self.z = y
		self.y = z
	abg = wzy

	@property
	def wzyx(self):
		return vec4(self.w, self.z, self.y, self.x)
	@wzyx.setter
	def wzyx(self, other):
		x = other.x
		y = other.y
		z = other.z
		w = other.w
		self.w = x
		self.z = y
		self.y = z
		self.x = w
	abgr = wzyx

	@property
	def wzyy(self):
		return vec4(self.w, self.z, self.y, self.y)
	abgg = wzyy

	@property
	def wzyz(self):
		return vec4(self.w, self.z, self.y, self.z)
	abgb = wzyz

	@property
	def wzyw(self):
		return vec4(self.w, self.z, self.y, self.w)
	abga = wzyw

	@property
	def wzz(self):
		return vec3(self.w, self.z, self.z)
	abb = wzz

	@property
	def wzzx(self):
		return vec4(self.w, self.z, self.z, self.x)
	abbr = wzzx

	@property
	def wzzy(self):
		return vec4(self.w, self.z, self.z, self.y)
	abbg = wzzy

	@property
	def wzzz(self):
		return vec4(self.w, self.z, self.z, self.z)
	abbb = wzzz

	@property
	def wzzw(self):
		return vec4(self.w, self.z, self.z, self.w)
	abba = wzzw

	@property
	def wzw(self):
		return vec3(self.w, self.z, self.w)
	aba = wzw

	@property
	def wzwx(self):
		return vec4(self.w, self.z, self.w, self.x)
	abar = wzwx

	@property
	def wzwy(self):
		return vec4(self.w, self.z, self.w, self.y)
	abag = wzwy

	@property
	def wzwz(self):
		return vec4(self.w, self.z, self.w, self.z)
	abab = wzwz

	@property
	def wzww(self):
		return vec4(self.w, self.z, self.w, self.w)
	abaa = wzww

	@property
	def ww(self):
		return vec2(self.w, self.w)
	aa = ww

	@property
	def wwx(self):
		return vec3(self.w, self.w, self.x)
	aar = wwx

	@property
	def wwxx(self):
		return vec4(self.w, self.w, self.x, self.x)
	aarr = wwxx

	@property
	def wwxy(self):
		return vec4(self.w, self.w, self.x, self.y)
	aarg = wwxy

	@property
	def wwxz(self):
		return vec4(self.w, self.w, self.x, self.z)
	aarb = wwxz

	@property
	def wwxw(self):
		return vec4(self.w, self.w, self.x, self.w)
	aara = wwxw

	@property
	def wwy(self):
		return vec3(self.w, self.w, self.y)
	aag = wwy

	@property
	def wwyx(self):
		return vec4(self.w, self.w, self.y, self.x)
	aagr = wwyx

	@property
	def wwyy(self):
		return vec4(self.w, self.w, self.y, self.y)
	aagg = wwyy

	@property
	def wwyz(self):
		return vec4(self.w, self.w, self.y, self.z)
	aagb = wwyz

	@property
	def wwyw(self):
		return vec4(self.w, self.w, self.y, self.w)
	aaga = wwyw

	@property
	def wwz(self):
		return vec3(self.w, self.w, self.z)
	aab = wwz

	@property
	def wwzx(self):
		return vec4(self.w, self.w, self.z, self.x)
	aabr = wwzx

	@property
	def wwzy(self):
		return vec4(self.w, self.w, self.z, self.y)
	aabg = wwzy

	@property
	def wwzz(self):
		return vec4(self.w, self.w, self.z, self.z)
	aabb = wwzz

	@property
	def wwzw(self):
		return vec4(self.w, self.w, self.z, self.w)
	aaba = wwzw

	@property
	def www(self):
		return vec3(self.w, self.w, self.w)
	aaa = www

	@property
	def wwwx(self):
		return vec4(self.w, self.w, self.w, self.x)
	aaar = wwwx

	@property
	def wwwy(self):
		return vec4(self.w, self.w, self.w, self.y)
	aaag = wwwy

	@property
	def wwwz(self):
		return vec4(self.w, self.w, self.w, self.z)
	aaab = wwwz

	@property
	def wwww(self):
		return vec4(self.w, self.w, self.w, self.w)
	aaaa = wwww


class mat2(object):
	__slots__ = 'm00', 'm01', 'm10', 'm11'

	def __init__(self, m00, m01, m10, m11):
		self.m00 = m00
		self.m01 = m01
		self.m10 = m10
		self.m11 = m11

	def __repr__(self):
		return "mat2(%s, %s, %s, %s)" % (self.m00, self.m01, self.m10, self.m11,)

	def __mul__(self, other):
		if isinstance(other, vec2):
			return vec2(self.m00*other.x+self.m01*other.y, self.m10*other.x+self.m11*other.y)
		elif isinstance(other, mat2):
			return mat2(self.m00*other.m00+self.m01*other.m10, self.m00*other.m01+self.m01*other.m11, self.m10*other.m00+self.m11*other.m10, self.m10*other.m01+self.m11*other.m11)
		elif isinstance(other, float):
			return mat2(self.m00*other, self.m01*other, self.m10*other, self.m11*other)
		else:
			return NotImplemented

	def __imul__(self, other):
		if isinstance(other, vec2):
			return vec2(self.m00*other.x+self.m10*other.y, self.m01*other.x+self.m11*other.y)
		elif isinstance(other, float):
			return mat2(self.m00*other, self.m01*other, self.m10*other, self.m11*other)
		else:
			return NotImplemented

class mat3(object):
	__slots__ = 'm00', 'm01', 'm02', 'm10', 'm11', 'm12', 'm20', 'm21', 'm22'

	def __init__(self, m00, m01, m02, m10, m11, m12, m20, m21, m22):
		self.m00 = m00
		self.m01 = m01
		self.m02 = m02
		self.m10 = m10
		self.m11 = m11
		self.m12 = m12
		self.m20 = m20
		self.m21 = m21
		self.m22 = m22

	def __repr__(self):
		return "mat3(%s, %s, %s, %s, %s, %s, %s, %s, %s)" % (self.m00, self.m01, self.m02, self.m10, self.m11, self.m12, self.m20, self.m21, self.m22,)

	def __mul__(self, other):
		if isinstance(other, vec3):
			return vec3(self.m00*other.x+self.m01*other.y+self.m02*other.z, self.m10*other.x+self.m11*other.y+self.m12*other.z, self.m20*other.x+self.m21*other.y+self.m22*other.z)
		elif isinstance(other, mat3):
			return mat3(self.m00*other.m00+self.m01*other.m10+self.m02*other.m20, self.m00*other.m01+self.m01*other.m11+self.m02*other.m21, self.m00*other.m02+self.m01*other.m12+self.m02*other.m22, self.m10*other.m00+self.m11*other.m10+self.m12*other.m20, self.m10*other.m01+self.m11*other.m11+self.m12*other.m21, self.m10*other.m02+self.m11*other.m12+self.m12*other.m22, self.m20*other.m00+self.m21*other.m10+self.m22*other.m20, self.m20*other.m01+self.m21*other.m11+self.m22*other.m21, self.m20*other.m02+self.m21*other.m12+self.m22*other.m22)
		elif isinstance(other, float):
			return mat3(self.m00*other, self.m01*other, self.m02*other, self.m10*other, self.m11*other, self.m12*other, self.m20*other, self.m21*other, self.m22*other)
		else:
			return NotImplemented

	def __imul__(self, other):
		if isinstance(other, vec3):
			return vec3(self.m00*other.x+self.m10*other.y+self.m20*other.z, self.m01*other.x+self.m11*other.y+self.m21*other.z, self.m02*other.x+self.m12*other.y+self.m22*other.z)
		elif isinstance(other, float):
			return mat3(self.m00*other, self.m01*other, self.m02*other, self.m10*other, self.m11*other, self.m12*other, self.m20*other, self.m21*other, self.m22*other)
		else:
			return NotImplemented

class mat4(object):
	__slots__ = 'm00', 'm01', 'm02', 'm03', 'm10', 'm11', 'm12', 'm13', 'm20', 'm21', 'm22', 'm23', 'm30', 'm31', 'm32', 'm33'

	def __init__(self, m00, m01, m02, m03, m10, m11, m12, m13, m20, m21, m22, m23, m30, m31, m32, m33):
		self.m00 = m00
		self.m01 = m01
		self.m02 = m02
		self.m03 = m03
		self.m10 = m10
		self.m11 = m11
		self.m12 = m12
		self.m13 = m13
		self.m20 = m20
		self.m21 = m21
		self.m22 = m22
		self.m23 = m23
		self.m30 = m30
		self.m31 = m31
		self.m32 = m32
		self.m33 = m33

	def __repr__(self):
		return "mat4(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % (self.m00, self.m01, self.m02, self.m03, self.m10, self.m11, self.m12, self.m13, self.m20, self.m21, self.m22, self.m23, self.m30, self.m31, self.m32, self.m33,)

	def __mul__(self, other):
		if isinstance(other, vec4):
			return vec4(self.m00*other.x+self.m01*other.y+self.m02*other.z+self.m03*other.w, self.m10*other.x+self.m11*other.y+self.m12*other.z+self.m13*other.w, self.m20*other.x+self.m21*other.y+self.m22*other.z+self.m23*other.w, self.m30*other.x+self.m31*other.y+self.m32*other.z+self.m33*other.w)
		elif isinstance(other, mat4):
			return mat4(self.m00*other.m00+self.m01*other.m10+self.m02*other.m20+self.m03*other.m30, self.m00*other.m01+self.m01*other.m11+self.m02*other.m21+self.m03*other.m31, self.m00*other.m02+self.m01*other.m12+self.m02*other.m22+self.m03*other.m32, self.m00*other.m03+self.m01*other.m13+self.m02*other.m23+self.m03*other.m33, self.m10*other.m00+self.m11*other.m10+self.m12*other.m20+self.m13*other.m30, self.m10*other.m01+self.m11*other.m11+self.m12*other.m21+self.m13*other.m31, self.m10*other.m02+self.m11*other.m12+self.m12*other.m22+self.m13*other.m32, self.m10*other.m03+self.m11*other.m13+self.m12*other.m23+self.m13*other.m33, self.m20*other.m00+self.m21*other.m10+self.m22*other.m20+self.m23*other.m30, self.m20*other.m01+self.m21*other.m11+self.m22*other.m21+self.m23*other.m31, self.m20*other.m02+self.m21*other.m12+self.m22*other.m22+self.m23*other.m32, self.m20*other.m03+self.m21*other.m13+self.m22*other.m23+self.m23*other.m33, self.m30*other.m00+self.m31*other.m10+self.m32*other.m20+self.m33*other.m30, self.m30*other.m01+self.m31*other.m11+self.m32*other.m21+self.m33*other.m31, self.m30*other.m02+self.m31*other.m12+self.m32*other.m22+self.m33*other.m32, self.m30*other.m03+self.m31*other.m13+self.m32*other.m23+self.m33*other.m33)
		elif isinstance(other, float):
			return mat4(self.m00*other, self.m01*other, self.m02*other, self.m03*other, self.m10*other, self.m11*other, self.m12*other, self.m13*other, self.m20*other, self.m21*other, self.m22*other, self.m23*other, self.m30*other, self.m31*other, self.m32*other, self.m33*other)
		else:
			return NotImplemented

	def __imul__(self, other):
		if isinstance(other, vec4):
			return vec4(self.m00*other.x+self.m10*other.y+self.m20*other.z+self.m30*other.w, self.m01*other.x+self.m11*other.y+self.m21*other.z+self.m31*other.w, self.m02*other.x+self.m12*other.y+self.m22*other.z+self.m32*other.w, self.m03*other.x+self.m13*other.y+self.m23*other.z+self.m33*other.w)
		elif isinstance(other, float):
			return mat4(self.m00*other, self.m01*other, self.m02*other, self.m03*other, self.m10*other, self.m11*other, self.m12*other, self.m13*other, self.m20*other, self.m21*other, self.m22*other, self.m23*other, self.m30*other, self.m31*other, self.m32*other, self.m33*other)
		else:
			return NotImplemented

