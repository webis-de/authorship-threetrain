import features
import json
import diskdict
import os
import os.path
import config
#from cached_property import cached_property
from werkzeug import cached_property
#imports a PAN-corpus into a features.documentbase
class tiraInterface:
	#BASE_FOLDER='/media/training-datasets/authorship-attribution/'
	def __init__(self,input_dataset,run,outdir,functionCollection=None):
		self.input_dataset = input_dataset
		self.run = run
		self.outdir = outdir
		self.functionCollection = functionCollection
	def loadCorpus(self):
		#folder should be a readable folder containing a file called 'meta-file.json'
		#returns a tuple trainingDocumentbase,unknownDocumentbase of the training and unlabelled documents.
		folder=config.tira_base_directory+'/'+self.input_dataset+'/'
		with open(folder+'meta-file.json','rt') as f:
			metadata = json.load(f)
		encoding = metadata['encoding']
		def readfile(filename):
			with open(filename,'rt',encoding=encoding) as f:
				return f.read()
		author_names = [auth['author-name'] for auth in metadata['candidate-authors']]
		docs = []
		for author in author_names:
			documents = os.listdir(folder+author)
			docs += [features.document(readfile(folder+author+'/'+doc),author) for doc in documents]
		training_docbase = features.documentbase(docs)
		unknown_paths = [folder+metadata['folder']+'/'+doc['unknown-text'] for doc in metadata['unknown-texts']]
		unknown_docbase = features.documentbase([features.document(readfile(p)) for p in unknown_paths])
		if self.functionCollection is not None:
			training_docbase.functionCollection = self.functionCollection
			unknown_docbase.functionCollection = self.functionCollection
		self._unknown_paths = {d.identifier: path for (d,path) in zip(unknown_docbase.documents, unknown_paths)}
		return training_docbase,unknown_docbase
	def writeResults(self,unknown_docbase, prediction):
		print("prediction: ", prediction)
		outdir=os.path.normpath(self.outdir+'/')+'/'
		os.mkdirs(outdir,exist_ok=True)
		answers = []
		for document,pred in zip(unknown_docbase.documents, prediction):
			answers.append({'unknown_text': os.path.basename(self._unknown_paths[document.identifier]), \
					'author': str(pred),
					'score': 1})
		with open(outdir+'answers.json','wt') as f:
			json.dump({'answers': answers}, f)
	@cached_property
	def workingDirectory(self):
		return './'+self.input_dataset+'/'
	def prepareWorkingDirectory(self):
		try:
			os.mkdir(self.workingDirectory)
		except FileExistsError:
			pass
	@cached_property
	def stanford_db(self):
		return self.workingDirectory + 'prepared-stanford-trees.db'
	@cached_property
	def tokens_db(self):
		return self.workingDirectory + 'prepared-tokens.db'
	@cached_property
	def pos_db(self):
		return self.workingDirectory + 'prepared-pos-tags.db'
	@cached_property
	def c_syntax_tree_db(self):
		return self.workingDirectory + 'prepared-c-syntax-trees.db'
	@cached_property
	def model_lex(self):
		return self.workingDirectory + 'lexical-view-model'
	@cached_property
	def model_chr(self):
		return self.workingDirectory + 'character-view-model'
	@cached_property
	def model_syn(self):
		return self.workingDirectory + 'syntactic-view-model'
	@cached_property
	def model_kim(self):
		return self.workingDirectory + 'kim-model'
	def __enter__(self):
		self._entered=[]
		stanford_dict = diskdict.DiskDict(self.stanford_db)
		self._entered.append(stanford_dict.__enter__())
		tokens_dict = diskdict.DiskDict(self.tokens_db)
		self._entered.append(tokens_dict.__enter__())
		pos_dict = diskdict.DiskDict(self.pos_db)
		self._entered.append(pos_dict.__enter__())
		c_syntax_tree_dict = diskdict.DiskDict(self.c_syntax_tree_db)
		self._entered.append(c_syntax_tree_dict.__enter__())
		self.functionCollection.getFunction(features.stanfordTreeDocumentFunction).setCacheDict(stanford_dict)
		self.functionCollection.getFunction(features.tokensDocumentFunction).setCacheDict(tokens_dict)
		self.functionCollection.getFunction(features.posDocumentFunction).setCacheDict(pos_dict)
		self.functionCollection.getFunction(features.stDocumentDocumentFunction).setCacheDict(c_syntax_tree_dict)
	def __exit__(self,*args):
		if not hasattr(self,'_entered'):
			return
		for handler in self._entered:
			handler.__exit__(*args)
		self._entered=[]
