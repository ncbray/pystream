template <class T> T * pybind_convertptr(PyObject *o)
{
	return reinterpret_cast<T *>(o);
}

/* Macro for returning Py_NotImplemented from a function */
#define Py_RETURN_NOTIMPLEMENTED return Py_INCREF(Py_NotImplemented), Py_NotImplemented