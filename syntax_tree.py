import c_syntax_tree as st
import stanford_parser
from pos import pos_tags
def stanfordTreeToStTree(tree):
	label=pos_tags.index(tree.label.upper())
	if label == -1:
		raise Exception("unknown label: "+tree.label)
	children = [stanfordTreeToStTree(ch) for ch in tree.children]
	return st.syntax_tree(label,children)
