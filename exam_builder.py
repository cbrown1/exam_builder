#!/usr/bin/python
# -*- coding: utf-8 -*-

"""exam_builder: Simple script to help building exams

    The usecase is large lecture courses where anything other than multiple-
    choice exams is not feasible. In these cases, it is often desirable to have
    multiple versions of an exam, with both question order and multiple-choice
    answer order randomized, to minimize cheating. This is where this script
    can help. Questions are stored in a yml file, along with some additional
    variables to dictate what is build and how. Because it uses jinja2
    templating, your output file format can be whatever you want. But a good
    choice is to write to markdown files which can then be processed into pdfs
    with pandoc.

"""

"""
TODO: Answers needs attention. out_answer['option'] is set in process_questions (~47), 
and also in main (~183). Also, ~117 has code that is needed to run but needs fixing
because we are not using yaml header data anymore. Same goes for omit. 
"""

import os
import sys
import argparse
import numpy as np
import yaml
import jinja2

log = False

def process_questions(in_items):

    out_items = []
    answer_options = "".join([chr(c) for c in np.arange(26)+97])
    question_i = 0
    for in_item in in_items:
        out_item = {}
        out_item['question'] = in_item['question'].encode('ascii')
        out_item['ind'] = question_i
        if in_item.has_key('answers'):
            answer_i = 0
            out_answers = []
            for in_answer in in_item['answers']:
                out_answer = {}
                out_answer['ind'] = answer_i
                out_answer['option'] = answer_options[answer_i]
                out_answer['answer_scored'] = in_answer
                if str(in_answer).startswith("+ "):
                    out_answer['answer'] = in_answer[2:]
                    out_item['correct_ind'] = answer_i
                else:
                    out_answer['answer'] = in_answer
                answer_i += 1
                out_answers.append(out_answer)
            out_item['answers'] = list(out_answers)
        elif in_item.has_key('answer'):
            out_item['answer'] = in_item['answer']
        else:
            out_item['answer'] = ""

        for key,val in in_item.iteritems():
            if key not in ['question', 'answer', 'answers']:
                out_item[key] = val

        out_items.append(out_item)
        question_i += 1
    return out_items

def main(yaml_file, template_file, output_file, question_order=None, a=None, variables=None, m=None, includes=None, l=False):

    global log
    log = l

    # Read in file. Take first section as yml block, everything else as questions
    raw = open(yaml_file, 'r').read()
    preamble = raw.split('---')[0]
    metadata = yaml.load(preamble)
    body = raw.replace(preamble, '')
    items_list = list(yaml.load_all(body))
    questions = process_questions(items_list)
    context = {}

    # Process includes
    if 'include' in metadata.keys():
        if isinstance(metadata['include'], str):
            metadata['include'] = [metadata['include']]
        for inc in metadata.get("include", []):
            if os.path.isfile(inc):
                do_log('including file [metadata]: {}'.format(inc))
                metadata.update(yaml.load(open(inc)))
            else:
                do_log('include file not found [metadata]: {}'.format(inc))
    if includes:
        for inc in includes:
            if os.path.isfile(inc):
                do_log('including file [command line]: {}'.format(inc))
                metadata.update(yaml.load(open(inc)))
            else:
                do_log('include file not found [command line]: {}'.format(inc))

    # Add variables to the jinja2 context
    for key,val in metadata.items():
        if isinstance(key, str):
            context[key] = val
    if variables:
        for var in variables:
            key,val = var.split(":")
            context[key] = val

