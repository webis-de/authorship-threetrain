#creates a KIM model for the PAN11 corpus despite sklearn killed the last process after mining
import features
import tira
from c_syntax_tree import syntax_tree
import svm
import math
def esyntax_tree(label,children):
	result=syntax_tree(label,children)
	result.setExtendable()
	return result
est=lambda d: esyntax_tree(d,[])
st=lambda d: syntax_tree(d,[])
recovered_trees = [est(21),est(65),est(32),esyntax_tree(74,[st(13)]),esyntax_tree(74,[syntax_tree(13,[est(40)])]), \
	esyntax_tree(74,[syntax_tree(13,[st(40)])]), est(46), est(28), est(66), est(33), est(10), est(38), est(1), est(29), esyntax_tree(13,[st(40)]), \
	est(13), est(53)]
tiraInterface = tira.tiraInterface('pan11-authorship-attribution-test-dataset-large-2015-10-20','none','/tmp/output',features.documentFunctionCollection())
tiraInterface.prepareWorkingDirectory()
training_dataset,unknown_dataset=tiraInterface.loadCorpus()
with tiraInterface:
	treeFeature=tiraInterface.functionCollection.getFunction(features.syntaxTreeFrequencyFeature,tuple(recovered_trees))
	treeFeature.moveToMemory(training_dataset.documents)
#	values=treeFeature.getValuev(training_dataset.documents)
#	for i,v in enumerate(values):
#		if any(math.isnan(x) for x in v):
#			print("this document: '%s' has vector %s" % (training_dataset.documents[i].text, repr(v)))
	classifier=features.documentClassifier(training_dataset, treeFeature, svm.SVM)
	#with open(tiraInterface.model_kim,'wb') as f:
	#	f.write(classifier.dumps())
	#print("written model.")
