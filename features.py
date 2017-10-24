import c_syntax_tree as st
import syntax_tree
import stanford_parser
from werkzeug import cached_property
from collections import Counter
import pos
import config
import easyparallel
import heapq
import diskdict
import hashlib
import pickle
import os.path

#we agree on the following terminology:
#	- a document is a natural language text
#	for examples, consult a bookshelf
#	- a document function is a (mathematical) mapping whose domain is the set of all documents
#	examples include POS tags, occuring ngrams
#	- a feature is a document function whose codomain is R^d for some natural number d (R denotes the set of real numbers)
#	examples include word counts, frequencies of k-ee-subtries
#	- a document database (or short documentbase) is a set of documents with an author assigned to each document
#	such a documentbase is the ground truth for the training
#	- a view is a mapping that assigns to each documentbase a feature
#	examples include: the word frequencies of all occuring word unigrams,
#	or the frequencies of all discriminative k-ee-subtrees
#	- a classifier is a document function which assigns, to each document, an author
#	our aim is to find a good classifier.

def normalizedCounter(*kwds):
	ctr = Counter(*kwds)
	if not config.normalize_features:
		return ctr
	s = sum(ctr.values())
	factor = 1.0/sum(ctr.values())
	return Counter({key: value*factor for (key,value) in ctr.items()})
def countermax(ctr):
	m=max(ctr.values())
	for key,value in ctr.items():
		if value == m:
			return key

document_identifier_hashfun = hashlib.sha256
class document:
	__slots__=['text','author','identifier']
	def __init__(self, text, author=None):
		self.text = text
		self.author=author
		self.identifier = document_identifier_hashfun(text.encode('utf-8')).digest()
		'''
	@cached_property
	def identifier(self):
		return document_identifier_hashfun(self.text.encode('utf-8')).digest()
		'''
class documentFunction:
	__slots__=['cachedValues','functionCollection']
	def __init__(self):
		#print("created document function",type(self),hasattr(self,'functionCollection'))
		if not hasattr(self,'functionCollection'):
			raise Exception("no function collection?")
		self.cachedValues={}
	def setCacheDict(self,dictionary):
		self.cachedValues=dictionary
	def closeCache(self):
		if isinstance(self.cachedValues,diskdict.DiskDict):
			self.cachedValues.close()
	'''def __del__(self):
		print("delete document function",type(self))'''
	def getValue(self,document):
		key=document.identifier
		if key in self.cachedValues:
			return self.cachedValues[key]
		result=self.mapping(document)
		self.cachedValues[key]=result
		return result
	def getValuev(self,documents):
		#vectorized function
		keys = [d.identifier for d in documents]
		available = [key in self.cachedValues for key in keys]
		missingIndices = [i for i in range(len(documents)) if not available[i]]
		missingValues = self.mappingv([documents[i] for i in missingIndices]) if missingIndices else []
		if len(missingIndices) != len(missingValues):
			raise Exception("Called mappingv with %u documents, got %u values." % (len(documents), len(missingValues)))
		missingIndex=0
		result = []
		for avail,key,doc in zip(available,keys,documents):
			if avail:
				result.append(self.cachedValues[key])
			else:
				value = missingValues[missingIndex]
				missingIndex += 1
				result.append(value)
				self.cachedValues[key]=value
		return result
	# one of mapping or mappingv must be implemented.
	def mapping(self,document):
		# applies to a single text
		return self.mappingv([document])[0]
	def mappingv(self,documents):
		# vectorized function
		return [self.mapping(d) for d in documents]
	def writeValueToCache(self,document,value):
		self.cachedValues[document.identifier]=value
	def valueIsCached(self, document):
		return document.identifier in self.cachedValues
	def clearCache(self):
		if isinstance(self.cachedValues,diskdict.DiskDict):
			self.cachedValues.close()
		self.cachedValues = {}
	def getCacheAsDict(self):
		return self.cachedValues.copy()
	def setCacheAsDict(self,dictionary):
		self.cachedValues.update(dictionary)
	def moveToMemory(self,documents):
		if isinstance(self.cachedValues,diskdict.DiskDict):
			#print("move to memory. Cached: ",len(self.cachedValues),": ",repr(list(self.cachedValues.keys())[:20]))
			self.cachedValues.moveToMemory([document.identifier for document in documents if document.identifier in self.cachedValues])
			unmovable = sum(1 for document in documents if document.identifier not in self.cachedValues)
			if unmovable > 0:
				raise Exception("Cannot move %d documents to memory" % unmovable)
	def removeFromMemory(self,document):
		if isinstance(self.cachedValues,diskdict.DiskDict):
			self.cachedValues.removeFromMemory(document.identifier)
	def forgetDocument(self,document):
		if document.identifier in self.cachedValues:
			if isinstance(self.cachedValues,diskdict.DiskDict):
				self.cachedValues.removeFromMemory(document.identifier)
			else:
				del self.cachedValues[document.identifier]
	def getFunction(self,functionClass,*args):
		if hasattr(self,'functionCollection'):
			return self.functionCollection.getFunction(functionClass,*args)
		else:
			return functionClass(*args)
