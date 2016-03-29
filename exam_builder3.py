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
TODO: Move the entire build section out of the yaml header and to command 
line input args. So the header should be just jinja2 vars, and there 
should be an easy way to specify other vars as input args as well. 

It should look something like:

exam_builder -o doc/Unit5_Exam -t lib/templates/mc_exam.template -q build/q_order_v0.txt

...etc.

Remember to do something with the out dir. Right now, it is very Goldbergian, where
out is specified in the makefile, but the subs are specified in the yaml. 

Also, just remove preprocess, as it is unnecessary and cumbersome to call from within 
exam_builder. Much better to just call the preprocess script from the makefile as needed. 
"""

"""
TODO: Add topics feature, where each question can belong to one or more topics, 
and then the user can specify which topics to include in an exam, and all of the 
questions that belong to that topic will be included. Question order will probably 
have to be improved concurrently.
"""

"""
TODO: Add 'follows' feature, where questions can be specified to occur following another. 
One use case is that a figure can be attached to a question, and multiple questions can 
refer to 'the fig above' 

Possible format: 

---
question: Given the diagram above...
answer: no
follows:
    var: image
    val: anatomy-diagram.svg

---
question: Given the diagram above...
answer: yes
image: anatomy-diagram.svg

The var and val must be unique, so an image var could work, or specify a separate var like id. The 
relative order of the to-be-moved questions should be respected, as well as the unmoved questions. Moved 
questions should appear directly after the specified question. Eg., let's say questions 5,6, & 7 
are all specified to follow question 4, and let's say the order is random and 7,3,4,8,1,5,9,6,2.
The resulting q order should be 3,(4,7,5,6),8,1,9,2

"""

"""
TODO: Improve question and answer order to be more robust, flexible, and intuitive. However,
keep in mind that if the command-line design suggested above is implemented, persistent 
q and a orders will not be necessary, since exam_builder will then only ever be aware of
a single template at a time. So, maybe big changes here are not necessary. 
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

def main(y, t, o, q=None, a=None, v=None, o=None, l=False):

    # Read in file. Take first section as yml block, everything else as questions
    raw = open(y, 'r').read()
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
                do_log('including file: {}'.format(inc))
                metadata.update(yaml.load(open(inc)))

    # Add variables to the jinja2 context
    for key,val in metadata.items():
        if isinstance(key, str):
            context[key] = val
    for var in v:
        key,val = var.split(":")
        context[key] = val

    # Process some settings
    if 'omit' not in metadata.keys():
        metadata['omit'] = []
    elif isinstance(metadata['omit'], str):
        metadata['omit'] = [metadata['omit']]
    if 'answer_options' in metadata.keys():
        answer_options = metadata['answer_options']
    else:
        answer_options = "".join([chr(c) for c in np.arange(26)+97])

#    version_options = "".join([chr(c) for c in np.arange(26)+65])

    if 'preprocess' in metadata.keys() and metadata['preprocess'] is not None:
        do_log('running preprocess stage: {}'.format(metadata['preprocess']))
        os.system(metadata['preprocess'])

    out_questions = []
    question_order = q

    if question_order.lower() == 'natural':
        do_log("Question order: Natural")
        question_order_n = np.arange(len(items_list))
    elif question_order.lower() == 'random':
        do_log("Question order: Random")
        question_order_n = np.arange(len(items_list))
        np.random.shuffle(question_order_n)
    elif os.path.isfile(question_order):
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

    if os.path.isfile(a):
        do_log("Question order: Specified by file {}".format(a))
        answer_order_n = np.loadtxt(a, dtype=np.int32)
    else:
        if a.lower() == 'random':
            do_log("Answer order: Random")
        else:
            do_log("Answer order: Natural")
        answer_order_n = np.zeros((len(items_list), 26), dtype=np.int32)
        for n in np.arange(len(items_list)):
            answer_order = np.arange(26)
            if a.lower() == 'random':
                np.random.shuffle(answer_order)
            answer_order_n[n] = answer_order


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
    context['questions'] = out_questions

    template = t
    filename = o
    if not os.path.isfile(template):
        raise IOError("*** Template not found: {}".format(template))
    else:
        do_log("Using template: {}".format(template))
        tpath,tfname = os.path.split(template)
        template_environment = jinja2.Environment(autoescape=False,
                                                    loader=jinja2.FileSystemLoader(tpath),
                                                    trim_blocks=True,
                                                  )

        markdown = template_environment.get_template(tfname).render(context)

        if metadata.has_key('appendix') and metadata['appendix'] is not None:
            do_log("Adding appendix: {}".format(metadata['appendix']))
            appendix = open(build['appendix'], 'r').read()
            markdown += appendix

        markdown.decode('ascii')

        do_log("Writing to file: {}".format(context['filename']))

        # Don't use dest, which allows filename to contain path info
        d = os.path.dirname(context['filename'])
        if not os.path.exists(d):
            os.makedirs(d)

        with open(context['filename'], 'w') as f:
            f.write(markdown.encode('utf8'))
    else:
        raise IOError("*** Template not found: {}".format(template))

#    version_i += 1
#
#        build_i += 1

    if 'postprocess' in metadata.keys() and metadata['postprocess'] is not None:
        do_log('Running postprocess stage: {}'.format(metadata['postprocess']))
        os.system(metadata['postprocess'])







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
    l = args.log

    main(y, t, o, q, a, v, o, l)
