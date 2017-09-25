import features
import stanford_parser
import c_syntax_tree as st
from pos import pos_tags
import gc
from memory_profiler import profile
import shelve
import time
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
def writeCache3(filename='imdb62_syntaxcache3'):
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with shelve.open(filename,flag='c') as shl:
		for key,value in function.getCacheAsDict().items():
			shl[str(key)] = value
def readCache(filename='imdb62_syntaxcache',indices=None):
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
			if indices is None or index in indices:
				function.writeValueToCache(document, trees)
			else:
				for tr in trees:
					tr.recursiveFree()
def readCache2(filename='imdb62_syntaxcache2', checkIfNeeded=True,indices=None):
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with open(filename,'rt',encoding='utf8') as f:
		documents = None if indices is None else [documentbase.documents[i] for i in indices]
		function.readCacheFromStream(f,documents=documents)
def readCache3(filename='imdb62_syntaxcache3',indices=None):
	function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	with shelve.open(filename,'r') as shl:
		if indices is None:
			function.setCacheAsDict(dict(shl))
		else:
			documents = [documentbase.documents[i] for i in indices]
			for doc in documents:
				if doc.identifier in shl:
					function.writeValueToCache(doc,shl[str(doc.identifier)])
loadReviews()
print("loaded reviews")
def initialize(filename='imdb62_syntaxcache',indices=None):
	try:
		readCache(filename=filename,indices=indices)
		#print("read from cache: ", [i for i,rev in enumerate(reviews) if rev.stanfordTrees is not None])
		function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
		print("read from cache: ", [i for i,doc in enumerate(documentbase.documents) if function.valueIsCached(doc)])
	except Exception as e:
		print("Failed to read cache")
		print(e)
	try:
		readCache2(indices=indices)
		function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
		print("read from cache 2: ", [i for i,doc in enumerate(documentbase.documents) if function.valueIsCached(doc)])
	except Exception as e:
		print("Failed to read cache 2")
		print(e)
	try:
		readCache3(indices=indices)
		function = functionCollection.getFunction(features.stanfordTreeDocumentFunction)
		print("read from cache 3: ", [i for i,doc in enumerate(documentbase.documents) if function.valueIsCached(doc)])
	except Exception as e:
		print("Failed to read cache 3")
		print(e)

@profile
def doMiningTest(base):
	st.showCMemoryStatistics()
	print("%d trees exist." % st.num_trees)
	result=base.mineDiscriminativePatterns(len(pos_tags),0,10,2,num_processes=3)
	print("got %d discriminative patterns." % len(result))
	del result
	gc.collect()
	if len(gc.garbage)> 0:
		print("garbage!")
		sys.exit(42)
	st.showCMemoryStatistics()
	print("%d trees exist." % st.num_trees)

if __name__ == '__main__':
	sum_tokens = 0
	wordlen = [len(doc.text.split(' ')) for doc in documentbase.documents]
	#print(wordlen)
	average = sum(wordlen)/float(len(wordlen))
	variance = sum( (w-average)**2 for w in wordlen ) / len(wordlen)
	print("average token count: %f" % average)
	print("standard deviation: %f" % (variance**0.5))
	indices=list(range(40))+list(range(1000,1040))+list(range(2000,2040))
	#initialize(indices=indices)
	time1 = time.perf_counter()
	readCache(indices=[])
	time2 = time.perf_counter()
	readCache3()
	time3 = time.perf_counter()
	#writeCache3()
	print("obtained trees (%f / %f)." % (time2-time1, time3-time2))
	trainingbase = documentbase.subbase(indices)
	base = trainingbase.stDocumentbase
	print("got documentbase.")
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
