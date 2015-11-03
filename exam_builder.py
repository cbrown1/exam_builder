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

def main(yaml_file, dest="."):

    # Read in file. Take first section as yml block, everything else as questions
    raw = open(yaml_file, 'r').read()
    preamble = raw.split('---')[0]
    metadata = yaml.load(preamble)
    body = raw.replace(preamble, '')
    items_list = list(yaml.load_all(body))
    questions = process_questions(items_list)
    context = {}
    random_orders = {}

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

    # Process some settings
    if 'omit' not in metadata.keys():
        metadata['omit'] = []
    elif isinstance(metadata['omit'], str):
        metadata['omit'] = [metadata['omit']]
    if 'answer_options' in metadata.keys():
        answer_options = metadata['answer_options']
    else:
        answer_options = "".join([chr(c) for c in np.arange(26)+97])

    version_options = "".join([chr(c) for c in np.arange(26)+65])

    if 'preprocess' in metadata.keys() and metadata['preprocess'] is not None:
        do_log('running global preprocess stage: {}'.format(metadata['preprocess']))
        os.system(metadata['preprocess'])

    # Loop through builds
    build_i = 0
    for build in metadata['build']:
        if 'filename' in build.keys():
            build_name = build['filename']
        else:
            build_name = str(build_i)
        if not build.has_key('question_order'):
            build['question_order'] = ['natural']
        elif isinstance(build['question_order'], str):
            build['question_order'] = [build['question_order']]

        if not build.has_key('answer_order'):
            build['answer_order'] = 'natural'
        if isinstance(build['answer_order'], str):
            aorder = build['answer_order']
            build['answer_order'] = []
            for order in build['question_order']:
                build['answer_order'].append(aorder)

        if 'preprocess' in build.keys() and build['preprocess'] is not 'None':
            do_log('Build: {}; running preprocess stage: {}'.format(build_name, build['preprocess']))
            os.system(build['preprocess'])

        # Loop through versions
        version_i = 0
        for version in build['question_order']:
            version_name = version_options[version_i]
            out_questions = []
            question_order = version
            context['version'] = version_name
            if question_order.lower() == 'natural':
                do_log("Build: {}, version: {}; Using natural question order".format(build_name, version_name))
                question_order_n = np.arange(len(items_list))
            elif question_order.lower() == 'random':
                do_log("Build: {}, version: {}; Using random question order".format(build_name, version_name))
                question_order_n = np.arange(len(items_list))
                np.random.shuffle(question_order_n)
            elif os.path.isfile(question_order):
                do_log("Build: {}, version: {}; Using specified question order from file: {}".format(build_name, version_name, question_order))
                question_order_n = np.loadtxt(question_order, dtype=np.int32)
            else:
                do_log("Build: {}, version: {}; Using specified question order: {}".format(build_name, version_name, question_order))
                question_order_n,store = str_to_range(question_order)
                if store:
                    if random_orders.has_key(store):
                        question_order_n = random_orders[store]
                    else:
                        random_orders[store] = question_order_n
            if 0 not in question_order_n:
                question_order_n = question_order_n - 1

            if build['answer_order'][version_i] == 'random':
                do_log("Build: {}, version: {}; using random answer order".format(build_name, version_name))
                answer_order_n = np.zeros((len(items_list), 26), dtype=np.int32)
                for n in np.arange(len(items_list)):
                    answer_order = np.arange(26)
                    np.random.shuffle(answer_order)
                    answer_order_n[n] = answer_order
            elif os.path.isfile(build['answer_order'][version_i]):
                do_log("Build: {}, version: {}; Using specified answer order from file: {}".format(build_name, version_name, build['answer_order'][version_i]))
                answer_order_n = np.loadtxt(build['answer_order'][version_i], dtype=np.int32)
            else:
                do_log("Build: {}, version: {}; using natural answer order".format(build_name, version_name))
                answer_order_n = np.zeros((len(items_list), 26), dtype=np.int32)
                for n in np.arange(len(items_list)):
                    answer_order = np.arange(26)
                    answer_order_n[n] = answer_order

            question_i = 0
            for i in question_order_n:
                in_question = questions[i]
                if in_question in metadata['omit']:
                    do_log("Build: {}, version: {}; skipping question {:}".format(build_name, version_name, i))
                else:
                    out_question = {}
                    out_question['n'] = question_i + 1
                    out_question['n_orig'] = in_question['ind'] + 1
                    out_question['question'] = in_question['question']

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

            for filename,template in build.get("template", []).iteritems():
                context['filename'] = os.path.join(dest,"{}_v{:}.md".format(filename, version_i))

                if os.path.isfile(template):
                    do_log("Build: {}, version: {}; Using template: {}".format(build_name, version_name, template))
                    tpath,tfname = os.path.split(template)
                    template_environment = jinja2.Environment(autoescape=False,
                                                                loader=jinja2.FileSystemLoader(tpath),
                                                                trim_blocks=True,
                                                              )

                    markdown = template_environment.get_template(tfname).render(context)

                    if build.has_key('appendix') and build['appendix'] is not None:
                        do_log("Build: {}, version: {}; Adding appendix: {}".format(build_name, version_name, build['appendix']))
                        appendix = open(build['appendix'], 'r').read()
                        markdown += appendix

                    markdown.decode('ascii')

                    do_log("Build: {}, version: {}; Writing to md file: {}".format(build_name, version_name, context['filename']))

                    # Don't use dest, which allows filename to contain path info
                    d = os.path.dirname(context['filename'])
                    if not os.path.exists(d):
                        os.makedirs(d)

                    with open(context['filename'], 'w') as f:
                        f.write(markdown.encode('utf8'))
                else:
                    raise IOError("Build: {}, version: {}; *** Template not found: {}".format(build_name, version_name, template))

            version_i += 1

        build_i += 1


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
    parser.add_argument("yaml_file", type=str,
                        help="the path to a yaml file representing exam data")
    parser.add_argument("dest", type=str, default=".",
                        help="output directory. default = current directory")
    parser.add_argument("-log", "--log", action='store_true', default=False,
                        help="turn on logging")
    args = parser.parse_args()

    yaml_file = args.yaml_file
    dest = args.dest
    log = args.log

    main(yaml_file, dest)
