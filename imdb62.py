import features
import stanford_parser
import c_syntax_tree as st
from pos import pos_tags
import gc
from memory_profiler import profile
import shelve
import time
import queue
import threading
import itertools
import diskdict
import sys
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
	read_indices=[]
	with open(filename,'rt',encoding='utf8') as f:
		while True:
			line=f.readline()
			if not line:
				print("read: ",len(read_indices)," items")
				return
			index=int(line)
			document = documentbase.documents[index]
			if document.identifier == -4137911097833308936:
				print("found the searched document!")
				print("index: ",index)
				if indices is None or index in indices:
					print("write to cache!")
			num_trees = int(f.readline().strip())
			trees=[]
			for _ in range(num_trees):
				trees.append(stanford_parser.readTreeFromStream(f))
			if indices is None or index in indices:
				function.writeValueToCache(document, trees)
				read_indices.append(index)
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
				key=str(doc.identifier)
				if key in shl:
					function.writeValueToCache(doc,shl[key])
class asynchronousLoader:
	def __init__(self):
		self.orderIndex = 0
		self.orders = []
		self.requestQueue = queue.Queue()
		self.responseQueue = queue.Queue()
		self.callback = None
		self.thread = threading.Thread(target=self.run_thread)
		self.thread.setDaemon(True)
		self.thread.start()
	def setCallback(self,callback):
		self.callback = callback
	def run_thread(self):
		while True:
			orders = [self.requestQueue.get()]
			try:
				while True:
					orders.append(self.requestQueue.get_nowait())
			except queue.Empty:
				pass
			indices = list(itertools.chain(*[order[1] for order in orders]))
			readCache(indices=indices)
			if self.callback is not None:
				self.callback(indices)
			for order in orders:
				self.responseQueue.put(order[0])
	def put_order(self,indices):
		num = self.orderIndex
		self.orderIndex += 1
		self.requestQueue.put( (num,indices[:]) )
		return num
	def wait_order(self,order):
		if order in self.orders:
			self.orders.remove(order)
		else:
			while True:
				found = self.responseQueue.get()
				if found == order:
					return
				self.orders.append(found)
loadReviews()
loader = asynchronousLoader()
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
	return
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
	fun =functionCollection.getFunction(features.stanfordTreeDocumentFunction)
	indices=None
	if len(sys.argv) > 1:
		i = int(sys.argv[1])
		if 0 <= i and i < 7:
			indices = list(range(i*10000,(i+1)*10000))
	with diskdict.DiskDict('stanford-trees') as dd:
		fun.setCacheDict(dd)
		print("keys available: ",list(fun.cachedValues.keys())[:10])
		print(-4137911097833308936 in fun.cachedValues)
		readCache(indices=indices)
		print(-4137911097833308936 in fun.cachedValues)
