"""
from myClasses import DOMNode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


import pytest

#i want to initialize a tree structure for testing
root_node = DOMNode(tag='div', classes=['center point-center'])
sline_node = DOMNode(tag='div', classes=['sline'])
root_node.add_child(sline_node)
for i in range (1,34):
    exam_var_block_node = DOMNode(tag='div', classes=[f'st{i}'], attrs={'id': 'test'})
    if i < 9:
        # these has an intermediary node that serves as a container which doesnt exists for i >=9
        sline_node.add_child(exam_var_block_node)

    else:
        root_node.add_child(exam_var_block_node)
    
    exam_var_block_node.add_child(DOMNode(tag='div', classes=['topline clearfix']))
    exam_var_block_node.add_child(DOMNode(tag='div', classes=['sline']))

    for child in exam_var_block_node.children:
        if 'topline clearfix' in child.classes:
            child.add_child(DOMNode(tag='div', classes=['head-fl clearfix']))
            child.children[0].add_child(DOMNode(tag='span')) # this span will contain the type_text for exam variant
        else:
            child.add_child(DOMNode(tag='div', classes=['gkzt-xueke mtT_30 clearfix']))
            # here i need to add multiple li children but the issue is i dont have a loop variable, i don't know how many li to add
            # this heavily depends on the exam variant so this node should have an extra attribute to indicate how many subjects it has
            for j in range(5):  # assuming we want to add 5 li elements for testing
                child.children[0].add_child(DOMNode(tag='li'))
                child.children[0].children[j].add_child(DOMNode(tag='div', classes=["word-xueke"]))  # each li has an a child . text has the subject name
                child.children[0].children[j].children[0].add_child(DOMNode(tag='div', classes=["xueke-a"]))  # each li has an a child
                for i in range (3):
                    child.children[0].children[j].children[0].children[0].add_child(DOMNode(tag='a'))  # each xueke-a has multiple a children each a is a link: link for exam, link for solution, link for analysis

"""

"""
critique:
| Problem                      | Solution                                              |
| ---------------------------- | ----------------------------------------------------- |
| Hard to debug                | Every node has metadata describing its role           |
| HTML changes                 | You only update the blueprint, not the logic          |
| No dynamic adaptability      | You populate children dynamically using Selenium      |
| Hard to understand hierarchy | You can visualize or print the tree with descriptions |
| Mixed concerns               | Separation between model, data, and logic             |

Overall Architecture:
Blueprint (JSON / dict)
↓
DOMBuilder (reads blueprint → creates structure)
↓
DOMNode (each with tag, classes, meta)
↓
SeleniumBinder (attaches web_element dynamically) this step works with the dombuilder, like for example when we are building the children dynamically based on the number of subjects available
↓
Query Engine / Scraper Logic

step 1: building json blueprints for each page structure
the json must be dynamic, meaning it should allow for variable number of children based on attributes, e.g., number_of_subjects: 5 and most of the structures are repeated just with different number of children/ 

"""

"""
import json
from tree_builder import TreeBuilder  # Or your class name

# --- Step 1: Load JSON schema ---
with open("schemas/gaokao_v1.json", "r", encoding="utf-8") as f:
    schema = json.load(f)

# --- Step 2: Initialize TreeBuilder ---
builder = TreeBuilder(schema)

# --- Step 3: Build the tree ---
# The root node schema is usually the main JSON minus templates
root_node_schema = {k: v for k, v in schema.items() if k != "templates"}
templates = schema.get("templates", {})

root_node = builder.build_tree(root_node_schema, templates)

# --- Step 4: Helper function to print the tree ---
def print_dom_tree(node, depth=0):
    indent = "  " * depth
    print(f"{indent}{node.tag} — {node.description} — classes: {node.classes}")
    for child in node.children:
        print_dom_tree(child, depth + 1)

# --- Step 5: Print the full tree ---
print_dom_tree(root_node)
"""

"""
now to add web_element bidings using selenium
the parent nodes where the children are (repeated) must have the webelement set for quick querying
this question:
    how this node structure will interact with the selenium scraper logic?
    how this node structure will be used to query the web page?
    how this node structure will be used to do parallel scraping?
    will this node structure actually reduce querying complexity (time and space) ?
    how will this node structure handle dynamic changes in the web page? aka reproducibility
    
"""

from selenium import webdriver
import json
from tree_builder import TreeBuilder




driver = webdriver.Chrome()
with open("schemas/gaokao_v1.json", "r") as f:
    schema = json.load(f)

builder = TreeBuilder(driver, "https://gaokao.eol.cn/e_html/gk/gkst/", schema)

root = builder.build_and_annotate()

log_counter= 0
root.print_dom_tree()
#print("number of sti children:", len(root.children[1].children))
#print("number of root children is:", len(root.children)) # should output 26 but only outputs 2
#(builder.find_in_tree("id","st33")).print_dom_tree()

"""
current = root
while current:
    print("this is the children of the current node:")
    print("number")
    print("characteristics")
 
"""