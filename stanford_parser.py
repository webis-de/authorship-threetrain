import subprocess
import os.path
import tempfile
import sys
from werkzeug import cached_property
import pickle
class stanfordTree:
	def __init__(self, label, parent=None, position=None):
		self.label=label
		self.data=None
		self.parent=parent
		self.rangeStart=None
		self.rangeEnd=None
		self.children = []
		if parent is not None:
			parent.children.append(self)
		if position is not None:
			self.rangeStart=position
			self.rangeEnd=position+1
	def updateRange(self):
		if self.rangeStart is not None and self.rangeEnd is not None:
			return
		self.rangeStart = min(ch.rangeStart for ch in self.children)
		self.rangeEnd = max(ch.rangeEnd for ch in self.children)
	def setPosition(self, pos):
		self.rangeStart=pos
		self.rangeEnd=pos+1
	def __str__(self):
		if len(self.children)==0:
			return '['+(self.data or 'None')+'/'+self.label+']'
		else:
			return '['+self.label+' '+' '.join(ch.__str__() for ch in self.children)+']'
	def writeStream(self, stream):
		stream.write(self.label+"\n"+(self.data or '')+"\n"+str(len(self.children))+"\n")
		for ch in self.children:
			ch.writeStream(stream)
	@cached_property
	def leaves(self):
		if len(self.children) == 0:
			return [self]
		else:
			res=[]
			for ch in self.children:
				res += ch.leaves
			return res
	def recursiveFree(self):
		#after calling this function, no other member function of this tree or any its descendants may be called
		if not hasattr(self,'parent'):
			return
		del self.parent,self.data,self.label,self.rangeStart,self.rangeEnd
		if self.children is not None:
			for ch in self.children:
				ch.recursiveFree()
			del self.children
def readTreeFromStream(stream,parent=None):
	result=stanfordTree(stream.readline().strip(), parent)
	result.data = stream.readline().strip() or None
	num_children = int(stream.readline().strip())
	for _ in range(num_children):
		readTreeFromStream(stream,result)
	return result
def parseText(texts):
	if texts == []:
		return []
	#NB the stanford parser is VERY BROKEN for it cannot, in combination with the crucial virt-sandbox, properly read data from stdin
	#UNLESS I, personally, by my own hands, type them into the terminal.
	handles=[]
	for t in texts:
		handle=tempfile.NamedTemporaryFile()
		handle.write(bytearray(t, encoding='utf8'))
		handle.flush()
		handles.append(handle)
	indexfile=tempfile.NamedTemporaryFile()
	indexfile.write(bytearray("\n".join(handle.name for handle in handles)+"\n",encoding='utf8'))
	indexfile.flush()
	command='''/usr/bin/virt-sandbox -- /usr/bin/xargs -a %s -n 10 /usr/bin/java -Xmx3g -mx3g -cp %s/stanford-parser-full-2017-06-09/*: edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat penn -outputFormatOptions includePunctuationDependencies -maxLength 250 edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz'''
	#NB this is not partable if sys.path[0] or indexfile.name contains a space.
	#print(command % (indexfile.name,sys.path[0]))
	mypath=os.path.dirname(os.path.abspath(__file__))
	#print(command % (indexfile.name,mypath))
	#from os import system
	#system(command % (indexfile.name,sys.path[0]))
	proc=subprocess.run((command % (indexfile.name,mypath)).split(' '), stdout=subprocess.PIPE, universal_newlines=True, stderr=subprocess.STDOUT)
	#command='''/usr/bin/virt-sandbox -- cat'''
	#proc=subprocess.run((command).split(' '), input="\n".join(handle.name for handle in handles), \
	#		stdout=subprocess.PIPE, universal_newlines=True)
	tokens = None
	pos=None
	trees=None
	results=[]
	position=0
	output=proc.stdout
	print(output)
	nextParsing = output.find('Parsing file:')
	while True:
		position = output.find('(ROOT', position)
		if position == -1:
			break
		if trees is None or position > nextParsing and nextParsing != -1:
			#tokens=[]
			#pos=[]
			trees=[]
			results.append(trees)
			nextParsing = output.find('Parsing file:', position)
			#print('nextParsing looks like this: '+output[nextParsing:nextParsing+100])
		tree = stanfordTree('ROOT')
		trees.append(tree)
		position += 5
		treepos=0
		while tree is not None:
			while output[position].isspace():
				position += 1
			if output[position] == '(':
				position += 1
				nextpos = output.find(' ', position)
				tree = stanfordTree(output[position:nextpos].strip(), parent=tree)
				position=nextpos
			else:
				#then there must follow data and a closed parenthesis
				newpos = output.find(')', position)
				dat=output[position:newpos].strip()
				if dat:
					tree.setPosition(treepos)
					treepos+=1
					#tokens.append(dat)
					#pos.append(tree.label)
					tree.data=dat
				else:
					tree.updateRange()
				position=newpos+1
				tree=tree.parent
	return results
if __name__=="__main__":
	results=parseText(['Is this a hash?! Oh, #2 is one. For $60 dollars, 60$ can be given! Would they "quote \'inside\'"? Or; if anything goes: Then this (or this?).'])
	dump = pickle.dumps(results)
	print(repr(results))
	print(dump)
	print(repr(pickle.loads(dump)))
