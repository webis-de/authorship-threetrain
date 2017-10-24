#!/usr/bin/env python3
#usage: tira-train-model.py `input_dataset` `run` `outdir` `model`
#where model is one of 'kim' 'lexical' 'character' 'syntactic'
#uses the model to predict the unknown data
import sys
import tira
import features
import prepare_documents
if len(sys.argv) < 5:
	print("Usage: see ",sys.argv[0])
	sys.exit(0)
functionCollection = features.documentFunctionCollection()
tiraInterface = tira.tiraInterface(sys.argv[1],sys.argv[2],sys.argv[3],functionCollection)
tiraInterface.prepareWorkingDirectory()
training_dataset,unknown_dataset=tiraInterface.loadCorpus()
prepare_documents.prepareDocumentsChunked(tiraInterface.stanford_db, tiraInterface.tokens_db, tiraInterface.pos_db, tiraInterface.c_syntax_tree_db, \
		unknown_dataset)
modelfile=None
if sys.argv[4] == 'kim':
	modelfile=tiraInterface.model_kim
elif sys.argv[4] == 'lexical':
	modelfile=tiraInterface.model_lex
elif sys.argv[4] == 'character':
	modelfile=tiraInterface.model_chr
elif sys.argv[4] == 'syntactic':
	modelfile=tiraInterface.model_syn
else:
	print("Unknown model: '%s'" % model)
	sys.exit(1)
prediction=None
with tiraInterface:
	classifier=None
	with open(modelfile,'rb') as f:
		classifier=features.loadClassifier(f.read(),functionCollection)
	prediction = classifier.predict(unknown_dataset.documents)
tiraInterface.writeResults(unknown_dataset, prediction)
