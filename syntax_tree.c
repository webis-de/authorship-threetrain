#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
#include <pthread.h>
typedef int st_label;
#define TREEFLAG_EXTENDABLE_EDGE 1
#define TREEFLAG_PACKED_CHILDREN 2
//#define TREEFLAG_ALREADY_MENTIONED 4
#define TREEFLAG_CANDIDATE 4
#define VALIDATE_EMBEDDINGS

#define COUNT_MALLOCS


struct st_syntax_tree {
	st_label label;
	unsigned int num_children;
	struct st_syntax_tree** children;
	int flags;
	unsigned int bestKnownRefcount;
	struct st_syntax_tree* copyUsedDuringSplitup;
	void* embeddingUsedDuringSplitup;
	struct st_syntax_tree* original;
};
typedef struct st_syntax_tree st_tree;

#ifdef COUNT_MALLOCS

#include <malloc.h>
int num_allocations=0;
int num_trees = 0;
ssize_t allocated_memory=0;
void* getmem(size_t s) {
	__sync_fetch_and_add(&num_allocations,1);
	void* ptr= malloc(s);
	size_t allocated = malloc_usable_size(ptr);
	/*
	if (allocated > s) {
		printf("requested %lu bytes, got %lu\n", s, allocated);
	}
	*/
	__sync_fetch_and_add(&allocated_memory,allocated);
	return ptr;
}
void freemem(void* ptr) {
	__sync_fetch_and_sub(&num_allocations,1);
	__sync_fetch_and_sub(&allocated_memory,malloc_usable_size(ptr));
	free(ptr);
}
void showMemoryInformation() {
	printf("%d memory blocks held with %ld bytes.\n",num_allocations,allocated_memory);
	printf("%d trees held of size %lu + %lu bytes each\n", num_trees, sizeof(st_tree), sizeof(st_tree*));
}
#else
#define getmem malloc
#define freemem free
void showMemoryInformation() {
	printf("memory allocations not tracked.\n");
}
#endif

