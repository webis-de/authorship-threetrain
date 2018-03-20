import features
import diskdict
class cacheEntry:
	def __init__(self,functionClass, filename):
		self.functionClass=functionClass
		self.filename=filename
class cache:
	def __init__(self, functionCollection):
		self.functionCollection=functionCollection
		self.entries=[]
	def setCacheFile(self, functionClass, filename):
		self.entries.append(cacheEntry(functionClass,filename))
	def __enter__(self):
		for entry in self.entries:
			print("open %s" % entry.filename)
			entry.diskdict=diskdict.DiskDict(entry.filename)
			entry.diskdict.__enter__()
			self.functionCollection.getFunction(entry.functionClass).setCacheDict(entry.diskdict)
		return self
	def __exit__(self,*args):
		for entry in self.entries:
			entry.diskdict.__exit__(*args)
