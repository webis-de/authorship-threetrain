configuration = {
'do_fake' : False, # set to true to insert only truely labelled documents
'use_small_cache':False, # set to true to use a small cache. Restrictions: num_authors <= 3, num_training + num_unlabelled + num_test <= 10
		# reduces startup time, useful to search errors
'num_authors' : 10, # number of authors to include into training
'do_fake' : False, # set to true to insert only truely labelled documents
'use_small_cache':False, # set to true to use a small cache. Restrictions: num_authors <= 3, num_training + num_unlabelled + num_test <= 10
		# reduces startup time, useful to search errors
'num_authors': 10, # number of authors to include into training
'num_training': 7, # training documents / author
'num_unlabelled': 240, # unlabelled documents / author
'num_test': 20, # test documents / author
'training_unlabelled': 160, # number of unlabelled documents to examine before re-computing classifiers
'training_iterations': 12, # number of training iterations (=number of re-trained classifiers) 
'num_threads_mining': 1, # number of threads involved for the mining algorithm. A number > 1 significantly increases the memory requirements
'num_threads_classifying': 4, # number of threads involved for the LR classifications
'normalize_features': True, # divides the frequency of a token in a document by the total number of tokens in this document,
			  # similarly the frequency of a character or pos n-gram by the total number of tokens in this document
			  # not mentioned in the paper, but seems useful
'undersample': True, # use an undersampling approach to skewed training databases. Not described in the paper, but
		   # apparently highly useful
'remine_trees': False, # mine the discriminative syntactic tree patterns in each training iteration (i.e. when the syntactic classifier is learnt)
		     # if False, mines in the beginning and then never again
		     # parameter not described in the paper
'min_support': 0, # theta value from the Kim paper. Only mine patterns which occur only in >= min_support sentences.
'num_bins': 10, # n value from the Kim paper. Number of bins to use for the binned information gain. A higher number
	      # approximates the actual information gain better but make the estimates worse, increasing memory and time requirements
'max_embeddable_edges': 2 # k value from the Kim paper. Mine k-ee tree patterns, i.e. patterns with <= k embedded edges
}
glob = globals()
for (key,value) in configuration.items():
	glob[key]=value
if num_authors * num_unlabelled < training_unlabelled * training_iterations:
	raise Exception("Got %u unlabelled documents avaiablable but requested %d for training" % \
		(num_authors*num_unlabelled, training_iterations*training_unlabelled))