void st_freeTree(st_tree* t) {
	int i;
	for (i=0; i<t->num_children; i++) {
		st_freeTree((st_tree*) t->children[i]);
	}
	if (t->children != NULL && ! (t->flags & TREEFLAG_PACKED_CHILDREN)) freemem(t->children);
	freemem(t);
#ifdef COUNT_MALLOCS
	__sync_fetch_and_sub(&num_trees,1);
#endif
}
void st_shallowFreeTree(st_tree* t) {
	if (t->children != NULL && ! (t->flags & TREEFLAG_PACKED_CHILDREN)) freemem(t->children);
	freemem(t);
#ifdef COUNT_MALLOCS
	__sync_fetch_and_sub(&num_trees,1);
#endif
}
st_tree* st_createTree(st_label label, unsigned int num_children, st_tree** children) {
	st_tree* result = (st_tree*) getmem(sizeof(st_tree));
	result->label=label;
	result->num_children=num_children;
	result->flags=0;
	result->bestKnownRefcount=0;
	result->copyUsedDuringSplitup=NULL;
	result->embeddingUsedDuringSplitup=NULL;
	result->original=NULL;
	if (num_children != 0) {
		result->children=children;
	} else {
		result->children=NULL;
	}
#ifdef COUNT_MALLOCS
	__sync_fetch_and_add(&num_trees,1);
#endif
	return result;
}
st_tree* st_prepareTree(st_label label, unsigned int num_children) {
	st_tree* result = (st_tree*) getmem(sizeof(st_tree) + sizeof(st_tree*) * num_children);
	result->label=label;
	result->num_children = num_children;
	result->bestKnownRefcount=0;
	result->copyUsedDuringSplitup=NULL;
	result->embeddingUsedDuringSplitup=NULL;
	result->original=NULL;
	if (num_children >0) {
		result->children = (st_tree**) (result+1);
	} else {
		result->children = NULL;
	}
	result->flags = TREEFLAG_PACKED_CHILDREN;
#ifdef COUNT_MALLOCS
	__sync_fetch_and_add(&num_trees,1);
#endif
	return result;
}
void st_setTreeChild(st_tree* parent, unsigned int index, st_tree* child) {
	parent->children[index]=child;
}
void st_setTreeExtendable(st_tree* tree, _Bool isExtendable) {
	if (isExtendable) {
		tree->flags |= TREEFLAG_EXTENDABLE_EDGE;
	} else {
		tree->flags &= ~TREEFLAG_EXTENDABLE_EDGE;
	}
}
void st_printTree(const st_tree* t, unsigned int level) {
	unsigned int i;
	for (i=0; i<level; i++) printf("  ");
	if (t->flags & TREEFLAG_EXTENDABLE_EDGE) printf("(extendable) ");
	printf("%d\n", t->label);
	for (i=0; i<t->num_children;i++) {
		st_printTree(t->children[i],level+1);
	}
}
st_label st_treeGetLabel(const st_tree* tree){return tree->label;}
unsigned int st_treeNumOfChildren(const st_tree* tree) {return tree->num_children;}
st_tree* st_treeGetChild(const st_tree* tree,unsigned int index) {return tree->children[index];}
_Bool st_treeGetExtendable(const st_tree* tree){return (tree->flags & TREEFLAG_EXTENDABLE_EDGE)!=0;}
_Bool st_canMatchPattern(const st_tree* pattern, const st_tree* tree) {
	if (pattern->label == tree->label) {
		int pchildnum, tchildnum;
		tchildnum=0;
		for (pchildnum=0;pchildnum<pattern->num_children;pchildnum++) {
			st_tree* pchild = pattern->children[pchildnum];
			while (tchildnum < tree->num_children && !st_canMatchPattern(pchild, tree->children[tchildnum])) {
				tchildnum++;
			}
			if (tchildnum >= tree->num_children) return false;
			tchildnum++;
		}
		return true;
	} else if (pattern->flags & TREEFLAG_EXTENDABLE_EDGE) {
		int i;
		for (i=0;i < tree->num_children; i++) {
			if (st_canMatchPattern(pattern, tree->children[i])) return true;
		}
	}
	return false;
}
unsigned int st_countNodes(const st_tree* tree) {
	unsigned int result = 1, i;
	for (i=0; i<tree->num_children;i++) {
		result += st_countNodes(tree->children[i]);
	}
	return result;
}
const st_tree** st_listNodes(const st_tree* tree, const st_tree** nodelist) { // not tested!
	//returns an array of pointers to the tree's nodes, in breadth-first manner.
	//nodelist must be a writeable memory region of size sizeof(st_tree*) * st_countNodes(tree)
	//returns nodelist + countNodes(tree)
	nodelist[0] = tree;
	nodelist += 1;
	int i;
	for (i=0; i < tree->num_children; i++) {
		nodelist = st_listNodes(tree->children[i], nodelist);
	}
	return nodelist;
}
st_tree* st_deepCopyTree(const st_tree* tree) {
	st_tree* result = st_prepareTree(tree->label, tree->num_children);
	result->flags |= tree->flags;
	int i;
	for (i=0; i<tree->num_children;i++) {
		st_tree* ch = st_deepCopyTree(tree->children[i]);
		result->children[i]=ch;
	}
	result->bestKnownRefcount = tree->bestKnownRefcount;
	return result;
}
typedef struct {
	unsigned int num_trees;
} st_document;
//the convention is that directly after the document, a list of `num_trees` entries of type st_tree* follows.
void st_shallowFreeDocument(st_document* doc) {
	freemem(doc);
}
st_document* st_prepareDocument(unsigned int num_trees) {
	st_document* result = (st_document*) getmem(sizeof(st_document) + num_trees * sizeof(st_tree*));
	result->num_trees = num_trees;
	return result;
}
void st_documentSetTree(st_document* doc, unsigned int index, st_tree* const tree) {
	((st_tree**) (void*) (doc+1))[index] = tree;
}
unsigned int st_occuringTrees(const st_tree* pattern, const st_document* doc) {
	unsigned int result = 0,i;
	for (i=0; i < doc->num_trees; i++) {
		if (st_canMatchPattern(pattern, ((st_tree**) (doc+1))[i])) result++;
	}
	return result;
}
double st_frequency(const st_tree* pattern, const st_document* doc) {
	return ((double) st_occuringTrees(pattern, doc))/((double) doc->num_trees);
}
typedef struct {
	unsigned int num_documents;
} st_documentclass;
//the convention is that it follows `num_documents` pointers to the documents.
void st_freeDocumentClass(st_documentclass* class) {
	freemem(class);
}
st_documentclass* st_prepareDocumentClass(unsigned int num_documents) {
	st_documentclass* result = getmem(sizeof(st_documentclass) + num_documents * sizeof(st_document*));
	result->num_documents = num_documents;
	return result;
}
void st_setDocumentInClass(st_documentclass* class, unsigned int index, st_document* const doc) {
	( (st_document**) (class+1))[index]=doc;
}
typedef struct {
	unsigned int num_classes;
	unsigned int num_documents;
} st_documentbase;
//the convention is that it follows `num_classes` pointers to the document classes.
void st_freeDocumentBase(st_documentbase* base) {
	freemem(base);
}
st_documentbase* st_prepareDocumentBase(unsigned int num_classes) {
	st_documentbase* result = getmem(sizeof(st_documentbase) + num_classes * sizeof(st_documentclass*));
	result->num_classes = num_classes;
	return result;
}
void st_setClassInDocumentBase(st_documentbase* base, unsigned int index, st_documentclass* const class) {
	( (st_documentclass**) (base+1))[index]=class;
}
void st_completeDocumentBaseSetup(st_documentbase* base) {
	base->num_documents=0;
	unsigned int i;
	for (i=0; i<base->num_classes; i++) {
		base->num_documents += ((st_documentclass**) base+1)[i]->num_documents;
	}
}
unsigned int st_support(const st_documentbase* base, const st_tree* pattern) {
	unsigned int result=0,i,j;
	for (i=0; i < base->num_classes;i++) {
		st_documentclass* class = ((st_documentclass**) (base+1))[i];
		for (j=0; j<class->num_documents;j++) {
			result += st_occuringTrees(pattern, ((st_document**) (class+1))[j]);
		}
	}
	return result;
}
double st_conditionalEntropy(const st_documentbase* base, const st_tree* pattern, unsigned int n, double* lowerBound) {
	//if lowerBound != NULL, it must be a valid writeable pointer to which the computed lower bound for all superpatterns is written.
	size_t memorysize = sizeof(unsigned int) * base->num_classes * n;
	unsigned int* frequencyMatrix = getmem(memorysize);
	memset(frequencyMatrix, 0, memorysize);
	unsigned int i,j;
	for (i=0; i<base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (base+1))[i];
		for (j=0; j<class->num_documents; j++) {
			double freq = st_frequency(pattern, ((st_document**) (class+1))[j]);
			int index = freq*n;
			if (index < 0) {
				index=0;
			}else if(index >= n) {
				index=n-1;
			}
			frequencyMatrix[index*base->num_classes+i]++;
		}
	}
	/*
	for (j=0;j<n;j++) {
		for (i=0;i<base->num_classes;i++) {
			printf("%d ",frequencyMatrix[j*base->num_classes+i]);
		}
		printf("\n");
	}
	*/
	double result=0;
	double dinv = 1.0/((double) base->num_documents);
	for (i=0; i<n; i++) {
		unsigned int total=0;
		unsigned int* row = frequencyMatrix + i*base->num_classes;
		for (j=0; j<base->num_classes;j++) total += row[j];
		double factor = 1.0/((double) total);
		for (j=0; j<base->num_classes;j++) {
			double val=row[j];
			if (val != 0) result -= val * dinv * log(val*factor);
		}
	}
	if (lowerBound != NULL) {
		double min=0;
		unsigned int total=0;
		for (i=0; i<base->num_classes;i++) total += frequencyMatrix[i];
		for (i=0; i<base->num_classes;i++) {
			unsigned int extra=frequencyMatrix[base->num_classes +i];
			total += extra;
			frequencyMatrix[i] += extra;
			double val=0;
			for (j=0; j<base->num_classes;j++) {
				double entry=frequencyMatrix[j];
				if (entry != 0) val -= entry * log(entry/total);
			}
			//printf("val: %f\n", val);
			if (i==0 || val<min) min=val;
			total -= extra;
			frequencyMatrix[i] -= extra;
		}
		//printf("min: %f\n", min);
		*lowerBound = min*dinv;
		/*
		if (result > *lowerBound) {
			printf("ERROR detected.\n");
			*lowerBound /= result-result;
		}
		*/
	}
	freemem(frequencyMatrix);
	return result;
}
struct st_partialPatternEmbedding {
	unsigned int classIndex;
	unsigned int documentIndex;
	unsigned int sentenceIndex;
	st_tree** rightPath;
	struct st_partialPatternEmbedding* next; // we agree on the convention that, in the list, classIndex is increasing,
						//then documentIndex is increasing, then sentenceIndex is increasing.
};
typedef struct st_partialPatternEmbedding st_patternEmbedding;
_Bool st_isValidEmbedding(const st_documentbase* base, const st_tree* pattern, const st_patternEmbedding* embedding) {
	unsigned int lc=0, ld=0, ls=0;
	while (embedding != NULL) {
		//printf("about to validate embedding in class %u, document %u, sentence %u\n", embedding->classIndex, embedding->documentIndex, embedding->sentenceIndex);
		if (embedding->classIndex >= base->num_classes || embedding->classIndex < lc) return false;
		st_documentclass* class = ((st_documentclass**) (base+1))[embedding->classIndex];
		if (embedding->documentIndex >= class->num_documents || (embedding->classIndex == lc && embedding->documentIndex < ld)) return false;
		st_document* document = ((st_document**) (class+1))[embedding->documentIndex];
		if (embedding->sentenceIndex >= document->num_trees  ||
			(embedding->classIndex == lc && embedding->documentIndex == ld && embedding->sentenceIndex < ls)) return false;
		if (!st_canMatchPattern(pattern, ((st_tree**) (document+1))[embedding->sentenceIndex])) return false;
		unsigned int i=0;
		const st_tree* node = pattern;
		while (true) {
			if (node->label != embedding->rightPath[i]->label) return false;
			if (i>0 && (node->flags & TREEFLAG_EXTENDABLE_EDGE) == 0) {
				st_tree* parent = embedding->rightPath[i-1];
				if (parent->children[parent->num_children-1] != embedding->rightPath[i]) {
					return false;
				}
			}
			if (node->num_children == 0) break;
			i=i+1;
			node = node->children[node->num_children-1];
		}
		lc = embedding->classIndex;
		ld = embedding->documentIndex;
		ls = embedding->sentenceIndex;
		embedding = embedding->next;
	}
	//printf("validated.\n");
	return true;
}
void st_validateEmbedding(const st_documentbase* base, const st_tree* pattern, const st_patternEmbedding* embedding) {
#ifdef VALIDATE_EMBEDDINGS
	if (!st_isValidEmbedding(base, pattern, embedding)) {
		unsigned int _=((st_tree*) NULL) -> num_children;
		_ = _/_;
	}
#endif
}
unsigned int st_rightPathLength(const st_tree* pattern) {
	unsigned int result = 1;
	while (pattern->num_children >0) {
		result++;
		pattern=pattern->children[pattern->num_children-1];
	}
	return result;
}
st_patternEmbedding* st_copyPatternEmbedding(const st_tree* pattern, const st_patternEmbedding* embedding) {
	if (embedding==NULL) return NULL;
	st_patternEmbedding* result = getmem(sizeof(st_patternEmbedding));
	result->classIndex = embedding->classIndex;
	result->documentIndex = embedding->documentIndex;
	result->sentenceIndex = embedding->sentenceIndex;
	unsigned int length = st_rightPathLength(pattern);
	result->rightPath = getmem(sizeof(st_tree*) * length);
	memcpy(result->rightPath, embedding->rightPath, sizeof(st_tree*)*length);
	result->next = st_copyPatternEmbedding(pattern,embedding->next);
	return result;
}
struct st_patternListEntry {
	st_tree* pattern;
	st_patternEmbedding* embedding;
	unsigned int num_embedded_edges;
	struct st_patternListEntry* pred;
	struct st_patternListEntry* succ;
};
typedef struct st_patternListEntry st_listedPattern;
typedef struct {
	unsigned int length;
	double cachedEntropy;
	st_listedPattern* first;
	st_listedPattern* last;
} st_patternList;
st_patternList* st_createEmptyPatternList() {
	st_patternList* result = getmem(sizeof(st_patternList));
	result->length=0;
	result->cachedEntropy = -1;
	result->first=NULL;
	result->last=NULL;
	return result;
}
void st_patternListInsertFirst(st_patternList* list, st_tree* pattern, unsigned int num_embedded_edges, st_patternEmbedding* embedding) {
	st_listedPattern* link = getmem(sizeof(st_listedPattern));
	link->pattern = pattern;
	link->embedding=embedding;
	link->num_embedded_edges = num_embedded_edges;
	link->pred = NULL;
	if (list->first != NULL) list->first->pred = link;
	link->succ = list->first;
	list->first=link;
	if (list->last == NULL) list->last=link;
	list->length++;
}
void st_patternListInsertLast(st_patternList* list, st_tree* pattern, unsigned int num_embedded_edges, st_patternEmbedding* embedding) {
	st_listedPattern* link = getmem(sizeof(st_listedPattern));
	link->pattern = pattern;
	link->embedding=embedding;
	link->num_embedded_edges = num_embedded_edges;
	link->succ = NULL;
	link->pred = list->last;
	if (list->last != NULL) list->last->succ = link;
	list->last=link;
	if (list->first == NULL) list->first=link;
	list->length++;
}
void st_patternListRemoveFirst(st_patternList* list) {
	st_listedPattern* link = list->first;
	list->first = link->succ;
	if (link->succ == NULL) {
		list->last = NULL;
	} else {
		link->succ->pred = NULL;
	}
	freemem(link);
	list->length--;
}
void st_patternListRemoveLast(st_patternList* list) {
	st_listedPattern* link = list->last;
	list->last = link->pred;
	if (link->pred == NULL) {
		list->first = NULL;
	} else {
		link->pred->succ = NULL;
	}
	freemem(link);
	list->length--;
}
void st_patternListRemoveListed(st_patternList* list, st_listedPattern* remove) {
	if (list->first == remove) {
		list->first = remove->succ;
	} else {
		remove->pred->succ = remove->succ;
	}
	if (list->last == remove) {
		list->last = remove->pred;
	} else {
		remove->succ->pred = remove->pred;
	}
	freemem(remove);
	list->length--;
}
void st_recursiveFreeEmbedding(st_patternEmbedding* embedding) {
	while (embedding != NULL) {
		//printf("about to freemem embedding in class %u, document %u, sentence %u\n", embedding->classIndex, embedding->documentIndex, embedding->sentenceIndex);
		freemem(embedding->rightPath);
		st_patternEmbedding* next = embedding->next;
		freemem(embedding);
		embedding=next;
	}
}
void st_deepCleanupList(st_patternList* list) {
	st_listedPattern* link;
	link=list->first;
	while (link != NULL) {
		st_freeTree(link->pattern);
		//printf("free the candidate %p.\n", link->pattern);
		st_recursiveFreeEmbedding(link->embedding);
		st_listedPattern* tmp=link;
		link=link->succ;
		freemem(tmp);
	}
	list->length=0;
	list->first=NULL;
	list->last=NULL;
}
void st_deepFreeList(st_patternList* list) {
	st_deepCleanupList(list);
	freemem(list);
}
void st_shallowFreeList(st_patternList* list) {
	//frees everything besides the patterns and embeddings
	st_listedPattern* link;
	link=list->first;
	while (link != NULL) {
		st_listedPattern* tmp=link;
		link=link->succ;
		freemem(tmp);
	}
	freemem(list);
}
unsigned int st_listGetLength(const st_patternList* list){return list->length;}
st_listedPattern* st_listGetFirstEntry(const st_patternList* list){return list->first;}
st_listedPattern* st_listedGetNext(const st_listedPattern* listed){return listed->succ;}
st_tree* st_listedGetPattern(const st_listedPattern* listed){return listed->pattern;}

