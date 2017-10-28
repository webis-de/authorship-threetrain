import config
if config.debug_memory:
	import tracemalloc
	tracemalloc.start(1024)
	import objgraph
	import sys
	from memory_profiler import profile
else:
	def profile(x):
		return x
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
	return [features.countermax(c) for c in acc]
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
	classifier = view.createClassifier(documentbase,regression.multiclassLogit)
	return classifier,classifier.predict(test_documents)

#features that are derived from stanfordTreeDocumentFunction
neededDocumentFunctions = [features.tokensDocumentFunction,features.posDocumentFunction,features.stDocumentDocumentFunction]
#@profile
def threeTrain(view1,view2,view3,trainingBase, unlabelledBase, testBase, num_iterations, num_unlabelled,results_stream=None,initial_classifier1=None,\
			initial_classifier2=None,initial_classifier3=None):
#if no initial classifiers are given, they are learned from the trainingBase.
	if None in trainingBase.authors:
		raise Exception("Training Base should be labelled.")
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
	#@profile
	def prepareDocuments(docs):
		import pickle
		print("preparing %d documents" % len(docs))
		chunksize=15000
		if functionCollection is not None:
			for i in range(0,len(docs),chunksize):
				chunk = docs[i:i+chunksize]
				functionCollection.moveToMemory(chunk,neededDocumentFunctions)
				#print("forget unnecessary document functions...")
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
	verificationBase = testBase.subbase([i for i,doc in enumerate(testBase.documents) if doc.author is not None])
	for iteration in range(num_iterations):
		gc.collect()
		remaining_unlabelled = len(unlabelledBase.documents)
		if remaining_unlabelled == 0:
			break
		if remaining_unlabelled < num_unlabelled:
			choiceIndices = random.sample(range(remaining_unlabelled,num_unlabelled))
		else:
			choiceIndices = list(range(remaining_unlabelled))
		choice = [unlabelledBase.documents[i] for i in choiceIndices]
		prepareDocuments(choice)
		cached_keys = [sorted(list(functionCollection.getFunction(f).cachedValues.memory_cache)) for f in neededDocumentFunctions]
		'''
		classifier1 = view1.createClassifier(balanced1)
		classified1 = classifier1.predict(choice)
		classifier2 = view2.createClassifier(balanced2)
		classified2 = classifier2.predict(choice)
		classifier3 = view3.createClassifier(balanced3)
		classified3 = classifier3.predict(choice)
		'''
		if iteration == 0 and initial_classifier1 is not None:
			classifier1=initial_classifier1
			parallelGroup.add_branch(classifier1.predict,choice)
		else:
			parallelGroup.add_branch(trainAndPredict,view1,balanced1,choice)
		if iteration == 0 and initial_classifier2 is not None:
			classifier2=initial_classifier2
			parallelGroup.add_branch(classifier2.predict,choice)
		else:
			parallelGroup.add_branch(trainAndPredict,view2,balanced2,choice)
		if iteration == 0 and initial_classifier3 is not None:
			classifier3=initial_classifier3
			parallelGroup.add_branch(classifier3.predict,choice)
		else:
			parallelGroup.add_branch(trainAndPredict,view3,balanced3,choice)
		print("waiting for classification and prediction...")
		parallelGroup_results = parallelGroup.get_results()
		print("got results!")
		if iteration == 0 and initial_classifier1 is not None:
			classified1=parallelGroup_results[0]
		else:
			classifier1,classified1 = parallelGroup_results[0]
		if iteration == 0 and initial_classifier2 is not None:
			classified2=parallelGroup_results[1]
		else:
			classifier2,classified2 = parallelGroup_results[1]
		if iteration == 0 and initial_classifier3 is not None:
			classified3=parallelGroup_results[2]
		else:
			classifier3,classified3 = parallelGroup_results[2]
		if verificationBase.documents:
			print("prediction verificationBase for the records...")
			parallelGroup.add_branch(classifier1.getValuev,verificationBase.documents)
			parallelGroup.add_branch(classifier2.getValuev,verificationBase.documents)
			parallelGroup.add_branch(classifier3.getValuev,verificationBase.documents)
			parallelGroup.get_results()
			print("got results for verificationBase!")
			resline="%d,%d,%d,%d,%d,%d" % (iteration,len(verificationBase.documents),getSuccessRate(verificationBase,classifier1),\
				getSuccessRate(verificationBase,classifier2),getSuccessRate(verificationBase,classifier3),\
				getAccumulatedSuccessRate(verificationBase,classifier1,classifier2,classifier3))
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
			if l1 is None or l2 is None or l3 is None:
				raise Exception("Classifier should assign proper labels (i.e. distinct from None)")
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
				if doc.author == l2:
					extra_true1+=1
				else:
					extra_false1+=1
			if discard and functionCollection is not None:
				#forget doc if the same text (=identifier) does not occur anywhere where it is needed
				idf = doc.identifier
				if idf not in labelled1.byIdentifier and idf not in labelled2.byIdentifier and idf not in labelled3.byIdentifier and \
							idf not in testBase.byIdentifier:
					functionCollection.forgetDocument(doc)
		labelled1 = labelled1.extend(extraLabelled1)
		labelled2 = labelled2.extend(extraLabelled2)
		labelled3 = labelled3.extend(extraLabelled3)
		print("labelled 1: ",Counter([d.author for d in labelled1.documents]))
		print("labelled 2: ",Counter([d.author for d in labelled2.documents]))
		print("labelled 3: ",Counter([d.author for d in labelled3.documents]))
		if None in labelled1.authors or None in labelled2.authors or None in labelled3.authors:
			raise Exception("Did not expect to find stupid labels here.")
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
	classifier1 = view1.createClassifier(balanced1,regression.multiclassLogit)
	classifier2 = view2.createClassifier(balanced2,regression.multiclassLogit)
	classifier3 = view3.createClassifier(balanced3,regression.multiclassLogit)
	pred = getAccumulatedPrediction(testBase,classifier1,classifier2,classifier3)
	if verificationBase.documents:
		correct = len([None for (pred,doc) in zip(pred,testBase.documents) if pred == doc.author])
		resline="%d,%d,%d,%d,%d,%d" % (num_iterations,len(verificationBase.documents),getSuccessRate(verificationBase,classifier1),\
			getSuccessRate(verificationBase,classifier2),getSuccessRate(verificationBase,classifier3),correct)
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
	trainDocuments = []
	unlabelledDocuments = []
	testDocuments = []
	authors = random.sample(imdb62.documentbase.authors[:3 if config.use_small_cache else 62],config.num_authors)
	for auth in authors:
		avail = imdb62.documentbase.byAuthor[auth]
		if config.use_small_cache:
			avail = avail[:10]
		avail = set(avail)
		tr= random.sample(avail,config.num_training)
		trainDocuments += tr
		avail = avail-set(tr)
		unl = random.sample(avail,config.num_unlabelled)
		unlabelledDocuments += unl
		avail = avail-set(unl)
		testDocuments += random.sample(avail,config.num_test)
	usedDocuments = trainDocuments + unlabelledDocuments + testDocuments
	if config.use_small_cache:
		print("use small cache.")
		#imdb62.initialize(indices=indices,filename='small_cache')
	else:
		#imdb62.initialize(indices=indices)
		pass
	#imdb62.writeCache(filename='small_cache',checkIfNeeded=False)
	#imdb62.computeStanfordTrees(indices)
	#imdb62.readCache(filename='small_cache')
	print("trees loaded.")
	'''
	trainBase = imdb62.documentbase.subbase(trainIndices)
	testBase = imdb62.documentbase.subbase(testIndices)
	unlabelledBase = imdb62.documentbase.subbase(unlabelledIndices)
	'''
	trainBase = features.documentbase(trainDocuments)
	trainBase.functionCollection = imdb62.functionCollection
	unlabelledBase = features.documentbase(unlabelledDocuments)
	unlabelledBase.functionCollection = imdb62.functionCollection
	testBase = features.documentbase(testDocuments)
	testBase.functionCollection = imdb62.functionCollection
	view1 = features.characterView([3])
	view1.functionCollection = imdb62.functionCollection
	view2 = features.lexicalView()
	view2.functionCollection = imdb62.functionCollection
	view3 = features.syntacticView([1,2,3], config.min_support, config.num_bins, config.max_embeddable_edges,\
								remine_trees_until = config.remine_trees_until,minedTreesCacheFile='mined-trees')
	view3.functionCollection = imdb62.functionCollection
	trueLabels=getTrueLabels(testBase.documents)
	with open("results.txt","at") as f:
		f.write('# '+config.config_str+"\n")
		prediction = threeTrain(view1, view2, view3, trainBase, unlabelledBase, testBase, config.training_iterations, config.training_unlabelled,f)
	print("success rate (three train): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction, trueLabels) if pred == tr]), len(testDocuments)))
#@profile
def runfunc():
	with diskdict.DiskDict('stanford-trees.db') as stanford_dict, diskdict.DiskDict('tokens.db') as tokens_dict, \
		diskdict.DiskDict('pos.db') as pos_dict, diskdict.DiskDict('c_syntax_tree.db') as st_dict:
		imdb62.functionCollection.getFunction(features.stanfordTreeDocumentFunction).setCacheDict(stanford_dict)
		imdb62.functionCollection.getFunction(features.tokensDocumentFunction).setCacheDict(tokens_dict)
		imdb62.functionCollection.getFunction(features.posDocumentFunction).setCacheDict(pos_dict)
		imdb62.functionCollection.getFunction(features.stDocumentDocumentFunction).setCacheDict(st_dict)
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