class derivedDocumentFunction(documentFunction):
	#does not only look at the text but also at the outcome of another document function
	__slots__=['predecessorFunctionClass','predecessorFunction']
	def __init__(self,predecessorFunctionClass,*kwds):
		self.predecessorFunctionClass = predecessorFunctionClass
		if not hasattr(self,'functionCollection'):
			self.predecessorFunction = predecessorFunctionClass(*kwds)
		else:
			self.predecessorFunction = self.functionCollection.getFunction(predecessorFunctionClass, *kwds)
		super().__init__()
	def deriveValue(self,document,predecessorValue):
		#to be implemented
		pass
	def mappingv(self,documents):
		values = self.predecessorFunction.getValuev(documents)
		return [self.deriveValue(document,value) for (document,value) in zip(documents,values)]
	def mapping(self,document):
		return self.deriveValue(document,self.predecessorFunction.getValue(document))
class documentFunctionCollection:
	#a set of document functions that may be derived from each other
	__slots__=['instances']
	def __init__(self):
		self.instances={}
		print("CREATED documentFunctionCollection",type(self))
	def __del__(self):
		print("DELETED documentFunctionCollection")
	def getFunction(self,functionClass,*kwds):
		key = (functionClass,kwds)
		if key not in self.instances:
			res = functionClass.__new__(functionClass,*kwds)
			res.functionCollection=self
			res.__init__(*kwds)
			self.instances[key] = res
			return res
		return self.instances[key]
	def getValue(self,document,functionClass,*kwds):
		return self.getFunction(functionClass, *kwds).getValue(document)
	def getValues(self,documents,functionClass,*kwds):
		return self.getFunction(functionClass, *kwds).getValuev(documents)
	def free(self):
		for fun in self.instances.values():
			fun.clearCache()
			fun.functionCollection = None
		self.instances = {}
	def forgetDocument(self,document,functionClasses=None):
		#print("asked functionCollection to forget document ",document.identifier)
		if functionClasses is None:
			for func in self.instances.values():
				func.forgetDocument(document)
		else:
			for functionClass in functionClasses:
				key = (functionClass,())
				if key in self.instances:
					self.instances[key].forgetDocument(document)
				else:
					print("Asked to forget document ",document.identifier," for class ",functionClass,", but have no instance for this.")
	def moveToMemory(self,docs,functionClasses=None):
		#print("move to memory with these instances: ",self.instances.keys())
		#print("functionClasses: ",functionClasses)
		for cls,func in self.instances.items():
			if functionClasses is None or cls[0] in functionClasses:
				func.moveToMemory(docs)
	def showMemoryStatistics(self):
		for key,value in self.instances.items():
			print("key: ",key)
			print("type(value): ",type(value))
			if isinstance(value.cachedValues,diskdict.DiskDict):
				print(key[0]," (",*key[1],") has a DiskDict as cache.")
			elif isinstance(value.cachedValues,dict):
				print(key[0]," (",*key[1],") has a pickled cache size of ",len(pickle.dumps(value.cachedValues)),\
										" and ",len(value.cachedValues)," cached values.")
			else:
				print("value: ",value)
				print("value.cachedValues: ",value.cachedValues)
				raise Exception("Unexpected type for cachedValues.")
	def getFeatureIdentifier(self,feature):
		for key,feat in self.instances.items():
			if feature is feat:
				return (key[0],*key[1])
		raise Exception("Cannot find feature "+repr(feature))
