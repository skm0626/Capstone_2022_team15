#!/bin/bash

count=0
for file1 in /home/foscar/다운로드/High_Resolution/*
do
	for file2 in $file1/*
	do
		for file3 in $file2/*
		do
			for file4 in $file3/*
			do
				for file5 in $file4/*
				do
					change_filename=`printf "%6d" $count`
					mv -v $file5 $change_filename.jpg
					count=$((${count}+1))
				done
			done
		done
	done
done
