import os
import sys
import time

# Change cwd to the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from nlp_parser import parse_prompt

print("Testing simple query...")
start_time = time.time()
res1 = parse_prompt("a guy")
end_time = time.time()
print(f"Result: {res1}")
print(f"Time taken: {end_time - start_time:.4f} seconds\n")

print("Testing complex query...")
start_time = time.time()
res2 = parse_prompt("a red car that is parked")
end_time = time.time()
print(f"Result: {res2}")
print(f"Time taken: {end_time - start_time:.4f} seconds\n")