#    # Process some settings
#    # TODO: m is omit string input arg
    if 'omit' not in metadata.keys():
        metadata['omit'] = []
    elif isinstance(metadata['omit'], str):
        metadata['omit'] = [metadata['omit']]
    if 'answer_options' in metadata.keys():
        answer_options = metadata['answer_options']
    else:
        answer_options = "".join([chr(c) for c in np.arange(26)+97])

    out_questions = []

    if not question_order or (question_order and question_order.lower() == 'natural'):
        do_log("Question order: Natural")
        question_order_n = np.arange(len(items_list))
    elif question_order and question_order.lower() == 'random':
        do_log("Question order: Random")
        question_order_n = np.arange(len(items_list))
        np.random.shuffle(question_order_n)
    elif question_order and os.path.isfile(question_order):
        do_log("Question order: Specified by file {}".format(question_order))
        question_order_n = np.loadtxt(question_order, dtype=np.int32)
    else:
        do_log("Question order: Specified by string {}".format(question_order))
        question_order_n,store = str_to_range(question_order)
        if store:
            if random_orders.has_key(store):
                question_order_n = random_orders[store]
            else:
                random_orders[store] = question_order_n
    if 0 not in question_order_n:
        question_order_n = question_order_n - 1

    if a and os.path.isfile(a):
        do_log("Question order: Specified by file {}".format(a))
        answer_order_n = np.loadtxt(a, dtype=np.int32)
    else:
        if a and a.lower() == 'random':
            do_log("Answer order: Random")
        else:
            do_log("Answer order: Natural")
        answer_order_n = np.zeros((len(items_list), 26), dtype=np.int32)
        for n in np.arange(len(items_list)):
            answer_order = np.arange(26)
            if a and a.lower() == 'random':
                np.random.shuffle(answer_order)
            answer_order_n[n] = answer_order

    question_i = 0
    for i in question_order_n:
        in_question = questions[i]
        if in_question in metadata['omit']:
            do_log("Omitting question {:}".format(i))
        else:
            out_question = {}
            out_question['n'] = question_i + 1
            out_question['n_orig'] = in_question['ind'] + 1
            out_question['question'] = in_question['question']

            for key,val in in_question.iteritems():
                if key not in ['question', 'answer', 'answers']:
                    out_question[key] = val

            out_answers = []
            if in_question.has_key('answers'):
                answer_i = 0
                for j_ in np.arange(len(in_question['answers'])): # answer_order_n[question_i]:
                    j = int(answer_order_n[question_i][j_])
                    this_option = answer_options[answer_i]
                    out_answer = {}
                    out_answer['ind'] = answer_i
                    out_answer['option'] = this_option
                    out_answer['answer_scored'] = in_question['answers'][j]['answer_scored']
                    out_answer['answer'] = in_question['answers'][j]['answer']
                    if str(out_answer['answer_scored']).startswith("+ "):
                        out_question['correct_ind'] = out_answer['ind'] #answer_i
                        out_question['correct_option'] = out_answer['option'] #answer_options[int(in_question['correct_ind'])] #answer_i]
                        out_question['correct_answer'] = out_answer['answer']
                    answer_i += 1
                    out_answers.append(out_answer)
            elif 'answer' in in_question.keys():
                out_answer = {'answer': in_question['answer']}
                out_answers.append(out_answer)
                out_question['correct_ind'] = 0
                out_question['correct_option'] = ""
                out_question['correct_answer'] = in_question['answer']
            else:
                out_answer = {'answer': ""}
                out_answers.append(out_answer)
                out_question['correct_ind'] = None
                out_question['correct_option'] = ""
                out_question['correct_answer'] = None

            out_question['answers'] = out_answers
        out_questions.append(out_question)
        question_i += 1

    # Begin group_with...
    gw_inds = {}
    out_questions_inds = []
    # Loop through questions, find followers
    for i in range(len(out_questions)):
        # Check if item is a follower
        if out_questions[i].has_key('group_with'):
            # Get key and val
            val = out_questions[i]['group_with']
            #print("Found follower: {:}, group: {}".format(i, val))
            # Find ind of leader
            ind = None
            for j in range(len(out_questions)):
                #print ("  Checking for leader: {:}".format(j))
                if out_questions[j].has_key('group') and out_questions[j]['group'] == val:
                    #print ("    Found leader: {:}".format(j))
                    ind = j
                    break
            if ind is None:
                do_log("Warning; group_with target not found! Adding question in place. Details: question ind: {:}, group not found: {}".format(i, val))
                out_questions_inds.append(i)
            else:
                #print("Got follower: {:}, leader: {:}".format(i, ind))
                # Add follower to list
                if ind in gw_inds.keys():
                    # Leader already exists, just append follower to list
                    gw_inds[ind].append(i)
                else:
                    # Leader key does not exists, add both leader and follower inds
                    gw_inds[ind] = [i]
        else:
            out_questions_inds.append(i)

    if len(gw_inds) > 0:

        out_questions_gw = []
        # Loop through all questions again, add to new list
        for i in out_questions_inds:
            #print("Adding item: {:}".format(i))
            this = out_questions[i]
            if i in gw_inds.keys():
                this['group_start'] = True
            out_questions_gw.append(this)
            # If this item is a leader
            if i in gw_inds.keys():
                #print ("  Item {:} has follower(s)".format(i))
                # Loop through followers
                for j in gw_inds[i]:
                    #print ("    Adding follower {:}".format(j))
                    # Add question items to questions list
                    this = out_questions[j]
                    if j == len(gw_inds)-1:
                        this['group_end'] = True
                    out_questions_gw.append(this)
        context['questions'] = out_questions_gw
    else:
        context['questions'] = out_questions
    # End group_with...

    context['filename'] = output_file
    if not os.path.isfile(template_file):
        raise IOError("*** Template not found: {}".format(template_file))
    else:
        do_log("Using template: {}".format(template_file))
        tpath,tfname = os.path.split(template_file)
        template_environment = jinja2.Environment(autoescape=False,
                                                    loader=jinja2.FileSystemLoader(tpath),
                                                    trim_blocks=True,
                                                  )

        output = template_environment.get_template(tfname).render(context)

        if metadata.has_key('appendix') and metadata['appendix'] is not None:
            do_log("Adding appendix: {}".format(metadata['appendix']))
            appendix = open(build['appendix'], 'r').read()
            output += appendix

        output.decode('ascii')

        if not o:
            do_log("No output file specified, writing to stdout")
            return output
        else:
            do_log("Writing to file: {}".format(context['filename']))

            # Don't use dest, which allows filename to contain path info
            d = os.path.dirname(context['filename'])
            if not os.path.exists(d):
                os.makedirs(d)

            with open(context['filename'], 'w') as f:
                f.write(output.encode('utf8'))





