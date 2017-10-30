#!/usr/bin/env bash
#Usage: subdivided_traitrain.sh (inputDataset) (inputRun) (outputDir) (numSubdivision)
#calls python3 tira-tritrain.py (inputDataset) (inputRun) (outputDir) (numSubdivision) $X
#where X=0,1,...,numSubdivision-1 and finally X=output
#use this instead of python3 tira-tritrain.py (inputDataset) (inputRun) (outputDir) (numSubdivision)
#if you have limited memory, python needs to by killed and restarted from time to time to
#not eat all your memory.
inputDataset=$1
inputRun=$2
outputDir=$3
numSubdivision=$4
if ! [ "$numSubdivision" -eq "$numSubdivision" ]
	then echo "Usage: subdivided_traitrain.sh (inputDataset) (inputRun) (outputDir) (numSubdivision)"
	exit 0
fi
seq 0 $(($numSubdivision-1)) | xargs -n 1 -- /usr/bin/python3 tira-tritrain.py "$inputDataset" "$inputRun" "$outputDir" "$numSubdivision"
/usr/bin/python3 tira-tritrain.py "$inputDataset" "$inputRun" "$outputDir" "$numSubdivision" output
