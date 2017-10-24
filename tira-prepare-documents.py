#!/usr/bin/env python3
#Usage: tira-prepare-documents `inputDataset` `run` `outdir`  `which`
#prepares the documents for the databases. First three arguments are from the PAN interface, last must be "training", "unknown" or "both".
import prepare_documents
import tira
import features
def prepareDocuments(tira,which):
	training_dataset,unknown_dataset = tira.loadCorpus()
	if which == 'both' or which == 'training':
		prepare_documents.prepareDocumentsChunked(tira.stanford_db,tira.tokens_db,tira.pos_db,tira.c_syntax_tree_db,training_dataset)
	if which == 'both' or which == 'unknown':
		prepare_documents.prepareDocumentsChunked(tira.stanford_db,tira.tokens_db,tira.pos_db,tira.c_syntax_tree_db,unknown_dataset)
if __name__ == '__main__':
	import sys
	interf=tira.tiraInterface(sys.argv[1],sys.argv[2],sys.argv[3],features.documentFunctionCollection())
	interf.prepareWorkingDirectory()
	prepareDocuments(interf,sys.argv[4])
