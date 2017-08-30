import imdb62
import regression
from functools import reduce
from pos import pos_tags
import random
class feature:
	# a feature maps reviews to vectors (without looking at the author)
	def __init__(self):
		raise Exception("This is - kind of - abstract")
	def vectorLength(self):
		pass
	def getVector(self, review):
		pass
class combinedFeature(feature):
	#given features ft1, ..., ftn; this one maps a document d to (ft1(d), ..., ftn(d))
	def __init__(self, subfeatures):
		self.subfeatures = subfeatures
	def vectorLength(self):
		return sum(ft.vectorLength() for ft in self.subfeatures)
	def getVector(self, review):
		result = []
		for ft in self.subfeatures:
			result += ft.getVector(review)
		return result
class documentClassifier:
	def __init__(self, feature, indices, labels):
		self.feature = feature
		self.indices = indices
		self.labels = labels
		self.reviews = [imdb62.reviews[i] for i in indices]
		self.features = [feature.getVector(rev) for rev in self.reviews]
		self.model = regression.multiclassLogit(imdb62.reviewers, self.labels, self.features)
	def predict(self, indices):
		features = [self.feature.getVector(imdb62.reviews[i]) for i in indices]
		return self.model.predict(features)
	def probabilities(self, indices):
		features = [self.feature.getVector(imdb62.reviews[i]) for i in indices]
		return self.model.getProbabilities(features)
class view:
	#a view takes a number of reviews and creates a feature (by looking at the authors)
	def __init__(self):
		raise Exception("This is - kind of - abstract")
	def extractFeature(self, indices):
		pass
	def createClassifier(self, indices, labels):
		return documentClassifier(self.extractFeature(indices), indices, labels)
class characterNGramFeature(feature):
	def __init__(self,n, values):
		self.n=n
		self.values=values
	def vectorLength(self):
		return len(self.values)
	def getVector(self, review):
		return [review.characterNGramCounts(self.n).get(val,0) for val in self.values]
class characterView(view):
	def __init__(self, ns):
		self.ns = ns
	def extractFeature(self, indices):
		features = []
		for n in self.ns:
			values=set()
			for i in indices:
				values = values.union(set(imdb62.reviews[i].characterNGramCounts(n)))
			features.append(characterNGramFeature(n,list(values)))
		return combinedFeature(features)
class wordUnigramFeature(feature):
	def __init__(self, values):
		self.values = values
	def vectorLength(self):
		return len(self.values)
	def getVector(self, review):
		#return [review.tokens.count(value) for value in self.values]
		return [review.tokenCounts.get(val,0) for val in self.values]
class lexicalView(view):
	def __init__(self):
		pass
	def extractFeature(self, indices):
		return wordUnigramFeature(list(reduce(lambda x,y: x.union(y), (set(imdb62.reviews[i].tokenCounts) for i in indices))))
class posNGramFeature(feature):
	def __init__(self, n,values):
		self.n=n
		self.values = values
	def vectorLength(self):
		return len(self.values)
	def getVector(self, review):
		#return [ len([None for i in range(len(review.pos)-len(value)) if review.pos[i:i+len(value)] == value]) for value in self.values ]
		return [review.posNGramCounts(self.n).get(val,0) for val in self.values]
class keeSubtreeFeature(feature):
	def __init__(self, values):
		self.values = values
		for value in values:
			value.nicePrint()
	def vectorLength(self):
		return len(self.values)
	def getVector(self, review):
		return [ review.stDocument.frequency(value) for value in self.values ]
class syntacticView(view):
	def __init__(self, ns, supportLowerBound, n, k):
		self.ns = ns
		self.supportLowerBound = supportLowerBound
		self.n = n
		self.k = k
	def extractFeature(self, indices):
		global pos_tags
		features=[]
		for n in self.ns:
			values = set()
			for i in indices:
				values = values.union(set(imdb62.reviews[i].posNGramCounts(n)))
			features.append(posNGramFeature(n,list(values)))
		#posFeature = posNGramFeature(posNgrams)
		base = imdb62.createStDocumentbase(indices)
		keeFeature = keeSubtreeFeature(base.mineDiscriminativePatterns(len(pos_tags), self.supportLowerBound, self.n, self.k))
		features.append(keeFeature)
		return combinedFeature(features)
		#return keeFeature
def getTrueLabels(indices):
	return [imdb62.reviews[i].revid for i in indices]
