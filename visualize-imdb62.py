import imdb62
import features
import tsne
import numpy as np
import pylab
import diskdict

indices=[]
for i in range(4):
	indices += list(range(i*1000,i*1000+100))
database=imdb62.documentbase.subbase(indices)
functionCollection=imdb62.functionCollection
characterFeatures=None
if __name__ == '__main__':
	with imdb62.cache:
		#view=features.characterView([3])
		#view=features.lexicalView()
		view=features.posView([3])
		view.functionCollection = functionCollection
		print("got lexical view")
		features=view.getFeature(database).getValuev(database.documents)
		print("got character features")
		maxValue=max((max(x) for x in features))
X=np.array(features)/maxValue
print(X)
Y=tsne.tsne(X)
'''
Y=np.loadtxt('reduced-dimensions')
'''
labels=[d.author for d in database.documents]
Y=Y[:800,:]
labels=labels[:800]
pylab.scatter(Y[:,0], Y[:,1], 20, labels)
pylab.savefig('imdb62-visualization.png')
pylab.show()
