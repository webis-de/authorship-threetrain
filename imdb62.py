import csv
class review:
	byReviewer = {}
	def __init__(self, identifier, revid, itemid, rating, title, content):
		self.identifier = identifier
		self.revid = revid
		self.itemid = itemid
		self.rating=rating
		self.title = title
		self.content = content
		if revid in review.byReviewer:
			review.byReviewer[revid].append(self)
		else:
			review.byReviewer[revid] = [self]
	def __str__(self):
		return "review #%d by user #%d about movie #%d (%f/10):\n%s\n%s" % \
			(self.identifier, self.revid, self.itemid, self.rating, self.title, self.content)
reviews=[]
for line in open("imdb62.txt"):
	line = line.split('\t')
	reviews.append(review(int(line[0]), int(line[1]), int(line[2]), float(line[3]), line[4], line[5]))
