import config
import concurrent.futures
from collections import Counter
import sklearn.linear_model
import liblinearutil
def countermax(ctr):
	m=max(ctr.values())
	for key,value in ctr.items():
		if value == m:
			return key
class multiclassLogitAbstract:
	def getProbabilities(self,vectors,num_threads):
		pass
	def predict(self,vectors):
		probs = self.getProbabilities(vectors)
		return [countermax(p) for p in probs]
class multiclassLogitSklearn(multiclassLogitAbstract):
	def __init__(self,labels,features):
		#print(features[0])
		self.labels = labels
		self.occuring_labels = sorted(set(labels))
		self.featureMax = [max(features[i][j] for i in range(len(features))) for j in range(len(features[0]))]
		self.factors = [ 1.0/mx if mx != 0 else 1.0 for mx in self.featureMax]
		self.features=[ [ value*factor for (value,factor) in zip(feature,self.factors)] for feature in features]
		self.model = sklearn.linear_model.LogisticRegression(penalty='l2',solver='liblinear',fit_intercept=False,tol=0.01,\
									multi_class='ovr',max_iter=10000,verbose=10,C=20)
		self.model.fit(features,labels)
		self.model.sparsify()
	def getProbabilities(self,vectors,num_threads=None):
		vectors = [[ v*factor for (v,factor) in zip(vector,self.factors) ] for vector in vectors]
		return [Counter({label: prob for (label,prob) in zip(self.occuring_labels,probs)}) for probs in self.model.predict_proba(vectors)]
class multiclassLogitLiblinear:
	def __init__(self, labels, features):
		self.labels = list(set(labels))
		self.int_labels = [self.labels.index(l) for l in labels]
		self.featureLength = len(features[0])
		self.featureMax = [max(features[i][j] for i in range(len(features))) for j in range(self.featureLength)]
		self.featureMin = [min(features[i][j] for i in range(len(features))) for j in range(self.featureLength)]
		self.factors = [ 1.0/mx if mx != 0 else 1.0 for (mx,mn) in zip(self.featureMax,self.featureMin) ]
		self.features=[ [ value*factor for (value,factor) in zip(feature,self.factors)] for feature in features]
		self.models = [ liblinearutil.train([1 if l == thislabel else -1 for l in self.int_labels], self.features,'-s 0') \
					for thislabel in range(len(self.labels)) ]
	def getProbabilities(self, vectors,num_threads=4):
		print("get probabilities for %d different labels, %d labels, %d vectors" % (len(self.labels),len(self.int_labels),len(vectors)))
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
if config.use_scikit:
	multiclassLogit=multiclassLogitSklearn
else:
	multiclassLogit=multiclassLogitLiblinear

class multiclassLogitCompare(multiclassLogitAbstract):
	def __init__(self,labels,features):
		self.labels = labels
		self.distinct_labels = sorted(set(labels))
		self.features = features
		self.scikit = multiclassLogitSklearn(labels,features)
		#print("scikit: ",self.scikit.model.coef_)
		self.liblinear = multiclassLogitLiblinear(labels,features)
		#print("liblinear: ")
		#for m in self.liblinear.models:
		#	print(m.get_decfun())
	def getProbabilities(self,vectors,num_threads=4):
		res1 = self.scikit.getProbabilities(vectors,num_threads)
		res2 = self.liblinear.getProbabilities(vectors,num_threads)
		for prob1,prob2 in zip(res1,res2):
			pr1sum = sum(prob1.values())
			pr2sum = sum(prob2.values())
			prefix=''
			best1 = countermax(prob1)
			best2 = countermax(prob2)
			if best1 != best2:
				prefix='best: %s <-> %s ' % (best1,best2)
			print(prefix+", ".join(label+": "+str(prob1[label]/pr1sum)+" <-> "+str(prob2[label]/pr2sum) \
											for label in self.distinct_labels))

		return res2
#multiclassLogit = multiclassLogitCompare
if __name__ == '__main__':
	labels = ['a','b','a','b','c','c','d','d']
	features = [ [0,1], [1,0],[0,2],[.9,.1],[-.1,-1],[.1,-2],[-1,.1],[-1.5,.2]]
	testFeatures = [ [0.1,0.9], [1.1,-0.1],[-.9,1.1]]
	'''model = multiclassLogitSklearn(labels,features)
	print(model.getProbabilities(testFeatures))
	model = multiclassLogitLiblinear(labels,features)
	print(model.getProbabilities(testFeatures))
	'''
	model = multiclassLogit(labels,features)
	print(model.getProbabilities(testFeatures))