st_tree* st_expandPatternRight(const st_tree* pattern, unsigned int index, st_label label, _Bool embeddable) {
	st_tree* result;
	if (index == 0) {
		result = st_prepareTree(pattern->label, pattern->num_children+1);
		result->children[pattern->num_children] = st_prepareTree(label, 0);
		if (embeddable) result->children[pattern->num_children]->flags |= TREEFLAG_EXTENDABLE_EDGE;
	} else {
		result = st_prepareTree(pattern->label, pattern->num_children);
	}
	result->flags |= pattern->flags;
	unsigned int i;
	for (i=0; i<result->num_children-1; i++) {
		result->children[i] = st_deepCopyTree(pattern->children[i]);
	}
	if (index != 0) {
		result->children[result->num_children-1] = st_expandPatternRight(pattern->children[pattern->num_children-1], index-1, label, embeddable);
	}
	return result;
}
unsigned int st_esupport(const st_documentbase* base, const st_patternEmbedding* embedding) {
	unsigned int result=0;
	int lc,ld,ls,firstLoop=1;
	while (embedding != NULL) {
		if (firstLoop || embedding->classIndex > lc || embedding->documentIndex > ld || embedding->sentenceIndex > ls) {
			result++;
			lc = embedding->classIndex;
			ld = embedding->documentIndex;
			ls = embedding->sentenceIndex;
		}
		embedding = embedding->next;
		firstLoop=0;
	}
	return result;
}

double st_econditionalEntropy(const st_documentbase* base, unsigned int n, double* lowerBound, const st_patternEmbedding* embedding) {
	//if lowerBound != NULL, it must be a valid writeable pointer to which the computed lower bound for all superpatterns is written.
	size_t memorysize = sizeof(unsigned int) * base->num_classes * n;
	unsigned int* frequencyMatrix = getmem(memorysize);
	//printf("allocated this frequency matrix: %p\n", frequencyMatrix);
	memset(frequencyMatrix, 0, memorysize);
	unsigned int i,j;
	int lc=-1,ld=-1,ls=-1;
	st_documentclass* class=NULL;
	st_document* document=NULL;
	unsigned int occurances=0;
	while (embedding != NULL) {
		//for each document in each class, we compute the number of sentences where the pattern is embeddable.
		//class is the class we are watching (=base->classes[lc])
		//document is the document we are watching (=class->documents[ld])
		//ls is the index of the last sentence occured.
		//occurances is the number of occurances in doc counted so far.
		if (lc == -1) {
			for (lc=0; lc<embedding->classIndex; lc++) {
				frequencyMatrix[lc] = ((st_documentclass**) (base+1))[lc]->num_documents;
			}
			frequencyMatrix[lc] += embedding->documentIndex;
		} else if (embedding->classIndex > lc || embedding->documentIndex > ld) {
			unsigned int frequency = (occurances * n)/document->num_trees;
			if (frequency >= n) frequency=n-1;
			frequencyMatrix[frequency*base->num_classes+lc]++;
			occurances=0;
			ld++;
			for (;lc<embedding->classIndex;lc++) {
				class = ((st_documentclass**) (base+1))[lc];
				frequencyMatrix[lc] += class->num_documents-ld;
				ld=0;
			}
			frequencyMatrix[lc] += embedding->documentIndex-ld;
		} else if (embedding->sentenceIndex == ls) {
			embedding = embedding->next;
			continue;
		}
		occurances++;
		lc = embedding->classIndex;
		ld = embedding->documentIndex;
		ls = embedding->sentenceIndex;
		class = ((st_documentclass**) (base+1))[lc];
		document = ((st_document**) (class+1))[ld];
		embedding = embedding->next;
	}
	if (lc != -1) {
		unsigned int frequency = (occurances * n)/document->num_trees;
		if (frequency >= n) frequency=n-1;
		frequencyMatrix[frequency*base->num_classes+lc]++;
		ld++;
		for (;lc<base->num_classes;lc++) {
			class = ((st_documentclass**) (base+1))[lc];
			frequencyMatrix[lc] += class->num_documents-ld;
			ld=0;
		}
	} else {
		for (lc=0; lc<base->num_classes;lc++) {
			frequencyMatrix[lc] = ((st_documentclass**) (base+1))[lc]->num_documents;
		}
	}
/*
	for (j=0;j<n;j++) {
		for (i=0;i<base->num_classes;i++) {
			printf("%d ",frequencyMatrix[j*base->num_classes+i]);
		}
		printf("\n");
	}
*/
	double result=0;
	double dinv = 1.0/((double) base->num_documents);
	for (i=0; i<n; i++) {
		unsigned int total=0;
		unsigned int* row = frequencyMatrix + i*base->num_classes;
		for (j=0; j<base->num_classes;j++) total += row[j];
		double factor = 1.0/((double) total);
		for (j=0; j<base->num_classes;j++) {
			double val=row[j];
			if (val != 0) result -= val * dinv * log(val*factor);
		}
	}
	//printf("result: %.18f\n", result);
	if (lowerBound != NULL) {
		double min=0;
		unsigned int total=0;
		for (i=0; i<base->num_classes;i++) total += frequencyMatrix[i];
		for (i=0; i<base->num_classes;i++) {
			unsigned int extra=frequencyMatrix[base->num_classes +i];
			total += extra;
			frequencyMatrix[i] += extra;
			double val=0;
			for (j=0; j<base->num_classes;j++) {
				double entry=frequencyMatrix[j];
				if (entry != 0) val -= entry * log(entry/total);
			}
			//printf("val: %f, min: %f\n", val, min);
			if (i==0 || val<min) min=val;
			total -= extra;
			frequencyMatrix[i] -= extra;
		}
		*lowerBound = min*dinv;
		/*
		printf("lowerBound: %.18f\n", *lowerBound);
		if (*lowerBound > result+1e-12) {
			printf("ERROR detected.\n");
			*lowerBound = ((double*) NULL)[0];
		}
		*/
	}
	//printf("about to free this frequency matrix: %p\n", frequencyMatrix);
	freemem(frequencyMatrix);
	return result;
}

