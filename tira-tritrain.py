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
import prepare_documents
import diskdict
from math import ceil
functionCollection = features.documentFunctionCollection()
tiraInterface = tira.tiraInterface(sys.argv[1],sys.argv[2],sys.argv[3],functionCollection)
tiraInterface.prepareWorkingDirectory()
training_dataset,unknown_dataset=tiraInterface.loadCorpus()
prepare_documents.prepareDocumentsChunked(tiraInterface.stanford_db, tiraInterface.tokens_db, tiraInterface.pos_db, tiraInterface.c_syntax_tree_db, \
		unknown_dataset)
def getModel(filename):
	global functionCollection
	with open(filename,'rb') as f:
		return features.loadClassifier(f.read(), functionCollection)
if len(sys.argv) >= 5:
	num_subdivisions = int(sys.argv[4])
else:
	num_subdivisions = 1
subdivision_length = ceil(len(unknown_dataset.documents)/num_subdivisions)
subdivisions = [range(i*subdivision_length,min((i+1)*subdivision_length,len(unknown_dataset.documents))) for i in range(num_subdivisions)]
print("subdivisions: ",subdivisions)
prediction = []
if len(sys.argv) >= 6:
	if sys.argv[5] == 'output':
		with diskdict.DiskDict(tiraInterface.tritrain_results_cache) as results_cache:
			identifiers = [d.identifier for d in unknown_dataset.documents]
			prediction = results_cache.fetchMany(identifiers)
			print("read prediction for ",identifiers," : ", prediction)
			tiraInterface.writeResults(unknown_dataset, prediction)
		sys.exit(0)
	index=int(sys.argv[5])
	subdivisions = subdivisions[index:index+1]
	num_subdivisions=1
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
		if not subdivisions[i]:
			continue
		unlabelledIndices = range(len(unknown_dataset.documents))
		if num_subdivisions > 1 or len(sys.argv) >= 6:
			#for j in range(num_subdivisions):
			#	if j!= i:
			#		unlabelledIndices += subdivisions[j]
			unlabelledIndices = list(set(unlabelledIndices) - set(subdivisions[i]))
		#else:
		print("unlabelled indices: ", unlabelledIndices)
		print("testIndices: ", subdivisions[i])
		unlabelledBase=unknown_dataset.subbase(unlabelledIndices)
		testBase=unknown_dataset.subbase(subdivisions[i])
		prediction += threeview.threeTrain(view1,view2,view3,training_dataset,unlabelledBase,testBase,config.training_iterations, \
			config.training_unlabelled, None, initial_classifier1, initial_classifier2, initial_classifier3)
if len(sys.argv) >= 6:
	with diskdict.DiskDict(tiraInterface.tritrain_results_cache) as results_cache:
		documents = [unknown_dataset.documents[index] for index in subdivisions[0]]
		identifiers = [d.identifier for d in documents]
		print("write prediction for ",identifiers," : ", prediction)
		for ident,pred in zip(identifiers, prediction):
			results_cache[ident] = pred
else:
	tiraInterface.writeResults(unknown_dataset, prediction)
