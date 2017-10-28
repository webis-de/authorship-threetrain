#!/usr/bin/env python3
#usage: tira-train-model.py `input_dataset` `run` `outdir` `model1` `model2` ...
#where model_n is one of 'kim' 'lexical' 'character' 'syntactic'
#trains each model using the available training data and writes to the appropriate file
import sys
import tira
import features
import prepare_documents
import regression
import svm
import config
if len(sys.argv) < 5:
	print("Usage: see ",sys.argv[0])
	sys.exit(0)
tiraInterface = tira.tiraInterface(sys.argv[1],sys.argv[2],sys.argv[3],features.documentFunctionCollection())
tiraInterface.prepareWorkingDirectory()
training_dataset,unknown_dataset=tiraInterface.loadCorpus()
with tiraInterface:
	for model in sys.argv[4:]:
		filename=None
		view=None
		ml=None
		if model == 'kim':
			view = features.kimView()
			ml=svm.SVM
			filename=tiraInterface.model_kim
		elif model == 'lexical':
			view=features.lexicalView()
			filename=tiraInterface.model_lex
		elif model == 'character':
			view=features.characterView([3])
			filename=tiraInterface.model_chr
		elif model == 'syntactic':
			view=features.syntacticView([1,2,3], config.min_support, config.num_bins, config.max_embeddable_edges)
			view.functionCollection = training_dataset.functionCollection
			filename=tiraInterface.model_syn
			try:
				with open(tiraInterface.model_kim,'rb') as f:
					view.readTreeFeatureFromClassifier(features.loadClassifier(f.read(),training_dataset.functionCollection))
			except FileNotFoundError:
				pass
		else:
			print("Unknown model: '%s'" % model)
			sys.exit(1)
		if ml is None:
			ml = regression.multiclassLogit
		view.functionCollection = training_dataset.functionCollection
		classifier=view.createClassifier(training_dataset, ml)
		with open(filename,'wb') as f:
			f.write(classifier.dumps())
		print("wrote to ",filename)