typedef struct {
	st_documentbase* base;
	st_patternList**** bestKnown; // class -> document -> sentence -> st_patternList*
	st_patternList* candidates;
	unsigned int numLabels;// we agree that all occuring labels are 0,...,numLabels-1.
	unsigned int supportLowerBound;//bound theta for frequent patterns
	unsigned int n;//number of bins
	unsigned int k;//max. number of embedded edges
} st_miningState;
_Bool st_isValidPattern(const st_miningState* state, const st_tree* pattern) {
	if (pattern->label < 0 || pattern->label >= state->numLabels) return false;
	unsigned int i;
	for (i=0; i<pattern->num_children; i++) {
		if (!st_isValidPattern(state, pattern->children[i])) return false;
	}
	return true;
}
_Bool st_isValidPatternList(const st_miningState* state, const st_patternList* list) {
	unsigned int trueLength = 0;
	const st_listedPattern* entry;
	for (entry = list->first; entry != NULL; entry = entry->succ) {
		trueLength++;
		if (!st_isValidEmbedding(state->base, entry->pattern, entry->embedding)) return false;
		if (!st_isValidPattern(state, entry->pattern)) return false;
	}
	return (list->length == trueLength);
}
_Bool st_isValidState(const st_miningState* state) {
	unsigned int i,j,k;
	for (i=0; i<state->base->num_classes; i++) {
		const st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		const st_patternList*** classBestKnown = (const st_patternList***) state->bestKnown[i];
		for (j=0; j<class->num_documents; j++) {
			const st_document* document = ((st_document**) (class+1))[j];
			const st_patternList** documentBestKnown =(const st_patternList**) classBestKnown[j];
			for (k=0; k<document->num_trees; k++) {
				//st_deepFreeList(documentBestKnown[k]);
				const st_patternList* list = (const st_patternList*) documentBestKnown[k];
				if (!st_isValidPatternList(state, list)) return false;
				//printf("validated bestKnown of class %u, document %u, sentence %u.\n", i, j, k);
			}
		}
	}
	if (!st_isValidPatternList(state, state->candidates)) return false;
	//printf("validated the candidates.\n");
	return true;
}
void st_validateState(const st_miningState* state) {
	if (!st_isValidState(state)) {
		state = ((st_miningState**) NULL)[0];
	}
}
st_miningState* st_createMiningState(st_documentbase* base, unsigned int numLabels, unsigned int supportLowerBound, unsigned int n, unsigned int kee) {
	unsigned int i,j,k;
	st_miningState* result = getmem(sizeof(st_miningState));
	result->base=base;
	result->bestKnown = getmem(sizeof(st_patternList***) * base->num_classes);
	for (i=0; i<base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (base+1))[i];
		st_patternList*** classBestKnown = getmem(sizeof(st_patternList**) * class->num_documents);
		result->bestKnown[i] = classBestKnown;
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown = getmem(sizeof(st_patternList*) * document->num_trees);
			classBestKnown[j]=documentBestKnown;
			for (k=0; k<document->num_trees; k++) {
				documentBestKnown[k] = st_createEmptyPatternList();
			}
		}
	}
	result->candidates = st_createEmptyPatternList();
	result->numLabels = numLabels;
	result->supportLowerBound = supportLowerBound;
	result->n=n;
	result->k=kee;
	st_validateState(result);
	return result;
}
void st_insertPattern(st_miningState* state, st_tree* pattern, unsigned int num_embedded_edges, st_patternEmbedding* embedding) {
	//after calling this function, pattern and embedding are either freed, or they occur
	//once in state->candidates and `pattern->bestKnownRefcount` times in state->bestKnown.
	/*
	st_validateEmbedding(state->base, pattern, embedding);
	//st_validateState(state);
	printf("asked to insert this pattern:\n");
	st_printTree(pattern, 0);
	unsigned int numEmbeddings=0;
	st_patternEmbedding* tmp = embedding;
	while (tmp != NULL) {
		numEmbeddings++;
		tmp=tmp->next;
	}
	printf("has %u embeddings.\n", numEmbeddings);
	*/
	if (st_esupport(state->base, embedding) < state->supportLowerBound) {
		st_freeTree(pattern);
		//printf("free the candidate %p.\n", pattern);
		st_recursiveFreeEmbedding(embedding);
		return;
	}
	//if (numEmbeddings > 100000) numEmbeddings=( (st_tree*) NULL) -> num_children;
	//printf("support bound passed.\n");
	double estimate;
	double entropy = st_econditionalEntropy(state->base, state->n, &estimate, embedding);
	_Bool candidate=false;
	st_patternEmbedding* emb;
	unsigned int num_embeddings=0;
	for (emb = embedding; emb != NULL; emb = emb->next) {
		num_embeddings++;
		//st_validateState(state);
		st_patternList* bestKnown = state->bestKnown[emb->classIndex][emb->documentIndex][emb->sentenceIndex];
		if (bestKnown->last != NULL && bestKnown ->last->pattern == pattern) continue;
		/*
		printf("iterate embedding in class %u, document %u, sentence %u.\n",emb->classIndex, emb->documentIndex, emb->sentenceIndex);
		printf("entropy: %f, estimate: %f, cached: %f\n", entropy, estimate, bestKnown->cachedEntropy);
		*/
		_Bool insert=false;
		if (bestKnown->length == 0) {
			insert=true;
		} else if (bestKnown->cachedEntropy > entropy) {
			//st_deepCleanupList(bestKnown);
			st_listedPattern* entry;
			for (entry= bestKnown->first;entry!=NULL;) {
				/*if (!st_isValidEmbedding(state->base, entry->pattern, entry->embedding)) {
					embedding=entry->embedding;
					printf("ERROR detected in embedding for class %u, document %u, sentence %u.\n", embedding->classIndex, embedding->documentIndex, embedding->sentenceIndex);
					printf("pattern:\n");
					st_printTree(entry->pattern,0);
					printf("embedding:\n");
					st_printTree(embedding->rightPath[0],0);
					pattern = ((st_listedPattern*) NULL)->pattern;
				}
				if (entry->pattern->bestKnownRefcount == 0) {
					printf("ERROR detected.\n");
					pattern = ((st_listedPattern*) NULL)->pattern;
				}*/
				if (entry->pattern->bestKnownRefcount <= 1 && (entry->pattern->flags & TREEFLAG_CANDIDATE) == 0) {
					st_freeTree(entry->pattern);
					//printf("free the candidate %p.\n", entry->pattern);
					st_recursiveFreeEmbedding(entry->embedding);
				} else {
					entry->pattern->bestKnownRefcount--;
				}
				entry=entry->succ;
				st_patternListRemoveFirst(bestKnown);
				//if (!st_isValidPatternList(state, bestKnown)) printf("ERROR detected after delete.\n");
			}
			insert=true;
		} else if (bestKnown->cachedEntropy == entropy) {
			insert=true;
		} else if (bestKnown->cachedEntropy >= estimate) {
			candidate=true;
		}
		//if (!st_isValidPatternList(state, bestKnown)) printf("ERROR detected before insert.\n");
		if (insert) {
			//if (pattern==NULL) pattern=st_expandPatternRight(oldPattern, position, label, embeddable);
			/*printf("The pattern\n");
			st_printTree(pattern, 0);
			printf("is the best known for class %u, document %u, sentence %u.\n", emb->classIndex, emb->documentIndex, emb->sentenceIndex);*/
			st_patternListInsertLast(bestKnown, pattern, num_embedded_edges,embedding);
			//if (!st_isValidPatternList(state, bestKnown)) printf("ERROR detected after insert.\n");
			bestKnown->cachedEntropy = entropy;
			candidate=true;
			pattern->bestKnownRefcount++;
		}
		//if (!st_isValidPatternList(state, bestKnown)) printf("ERROR detected before validation.\n");
		//if (!st_isValidPatternList(state, state->candidates)) printf("ERROR detected in CANDIDATES.\n");
		//st_validateState(state);
	}
	//printf("\n");
	if (candidate) {
		//if (pattern==NULL) pattern=st_expandPatternRight(oldPattern, position, label, embeddable);
		/*
		printf("We insert the following pattern:\n");
		st_printTree(pattern, 0);
		printf("entropy: %f, estimated: %f, embeddings: %u.\n", entropy, estimate, num_embeddings);
		*/
		st_patternListInsertLast(state->candidates, pattern, num_embedded_edges, embedding);
		pattern->flags |= TREEFLAG_CANDIDATE;
		//printf("insert the candidate %p.\n", pattern);
	} else {
		st_freeTree(pattern);
		//printf("free the candidate (instead of insert) %p.\n", pattern);
		st_recursiveFreeEmbedding(embedding);
	}
	//st_validateState(state);
}

