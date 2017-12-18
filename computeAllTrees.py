import imdb62
import easyparallel
num_threads = 4 # set to 1 if you use virt-sandbox
group = easyparallel.ParallelismGroup()
chunksize=40
for pos in range(0,len(imdb62.documentbase.documents),chunksize*num_threads):
	for i in range(num_threads):
		group.add_branch(imdb62.computeStanfordTrees,range(pos+chunksize*i, pos+chunksize*(i+1)))
	group.get_results()
	if imdb62.cacheUpdateNeeded:
		imdb62.writeCache()