class feature(documentFunction):
	__slots__=[]
	def vectorLength(self):
		pass
class combinedFeature(feature):
	#given features ft1, ..., ftn; this one maps a document d to (ft1(d), ..., ftn(d))
	__slots__=['subfeatures']
	def __init__(self, *argss):
		print("create combined feature with function collection ", self.functionCollection)
		self.subfeatures=[self.getFunction(*args) for args in argss]
		super().__init__()
	def vectorLength(self):
		return sum(ft.vectorLength() for ft in self.subfeatures)
	def mapping(self, document):
		result = []
		for ft in self.subfeatures:
			result+= ft.getValue(document)
		return result
	def mappingv(self, documents):
		result = [[] for _ in documents]
		for ft in self.subfeatures:
			vals=ft.getValuev(documents)
			for v,r in zip(vals,result):
				r += v
		return result
class derivedFeature(feature,derivedDocumentFunction):
	__slots__=[]
	pass
class documentbase:
	def __init__(self, documents):
		self.documents = documents
		'''print("created documentbase")
	def __del__(self):
		print("deleted documentbase")'''
	def getFunction(self,functionClass,*kwds):
		if not hasattr(self,'functionCollection'):
			return functionClass(*kwds)
		else:
			return self.functionCollection.getFunction(functionClass,*kwds)
	@cached_property
	def byAuthor(self):
		result = {}
		for d in self.documents:
			if d.author in result:
				result[d.author].append(d)
			else:
				result[d.author]=[d]
		return result
	@cached_property
	def authors(self):
		return list(set(self.byAuthor))
	@cached_property
	def stDocumentbase(self):
		function = self.getFunction(stDocumentDocumentFunction)
		return st.documentbase([st.documentclass(function.getValuev(documents),label=author) for (author,documents) in self.byAuthor.items()])
	def subbase(self, indices):
		result=documentbase([self.documents[i] for i in indices])
		if hasattr(self,'functionCollection'):
			result.functionCollection = self.functionCollection
		return result
	def extend(self, extraDocuments):
		result = documentbase(self.documents + extraDocuments)
		if hasattr(self,'functionCollection'):
			result.functionCollection = self.functionCollection
		return result
	@cached_property
	def byIdentifier(self):
		result = {}
		for d in self.documents:
			if d.identifier in result:
				result[d.identifier].append(d)
			else:
				result[d.identifier] = [d]
		return result
	def strippedDuplicates(self,warn=True):
		#returns a documentbase with duplicates removed. Two documents are considered duplicate iff identifier and author coincide.
		result = []
		for docs in self.byIdentifier.values():
			known_authors = []
			for doc in docs:
				if doc.author not in known_authors:
					known_authors.append(doc.author)
					result.append(doc)
			if len(known_authors) > 1 and warn:
				print("WARNING: Found same text by %d authors" % len(known_authors))
				print("authors: ",", ".join(str(a) for a in known_authors))
				print("text:")
				print(docs[0].text)
		result = documentbase(result)
		if hasattr(self,'functionCollection'):
			result.functionCollection = self.functionCollection
		return result
	def hasSameDocument(self,doc):
		#returns true if a document with same author and identifier occurs
		if not doc.identifier in self.byIdentifier:
			return False
		return doc.author in (d.author for d in self.byIdentifier[doc.identifier])
