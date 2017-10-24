#!/usr/bin/env python3
#usage: tira-tritrain.py `input_dataset` `run` `outdir` (opt. num_subdivisions, default 1)
#divides the input dataset into num_subdivisions subsets. For each of these subsets, does the following:
#	denote by trainingBase the set of training documents, by unknownBase the union of the other subdivisions and by testBase this subdivision
# 	perform tri-training, predict for this subdivision.
import tira
import threeview
import config
import features
import sys
functionCollection = features.documentFunctionCollection()
tiraInterface = tira.tiraInterface(sys.argv[1],sys.argv[2],sys.argv[3],functionCollection)
training_dataset,unknown_dataset=tiraInterface.loadCorpus()
def getModel(filename):
	global functionCollection
	with open(filename,'rb') as f:
		return features.loadClassifier(f.read(), functionCollection)
if len(sys.argv) >= 5:
	num_subdivisions = int(sys.argv[4])
else:
	num_subdivisions = 1
subdivision_length = int(len(unknown_dataset.documents)/num_subdivisions)
subdivisions = [range(i*subdivision_length,min((i+1)*subdivision_length,len(unknown_dataset.documents))) for i in range(num_subdivisions)]
prediction = []
with tiraInterface:
	initial_classifier1=getModel(tiraInterface.model_chr)
	initial_classifier2=getModel(tiraInterface.model_lex)
	initial_classifier3=getModel(tiraInterface.model_syn)
	view1 = features.characterView([3])
	view1.functionCollection = training_dataset.functionCollection
	view2 = features.lexicalView()
	view2.functionCollection = training_dataset.functionCollection
	view3 = features.syntacticView([1,2,3], config.min_support, config.num_bins, config.max_embeddable_edges)
	view3.functionCollection = training_dataset.functionCollection
	view3.readTreeFeatureFromClassifier(initial_classifier3)
	for i in range(num_subdivisions):
		unlabelledIndices=[]
		if num_subdivisions > 1:
			for j in range(num_subdivisions):
				if j!= i:
					unlabelledIndices += subdivisions[j]
		else:
			unlabelledIndices = range(len(unknown_dataset.documents))
		unlabelledBase=unknown_dataset.subbase(unlabelledIndices)
		testBase=unknown_dataset.subbase(subdivisions[i])
		prediction += threeview.threeTrain(view1,view2,view3,training_dataset,unlabelledBase,testBase,config.training_iterations, \
			config.training_unlabelled, None, initial_classifier1, initial_classifier2, initial_classifier3)
tiraInterface.writeResults(unknown_dataset, prediction)