def threeTrain(view1, view2, view3, labelledIndices, labels, unlabelledIndices, testIndices, num_iterations, num_unlabelled):
	labelled1 = labelledIndices[:]
	labels1 = labels[:]
	labelled2 = labelledIndices[:]
	labels2 = labels[:]
	labelled3 = labelledIndices[:]
	labels3 = labels[:]
	unlabelledIndices = unlabelledIndices[:]
	for iteration in range(num_iterations):
		choice = random.sample(unlabelledIndices, num_unlabelled)
		classifier1 = view1.createClassifier(labelled1, labels1)
		classified1 = classifier1.predict(choice)
		classifier2 = view2.createClassifier(labelled2, labels2)
		classified2 = classifier2.predict(choice)
		classifier3 = view3.createClassifier(labelled3, labels3)
		classified3 = classifier3.predict(choice)
		extraLabelled1 = [i for i in range(len(choice)) if classified2[i] == classified3[i]]
		extraLabels1 = [classified2[i] for i in extraLabelled1]
		extraLabelled2 = [i for i in range(len(choice)) if classified1[i] == classified3[i]]
		extraLabels2 = [classified1[i] for i in extraLabelled2]
		extraLabelled3 = [i for i in range(len(choice)) if classified1[i] == classified2[i]]
		extraLabels3 = [classified1[i] for i in extraLabelled3]
		labelled1 += [choice[i] for i in extraLabelled1]
		labels1 += extraLabels1
		labelled2 += [choice[i] for i in extraLabelled2]
		labels2 += extraLabels2
		labelled3 += [choice[i] for i in extraLabelled3]
		labels3 += extraLabels3
		for i in choice:
			unlabelledIndices.remove(i)
	classifier1 = view1.createClassifier(labelled1, labels1)
	prob1 = classifier1.probabilities(testIndices)
	classifier2 = view2.createClassifier(labelled2, labels2)
	prob2 = classifier2.probabilities(testIndices)
	classifier3 = view3.createClassifier(labelled3, labels3)
	prob3 = classifier3.probabilities(testIndices)
	accumulated = [ [p1+p2+p3 for (p1,p2,p3) in zip(vec1, vec2, vec3)] for (vec1,vec2,vec3) in zip(prob1, prob2, prob3)]
	return [imdb62.reviewers[p.index(max(p))] for p in accumulated]

indices = []
trainIndices = []
testIndices = []
for i in range(8):
	indices += list(range(i*1000, i*1000+40))
	trainIndices += list(range(i*1000, i*1000+10))
	testIndices += list(range(i*1000+30, i*1000+40))
for pos in range(0,len(indices), 40):
	imdb62.computeStanfordTrees(indices[pos:pos+40])
	imdb62.writeCache()
imdb62.reviewers = list(set([imdb62.reviews[i].revid for i in indices]))


trueLabels = getTrueLabels(testIndices)

view1 = characterView([1,2,3])
classifier1 = view1.createClassifier(trainIndices, getTrueLabels(trainIndices))
view2 = lexicalView()
classifier2 = view2.createClassifier(trainIndices, getTrueLabels(trainIndices))
view3 = syntacticView([1,2,3], 0, 10, 2)
classifier3 = view3.createClassifier(trainIndices, getTrueLabels(trainIndices))
prob1 = classifier1.probabilities(testIndices)
prob2 = classifier2.probabilities(testIndices)
prob3 = classifier3.probabilities(testIndices)
accumulated = [ [p1+p2+p3 for (p1,p2,p3) in zip(vec1, vec2, vec3)] for (vec1,vec2,vec3) in zip(prob1, prob2, prob3)]
pred1 = [imdb62.reviewers[p.index(max(p))] for p in prob1]
pred2 = [imdb62.reviewers[p.index(max(p))] for p in prob2]
pred3 = [imdb62.reviewers[p.index(max(p))] for p in prob3]
accumulatedPrediction = [imdb62.reviewers[p.index(max(p))] for p in accumulated]
for i in range(len(testIndices)):
	out=str(imdb62.reviews[testIndices[i]].identifier)+' ('
	out += '1' if pred1[i] == trueLabels[i] else '0'
	out += '1' if pred2[i] == trueLabels[i] else '0'
	out += '1' if pred3[i] == trueLabels[i] else '0'
	out += '1' if accumulatedPrediction[i] == trueLabels[i] else '0'
	out += ')'
	for j in range(len(prob1[i])):
		pattern=''
		if imdb62.reviewers[j] == trueLabels[i]:
			pattern='\t[%f,%f,%f]'
		else:
			pattern='\t(%f,%f,%f)'
		out += pattern % (prob1[i][j], prob2[i][j], prob3[i][j])
	print(out)
print("success rate (character): %d/%d." % ( len([None for (pred,tr) in zip(pred1, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (lexical): %d/%d." % ( len([None for (pred,tr) in zip(pred2, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (syntactic): %d/%d." % ( len([None for (pred,tr) in zip(pred3, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (accumulated): %d/%d." % ( len([None for (pred,tr) in zip(accumulatedPrediction, trueLabels) if pred == tr]), len(testIndices)))

unlabelledIndices = list(set(indices)-set(trainIndices)-set(testIndices))
prediction = threeTrain(view1, view2, view3, trainIndices, getTrueLabels(trainIndices), unlabelledIndices, testIndices, 2, 40)
print(list(zip(prediction, trueLabels)))
print("success rate (character): %d/%d." % ( len([None for (pred,tr) in zip(pred1, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (lexical): %d/%d." % ( len([None for (pred,tr) in zip(pred2, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (syntactic): %d/%d." % ( len([None for (pred,tr) in zip(pred3, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (accumulated): %d/%d." % ( len([None for (pred,tr) in zip(accumulatedPrediction, trueLabels) if pred == tr]), len(testIndices)))
print("success rate (three train): %d/%d.\n" % ( len([None for (pred,tr) in zip(prediction, getTrueLabels(testIndices)) if pred == tr]), len(testIndices)))

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

