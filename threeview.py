import imdb62
import features
import random
import gc
def getSuccessRate(testBase,classifier):
	return len([None for (pred,doc) in zip(classifier.getValuev(testBase.documents),testBase.documents) if pred == doc.author])
def getAccumulatedPrediction(testBase,*classifiers):
	probs = [cl.getProbabilities(testBase.documents) for cl in classifiers]
	authors = tuple(classifiers[0].regression.labels)
	for i in range(1,len(classifiers)):
		assert(tuple(classifiers[i].regression.labels) == authors)
	acc = [[sum(p[i][j] for p in probs) for j in range(len(authors))] for i in range(len(testBase.documents))]
	return [authors[p.index(max(p))] for p in acc]
def getAccumulatedSuccessRate(testBase,*classifiers):
	return len([None for (pred,doc) in zip(getAccumulatedPrediction(testBase,*classifiers),testBase.documents) if pred == doc.author])
def getTrueLabels(documents):
	return [d.author for d in documents]
def threeTrain(view1,view2,view3,trainingBase, unlabelledBase, testBase, num_iterations, num_unlabelled,results_stream=None):
	labelled1 = trainingBase
	labelled2 = trainingBase
	labelled3 = trainingBase
	extra_true1=0
	extra_true2=0
	extra_true3=0
	extra_false1=0
	extra_false2=0
	extra_false3=0
	for iteration in range(num_iterations):
		gc.collect()
		choiceIndices = random.sample(range(len(unlabelledBase.documents)),num_unlabelled)
		choice = [unlabelledBase.documents[i] for i in choiceIndices]
		classifier1 = view1.createClassifier(labelled1)
		classified1 = classifier1.getValuev(choice)
		classifier2 = view2.createClassifier(labelled2)
		classified2 = classifier2.getValuev(choice)
		classifier3 = view3.createClassifier(labelled3)
		classified3 = classifier3.getValuev(choice)
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
			if l1 == l2:
				extraLabelled3.append(features.document(doc.text,l1))
				if doc.author == l1:
					extra_true3+=1
				else:
					extra_false3 += 1
			if l1 == l3:
				extraLabelled2.append(features.document(doc.text,l1))
				if doc.author == l1:
					extra_true2+=1
				else:
					extra_false2 += 1
			if l2 == l3:
				extraLabelled1.append(features.document(doc.text,l2))
				if doc.author == l2:
					extra_true1+=1
				else:
					extra_false1+=1
		labelled1 = labelled1.extend(extraLabelled1)
		labelled2 = labelled2.extend(extraLabelled2)
		labelled3 = labelled3.extend(extraLabelled3)
		unlabelledBase = unlabelledBase.subbase(list(set(range(len(unlabelledBase.documents))) - set(choiceIndices)))
	print("added documents (true/false): %d/%d   %d/%d   %d/%d" % (extra_true1,extra_false1,extra_true2,extra_false2,extra_true3,extra_false3))
	classifier1 = view1.createClassifier(labelled1)
	classifier2 = view2.createClassifier(labelled2)
	classifier3 = view3.createClassifier(labelled3)
	pred = getAccumulatedPrediction(testBase,classifier1,classifier2,classifier3)
	correct = len([None for (pred,doc) in zip(pred,testBase.documents) if pred == doc.author])
	resline="%d,%d,%d,%d,%d,%d" % (num_iterations,len(testBase.documents),getSuccessRate(testBase,classifier1),\
		getSuccessRate(testBase,classifier2),getSuccessRate(testBase,classifier3),correct)
	print("RESULTS: ",resline)
	if results_stream != None:
		results_stream.write(resline+"\n")
		results_stream.flush()
	return pred
def mainfunc():
	indices = []
	trainIndices = []
	testIndices = []
	for i in range(3,7):
		indices += list(range(i*1000, i*1000+60))
		trainIndices += list(range(i*1000, i*1000+10))
		testIndices += list(range(i*1000+10, i*1000+20))
	imdb62.initialize(indices)
	#imdb62.writeCache(filename='small_cache',checkIfNeeded=False)
	#imdb62.computeStanfordTrees(indices)
	#imdb62.readCache()#filename='small_cache')
	print("trees loaded.")
	trainBase = imdb62.documentbase.subbase(trainIndices)
	testBase = imdb62.documentbase.subbase(testIndices)
	unlabelledIndices = list(set(indices)-set(trainIndices)-set(testIndices))
	unlabelledBase = imdb62.documentbase.subbase(unlabelledIndices)
	print("handle: %x" % trainBase.stDocumentbase.handle)
	view1 = features.characterView([1,2,3])
	view1.functionCollection = imdb62.functionCollection
	view2 = features.lexicalView()
	view2.functionCollection = imdb62.functionCollection
	view3 = features.syntacticView([1,2,3], 0, 10, 2)
	view3.functionCollection = imdb62.functionCollection
	trueLabels=getTrueLabels(testBase.documents)
	with open("results.txt","at") as f:
		prediction = threeTrain(view1, view2, view3, trainBase, unlabelledBase, testBase, 4, 40,f)
	print("success rate (three train): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction, trueLabels) if pred == tr]), len(testIndices)))
if __name__=='__main__':
	mainfunc()
	for _ in range(3):
		print("collect: %u"%gc.collect())
	print("garbage: %u" % len(gc.garbage))
