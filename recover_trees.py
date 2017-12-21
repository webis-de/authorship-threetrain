import c_syntax_tree
class recoveredTree:
	def __init__(self,label,extendable,parent):
		self.label=label
		self.extendable=extendable
		self.parent=parent
		self.children=[]
		if parent is not None:
			parent.children.append(self)
	def toSyntaxTree(self):
		res=c_syntax_tree.syntax_tree(self.label,[ch.toSyntaxTree() for ch in self.children])
		res.setExtendable(self.extendable)
		return res
def recover_trees(output):
	result=[]
	lines=output.split('\n')
	lastTree=None
	lastIndent=0
	for line in lines:
		print("lastIndent: %d, line: '%s'" % (lastIndent,line))
		if not line:
			continue
		indent=0
		while line[:2] == '  ':
			indent += 1
			line = line[2:]
		if indent > lastIndent+1:
			raise Exception("malformed tree found")
		if indent>0:
			for _ in range(indent,lastIndent+1):
				lastTree = lastTree.parent
		else:
			lastTree = None
		searchText='(extendable) '
		extendable=False
		if line[:len(searchText)] == searchText:
			extendable=True
			line=line[len(searchText):]
		lastTree = recoveredTree(int(line), extendable, lastTree)
		if indent==0:
			result.append(lastTree)
		lastIndent=indent
	return [r.toSyntaxTree() for r in result]
if __name__ == '__main__':
	for tree in recover_trees('''(extendable) 7
(extendable) 13
  29
  (extendable) 41
(extendable) 15
  13
    13
    (extendable) 13
      29
      38
(extendable) 26
(extendable) 50'''):
		tree.print()
