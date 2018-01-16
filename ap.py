import features
import os
import xml.etree.ElementTree as ET
import prepare_documents
import random
import svm
import pickle
import config
functionCollection = features.documentFunctionCollection()
mypath=os.path.dirname(os.path.abspath(__file__))
ap_path=mypath+'/ap/'
DTD='''<?xml version="1.1"?>
<!DOCTYPE apxml [
	<!ENTITY lsqb "[">
	<!ENTITY rsqb "]">
	<!ENTITY plus "+">
	<!ENTITY equals "=">
]>'''
def extractDocuments(content):
	for white1 in [' ','\n']:
		for white2 in [' ','\n']:
			content=content.replace(white1+'&'+white2, white1+'&amp;'+white2)
	for node in ET.XML(DTD+'<root>'+content+'</root>'):
		auth=None
		text=''
		for subnode in node:
			if subnode.tag=='BYLINE' and subnode.text[:3]=='By ' and subnode.text.lower() != 'by the associated press':
				if auth is not None:
					print('Multiple authors of one document: %s & %s (discard document)' % (auth,subnode.text[3:]))
					auth=None
					break
				auth=subnode.text[3:]
			elif subnode.tag=='TEXT' and subnode.text:
				text+=subnode.text
		text=text.strip()
		if auth and text:
			yield features.document(text,auth)
docs=None
try:
	with open('ap.pickle','rb') as f:
		docs=pickle.load(f)
except FileNotFoundError:
	docs=[]
	for filename in os.listdir(ap_path):
		print(filename)
		with open(ap_path+filename,'rt',encoding='latin1') as filehandle:
			docs += list(extractDocuments(filehandle.read()))
	with open('ap.pickle','wb') as f:
		pickle.dump(docs,f)
documentbase=features.documentbase(docs)
documentbase.functionCollection = functionCollection
selected_authors={
	'Barry Schweid' : ['BARRY SCHWEID', 'BARRRY SCHWEID'],
	'Chet Currier' : ['CHET CURRIER'],
	'Dave Skidmore': ['DAVE SKIDMORE'],
	'David Dishneau': ['DAVID DISHNEAU'],
	'Don Kendall' : ['DONALD KENDALL', 'DONALD M. KENDALL', 'DON KENDALL'],
	'Martin Crutsinger' : ['MARTIN CRUTSINGER', 'MARTIN S. CRUTSINGER'],
	'Rita Beamish' : ['RITA BEAMISH']
}
# !!! reducing number of authors to three !!!
for auth in list(selected_authors):
        if auth[0] != 'D':
                del selected_authors[auth]
#
selected_author_names = list(selected_authors.keys())
selected_authors_reversed={}
for name,pseudos in selected_authors.items():
	for p in pseudos:
		selected_authors_reversed[p] = name
selected_docs=[]
for doc in docs:
	if doc.author in selected_authors_reversed:
		selected_docs.append(features.document(doc.text, selected_authors_reversed[doc.author]))
selected_base = features.documentbase(selected_docs)
selected_base.functionCollection = functionCollection
selected_author_documents=[selected_base.byAuthor[auth] for auth in selected_author_names]
def prepareSelected():
	global selected_base
	prepare_documents.prepareDocumentsChunked('ap-selected-stanford.db','ap-selected-tokens.db','ap-selected-pos.db','ap-selected-c_syntax_tree.db',\
		selected_base)
def genCrossvalIndices(N,k):
	sampleSize=N//k
	indices=list(range(N))
	result=[indices]
	for _ in range(k-1):
		sample=random.sample(indices,sampleSize)
		result.append(sample)
		for i in sample:
			indices.remove(i)
	return result
random.seed(1)
crossvalIndices = [genCrossvalIndices(len(docs),5) for docs in selected_author_documents]
random.seed(config.random_seed)
crossvalDocuments = [ [ [docs[i] for i in indices] for indices in cvindices] for (docs,cvindices) in zip(selected_author_documents,crossvalIndices)]
def getTrainingDocuments(i):
	result=[]
	for authDocs in crossvalDocuments:
		for j in range(5):
			if j != i:
				result += authDocs[j]
	return result
def trainModel(i):
	trainingBase = features.documentbase(getTrainingDocuments(i))
	trainingBase.functionCollection=functionCollection
	view=features.kimView()
	view.functionCollection = functionCollection
	classifier=view.createClassifier(trainingBase, svm.SVM)
	filename="ap-selected-model-%d-%d" % (len(selected_author_names),i)
	with open(filename,"wb") as f:
		f.write(classifier.dumps())
	print("wrote to ",filename)
	return classifier
def readModel(i):
	filename="ap-selected-model-%d-%d" % (len(selected_author_names),i)
	with open(filename,'rb') as f:
		return features.loadClassifier(f.read(),functionCollection)
def getModel(i):
	try:
		return readModel(i)
	except FileNotFoundError:
		return trainModel(i)
def runCrossvalidation():
	print(",".join(selected_author_names)+",total")
	for i in range(5):
		model=readModel(i)
		testDocuments=[]
		for authorDocs in crossvalDocuments:
			testDocuments += authorDocs[i]
		prediction=model.predict(testDocuments)
		numDocuments=[len(authDocs[i]) for authDocs in crossvalDocuments]
		numCorrect=[0 for _ in selected_author_names]
		for doc,pred in zip(testDocuments,prediction):
			if doc.author == pred:
				numCorrect[selected_author_names.index(pred)] += 1
		print(",".join("%d/%d" % (c,d) for (c,d) in zip(numCorrect,numDocuments))+"%d/%d" % (sum(numCorrect),sum(numDocuments)))
if __name__ == '__main__':
	runCrossvalidation()
	#for i in range(5):
	#	getModel(i)