void st_appendSingletonEmbeddings(st_tree* tree, st_label label,
		unsigned int classIndex, unsigned int documentIndex, unsigned int sentenceIndex, st_patternEmbedding** embedding) {
	if (tree->label == label) {
		st_patternEmbedding* emb = getmem(sizeof(st_patternEmbedding));
		emb->classIndex = classIndex;
		emb->documentIndex = documentIndex;
		emb->sentenceIndex = sentenceIndex;
		emb->rightPath = getmem(sizeof(st_tree*));
		emb->rightPath[0] = tree;
		emb->next = *embedding;
		*embedding=emb;
	}
	unsigned int i;
	for (i=0; i<tree->num_children;i++) {
		st_appendSingletonEmbeddings(tree->children[i], label, classIndex, documentIndex, sentenceIndex, embedding);
	}
}
void st_insertSingletonCandidate(st_miningState* state, st_label label) {
	st_tree* pattern = st_prepareTree(label,0);
	pattern->flags |= TREEFLAG_EXTENDABLE_EDGE;
	st_patternEmbedding* embedding = NULL;
	int classIndex, documentIndex, sentenceIndex;
	for (classIndex = state->base->num_classes-1; classIndex >= 0; classIndex--) {
		st_documentclass* class = ((st_documentclass**)(state->base+1))[classIndex];
		for (documentIndex = class->num_documents-1; documentIndex >= 0; documentIndex--) {
			st_document* document = ((st_document**)(class+1))[documentIndex];
			for (sentenceIndex = document->num_trees-1; sentenceIndex >= 0; sentenceIndex--) {
				st_tree* tree = ((st_tree**)(document+1))[sentenceIndex];
				st_appendSingletonEmbeddings(tree, label, classIndex, documentIndex, sentenceIndex, &embedding);
			}
		}
	}
	//st_patternListInsertLast(state->candidates, pattern, 0, embedding);
	st_insertPattern(state, pattern, 0, embedding);
}
void st_populateMiningState(st_miningState* state) {
	unsigned int i;
	for (i=0; i<state->numLabels;i++) st_insertSingletonCandidate(state, i);
}
void st_freeMiningState(st_miningState* state) { // frees all beside state->base
	st_listedPattern* listed;
	for (listed=state->candidates->first;listed!=NULL;) {
		if (listed->pattern->bestKnownRefcount == 0) {
			//printf("free the candidate %p.\n", listed->pattern);
			st_freeTree(listed->pattern);
			st_recursiveFreeEmbedding(listed->embedding);
		}
		listed=listed->succ;
	}
	st_shallowFreeList(state->candidates);
	unsigned int i,j,k;
	for (i=0; i<state->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		st_patternList*** classBestKnown = state->bestKnown[i];
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown =classBestKnown[j];
			classBestKnown[j]=documentBestKnown;
			for (k=0; k<document->num_trees; k++) {
				//st_deepFreeList(documentBestKnown[k]);
				st_patternList* list = documentBestKnown[k];
				while (list->length > 0) {
					st_tree* pattern = list->first->pattern;
					if (pattern->bestKnownRefcount <= 1) {
						st_freeTree(pattern);
						//printf("free the candidate %p.\n", pattern);
						st_recursiveFreeEmbedding(list->first->embedding);
					} else {
						pattern->bestKnownRefcount--;
					}
					st_patternListRemoveFirst(list);
				}
				freemem(list);
			}
			freemem(documentBestKnown);
		}
		freemem(classBestKnown);
	}
	freemem(state->bestKnown);
	//st_deepFreeList(state->candidates);
	freemem(state);
}
void st_expandEmbedding(st_tree* node, st_patternEmbedding* embedding, unsigned int position,
			st_patternEmbedding** expandedEmbeddings, st_patternEmbedding** lastEmbedding, _Bool recursive) {
	st_patternEmbedding* newEmbedding = getmem(sizeof(st_patternEmbedding));
	newEmbedding->classIndex = embedding->classIndex;
	newEmbedding->documentIndex = embedding->documentIndex;
	newEmbedding->sentenceIndex = embedding->sentenceIndex;
	newEmbedding->rightPath = getmem(sizeof(st_tree*) * (position+2));
	memcpy(newEmbedding->rightPath, embedding->rightPath, sizeof(st_tree*) * (position+1));
	newEmbedding->rightPath[position+1] = node;
	/*newEmbedding->next = expandedEmbeddings[node->label];
	expandedEmbeddings[node->label] = newEmbedding;*/
	newEmbedding->next = NULL;
	if (lastEmbedding[node->label] == NULL) {
		lastEmbedding[node->label] = newEmbedding;
		expandedEmbeddings[node->label] = newEmbedding;
	} else {
		lastEmbedding[node->label]->next = newEmbedding;
		lastEmbedding[node->label] = newEmbedding;
	}
	if (recursive) {
		unsigned int i;
		for (i=0; i<node->num_children; i++) st_expandEmbedding(node->children[i], embedding, position, expandedEmbeddings, lastEmbedding, true);
	}
}
void st_printEmbedding(st_patternEmbedding* embedding, unsigned int pathLength) {
	while (embedding != NULL) {
		printf("Embedding for class %u, document %u, sentence %u.\n", embedding->classIndex, embedding->documentIndex, embedding->sentenceIndex);
		unsigned int i;
		for (i=0; i<pathLength;i++) {
			printf("rightPath[%u]:\n", i);
			st_printTree(embedding->rightPath[i], 0);
		}
		printf("next:\n");
		embedding=embedding->next;
	}
	printf("NULL.\n");
}
void st_expandPattern(st_miningState* state, st_tree* pattern, unsigned int num_embedded_edges, st_patternEmbedding* embedding,
											unsigned int position, _Bool embeddable) {
	//st_validateState(state);
	//st_validateEmbedding(state->base, pattern, embedding);
	//printf("expand this pattern with %u embedded edges at position %u (embeddable: %u):\n", num_embedded_edges, position, embeddable);
	//st_printTree(pattern, 0);
	st_patternEmbedding** expandedEmbeddings = getmem(sizeof(st_patternEmbedding*) * state->numLabels);
	st_patternEmbedding** lastEmbedding = getmem(sizeof(st_patternEmbedding*) * state->numLabels);
	unsigned int i;
	for (i=0; i<state->numLabels; i++) {
		expandedEmbeddings[i]=NULL;
		lastEmbedding[i]=NULL;
	}
	st_patternEmbedding* emb;
	_Bool isLeaf;
	st_tree* node;
	node=pattern;
	for (i=0; i<position; i++) {
		node=node->children[node->num_children-1];
	}
	isLeaf =  (node->num_children == 0);
	for (emb=embedding; emb != NULL; emb = emb->next) {
		st_tree* node = emb->rightPath[position];
		//printf("expand this embedding:\n");
		//st_printTree(node, 0);
		st_tree* waitChild = NULL;
		if (!isLeaf) waitChild = emb->rightPath[position+1];
		//iterate the children of emb->rightPath[position] which are right of emb->rightPath[position+1] (if this exists)
		for (i=0; i<node->num_children; i++) {
			if (waitChild != NULL) {
				if (node->children[i] == waitChild) {
					waitChild=NULL;
				}
				continue;
			}
			st_expandEmbedding(node->children[i], emb, position, expandedEmbeddings, lastEmbedding, embeddable);

			
			/*
			unsigned int j;
			for (j=0; j<state->numLabels; j++) {
				st_tree* expanded = st_expandPatternRight(pattern, position, j, embeddable);
				if (!st_isValidEmbedding(state->base, expanded, expandedEmbeddings[j])) {
					printf("ERROR: invalid expanded embedding for continuation %u.\n", j);
					printf("expanded pattern:\n");
					st_printTree(expanded,0);
					printf("node:\n");
					st_printTree(node, 0);
					st_printEmbedding(expandedEmbeddings[j], position+2);
					state = ((st_miningState**) NULL)[0];
				}
				st_freeTree(expanded);
			}
			*/
		}
	}
	if (embeddable) num_embedded_edges++;
	for (i=0; i<state->numLabels; i++) {
		if (expandedEmbeddings[i] != NULL) {
			st_tree* expanded = st_expandPatternRight(pattern, position, i, embeddable);
			/*
			if (!st_isValidPattern(state, expanded)) {
				printf("ERROR: invalid expanded pattern.\n");
			}
			if (!st_isValidEmbedding(state->base, expanded, expandedEmbeddings[i])) {
				printf("ERROR: invalid expanded embedding.\n");
			}
			*/
			st_insertPattern(state, expanded, num_embedded_edges, expandedEmbeddings[i]);
		}
	}
	freemem(expandedEmbeddings);
	freemem(lastEmbedding);
}
_Bool st_indistinguishablePatterns(const st_patternEmbedding* embedding1, const st_patternEmbedding* embedding2) {
	//two patterns are indistinguishable if they match exactly the same trees
	unsigned int lc1=-1,ld1=-1,ls1=-1,lc2=-1,ld2=-1,ls2=-1;
	while (true) {
		if (embedding1 == NULL) return (embedding2 == 0);
		if (embedding2 == NULL) return false;
		if (embedding1->classIndex != embedding2->classIndex ||
			embedding1->documentIndex != embedding2->documentIndex ||
			embedding1->sentenceIndex != embedding2->sentenceIndex) return false;
		lc1=embedding1->classIndex;
		ld1=embedding1->documentIndex;
		ls1=embedding1->sentenceIndex;
		while (embedding1 != NULL && embedding1->classIndex == lc1 && embedding1->documentIndex == ld1 && embedding1->sentenceIndex == ls1) {
			embedding1 = embedding1->next;
		}
		lc2=embedding2->classIndex;
		ld2=embedding2->documentIndex;
		ls2=embedding2->sentenceIndex;
		while (embedding2 != NULL && embedding2->classIndex == lc2 && embedding2->documentIndex == ld2 && embedding2->sentenceIndex == ls2) {
			embedding2 = embedding2->next;
		}
	}
}
_Bool st_doMiningIterations(st_miningState* state, unsigned int num_iterations) {
	//returns true if these iterations were sufficient or false if there are candidates remaining
	st_validateState(state);
	unsigned int iter=0;
	while (state->candidates->length > 0 && (num_iterations == -1 || num_iterations-- > 0)) {
		//st_listedPattern* cand;
		//for (cand = state->candidates->first; cand != NULL; cand = cand->succ) st_printTree(cand->pattern,0);
		st_listedPattern* entry = state->candidates->first;
		st_tree* pattern=entry->pattern;
		//printf("consider this candidate pattern:\n");st_printTree(pattern,0);
		st_patternEmbedding* embedding=entry->embedding;
		if (num_iterations == -1) {
			printf(".");
			if (++iter == 100) {
				printf("\n");
				double entropy, estimate;
				entropy=st_econditionalEntropy(state->base, state->n, &estimate, embedding);
				printf("Remaining %d candidates, latest candidate has entropy %f (estimated %f).\n",
										state->candidates->length, entropy, estimate);
				st_printTree(pattern,0);
				iter=0;
			}
		}
		st_validateEmbedding(state->base, pattern, embedding);
		unsigned int num_embedded_edges = entry->num_embedded_edges;
		st_patternListRemoveFirst(state->candidates);
		st_tree* node = pattern;
		unsigned int position = 0;
		while (true) {
			st_expandPattern(state, pattern, num_embedded_edges, embedding, position, false);
			if (num_embedded_edges < state->k) {
				st_expandPattern(state, pattern, num_embedded_edges, embedding, position, true);
			}
			if (node->num_children == 0) break;
			node=node->children[node->num_children-1];
			position++;
		}
		pattern->flags &= ~TREEFLAG_CANDIDATE;
		if (pattern->bestKnownRefcount == 0) {
			st_freeTree(pattern);
			//printf("free the candidate %p.\n", pattern);
			st_recursiveFreeEmbedding(embedding);
		}
	}
	return state->candidates->length==0;
}
st_patternList* st_getDiscriminativePatterns(st_miningState* state) {
	//prereq: state must be fully mined.
	unsigned int i,j,k;
	st_patternList* result = st_createEmptyPatternList();
	for (i=0; i<state->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		st_patternList*** classBestKnown = state->bestKnown[i];
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown =classBestKnown[j];
			classBestKnown[j]=documentBestKnown;
			for (k=0; k<document->num_trees; k++) {
				//st_deepFreeList(documentBestKnown[k]);
				st_patternList* list = documentBestKnown[k];
				st_listedPattern* entry;
				for (entry = list->first; entry != NULL; entry = entry->succ) {
					//search whether entry already occurs or is indistinguishable from an occuring pattern.
					st_listedPattern* listed;
					_Bool insert=true;
					for (listed = result->first; listed != NULL; listed = listed->succ) {
						if (entry->pattern == listed->pattern || st_indistinguishablePatterns(entry->embedding, listed->embedding)) {
							insert=false;
							break;
						}
					}
					if ( insert ) {
						st_patternListInsertLast(result, entry->pattern, entry->num_embedded_edges, entry->embedding);
					}
				}
			}
		}
	}
	return result;
}
st_patternList* st_mine(st_miningState* state) {
	//printf("start mining...\n");
	st_populateMiningState(state);
	st_doMiningIterations(state, -1);
	st_validateState(state);
	/*
	st_listedPattern* entry;
	//printf("mined %u patterns.\n", result->length);
	for (entry=result->first; entry != NULL; entry=entry->succ) {
		entry->pattern->flags &= ~TREEFLAG_ALREADY_MENTIONED;
		//st_printTree(entry->pattern, 0);
	}
	*/
	return st_getDiscriminativePatterns(state);
}
unsigned int st_numCandidates(const st_miningState* state) {
	return state->candidates->length;
}
void st_appendPatternList(st_patternList* list1, st_patternList* list2) {
	//destroys list2 and appends its entries to list1
	if (list1->length == 0) {
		list1->first = list2->first;
		list1->last = list2->last;
		list1->length = list2->length;
	} else if (list2->length != 0) {
		list1->last->succ = list2->first;
		list2->first->pred = list1->last;
		list1->last = list2->last;
		list1->length += list2->length;
	}
	freemem(list2);
}
typedef struct {
	unsigned int num_substates;
	st_miningState** substates;
} st_splitState;
st_miningState* st_extractSubstate(st_miningState* state, unsigned int startIndex, unsigned int length) {
	st_miningState* result = getmem(sizeof(st_miningState));
	unsigned int i,j,k;
	result->base = state->base;
	result->candidates = st_createEmptyPatternList();
	st_listedPattern* listed = state->candidates->first;
	for (i=0; i<startIndex;i++) {
		listed = listed->succ;
	}
	for (i=0; i<length;i++) {
		//if (listed->pattern->bestKnownRefcount>0) {
		st_tree* pattern = listed->pattern;
		pattern->copyUsedDuringSplitup = st_deepCopyTree(pattern);
		//printf("copy %p to %p.\n", pattern, pattern->copyUsedDuringSplitup);
		pattern->embeddingUsedDuringSplitup = st_copyPatternEmbedding(pattern,listed->embedding);
		st_patternListInsertLast(result->candidates, pattern->copyUsedDuringSplitup, listed->num_embedded_edges, pattern->embeddingUsedDuringSplitup);
		pattern->copyUsedDuringSplitup->original = pattern;
		//}
		listed = listed->succ;
	}
	result->bestKnown = getmem(sizeof(st_patternList***) * state->base->num_classes);
	for (i=0; i<state->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		st_patternList*** classBestKnown = getmem(sizeof(st_patternList**) * class->num_documents);
		result->bestKnown[i] = classBestKnown;
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown = getmem(sizeof(st_patternList*) * document->num_trees);
			classBestKnown[j]=documentBestKnown;
			for (k=0; k<document->num_trees; k++) {
				st_patternList* sentenceBestKnown = st_createEmptyPatternList();
				documentBestKnown[k]=sentenceBestKnown;
				st_patternList* stateBestKnown = state->bestKnown[i][j][k];
				sentenceBestKnown->cachedEntropy = stateBestKnown->cachedEntropy;
				st_listedPattern* listed;
				for (listed = stateBestKnown->first;listed != NULL; listed=listed->succ) {
					st_tree* pattern = listed->pattern;
					if (pattern->copyUsedDuringSplitup == NULL) {
						pattern->copyUsedDuringSplitup = st_deepCopyTree(pattern);
						//printf("copy %p to %p.\n", pattern, pattern->copyUsedDuringSplitup);
						pattern->copyUsedDuringSplitup->original = pattern;
						pattern->copyUsedDuringSplitup->flags &= ~TREEFLAG_CANDIDATE;
						pattern->embeddingUsedDuringSplitup = st_copyPatternEmbedding(pattern,listed->embedding);
					}
					st_patternListInsertLast(sentenceBestKnown, pattern->copyUsedDuringSplitup, listed->num_embedded_edges,
							(st_patternEmbedding*) pattern->embeddingUsedDuringSplitup);
				}
			}
		}
	}
	for (i=0; i<state->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			for (k=0; k<document->num_trees; k++) {
				st_patternList* stateBestKnown = state->bestKnown[i][j][k];
				st_listedPattern* listed;
				for (listed = stateBestKnown->first;listed != NULL; listed=listed->succ) {
					st_tree* pattern = listed->pattern;
					pattern->copyUsedDuringSplitup=NULL;
					pattern->embeddingUsedDuringSplitup=NULL;
				}
			}
		}
	}
	for (listed=state->candidates->first;listed!=NULL;listed=listed->succ) {
		listed->pattern->copyUsedDuringSplitup=NULL;
		listed->pattern->embeddingUsedDuringSplitup=NULL;
	}
	result->numLabels = state->numLabels;
	result->supportLowerBound = state->supportLowerBound;
	result->n=state->n;
	result->k=state->k;
	st_validateState(result);
	return result;
}
void st_debugState(st_miningState* state) {
	printf("state for documentbase %p, %u candidates, %u labels. support lower bound: %u, n: %u, k: %u\n", state->base, state->candidates->length,
			state->numLabels, state->supportLowerBound, state->n, state->k);
	st_listedPattern* listed;
	for (listed=state->candidates->first; listed!=NULL; listed=listed->succ) {
		printf("%p (with flags %x) is a candidate.\n", listed->pattern, listed->pattern->flags);
	}
	unsigned int i,j,k;
	for (i=0; i<state->base->num_classes; i++) {
		const st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		const st_patternList*** classBestKnown = (const st_patternList***) state->bestKnown[i];
		for (j=0; j<class->num_documents; j++) {
			const st_document* document = ((st_document**) (class+1))[j];
			const st_patternList** documentBestKnown =(const st_patternList**) classBestKnown[j];
			for (k=0; k<document->num_trees; k++) {
				//st_deepFreeList(documentBestKnown[k]);
				const st_patternList* list = (const st_patternList*) documentBestKnown[k];
				printf("bestKnown[%u][%u][%u] has length %u.\n", i,j,k,list->length);
				for (listed=list->first;listed!=NULL;listed=listed->succ) {
					printf("%p (with flags %x) is a best known.\n", listed->pattern, listed->pattern->flags);
				}
				//printf("validated bestKnown of class %u, document %u, sentence %u.\n", i, j, k);
			}
		}
	}
}
void st_miningStateStatistics(const st_miningState*, unsigned int*, unsigned int*);
st_splitState* st_splitupState(st_miningState* state, unsigned int num_substates) {
	/*
	unsigned int patterns,embeddings;
	st_miningStateStatistics(state, &patterns, &embeddings);
	printf("splitup state with %u patterns and %u embeddings.\n", patterns, embeddings);
	*/
	st_splitState* result = getmem(sizeof(st_splitState));
	result->num_substates = num_substates;
	result->substates = getmem(sizeof(st_miningState) * num_substates);
	unsigned int cands = state->candidates->length;
	unsigned int length = cands/num_substates;
	unsigned int i;
	//printf("%u candidates, create %u substates, length is %u.\n", cands, num_substates, length);
	for (i=0; i<num_substates-1; i++) {
		result->substates[i] = st_extractSubstate(state, i*length, length);
	}
	result->substates[num_substates-1] = st_extractSubstate(state, (num_substates-1)*length, cands-(num_substates-1)*length);
/*
	for (i=0; i<num_substates;i++) {
		st_miningState* state = result->substates[i];
		printf("result->substates[%u]:\n", i);
		st_debugState(state);
	}
*/
	return result;
}
_Bool st_doMiningIterationsInSplitState(st_splitState* states, unsigned int index, unsigned int iterations) {
	return st_doMiningIterations(states->substates[index], iterations);
}
void st_tidyBestKnown(st_patternList* list) {
	//removes entries such that each original-value occurs exactly once.
	st_listedPattern* link1, *link2;
	for (link1=list->first; link1!=NULL;link1=link1->succ) {
		for (link2=link1->succ; link2!=NULL; ) {
			if (link1->pattern->original == link2->pattern->original) {
				if (link2->pattern->bestKnownRefcount-- <= 1) {
					if ((link2->pattern->flags & TREEFLAG_CANDIDATE) == 0) {
						st_freeTree(link2->pattern);
						//printf("free the candidate %p\n", link2->pattern);
						st_recursiveFreeEmbedding(link2->embedding);
					}
				}
				st_listedPattern* tmp = link2->succ;
				st_patternListRemoveListed(list, link2);
				link2=tmp;
			} else {
				link2=link2->succ;
			}
		}
	}
}
st_miningState* st_mergeStates(st_splitState* states) {
	//destroys the input and returns a mining state by concatenating the candidates and collecting the best of bestKnown.
	st_miningState* fst = states->substates[0];
	st_miningState* result = st_createMiningState(fst->base, fst->numLabels, fst->supportLowerBound, fst->n, fst->k);
	unsigned int i,j,k,index;
	st_patternList**** classBestKnown = getmem(sizeof(st_patternList***) * states->num_substates);
	st_patternList*** documentBestKnown = getmem(sizeof(st_patternList**) * states->num_substates);
	st_patternList** sentenceBestKnown = getmem(sizeof(st_patternList*) * states->num_substates);
	for (i=0; i<fst->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (fst->base+1))[i];
		for (index=0; index<states->num_substates;index++) {
			classBestKnown[index] = states->substates[index]->bestKnown[i];
		}
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			for (index=0; index<states->num_substates;index++) {
				documentBestKnown[index] = classBestKnown[index][j];
			}
			for (k=0; k<document->num_trees; k++) {
				double minimalEntropy = -1;
				for (index=0; index<states->num_substates;index++) {
					sentenceBestKnown[index] = documentBestKnown[index][k];
					double ent = sentenceBestKnown[index]->cachedEntropy;
					if (minimalEntropy == -1 || (ent != -1 && ent < minimalEntropy)) minimalEntropy = ent;
				}
				st_patternList* resultBestKnown = result->bestKnown[i][j][k];
				resultBestKnown->cachedEntropy = minimalEntropy;
				for (index=0; index<states->num_substates;index++) {
					st_patternList* lst = sentenceBestKnown[index];
					if (lst->length == 0) continue;
					if (lst->cachedEntropy == minimalEntropy) {
						st_appendPatternList(resultBestKnown, lst);
						st_tidyBestKnown(resultBestKnown);
					} else {
						//free the entries.
						st_listedPattern* listed;
						for (listed = lst->first; listed!=NULL;) {
							st_tree* pattern = listed->pattern;
							if (pattern->bestKnownRefcount-- <= 1) {
								if ((pattern->flags & TREEFLAG_CANDIDATE) == 0) {
									st_freeTree(pattern);
									//printf("free the candidate %p.\n", pattern);
									st_recursiveFreeEmbedding(listed->embedding);
								}
							}
							listed=listed->succ;
							st_patternListRemoveFirst(lst);
						}
						freemem(lst);
					}
				}
			}
			for (index=0; index<states->num_substates;index++) {
				freemem(documentBestKnown[index]);
			}
		}
		for (index=0; index<states->num_substates;index++) {
			freemem(classBestKnown[index]);
		}
	}
	for (index=0; index<states->num_substates;index++) {
		st_miningState* state = states->substates[index];
		freemem(state->bestKnown);
		st_appendPatternList(result->candidates, state->candidates);
		freemem(state);
	}
	freemem(classBestKnown);
	freemem(documentBestKnown);
	freemem(sentenceBestKnown);
	freemem(states->substates);
	freemem(states);
	return result;
}
typedef struct {
	st_miningState* state;
	unsigned int iterations;
} st_miningInfo;
void* st_doMineFromInfo(void* arg) {
	st_miningInfo* info = (st_miningInfo*) arg;
	st_doMiningIterations(info->state, info->iterations);
	return NULL;
}
void st_doParallelMiningIterations(st_splitState* states, unsigned int iterations) {
	pthread_t* threads = getmem(sizeof(pthread_t) * states->num_substates);
	st_miningInfo* info = getmem(sizeof(st_miningInfo) * states->num_substates);
	unsigned int i;
	for (i=0; i<states->num_substates;i++) {
		info[i].state = states->substates[i];
		info[i].iterations = iterations;
		pthread_create(&(threads[i]), NULL, st_doMineFromInfo, info+i);
	}
	for (i=0; i<states->num_substates;i++) {
		pthread_join(threads[i], NULL);
	}
	freemem(info);
	freemem(threads);
}
void st_doNonparallelMiningIterations(st_splitState* states, unsigned int iterations) {
	unsigned int i;
	for (i=0; i<states->num_substates;i++) {
		st_doMiningIterations(states->substates[i],iterations);
	}
}
unsigned int st_lengthEmbedding(const st_patternEmbedding* embedding) {
	unsigned int result=0;
	while (embedding != NULL) {
		result++;
		embedding = embedding->next;
	}
	return result;
}
unsigned int st_treeSize(const st_tree* tree) {
	unsigned int result=1,i;
	for (i=0;i<tree->num_children;i++) {
		result += st_treeSize(tree->children[i]);
	}
	return result;
}
void st_patternListStatistics(const st_patternList* list, unsigned int* patterns, unsigned int* embeddings) {
	*patterns=0;
	*embeddings=0;
	const st_listedPattern* listed;
	for (listed=list->first;listed!=NULL; listed=listed->succ) {
		*patterns += st_treeSize(listed->pattern);
		*embeddings += st_lengthEmbedding(listed->embedding);
	}
}
void st_miningStateStatistics(const st_miningState* state, unsigned int* patterns, unsigned int* embeddings) {
	unsigned int pats, embs;
	st_patternListStatistics(state->candidates, patterns,embeddings);
	unsigned int i,j,k;
	for (i=0; i<state->base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (state->base+1))[i];
		st_patternList*** classBestKnown = state->bestKnown[i];
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown =classBestKnown[j];
			classBestKnown[j]=documentBestKnown;
			for (k=0; k<document->num_trees; k++) {
				//st_deepFreeList(documentBestKnown[k]);
				st_patternListStatistics(documentBestKnown[k], &pats, &embs);
				*patterns += pats;
				*embeddings += embs;
			}
		}
	}
}
void st_testFillArray(unsigned int length, char* array) {
	while (length-- > 0) {
		*(array++)=1;
	}
}
void st_testPrintArray(unsigned int length, char* array) {
	unsigned int i;
	printf("array: ");
	for (i=0; i<length; i++) {
		if (i>0) {
			printf(", ");
		}
		printf("%d",array[i]);
		if (i>1000) break;
	}
	printf("\n");
}
typedef struct {
	st_label label;
	unsigned short int num_children;
	short int flags;
} st_stored_tree;
unsigned int st_getSizeForTreeStorage(const st_tree* tree) {
	return sizeof(st_stored_tree) * st_countNodes(tree);
}
void _st_storeTree(const st_tree* tree, st_stored_tree** memory) {
	st_stored_tree* ptr = *memory;
	ptr->label = tree->label;
	ptr->num_children = tree->num_children;
	ptr->flags = tree->flags & TREEFLAG_EXTENDABLE_EDGE;
	(*memory)++;
	unsigned int i;
	for (i=0; i< tree->num_children;i++) {
		_st_storeTree(tree->children[i], memory);
	}
}
void st_storeTree(const st_tree* tree, st_stored_tree* memory) {
	_st_storeTree(tree,&memory);
}
st_tree* _st_readTree(st_stored_tree** memory) {
	st_stored_tree* ptr = *memory;
	st_tree* tree = st_prepareTree(ptr->label, ptr->num_children);
	tree->flags |= ptr->flags;
	(*memory)++;
	unsigned int i;
	for (i=0; i< tree->num_children;i++) {
		st_setTreeChild(tree,i,_st_readTree(memory));
	}
	return tree;
}
st_tree* st_readTree(st_stored_tree* memory) {
	return _st_readTree(&memory);
}
int main(int argc, char* argv[]) {
	st_tree* tree1 = st_prepareTree(0, 0);
	st_tree* tree2 = st_prepareTree(1, 0);
	st_tree* tree3 = st_prepareTree(2, 0);
	st_tree* tree4 = st_prepareTree(3, 0);
	st_document* doc1 = st_prepareDocument(1);
	st_documentSetTree(doc1,0,tree1);
	st_document* doc2 = st_prepareDocument(1);
	st_documentSetTree(doc2,0,tree2);
	st_document* doc3 = st_prepareDocument(1);
	st_documentSetTree(doc3,0,tree3);
	st_document* doc4 = st_prepareDocument(1);
	st_documentSetTree(doc4,0,tree4);
	st_documentclass* class1 = st_prepareDocumentClass(2);
	st_setDocumentInClass(class1,0,doc1);
	st_setDocumentInClass(class1,1,doc2);
	st_documentclass* class2 = st_prepareDocumentClass(2);
	st_setDocumentInClass(class2,0,doc3);
	st_setDocumentInClass(class2,1,doc4);
	st_documentbase* base = st_prepareDocumentBase(2);
	st_setClassInDocumentBase(base,0,class1);
	st_setClassInDocumentBase(base,1,class2);
	st_completeDocumentBaseSetup(base);
	printf("base: %p\n", base);

	st_miningState* state = st_createMiningState(base, 4, 1, 10, 2);
	printf("starting state:\n");
	st_debugState(state);
	st_populateMiningState(state);
	printf("populated state:\n");
	st_debugState(state);
	while(state->candidates->length > 0) {
		st_splitState* split = st_splitupState(state,2);
		st_freeMiningState(state);
		st_doParallelMiningIterations(split,1);
		printf("after mining, state1:\n");
		st_debugState(split->substates[0]);
		printf("after mining, state2:\n");
		st_debugState(split->substates[1]);
		/*
		st_freeMiningState(split->substates[0],false);
		st_freeMiningState(split->substates[1],false);
		free(split->substates);
		free(split);
		*/
		state = st_mergeStates(split);
		printf("merged:\n");
		st_debugState(state);
	}
	st_patternList* list = st_getDiscriminativePatterns(state);
	//st_patternList* list = st_mine(state);
	st_listedPattern* entry;
	for (entry=list->first; entry != NULL; entry=entry->succ) {
		printf("We get the following discriminative pattern:\n");
		st_printTree(entry->pattern, 0);
	}
	st_shallowFreeList(list);
	st_freeMiningState(state);
		/*
	*/
	st_freeDocumentBase(base);
	st_freeDocumentClass(class1);
	st_freeDocumentClass(class2);
	st_shallowFreeDocument(doc1);
	st_shallowFreeDocument(doc2);
	st_shallowFreeDocument(doc3);
	st_shallowFreeDocument(doc4);
	st_shallowFreeTree(tree1);
	st_shallowFreeTree(tree2);
	st_shallowFreeTree(tree3);
	st_shallowFreeTree(tree4);
	showMemoryInformation();
	return 0;
}
