import liblinearutil
import concurrent.futures
from collections import Counter
def countermax(ctr):
	m=max(ctr.values())
	for key,value in ctr.items():
		if value == m:
			return key
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
	def getProbabilities(self, vectors,num_threads=4):
		print("get probabilities for %d labels, %d classes, %d vectors" % (len(self.labels),len(self.classes),len(vectors)))
		vectors = [[ v*factor for (v,factor) in zip(vector,self.factors) ] for vector in vectors]
		probabilities = [ Counter({}) for _ in vectors ]
		if num_threads == 1:
			for label,model in zip(self.labels,self.models):
				result = liblinearutil.predict([], vectors, model, '-b 1')
				for j,prob in enumerate(result[2]):
					probabilities[j][label]=prob[0]
		else:
			exc = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)
			future_to_results = {exc.submit(liblinearutil.predict,[],vectors,self.models[i],'-b 1'): l for i,l in enumerate(self.labels)}
			for future in concurrent.futures.as_completed(future_to_results):
				label = future_to_results[future]
				result = future.result()
				for j,prob in enumerate(result[2]):
					probabilities[j][label] = prob[0]
		return probabilities
	def predict(self,vectors):
		probs = self.getProbabilities(vectors)
		return [countermax(p) for p in probs]
if __name__ == '__main__':
	model = multiclassLogit(['a','b','c'], ['a','b','c','c'], [ [0,1], [1,0],[1,1], [1,1.1] ])
	print(model.getProbabilities([ [0.1,0.9], [1.1,-0.1]]))
