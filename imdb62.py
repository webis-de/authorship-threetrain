import csv
import stanford_parser
import c_syntax_tree as st
import syntax_tree
from werkzeug import cached_property
import faulthandler
from pos import pos_tags
faulthandler.enable()
class review:
	byReviewer = {}
	def __init__(self, identifier, revid, itemid, rating, title, content):
		self.identifier = identifier
		self.revid = revid
		self.itemid = itemid
		self.rating=rating
		self.title = title
		self.content = content
		self.stanfordTrees = None
		if revid in review.byReviewer:
			review.byReviewer[revid].append(self)
		else:
			review.byReviewer[revid] = [self]
	def __str__(self):
		return "review #%d by user #%d about movie #%d (%f/10):\n%s\n%s" % \
			(self.identifier, self.revid, self.itemid, self.rating, self.title, self.content)
	def setStanfordTrees(self,trees):
		print("set trees for review %d" % self.identifier)
		self.stanfordTrees=trees
	def writeTrees(self,stream):
		stream.write(str(len(self.stanfordTrees))+"\n")
		for tree in self.stanfordTrees:
			tree.writeStream(stream)
	def readTrees(self,stream):
		num=int(stream.readline().strip())
		self.stanfordTrees=[]
		for _ in range(num):
			self.stanfordTrees.append(stanford_parser.readTreeFromStream(stream))
	@cached_property
	def tokens(self):
		res = []
		for tree in self.stanfordTrees:
			res += [l.data for l in tree.leaves]
		return res
	@cached_property
	def pos(self):
		res = []
		for tree in self.stanfordTrees:
			res += [l.label for l in tree.leaves]
		return res
	@cached_property
	def stDocument(self):
		return st.document([syntax_tree.stanfordTreeToStTree(t) for t in self.stanfordTrees])
reviews=[]
cacheUpdateNeeded=False
def loadReviews():
	global reviews
	reviews=[]
	for line in open("imdb62.txt"):
		line = line.split('\t')
		reviews.append(review(int(line[0]), int(line[1]), int(line[2]), float(line[3]), line[4], line[5]))
def computeStanfordTrees(indices,overwrite=False):
	global cacheUpdateNeeded
	if not overwrite:
		indices = [i for i in indices if reviews[i].stanfordTrees is None]
	if not indices:
		return
	cacheUpdateNeeded=True
	texts = [reviews[i].content for i in indices]
	results = stanford_parser.parseText(texts)
	assert(len(results) == len(indices))
	for i,trees in zip(indices,results):
		print("call setStanfordTrees for #%d" % i)
		reviews[i].setStanfordTrees(trees)
def writeCache(filename='imdb62_syntaxcache'):
	with open(filename,'wt',encoding='utf8') as f:
		for i,rev in enumerate(reviews):
			if rev.stanfordTrees is not None:
				print("write cache for review #%d" % i)
				f.write(str(i)+"\n")
				rev.writeTrees(f)
def readCache(filename='imdb62_syntaxcache'):
	with open(filename,'rt',encoding='utf8') as f:
		while True:
			line=f.readline()
			if not line:
				return
			index=int(line)
			reviews[index].readTrees(f)
def createStDocumentbase(indices=None):
	selection = reviews if indices is None else [reviews[i] for i in indices]
	selection = [sel for sel in selection if sel.stanfordTrees is not None]
	byReviewer = {}
	for rev in selection:
		if rev.revid in byReviewer:
			byReviewer[rev.revid].append(rev)
		else:
			byReviewer[rev.revid] = [rev]
	#print(review.byReviewer)
	#print(list(review.byReviewer.items())[:10])
	classes = [(reviewer,reviews) for (reviewer,reviews) in byReviewer.items() if reviews]
	#print(classes[:10])
	#classes = [(reviewer,reviews) for (reviewer,reviews) in classes if reviews]
	#print(classes[:10])
	print("%d classes of size" % len(classes), [len(reviews) for (reviewer,reviews) in classes])
	return st.documentbase([st.documentclass([r.stDocument for r in reviews],reviewer) for (reviewer,reviews) in classes])

loadReviews()
try:
	readCache()
	print("read from cache: ", [i for i,rev in enumerate(reviews) if rev.stanfordTrees is not None])
except Exception as e:
	print("Failed to read cache")
	print(e)
	loadReviews()
indices=list(range(40))+list(range(1000,1040))
computeStanfordTrees(indices)
if cacheUpdateNeeded:
	print("write cache...")
	writeCache()
	print("cache written.")
base=createStDocumentbase(indices)
testpattern = st.syntax_tree(16,[]) #particle
testpattern.setExtendable(True)
print(base.support(testpattern))
print(base.conditionalEntropy(testpattern,10))
doc=reviews[0].stDocument
print(doc.frequency(testpattern))
for i,tree in enumerate(doc.trees):
	if tree.patternOccurs(testpattern):
		#tree.print()
		stree = reviews[0].stanfordTrees[i]
		#print(" ".join(x.data for x in stree.leaves))
print("now we go for discrimination...")
result=base.mineDiscriminativePatterns(len(pos_tags),0,10,2)
for tree in result:
	tree.print()
