#aimed to provide the same functionality as shelve with arbitrary picklable keys.
import sqlite3
import zlib
from collections import MutableMapping
import pickle
import itertools
hashfunc = zlib.adler32
class DiskDict(MutableMapping):
	__slos__ = ['connection','cursor','tablename','requested_name','_keys','memory_cache']
	def __init__(self,filename,tablename='records'):
			# use no untrusted value for `tablename`
		self.connection = sqlite3.connect(filename)
		self.cursor = self.connection.cursor()
		self.tablename = tablename
		self.requested_name = tablename+'__requested__'
		self.cursor.execute('CREATE TABLE IF NOT EXISTS `%s` (`py_hash` INT KEY, `py_key` BLOB, `py_value` BLOB)' % tablename)
		self.cursor.execute('CREATE TEMPORARY TABLE IF NOT EXISTS `%s` (`py_hash` INT KEY, `py_key` BLOB)' % self.requested_name)
		self.cursor.execute('SELECT `py_key` FROM `%s`' % tablename)
		self._keys = [pickle.loads(row[0]) for row in self.cursor.fetchall()]
		self.memory_cache = {}
	def __iter__(self):
		return iter(self._keys)
	def __len__(self):
		return len(self._keys)
	def __contains__(self,key):
		return key in self._keys
	def _fetchMany(self,pickled,hashes):
		if not pickled:
			return []
		#self.cursor.execute('DELETE FROM `%s`' % self.requested_name)
		query='INSERT INTO `%s` (`py_hash`,`py_key`) VALUES (?,?)'%self.requested_name
		args =zip(hashes,pickled) 
		self.cursor.executemany(query,args)
		self.connection.commit()
		self.cursor.execute('SELECT `py_value` FROM `%s` INNER JOIN `%s` USING (`py_hash`,`py_key`)' % (self.requested_name,self.tablename))
		#result = [pickle.loads(row[0]) for row in self.cursor.fetchall()] # works but for some reason produces MANY blocks of 52 bytes.
		fetched = self.cursor.fetchall()
		column = [row[0] for row in fetched]
		result = [pickle.loads(entry) for entry in column]
		self.cursor.execute('DELETE FROM `%s`' % self.requested_name)
		self.connection.commit()
		return result
	def fetchMany(self,keys):
		keys = [k for k in keys if k in self._keys]
		pickled = [pickle.dumps(key) for key in keys]
		hashes = [hashfunc(p) for p in pickled]
		return self._fetchMany(pickled,hashes)
	def values(self):
		return self.fetchMany(self._keys)
	def moveToMemory(self,keys):
		keys = [k for k in keys if k in self._keys]
		pickled = [pickle.dumps(key) for key in keys]
		hashes = [hashfunc(p) for p in pickled]
		mems = []
		for h in hashes:
			if h in self.memory_cache:
				mem = self.memory_cache[h]
			else:
				mem={}
				self.memory_cache[h]=mem
			mems.append(mem)
		useful = [(p,h,m) for (p,h,m) in zip(pickled,hashes,mems) if p not in m]
		results = self._fetchMany([p for (p,h,m) in useful],[h for (p,h,m) in useful])
		for u,r in zip(useful,results):
			p,h,m = u
			m[p] = r
	def removeFromMemory(self,key):
		pickled = pickle.dumps(key)
		h = hashfunc(pickled)
		if not h in self.memory_cache:
			return
		mem=self.memory_cache[h]
		if not pickled in mem:
			return
		del mem[pickled]
		if not mem:
			del self.memory_cache[h]
	def showMemoryStatistics(self):
		print("DiskDict: Remembered %d values" % (sum(len(v) for v in self.memory_cache.values())))
	def __getitem__(self,key):
		if not key in self._keys:
			raise KeyError
		pickled = pickle.dumps(key)
		h = hashfunc(pickled)
		if h in self.memory_cache:
			mem = self.memory_cache[h]
			if pickled in mem:
				return mem[pickled]
		self.cursor.execute('SELECT `py_value` FROM `%s` WHERE `py_hash` == ? AND `py_key` == ?' % self.tablename, (h,pickled))
		return pickle.loads(self.cursor.fetchone()[0])
	def __setitem__(self,key,value):
		pickled = pickle.dumps(key)
		h=hashfunc(pickled)
		if h in self.memory_cache:
			mem = self.memory_cache[h]
			if pickled in mem:
				mem[pickled]=value
		if key in self._keys:
			self.cursor.execute('UPDATE `%s` SET `py_value` = ? WHERE `py_hash` == ? AND `py_key`== ?' % self.tablename,\
				(pickle.dumps(value),h,pickled))
		else:
			self.cursor.execute('INSERT INTO `%s` (`py_hash`,`py_key`,`py_value`) VALUES (?,?,?)' % self.tablename,\
				(h,pickled,pickle.dumps(value)))
			self._keys.append(key)
	def __delitem__(self,key):
		if not key in self._keys:
			raise KeyError
		pickled = pickle.dumps(key)
		h=hashfunc(pickled)
		if h in self.memory_cache:
			mem = self.memory_cache[h]
			if pickled in mem:
				del mem[pickled]
				if not mem:
					del self.memory_cache[h]
		self.cursor.execute('DELETE FROM `%s` WHERE `py_hash` == ? AND `py_key == ?`' % self.tablename, (h,pickled))
		self.keys.remove(key)
	def get(self,key,default=None):
		if key in self:
			return self[key]
		return default
	def __enter__(self):
		return self
	def __exit__(self,type,value,traceback):
		self.close()
	def close(self):
		if self.cursor is not None:
			self.connection.commit()
			self.cursor.close()
			self.cursor=None
			self.connection.close()
			self.connection=None
	def __del__(self):
		self.close()
if __name__ == '__main__':
	import tracemalloc
	import random
	tracemalloc.start(2014)
	with DiskDict('examplediskdict') as d:
		print("found these keys: ",','.join(repr(x) for x in d.keys()))
		print("found these values",','.join(repr(x) for x in d.values()))
		d[len(d)] = random.random()
	for stat in tracemalloc.take_snapshot().statistics('traceback')[:5]:
		print(stat)
		prevLine=None
		for line in stat.traceback.format():
			if line is prevLine:
				continue
			print(line)
			prevLine = line

