import os
import subprocess
import sys
import re
import numpy as np
stream = sys.argv[1]

try:
    res_hits = subprocess.check_output(['grep', '-rc', 'hit = 1',stream]).decode('utf-8').strip().split('\n')
    hits = int(res_hits[0])
except subprocess.CalledProcessError:
    hits = 0


try:
    chunks = int(subprocess.check_output(['grep', '-c', 'Image filename',stream]).decode('utf-8').strip().split('\n')[0]) #len(res_hits)
except subprocess.CalledProcessError:
    chunks = 0


try:
    res_indexed = subprocess.check_output(['grep', '-rc', 'Begin crystal',stream]).decode('utf-8').strip().split('\n')
    indexed = int(res_indexed[0])
except subprocess.CalledProcessError:
    indexed = 0

try:
    res_none_indexed_patterns = subprocess.check_output(['grep', '-rc', 'indexed_by = none',stream]).decode('utf-8').strip().split('\n')
    none_indexed_patterns = int(res_none_indexed_patterns[0])
except subprocess.CalledProcessError:
    none_indexed_patterns = 0


indexed_patterns = chunks - none_indexed_patterns

print_line = f'{stream:<20}; num patterns/hits = {str(chunks)+"/"+str(hits):^10}; indexed patterns/indexed crystals = {str(indexed_patterns)+"/"+str(indexed):^10}'

print(print_line)