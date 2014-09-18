
from pprint import pprint
import tinycss

# Use a layout function to test each node against TSS selectors?
def apply_tss(node):
    node_style = NodeStyle()
    for rule in node_rules:
        # Test this node against each selector
        if test_node_against_selector(node, rule.selector):
            node_style, node = apply_node_rule(rule, node_style, node)
    node.set_style(node_style);
    return node

def test_node_against_selector(node, selector):
    # Interpret a selector in the context of a live tree (vs. a DOM)
    # and return True if this node matches (or False). 
    #
    # We'll optimistically hope that this node is a match, but walk 
    # the series of tokens looking for a reason to fail it.

    # keep track of the most recently specified context element(s), since we
    # will often test their properties
    context_elements = [ node.get_tree_root() ]

    # wait for descendant name after a whitespace token
    waiting_for_descendant_element_name = True

    # wait for a class (attribute) name after a '.' token
    waiting_for_class_name = False

    for token in selector:
        #pprint("NEW context_elements:")
        #pprint(context_elements)

        if token.type == u'S':  # string
            # ASSUME this is whitespace?
            waiting_for_descendant_element_name = True
            waiting_for_class_name = False

        elif token.type == u'IDENT': # element or classname
            if waiting_for_descendant_element_name:
                if token.value == 'node':
                    # gather all descendant nodes
                    new_context_elements = []
                    for e in context_elements:
                        new_context_elements.extend(e.get_descendants())
                else:
                    # ignore other element names for now
                    report_unsupported_element_selector(token.value)
            elif waiting_for_class_name:
                # test for matching classname
                new_context_elements = []
                for e in context_elements:
                    if e.nexml_node.anyAttributes_.has_key( 'class'):
                        if e.nexml_node.anyAttributes_['class'] == token.value:
                            new_context_elements.append(e)
            else:
                print("Unexpected IDENT in selector: %s" % token.value)

        elif token.type == u'[': # property test
            # compare this property or metadata
            context_elements = [e for e in context_elements 
                if compare_property(e,token)]
            
            pass

        elif token.type == u'DELIM':
            if token.value == '.':
                waiting_for_class_name = True
                waiting_for_descendant_element_name = False
            else:
                print("Unsupported DELIM in selector: %s" % token.value)

        else:
            print("Unexpected token type (%s) in selector: %s" % 
                (token.type, token.value))
    
    return True


TREE_ONLY_SELECTOR_TOKENS = ("canvas", "tree", "scale")
TREE_STYLE_PROPERTIES = ("layout","border",)
# See the full list at 
# http://pythonhosted.org/ete2/reference/reference_treeview.html#treestyle

NODE_STYLE_PROPERTIES = ("color", "background-color", "size", "shape",)
# See the full list at 
# http://pythonhosted.org/ete2/reference/reference_treeview.html#ete2.NodeStyle


# Report unsupported style properties, etc. *just once*

unsupported_tree_styles = []
def report_unsupported_tree_style(name):
    if name not in unsupported_tree_styles:
        print("ETE TreeStyle does not provide '%s'" % name)
        unsupported_tree_styles.append(name)

unsupported_node_styles = []
def report_unsupported_node_style(name):
    if name not in unsupported_node_styles:
        print("ETE NodeStyle does not provide '%s'" % name)
        unsupported_node_styles.append(name)

unsupported_element_selectors = []
def report_unsupported_element_selector(name):
    if name not in unsupported_element_selectors:
        print("ETE does not support element selector '%s'" % name)
        unsupported_element_selectors.append(name)


def apply_node_rule(rule, node_style, node):
    for style in rule.declarations:
        # N.B. name is always normalized lower-case
        # Translate TSS/CSS property names into ETE properties
        if style.name not in NODE_STYLE_PROPERTIES:
            report_unsupported_node_style(style.name)
            continue

        # TODO: handle dynamic (data-driven) values in all cases!
        if style.name == "color":
            node_style["fgcolor"] = style.value.as_css()
        elif style.name == "background-color":
            node_style["bgcolor"] = style.value.as_css()
        else:
            # by default, use the same name as in TSS
            try:
                setattr(node_style, style.name, style.value.as_css())
            except:
                print("Invalid property for node: %s" % style.name);
                pass

        # TODO: consider style.priority? ('important')

    # node_style["shape"] = "sphere"
    # node_style["hz_line_type"] = 2
    # node_style["hz_line_color"] = "#cc99cc"
    # node_style["size"] = 10

    return node_style, node

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

            # Some rules should modify the current TreeStyle
            if r.selector.as_css() in TREE_ONLY_SELECTOR_TOKENS:
                for style in r.declarations:
                    if style.name not in TREE_STYLE_PROPERTIES:
                        report_unsupported_tree_style(style.name)
                        continue
                    if style.name == "layout":
                        its_value = style.value.as_css()
                        if its_value == "rectangular":
                            tree_style.mode = "r"
                        elif its_value == "circular":
                            tree_style.mode = "c"
                    elif style.name == "border":
                        # crappy support for this
                        its_value = style.value.as_css()
                        if its_value == "none":
                            tree_style.show_border = False
                        else:
                            tree_style.show_border = True
                    else:
                        setattr(tree_style, style.name, style.value.as_css())

            #tree_style.mode = 'c'  # circular
            #tree_style.show_leaf_name = False
            #tree_style.show_branch_length = True
                
    return tree_style, node_rules
        
def compare_property(element, test_container):
    # Split this token to get property name, operator, and value;
    # compare to this element's properties (including typical
    # metadata) and return the result
    
    # find the operator (DELIM) and concat the rest
    test_property = ''
    test_operator = None
    test_value = None
    for token in test_container.content:
        if token.type == u'DELIM':
            test_operator = token.value
        elif test_operator is None:
            # keep adding to the property name
            test_property = "%s%s" % (test_property, token.value,)
        else:
            if test_value is None:
                test_value = token.value
            else:
                # keep adding to the test value (ASSUMES a string)
                test_value = "%s%s" % (test_value, token.value,)
        
    el_value = get_property_or_meta(element, test_property)
    if el_value is None:
        return False
    else:
        if test_operator is None:
            # match on the mere existence of this property
            return True
        else:
            # use the operator and value to work it out
            if test_operator == '=':
                # test for equality
                return el_value == test_value
            elif test_operator == '!=':
                # test for inequality
                return el_value != test_value
            # value comparisons (alpha, numeric?)
            elif test_operator == '>':
                return el_value > test_value
            elif test_operator == '<':
                return el_value < test_value
            elif test_operator == '>=':
                return el_value >= test_value
            elif test_operator == '<=':
                return el_value <= test_value
            # string comparisons (startswith, endswith, anywhere)
            elif test_operator == '^=':
                return el_value.startswith(test_value)
            elif test_operator == '$=':
                return el_value.endswith(test_value)
            elif test_operator == '*=':
                return el_value.find(test_value) != -1

def get_property_or_meta(element, property_name):
    # check first for an attribute by this name
    if getattr(element, property_name, None):
        return getattr(element, property_name, None)
    # ...then for a child META element
    for metatag in element.nexml_node.meta:
        # ASSUMES there's just one matching metatag!
        if metatag.property == property_name:
            # TODO: normalize to lower-case?
            return metatag.content
    # TODO: ...finally, check for a distant META tag that 
    # points to this element?
    return None

