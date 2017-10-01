import config
import concurrent.futures
from collections import Counter
import sklearn.linear_model
import liblinearutil
import pickle
import tempfile
import os
def countermax(ctr):
	m=max(ctr.values())
	for key,value in ctr.items():
		if value == m:
			return key
class multiclassLogitAbstract:
	def getProbabilities(self,vectors):
		pass
	def predict(self,vectors):
		probs = self.getProbabilities(vectors)
		return [countermax(p) for p in probs]
class multiclassLogitSklearn(multiclassLogitAbstract):
	__slots__ = ['occuring_labels','factors','model']
	def __init__(self,labels,features):
		#print(features[0])
		self.occuring_labels = sorted(set(labels))
		featureMax = [max(features[i][j] for i in range(len(features))) for j in range(len(features[0]))]
		self.factors = [ 1.0/mx if mx != 0 else 1.0 for mx in featureMax]
		features=[ [ value*factor for (value,factor) in zip(feature,self.factors)] for feature in features]
		self.model = sklearn.linear_model.LogisticRegression(penalty='l2',solver=config.scikit_solver,fit_intercept=config.scikit_fit_intercept,\
				tol=config.scikit_tolerance,multi_class=config.scikit_multi_class,max_iter=10000,\
				class_weight='balanced' if config.scikit_balance_classes else None,n_jobs=config.num_threads_classifying)
		self.model.fit(features,labels)
		#print("train scikit: ",self.features,labels)
	def getProbabilities(self,vectors):
		vectors = [[ v*factor for (v,factor) in zip(vector,self.factors) ] for vector in vectors]
		return [Counter({label: prob for (label,prob) in zip(self.occuring_labels,probs)}) for probs in self.model.predict_proba(vectors)]
class multiclassLogitLiblinear:
	__slots__ = ['labels','int_labels','factors','models']
	def __init__(self, labels, features):
		self.labels = list(set(labels))
		self.int_labels = [self.labels.index(l) for l in labels]
		featureLength = len(features[0])
		featureMax = [max(features[i][j] for i in range(len(features))) for j in range(featureLength)]
		self.factors = [ 1.0/mx if mx != 0 else 1.0 for mx in featureMax ]
		features=[ [ value*factor for (value,factor) in zip(feature,self.factors)] for feature in features]
		self.models = [ liblinearutil.train([1 if l == thislabel else -1 for l in self.int_labels], features,'-s 0') \
					for thislabel in range(len(self.labels)) ]
		#print("train liblinear: ",self.features,labels)
	def getProbabilities(self, vectors):
		print("get probabilities for %d different labels, %d labels, %d vectors" % (len(self.labels),len(self.int_labels),len(vectors)))
		vectors = [[ v*factor for (v,factor) in zip(vector,self.factors) ] for vector in vectors]
		probabilities = [ Counter({}) for _ in vectors ]
		if config.num_threads_classifying == 1:
			for label,model in zip(self.labels,self.models):
				result = liblinearutil.predict([], vectors, model, '-b 1')
				for j,prob in enumerate(result[2]):
					probabilities[j][label]=prob[0]
		else:
			exc = concurrent.futures.ThreadPoolExecutor(max_workers=config.num_threads_classifying)
			future_to_results = {exc.submit(liblinearutil.predict,[],vectors,self.models[i],'-b 1'): l for i,l in enumerate(self.labels)}
			for future in concurrent.futures.as_completed(future_to_results):
				label = future_to_results[future]
				result = future.result()
				for j,prob in enumerate(result[2]):
					probabilities[j][label] = prob[0]
		return probabilities
	def __getstate__(self):
		result = {'labels': self.labels, 'factors': self.factors, 'int_labels': self.int_labels}
		models = []
		with tempfile.NamedTemporaryFile() as fileobj:
			for model in self.models:
				liblinearutil.save_model(fileobj.name,model)
				fileobj.seek(0,os.SEEK_SET)
				models.append(fileobj.read())
		result['models'] = models
		return result
	def __setstate__(self,state):
		self.labels = state['labels']
		self.factors = state['factors']
		self.int_labels = state['int_labels']
		self.models = []
		with tempfile.NamedTemporaryFile() as fileobj:
			for model in state['models']:
				fileobj.seek(0,os.SEEK_SET)
				fileobj.write(model)
				fileobj.flush()
				self.models.append(liblinearutil.load_model(fileobj.name))
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
		print("scikit: ",self.scikit.model.coef_)
		self.liblinear = multiclassLogitLiblinear(labels,features)
		print("liblinear: ")
		for m in self.liblinear.models:
			print(m.get_decfun())
	def getProbabilities(self,vectors):
		res1 = self.scikit.getProbabilities(vectors)
		res2 = self.liblinear.getProbabilities(vectors)
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
	model = multiclassLogitCompare(labels,features)
	print(model.getProbabilities(testFeatures))
	pickled = pickle.dumps(model)
	print(pickled)
	model = pickle.loads(pickled)
	print(model.getProbabilities(testFeatures))
