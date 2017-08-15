from ctypes import CDLL, c_bool, c_int, c_uint, c_void_p
import sys
libsyntax_tree = CDLL(sys.path[0]+"/libsyntax_tree.so")
libsyntax_tree.st_freeTree.argtypes = [c_void_p]
libsyntax_tree.st_shallowFreeTree.argtypes = [c_void_p]
#libsyntax_tree.st_createTree.argtypes = [c_int, c_uint, ]
libsyntax_tree.st_prepareTree.argtypes = [c_int, c_uint]
libsyntax_tree.st_prepareTree.restype = c_void_p
libsyntax_tree.st_setTreeChild.argtypes = [c_void_p, c_uint, c_void_p]
libsyntax_tree.st_setTreeExtendable.argtypes = [c_void_p, c_bool]
libsyntax_tree.st_printTree.argtypes = [c_void_p, c_int]
libsyntax_tree.st_canMatchPattern.argtypes = [c_void_p, c_void_p]
libsyntax_tree.st_canMatchPattern.restype = c_bool
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
if __name__ == "__main__":
	leaf1 = syntax_tree(1, [])
	leaf2 = syntax_tree(2, [])
	branch1 = syntax_tree(1, [leaf1,leaf2])
	leaf3=syntax_tree(3,[])
	root = syntax_tree(42, [branch1, leaf3])
	testpattern = syntax_tree(42, [syntax_tree(42, [])])
	root.print()
	testpattern.print()
	print(root.patternOccurs(testpattern))
