#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
typedef int st_label;
#define TREEFLAG_EXTENDABLE_EDGE 1
#define TREEFLAG_PACKED_CHILDREN 2
#define TREEFLAG_ALREADY_MENTIONED 4
#define TREEFLAG_CANDIDATE 8
#define VALIDATE_EMBEDDINGS
struct st_syntax_tree {
	st_label label;
	struct st_syntax_tree* parent;
	unsigned int num_children;
	struct st_syntax_tree** children;
	int flags;
	unsigned int bestKnownRefcount;
};
typedef struct st_syntax_tree st_tree;
void st_freeTree(st_tree* t) {
	int i;
	for (i=0; i<t->num_children; i++) {
		st_freeTree((st_tree*) t->children[i]);
	}
	if (t->children != NULL && ! (t->flags & TREEFLAG_PACKED_CHILDREN)) free(t->children);
	free(t);
}
void st_shallowFreeTree(st_tree* t) {
	if (t->children != NULL && ! (t->flags & TREEFLAG_PACKED_CHILDREN)) free(t->children);
	free(t);
}
st_tree* st_createTree(st_label label, unsigned int num_children, st_tree** children) {
	int i;
	st_tree* result = (st_tree*) malloc(sizeof(st_tree));
	result->label=label;
	result->parent=NULL;
	result->num_children=num_children;
	result->flags=0;
	result->bestKnownRefcount = 0;
	if (num_children != 0) {
		result->children=children;
	} else {
		result->children=NULL;
	}
	for (i=0;i<num_children;i++) {
		children[i]->parent = result;
	}
	return result;
}
st_tree* st_prepareTree(st_label label, unsigned int num_children) {
	st_tree* result = (st_tree*) malloc(sizeof(st_tree) + sizeof(st_tree*) * num_children);
	result->label=label;
	result->parent = NULL;
	result->num_children = num_children;
	result->bestKnownRefcount = 0;
	if (num_children >0) {
		result->children = (void*) ((char*) result) + sizeof(st_tree);
	} else {
		result->children = NULL;
	}
	result->flags = TREEFLAG_PACKED_CHILDREN;
	return result;
}
void st_setTreeChild(st_tree* parent, unsigned int index, st_tree* child) {
	parent->children[index]=child;
	child->parent = parent;
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
_Bool st_treeGetExtendable(const st_tree* tree){return (tree->flags & TREEFLAG_EXTENDABLE_EDGE)==0;}
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
		ch->parent=result;
	}
	return result;
}
typedef struct {
	unsigned int num_trees;
} st_document;
//the convention is that directly after the document, a list of `num_trees` entries of type st_tree* follows.
void st_shallowFreeDocument(st_document* doc) {
	free(doc);
}
st_document* st_prepareDocument(unsigned int num_trees) {
	st_document* result = (st_document*) malloc(sizeof(st_document) + num_trees * sizeof(st_tree*));
	result->num_trees = num_trees;
	return result;
}
void st_documentSetTree(st_document* doc, unsigned int index, st_tree* const tree) {
	((st_tree**) (void*) (doc+1))[index] = tree;
}
unsigned int st_occuringTrees(const st_tree* pattern, const st_document* doc) {
	unsigned int result = 0,i;
	for (i=0; i < doc->num_trees; i++) {
		if (st_canMatchPattern(pattern, ((st_tree**) (void*) (doc+1))[i])) result++;
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
	free(class);
}
st_documentclass* st_prepareDocumentClass(unsigned int num_documents) {
	st_documentclass* result = malloc(sizeof(st_documentclass) + num_documents * sizeof(st_document*));
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
	free(base);
}
st_documentbase* st_prepareDocumentBase(unsigned int num_classes) {
	st_documentbase* result = malloc(sizeof(st_documentbase) + num_classes * sizeof(st_documentclass*));
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
	unsigned int* frequencyMatrix = malloc(memorysize);
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
	for (j=0;j<n;j++) {
		for (i=0;i<base->num_classes;i++) {
			printf("%d ",frequencyMatrix[j*base->num_classes+i]);
		}
		printf("\n");
	}
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
			printf("val: %f\n", val);
			if (i==0 || val<min) min=val;
			total -= extra;
			frequencyMatrix[i] -= extra;
		}
		printf("min: %f\n", min);
		*lowerBound = min*dinv;
		if (result > *lowerBound) {
			printf("ERROR detected.\n");
			*lowerBound /= result-result;
		}
	}
	free(frequencyMatrix);
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
		unsigned int i=0;
		const st_tree* node = pattern;
		while (true) {
			if (node->label != embedding->rightPath[i]->label) return false;
			if (i>0 && (node->flags & TREEFLAG_EXTENDABLE_EDGE) == 0 && embedding->rightPath[i]->parent != embedding->rightPath[i-1]) {
				return false;
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
	st_patternList* result = malloc(sizeof(st_patternList));
	result->length=0;
	result->cachedEntropy = -1;
	result->first=NULL;
	result->last=NULL;
	return result;
}
void st_patternListInsertFirst(st_patternList* list, st_tree* pattern, unsigned int num_embedded_edges, st_patternEmbedding* embedding) {
	st_listedPattern* link = malloc(sizeof(st_listedPattern));
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
	st_listedPattern* link = malloc(sizeof(st_listedPattern));
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
	free(link);
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
	free(link);
	list->length--;
}
void st_recursiveFreeEmbedding(st_patternEmbedding* embedding) {
	while (embedding != NULL) {
		//printf("about to free embedding in class %u, document %u, sentence %u\n", embedding->classIndex, embedding->documentIndex, embedding->sentenceIndex);
		free(embedding->rightPath);
		st_patternEmbedding* next = embedding->next;
		free(embedding);
		embedding=next;
	}
}
void st_deepCleanupList(st_patternList* list) {
	st_listedPattern* link;
	link=list->first;
	while (link != NULL) {
		st_freeTree(link->pattern);
		st_recursiveFreeEmbedding(link->embedding);
		st_listedPattern* tmp=link;
		link=link->succ;
		free(tmp);
	}
	list->length=0;
	list->first=NULL;
	list->last=NULL;
}
void st_deepFreeList(st_patternList* list) {
	st_deepCleanupList(list);
	free(list);
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
	unsigned int* frequencyMatrix = malloc(memorysize);
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
	free(frequencyMatrix);
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
	st_miningState* result = malloc(sizeof(st_miningState));
	result->base=base;
	result->bestKnown = malloc(sizeof(st_patternList***) * base->num_classes);
	for (i=0; i<base->num_classes; i++) {
		st_documentclass* class = ((st_documentclass**) (base+1))[i];
		st_patternList*** classBestKnown = malloc(sizeof(st_patternList**) * class->num_documents);
		result->bestKnown[i] = classBestKnown;
		for (j=0; j<class->num_documents; j++) {
			st_document* document = ((st_document**) (class+1))[j];
			st_patternList** documentBestKnown = malloc(sizeof(st_patternList*) * document->num_trees);
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
		st_recursiveFreeEmbedding(embedding);
		return;
	}
	//if (numEmbeddings > 100000) numEmbeddings=( (st_tree*) NULL) -> num_children;
	//printf("support bound passed.\n");
	double estimate;
	double entropy = st_econditionalEntropy(state->base, state->n, &estimate, embedding);
	_Bool candidate=false;
	st_patternEmbedding* emb;
	for (emb = embedding; emb != NULL; emb = emb->next) {
		//st_validateState(state);
		st_patternList* bestKnown = state->bestKnown[emb->classIndex][emb->documentIndex][emb->sentenceIndex];
		if (bestKnown->last != NULL && bestKnown ->last->pattern == pattern) continue;
		//printf("iterate embedding in class %u, document %u, sentence %u.\n",emb->classIndex, emb->documentIndex, emb->sentenceIndex);
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
		printf("We insert the following pattern:\n");
		st_printTree(pattern, 0);
		printf("entropy: %f, estimated: %f.\n", entropy, estimate);
		st_patternListInsertLast(state->candidates, pattern, num_embedded_edges, embedding);
		pattern->flags |= TREEFLAG_CANDIDATE;
	} else {
		st_freeTree(pattern);
		st_recursiveFreeEmbedding(embedding);
	}
	//st_validateState(state);
}

void st_appendSingletonEmbeddings(st_tree* tree, st_label label,
		unsigned int classIndex, unsigned int documentIndex, unsigned int sentenceIndex, st_patternEmbedding** embedding) {
	if (tree->label == label) {
		st_patternEmbedding* emb = malloc(sizeof(st_patternEmbedding));
		emb->classIndex = classIndex;
		emb->documentIndex = documentIndex;
		emb->sentenceIndex = sentenceIndex;
		emb->rightPath = malloc(sizeof(st_tree*));
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
		printf("search for embeddings of %d in class %u\n", label, classIndex);
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
				while (list->length > 0) st_patternListRemoveFirst(list);
				free(list);
			}
			free(documentBestKnown);
		}
		free(classBestKnown);
	}
	free(state->bestKnown);
	st_deepFreeList(state->candidates);
	free(state);
}
void st_expandEmbedding(st_tree* node, st_patternEmbedding* embedding, unsigned int position,
			st_patternEmbedding** expandedEmbeddings, st_patternEmbedding** lastEmbedding, _Bool recursive) {
	st_patternEmbedding* newEmbedding = malloc(sizeof(st_patternEmbedding));
	newEmbedding->classIndex = embedding->classIndex;
	newEmbedding->documentIndex = embedding->documentIndex;
	newEmbedding->sentenceIndex = embedding->sentenceIndex;
	newEmbedding->rightPath = malloc(sizeof(st_tree*) * (position+2));
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
	st_patternEmbedding** expandedEmbeddings = malloc(sizeof(st_patternEmbedding*) * state->numLabels);
	st_patternEmbedding** lastEmbedding = malloc(sizeof(st_patternEmbedding*) * state->numLabels);
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
				} else {
					continue;
				}
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
	free(expandedEmbeddings);
	free(lastEmbedding);
}
st_patternList* st_mine(st_miningState* state) {
	printf("start mining...\n");
	st_populateMiningState(state);
	unsigned int i,j,k;
	st_validateState(state);
	while (state->candidates->length > 0) {
		printf("New mining iteration, we have %u candidates remaining.\n", state->candidates->length);
		//st_listedPattern* cand;
		//for (cand = state->candidates->first; cand != NULL; cand = cand->succ) st_printTree(cand->pattern,0);
		st_listedPattern* entry = state->candidates->first;
		st_tree* pattern=entry->pattern;
		st_patternEmbedding* embedding=entry->embedding;
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
			st_recursiveFreeEmbedding(embedding);
		}
	}
	st_validateState(state);
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
					if ( (entry->pattern->flags & TREEFLAG_ALREADY_MENTIONED) == 0) {
						st_patternListInsertLast(result, entry->pattern, entry->num_embedded_edges, entry->embedding);
						entry->pattern->flags |= TREEFLAG_ALREADY_MENTIONED;
					}
				}
			}
		}
	}
	st_listedPattern* entry;
	for (entry=result->first; entry != NULL; entry=entry->succ) {
		entry->pattern->flags &= ~TREEFLAG_ALREADY_MENTIONED;
	}
	return result;

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

	st_miningState* state = st_createMiningState(base, 4, 1, 10, 2);
	st_patternList* list = st_mine(state);
	printf("got %u discriminative patterns.\n", list->length);
	st_listedPattern* entry;
	for (entry=list->first; entry != NULL; entry=entry->succ) {
		printf("We get the following discriminative pattern:\n");
		st_printTree(entry->pattern, 0);
	}
	st_deepFreeList(list);
	st_freeMiningState(state);
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
	return 0;
}
