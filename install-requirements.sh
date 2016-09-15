#!/usr/bin/env bash

for file in `ls functions/*/requirements.txt`
do
  pip install --upgrade -r $file -t `dirname $file` 
done