class view:
	__slots__=['functionCollection']
	def getFeature(self,docbase):
		pass
	def getFunction(self,functionClass,*kwds):
		if not hasattr(self,'functionCollection'):
			return functionClass(*kwds)
		else:
			return self.functionCollection.getFunction(functionClass,*kwds)
	def getValue(self,document,functionClass,*kwds):
		return self.getFunction(functionClass,*kwds).getValue(document)
	def getValues(self,documents,functionClass,*kwds):
		return self.getFunction(functionClass,*kwds).getValuev(documents)
	def createClassifier(self,trainingDocbase,ml):
		return documentClassifier(trainingDocbase,self.getFeature(trainingDocbase),ml)

# now to the concrete stuff
class stanfordTreeDocumentFunction(documentFunction):
	__slots__=[]
	# to each document, return a list of stanford trees, encoding the tokenization, pos-tagging and syntactic structure
	def mappingv(self,documents):
		return easyparallel.callWorkerFunction(stanford_parser.parseText,[d.text for d in documents])
class tokensDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	#for each document, returns a list of tokens
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		result = []
		for tree in trees:
			result += [l.data for l in tree.leaves]
		return result
class tokensCounterDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	#normalized
	def __init__(self):
		super().__init__(tokensDocumentFunction)
	def deriveValue(self,document,tokens):
		return normalizedCounter(tokens)
class numTokensDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	def __init__(self):
		super().__init__(tokensDocumentFunction)
	def deriveValue(self,document,tokens):
		return len(tokens)
'''
class characterNGramDocumentFunction(derivedDocumentFunction):
	def __init__(self,n):
		self.n=n
		super().__init__(tokensDocumentFunction)
	def deriveValue(self,document,tokens):
		#print("Called to get character n grams for text %s and tokens %s" % (repr(document.text),repr(tokens)))
		result = []
		for tok in tokens:
			result += [tok[i:i+self.n] for i in range(len(tok)-self.n+1)]
		return result
'''
class characterNGramDocumentFunction(documentFunction):
	__slots__=['n']
	def __init__(self,n):
		self.n=n
		super().__init__()
	def mapping(self,document):
		t=document.text
		return [t[i:i+self.n] for i in range(len(t)-self.n)]
class characterNGramCounterDocumentFunction(derivedDocumentFunction):
	__slots__=['n']
	def __init__(self,n):
		super().__init__(characterNGramDocumentFunction,n)
	def deriveValue(self,document,tokens):
		return normalizedCounter(tokens)
class numCharactersDocumentFunction(documentFunction):
	__slots__=[]
	def mapping(self,document):
		return len(document.text)
class posDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	#for each document, returns a list of pos tokens
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		result = []
		for tree in trees:
			result += [l.label for l in tree.leaves]
		return result
class posCounterDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	def __init__(self):
		super().__init__(posDocumentFunction)
	def deriveValue(self,document,pos):
		return normalizedCounter(pos)
class posNGramDocumentFunction(derivedDocumentFunction):
	__slots__=['n']
	def __init__(self,n):
		self.n=n
		super().__init__(posDocumentFunction)
	def deriveValue(self,document,pos):
		return [tuple(pos[i:i+self.n]) for i in range(len(pos)-self.n+1)]
class posNGramCounterDocumentFunction(derivedDocumentFunction):
	__slots__=['n']
	def __init__(self,n):
		self.n=n
		super().__init__(posNGramDocumentFunction,n)
	def deriveValue(self,document,pos):
		return normalizedCounter(pos)
class stDocumentDocumentFunction(derivedDocumentFunction):
	__slots__=[]
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		return st.document([syntax_tree.stanfordTreeToStTree(tree) for tree in trees])
class wordUnigramFeature(derivedFeature):
	__slots__=['words']
	def __init__(self,words):
		self.words = words
		derivedDocumentFunction.__init__(self,tokensCounterDocumentFunction)
	def vectorLength(self):
		return len(self.words)
	def deriveValue(self,document,tokensCounter):
		return [tokensCounter[tok] for tok in self.words]
