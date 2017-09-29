import config
if config.debug_memory:
	import tracemalloc
	tracemalloc.start(1024)
	import objgraph
	import sys
import imdb62
import features
import random
import gc
import c_syntax_tree
import regression
from collections import Counter
from functools import reduce
import heapq
import easyparallel
import diskdict
from memory_profiler import profile
def showMemoryStatistics():
	for stat in tracemalloc.take_snapshot().statistics('traceback')[:5]:
		print(stat)
		prevLine=None
		for line in stat.traceback.format():
			if line is prevLine:
				continue
			print(line)
			prevLine = line
	tracked = [(x,sys.getsizeof(x)) for x in gc.get_objects()]
	most_expensive = heapq.nlargest(10,tracked,lambda t: t[1])
	print("most expensive: ")
	for t in most_expensive:
		print("type: %s, size: %d, repr[:1024]: %s" % (type(t[0]),t[1],repr(t[0])[:1024]))
def getSuccessRate(testBase,classifier):
	return len([None for (pred,doc) in zip(classifier.predict(testBase.documents),testBase.documents) if pred == doc.author])
def getAccumulatedPrediction(testBase,*classifiers):
	probs = [cl.getValuev(testBase.documents) for cl in classifiers]
	acc = [reduce(lambda c1,c2: c1+c2, (p[i] for p in probs)) for i in range(len(testBase.documents))]
	return [regression.countermax(c) for c in acc]
def getAccumulatedSuccessRate(testBase,*classifiers):
	return len([None for (pred,doc) in zip(getAccumulatedPrediction(testBase,*classifiers),testBase.documents) if pred == doc.author])
def getTrueLabels(documents):
	return [d.author for d in documents]
def getBalancedSubbase(documentbase,classifier=None,predicted_probabilities=None):
	#gets a subbase of documentbase where each author occurs with the same frequency, choosen maximally
	#if an additional classifier is given, tries to choose the documents most 'typically' for this author and classifier.
	ctr = Counter({auth: len(docs) for (auth,docs) in documentbase.byAuthor.items()})
	confidence=None
	if classifier is not None:
		predicted_probabilities = predicted_probabilities if predicted_probabilities is not None else classifier.getValuev(documentbase.documents)
		confidence = {doc.identifier: prob for (doc,prob) in zip(documentbase.documents, predicted_probabilities)}
	num_docs = min(ctr.values())
	result_docs = []
	for auth in documentbase.authors:
		docs = documentbase.byAuthor[auth]
		if classifier is None:
			result_docs += random.sample(docs,num_docs)
		else:
			result_docs += heapq.nlargest(num_docs,docs,lambda doc: confidence[doc.identifier][doc.author])
	result = features.documentbase(result_docs)
	if hasattr(documentbase,'functionCollection'):
		result.functionCollection = documentbase.functionCollection
	return result
def trainAndPredict(view,documentbase,test_documents):
	classifier = view.createClassifier(documentbase)
	return classifier,classifier.predict(test_documents)

