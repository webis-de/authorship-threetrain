import imdb62
chunksize = 100
for pos in range(0,len(imdb62.reviews),chunksize):
	imdb62.computeStanfordTrees(range(pos, pos+chunksize))
	if imdb62.cacheUpdateNeeded:
		imdb62.writeCache()