class characterNGramFeature(derivedFeature):
	__slots__=['n','ngrams']
	def __init__(self,n,ngrams):
		self.n = n
		self.ngrams = ngrams
		derivedDocumentFunction.__init__(self,characterNGramCounterDocumentFunction,n)
	def vectorLength(self):
		return len(self.ngrams)
	def deriveValue(self,document,ngramsCounter):
		return [ngramsCounter[ngram] for ngram in self.ngrams]
class posNGramFeature(derivedFeature):
	__slots__=['n','ngrams']
	def __init__(self,n,ngrams):
		self.n = n
		self.ngrams = ngrams
		derivedDocumentFunction.__init__(self,posNGramCounterDocumentFunction,n)
	def vectorLength(self):
		return len(self.ngrams)
	def deriveValue(self,document,ngramsCounter):
		return [ngramsCounter[ngram] for ngram in self.ngrams]
class syntaxTreeFrequencyFeature(derivedFeature):
	__slots__=['trees']
	def __init__(self,trees):
		self.trees=trees
		derivedDocumentFunction.__init__(self,stDocumentDocumentFunction)
	def vectorLength(self):
		return len(self.trees)
	def deriveValue(self,_,document):
		return [document.frequency(tree) for tree in self.trees]
class characterView(view):
	__slots__=['ns']
	def __init__(self,ns):
		self.ns = ns
	def getFeature(self, docbase):
		features = []
		for n in self.ns:
			limit = config.featurelimit_max_character_ngrams[n-1]
			function = self.getFunction(characterNGramCounterDocumentFunction,n)
			if limit is None:
				values=set()
				for doc in docbase.documents:
					values = values.union(set(function.getValue(doc)))
				features.append((characterNGramFeature,n,tuple(values)))
			else:
				values = Counter()
				for doc in docbase.documents:
					values += function.getValue(doc)
				selection = heapq.nlargest(limit,values,lambda ngram: values[ngram])
				features.append((characterNGramFeature,n,tuple(selection)))
		#return combinedFeature(features,self.functionCollection if hasattr(self,'functionCollection') else None)
		return self.getFunction(combinedFeature,*features)
class lexicalView(view):
	__slots__=[]
	def getFeature(self, docbase):
		function = self.getFunction(tokensCounterDocumentFunction)
		limit = config.featurelimit_max_word_unigrams
		if limit is None:
			values=set()
			for doc in docbase.documents:
				values = values.union(set(function.getValue(doc)))
			return self.getFunction(wordUnigramFeature,tuple(values))
		else:
			values=Counter()
			for doc in docbase.documents:
				values += function.getValue(doc)
			selection = heapq.nlargest(limit,values,lambda unigram: values[unigram])
			return self.getFunction(wordUnigramFeature,tuple(selection))
class syntacticView(view):
	__slots__=['ns','supportLowerBound','n','k','remine_trees_until','minedTreesCacheFile','treeFeature']
	def __init__(self, ns, supportLowerBound, n, k, remine_trees_until=0, minedTreesCacheFile = None):
