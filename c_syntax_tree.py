from ctypes import CDLL, byref, c_bool, c_char, c_wchar, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, c_long, c_ulong, c_longlong, c_ulonglong, c_size_t, c_ssize_t, c_float, c_double, c_longdouble, c_char_p, c_wchar_p, c_void_p
import os
import re
import pos
import time
from functools import reduce
libsyntax_tree = CDLL(os.path.dirname(os.path.abspath(__file__))+"/libsyntax_tree.so")
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
libsyntax_tree.st_storeTree.argtypes = [c_void_p,c_void_p]
libsyntax_tree.st_readTree.argtypes = [c_void_p]
class syntax_tree:
	__slots__ = ['handle']
	def __init__(self, label, children, data=None):	
		#self.label = label
		#self.children = children
		self.handle = libsyntax_tree.st_prepareTree(label, len(children))
		#self.data=data
		for i,ch in enumerate(children):
			libsyntax_tree.st_setTreeChild(self.handle, i, ch.handle)
			ch.handle = None
		#self.extendable = False
	def free(self):
		#NB: After calling this function, NO OTHER MEMBER FUNCTION may be called.
		if libsyntax_tree is not None and self.handle is not None:
			libsyntax_tree.st_freeTree(self.handle)
			self.handle = None
		elif libsyntax_tree is None:
			raise Exception("Connection to libsyntax_tree lost.")
	def __del__(self):
		self.free()
	def print(self):
		libsyntax_tree.st_printTree(self.handle,0)
	def setExtendable(self, isExtendable=True):
		#self.extendable = isExtendable
		libsyntax_tree.st_setTreeExtendable(self.handle, isExtendable)
	def patternOccurs(self, pattern):
		return libsyntax_tree.st_canMatchPattern(pattern.handle, self.handle)
	def countNodes(self):
		return libsyntax_tree.st_countNodes(self.handle)

	def __getstate__(self):
		array_size = libsyntax_tree.st_getSizeForTreeStorage(self.handle)
		#print("array size: ",array_size)
		array_type = c_byte * array_size
		array      = array_type(0)
		#print("array, initially: ",array)
		#print("handle: ",tree.handle)
		libsyntax_tree.st_storeTree(self.handle, array)
		#print("array, now: ",array)
		return bytes(array)
	def __setstate__(self,bts):
		self.handle = libsyntax_tree.st_readTree(bts)
'''
def copySyntaxTreeFromHandle(handle):
	result=syntax_tree(libsyntax_tree.st_treeGetLabel(handle), [copySyntaxTreeFromHandle(libsyntax_tree.st_treeGetChild(handle, index)) for\
		index in range(libsyntax_tree.st_treeNumOfChildren(handle))])
	result.setExtendable(libsyntax_tree.st_treeGetExtendable(handle))
	return result
'''
def copySyntaxTreeFromHandle(handle):
	result = syntax_tree.__new__(syntax_tree)
	result.handle = libsyntax_tree.st_deepCopyTree(handle)
	return result
def copyPatternListFromHandle(handle):
	result = [None]*libsyntax_tree.st_listGetLength(handle)
	entry = libsyntax_tree.st_listGetFirstEntry(handle)
	for i in range(len(result)):
		result[i] = copySyntaxTreeFromHandle(libsyntax_tree.st_listedGetPattern(entry))
		entry = libsyntax_tree.st_listedGetNext(entry)
	return result
class document:
	__slots__ = ['trees','handle']
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
	def __getstate__(self):
		return self.trees
	def __setstate__(self,trees):
		self.__init__(trees)
class documentclass:
	__slots__ = ['documents','label','handle']
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
	__slots__ = ['classes','handle']
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
	def conditionalEntropy(self,pattern,n):
		return libsyntax_tree.st_conditionalEntropy(self.handle,pattern.handle,n,None)
	def mineDiscriminativePatterns(self,numLabels,supportLowerBound,n,k,num_processes=1):
		print("create mining state.")
		state=libsyntax_tree.st_createMiningState(self.handle,numLabels,supportLowerBound,n,k)
		print("now go for a mine.")
		#lst = libsyntax_tree.st_mine(state)
		libsyntax_tree.st_populateMiningState(state)
		if num_processes > 1:
			numIterations = 8000
			while libsyntax_tree.st_numCandidates(state) != 0:
				iteration_start = time.perf_counter()
				print("numIterations: %f, remaining %u candidates"%(numIterations,libsyntax_tree.st_numCandidates(state)))
				if numIterations > 2**20:
					numIterations = 2**20
				elif numIterations < 2:
					numIterations = 2
				split = libsyntax_tree.st_splitupState(state,num_processes)
				libsyntax_tree.st_freeMiningState(state)
				startTime = time.perf_counter()
				libsyntax_tree.st_doParallelMiningIterations(split, int(numIterations))
				neededTime = time.perf_counter()-startTime
				state = libsyntax_tree.st_mergeStates(split)
				iterationTime = time.perf_counter()-iteration_start
				print("Needed time: %f. Iteration time: %f" % (neededTime,iterationTime))
				if neededTime != 0:
					numIterations *= (4*(iterationTime-neededTime)/neededTime)**0.7
					#spend 80% of the time mining, 20% syncing.
			'''
			libsyntax_tree.st_doMiningIterations(state,-1)
					'''
		else:
			libsyntax_tree.st_doMiningIterations(state,-1)
		lst = libsyntax_tree.st_getDiscriminativePatterns(state)
		print("mining returned %d trees." % libsyntax_tree.st_listGetLength(lst))
		result = copyPatternListFromHandle(lst)
		libsyntax_tree.st_shallowFreeList(lst)
		libsyntax_tree.st_freeMiningState(state)
		return result
def showCMemoryStatistics():
	libsyntax_tree.showMemoryInformation()
libsyntax_tree.st_testFillArray.argtypes=[c_uint, c_void_p]
libsyntax_tree.st_testPrintArray.argtypes=[c_uint, c_void_p]
def cArrayTest():
	array_size=1024**3
	ct = c_byte * array_size
	myarray = ct(0)
	libsyntax_tree.st_testFillArray(array_size,myarray)
	print("value at position 42: ",myarray[42])
	libsyntax_tree.st_testPrintArray(array_size,myarray)
	libsyntax_tree.st_testPrintArray(2,b'11')
	print("values: ",bytes(myarray)[:42])
	del myarray
if __name__ == "__main__":
	cArrayTest()
	tree = syntax_tree(42,[syntax_tree(1,[]),syntax_tree(2,[syntax_tree(3,[])])])
	print("tree:")
	tree.print()
	bts = tree.__getstate__()
	print("bytes: ",bts)
	tree.__setstate__(bts)
	print("tree, again:")
	tree.print()