#features that are derived from stanfordTreeDocumentFunction
neededDocumentFunctions = [features.tokensDocumentFunction,features.posDocumentFunction,features.stDocumentDocumentFunction]
#@profile
def threeTrain(view1,view2,view3,trainingBase, unlabelledBase, testBase, num_iterations, num_unlabelled,results_stream=None):
	labelled1 = trainingBase
	labelled2 = trainingBase
	labelled3 = trainingBase
	balanced1 = labelled1
	balanced2 = labelled2
	balanced3 = labelled3
	extra_true1=0
	extra_true2=0
	extra_true3=0
	extra_false1=0
	extra_false2=0
	extra_false3=0
	parallelGroup = easyparallel.ParallelismGroup(3)
	functionCollection = trainingBase.functionCollection if hasattr(trainingBase,'functionCollection') else None
	@profile
	def prepareDocuments(docs):
		chunksize=2000
		if functionCollection is not None:
			for i in range(0,len(docs),chunksize):
				chunk = docs[i:i+chunksize]
				#print("move %d documents to memory..." % len(chunk))
				#for doc in docs:
				#	functionCollection.moveToMemory(doc)
				functionCollection.moveToMemory(chunk)
				#print("compute needed document functions...")
				for func in neededDocumentFunctions:
					functionCollection.getValues(chunk,func)
				#print("forget unnecessary document functions...")
				stanford_trees = functionCollection.getValues(chunk,features.stanfordTreeDocumentFunction)
				for trees in stanford_trees:
					for tree in trees:
						'''
						objgraph.show_backrefs(tree)
						raise Exception("This is what you wanted to see, right?")
						'''
						tree.recursiveFree()
				del stanford_trees
				for doc in chunk:
					functionCollection.forgetDocument(doc,[features.stanfordTreeDocumentFunction])
				#print("prepared %d documents." % len(chunk))
				gc.collect()
				if config.debug_memory:
					print("garbage: ",len(gc.garbage))
					print("15 most common types:")
					objgraph.show_most_common_types(limit=15)
					c_syntax_tree.showCMemoryStatistics()
					showMemoryStatistics()
					functionCollection.showMemoryStatistics()
					functionCollection.getFunction(features.stanfordTreeDocumentFunction).cachedValues.showMemoryStatistics()
					print("leaking: ",len(objgraph.get_leaking_objects()))
	prepareDocuments(trainingBase.documents)
	prepareDocuments(testBase.documents)
	for iteration in range(num_iterations):
		gc.collect()
		choiceIndices = random.sample(range(len(unlabelledBase.documents)),num_unlabelled)
		choice = [unlabelledBase.documents[i] for i in choiceIndices]
		prepareDocuments(choice)
		print("got choice")
		'''
		classifier1 = view1.createClassifier(balanced1)
		classified1 = classifier1.predict(choice)
		classifier2 = view2.createClassifier(balanced2)
		classified2 = classifier2.predict(choice)
		classifier3 = view3.createClassifier(balanced3)
		classified3 = classifier3.predict(choice)
		'''
		parallelGroup.add_branch(trainAndPredict,view1,balanced1,choice)
		parallelGroup.add_branch(trainAndPredict,view2,balanced2,choice)
		parallelGroup.add_branch(trainAndPredict,view3,balanced3,choice)
		print("waiting for classification and prediction...")
		parallelGroup_results = parallelGroup.get_results()
		print("got results!")
		classifier1,classified1 = parallelGroup_results[0]
		classifier2,classified2 = parallelGroup_results[1]
		classifier3,classified3 = parallelGroup_results[2]
		resline="%d,%d,%d,%d,%d,%d" % (iteration,len(testBase.documents),getSuccessRate(testBase,classifier1),\
			getSuccessRate(testBase,classifier2),getSuccessRate(testBase,classifier3),\
			getAccumulatedSuccessRate(testBase,classifier1,classifier2,classifier3))
		print("RESULT:",resline)
		if results_stream != None:
			results_stream.write(resline+"\n")
			results_stream.flush()
		extraLabelled1=[]
		extraLabelled2=[]
		extraLabelled3=[]
		for l1,l2,l3,doc in zip(classified1,classified2,classified3,choice):
			print("classified: %s, %s, %s. true: %s"%(l1,l2,l3,doc.author))
			#print(p1,p2,p3)
			discard=True
			if l1 == l2:
				discard=False
				if config.do_fake:
					extraLabelled3.append(doc)
				else:
					extraLabelled3.append(features.document(doc.text,l1))
				if doc.author == l1:
					extra_true3+=1
				else:
					extra_false3+=1
			if l1 == l3:
				discard=False
				if config.do_fake:
					extraLabelled2.append(doc)
				else:
					extraLabelled2.append(features.document(doc.text,l1))
				if doc.author == l1:
					extra_true2+=1
				else:
					extra_false2+=1
			if l2 == l3:
				discard=False
				if config.do_fake:
					extraLabelled1.append(doc)
				else:
					extraLabelled1.append(features.document(doc.text,l2))
				extraLabelled1.append(doc)
				if doc.author == l2:
					extra_true1+=1
				else:
					extra_false1+=1
			if discard and functionCollection is not None:
				functionCollection.forgetDocument(doc)
		labelled1 = labelled1.extend(extraLabelled1)
		labelled2 = labelled2.extend(extraLabelled2)
		labelled3 = labelled3.extend(extraLabelled3)
		print("labelled 1: ",Counter([d.author for d in labelled1.documents]))
		print("labelled 2: ",Counter([d.author for d in labelled2.documents]))
		print("labelled 3: ",Counter([d.author for d in labelled3.documents]))
		unlabelledBase = unlabelledBase.subbase(list(set(range(len(unlabelledBase.documents))) - set(choiceIndices)))
		if config.undersample:
			'''
			balanced1 = getBalancedSubbase(labelled1,classifier1)
			balanced2 = getBalancedSubbase(labelled2,classifier2)
			balanced3 = getBalancedSubbase(labelled3,classifier3)
			'''
			parallelGroup.add_branch(getBalancedSubbase,labelled1,classifier1)
			parallelGroup.add_branch(getBalancedSubbase,labelled2,classifier2)
			parallelGroup.add_branch(getBalancedSubbase,labelled3,classifier3)
			balanced1,balanced2,balanced3 = parallelGroup.get_results()
		else:
			balanced1,balanced2,balanced3 = labelled1,labelled2,labelled3
		classifier1.clearCache()
		classifier2.clearCache()
		classifier3.clearCache()
		classifier1=None
		classifier2=None
		classifier3=None
		print("added documents (true/false): %d/%d   %d/%d   %d/%d" % (extra_true1,extra_false1,extra_true2,extra_false2,extra_true3,extra_false3))
	classifier1 = view1.createClassifier(balanced1)
	classifier2 = view2.createClassifier(balanced2)
	classifier3 = view3.createClassifier(balanced3)
	pred = getAccumulatedPrediction(testBase,classifier1,classifier2,classifier3)
	correct = len([None for (pred,doc) in zip(pred,testBase.documents) if pred == doc.author])
	resline="%d,%d,%d,%d,%d,%d" % (num_iterations,len(testBase.documents),getSuccessRate(testBase,classifier1),\
		getSuccessRate(testBase,classifier2),getSuccessRate(testBase,classifier3),correct)
	print("RESULTS: ",resline)
	if results_stream != None:
		results_stream.write(resline+"\n")
		results_stream.flush()
	classifier1.clearCache()
	classifier2.clearCache()
	classifier3.clearCache()
	return pred
