#!/usr/bin/env python3
#Usage: prepare-documents.py `stanford-databasefile` `tokens-databasefile` `pos-databasefile` `c_syntax_tree-databasefile` \
#	`documentfile_1` ... `documentfile_n`
# reads the documents in the files `documentfile_1` ... `documentfile_n`, computes the stanford trees, things derived from this,
# and writes them to the given databasefiles.
# make sure no other process is reading the given databasefiles when calling this one.
import features
import stanford_parser
import syntax_tree
import diskdict
def prepareDocumentsChunked(stanford_db, tokens_db, pos_db, c_syntax_tree_db, documentbase,chunksize=1000, onlyRelevantDocuments=True):
	pos=0
	N=len(documentbase.documents)
	while pos<N:
		subb = documentbase.subbase(range(pos,min(N,pos+chunksize)))
		prepareDocuments(stanford_db, tokens_db, pos_db, c_syntax_tree_db, subb, onlyRelevantDocuments)
		pos += chunksize
def prepareDocuments(stanford_db, tokens_db, pos_db, c_syntax_tree_db, documentbase, onlyRelevantDocuments=True):
	functionCollection = documentbase.functionCollection
	with diskdict.DiskDict(stanford_db) as stanford_dict, diskdict.DiskDict(tokens_db) as tokens_dict, \
					diskdict.DiskDict(pos_db) as pos_dict, diskdict.DiskDict(c_syntax_tree_db) as st_dict:
		functionCollection.getFunction(features.stanfordTreeDocumentFunction).setCacheDict(stanford_dict)
		functionCollection.getFunction(features.tokensDocumentFunction).setCacheDict(tokens_dict)
		functionCollection.getFunction(features.posDocumentFunction).setCacheDict(pos_dict)
		functionCollection.getFunction(features.stDocumentDocumentFunction).setCacheDict(st_dict)
		docs = documentbase.documents
		if onlyRelevantDocuments:
			docs = [d for d in docs if not (d in stanford_dict and d in tokens_dict and d in pos_dict and d in st_dict)]
		functionCollection.getValues(documentbase.documents, features.stanfordTreeDocumentFunction)
		functionCollection.moveToMemory(documentbase.documents, [features.stanfordTreeDocumentFunction])
		functionCollection.getValues(documentbase.documents, features.tokensDocumentFunction)
		functionCollection.getValues(documentbase.documents, features.posDocumentFunction)
		functionCollection.getValues(documentbase.documents, features.stDocumentDocumentFunction)
	print("prepared %d documents" % len(documentbase.documents))
if __name__ == '__main__':
	import sys
	if len(sys.argv) < 6:
		print("usage: see ",sys.argv[0])
		sys.exit(1)
	stanford_db = sys.argv[1]
	tokens_db = sys.argv[2]
	pos_db = sys.argv[3]
	c_syntax_tree_db = sys.argv[4]
	documents = sys.argv[5:]
	functionCollection = features.documentFunctionCollection()
	def readfile(filename):
		with open(filename,'rt') as f:
			return f.read()
	documentbase = features.documentbase([features.document(readfile(d)) for f in documents])
	documentbase.functionCollection = functionCollection
	prepareDocuments(stanford_db, tokens_db, pos_db, c_syntax_tree_db, documentbase)
