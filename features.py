import c_syntax_tree as st
import syntax_tree
import stanford_parser
from werkzeug import cached_property
#import pickle
from collections import Counter
import pos
import regression
import config
import concurrent.futures
import easyparallel
import heapq
import diskdict
import hashlib
import pickle

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
document_identifier_hashfun = hashlib.sha256
class document:
	def __init__(self, text, author=None):
		self.text = text
		self.author=author
	@cached_property
	def identifier(self):
		return document_identifier_hashfun(self.text.encode('utf-8')).digest()
class documentFunction:
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
			self.cachedValues.moveToMemory([document.identifier for document in documents])
	def removeFromMemory(self,document):
		if isinstance(self.cachedValues,diskdict.DiskDict):
			self.cachedValues.removeFromMemory(document.identifier)
	def forgetDocument(self,document):
		if document.identifier in self.cachedValues:
			if isinstance(self.cachedValues,diskdict.DiskDict):
				self.cachedValues.removeFromMemory(document.identifier)
			else:
				del self.cachedValues[document.identifier]
class derivedDocumentFunction(documentFunction):
	#does not only look at the text but also at the outcome of another document function
	def __init__(self,predecessorFunctionClass,*kwds):
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
		print("asked functionCollection to forget document ",document.identifier)
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
	def moveToMemory(self,docs):
		for func in self.instances.values():
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
class feature(documentFunction):
	def vectorLength(self):
		pass
class combinedFeature(feature):
	#given features ft1, ..., ftn; this one maps a document d to (ft1(d), ..., ftn(d))
	def __init__(self, subfeatures,functionCollection=None):
		self.subfeatures = subfeatures
		if functionCollection is not None:
			self.functionCollection = functionCollection
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
class view:
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
	def createClassifier(self,trainingDocbase):
		return documentClassifier(trainingDocbase,self.getFeature(trainingDocbase))

# now to the concrete stuff
class stanfordTreeDocumentFunction(documentFunction):
	# to each document, return a list of stanford trees, encoding the tokenization, pos-tagging and syntactic structure
	def mappingv(self,documents):
		return easyparallel.callWorkerFunction(stanford_parser.parseText,[d.text for d in documents])
class tokensDocumentFunction(derivedDocumentFunction):
	#for each document, returns a list of tokens
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		result = []
		for tree in trees:
			result += [l.data for l in tree.leaves]
		return result
class tokensCounterDocumentFunction(derivedDocumentFunction):
	#normalized
	def __init__(self):
		super().__init__(tokensDocumentFunction)
	def deriveValue(self,document,tokens):
		return normalizedCounter(tokens)
class numTokensDocumentFunction(derivedDocumentFunction):
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
	def __init__(self,n):
		self.n=n
		super().__init__()
	def mapping(self,document):
		t=document.text
		return [t[i:i+self.n] for i in range(len(t)-self.n)]
class characterNGramCounterDocumentFunction(derivedDocumentFunction):
	def __init__(self,n):
		super().__init__(characterNGramDocumentFunction,n)
	def deriveValue(self,document,tokens):
		return normalizedCounter(tokens)
class numCharactersDocumentFunction(documentFunction):
	def mapping(self,document):
		return len(document.text)
class posDocumentFunction(derivedDocumentFunction):
	#for each document, returns a list of pos tokens
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		result = []
		for tree in trees:
			result += [l.label for l in tree.leaves]
		return result
class posCounterDocumentFunction(derivedDocumentFunction):
	def __init__(self):
		super().__init__(posDocumentFunction)
	def deriveValue(self,document,pos):
		return normalizedCounter(pos)
class posNGramDocumentFunction(derivedDocumentFunction):
	def __init__(self,n):
		self.n=n
		super().__init__(posDocumentFunction)
	def deriveValue(self,document,pos):
		return [tuple(pos[i:i+self.n]) for i in range(len(pos)-self.n+1)]
class posNGramCounterDocumentFunction(derivedDocumentFunction):
	def __init__(self,n):
		self.n=n
		super().__init__(posNGramDocumentFunction,n)
	def deriveValue(self,document,pos):
		return normalizedCounter(pos)
class stDocumentDocumentFunction(derivedDocumentFunction):
	def __init__(self):
		super().__init__(stanfordTreeDocumentFunction)
	def deriveValue(self,document,trees):
		return st.document([syntax_tree.stanfordTreeToStTree(tree) for tree in trees])
class wordUnigramFeature(derivedFeature):
	def __init__(self,words):
		self.words = words
		derivedDocumentFunction.__init__(self,tokensCounterDocumentFunction)
	def vectorLength(self):
		return len(self.words)
	def deriveValue(self,document,tokensCounter):
		return [tokensCounter[tok] for tok in self.words]
class characterNGramFeature(derivedFeature):
	def __init__(self,n,ngrams):
		self.n = n
		self.ngrams = ngrams
		derivedDocumentFunction.__init__(self,characterNGramCounterDocumentFunction,n)
	def vectorLength(self):
		return len(self.ngrams)
	def deriveValue(self,document,ngramsCounter):
		return [ngramsCounter[ngram] for ngram in self.ngrams]
