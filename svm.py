import features
from collections import Counter
from sklearn.svm import SVC
import math
class svmModel(features.mlModel):
	__slots__=['occuring_labels', 'model']
	def __init__(self,labels,features):
		self.occuring_labels = sorted(set(labels))
		self.model = SVC(probability=True)
		self.model.fit(features,labels)
	def getProbabilities(self,vectors):
		return [Counter({label: prob for (label,prob) in zip(self.occuring_labels,probs)}) for probs in self.model.predict_proba(vectors)]
SVM=features.easyparallelArgumentPassingLearningMachine(svmModel)
if __name__ == '__main__':
	points1 = [(1,0), (0,1), (1,2), (3,0)]
	points2 = [(0,-4), (-5,-5), (-1,0)]
	testPoints = [(1,1), (-1,-1), (5,6), (-17,-1), (-1,-17)]
	model = svmModel([1]*len(points1) + [2] * len(points2), points1+points2)
	print(model.getPrediction(testPoints))
	model = svmModel([2]*len(points2) + [1] * len(points1), points2+points1)
	print(model.getPrediction(testPoints))

