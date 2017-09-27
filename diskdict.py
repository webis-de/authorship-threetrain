#aimed to provide the same functionality as shelve with arbitrary picklable keys.
import sqlite3
import zlib
from collections import MutableMapping
import pickle
import random
hashfunc = zlib.adler32
class DiskDict(MutableMapping):
	def __init__(self,filename,tablename='records'):
			# use no untrusted value for `tablename`
		self.connection = sqlite3.connect(filename)
		self.cursor = self.connection.cursor()
		self.tablename = tablename
		self.cursor.execute('CREATE TABLE IF NOT EXISTS `%s` (`py_hash` INT KEY, `py_key` BLOB, `py_value` BLOB)' % tablename)
		self.cursor.execute('SELECT `py_key` FROM `%s`' % tablename)
		self._keys = [pickle.loads(row[0]) for row in self.cursor.fetchall()]
		self.memory_cache = {}
		print("DiskDict: keys: ",repr(self._keys[:10]))
	def __iter__(self):
		return iter(self._keys)
	def __len__(self):
		return len(self._keys)
	def __contains__(self,key):
		return key in self._keys
	def moveToMemory(self,key):
		pickled = pickle.dumps(key)
		h = hashfunc(pickled)
		if h in self.memory_cache:
			mem = self.memory_cache[h]
		else:
			mem={}
			self.memory_cache[h]=mem
		if pickled in mem:
			return
		self.cursor.execute('SELECT `py_value` FROM `%s` WHERE `py_hash` == ? AND `py_key` == ?' % self.tablename, (h,pickled))
		mem[pickled] = pickle.loads(self.cursor.fetchone()[0])
	def removeFromMemory(self,key):
		pickled = pickle.dumps(key)
		h = hashfunc(pickled)
		mem=self.memory_cache[h]
		del mem[pickled]
		if not mem:
			del self.memory_cache[h]
	def __getitem__(self,key):
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
		if key in self._keys:
			self.cursor.execute('UPDATE `%s` SET `py_value` = ? WHERE `py_hash` == ? AND `py_key`== ?' % self.tablename,\
				(pickle.dumps(value),h,pickled))
		else:
			self.cursor.execute('INSERT INTO `%s` (`py_hash`,`py_key`,`py_value`) VALUES (?,?,?)' % self.tablename,\
				(h,pickled,pickle.dumps(value)))
			self._keys.append(key)
	def __delitem__(self,key):
		pickled = pickle.dumps(key)
		h=hashfunc(pickled)
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
			print("DiskDict: closing. self._keys: ",repr(self._keys[:10]))
			self.connection.commit()
			self.cursor.close()
			self.cursor=None
			self.connection.close()
			self.connection=None
	def __del__(self):
		self.close()
if __name__ == '__main__':
	with DiskDict('examplediskdict') as d:
		print("found these keys: ",','.join(repr(x) for x in d.keys()))
		print("found these values",','.join(repr(x) for x in d.values()))
		d[len(d)] = random.random()