#@profile
def mainfunc():
	print("begin threeview.mainfunc")
	trainIndices = []
	unlabelledIndices = []
	testIndices = []
	author_indices = random.sample(range(3 if config.use_small_cache else 62),config.num_authors)
	for i in author_indices:
		range_max = ((i+1)*1000) if not config.use_small_cache else (i*1000+10)
		avail = set(range(i*1000,range_max))
		tr = random.sample(avail,config.num_training)
		avail = avail-set(tr)
		unl = random.sample(avail,config.num_unlabelled)
		avail = avail-set(unl)
		tst = random.sample(avail,config.num_test)
		avail = avail-set(tst)
		trainIndices += list(tr)
		unlabelledIndices += list(unl)
		testIndices += list(tst)
	indices = trainIndices + unlabelledIndices + testIndices
	if config.use_small_cache:
		print("use small cache.")
		imdb62.initialize(indices=indices,filename='small_cache')
	else:
		#imdb62.initialize(indices=indices)
		pass
	#imdb62.writeCache(filename='small_cache',checkIfNeeded=False)
	#imdb62.computeStanfordTrees(indices)
	#imdb62.readCache(filename='small_cache')
	print("trees loaded.")
	trainBase = imdb62.documentbase.subbase(trainIndices)
	testBase = imdb62.documentbase.subbase(testIndices)
	unlabelledBase = imdb62.documentbase.subbase(unlabelledIndices)
	view1 = features.characterView([3])
	view1.functionCollection = imdb62.functionCollection
	view2 = features.lexicalView()
	view2.functionCollection = imdb62.functionCollection
	view3 = features.syntacticView([1,2,3], config.min_support, config.num_bins, config.max_embeddable_edges,\
										remine_trees_until = config.remine_trees_until)
	view3.functionCollection = imdb62.functionCollection
	trueLabels=getTrueLabels(testBase.documents)
	with open("results.txt","at") as f:
		f.write('# '+config.config_str+"\n")
		prediction = threeTrain(view1, view2, view3, trainBase, unlabelledBase, testBase, config.training_iterations, config.training_unlabelled,f)
	print("success rate (three train): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction, trueLabels) if pred == tr]), len(testIndices)))
#@profile
def runfunc():
	with diskdict.DiskDict('stanford-trees.db') as dd:
		imdb62.functionCollection.getFunction(features.stanfordTreeDocumentFunction).setCacheDict(dd)
		mainfunc()
	imdb62.functionCollection.free()
	del imdb62.functionCollection,imdb62.documentbase
	for _ in range(2):
		print("collect: %u"%gc.collect())
	print("garbage: %u" % len(gc.garbage))
	#print("global variables: ",globals().keys())
	c_syntax_tree.showCMemoryStatistics()
	#input("press enter to exit.")
	'''
	for stat in tracemalloc.take_snapshot().statistics('traceback')[:5]:
		print(stat)
		prevLine=None
		for line in stat.traceback.format():
			if line is prevLine:
				continue
			print(line)
			prevLine = line
			'''
if __name__=='__main__':
	runfunc()
