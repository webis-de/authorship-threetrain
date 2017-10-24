import random
import numpy
#this configuration file is aimed to produce the best results
configuration = {
'do_fake' : False, # set to true to insert only truely labelled documents
'use_small_cache':False, # set to true to use a small cache. Restrictions: num_authors <= 3, num_training + num_unlabelled + num_test <= 10
		# reduces startup time, useful to search errors
'num_authors': 10, # number of authors to include into training
'num_training': 7, # training documents / author
'num_unlabelled':200 , # unlabelled documents / author
'num_test': 20, # test documents / author
'training_unlabelled': 1, # number of unlabelled documents to examine before re-computing classifiers
'training_iterations': 10, # number of training iterations (=number of re-trained classifiers) 
'num_threads_mining': 4, # number of threads involved for the mining algorithm. A number > 1 significantly increases the memory requirements
'num_threads_classifying': 4, # number of threads involved for the LR classifications. Irrelevant to scikit (apparently)
'normalize_features': False, # divides the frequency of a token in a document by the total number of tokens in this document,
			  # similarly the frequency of a character or pos n-gram by the total number of tokens in this document
			  # not mentioned in the paper, but seems useful
'undersample': True, # use an undersampling approach to skewed training databases. Not described in the paper, but
		   # apparently highly useful when using liblinear
'remine_trees_until': 2, # number of times the syntactic tree patterns are re-mined. Normally, when the classifiers
			 # are trained, completely new trees are mined. This gets expensive (in terms of time and space)
			 # when a lot of documents are available. Therefore, only the first times, new trees are mined
			 # and afterwards, the old trees are re-used. Set to 0 to always re-mine trees. Set to 1 to mine trees exactly once.

'min_support': 0, # theta value from the Kim paper. Only mine patterns which occur only in >= min_support sentences.
'num_bins': 10, # n value from the Kim paper. Number of bins to use for the binned information gain. A higher number
	      # approximates the actual information gain better but make the estimates worse, increasing memory and time requirements
'max_embeddable_edges': 2, # k value from the Kim paper. Mine k-ee tree patterns, i.e. patterns with <= k embedded edges
'use_scikit': True, # set false to use liblinear
'random_seed': 43, # random seed to use; set to None for using the default (and always changing) seed
'scikit_solver': 'saga', #solver to use in sklearn.linear_model.LogisticRegression. Irrelevant if use_scikit=False. Default 'liblinear'
'scikit_fit_intercept': False, #parameter for sklearn.linear_model.LogisticRegression. Irrelevant if use_scikit=False. Default False
'scikit_tolerance': 0.0001, #parameter for sklearn.linear_model.LogisticRegression. Irrelevant if use_scikit=False. Default 0.01
'scikit_multi_class': 'multinomial', #parameter for sklearn.linear_model.LogisticRegression. Must be either 'ovr' (one versus rest) or 'multinomial'.
				#Irrelevant if use_scikit=False. Default 'ovr'
'scikit_balance_classes': False, #whether to balance the classes, so imbalanced training sets (with differing numbers of documents per author) get
				# compensated. Irrelevant if use_scikit=False. Default False. Should be seen as an alternative to undersample.
	#if the default values for the five preceding parameters are chosen, the value of use_scikit should be mostly
	#irrelevant for the outcome of the program (the training process should be identical, the prediction may slightly be altered
	#due to the fact that scikit normalizes probability outcomes to sum up to 1)

'featurelimit_max_character_ngrams': [None,None,None], # limit the character unigrams, bigrams, trigrams etc. to the most frequent ones.
							# Must have three entires either None or a natural number or zero. Defaults to [None,None,None].
							# If n = 1,2,3 and featurelimit_max_character_ngrams[n-1] is None, consider all character n-grams.
							# Otherwise consider only the featurelimit_max_character_ngrams[n-1] most frequent n-grams.
							# Note that only the case n=3 is relevant.
'featurelimit_max_word_unigrams': None, #similar. Defauls to None
'featurelimit_max_pos_ngrams': [None,None,None], #similar. Defauls to [None,None,None]. The cases n=1,2,3 are relevant.

'debug_memory': False, # shows various statistics around memory allocation. Compare the COUNT_MALLOC constant of syntax_tree.c
'tira_base_directory': '.' #change to '/media/training-datasets/authorship-attribution/' when running on actual TIRA computer.
}
glob = globals()
for (key,value) in configuration.items():
	glob[key]=value
if num_authors * num_unlabelled < training_unlabelled * training_iterations:
	raise Exception("Got %u unlabelled documents avaiablable but requested %d for training" % \
		(num_authors*num_unlabelled, training_iterations*training_unlabelled))
config_str = ', '.join(key+': '+str(configuration[key]) for key in sorted(configuration.keys()))
print(config_str)
if random_seed is not None:
	random.seed(random_seed)
	numpy.random.seed(random_seed)
