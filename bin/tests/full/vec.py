class vec2(object):
	__slots__ = 'x', 'y'

	def __init__(self, x, y=None):
		self.x = x
		self.y = y

	def __repr__(self):
		return "vec2(%s, %s)" % (self.x, self.y,)

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y


	def length(self):
		return self.dot(self)**0.5


	def normalize(self):
		return self/self.length()


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


	@property
	def r(self):
		return self.x
	@property
	def xx(self):
		return vec2(self.x, self.x)
	@property
	def rr(self):
		return vec2(self.x, self.x)
	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	@property
	def rrr(self):
		return vec3(self.x, self.x, self.x)
	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def rrrr(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def rrrg(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	@property
	def rrg(self):
		return vec3(self.x, self.x, self.y)
	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def rrgr(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def rrgg(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def xy(self):
		return vec2(self.x, self.y)
	@property
	def rg(self):
		return vec2(self.x, self.y)
	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	@property
	def rgr(self):
		return vec3(self.x, self.y, self.x)
	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def rgrr(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def rgrg(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	@property
	def rgg(self):
		return vec3(self.x, self.y, self.y)
	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def rggr(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def rggg(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def g(self):
		return self.y
	@property
	def yx(self):
		return vec2(self.y, self.x)
	@property
	def gr(self):
		return vec2(self.y, self.x)
	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	@property
	def grr(self):
		return vec3(self.y, self.x, self.x)
	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def grrr(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def grrg(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	@property
	def grg(self):
		return vec3(self.y, self.x, self.y)
	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def grgr(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def grgg(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def yy(self):
		return vec2(self.y, self.y)
	@property
	def gg(self):
		return vec2(self.y, self.y)
	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	@property
	def ggr(self):
		return vec3(self.y, self.y, self.x)
	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def ggrr(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def ggrg(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	@property
	def ggg(self):
		return vec3(self.y, self.y, self.y)
	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def gggr(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	@property
	def gggg(self):
		return vec4(self.y, self.y, self.y, self.y)

class vec3(object):
	__slots__ = 'x', 'y', 'z'

	def __init__(self, x, y=None, z=None):
		self.x = x
		self.y = y
		self.z = z

	def __repr__(self):
		return "vec3(%s, %s, %s)" % (self.x, self.y, self.z,)

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y+self.z*other.z


	def length(self):
		return self.dot(self)**0.5


	def normalize(self):
		return self/self.length()


	def cross(self, other):
		x = self.y*other.z-self.z*other.y
		y = self.z*other.x-self.x*other.z
		z = self.x*other.y-self.y*other.x
		return vec3(x, y, z)


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


	@property
	def r(self):
		return self.x
	@property
	def xx(self):
		return vec2(self.x, self.x)
	@property
	def rr(self):
		return vec2(self.x, self.x)
	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	@property
	def rrr(self):
		return vec3(self.x, self.x, self.x)
	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def rrrr(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def rrrg(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def xxxz(self):
		return vec4(self.x, self.x, self.x, self.z)
	@property
	def rrrb(self):
		return vec4(self.x, self.x, self.x, self.z)
	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	@property
	def rrg(self):
		return vec3(self.x, self.x, self.y)
	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def rrgr(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def rrgg(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def xxyz(self):
		return vec4(self.x, self.x, self.y, self.z)
	@property
	def rrgb(self):
		return vec4(self.x, self.x, self.y, self.z)
	@property
	def xxz(self):
		return vec3(self.x, self.x, self.z)
	@property
	def rrb(self):
		return vec3(self.x, self.x, self.z)
	@property
	def xxzx(self):
		return vec4(self.x, self.x, self.z, self.x)
	@property
	def rrbr(self):
		return vec4(self.x, self.x, self.z, self.x)
	@property
	def xxzy(self):
		return vec4(self.x, self.x, self.z, self.y)
	@property
	def rrbg(self):
		return vec4(self.x, self.x, self.z, self.y)
	@property
	def xxzz(self):
		return vec4(self.x, self.x, self.z, self.z)
	@property
	def rrbb(self):
		return vec4(self.x, self.x, self.z, self.z)
	@property
	def xy(self):
		return vec2(self.x, self.y)
	@property
	def rg(self):
		return vec2(self.x, self.y)
	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	@property
	def rgr(self):
		return vec3(self.x, self.y, self.x)
	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def rgrr(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def rgrg(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def xyxz(self):
		return vec4(self.x, self.y, self.x, self.z)
	@property
	def rgrb(self):
		return vec4(self.x, self.y, self.x, self.z)
	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	@property
	def rgg(self):
		return vec3(self.x, self.y, self.y)
	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def rggr(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def rggg(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def xyyz(self):
		return vec4(self.x, self.y, self.y, self.z)
	@property
	def rggb(self):
		return vec4(self.x, self.y, self.y, self.z)
	@property
	def xyz(self):
		return vec3(self.x, self.y, self.z)
	@property
	def rgb(self):
		return vec3(self.x, self.y, self.z)
	@property
	def xyzx(self):
		return vec4(self.x, self.y, self.z, self.x)
	@property
	def rgbr(self):
		return vec4(self.x, self.y, self.z, self.x)
	@property
	def xyzy(self):
		return vec4(self.x, self.y, self.z, self.y)
	@property
	def rgbg(self):
		return vec4(self.x, self.y, self.z, self.y)
	@property
	def xyzz(self):
		return vec4(self.x, self.y, self.z, self.z)
	@property
	def rgbb(self):
		return vec4(self.x, self.y, self.z, self.z)
	@property
	def xz(self):
		return vec2(self.x, self.z)
	@property
	def rb(self):
		return vec2(self.x, self.z)
	@property
	def xzx(self):
		return vec3(self.x, self.z, self.x)
	@property
	def rbr(self):
		return vec3(self.x, self.z, self.x)
	@property
	def xzxx(self):
		return vec4(self.x, self.z, self.x, self.x)
	@property
	def rbrr(self):
		return vec4(self.x, self.z, self.x, self.x)
	@property
	def xzxy(self):
		return vec4(self.x, self.z, self.x, self.y)
	@property
	def rbrg(self):
		return vec4(self.x, self.z, self.x, self.y)
	@property
	def xzxz(self):
		return vec4(self.x, self.z, self.x, self.z)
	@property
	def rbrb(self):
		return vec4(self.x, self.z, self.x, self.z)
	@property
	def xzy(self):
		return vec3(self.x, self.z, self.y)
	@property
	def rbg(self):
		return vec3(self.x, self.z, self.y)
	@property
	def xzyx(self):
		return vec4(self.x, self.z, self.y, self.x)
	@property
	def rbgr(self):
		return vec4(self.x, self.z, self.y, self.x)
	@property
	def xzyy(self):
		return vec4(self.x, self.z, self.y, self.y)
	@property
	def rbgg(self):
		return vec4(self.x, self.z, self.y, self.y)
	@property
	def xzyz(self):
		return vec4(self.x, self.z, self.y, self.z)
	@property
	def rbgb(self):
		return vec4(self.x, self.z, self.y, self.z)
	@property
	def xzz(self):
		return vec3(self.x, self.z, self.z)
	@property
	def rbb(self):
		return vec3(self.x, self.z, self.z)
	@property
	def xzzx(self):
		return vec4(self.x, self.z, self.z, self.x)
	@property
	def rbbr(self):
		return vec4(self.x, self.z, self.z, self.x)
	@property
	def xzzy(self):
		return vec4(self.x, self.z, self.z, self.y)
	@property
	def rbbg(self):
		return vec4(self.x, self.z, self.z, self.y)
	@property
	def xzzz(self):
		return vec4(self.x, self.z, self.z, self.z)
	@property
	def rbbb(self):
		return vec4(self.x, self.z, self.z, self.z)
	@property
	def g(self):
		return self.y
	@property
	def yx(self):
		return vec2(self.y, self.x)
	@property
	def gr(self):
		return vec2(self.y, self.x)
	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	@property
	def grr(self):
		return vec3(self.y, self.x, self.x)
	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def grrr(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def grrg(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def yxxz(self):
		return vec4(self.y, self.x, self.x, self.z)
	@property
	def grrb(self):
		return vec4(self.y, self.x, self.x, self.z)
	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	@property
	def grg(self):
		return vec3(self.y, self.x, self.y)
	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def grgr(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def grgg(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def yxyz(self):
		return vec4(self.y, self.x, self.y, self.z)
	@property
	def grgb(self):
		return vec4(self.y, self.x, self.y, self.z)
	@property
	def yxz(self):
		return vec3(self.y, self.x, self.z)
	@property
	def grb(self):
		return vec3(self.y, self.x, self.z)
	@property
	def yxzx(self):
		return vec4(self.y, self.x, self.z, self.x)
	@property
	def grbr(self):
		return vec4(self.y, self.x, self.z, self.x)
	@property
	def yxzy(self):
		return vec4(self.y, self.x, self.z, self.y)
	@property
	def grbg(self):
		return vec4(self.y, self.x, self.z, self.y)
	@property
	def yxzz(self):
		return vec4(self.y, self.x, self.z, self.z)
	@property
	def grbb(self):
		return vec4(self.y, self.x, self.z, self.z)
	@property
	def yy(self):
		return vec2(self.y, self.y)
	@property
	def gg(self):
		return vec2(self.y, self.y)
	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	@property
	def ggr(self):
		return vec3(self.y, self.y, self.x)
	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def ggrr(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def ggrg(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def yyxz(self):
		return vec4(self.y, self.y, self.x, self.z)
	@property
	def ggrb(self):
		return vec4(self.y, self.y, self.x, self.z)
	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	@property
	def ggg(self):
		return vec3(self.y, self.y, self.y)
	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def gggr(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	@property
	def gggg(self):
		return vec4(self.y, self.y, self.y, self.y)
	@property
	def yyyz(self):
		return vec4(self.y, self.y, self.y, self.z)
	@property
	def gggb(self):
		return vec4(self.y, self.y, self.y, self.z)
	@property
	def yyz(self):
		return vec3(self.y, self.y, self.z)
	@property
	def ggb(self):
		return vec3(self.y, self.y, self.z)
	@property
	def yyzx(self):
		return vec4(self.y, self.y, self.z, self.x)
	@property
	def ggbr(self):
		return vec4(self.y, self.y, self.z, self.x)
	@property
	def yyzy(self):
		return vec4(self.y, self.y, self.z, self.y)
	@property
	def ggbg(self):
		return vec4(self.y, self.y, self.z, self.y)
	@property
	def yyzz(self):
		return vec4(self.y, self.y, self.z, self.z)
	@property
	def ggbb(self):
		return vec4(self.y, self.y, self.z, self.z)
	@property
	def yz(self):
		return vec2(self.y, self.z)
	@property
	def gb(self):
		return vec2(self.y, self.z)
	@property
	def yzx(self):
		return vec3(self.y, self.z, self.x)
	@property
	def gbr(self):
		return vec3(self.y, self.z, self.x)
	@property
	def yzxx(self):
		return vec4(self.y, self.z, self.x, self.x)
	@property
	def gbrr(self):
		return vec4(self.y, self.z, self.x, self.x)
	@property
	def yzxy(self):
		return vec4(self.y, self.z, self.x, self.y)
	@property
	def gbrg(self):
		return vec4(self.y, self.z, self.x, self.y)
	@property
	def yzxz(self):
		return vec4(self.y, self.z, self.x, self.z)
	@property
	def gbrb(self):
		return vec4(self.y, self.z, self.x, self.z)
	@property
	def yzy(self):
		return vec3(self.y, self.z, self.y)
	@property
	def gbg(self):
		return vec3(self.y, self.z, self.y)
	@property
	def yzyx(self):
		return vec4(self.y, self.z, self.y, self.x)
	@property
	def gbgr(self):
		return vec4(self.y, self.z, self.y, self.x)
	@property
	def yzyy(self):
		return vec4(self.y, self.z, self.y, self.y)
	@property
	def gbgg(self):
		return vec4(self.y, self.z, self.y, self.y)
	@property
	def yzyz(self):
		return vec4(self.y, self.z, self.y, self.z)
	@property
	def gbgb(self):
		return vec4(self.y, self.z, self.y, self.z)
	@property
	def yzz(self):
		return vec3(self.y, self.z, self.z)
	@property
	def gbb(self):
		return vec3(self.y, self.z, self.z)
	@property
	def yzzx(self):
		return vec4(self.y, self.z, self.z, self.x)
	@property
	def gbbr(self):
		return vec4(self.y, self.z, self.z, self.x)
	@property
	def yzzy(self):
		return vec4(self.y, self.z, self.z, self.y)
	@property
	def gbbg(self):
		return vec4(self.y, self.z, self.z, self.y)
	@property
	def yzzz(self):
		return vec4(self.y, self.z, self.z, self.z)
	@property
	def gbbb(self):
		return vec4(self.y, self.z, self.z, self.z)
	@property
	def b(self):
		return self.z
	@property
	def zx(self):
		return vec2(self.z, self.x)
	@property
	def br(self):
		return vec2(self.z, self.x)
	@property
	def zxx(self):
		return vec3(self.z, self.x, self.x)
	@property
	def brr(self):
		return vec3(self.z, self.x, self.x)
	@property
	def zxxx(self):
		return vec4(self.z, self.x, self.x, self.x)
	@property
	def brrr(self):
		return vec4(self.z, self.x, self.x, self.x)
	@property
	def zxxy(self):
		return vec4(self.z, self.x, self.x, self.y)
	@property
	def brrg(self):
		return vec4(self.z, self.x, self.x, self.y)
	@property
	def zxxz(self):
		return vec4(self.z, self.x, self.x, self.z)
	@property
	def brrb(self):
		return vec4(self.z, self.x, self.x, self.z)
	@property
	def zxy(self):
		return vec3(self.z, self.x, self.y)
	@property
	def brg(self):
		return vec3(self.z, self.x, self.y)
	@property
	def zxyx(self):
		return vec4(self.z, self.x, self.y, self.x)
	@property
	def brgr(self):
		return vec4(self.z, self.x, self.y, self.x)
	@property
	def zxyy(self):
		return vec4(self.z, self.x, self.y, self.y)
	@property
	def brgg(self):
		return vec4(self.z, self.x, self.y, self.y)
	@property
	def zxyz(self):
		return vec4(self.z, self.x, self.y, self.z)
	@property
	def brgb(self):
		return vec4(self.z, self.x, self.y, self.z)
	@property
	def zxz(self):
		return vec3(self.z, self.x, self.z)
	@property
	def brb(self):
		return vec3(self.z, self.x, self.z)
	@property
	def zxzx(self):
		return vec4(self.z, self.x, self.z, self.x)
	@property
	def brbr(self):
		return vec4(self.z, self.x, self.z, self.x)
	@property
	def zxzy(self):
		return vec4(self.z, self.x, self.z, self.y)
	@property
	def brbg(self):
		return vec4(self.z, self.x, self.z, self.y)
	@property
	def zxzz(self):
		return vec4(self.z, self.x, self.z, self.z)
	@property
	def brbb(self):
		return vec4(self.z, self.x, self.z, self.z)
	@property
	def zy(self):
		return vec2(self.z, self.y)
	@property
	def bg(self):
		return vec2(self.z, self.y)
	@property
	def zyx(self):
		return vec3(self.z, self.y, self.x)
	@property
	def bgr(self):
		return vec3(self.z, self.y, self.x)
	@property
	def zyxx(self):
		return vec4(self.z, self.y, self.x, self.x)
	@property
	def bgrr(self):
		return vec4(self.z, self.y, self.x, self.x)
	@property
	def zyxy(self):
		return vec4(self.z, self.y, self.x, self.y)
	@property
	def bgrg(self):
		return vec4(self.z, self.y, self.x, self.y)
	@property
	def zyxz(self):
		return vec4(self.z, self.y, self.x, self.z)
	@property
	def bgrb(self):
		return vec4(self.z, self.y, self.x, self.z)
	@property
	def zyy(self):
		return vec3(self.z, self.y, self.y)
	@property
	def bgg(self):
		return vec3(self.z, self.y, self.y)
	@property
	def zyyx(self):
		return vec4(self.z, self.y, self.y, self.x)
	@property
	def bggr(self):
		return vec4(self.z, self.y, self.y, self.x)
	@property
	def zyyy(self):
		return vec4(self.z, self.y, self.y, self.y)
	@property
	def bggg(self):
		return vec4(self.z, self.y, self.y, self.y)
	@property
	def zyyz(self):
		return vec4(self.z, self.y, self.y, self.z)
	@property
	def bggb(self):
		return vec4(self.z, self.y, self.y, self.z)
	@property
	def zyz(self):
		return vec3(self.z, self.y, self.z)
	@property
	def bgb(self):
		return vec3(self.z, self.y, self.z)
	@property
	def zyzx(self):
		return vec4(self.z, self.y, self.z, self.x)
	@property
	def bgbr(self):
		return vec4(self.z, self.y, self.z, self.x)
	@property
	def zyzy(self):
		return vec4(self.z, self.y, self.z, self.y)
	@property
	def bgbg(self):
		return vec4(self.z, self.y, self.z, self.y)
	@property
	def zyzz(self):
		return vec4(self.z, self.y, self.z, self.z)
	@property
	def bgbb(self):
		return vec4(self.z, self.y, self.z, self.z)
	@property
	def zz(self):
		return vec2(self.z, self.z)
	@property
	def bb(self):
		return vec2(self.z, self.z)
	@property
	def zzx(self):
		return vec3(self.z, self.z, self.x)
	@property
	def bbr(self):
		return vec3(self.z, self.z, self.x)
	@property
	def zzxx(self):
		return vec4(self.z, self.z, self.x, self.x)
	@property
	def bbrr(self):
		return vec4(self.z, self.z, self.x, self.x)
	@property
	def zzxy(self):
		return vec4(self.z, self.z, self.x, self.y)
	@property
	def bbrg(self):
		return vec4(self.z, self.z, self.x, self.y)
	@property
	def zzxz(self):
		return vec4(self.z, self.z, self.x, self.z)
	@property
	def bbrb(self):
		return vec4(self.z, self.z, self.x, self.z)
	@property
	def zzy(self):
		return vec3(self.z, self.z, self.y)
	@property
	def bbg(self):
		return vec3(self.z, self.z, self.y)
	@property
	def zzyx(self):
		return vec4(self.z, self.z, self.y, self.x)
	@property
	def bbgr(self):
		return vec4(self.z, self.z, self.y, self.x)
	@property
	def zzyy(self):
		return vec4(self.z, self.z, self.y, self.y)
	@property
	def bbgg(self):
		return vec4(self.z, self.z, self.y, self.y)
	@property
	def zzyz(self):
		return vec4(self.z, self.z, self.y, self.z)
	@property
	def bbgb(self):
		return vec4(self.z, self.z, self.y, self.z)
	@property
	def zzz(self):
		return vec3(self.z, self.z, self.z)
	@property
	def bbb(self):
		return vec3(self.z, self.z, self.z)
	@property
	def zzzx(self):
		return vec4(self.z, self.z, self.z, self.x)
	@property
	def bbbr(self):
		return vec4(self.z, self.z, self.z, self.x)
	@property
	def zzzy(self):
		return vec4(self.z, self.z, self.z, self.y)
	@property
	def bbbg(self):
		return vec4(self.z, self.z, self.z, self.y)
	@property
	def zzzz(self):
		return vec4(self.z, self.z, self.z, self.z)
	@property
	def bbbb(self):
		return vec4(self.z, self.z, self.z, self.z)

class vec4(object):
	__slots__ = 'x', 'y', 'z', 'w'

	def __init__(self, x, y=None, z=None, w=None):
		self.x = x
		self.y = y
		self.z = z
		self.w = w

	def __repr__(self):
		return "vec4(%s, %s, %s, %s)" % (self.x, self.y, self.z, self.w,)

	def dot(self, other):
		#assert type(self) is type(other)
		return self.x*other.x+self.y*other.y+self.z*other.z+self.w*other.w


	def length(self):
		return self.dot(self)**0.5


	def normalize(self):
		return self/self.length()


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


	@property
	def r(self):
		return self.x
	@property
	def xx(self):
		return vec2(self.x, self.x)
	@property
	def rr(self):
		return vec2(self.x, self.x)
	@property
	def xxx(self):
		return vec3(self.x, self.x, self.x)
	@property
	def rrr(self):
		return vec3(self.x, self.x, self.x)
	@property
	def xxxx(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def rrrr(self):
		return vec4(self.x, self.x, self.x, self.x)
	@property
	def xxxy(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def rrrg(self):
		return vec4(self.x, self.x, self.x, self.y)
	@property
	def xxxz(self):
		return vec4(self.x, self.x, self.x, self.z)
	@property
	def rrrb(self):
		return vec4(self.x, self.x, self.x, self.z)
	@property
	def xxxw(self):
		return vec4(self.x, self.x, self.x, self.w)
	@property
	def rrra(self):
		return vec4(self.x, self.x, self.x, self.w)
	@property
	def xxy(self):
		return vec3(self.x, self.x, self.y)
	@property
	def rrg(self):
		return vec3(self.x, self.x, self.y)
	@property
	def xxyx(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def rrgr(self):
		return vec4(self.x, self.x, self.y, self.x)
	@property
	def xxyy(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def rrgg(self):
		return vec4(self.x, self.x, self.y, self.y)
	@property
	def xxyz(self):
		return vec4(self.x, self.x, self.y, self.z)
	@property
	def rrgb(self):
		return vec4(self.x, self.x, self.y, self.z)
	@property
	def xxyw(self):
		return vec4(self.x, self.x, self.y, self.w)
	@property
	def rrga(self):
		return vec4(self.x, self.x, self.y, self.w)
	@property
	def xxz(self):
		return vec3(self.x, self.x, self.z)
	@property
	def rrb(self):
		return vec3(self.x, self.x, self.z)
	@property
	def xxzx(self):
		return vec4(self.x, self.x, self.z, self.x)
	@property
	def rrbr(self):
		return vec4(self.x, self.x, self.z, self.x)
	@property
	def xxzy(self):
		return vec4(self.x, self.x, self.z, self.y)
	@property
	def rrbg(self):
		return vec4(self.x, self.x, self.z, self.y)
	@property
	def xxzz(self):
		return vec4(self.x, self.x, self.z, self.z)
	@property
	def rrbb(self):
		return vec4(self.x, self.x, self.z, self.z)
	@property
	def xxzw(self):
		return vec4(self.x, self.x, self.z, self.w)
	@property
	def rrba(self):
		return vec4(self.x, self.x, self.z, self.w)
	@property
	def xxw(self):
		return vec3(self.x, self.x, self.w)
	@property
	def rra(self):
		return vec3(self.x, self.x, self.w)
	@property
	def xxwx(self):
		return vec4(self.x, self.x, self.w, self.x)
	@property
	def rrar(self):
		return vec4(self.x, self.x, self.w, self.x)
	@property
	def xxwy(self):
		return vec4(self.x, self.x, self.w, self.y)
	@property
	def rrag(self):
		return vec4(self.x, self.x, self.w, self.y)
	@property
	def xxwz(self):
		return vec4(self.x, self.x, self.w, self.z)
	@property
	def rrab(self):
		return vec4(self.x, self.x, self.w, self.z)
	@property
	def xxww(self):
		return vec4(self.x, self.x, self.w, self.w)
	@property
	def rraa(self):
		return vec4(self.x, self.x, self.w, self.w)
	@property
	def xy(self):
		return vec2(self.x, self.y)
	@property
	def rg(self):
		return vec2(self.x, self.y)
	@property
	def xyx(self):
		return vec3(self.x, self.y, self.x)
	@property
	def rgr(self):
		return vec3(self.x, self.y, self.x)
	@property
	def xyxx(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def rgrr(self):
		return vec4(self.x, self.y, self.x, self.x)
	@property
	def xyxy(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def rgrg(self):
		return vec4(self.x, self.y, self.x, self.y)
	@property
	def xyxz(self):
		return vec4(self.x, self.y, self.x, self.z)
	@property
	def rgrb(self):
		return vec4(self.x, self.y, self.x, self.z)
	@property
	def xyxw(self):
		return vec4(self.x, self.y, self.x, self.w)
	@property
	def rgra(self):
		return vec4(self.x, self.y, self.x, self.w)
	@property
	def xyy(self):
		return vec3(self.x, self.y, self.y)
	@property
	def rgg(self):
		return vec3(self.x, self.y, self.y)
	@property
	def xyyx(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def rggr(self):
		return vec4(self.x, self.y, self.y, self.x)
	@property
	def xyyy(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def rggg(self):
		return vec4(self.x, self.y, self.y, self.y)
	@property
	def xyyz(self):
		return vec4(self.x, self.y, self.y, self.z)
	@property
	def rggb(self):
		return vec4(self.x, self.y, self.y, self.z)
	@property
	def xyyw(self):
		return vec4(self.x, self.y, self.y, self.w)
	@property
	def rgga(self):
		return vec4(self.x, self.y, self.y, self.w)
	@property
	def xyz(self):
		return vec3(self.x, self.y, self.z)
	@property
	def rgb(self):
		return vec3(self.x, self.y, self.z)
	@property
	def xyzx(self):
		return vec4(self.x, self.y, self.z, self.x)
	@property
	def rgbr(self):
		return vec4(self.x, self.y, self.z, self.x)
	@property
	def xyzy(self):
		return vec4(self.x, self.y, self.z, self.y)
	@property
	def rgbg(self):
		return vec4(self.x, self.y, self.z, self.y)
	@property
	def xyzz(self):
		return vec4(self.x, self.y, self.z, self.z)
	@property
	def rgbb(self):
		return vec4(self.x, self.y, self.z, self.z)
	@property
	def xyzw(self):
		return vec4(self.x, self.y, self.z, self.w)
	@property
	def rgba(self):
		return vec4(self.x, self.y, self.z, self.w)
	@property
	def xyw(self):
		return vec3(self.x, self.y, self.w)
	@property
	def rga(self):
		return vec3(self.x, self.y, self.w)
	@property
	def xywx(self):
		return vec4(self.x, self.y, self.w, self.x)
	@property
	def rgar(self):
		return vec4(self.x, self.y, self.w, self.x)
	@property
	def xywy(self):
		return vec4(self.x, self.y, self.w, self.y)
	@property
	def rgag(self):
		return vec4(self.x, self.y, self.w, self.y)
	@property
	def xywz(self):
		return vec4(self.x, self.y, self.w, self.z)
	@property
	def rgab(self):
		return vec4(self.x, self.y, self.w, self.z)
	@property
	def xyww(self):
		return vec4(self.x, self.y, self.w, self.w)
	@property
	def rgaa(self):
		return vec4(self.x, self.y, self.w, self.w)
	@property
	def xz(self):
		return vec2(self.x, self.z)
	@property
	def rb(self):
		return vec2(self.x, self.z)
	@property
	def xzx(self):
		return vec3(self.x, self.z, self.x)
	@property
	def rbr(self):
		return vec3(self.x, self.z, self.x)
	@property
	def xzxx(self):
		return vec4(self.x, self.z, self.x, self.x)
	@property
	def rbrr(self):
		return vec4(self.x, self.z, self.x, self.x)
	@property
	def xzxy(self):
		return vec4(self.x, self.z, self.x, self.y)
	@property
	def rbrg(self):
		return vec4(self.x, self.z, self.x, self.y)
	@property
	def xzxz(self):
		return vec4(self.x, self.z, self.x, self.z)
	@property
	def rbrb(self):
		return vec4(self.x, self.z, self.x, self.z)
	@property
	def xzxw(self):
		return vec4(self.x, self.z, self.x, self.w)
	@property
	def rbra(self):
		return vec4(self.x, self.z, self.x, self.w)
	@property
	def xzy(self):
		return vec3(self.x, self.z, self.y)
	@property
	def rbg(self):
		return vec3(self.x, self.z, self.y)
	@property
	def xzyx(self):
		return vec4(self.x, self.z, self.y, self.x)
	@property
	def rbgr(self):
		return vec4(self.x, self.z, self.y, self.x)
	@property
	def xzyy(self):
		return vec4(self.x, self.z, self.y, self.y)
	@property
	def rbgg(self):
		return vec4(self.x, self.z, self.y, self.y)
	@property
	def xzyz(self):
		return vec4(self.x, self.z, self.y, self.z)
	@property
	def rbgb(self):
		return vec4(self.x, self.z, self.y, self.z)
	@property
	def xzyw(self):
		return vec4(self.x, self.z, self.y, self.w)
	@property
	def rbga(self):
		return vec4(self.x, self.z, self.y, self.w)
	@property
	def xzz(self):
		return vec3(self.x, self.z, self.z)
	@property
	def rbb(self):
		return vec3(self.x, self.z, self.z)
	@property
	def xzzx(self):
		return vec4(self.x, self.z, self.z, self.x)
	@property
	def rbbr(self):
		return vec4(self.x, self.z, self.z, self.x)
	@property
	def xzzy(self):
		return vec4(self.x, self.z, self.z, self.y)
	@property
	def rbbg(self):
		return vec4(self.x, self.z, self.z, self.y)
	@property
	def xzzz(self):
		return vec4(self.x, self.z, self.z, self.z)
	@property
	def rbbb(self):
		return vec4(self.x, self.z, self.z, self.z)
	@property
	def xzzw(self):
		return vec4(self.x, self.z, self.z, self.w)
	@property
	def rbba(self):
		return vec4(self.x, self.z, self.z, self.w)
	@property
	def xzw(self):
		return vec3(self.x, self.z, self.w)
	@property
	def rba(self):
		return vec3(self.x, self.z, self.w)
	@property
	def xzwx(self):
		return vec4(self.x, self.z, self.w, self.x)
	@property
	def rbar(self):
		return vec4(self.x, self.z, self.w, self.x)
	@property
	def xzwy(self):
		return vec4(self.x, self.z, self.w, self.y)
	@property
	def rbag(self):
		return vec4(self.x, self.z, self.w, self.y)
	@property
	def xzwz(self):
		return vec4(self.x, self.z, self.w, self.z)
	@property
	def rbab(self):
		return vec4(self.x, self.z, self.w, self.z)
	@property
	def xzww(self):
		return vec4(self.x, self.z, self.w, self.w)
	@property
	def rbaa(self):
		return vec4(self.x, self.z, self.w, self.w)
	@property
	def xw(self):
		return vec2(self.x, self.w)
	@property
	def ra(self):
		return vec2(self.x, self.w)
	@property
	def xwx(self):
		return vec3(self.x, self.w, self.x)
	@property
	def rar(self):
		return vec3(self.x, self.w, self.x)
	@property
	def xwxx(self):
		return vec4(self.x, self.w, self.x, self.x)
	@property
	def rarr(self):
		return vec4(self.x, self.w, self.x, self.x)
	@property
	def xwxy(self):
		return vec4(self.x, self.w, self.x, self.y)
	@property
	def rarg(self):
		return vec4(self.x, self.w, self.x, self.y)
	@property
	def xwxz(self):
		return vec4(self.x, self.w, self.x, self.z)
	@property
	def rarb(self):
		return vec4(self.x, self.w, self.x, self.z)
	@property
	def xwxw(self):
		return vec4(self.x, self.w, self.x, self.w)
	@property
	def rara(self):
		return vec4(self.x, self.w, self.x, self.w)
	@property
	def xwy(self):
		return vec3(self.x, self.w, self.y)
	@property
	def rag(self):
		return vec3(self.x, self.w, self.y)
	@property
	def xwyx(self):
		return vec4(self.x, self.w, self.y, self.x)
	@property
	def ragr(self):
		return vec4(self.x, self.w, self.y, self.x)
	@property
	def xwyy(self):
		return vec4(self.x, self.w, self.y, self.y)
	@property
	def ragg(self):
		return vec4(self.x, self.w, self.y, self.y)
	@property
	def xwyz(self):
		return vec4(self.x, self.w, self.y, self.z)
	@property
	def ragb(self):
		return vec4(self.x, self.w, self.y, self.z)
	@property
	def xwyw(self):
		return vec4(self.x, self.w, self.y, self.w)
	@property
	def raga(self):
		return vec4(self.x, self.w, self.y, self.w)
	@property
	def xwz(self):
		return vec3(self.x, self.w, self.z)
	@property
	def rab(self):
		return vec3(self.x, self.w, self.z)
	@property
	def xwzx(self):
		return vec4(self.x, self.w, self.z, self.x)
	@property
	def rabr(self):
		return vec4(self.x, self.w, self.z, self.x)
	@property
	def xwzy(self):
		return vec4(self.x, self.w, self.z, self.y)
	@property
	def rabg(self):
		return vec4(self.x, self.w, self.z, self.y)
	@property
	def xwzz(self):
		return vec4(self.x, self.w, self.z, self.z)
	@property
	def rabb(self):
		return vec4(self.x, self.w, self.z, self.z)
	@property
	def xwzw(self):
		return vec4(self.x, self.w, self.z, self.w)
	@property
	def raba(self):
		return vec4(self.x, self.w, self.z, self.w)
	@property
	def xww(self):
		return vec3(self.x, self.w, self.w)
	@property
	def raa(self):
		return vec3(self.x, self.w, self.w)
	@property
	def xwwx(self):
		return vec4(self.x, self.w, self.w, self.x)
	@property
	def raar(self):
		return vec4(self.x, self.w, self.w, self.x)
	@property
	def xwwy(self):
		return vec4(self.x, self.w, self.w, self.y)
	@property
	def raag(self):
		return vec4(self.x, self.w, self.w, self.y)
	@property
	def xwwz(self):
		return vec4(self.x, self.w, self.w, self.z)
	@property
	def raab(self):
		return vec4(self.x, self.w, self.w, self.z)
	@property
	def xwww(self):
		return vec4(self.x, self.w, self.w, self.w)
	@property
	def raaa(self):
		return vec4(self.x, self.w, self.w, self.w)
	@property
	def g(self):
		return self.y
	@property
	def yx(self):
		return vec2(self.y, self.x)
	@property
	def gr(self):
		return vec2(self.y, self.x)
	@property
	def yxx(self):
		return vec3(self.y, self.x, self.x)
	@property
	def grr(self):
		return vec3(self.y, self.x, self.x)
	@property
	def yxxx(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def grrr(self):
		return vec4(self.y, self.x, self.x, self.x)
	@property
	def yxxy(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def grrg(self):
		return vec4(self.y, self.x, self.x, self.y)
	@property
	def yxxz(self):
		return vec4(self.y, self.x, self.x, self.z)
	@property
	def grrb(self):
		return vec4(self.y, self.x, self.x, self.z)
	@property
	def yxxw(self):
		return vec4(self.y, self.x, self.x, self.w)
	@property
	def grra(self):
		return vec4(self.y, self.x, self.x, self.w)
	@property
	def yxy(self):
		return vec3(self.y, self.x, self.y)
	@property
	def grg(self):
		return vec3(self.y, self.x, self.y)
	@property
	def yxyx(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def grgr(self):
		return vec4(self.y, self.x, self.y, self.x)
	@property
	def yxyy(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def grgg(self):
		return vec4(self.y, self.x, self.y, self.y)
	@property
	def yxyz(self):
		return vec4(self.y, self.x, self.y, self.z)
	@property
	def grgb(self):
		return vec4(self.y, self.x, self.y, self.z)
	@property
	def yxyw(self):
		return vec4(self.y, self.x, self.y, self.w)
	@property
	def grga(self):
		return vec4(self.y, self.x, self.y, self.w)
	@property
	def yxz(self):
		return vec3(self.y, self.x, self.z)
	@property
	def grb(self):
		return vec3(self.y, self.x, self.z)
	@property
	def yxzx(self):
		return vec4(self.y, self.x, self.z, self.x)
	@property
	def grbr(self):
		return vec4(self.y, self.x, self.z, self.x)
	@property
	def yxzy(self):
		return vec4(self.y, self.x, self.z, self.y)
	@property
	def grbg(self):
		return vec4(self.y, self.x, self.z, self.y)
	@property
	def yxzz(self):
		return vec4(self.y, self.x, self.z, self.z)
	@property
	def grbb(self):
		return vec4(self.y, self.x, self.z, self.z)
	@property
	def yxzw(self):
		return vec4(self.y, self.x, self.z, self.w)
	@property
	def grba(self):
		return vec4(self.y, self.x, self.z, self.w)
	@property
	def yxw(self):
		return vec3(self.y, self.x, self.w)
	@property
	def gra(self):
		return vec3(self.y, self.x, self.w)
	@property
	def yxwx(self):
		return vec4(self.y, self.x, self.w, self.x)
	@property
	def grar(self):
		return vec4(self.y, self.x, self.w, self.x)
	@property
	def yxwy(self):
		return vec4(self.y, self.x, self.w, self.y)
	@property
	def grag(self):
		return vec4(self.y, self.x, self.w, self.y)
	@property
	def yxwz(self):
		return vec4(self.y, self.x, self.w, self.z)
	@property
	def grab(self):
		return vec4(self.y, self.x, self.w, self.z)
	@property
	def yxww(self):
		return vec4(self.y, self.x, self.w, self.w)
	@property
	def graa(self):
		return vec4(self.y, self.x, self.w, self.w)
	@property
	def yy(self):
		return vec2(self.y, self.y)
	@property
	def gg(self):
		return vec2(self.y, self.y)
	@property
	def yyx(self):
		return vec3(self.y, self.y, self.x)
	@property
	def ggr(self):
		return vec3(self.y, self.y, self.x)
	@property
	def yyxx(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def ggrr(self):
		return vec4(self.y, self.y, self.x, self.x)
	@property
	def yyxy(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def ggrg(self):
		return vec4(self.y, self.y, self.x, self.y)
	@property
	def yyxz(self):
		return vec4(self.y, self.y, self.x, self.z)
	@property
	def ggrb(self):
		return vec4(self.y, self.y, self.x, self.z)
	@property
	def yyxw(self):
		return vec4(self.y, self.y, self.x, self.w)
	@property
	def ggra(self):
		return vec4(self.y, self.y, self.x, self.w)
	@property
	def yyy(self):
		return vec3(self.y, self.y, self.y)
	@property
	def ggg(self):
		return vec3(self.y, self.y, self.y)
	@property
	def yyyx(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def gggr(self):
		return vec4(self.y, self.y, self.y, self.x)
	@property
	def yyyy(self):
		return vec4(self.y, self.y, self.y, self.y)
	@property
	def gggg(self):
		return vec4(self.y, self.y, self.y, self.y)
	@property
	def yyyz(self):
		return vec4(self.y, self.y, self.y, self.z)
	@property
	def gggb(self):
		return vec4(self.y, self.y, self.y, self.z)
	@property
	def yyyw(self):
		return vec4(self.y, self.y, self.y, self.w)
	@property
	def ggga(self):
		return vec4(self.y, self.y, self.y, self.w)
	@property
	def yyz(self):
		return vec3(self.y, self.y, self.z)
	@property
	def ggb(self):
		return vec3(self.y, self.y, self.z)
	@property
	def yyzx(self):
		return vec4(self.y, self.y, self.z, self.x)
	@property
	def ggbr(self):
		return vec4(self.y, self.y, self.z, self.x)
	@property
	def yyzy(self):
		return vec4(self.y, self.y, self.z, self.y)
	@property
	def ggbg(self):
		return vec4(self.y, self.y, self.z, self.y)
	@property
	def yyzz(self):
		return vec4(self.y, self.y, self.z, self.z)
	@property
	def ggbb(self):
		return vec4(self.y, self.y, self.z, self.z)
	@property
	def yyzw(self):
		return vec4(self.y, self.y, self.z, self.w)
	@property
	def ggba(self):
		return vec4(self.y, self.y, self.z, self.w)
	@property
	def yyw(self):
		return vec3(self.y, self.y, self.w)
	@property
	def gga(self):
		return vec3(self.y, self.y, self.w)
	@property
	def yywx(self):
		return vec4(self.y, self.y, self.w, self.x)
	@property
	def ggar(self):
		return vec4(self.y, self.y, self.w, self.x)
	@property
	def yywy(self):
		return vec4(self.y, self.y, self.w, self.y)
	@property
	def ggag(self):
		return vec4(self.y, self.y, self.w, self.y)
	@property
	def yywz(self):
		return vec4(self.y, self.y, self.w, self.z)
	@property
	def ggab(self):
		return vec4(self.y, self.y, self.w, self.z)
	@property
	def yyww(self):
		return vec4(self.y, self.y, self.w, self.w)
	@property
	def ggaa(self):
		return vec4(self.y, self.y, self.w, self.w)
	@property
	def yz(self):
		return vec2(self.y, self.z)
	@property
	def gb(self):
		return vec2(self.y, self.z)
	@property
	def yzx(self):
		return vec3(self.y, self.z, self.x)
	@property
	def gbr(self):
		return vec3(self.y, self.z, self.x)
	@property
	def yzxx(self):
		return vec4(self.y, self.z, self.x, self.x)
	@property
	def gbrr(self):
		return vec4(self.y, self.z, self.x, self.x)
	@property
	def yzxy(self):
		return vec4(self.y, self.z, self.x, self.y)
	@property
	def gbrg(self):
		return vec4(self.y, self.z, self.x, self.y)
	@property
	def yzxz(self):
		return vec4(self.y, self.z, self.x, self.z)
	@property
	def gbrb(self):
		return vec4(self.y, self.z, self.x, self.z)
	@property
	def yzxw(self):
		return vec4(self.y, self.z, self.x, self.w)
	@property
	def gbra(self):
		return vec4(self.y, self.z, self.x, self.w)
	@property
	def yzy(self):
		return vec3(self.y, self.z, self.y)
	@property
	def gbg(self):
		return vec3(self.y, self.z, self.y)
	@property
	def yzyx(self):
		return vec4(self.y, self.z, self.y, self.x)
	@property
	def gbgr(self):
		return vec4(self.y, self.z, self.y, self.x)
	@property
	def yzyy(self):
		return vec4(self.y, self.z, self.y, self.y)
	@property
	def gbgg(self):
		return vec4(self.y, self.z, self.y, self.y)
	@property
	def yzyz(self):
		return vec4(self.y, self.z, self.y, self.z)
	@property
	def gbgb(self):
		return vec4(self.y, self.z, self.y, self.z)
	@property
	def yzyw(self):
		return vec4(self.y, self.z, self.y, self.w)
	@property
	def gbga(self):
		return vec4(self.y, self.z, self.y, self.w)
	@property
	def yzz(self):
		return vec3(self.y, self.z, self.z)
	@property
	def gbb(self):
		return vec3(self.y, self.z, self.z)
	@property
	def yzzx(self):
		return vec4(self.y, self.z, self.z, self.x)
	@property
	def gbbr(self):
		return vec4(self.y, self.z, self.z, self.x)
	@property
	def yzzy(self):
		return vec4(self.y, self.z, self.z, self.y)
	@property
	def gbbg(self):
		return vec4(self.y, self.z, self.z, self.y)
	@property
	def yzzz(self):
		return vec4(self.y, self.z, self.z, self.z)
	@property
	def gbbb(self):
		return vec4(self.y, self.z, self.z, self.z)
	@property
	def yzzw(self):
		return vec4(self.y, self.z, self.z, self.w)
	@property
	def gbba(self):
		return vec4(self.y, self.z, self.z, self.w)
	@property
	def yzw(self):
		return vec3(self.y, self.z, self.w)
	@property
	def gba(self):
		return vec3(self.y, self.z, self.w)
	@property
	def yzwx(self):
		return vec4(self.y, self.z, self.w, self.x)
	@property
	def gbar(self):
		return vec4(self.y, self.z, self.w, self.x)
	@property
	def yzwy(self):
		return vec4(self.y, self.z, self.w, self.y)
	@property
	def gbag(self):
		return vec4(self.y, self.z, self.w, self.y)
	@property
	def yzwz(self):
		return vec4(self.y, self.z, self.w, self.z)
	@property
	def gbab(self):
		return vec4(self.y, self.z, self.w, self.z)
	@property
	def yzww(self):
		return vec4(self.y, self.z, self.w, self.w)
	@property
	def gbaa(self):
		return vec4(self.y, self.z, self.w, self.w)
	@property
	def yw(self):
		return vec2(self.y, self.w)
	@property
	def ga(self):
		return vec2(self.y, self.w)
	@property
	def ywx(self):
		return vec3(self.y, self.w, self.x)
	@property
	def gar(self):
		return vec3(self.y, self.w, self.x)
	@property
	def ywxx(self):
		return vec4(self.y, self.w, self.x, self.x)
	@property
	def garr(self):
		return vec4(self.y, self.w, self.x, self.x)
	@property
	def ywxy(self):
		return vec4(self.y, self.w, self.x, self.y)
	@property
	def garg(self):
		return vec4(self.y, self.w, self.x, self.y)
	@property
	def ywxz(self):
		return vec4(self.y, self.w, self.x, self.z)
	@property
	def garb(self):
		return vec4(self.y, self.w, self.x, self.z)
	@property
	def ywxw(self):
		return vec4(self.y, self.w, self.x, self.w)
	@property
	def gara(self):
		return vec4(self.y, self.w, self.x, self.w)
	@property
	def ywy(self):
		return vec3(self.y, self.w, self.y)
	@property
	def gag(self):
		return vec3(self.y, self.w, self.y)
	@property
	def ywyx(self):
		return vec4(self.y, self.w, self.y, self.x)
	@property
	def gagr(self):
		return vec4(self.y, self.w, self.y, self.x)
	@property
	def ywyy(self):
		return vec4(self.y, self.w, self.y, self.y)
	@property
	def gagg(self):
		return vec4(self.y, self.w, self.y, self.y)
	@property
	def ywyz(self):
		return vec4(self.y, self.w, self.y, self.z)
	@property
	def gagb(self):
		return vec4(self.y, self.w, self.y, self.z)
	@property
	def ywyw(self):
		return vec4(self.y, self.w, self.y, self.w)
	@property
	def gaga(self):
		return vec4(self.y, self.w, self.y, self.w)
	@property
	def ywz(self):
		return vec3(self.y, self.w, self.z)
	@property
	def gab(self):
		return vec3(self.y, self.w, self.z)
	@property
	def ywzx(self):
		return vec4(self.y, self.w, self.z, self.x)
	@property
	def gabr(self):
		return vec4(self.y, self.w, self.z, self.x)
	@property
	def ywzy(self):
		return vec4(self.y, self.w, self.z, self.y)
	@property
	def gabg(self):
		return vec4(self.y, self.w, self.z, self.y)
	@property
	def ywzz(self):
		return vec4(self.y, self.w, self.z, self.z)
	@property
	def gabb(self):
		return vec4(self.y, self.w, self.z, self.z)
	@property
	def ywzw(self):
		return vec4(self.y, self.w, self.z, self.w)
	@property
	def gaba(self):
		return vec4(self.y, self.w, self.z, self.w)
	@property
	def yww(self):
		return vec3(self.y, self.w, self.w)
	@property
	def gaa(self):
		return vec3(self.y, self.w, self.w)
	@property
	def ywwx(self):
		return vec4(self.y, self.w, self.w, self.x)
	@property
	def gaar(self):
		return vec4(self.y, self.w, self.w, self.x)
	@property
	def ywwy(self):
		return vec4(self.y, self.w, self.w, self.y)
	@property
	def gaag(self):
		return vec4(self.y, self.w, self.w, self.y)
	@property
	def ywwz(self):
		return vec4(self.y, self.w, self.w, self.z)
	@property
	def gaab(self):
		return vec4(self.y, self.w, self.w, self.z)
	@property
	def ywww(self):
		return vec4(self.y, self.w, self.w, self.w)
	@property
	def gaaa(self):
		return vec4(self.y, self.w, self.w, self.w)
	@property
	def b(self):
		return self.z
	@property
	def zx(self):
		return vec2(self.z, self.x)
	@property
	def br(self):
		return vec2(self.z, self.x)
	@property
	def zxx(self):
		return vec3(self.z, self.x, self.x)
	@property
	def brr(self):
		return vec3(self.z, self.x, self.x)
	@property
	def zxxx(self):
		return vec4(self.z, self.x, self.x, self.x)
	@property
	def brrr(self):
		return vec4(self.z, self.x, self.x, self.x)
	@property
	def zxxy(self):
		return vec4(self.z, self.x, self.x, self.y)
	@property
	def brrg(self):
		return vec4(self.z, self.x, self.x, self.y)
	@property
	def zxxz(self):
		return vec4(self.z, self.x, self.x, self.z)
	@property
	def brrb(self):
		return vec4(self.z, self.x, self.x, self.z)
	@property
	def zxxw(self):
		return vec4(self.z, self.x, self.x, self.w)
	@property
	def brra(self):
		return vec4(self.z, self.x, self.x, self.w)
	@property
	def zxy(self):
		return vec3(self.z, self.x, self.y)
	@property
	def brg(self):
		return vec3(self.z, self.x, self.y)
	@property
	def zxyx(self):
		return vec4(self.z, self.x, self.y, self.x)
	@property
	def brgr(self):
		return vec4(self.z, self.x, self.y, self.x)
	@property
	def zxyy(self):
		return vec4(self.z, self.x, self.y, self.y)
	@property
	def brgg(self):
		return vec4(self.z, self.x, self.y, self.y)
	@property
	def zxyz(self):
		return vec4(self.z, self.x, self.y, self.z)
	@property
	def brgb(self):
		return vec4(self.z, self.x, self.y, self.z)
	@property
	def zxyw(self):
		return vec4(self.z, self.x, self.y, self.w)
	@property
	def brga(self):
		return vec4(self.z, self.x, self.y, self.w)
	@property
	def zxz(self):
		return vec3(self.z, self.x, self.z)
	@property
	def brb(self):
		return vec3(self.z, self.x, self.z)
	@property
	def zxzx(self):
		return vec4(self.z, self.x, self.z, self.x)
	@property
	def brbr(self):
		return vec4(self.z, self.x, self.z, self.x)
	@property
	def zxzy(self):
		return vec4(self.z, self.x, self.z, self.y)
	@property
	def brbg(self):
		return vec4(self.z, self.x, self.z, self.y)
	@property
	def zxzz(self):
		return vec4(self.z, self.x, self.z, self.z)
	@property
	def brbb(self):
		return vec4(self.z, self.x, self.z, self.z)
	@property
	def zxzw(self):
		return vec4(self.z, self.x, self.z, self.w)
	@property
	def brba(self):
		return vec4(self.z, self.x, self.z, self.w)
	@property
	def zxw(self):
		return vec3(self.z, self.x, self.w)
	@property
	def bra(self):
		return vec3(self.z, self.x, self.w)
	@property
	def zxwx(self):
		return vec4(self.z, self.x, self.w, self.x)
	@property
	def brar(self):
		return vec4(self.z, self.x, self.w, self.x)
	@property
	def zxwy(self):
		return vec4(self.z, self.x, self.w, self.y)
	@property
	def brag(self):
		return vec4(self.z, self.x, self.w, self.y)
	@property
	def zxwz(self):
		return vec4(self.z, self.x, self.w, self.z)
	@property
	def brab(self):
		return vec4(self.z, self.x, self.w, self.z)
	@property
	def zxww(self):
		return vec4(self.z, self.x, self.w, self.w)
	@property
	def braa(self):
		return vec4(self.z, self.x, self.w, self.w)
	@property
	def zy(self):
		return vec2(self.z, self.y)
	@property
	def bg(self):
		return vec2(self.z, self.y)
	@property
	def zyx(self):
		return vec3(self.z, self.y, self.x)
	@property
	def bgr(self):
		return vec3(self.z, self.y, self.x)
	@property
	def zyxx(self):
		return vec4(self.z, self.y, self.x, self.x)
	@property
	def bgrr(self):
		return vec4(self.z, self.y, self.x, self.x)
	@property
	def zyxy(self):
		return vec4(self.z, self.y, self.x, self.y)
	@property
	def bgrg(self):
		return vec4(self.z, self.y, self.x, self.y)
	@property
	def zyxz(self):
		return vec4(self.z, self.y, self.x, self.z)
	@property
	def bgrb(self):
		return vec4(self.z, self.y, self.x, self.z)
	@property
	def zyxw(self):
		return vec4(self.z, self.y, self.x, self.w)
	@property
	def bgra(self):
		return vec4(self.z, self.y, self.x, self.w)
	@property
	def zyy(self):
		return vec3(self.z, self.y, self.y)
	@property
	def bgg(self):
		return vec3(self.z, self.y, self.y)
	@property
	def zyyx(self):
		return vec4(self.z, self.y, self.y, self.x)
	@property
	def bggr(self):
		return vec4(self.z, self.y, self.y, self.x)
	@property
	def zyyy(self):
		return vec4(self.z, self.y, self.y, self.y)
	@property
	def bggg(self):
		return vec4(self.z, self.y, self.y, self.y)
	@property
	def zyyz(self):
		return vec4(self.z, self.y, self.y, self.z)
	@property
	def bggb(self):
		return vec4(self.z, self.y, self.y, self.z)
	@property
	def zyyw(self):
		return vec4(self.z, self.y, self.y, self.w)
	@property
	def bgga(self):
		return vec4(self.z, self.y, self.y, self.w)
	@property
	def zyz(self):
		return vec3(self.z, self.y, self.z)
	@property
	def bgb(self):
		return vec3(self.z, self.y, self.z)
	@property
	def zyzx(self):
		return vec4(self.z, self.y, self.z, self.x)
	@property
	def bgbr(self):
		return vec4(self.z, self.y, self.z, self.x)
	@property
	def zyzy(self):
		return vec4(self.z, self.y, self.z, self.y)
	@property
	def bgbg(self):
		return vec4(self.z, self.y, self.z, self.y)
	@property
	def zyzz(self):
		return vec4(self.z, self.y, self.z, self.z)
	@property
	def bgbb(self):
		return vec4(self.z, self.y, self.z, self.z)
	@property
	def zyzw(self):
		return vec4(self.z, self.y, self.z, self.w)
	@property
	def bgba(self):
		return vec4(self.z, self.y, self.z, self.w)
	@property
	def zyw(self):
		return vec3(self.z, self.y, self.w)
	@property
	def bga(self):
		return vec3(self.z, self.y, self.w)
	@property
	def zywx(self):
		return vec4(self.z, self.y, self.w, self.x)
	@property
	def bgar(self):
		return vec4(self.z, self.y, self.w, self.x)
	@property
	def zywy(self):
		return vec4(self.z, self.y, self.w, self.y)
	@property
	def bgag(self):
		return vec4(self.z, self.y, self.w, self.y)
	@property
	def zywz(self):
		return vec4(self.z, self.y, self.w, self.z)
	@property
	def bgab(self):
		return vec4(self.z, self.y, self.w, self.z)
	@property
	def zyww(self):
		return vec4(self.z, self.y, self.w, self.w)
	@property
	def bgaa(self):
		return vec4(self.z, self.y, self.w, self.w)
	@property
	def zz(self):
		return vec2(self.z, self.z)
	@property
	def bb(self):
		return vec2(self.z, self.z)
	@property
	def zzx(self):
		return vec3(self.z, self.z, self.x)
	@property
	def bbr(self):
		return vec3(self.z, self.z, self.x)
	@property
	def zzxx(self):
		return vec4(self.z, self.z, self.x, self.x)
	@property
	def bbrr(self):
		return vec4(self.z, self.z, self.x, self.x)
	@property
	def zzxy(self):
		return vec4(self.z, self.z, self.x, self.y)
	@property
	def bbrg(self):
		return vec4(self.z, self.z, self.x, self.y)
	@property
	def zzxz(self):
		return vec4(self.z, self.z, self.x, self.z)
	@property
	def bbrb(self):
		return vec4(self.z, self.z, self.x, self.z)
	@property
	def zzxw(self):
		return vec4(self.z, self.z, self.x, self.w)
	@property
	def bbra(self):
		return vec4(self.z, self.z, self.x, self.w)
	@property
	def zzy(self):
		return vec3(self.z, self.z, self.y)
	@property
	def bbg(self):
		return vec3(self.z, self.z, self.y)
	@property
	def zzyx(self):
		return vec4(self.z, self.z, self.y, self.x)
	@property
	def bbgr(self):
		return vec4(self.z, self.z, self.y, self.x)
	@property
	def zzyy(self):
		return vec4(self.z, self.z, self.y, self.y)
	@property
	def bbgg(self):
		return vec4(self.z, self.z, self.y, self.y)
	@property
	def zzyz(self):
		return vec4(self.z, self.z, self.y, self.z)
	@property
	def bbgb(self):
		return vec4(self.z, self.z, self.y, self.z)
	@property
	def zzyw(self):
		return vec4(self.z, self.z, self.y, self.w)
	@property
	def bbga(self):
		return vec4(self.z, self.z, self.y, self.w)
	@property
	def zzz(self):
		return vec3(self.z, self.z, self.z)
	@property
	def bbb(self):
		return vec3(self.z, self.z, self.z)
	@property
	def zzzx(self):
		return vec4(self.z, self.z, self.z, self.x)
	@property
	def bbbr(self):
		return vec4(self.z, self.z, self.z, self.x)
	@property
	def zzzy(self):
		return vec4(self.z, self.z, self.z, self.y)
	@property
	def bbbg(self):
		return vec4(self.z, self.z, self.z, self.y)
	@property
	def zzzz(self):
		return vec4(self.z, self.z, self.z, self.z)
	@property
	def bbbb(self):
		return vec4(self.z, self.z, self.z, self.z)
	@property
	def zzzw(self):
		return vec4(self.z, self.z, self.z, self.w)
	@property
	def bbba(self):
		return vec4(self.z, self.z, self.z, self.w)
	@property
	def zzw(self):
		return vec3(self.z, self.z, self.w)
	@property
	def bba(self):
		return vec3(self.z, self.z, self.w)
	@property
	def zzwx(self):
		return vec4(self.z, self.z, self.w, self.x)
	@property
	def bbar(self):
		return vec4(self.z, self.z, self.w, self.x)
	@property
	def zzwy(self):
		return vec4(self.z, self.z, self.w, self.y)
	@property
	def bbag(self):
		return vec4(self.z, self.z, self.w, self.y)
	@property
	def zzwz(self):
		return vec4(self.z, self.z, self.w, self.z)
	@property
	def bbab(self):
		return vec4(self.z, self.z, self.w, self.z)
	@property
	def zzww(self):
		return vec4(self.z, self.z, self.w, self.w)
	@property
	def bbaa(self):
		return vec4(self.z, self.z, self.w, self.w)
	@property
	def zw(self):
		return vec2(self.z, self.w)
	@property
	def ba(self):
		return vec2(self.z, self.w)
	@property
	def zwx(self):
		return vec3(self.z, self.w, self.x)
	@property
	def bar(self):
		return vec3(self.z, self.w, self.x)
	@property
	def zwxx(self):
		return vec4(self.z, self.w, self.x, self.x)
	@property
	def barr(self):
		return vec4(self.z, self.w, self.x, self.x)
	@property
	def zwxy(self):
		return vec4(self.z, self.w, self.x, self.y)
	@property
	def barg(self):
		return vec4(self.z, self.w, self.x, self.y)
	@property
	def zwxz(self):
		return vec4(self.z, self.w, self.x, self.z)
	@property
	def barb(self):
		return vec4(self.z, self.w, self.x, self.z)
	@property
	def zwxw(self):
		return vec4(self.z, self.w, self.x, self.w)
	@property
	def bara(self):
		return vec4(self.z, self.w, self.x, self.w)
	@property
	def zwy(self):
		return vec3(self.z, self.w, self.y)
	@property
	def bag(self):
		return vec3(self.z, self.w, self.y)
	@property
	def zwyx(self):
		return vec4(self.z, self.w, self.y, self.x)
	@property
	def bagr(self):
		return vec4(self.z, self.w, self.y, self.x)
	@property
	def zwyy(self):
		return vec4(self.z, self.w, self.y, self.y)
	@property
	def bagg(self):
		return vec4(self.z, self.w, self.y, self.y)
	@property
	def zwyz(self):
		return vec4(self.z, self.w, self.y, self.z)
	@property
	def bagb(self):
		return vec4(self.z, self.w, self.y, self.z)
	@property
	def zwyw(self):
		return vec4(self.z, self.w, self.y, self.w)
	@property
	def baga(self):
		return vec4(self.z, self.w, self.y, self.w)
	@property
	def zwz(self):
		return vec3(self.z, self.w, self.z)
	@property
	def bab(self):
		return vec3(self.z, self.w, self.z)
	@property
	def zwzx(self):
		return vec4(self.z, self.w, self.z, self.x)
	@property
	def babr(self):
		return vec4(self.z, self.w, self.z, self.x)
	@property
	def zwzy(self):
		return vec4(self.z, self.w, self.z, self.y)
	@property
	def babg(self):
		return vec4(self.z, self.w, self.z, self.y)
	@property
	def zwzz(self):
		return vec4(self.z, self.w, self.z, self.z)
	@property
	def babb(self):
		return vec4(self.z, self.w, self.z, self.z)
	@property
	def zwzw(self):
		return vec4(self.z, self.w, self.z, self.w)
	@property
	def baba(self):
		return vec4(self.z, self.w, self.z, self.w)
	@property
	def zww(self):
		return vec3(self.z, self.w, self.w)
	@property
	def baa(self):
		return vec3(self.z, self.w, self.w)
	@property
	def zwwx(self):
		return vec4(self.z, self.w, self.w, self.x)
	@property
	def baar(self):
		return vec4(self.z, self.w, self.w, self.x)
	@property
	def zwwy(self):
		return vec4(self.z, self.w, self.w, self.y)
	@property
	def baag(self):
		return vec4(self.z, self.w, self.w, self.y)
	@property
	def zwwz(self):
		return vec4(self.z, self.w, self.w, self.z)
	@property
	def baab(self):
		return vec4(self.z, self.w, self.w, self.z)
	@property
	def zwww(self):
		return vec4(self.z, self.w, self.w, self.w)
	@property
	def baaa(self):
		return vec4(self.z, self.w, self.w, self.w)
	@property
	def a(self):
		return self.w
	@property
	def wx(self):
		return vec2(self.w, self.x)
	@property
	def ar(self):
		return vec2(self.w, self.x)
	@property
	def wxx(self):
		return vec3(self.w, self.x, self.x)
	@property
	def arr(self):
		return vec3(self.w, self.x, self.x)
	@property
	def wxxx(self):
		return vec4(self.w, self.x, self.x, self.x)
	@property
	def arrr(self):
		return vec4(self.w, self.x, self.x, self.x)
	@property
	def wxxy(self):
		return vec4(self.w, self.x, self.x, self.y)
	@property
	def arrg(self):
		return vec4(self.w, self.x, self.x, self.y)
	@property
	def wxxz(self):
		return vec4(self.w, self.x, self.x, self.z)
	@property
	def arrb(self):
		return vec4(self.w, self.x, self.x, self.z)
	@property
	def wxxw(self):
		return vec4(self.w, self.x, self.x, self.w)
	@property
	def arra(self):
		return vec4(self.w, self.x, self.x, self.w)
	@property
	def wxy(self):
		return vec3(self.w, self.x, self.y)
	@property
	def arg(self):
		return vec3(self.w, self.x, self.y)
	@property
	def wxyx(self):
		return vec4(self.w, self.x, self.y, self.x)
	@property
	def argr(self):
		return vec4(self.w, self.x, self.y, self.x)
	@property
	def wxyy(self):
		return vec4(self.w, self.x, self.y, self.y)
	@property
	def argg(self):
		return vec4(self.w, self.x, self.y, self.y)
	@property
	def wxyz(self):
		return vec4(self.w, self.x, self.y, self.z)
	@property
	def argb(self):
		return vec4(self.w, self.x, self.y, self.z)
	@property
	def wxyw(self):
		return vec4(self.w, self.x, self.y, self.w)
	@property
	def arga(self):
		return vec4(self.w, self.x, self.y, self.w)
	@property
	def wxz(self):
		return vec3(self.w, self.x, self.z)
	@property
	def arb(self):
		return vec3(self.w, self.x, self.z)
	@property
	def wxzx(self):
		return vec4(self.w, self.x, self.z, self.x)
	@property
	def arbr(self):
		return vec4(self.w, self.x, self.z, self.x)
	@property
	def wxzy(self):
		return vec4(self.w, self.x, self.z, self.y)
	@property
	def arbg(self):
		return vec4(self.w, self.x, self.z, self.y)
	@property
	def wxzz(self):
		return vec4(self.w, self.x, self.z, self.z)
	@property
	def arbb(self):
		return vec4(self.w, self.x, self.z, self.z)
	@property
	def wxzw(self):
		return vec4(self.w, self.x, self.z, self.w)
	@property
	def arba(self):
		return vec4(self.w, self.x, self.z, self.w)
	@property
	def wxw(self):
		return vec3(self.w, self.x, self.w)
	@property
	def ara(self):
		return vec3(self.w, self.x, self.w)
	@property
	def wxwx(self):
		return vec4(self.w, self.x, self.w, self.x)
	@property
	def arar(self):
		return vec4(self.w, self.x, self.w, self.x)
	@property
	def wxwy(self):
		return vec4(self.w, self.x, self.w, self.y)
	@property
	def arag(self):
		return vec4(self.w, self.x, self.w, self.y)
	@property
	def wxwz(self):
		return vec4(self.w, self.x, self.w, self.z)
	@property
	def arab(self):
		return vec4(self.w, self.x, self.w, self.z)
	@property
	def wxww(self):
		return vec4(self.w, self.x, self.w, self.w)
	@property
	def araa(self):
		return vec4(self.w, self.x, self.w, self.w)
	@property
	def wy(self):
		return vec2(self.w, self.y)
	@property
	def ag(self):
		return vec2(self.w, self.y)
	@property
	def wyx(self):
		return vec3(self.w, self.y, self.x)
	@property
	def agr(self):
		return vec3(self.w, self.y, self.x)
	@property
	def wyxx(self):
		return vec4(self.w, self.y, self.x, self.x)
	@property
	def agrr(self):
		return vec4(self.w, self.y, self.x, self.x)
	@property
	def wyxy(self):
		return vec4(self.w, self.y, self.x, self.y)
	@property
	def agrg(self):
		return vec4(self.w, self.y, self.x, self.y)
	@property
	def wyxz(self):
		return vec4(self.w, self.y, self.x, self.z)
	@property
	def agrb(self):
		return vec4(self.w, self.y, self.x, self.z)
	@property
	def wyxw(self):
		return vec4(self.w, self.y, self.x, self.w)
	@property
	def agra(self):
		return vec4(self.w, self.y, self.x, self.w)
	@property
	def wyy(self):
		return vec3(self.w, self.y, self.y)
	@property
	def agg(self):
		return vec3(self.w, self.y, self.y)
	@property
	def wyyx(self):
		return vec4(self.w, self.y, self.y, self.x)
	@property
	def aggr(self):
		return vec4(self.w, self.y, self.y, self.x)
	@property
	def wyyy(self):
		return vec4(self.w, self.y, self.y, self.y)
	@property
	def aggg(self):
		return vec4(self.w, self.y, self.y, self.y)
	@property
	def wyyz(self):
		return vec4(self.w, self.y, self.y, self.z)
	@property
	def aggb(self):
		return vec4(self.w, self.y, self.y, self.z)
	@property
	def wyyw(self):
		return vec4(self.w, self.y, self.y, self.w)
	@property
	def agga(self):
		return vec4(self.w, self.y, self.y, self.w)
	@property
	def wyz(self):
		return vec3(self.w, self.y, self.z)
	@property
	def agb(self):
		return vec3(self.w, self.y, self.z)
	@property
	def wyzx(self):
		return vec4(self.w, self.y, self.z, self.x)
	@property
	def agbr(self):
		return vec4(self.w, self.y, self.z, self.x)
	@property
	def wyzy(self):
		return vec4(self.w, self.y, self.z, self.y)
	@property
	def agbg(self):
		return vec4(self.w, self.y, self.z, self.y)
	@property
	def wyzz(self):
		return vec4(self.w, self.y, self.z, self.z)
	@property
	def agbb(self):
		return vec4(self.w, self.y, self.z, self.z)
	@property
	def wyzw(self):
		return vec4(self.w, self.y, self.z, self.w)
	@property
	def agba(self):
		return vec4(self.w, self.y, self.z, self.w)
	@property
	def wyw(self):
		return vec3(self.w, self.y, self.w)
	@property
	def aga(self):
		return vec3(self.w, self.y, self.w)
	@property
	def wywx(self):
		return vec4(self.w, self.y, self.w, self.x)
	@property
	def agar(self):
		return vec4(self.w, self.y, self.w, self.x)
	@property
	def wywy(self):
		return vec4(self.w, self.y, self.w, self.y)
	@property
	def agag(self):
		return vec4(self.w, self.y, self.w, self.y)
	@property
	def wywz(self):
		return vec4(self.w, self.y, self.w, self.z)
	@property
	def agab(self):
		return vec4(self.w, self.y, self.w, self.z)
	@property
	def wyww(self):
		return vec4(self.w, self.y, self.w, self.w)
	@property
	def agaa(self):
		return vec4(self.w, self.y, self.w, self.w)
	@property
	def wz(self):
		return vec2(self.w, self.z)
	@property
	def ab(self):
		return vec2(self.w, self.z)
	@property
	def wzx(self):
		return vec3(self.w, self.z, self.x)
	@property
	def abr(self):
		return vec3(self.w, self.z, self.x)
	@property
	def wzxx(self):
		return vec4(self.w, self.z, self.x, self.x)
	@property
	def abrr(self):
		return vec4(self.w, self.z, self.x, self.x)
	@property
	def wzxy(self):
		return vec4(self.w, self.z, self.x, self.y)
	@property
	def abrg(self):
		return vec4(self.w, self.z, self.x, self.y)
	@property
	def wzxz(self):
		return vec4(self.w, self.z, self.x, self.z)
	@property
	def abrb(self):
		return vec4(self.w, self.z, self.x, self.z)
	@property
	def wzxw(self):
		return vec4(self.w, self.z, self.x, self.w)
	@property
	def abra(self):
		return vec4(self.w, self.z, self.x, self.w)
	@property
	def wzy(self):
		return vec3(self.w, self.z, self.y)
	@property
	def abg(self):
		return vec3(self.w, self.z, self.y)
	@property
	def wzyx(self):
		return vec4(self.w, self.z, self.y, self.x)
	@property
	def abgr(self):
		return vec4(self.w, self.z, self.y, self.x)
	@property
	def wzyy(self):
		return vec4(self.w, self.z, self.y, self.y)
	@property
	def abgg(self):
		return vec4(self.w, self.z, self.y, self.y)
	@property
	def wzyz(self):
		return vec4(self.w, self.z, self.y, self.z)
	@property
	def abgb(self):
		return vec4(self.w, self.z, self.y, self.z)
	@property
	def wzyw(self):
		return vec4(self.w, self.z, self.y, self.w)
	@property
	def abga(self):
		return vec4(self.w, self.z, self.y, self.w)
	@property
	def wzz(self):
		return vec3(self.w, self.z, self.z)
	@property
	def abb(self):
		return vec3(self.w, self.z, self.z)
	@property
	def wzzx(self):
		return vec4(self.w, self.z, self.z, self.x)
	@property
	def abbr(self):
		return vec4(self.w, self.z, self.z, self.x)
	@property
	def wzzy(self):
		return vec4(self.w, self.z, self.z, self.y)
	@property
	def abbg(self):
		return vec4(self.w, self.z, self.z, self.y)
	@property
	def wzzz(self):
		return vec4(self.w, self.z, self.z, self.z)
	@property
	def abbb(self):
		return vec4(self.w, self.z, self.z, self.z)
	@property
	def wzzw(self):
		return vec4(self.w, self.z, self.z, self.w)
	@property
	def abba(self):
		return vec4(self.w, self.z, self.z, self.w)
	@property
	def wzw(self):
		return vec3(self.w, self.z, self.w)
	@property
	def aba(self):
		return vec3(self.w, self.z, self.w)
	@property
	def wzwx(self):
		return vec4(self.w, self.z, self.w, self.x)
	@property
	def abar(self):
		return vec4(self.w, self.z, self.w, self.x)
	@property
	def wzwy(self):
		return vec4(self.w, self.z, self.w, self.y)
	@property
	def abag(self):
		return vec4(self.w, self.z, self.w, self.y)
	@property
	def wzwz(self):
		return vec4(self.w, self.z, self.w, self.z)
	@property
	def abab(self):
		return vec4(self.w, self.z, self.w, self.z)
	@property
	def wzww(self):
		return vec4(self.w, self.z, self.w, self.w)
	@property
	def abaa(self):
		return vec4(self.w, self.z, self.w, self.w)
	@property
	def ww(self):
		return vec2(self.w, self.w)
	@property
	def aa(self):
		return vec2(self.w, self.w)
	@property
	def wwx(self):
		return vec3(self.w, self.w, self.x)
	@property
	def aar(self):
		return vec3(self.w, self.w, self.x)
	@property
	def wwxx(self):
		return vec4(self.w, self.w, self.x, self.x)
	@property
	def aarr(self):
		return vec4(self.w, self.w, self.x, self.x)
	@property
	def wwxy(self):
		return vec4(self.w, self.w, self.x, self.y)
	@property
	def aarg(self):
		return vec4(self.w, self.w, self.x, self.y)
	@property
	def wwxz(self):
		return vec4(self.w, self.w, self.x, self.z)
	@property
	def aarb(self):
		return vec4(self.w, self.w, self.x, self.z)
	@property
	def wwxw(self):
		return vec4(self.w, self.w, self.x, self.w)
	@property
	def aara(self):
		return vec4(self.w, self.w, self.x, self.w)
	@property
	def wwy(self):
		return vec3(self.w, self.w, self.y)
	@property
	def aag(self):
		return vec3(self.w, self.w, self.y)
	@property
	def wwyx(self):
		return vec4(self.w, self.w, self.y, self.x)
	@property
	def aagr(self):
		return vec4(self.w, self.w, self.y, self.x)
	@property
	def wwyy(self):
		return vec4(self.w, self.w, self.y, self.y)
	@property
	def aagg(self):
		return vec4(self.w, self.w, self.y, self.y)
	@property
	def wwyz(self):
		return vec4(self.w, self.w, self.y, self.z)
	@property
	def aagb(self):
		return vec4(self.w, self.w, self.y, self.z)
	@property
	def wwyw(self):
		return vec4(self.w, self.w, self.y, self.w)
	@property
	def aaga(self):
		return vec4(self.w, self.w, self.y, self.w)
	@property
	def wwz(self):
		return vec3(self.w, self.w, self.z)
	@property
	def aab(self):
		return vec3(self.w, self.w, self.z)
	@property
	def wwzx(self):
		return vec4(self.w, self.w, self.z, self.x)
	@property
	def aabr(self):
		return vec4(self.w, self.w, self.z, self.x)
	@property
	def wwzy(self):
		return vec4(self.w, self.w, self.z, self.y)
	@property
	def aabg(self):
		return vec4(self.w, self.w, self.z, self.y)
	@property
	def wwzz(self):
		return vec4(self.w, self.w, self.z, self.z)
	@property
	def aabb(self):
		return vec4(self.w, self.w, self.z, self.z)
	@property
	def wwzw(self):
		return vec4(self.w, self.w, self.z, self.w)
	@property
	def aaba(self):
		return vec4(self.w, self.w, self.z, self.w)
	@property
	def www(self):
		return vec3(self.w, self.w, self.w)
	@property
	def aaa(self):
		return vec3(self.w, self.w, self.w)
	@property
	def wwwx(self):
		return vec4(self.w, self.w, self.w, self.x)
	@property
	def aaar(self):
		return vec4(self.w, self.w, self.w, self.x)
	@property
	def wwwy(self):
		return vec4(self.w, self.w, self.w, self.y)
	@property
	def aaag(self):
		return vec4(self.w, self.w, self.w, self.y)
	@property
	def wwwz(self):
		return vec4(self.w, self.w, self.w, self.z)
	@property
	def aaab(self):
		return vec4(self.w, self.w, self.w, self.z)
	@property
	def wwww(self):
		return vec4(self.w, self.w, self.w, self.w)
	@property
	def aaaa(self):
		return vec4(self.w, self.w, self.w, self.w)

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

