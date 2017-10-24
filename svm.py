import features
from collections import Counter
from sklearn.svm import SVC
class svmModel(features.mlModel):
	__slots__=['occuring_labels', 'model']
	def __init__(self,labels,features):
		self.occuring_labels = sorted(set(labels))
		self.model = SVC(probability=True)
		self.model.fit(features,labels)
	def getProbabilities(self,vectors):
		return [Counter({label: prob for (label,prob) in zip(self.occuring_labels,probs)}) for probs in self.model.predict_proba(vectors)]
SVM=features.easyparallelArgumentPassingLearningMachine(svmModel)
