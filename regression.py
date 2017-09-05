import liblinearutil
class multiclassLogit:
	def __init__(self, labels, classes, features):
		self.labels = labels
		self.classes = [labels.index(cl) for cl in classes]
		self.featureLength = len(features[0])
		self.featureMax = [max(features[i][j] for i in range(len(features))) for j in range(self.featureLength)]
		self.featureMin = [min(features[i][j] for i in range(len(features))) for j in range(self.featureLength)]
		self.factors = [ 1.0/mx if mx != 0 else 1.0 for (mx,mn) in zip(self.featureMax,self.featureMin) ]
		self.features=[ [ value*factor for (value,factor) in zip(feature,self.factors)] for feature in features]
		self.models = [ liblinearutil.train([1 if cl == thisclass else -1 for cl in self.classes], self.features,'-s 0') \
					for thisclass in range(len(self.labels)) ]
	def getProbabilities(self, vectors):
		vectors = [[ v*factor for (v,factor) in zip(vector,self.factors) ] for vector in vectors]
		probabilities = [ [None]*len(self.labels) for _ in vectors ]
		for i,model in enumerate(self.models):
			result = liblinearutil.predict([], vectors, model, '-b 1')
			for j,prob in enumerate(result[2]):
				probabilities[j][i]=prob[0]
		return probabilities
	def predict(self,vectors):
		probs = self.getProbabilities(vectors)
		max_ind = [p.index(max(p)) for p in probs]
		return [self.labels[i] for i in max_ind]

if __name__ == '__main__':
	model = multiclassLogit(['a','b','c'], ['a','b','c','c'], [ [0,1], [1,0],[1,1], [1,1.1] ])
	print(model.getProbabilities([ [0.1,0.9], [1.1,-0.1]]))
