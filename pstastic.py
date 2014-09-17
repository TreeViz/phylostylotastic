from ete2 import Nexml, TreeStyle, NodeStyle
import tinycss
import sys
import os

if len(sys.argv) < 2:
    print("Command line argument required: NeXML file")
    exit(-1)

custom_stylesheet = None
if len(sys.argv) > 2:
    if sys.argv[2]:
        custom_stylesheet = sys.argv[2]
    
nexml = Nexml()
nexml.build_from_file(sys.argv[1])

def build_tree_style(tree):
    # use our simple TSS cascade to prepare an ETE TreeStyle object
    sheets = gather_tss_stylesheets(tree)
    if len(sheets) == 0:
        return None

    # Some styles can be applied to the entire tree
    ts = TreeStyle()
    # For nodes (and other elements?), build an ordered set of TSS rules 
    # to apply to each element in our layout function
    node_rules = []

    for s in sheets:
        ts, tss_cascade = apply_stylesheet(
            stylesheet=s, 
            tree_style=ts,
            node_rules=node_rules)

    # Use a layout function to test each node against TSS selectors?
    def apply_tss(node):
        node_style = NodeStyle()
        for rule in node_rules:
            # Test this node against each selector
            if test_node_against_selector(node, rule.selector):
                node_style, node = apply_node_rule(rule, node_style, node)
        node.set_style(node_style);
        return node

    # apply this layout function to each node as it's rendered
    ts.layout_fn = apply_tss
    return ts

def test_node_against_selector(node, selector):
    # TODO: Here we can interpret our selectors 
    # in the context of a live tree (vs. a DOM)
    return True

def apply_node_rule(rule, node_style, node):
    for style in rule.declarations:
        print(style)
    node_style["shape"] = "sphere"
    node_style["fgcolor"] = "orange"
    node_style["hz_line_type"] = 2
    node_style["hz_line_color"] = "#cc99cc"
    node_style["size"] = 10
    return node_style, node

def gather_tss_stylesheets(tree):
    sheets = []
    # if a stylesheet was provided, this is all we should use
    if custom_stylesheet:
        sheets.append(custom_stylesheet)
        return sheets

    # TODO: add any default stylesheet for this tool?

    # add any linked stylesheets in the NeXML file
    # add any embedded stylesheets in the NeXML file
    nexml_doc = tree.nexml_project
    if nexml_doc:
        # TODO: can we retrieve <?xml-stylesheet ... ?> elements?
        pass

    # TODO: add any linked stylesheets just for this tree

    # TODO: add any embedded stylesheets in this tree

    return sheets 

# Apply styles to an existing TreeStyle object and return it
def apply_stylesheet(stylesheet, tree_style, node_rules):
    if (not stylesheet):
        print("Missing stylesheet!")
        return tree_style, node_rules
    if (not tree_style):
        print("Missing tree_style!")
        return None, None

    # parse the TSS from its CSS-style syntax
    parser = tinycss.make_parser('page3')
    # load the stylesheet using its path+filename
    stylesheet = os.path.abspath(stylesheet)
    style = parser.parse_stylesheet_file(css_file=stylesheet)
    print("Found %i rules, %i errors" % 
       (len(style.rules),len(style.errors)))
    if len(style.errors) > 0:
        for e in style.errors:
            print(e)

    # walk the TSS rules and translate them into TreeStyle properties
    # or add them to the node_rules collection
    for r in style.rules:
        if r.at_keyword:
            # this is an ImportRule, MediaRule, or the like
            # TODO: support @import, etc?
            print("Unsupported at-rule:")
            print(r)
        else:
            # it's a normal CSS RuleSet
            #print("TSS RuleSet:")
            #print("  selector: %s" % r.selector.as_css())
            #print("  as list:  %s" % repr(r.selector))
            #print("  declarations: %s" % r.declarations)

            # add every rule to node tests 
            node_rules.append(r)

            # TODO: interpret its selector to find targets
            # see https://pythonhosted.org/tinycss/parsing.html

            # TODO: modify the current TreeStyle to reflect its declarations
            #tree_style.mode = 'c'  # circular
            #tree_style.show_leaf_name = False
            #tree_style.show_branch_length = True

    return tree_style, node_rules

# render a series of SVG files (one for each tree)
for trees in nexml.get_trees():
    tree_index = 0
    for tree in trees.get_tree():
        tree_index += 1
        ts = build_tree_style(tree)
        tree.render("output%d.svg" % tree_index, tree_style=ts)

        # let's try the interactive QT viewer
        tree.show(tree_style=ts)

