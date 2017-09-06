import features
import stanford_parser
import c_syntax_tree as st
from pos import pos_tags
documentbase=None
functionCollection=None
cacheUpdateNeeded=False
def loadReviews():
	global documentbase,functionCollection
	reviews=[]
	with open("imdb62.txt") as f:
		for line in f:
			line = line.split('\t')
			reviews.append(features.document(line[5], line[1]))
	documentbase = features.documentbase(reviews)
	functionCollection = features.documentFunctionCollection()
	documentbase.functionCollection = functionCollection
def computeStanfordTrees(indices=None):
	global cacheUpdateNeeded
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	docs = documentbase.documents if indices is None else [documentbase.documents[i] for i in indices]
	indices = [d for d in docs if not function.valueIsCached(d)]
	if not indices:
		return
	cacheUpdateNeeded=True
	'''
	texts = [reviews[i].content for i in indices]
	results = stanford_parser.parseText(texts)
	if len(results) != len(indices):
		raise Exception("Got %d results for %d texts." % (len(results), len(texts)))
	for i,trees in zip(indices,results):
		print("call setStanfordTrees for #%d" % i)
		reviews[i].setStanfordTrees(trees)
	'''
	print("%u docs" % len(docs))
	function.getValuev(docs)
def writeCache(filename='imdb62_syntaxcache',checkIfNeeded=True):
	global cacheUpdateNeeded
	if checkIfNeeded and not cacheUpdateNeeded:
		return
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with open(filename,'wt',encoding='utf8') as f:
		for i,document in enumerate(documentbase.documents):
			if function.valueIsCached(document):
				print("write cache for review #%d" % i)
				f.write(str(i)+"\n")
				trees = function.getValue(document)
				f.write(str(len(trees))+"\n")
				for tree in trees:
					tree.writeStream(f)
	cacheUpdateNeeded=False
def writeCache2(filename='imdb62_syntaxcache2', checkIfNeeded=True):
	global cacheUpdateNeeded
	if checkIfNeeded and not cacheUpdateNeeded:
		return
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with open(filename,'wt',encoding='utf8') as f:
		function.writeCacheToStream(f)
def readCache(filename='imdb62_syntaxcache'):
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with open(filename,'rt',encoding='utf8') as f:
		while True:
			line=f.readline()
			if not line:
				return
			index=int(line)
			document = documentbase.documents[index]
			num_trees = int(f.readline().strip())
			trees=[]
			for _ in range(num_trees):
				trees.append(stanford_parser.readTreeFromStream(f))
			function.writeValueToCache(document, trees)
def readCache2(filename='imdb62_syntaxcache2', checkIfNeeded=True):
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with open(filename,'rt',encoding='utf8') as f:
		function.readCacheFromStream(f)
loadReviews()
try:
	readCache()
	#print("read from cache: ", [i for i,rev in enumerate(reviews) if rev.stanfordTrees is not None])
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	print("read from cache: ", [i for i,doc in enumerate(documentbase.documents) if function.valueIsCached(doc)])
except Exception as e:
	print("Failed to read cache")
	print(e)
try:
	readCache2()
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	print("read from cache: ", [i for i,doc in enumerate(documentbase.documents) if function.valueIsCached(doc)])
except Exception as e:
	print("Failed to read cache 2")
	print(e)
if __name__ == '__main__':
	indices=list(range(40))+list(range(1000,1040))+list(range(2000,2040))
	computeStanfordTrees(indices)
	print("write cache...")
	writeCache()
	cacheUpdateNeeded=True
	writeCache2()
	print("cache written.")
	trainingbase = documentbase.subbase(indices)
	base = trainingbase.stDocumentbase
	testpattern = st.syntax_tree(16,[]) #particle
	testpattern.setExtendable(True)
	print(base.support(testpattern))
	print(base.conditionalEntropy(testpattern,10))
	stanfordTreeFunction = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	doc=functionCollection.getValue(documentbase.documents[0],features.stDocumentDocumentFunction)
	print(doc.frequency(testpattern))
	for i,tree in enumerate(doc.trees):
		if tree.patternOccurs(testpattern):
			#tree.print()
			stree = stanfordTreeFunction.getValue(documentbase.documents[0])[i]
			#print(" ".join(x.data for x in stree.leaves))
	result=base.mineDiscriminativePatterns(len(pos_tags),0,10,2)
	print("got %d discriminative patterns." % len(result))
	for pattern in result:
		print("we get this pattern with conditional entropy %f:" % base.conditionalEntropy(pattern, 10))
		pattern.nicePrint()
		pattern.print()
