all: libsyntax_tree.so pos.py syntax_tree_function_signatures
.PHONY: all
libsyntax_tree.so: syntax_tree.o
	gcc -o libsyntax_tree.so -shared syntax_tree.o
syntax_tree.o: syntax_tree.c
	gcc -Wall -Werror -g -c -fpic -lm -o syntax_tree.o syntax_tree.c
pos.py: make_pospy.py pos.txt
	python3 make_pospy.py
syntax_tree_function_signatures: syntax_tree.c
	cproto -f2 -o syntax_tree_function_signatures syntax_tree.c
