import imdb62
import features
import random
def getTrueLabels(documents):
	return [d.author for d in documents]
def threeTrain(view1,view2,view3,trainingBase, unlabelledBase, testBase, num_iterations, num_unlabelled):
	labelled1 = trainingBase
	labelled2 = trainingBase
	labelled3 = trainingBase
	for iteration in range(num_iterations):
		choiceIndices = random.sample(range(len(unlabelledBase.documents)),num_unlabelled)
		choice = [unlabelledBase.documents[i] for i in choiceIndices]
		classifier1 = view1.createClassifier(labelled1)
		classified1 = classifier1.getValuev(choice)
		classifier2 = view2.createClassifier(labelled2)
		classified2 = classifier2.getValuev(choice)
		classifier3 = view3.createClassifier(labelled3)
		classified3 = classifier3.getValuev(choice)
		print(classified1)
		print(classified2)
		print(classified3)
		print("true:")
		print([d.author for d in choice])
		extraLabelled1 = [features.document(choice[i].text,classified2[i]) for i in range(len(choice)) if classified2[i] == classified3[i]]
		extraLabelled2 = [features.document(choice[i].text,classified1[i]) for i in range(len(choice)) if classified1[i] == classified3[i]]
		extraLabelled3 = [features.document(choice[i].text,classified1[i]) for i in range(len(choice)) if classified1[i] == classified2[i]]
		print("labelled1 gets %d documents, labelled2 gets %d, labelled3 gets %d." % (len(extraLabelled1), len(extraLabelled2), len(extraLabelled3)))
		labelled1 = labelled1.extend(extraLabelled1)
		labelled2 = labelled2.extend(extraLabelled2)
		labelled3 = labelled3.extend(extraLabelled3)
		unlabelledBase = unlabelledBase.subbase(list(set(range(len(unlabelledBase.documents))) - set(choiceIndices)))
	classifier1 = view1.createClassifier(labelled1)
	prob1 = classifier1.getProbabilities(testBase.documents)
	classifier2 = view2.createClassifier(labelled2)
	prob2 = classifier2.getProbabilities(testBase.documents)
	classifier3 = view3.createClassifier(labelled3)
	prob3 = classifier3.getProbabilities(testBase.documents)
	print("trainingBase.authors: ",trainingBase.authors)
	print("classifier1.labels: ",classifier1.regression.labels)
	print("classifier2.labels: ",classifier2.regression.labels)
	print("classifier3.labels: ",classifier3.regression.labels)
	accumulated = [ [p1+p2+p3 for (p1,p2,p3) in zip(vec1, vec2, vec3)] for (vec1,vec2,vec3) in zip(prob1, prob2, prob3)]
	return [trainingBase.authors[p.index(max(p))] for p in accumulated]
indices = []
trainIndices = []
testIndices = []
for i in range(4):
	indices += list(range(i*1000, i*1000+40))
	trainIndices += list(range(i*1000+5, i*1000+10))
	testIndices += list(range(i*1000+30, i*1000+40))
for pos in range(0,len(indices), 40):
	imdb62.computeStanfordTrees(indices[pos:pos+40])
	if imdb62.cacheUpdateNeeded:
		imdb62.writeCache()
		imdb62.cacheUpdateNeeded=True
		imdb62.writeCache2()
trainBase = imdb62.documentbase.subbase(trainIndices)
testBase = imdb62.documentbase.subbase(testIndices)
unlabelledIndices = list(set(indices)-set(trainIndices)-set(testIndices))
unlabelledBase = imdb62.documentbase.subbase(unlabelledIndices)

view1 = features.characterView([1,2,3])
view1.functionCollection = imdb62.functionCollection
classifier1 = view1.createClassifier(trainBase)
view2 = features.lexicalView()
view2.functionCollection = imdb62.functionCollection
classifier2 = view2.createClassifier(trainBase)
view3 = features.syntacticView([1,2,3], 0, 10, 2)
view3.functionCollection = imdb62.functionCollection
classifier3 = view3.createClassifier(trainBase)
prob1 = classifier1.getProbabilities(testBase.documents)
prob2 = classifier2.getProbabilities(testBase.documents)
prob3 = classifier3.getProbabilities(testBase.documents)
accumulated = [ [p1+p2+p3 for (p1,p2,p3) in zip(vec1, vec2, vec3)] for (vec1,vec2,vec3) in zip(prob1, prob2, prob3)]
pred1 = [trainBase.authors[p.index(max(p))] for p in prob1]
pred2 = [trainBase.authors[p.index(max(p))] for p in prob2]
pred3 = [trainBase.authors[p.index(max(p))] for p in prob3]
accumulatedPrediction = [trainBase.authors[p.index(max(p))] for p in accumulated]
trueLabels = [d.author for d in testBase.documents]
for i in range(len(testIndices)):
	out=str(i)+' ('
	out += '1' if pred1[i] == trueLabels[i] else '0'
	out += '1' if pred2[i] == trueLabels[i] else '0'
	out += '1' if pred3[i] == trueLabels[i] else '0'
	out += '1' if accumulatedPrediction[i] == trueLabels[i] else '0'
	out += ')'
	for j in range(len(prob1[i])):
		pattern=''
		if trainBase.authors[j] == trueLabels[i]:
			pattern='\t[%f,%f,%f]'
		else:
			pattern='\t(%f,%f,%f)'
		out += pattern % (prob1[i][j], prob2[i][j], prob3[i][j])
	print(out)
print("success rate (character): %d/%d." % ( len([None for (pred,tr) in zip(pred1, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (lexical): %d/%d." % ( len([None for (pred,tr) in zip(pred2, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (syntactic): %d/%d." % ( len([None for (pred,tr) in zip(pred3, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (accumulated): %d/%d." % ( len([None for (pred,tr) in zip(accumulatedPrediction, trueLabels) if pred == tr]), len(testIndices)))

prediction = threeTrain(view1, view2, view3, trainBase, unlabelledBase, testBase, 2, 10)
print(list(zip(prediction, trueLabels)))
print("success rate (character): %d/%d." % ( len([None for (pred,tr) in zip(pred1, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (lexical): %d/%d." % ( len([None for (pred,tr) in zip(pred2, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (syntactic): %d/%d." % ( len([None for (pred,tr) in zip(pred3, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (accumulated): %d/%d." % ( len([None for (pred,tr) in zip(accumulatedPrediction, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (three train): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction, trueLabels) if pred == tr]), len(testIndices)))

from sys import exit
exit(0)

view3 = syntacticView([1,2,3], 0, 10, 2)
classifier = view3.createClassifier(trainIndices, getTrueLabels(trainIndices))
prediction3 = classifier.predict(testIndices)
print(list(zip(prediction3, trueLabels)))
print("success rate (syntactic): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction3, getTrueLabels(testIndices)) if pred == tr]), len(testIndices)))

view1 = characterView([1,2,3])
classifier = view1.createClassifier(trainIndices, getTrueLabels(trainIndices))
prediction1 = classifier.predict(testIndices)
print(list(zip(prediction1, trueLabels)))
print("success rate (character): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction1, getTrueLabels(testIndices)) if pred == tr]), len(testIndices)))

view2 = lexicalView()
classifier = view2.createClassifier(trainIndices, getTrueLabels(trainIndices))
prediction2 = classifier.predict(testIndices)
print(list(zip(prediction2, trueLabels)))
print("success rate (lexical): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction2, getTrueLabels(testIndices)) if pred == tr]), len(testIndices)))