class posNGramFeature(derivedFeature):
	def __init__(self,n,ngrams):
		self.n = n
		self.ngrams = ngrams
		derivedDocumentFunction.__init__(self,posNGramCounterDocumentFunction,n)
	def vectorLength(self):
		return len(self.ngrams)
	def deriveValue(self,document,ngramsCounter):
		return [ngramsCounter[ngram] for ngram in self.ngrams]
class syntaxTreeFrequencyFeature(derivedFeature):
	def __init__(self,trees):
		self.trees=trees
		derivedDocumentFunction.__init__(self,stDocumentDocumentFunction)
	def vectorLength(self):
		return len(self.trees)
	def deriveValue(self,_,document):
		return [document.frequency(tree) for tree in self.trees]
class characterView(view):
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
				features.append(self.getFunction(characterNGramFeature,n,tuple(values)))
			else:
				values = Counter()
				for doc in docbase.documents:
					values += function.getValue(doc)
				selection = heapq.nlargest(limit,values,lambda ngram: values[ngram])
				features.append(self.getFunction(characterNGramFeature,n,tuple(selection)))
		return combinedFeature(features,self.functionCollection if hasattr(self,'functionCollection') else None)
class lexicalView(view):
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
	def __init__(self, ns, supportLowerBound, n, k, remine_trees_until=0):
		self.ns = ns
		self.supportLowerBound = supportLowerBound
		self.n = n
		self.k = k
		self.remine_trees_until = None if remine_trees_until == 0 else remine_trees_until
	def getFeature(self,docbase):
		features=[]
		for n in self.ns:
			function = self.getFunction(posNGramCounterDocumentFunction,n)
			limit = config.featurelimit_max_pos_ngrams[n-1]
			if limit is None:
				values = set()
				for doc in docbase.documents:
					values = values.union(set(function.getValue(doc)))
				features.append(self.getFunction(posNGramFeature,n,tuple(values)))
			else:
				values = Counter()
				for doc in docbase.documents:
					values += function.getValue(doc)
				selection = heapq.nlargest(limit,values,lambda ngram: values[ngram])
				features.append(self.getFunction(posNGramFeature,n,tuple(selection)))
		base = docbase.stDocumentbase
		if self.remine_trees_until is 0:
			treeFeature = self.treeFeature
		else:
			treeFeature = self.getFunction(syntaxTreeFrequencyFeature, \
				tuple(base.mineDiscriminativePatterns(len(pos.pos_tags), self.supportLowerBound, self.n, self.k,\
												num_processes=config.num_threads_mining)))
			if self.remine_trees_until is not None:
				self.remine_trees_until -= 1
				if self.remine_trees_until == 0:
					self.treeFeature = treeFeature
		features.append(treeFeature)
		return combinedFeature(features,self.functionCollection if hasattr(self,'functionCollection') else None)
		#return keeFeature
class documentClassifier(documentFunction):
	def __init__(self,trainingDocbase,feature):
		self.docbase = trainingDocbase
		self.feature = feature
		self.authors = [doc.author for doc in trainingDocbase.documents]
		self.vectors = self.feature.getValuev(trainingDocbase.documents)
		print("start classifying with %d vectors and %d features" % (len(self.vectors),feature.vectorLength()))
		self.regression = easyparallel.callWorkerFunction(regression.multiclassLogit,self.authors, self.vectors)
		print("returned from classifying with %d vectors and %d features" % (len(self.vectors),feature.vectorLength()))
		self.cachedProbabilities = {}
		if hasattr(feature,'functionCollection'):
			self.functionCollection = feature.functionCollection
		super().__init__()
	def mappingv(self,documents):
		#return self.regression.predict(self.feature.getValuev(documents))
		print("start predicting with %d features and %d documents" % (self.feature.vectorLength(),len(documents)))
		vectors = self.feature.getValuev(documents)
		print("got %d features for %d documents" % (self.feature.vectorLength(),len(documents)))
		result = easyparallel.callWorkerFunction(self.regression.getProbabilities,vectors)
		print("got probabilities %d features and %d documents" % (self.feature.vectorLength(),len(documents)))
		return result
		'''
	def getProbabilities(self,documents):
		return self.regression.getProbabilities(self.feature.getValuev(documents))
		'''
	def predict(self,documents):
		probs = self.getValuev(documents)
		return [regression.countermax(p) for p in probs]
if __name__== '__main__':
	coll = documentFunctionCollection()
	base = documentbase([document('This is your father','papa'), document('This is your mother.', 'mama')])
	base.functionCollection = coll
	view1 = characterView([1,2,3])
	view1.functionCollection = coll
	feature1 = view1.getFeature(base)
	print("feature 1:")
	print(feature1.getValuev(base.documents))
	classifier1 = documentClassifier(base, feature1)
	print(classifier1.getValuev(base.documents))
	view2 = lexicalView()
	view2.functionCollection = coll
	feature2 = view2.getFeature(base)
	print("feature 2:")
	print(feature2.getValuev(base.documents))
	classifier2 = documentClassifier(base, feature2)
	print(classifier2.getValuev(base.documents))
	view3 = syntacticView([1,2,3],0,10,2)
	view3.functionCollection = coll
	feature3 = view3.getFeature(base)
	print("feature 3:")
	print(feature3.getValuev(base.documents))
	classifier3 = documentClassifier(base, feature3)
	print(classifier3.getValuev(base.documents))
