#aimed to provide the same functionality as shelve with arbitrary picklable keys.
import dbm
from collections import MutableMapping
import pickle
import random
class DiskDict(MutableMapping):
	def __init__(self,filename):
		self.dbm = dbm.open(filename,mode)
		self.mode = mode
		self._keys_changed=False
		#print("DiskDict: opened '%s', found these keys: "%filename,self.dbm.keys())
		if b'keys' in self.dbm:
			self._keys = pickle.loads(self.dbm[b'keys'])
			#print("DiskDict: keys evaluates to ",repr(self._keys))
			#self._keys = [key for key in self._keys if b'item'+pickle.dumps(key) in self.dbm]
			#print("DiskDict: filtered:",self._keys[:10])
		else:
			self._keys = []
	def __iter__(self):
		return iter(self._keys)
	def __len__(self):
		return len(self._keys)
	def __contains__(self,key):
		return key in self._keys
	def __getitem__(self,key):
		dkey = b'item'+pickle.dumps(key)
		return pickle.loads(self.dbm[dkey])
	def __setitem__(self,key,value):
		if not key in self._keys:
			self._keys.append(key)
			self._keys_changed = True
		dkey = b'item'+pickle.dumps(key)
		dvalue = pickle.dumps(value)
		self.dbm[dkey] = dvalue
	def __delitem__(self,key):
		del self.dbm[b'item'+pickle.dumps(key)]
		self.keys.remove(key)
		self._keys_changed = True
	def get(self,key,default=None):
		if key in self:
			return self[key]
		return default
	def __enter__(self):
		return self
	def __exit__(self,type,value,traceback):
		self.close()
	def close(self):
		if self.dbm is not None:
			print("DiskDict: closing. self._keys: ",self._keys[:10])
			if self._keys_changed:
				self.dbm[b'keys'] = pickle.dumps(self._keys)
			print("self.dbm.keys(): ",repr(list(self.dbm.keys())[:10]))
			self.dbm.close()
			self.dbm = None
	def __del__(self):
		self.close()
if __name__ == '__main__':
	with DiskDict('examplediskdict') as d:
		print("found these keys: ",','.join(repr(x) for x in d.keys()))
		print("found these values",','.join(repr(x) for x in d.values()))
	d[len(d)] = random.random()
