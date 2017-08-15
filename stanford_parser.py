import subprocess
import os.path
import tempfile
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
def parseText(texts):
	#NB the stanford parser is VERY BROKEN for it cannot, in combination with the crucial virt-sandbox, properly read data from stdin
	#UNLESS I, personally, by my own hands, type them into the terminal.
	handles=[]
	for t in texts:
		handle=tempfile.NamedTemporaryFile()
		handle.write(bytearray(t, encoding='utf8'))
		handle.flush()
		handles.append(handle)
	command='''/usr/bin/virt-sandbox -- /usr/bin/java -mx150m -cp /home/ego/stylometry-paraphrasing/prog/stanford-parser-full-2017-06-09/*: edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat penn -outputFormatOptions includePunctuationDependencies edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz'''
	proc=subprocess.run(command.split(' ')+[handle.name for handle in handles], stdout=subprocess.PIPE, universal_newlines=True)
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
		if position > nextParsing and nextParsing != -1:
			tokens=[]
			pos=[]
			trees=[]
			results.append( (tokens,pos,trees))
			nextParsing = output.find('Parsing file:', position)
			print('nextParsing looks like this: '+output[nextParsing:nextParsing+100])
		tree = stanfordTree('ROOT')
		trees.append(tree)
		position += 5
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
					tree.setPosition(len(tokens))
					tokens.append(dat)
					pos.append(tree.label)
					tree.data=dat
				else:
					tree.updateRange()
				position=newpos+1
				tree=tree.parent
	return results
#print(parseText(['Is this a hash?! Oh, #2 is one. For $60 dollars, 60$ can be given! Would they "quote \'inside\'"? Or; if anything goes: Then this (or this?).']))