#if minedTreesCacheFile exists, read the trees from minedTreesCacheFile. Otherwise:
#if remine_trees_until == 0, remine trees everytime. Otherwise, remine `remine_trees_until` times.
#After each mining, the result gets saved to `minedTreesCacheFile`.
		self.ns = ns
		self.supportLowerBound = supportLowerBound
		self.n = n
		self.k = k
		self.remine_trees_until = None if remine_trees_until == 0 else remine_trees_until
		self.minedTreesCacheFile = minedTreesCacheFile
		self.treeFeature = None
	def getFeature(self,docbase):
		features=[]
		for n in self.ns:
			function = self.getFunction(posNGramCounterDocumentFunction,n)
			limit = config.featurelimit_max_pos_ngrams[n-1]
			if limit is None:
				values = set()
				for doc in docbase.documents:
					values = values.union(set(function.getValue(doc)))
				features.append((posNGramFeature,n,tuple(values)))
			else:
				values = Counter()
				for doc in docbase.documents:
					values += function.getValue(doc)
				selection = heapq.nlargest(limit,values,lambda ngram: values[ngram])
				features.append((posNGramFeature,n,tuple(selection)))
		base = docbase.stDocumentbase
		if self.treeFeature is None and self.minedTreesCacheFile is not None and os.path.exists(self.minedTreesCacheFile):
			with open(self.minedTreesCacheFile,'rb') as f:
				self.treeFeature = pickle.load(f)
				self.remine_trees_until = 0
		if self.remine_trees_until is 0:
			treeFeature = self.treeFeature
		else:
			treeFeature = (syntaxTreeFrequencyFeature, \
				tuple(base.mineDiscriminativePatterns(len(pos.pos_tags), self.supportLowerBound, self.n, self.k,\
												num_processes=config.num_threads_mining)))
			if self.remine_trees_until is not None:
				self.remine_trees_until -= 1
				if self.remine_trees_until == 0:
					self.treeFeature = treeFeature
			if self.minedTreesCacheFile is not None:
				with open(self.minedTreesCacheFile,'wb') as f:
					pickle.dump(trees,f)
		features.append(treeFeature)
		#return combinedFeature(features,self.functionCollection if hasattr(self,'functionCollection') else None)
		return self.getFunction(combinedFeature,*features)
		#return treeFeature
	def setTreeFeature(self,feature):
		self.treeFeature = self.functionCollection.getFeatureIdentifier(feature)
		self.remine_trees_until=0
	def readTreeFeatureFromClassifier(self,classifier):
		self.setTreeFeature(classifier.feature)
class kimView(view):
	__slots__= ['supportLowerBound', 'n', 'k']
	def __init__(self,supportLowerBound=0, n=10, k=2):
		self.supportLowerBound = supportLowerBound
		self.n=n
		self.k=k
	def getFeature(self,docbase):
		return self.getFunction(syntaxTreeFrequencyFeature, tuple(docbase.stDocumentbase.mineDiscriminativePatterns(len(pos.pos_tags), \
			self.supportLowerBound, self.n, self.k, num_processes=config.num_threads_mining)))
class mlModel:
	# a model is a mapping from an abstract feature space F and a set of labels L to the unit interval [0,1].
	# they are created from by a machine learning algorithm. This class should be inherited from
	__slots__=[]
	def getProbabilities(self,vectors):
		raise NotImplementedError
		#vectors is a list of elements of F.
		#should return a dict or counter of the form {l1: p1, ..., ln:pn} where L={l1,...,ln} are the different labels
		#and p1,...,pn in [0,1]. A higher value for pi means that label li is more likely.
	def getPrediction(self,vectors):
		# gets a list of elements of V and returns a list of same lengths of elements in L.
		# returns an element with maximal probability
		return countermax(self.getProbabilities(vectors))
	# derived classes should further make sure they are picklable (i.e. implement __getstate__ and __setstate__)
class learningMachine:
	# a learning maching takes a list of tuples (v,l) where v is an element of an abstract feature space F and
	# l is a label. It returns an instance of mlModel with the same label set and feature space.
	# instances of this class should be hashable.
	__slots__=[]
	def getModel(self,labels,vectors):
		pass
class argumentPassingLearningMachine(learningMachine):
	#takes a class derived from mlModel. For each call of getModel, it passes the arguments to the __init__-function of the given class.
	__slots__=['modelClass']
	def __init__(self,modelClass):
		self.modelClass = modelClass
	def getModel(self,labels,vectors):
		return self.modelClass(labels,vectors)
