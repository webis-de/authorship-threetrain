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
class ParallelismGroup:
	def __init__(self,num_kernels):
		#creates at most `num_kernels` subprocesses
		self.num_kernels = num_kernels
		self.pool = multiprocessing.Pool(num_kernels)
		self.lock = threading.Lock()
		self.threads = []
	def add_branch(self,fun,*args,**kwargs):
		self.threads.append(OuterThread(fun,args,kwargs,self.lock,self.pool))
	def map_branches(self,fun,args):
		for ar in args:
			self.add_branch(fun,ar)
	def map(self,fun,args):
		self.map_branches(fun,args)
		return self.get_results()
	def get_results(self):
		#BLOCKS until all created branches return. Returns the results of the branched function calls in order of calling add_branch (not thread-safe)
		for th in self.threads:
			th.join()
		for th in self.threads:
			if th.excepted:
				raise th.exception
		result = [th.result for th in self.threads]
		self.threads = []
		return result
class OuterThread(threading.Thread):
	def __init__(self,fun,args,kwargs,lock,pool):
		self.fun = fun
		self.args = args
		self.kwargs = kwargs
		self.lock = lock
		self.pool = pool
		self.local = threading.local()
		super().__init__()
		self.start()
	def run(self):
		self.excepted=False
		try:
			self.result = self.fun(*self.args,**self.kwargs)
		except Exception as e:
			self.excepted=True
			self.exception = e
def callWorkerFunction(fun,*args,**kwargs):
	thread = threading.current_thread()
	if isinstance(thread,OuterThread):
		thread.lock.acquire()
		result = thread.pool.apply_async(fun,args,kwargs)
		thread.lock.release()
		return result.get()
	return fun(*args,**kwargs)
if __name__ == '__main__':
	def performance(num):
		callWorkerFunction(complicatedPrint,'hello %d' % num)
		return num
	def complicatedPrint(message):
		print("goint to print ",message," ...")
		os.system('sleep 4')
		print(message)

	group = ParallelismGroup(4)
	print(group.map(performance,range(12)))
	print([performance(j) for j in range(20,24)])