def str_to_range(s):
    """Translate a print-range style string to a list of integers

      The input should be a string of comma-delimited values, each of
      which can be either a number, or a colon-delimited range. If the
      first token in the list is the string "random" or "r", then the
      output list will be randomized before it is returned ("r,1:10").

      >>> str_to_range('1:5, 20, 22')
      [1, 2, 3, 4, 5, 20, 22]
    """
    s = s.strip()
    randomize = False
    store = None
    if s.count(":"):
        tokens = [x.strip().split(":") for x in s.split(",")]
    else:
        tokens = [x.strip().split("-") for x in s.split(",")]

    if tokens[0][0][0] == "r":
        randomize = True
        if len(tokens[0][0]) > 1:
            store = tokens[0][0][1:]
        tokens = tokens[1:]

    # Translate ranges and enumerations into a list of int indices.
    def parse(x):
        if len(x) == 1:
            if x == [""]:  # this occurs when there are trailing commas
                return []
            else:
                #return map(int, x)
                return [int(x[0])-1]
        elif len(x) == 2:
            a,b = x
            return range(int(a)-1, int(b))
        else:
            raise ValueError

    result = reduce(list.__add__, [parse(x) for x in tokens])

    if randomize:
        np.random.shuffle(result)

    return result,store

def do_log(message):
    """Writes info to the console
    """
    if log and message is not None and message != '':
        print(message)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Simple script to help building exams")
    parser.add_argument("-y", "--yaml_file",
                        help="the path to a yaml file representing exam data")

    parser.add_argument("-t", "--template", 
                        help="The template to use.")

    parser.add_argument("-o", "--output_dir",
                        help="output directory.")

    parser.add_argument("-q", "--question_order", default=None, 
                        help="A file indicating the question order. File should be text, with one value per row.")

    parser.add_argument("-a", "--answer_order", default=None, 
                        help="A file indicating the answer order. File should be text, with one row per question containing space-delimited numbers.")

    parser.add_argument("-v", "--variable", default=None, action='append', 
                        help="A var:val pair for use in the jinja2 template. Reuse as necessary.")

    parser.add_argument("-m", "--omit", default=None, 
                        help="A comma-delimited list of question numbers to omit.")

    parser.add_argument("-i", "--include", default=None, action='append', 
                        help="Another yaml file to include. Reuse as necessary.")

    parser.add_argument("-log", "--log", action='store_true', default=False,
                        help="Include to turn on logging.")

    args = parser.parse_args()

    y = args.yaml_file
    t = args.template
    o = args.output_dir
    q = args.question_order
    a = args.answer_order
    v = args.variable
    m = args.omit
    i = args.include
    l = args.log

    ret = main(y, t, o, q, a, v, m, i, l)
    print( ret )
