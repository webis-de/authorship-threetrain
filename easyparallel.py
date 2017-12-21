'''
This module is aimed to simplify using true parallelism (not bound by GIL) in nested function calls.
Overcoming GIL requires methods whose input and output can be (easily!) pickled. This may be true for
the functions which do the actual computational work, but is in general wrong for high-level interfaces.

This module assumes that there are specially worker-functions which
	- have input and output picklable
	- the cost of pickling input and output plus starting a new python process is significantly less than the cost of running the function
If it is a class function, the instance it is called with is pickled to.
'''
import threading
import multiprocessing
import os
DEBUG=True
def debugInfo(msg):
	global DEBUG
	if DEBUG:
		print("*** easyparallel ***: "+str(msg))
class ParallelismGroup:
	__slots__ = ['lock','controllock','threads']#
	def __init__(self):#,num_kernels
		#self.num_kernels = num_kernels
		#self.pool = None
		self.lock = threading.Lock()
		self.controllock = threading.Lock()
		self.threads = []
		self.lock.acquire()
	def add_branch(self,fun,*args,**kwargs):
		#if self.pool is None:
		#	self.pool = multiprocessing.Pool(self.num_kernels)
		with self.controllock:
			self.threads.append(OuterThread(fun,args,kwargs,self.lock))#
	def map_branches(self,fun,args):
		for ar in args:
			self.add_branch(fun,ar)
	def map(self,fun,args):
		self.map_branches(fun,args)
		return self.get_results()
	def get_results(self):
		#BLOCKS until all created branches return. Returns the results of the branched function calls in order of calling add_branch (not thread-safe)
		with self.controllock:
			self.lock.release()
			debugInfo('collecting results...')
			for th in self.threads:
				th.join()
			debugInfo('all threads joined')
			#self.pool.close()
			for th in self.threads:
				if th.excepted:
					raise th.exception
			result = [th.result for th in self.threads]
			self.threads = []
			#self.pool = None
			self.lock.acquire()
			return result
class OuterThread(threading.Thread):
	__slots__ = ['fun','args','kwargs','result','excepted','exception','group']#,'pool','lock','local'
	def __init__(self,fun,args,kwargs,lock):#,pool
		self.fun = fun
		self.args = args
		self.kwargs = kwargs
		#self.group=group
		self.lock = lock
		#self.pool = pool
		#self.local = threading.local()
		super().__init__()
		self.start()
		debugInfo('started thread %s' % self)
	def run(self):
		debugInfo('run thread %s' % self)
		self.excepted=False
		try:
			self.result = self.fun(*self.args,**self.kwargs)
			debugInfo('thread %s gave result' % self)
		except Exception as e:
			self.excepted=True
			self.exception = e
			debugInfo('thread %s gave excepted' % self)
ALL_PROCESSES=[]
class OuterProcess(multiprocessing.Process):
	__slots__ = ['fun','args','kwargs','queue']
	def __init__(self,fun,args,kwargs):
		ALL_PROCESSES.append(self)
		self.fun=fun
		self.args=args
		self.kwargs=kwargs
		#self.thread=thread
		self.queue=multiprocessing.Queue()
		super().__init__()
		self.start()
		debugInfo('started process %s from %s' % (self,multiprocessing.current_process()))
	def run(self):
		debugInfo('run process %s' % self)
		ret=None
		try:
			ret={'result':self.fun(*self.args,**self.kwargs),'excepted':False}
			debugInfo('process %s gave result' % self)
		except Exception as e:
			ret= {'excepted':True,'exception':e}
			debugInfo('process %s excepted' % self)
		self.queue.put(ret)
	def fetchResult(self):
		debugInfo('fetch result for process %s' % self)
		#self.join()
		#debugInfo('joined process %s' % self)
		read=self.queue.get()
		debugInfo('got result for process %s' % self)
		if read['excepted']:
			raise read['exception']
		return read['result']
def callWorkerFunction(fun,*args,**kwargs):
	#if DEBUG:
	#	print("callWorkerFunction",fun,args,kwargs)
	thread = threading.current_thread()
	if isinstance(thread,OuterThread):
		#with thread.lock:
		#	result=thread.pool.apply_async(fun,args,kwargs)
		#return result.get()
		with thread.lock:
			proc=OuterProcess(fun,args,kwargs)
		return proc.fetchResult()
	return fun(*args,**kwargs)
'''
class worker(object):
	__slots__=['f']
	def __init__(self,*args):
		print("initiated worker for ",args)
		self.f=args[0]
	def __call__(self,*args,**kwargs):
		if DEBUG:
			print('__call__ed ',self,' with ',args,kwargs)
		return callWorkerFunction(self.f,*args,**kwargs)
'''
def worker(f):
	def result(*args,**kwargs):
		return callWorkerFunction(f,*args,**kwargs)
	return result
if __name__ == '__main__':
	def performance(num):
		callWorkerFunction(complicatedPrint,'hello %d' % num)
		return num
	def complicatedPrint(message):
		print("goint to print ",message," ...")
		os.system('sleep 0.4')
		print(message)
	group = ParallelismGroup()
	print(group.map(performance,range(2)))
	#print([performance(j) for j in range(20,24)])
