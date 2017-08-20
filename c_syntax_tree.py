from ctypes import CDLL, byref, c_bool, c_char, c_wchar, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, c_long, c_ulong, c_longlong, c_ulonglong, c_size_t, c_ssize_t, c_float, c_double, c_longdouble, c_char_p, c_wchar_p, c_void_p
import sys
import re
libsyntax_tree = CDLL(sys.path[0]+"/libsyntax_tree.so")
regex=re.compile("(.*\W)(\w+)\s*\((.*)\);\s")
ctypes_translation = {
'_Bool': c_bool,
'char': c_char,
'wchar_t': c_wchar,
'char': c_byte,
'unsigned char': c_ubyte,
'short': c_short,
'unsigned short': c_ushort,
'int': c_int,
'unsigned int': c_uint,
'long': c_long,
'unsigned long': c_ulong,
'__int64': c_longlong,
'long long': c_longlong,
'unsigned __int64': c_ulonglong,
'unsigned long long': c_ulonglong,
'size_t': c_size_t,
'ssize_t': c_ssize_t,
'Py_ssize_t': c_ssize_t,
'float': c_float,
'double': c_double,
'long double': c_longdouble,
'char *': c_char_p,
'wchar_t *': c_wchar_p,
'void *': c_void_p,
'void': None
}
c_typedefs = {
'st_label': c_int
}
def translateCtype(typ):
	if typ in ctypes_translation:
		return ctypes_translation[typ]
	if typ in c_typedefs:
		return c_typedefs[typ]
	if "*" in typ:
		return c_void_p
	raise Exception("Cannot translate type: "+repr(typ))
with open("syntax_tree_function_signatures","r",encoding="utf8") as f:
	for line in f:
		match=regex.fullmatch(line)
		if match:
			restype, name, args = match.groups()
			args=[translateCtype(a.strip()) for a in args.split(",")]
			args = list(filter(lambda x: x,args))
			restype = translateCtype(restype.strip())
			name=name.strip()
			fptr=getattr(libsyntax_tree,name)
			fptr.restype=restype
			fptr.argtypes=args
class syntax_tree:
	def __init__(self, label, children):	
		self.label = label
		self.parent = None
		self.children = children
		for ch in children:
			ch.parent=self
		self.handle = libsyntax_tree.st_prepareTree(label, len(children))
		for i,ch in enumerate(children):
			libsyntax_tree.st_setTreeChild(self.handle, i, ch.handle)
		self.extendable = False
	def free(self):
		#NB: After calling this function, NO OTHER MEMBER FUNCTION may be called.
		if libsyntax_tree is not None and self.handle is not None:
			libsyntax_tree.st_shallowFreeTree(self.handle)
			self.handle = None
	def __del__(self):
		self.free()
	def print(self):
		libsyntax_tree.st_printTree(self.handle,0)
	def setExtendable(self, isExtendable=True):
		self.extendable = isExtendable
		libsyntax_tree.st_setTreeExtendable(self.handle, isExtendable)
	def patternOccurs(self, pattern):
		return libsyntax_tree.st_canMatchPattern(pattern.handle, self.handle)
	def countNodes(self):
		return libsyntax_tree.st_countNodes(self.handle)
class document:
	def __init__(self, trees):
		self.trees=trees
		self.handle = libsyntax_tree.st_prepareDocument(len(trees))
		for i,tree in enumerate(trees):
			libsyntax_tree.st_documentSetTree(self.handle,i,tree.handle)
	def free(self):
		#NB: After calling this function, NO OTHER MEMBER FUNCTION may be called.
		if libsyntax_tree is not None and self.handle is not None:
			libsyntax_tree.st_shallowFreeDocument(self.handle)
			self.handle=None
	def __del__(self):
		self.free()
	def countOccuringTrees(self,pattern):
		return libsyntax_tree.st_occuringTrees(pattern.handle,self.handle)
	def frequency(self,pattern):
		return libsyntax_tree.st_frequency(pattern.handle,self.handle)
class documentclass:
	def __init__(self, documents,label=None):
		self.documents=documents
		self.label=label # label is just used internally
		self.handle = libsyntax_tree.st_prepareDocumentClass(len(documents))
		for i,doc in enumerate(documents):
			libsyntax_tree.st_setDocumentInClass(self.handle,i,doc.handle)
	def free(self):
		#NB: After calling this function, NO OTHER MEMBER FUNCTION may be called.
		if libsyntax_tree is not None and self.handle is not None:
			libsyntax_tree.st_freeDocumentClass(self.handle)
			self.handle=None
	def __del__(self):
		self.free()
class documentbase:
	def __init__(self, classes):
		self.classes=classes
		self.handle = libsyntax_tree.st_prepareDocumentBase(len(classes))
		for i,cl in enumerate(classes):
			libsyntax_tree.st_setClassInDocumentBase(self.handle,i,cl.handle)
		libsyntax_tree.st_completeDocumentBaseSetup(self.handle)
	def free(self):
		#NB: After calling this function, NO OTHER MEMBER FUNCTION may be called.
		if libsyntax_tree is not None and self.handle is not None:
			libsyntax_tree.st_freeDocumentBase(self.handle)
			self.handle=None
	def __del__(self):
		self.free()
	def support(self,pattern):
		return libsyntax_tree.st_support(self.handle,pattern.handle)
	def conditionalEntropy(self,pattern,n,estimate=True):
		if not estimate:
			return libsyntax_tree.st_conditionalEntropy(self.handle,pattern.handle,n,None)
		est=c_double()
		print("about to call...")
		result=libsyntax_tree.st_conditionalEntropy(self.handle,pattern.handle,n,byref(est))
		print("called.")
		return (result,est.value)

if __name__ == "__main__":
	testpattern = syntax_tree(42, [syntax_tree(42, [])])
	testpattern.print()
	singledoc = lambda x: document([syntax_tree(x,[])])
	base = documentbase([documentclass([singledoc(1), singledoc(2)]),documentclass([singledoc(3), singledoc(42)])])
	print(base.conditionalEntropy(testpattern,10,True))
