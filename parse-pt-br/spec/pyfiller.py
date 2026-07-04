# NLP++ python pass: pyfiller
# Invoked as:  python "<appdir>/spec/pyfiller.py" "<appdir>" "<inputfile>" <pre|post>
#   The pass runs wherever it sits in the sequence. The engine passes
#   "pre" when it is placed before the tokenizer (raw text), or
#   "post" when it is placed after the tokenizer.
import sys, io, os

appdir    = sys.argv[1] if len(sys.argv) > 1 else "."
inputfile = sys.argv[2] if len(sys.argv) > 2 else ""
phase     = sys.argv[3] if len(sys.argv) > 3 else "post"

# TODO: your pass logic here