class easyparallelArgumentPassingLearningMachine(learningMachine):
	#takes a class derived from mlModel. For each call of getModel, it passes the arguments to the __init__-function of the given class.
	#the init-function MAY be called in another process (using multiprocessing), so it should not modify any global state.
	__slots__=['modelClass']
	def __init__(self,modelClass):
		self.modelClass = modelClass
	def getModel(self,labels,vectors):
		return easyparallel.callWorkerFunction(self.modelClass,labels,vectors)
class documentClassifier(documentFunction):
	__slots__=['feature','model']
	def __init__(self,trainingDocbase,feature,ml):
		docbase = trainingDocbase
		self.feature = feature
		authors = [doc.author for doc in trainingDocbase.documents]
		vectors = feature.getValuev(trainingDocbase.documents)
		print("start classifying with %d vectors and %d features" % (len(vectors),feature.vectorLength()))
		#self.regression = easyparallel.callWorkerFunction(regression.multiclassLogit,authors,vectors)
		self.model = ml.getModel(authors,vectors)
		print("returned from classifying with %d vectors and %d features" % (len(vectors),feature.vectorLength()))
		if hasattr(feature,'functionCollection'):
			self.functionCollection = feature.functionCollection
		super().__init__()
	def mappingv(self,documents):
		#return self.regression.predict(self.feature.getValuev(documents))
		print("start predicting with %d features and %d documents" % (self.feature.vectorLength(),len(documents)))
		vectors = self.feature.getValuev(documents)
		print("got %d features for %d documents" % (self.feature.vectorLength(),len(documents)))
		#result = easyparallel.callWorkerFunction(self.regression.getProbabilities,vectors)
		result = self.model.getProbabilities(vectors)
		print("got probabilities %d features and %d documents" % (self.feature.vectorLength(),len(documents)))
		return result
		'''
	def getProbabilities(self,documents):
		return self.regression.getProbabilities(self.feature.getValuev(documents))
		'''
	def predict(self,documents):
		probs = self.getValuev(documents)
		return [countermax(p) for p in probs]
	def dumps(self):
		return pickle.dumps( (self.functionCollection.getFeatureIdentifier(self.feature), self.model))
	def loads(self,state,functionCollection):
		self.functionCollection = functionCollection
		state = pickle.loads(state)
		self.feature = functionCollection.getFunction(*state[0])
		self.model = state[1]
		super().__init__()
def loadClassifier(state,functionCollection):
	result = documentClassifier.__new__(documentClassifier)
	result.loads(state,functionCollection)
	return result
if __name__== '__main__':
	import regression
	coll = documentFunctionCollection()
	base = documentbase([document('This is your father','papa'), document('This is your mother.', 'mama')])
	base.functionCollection = coll
	view1 = characterView([1,2,3])
	view1.functionCollection = coll
	feature1 = view1.getFeature(base)
	print("feature 1:")
	print(feature1.getValuev(base.documents))
	print("use this learning maching: ",regression.multiclassLogit)
	classifier1 = documentClassifier(base, feature1, regression.multiclassLogit)
	print(classifier1.getValuev(base.documents))
	view2 = lexicalView()
	view2.functionCollection = coll
	feature2 = view2.getFeature(base)
	print("feature 2:")
	print(feature2.getValuev(base.documents))
	classifier2 = documentClassifier(base, feature2, regression.multiclassLogit)
	print(classifier2.getValuev(base.documents))
	view3 = syntacticView([1,2,3],0,10,2)
	view3.functionCollection = coll
	feature3 = view3.getFeature(base)
	print("feature 3:")
	print(feature3.getValuev(base.documents))
	classifier3 = documentClassifier(base, feature3, regression.multiclassLogit)
	print(classifier3.getValuev(base.documents))
	dumped = classifier3.dumps()
	print("clasifier 3 got dumped to "+repr(dumped))
	print(loadClassifier(dumped,coll).getValuev(base.documents))
