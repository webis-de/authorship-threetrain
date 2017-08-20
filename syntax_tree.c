#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
typedef int st_label;
#define TREEFLAG_EXTENDABLE_EDGE 1
#define TREEFLAG_PACKED_CHILDREN 1<<1
struct st_syntax_tree {
	st_label label;
	struct st_syntax_tree* parent;
	unsigned int num_children;
	struct st_syntax_tree** children;
	int flags;
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
	result->flags = tree->flags;
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
			frequencyMatrix[index*base->num_classes+j]++;
		}
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
		double min;
		unsigned int total=0;
		for (i=0; i<base->num_documents;i++) total += frequencyMatrix[i];
		for (i=0; i<base->num_documents;i++) {
			unsigned int extra=frequencyMatrix[base->num_classes +i];
			total += extra;
			frequencyMatrix[i] += extra;
			double val=0;
			for (j=0; j<base->num_documents;j++) {
				double entry=frequencyMatrix[j];
				if (entry != 0) val -= entry * log(entry/total);
			}
			if (i==0 || val<min) min=val;
		}
		*lowerBound = min*dinv;
	}
	free(frequencyMatrix);
	return result;
}
//next: Algorithm to store double linked lists of patterns.
struct st_partialPatternEmbedding {
	unsigned int documentIndex;
	unsigned int sentenceIndex;
	st_tree** rightPath;
	struct st_partialPatternEmbedding* next;
};
typedef struct st_partialPatternEmbedding st_patternEmbedding;
struct st_patternListEntry {
	st_tree* pattern;
	st_patternEmbedding* embedding;
	struct st_patternListEntry* pred;
	struct st_patternListEntry* succ;
};
typedef struct st_patternListEntry st_listedPattern;
typedef struct {
	unsigned int length;
	double cachedIG;
	st_listedPattern* first;
	st_listedPattern* last;
} st_patternList;
st_patternList* st_createEmptyPatternList() {
	st_patternList* result = malloc(sizeof(st_patternList));
	result->length=0;
	result->cachedIG = -1;
	result->first=NULL;
	result->last=NULL;
	return result;
}
void st_patternListInsertFirst(st_patternList* list, st_tree* pattern, st_patternEmbedding* embedding) {
	st_listedPattern* link = malloc(sizeof(st_listedPattern));
	link->pattern = pattern;
	link->embedding=embedding;
	link->pred = NULL;
	link->succ = list->first;
	list->first=link;
	if (list->last == NULL) list->last=link;
	list->length++;
}
void st_patternListInsertLast(st_patternList* list, st_tree* pattern, st_patternEmbedding* embedding) {
	st_listedPattern* link = malloc(sizeof(st_listedPattern));
	link->pattern = pattern;
	link->embedding=embedding;
	link->succ = NULL;
	link->pred = list->last;
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
void st_shallowCleanupList(st_patternList* list) {
	st_listedPattern* link;
	link=list->first;
	while (link != NULL) {
		st_listedPattern* tmp=link;
		link=link->succ;
		free(tmp);
	}
	list->length=0;
	list->first=NULL;
	list->last=NULL;
}
int main(int argc, char* argv[]) {
	st_tree* tree1 = st_prepareTree(1, 0);
	st_tree* tree2 = st_prepareTree(2, 0);
	st_tree* tree3 = st_prepareTree(3, 0);
	st_tree* tree4 = st_prepareTree(4, 0);
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

	double est;
	printf("%f\n", st_conditionalEntropy(base,tree1,100,&est));
	printf("%f\n", est);

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
